"""`Game` — the OOP shell over the functional engine core.

Per ADR-001 (hybrid paradigm) `Game` is a state container that calls pure
transition functions in `wumpus.engine.transitions` and holds the resulting
`World` value. Two `Game(seed=k)` instances driven through the same action
sequence are observationally equivalent (SC1 determinism contract).

R0 implements:
    - `__init__(seed: int)` constructor; deterministic from seed alone
    - `step(action: str) -> Observation` for "move <N>" actions only
    - `snapshot() -> Snapshot` serializable engine state
    - `world_state() -> World` side-effect-free internal-state read
    - `subscribe(sink) -> None` / `unsubscribe(sink) -> None`

The `_debug_events` design decision (DISTILL deferred to DELIVER): R0 ships
a private `_debug_events: list[Event]` populated alongside subscriber emission.
This is an internal observability backdoor for tests that need to compare
"engine emission with vs. without subscribers" without making the no-sink
case awkward. The attribute is leading-underscore by contract; consumers
outside the engine + tests MUST NOT depend on it.
"""

from __future__ import annotations

import base64
import enum
import pickle
import random
from typing import TYPE_CHECKING

from wumpus.engine._r0_toy_cave import initial_world as _r0_toy_initial_world
from wumpus.engine.arrow_walk import walk_arrow
from wumpus.engine.cave_gen import generate_initial_layout
from wumpus.engine.hash import internal_state_hash
from wumpus.engine.hazard_resolve import hazard_resolve
from wumpus.engine.render_terminal import lines_for_events
from wumpus.engine.sense import emit_senses_for_room
from wumpus.engine.transitions import _adjacent_rooms_for_cave, resolve_move
from wumpus.events import (
    SCHEMA_VERSION,
    ActionChosen,
    ArrowFired,
    CrookedPathRejected,
    Event,
    GameEnded,
    GameStarted,
    InstructionsShown,
    LocationReported,
    MoveResolved,
    PlayerTeleported,
    PromptIssued,
    SessionEnded,
)
from wumpus.surfaces.yob import YobSurface
from wumpus.types import (
    Observation,
    PromptKind,
    Snapshot,
    Surface,
    VariantConfig,
    World,
)

if TYPE_CHECKING:
    from wumpus.sinks import Sink

# R0 placeholder constants — see SC8. Real Yob surface text lives in
# `wumpus.surfaces.yob` (R4-S03), NOT in the engine module.
_R0_ENGINE_VERSION: str = "0.0.0"
# R4-S03: `surface_id` is now read from the injected Surface
# (`self._surface.surface_id`) on every GameStarted + Snapshot, so a non-Yob
# surface is recorded honestly. For a Yob run the value is "yob" — identical
# to the prior hardcoded constant. The `<placeholder>` token remains on
# `surface_variant` (HARNESS_PRIVATE per ADR-004) until per-turn variant
# tagging lands with the Mystery surface (R4-S05).
_R0_SURFACE_VARIANT: str = "<placeholder>"

# Cave-topology selector. "yob" is the canonical 20-room dodecahedron + FNB
# rejection-loop layout (R1-S01 default). "toy" is the R0 walking-skeleton
# 3-room linear cave, retained for the R0 acceptance + unit tests that pin
# the engine's deterministic-from-seed abstractions on the cheapest substrate.
_CAVE_YOB: str = "yob"
_CAVE_TOY: str = "toy"


def _bootstrap_seed() -> int:
    # SC1 determinism-source carve-out (R3-S03): this is the ONE permitted
    # use of `secrets` in engine code. `Game(seed=None)` calls this once to
    # roll a concrete OS-entropy integer seed; that seed is then FIXED on the
    # instance and logged in `GameStarted.seed`, so determinism is preserved
    # from this point forward (replay reuses the logged seed). `secrets`
    # appearing in any OTHER function fails the determinism-source audit.
    import secrets

    return secrets.randbits(63)


class _HazardOutcome(enum.Enum):
    """Tri-valued result of `_resolve_post_move_hazards`.

    - `NONE`: the resolver fired no events; the player is in a safe room.
      The shell should emit sense+location for the originally-targeted room.
    - `TERMINAL`: a `GameEnded` event fired (eaten_after_bump or fell_in_pit).
      The shell skips sense+location entirely.
    - `SAFE_TELEPORT`: a bat snatch teleported the player to a hazard-free
      room (no GameEnded). The shell should emit sense+location for the
      teleport destination (the current `world.player_room`).
    """

    NONE = "none"
    TERMINAL = "terminal"
    SAFE_TELEPORT = "safe_teleport"


class Game:
    """OOP shell over the functional engine core.

    R1-S01 supports `step("move <N>")` against the 20-room dodecahedron by
    default. The `cave="toy"` constructor option falls back to R0's 3-room
    linear cave for tests that pin the engine's abstractions on the cheapest
    substrate; that fallback is test-only and will be retired when R0's
    acceptance scenarios are rewritten against the real geometry.
    """

    def __init__(
        self,
        seed: int | None = None,
        cave: str = _CAVE_YOB,
        variant: VariantConfig | None = None,
        surface: Surface | None = None,
    ) -> None:
        # R2-S02: seed=None → roll an OS-entropy seed so the ledger header
        # carries a concrete integer the replay path can reuse. Without
        # this, replay would have no way to reconstruct the initial
        # layout (the seed IS the contract). The roll is delegated to the
        # dedicated `_bootstrap_seed` helper — the ONLY place `secrets` may
        # appear in engine code (SC1 determinism-source audit carve-out).
        if seed is None:
            seed = _bootstrap_seed()
        # R4-S01: `variant=None` → Yob 1973 defaults. `Game(seed=k)` is
        # equivalent to `Game(seed=k, variant=VariantConfig())`. The config
        # parameterizes cave generation (entity counts, room count) and the
        # starting arrow count without changing the internal state schema.
        self._variant: VariantConfig = (
            variant if variant is not None else VariantConfig()
        )
        # R4-S02: the ordered names of the active escalation rules, recorded
        # in every GameStarted + Snapshot so the consultation order survives
        # the JSON round-trip even though the rule OBJECTS themselves cannot
        # be reconstructed from a snapshot (they are arbitrary callables).
        self._active_escalation_rules: tuple[str, ...] = self._variant.rule_names()
        # R4-S03: the engine reads player-facing strings from an injected
        # Surface at the output boundary (SC8). `surface=None` defaults to the
        # Yob surface — `Game(seed=k)` is equivalent to
        # `Game(seed=k, surface=YobSurface())`. The surface is RNG-free and
        # never reads engine state (SC9); the engine only ever asks it to
        # translate structured tags into strings.
        self._surface: Surface = surface if surface is not None else YobSurface()
        self._seed: int = seed
        self._random: random.Random = random.Random(seed)
        self._cave: str = cave
        self._world: World = self._build_initial_world(cave)
        # R1-S07: pin the initial World snapshot for SAME SET-UP=Y restore.
        # The frozen-dataclass World is value-typed, so the reference cannot
        # be mutated; subsequent transitions REPLACE `_world` with new World
        # values, leaving `_initial_layout` intact for the lifetime of the
        # Game instance. R1-S08: `_initial_layout` is pinned BEFORE the
        # pre-game INSTRUCTIONS state is entered — restoring on SAME SET-UP=Y
        # should NOT re-show the instructions block (Yob's GOTO 360 restores
        # the cave + arrows but does not GOSUB 1000 again).
        self._initial_layout: World = self._world
        # R1-S08: production (yob) construction enters the pre-game
        # INSTRUCTIONS (Y-N)? state. The first `step()` call MUST be
        # `step("Y")` or `step("N")` (case-insensitive); other input
        # re-prompts. Toy-cave construction skips the pre-game state to
        # keep R0's deterministic-action-sequence tests untouched —
        # `cave="toy"` is a test-only substrate, the production R1-S08
        # contract does not apply.
        if cave == _CAVE_YOB:
            self._world = self._enter_instructions_state(self._world)
        # R1-S07: per-step event buffer used by `_render_observation` to
        # populate `Observation.rendered_lines` via the surface seam. Cleared
        # at the START of every `step()` call (and at the synthesized
        # post-terminal prompt emission inside the same step).
        self._step_events: list[Event] = []
        self._subscribers: list[Sink] = []
        # R0 _debug_events decision (Option A): always-populated internal
        # event log, scoped to the Game instance. Tests use this to compare
        # engine emission with vs. without a subscriber attached.
        self._debug_events: list[Event] = []

        # Emit GameStarted with post-init state.
        start_event = GameStarted(
            schema_version=SCHEMA_VERSION,
            turn=self._world.turn,
            surface_variant=_R0_SURFACE_VARIANT,
            internal_state_hash=internal_state_hash(self._world),
            rng_cursor=self._encode_rng_cursor(),
            seed=seed,
            engine_version=_R0_ENGINE_VERSION,
            surface_id=self._surface.surface_id,
            layout_hash=internal_state_hash(self._initial_layout),
            variant_config=self._variant.as_dict(),
            active_escalation_rules=self._active_escalation_rules,
        )
        self._emit(start_event)
        # R1-S08: if production (yob) pre-game state is active, emit
        # PromptIssued(kind="instructions") so the caller knows a Y/N
        # answer is awaited.
        if cave == _CAVE_YOB and self._world.pending_prompt == "instructions":
            self._emit(
                PromptIssued(
                    schema_version=SCHEMA_VERSION,
                    turn=self._world.turn,
                    surface_variant=_R0_SURFACE_VARIANT,
                    internal_state_hash=internal_state_hash(self._world),
                    rng_cursor=self._encode_rng_cursor(),
                    kind="instructions",
                    context=None,
                )
            )

    @staticmethod
    def _enter_instructions_state(world: World) -> World:
        """Return a copy of `world` with `pending_prompt="instructions"`.

        R1-S08 pre-game state — the engine awaits a Y/N answer at the
        INSTRUCTIONS (Y-N)? prompt before any other action can be taken."""
        return World(
            player_room=world.player_room,
            wumpus_rooms=world.wumpus_rooms,
            pit_rooms=world.pit_rooms,
            bat_rooms=world.bat_rooms,
            arrows=world.arrows,
            turn=world.turn,
            alive=world.alive,
            pending_prompt="instructions",
            pending_arrow_path=world.pending_arrow_path,
            pending_path_length=world.pending_path_length,
        )

    # ---- test hatch (TEST-ONLY; underscore-prefixed not in public API) ----

    @classmethod
    def _from_world(cls, world: World, *, seed: int = 0) -> "Game":
        """TEST-ONLY constructor that pins the initial World instead of rolling
        it from `seed`. The `seed` argument still seeds the engine's RNG so
        downstream RNG-consuming steps (R1-S03 startle, R1-S04 bat teleport)
        remain deterministic.

        This hatch lets acceptance tests express preconditions like "player
        adjacent to wumpus AND a pit" without searching for a seed whose FNB
        layout happens to satisfy that geometry. The underscore prefix signals
        non-public API; the contract is that the supplied World must already
        satisfy Yob's invariants (distinct entity rooms, valid 1..20 indices).
        """
        game = cls.__new__(cls)
        game._seed = seed
        game._random = random.Random(seed)
        game._cave = _CAVE_YOB
        # R4-S01: the test hatch pins a World directly, so the variant only
        # supplies the GameStarted header + SAME SET-UP restore arrow count.
        # Default VariantConfig() (Yob) is correct — the World already carries
        # whatever tuple shapes the test specified.
        game._variant = VariantConfig()
        game._active_escalation_rules = game._variant.rule_names()
        # R4-S03: the test hatch renders through the default Yob surface.
        game._surface = YobSurface()
        game._world = world
        # R1-S07: pin the initial layout for SAME SET-UP=Y restore. See
        # `__init__` for the field's contract.
        game._initial_layout = world
        game._step_events = []
        game._subscribers = []
        game._debug_events = []

        start_event = GameStarted(
            schema_version=SCHEMA_VERSION,
            turn=game._world.turn,
            surface_variant=_R0_SURFACE_VARIANT,
            internal_state_hash=internal_state_hash(game._world),
            rng_cursor=game._encode_rng_cursor(),
            seed=seed,
            engine_version=_R0_ENGINE_VERSION,
            surface_id=game._surface.surface_id,
            layout_hash=internal_state_hash(game._world),
            variant_config=game._variant.as_dict(),
            active_escalation_rules=game._active_escalation_rules,
        )
        game._emit(start_event)
        return game

    # ---- public driving-port API -----------------------------------------

    def step(self, action: str) -> Observation:
        """Apply `action` to the engine.

        R0 supported only `move <N>` actions. R1-S05 extends `step` with the
        shoot sub-state-machine: `step("S")` enters shoot mode, after which
        the engine awaits a path length (1..5), then per-slot rooms. The
        shoot sub-state-machine is driven entirely through follow-up `step`
        calls that supply the next bare integer; the engine routes on the
        World's `pending_prompt` field.

        Returns an `Observation` describing the post-step view. Events are
        emitted to all subscribed sinks (and to `_debug_events`) in the order
        the transition produced them.

        R1-S02: on a successful move (MoveAttempted accepted=True followed by
        MoveResolved) the engine emits any SenseEmitted events for the newly
        entered room in Yob L-array order, then a single LocationReported.
        Rejected moves emit only MoveAttempted(accepted=False) and skip
        sense / location emission (the player never entered a new room).

        R1-S03: after `MoveResolved` the engine checks for a co-located
        hazard via `hazard_resolve`. If the player walked into the wumpus's
        room, the resolver emits `HazardTriggered(WUMPUS)`, runs the FNC(0)
        startle, and (if the startled wumpus lands on the player) emits
        `GameEnded(eaten_after_bump)`. When a wumpus or pit hazard fires
        (terminal or near-terminal), sense + location events are suppressed
        for that room.

        R1-S04: pit and bat arms ship. A pit fall short-circuits the move
        (HazardTriggered(PIT) + GameEnded(fell_in_pit), no sense+location).
        A bat snatch emits HazardTriggered(BAT) + PlayerTeleported, then
        the resolver recurses on the new room. If the recursion lands the
        player in a safe room (no further hazard), the shell re-emits
        sense events for the new room (Yob 4280-4290 prints sense+location
        for the teleport destination), followed by LocationReported.

        R1-S05: shoot path collection. `step("S")` from the base state emits
        `ActionChosen("S")` + `PromptIssued("shoot_path_len")` and parks the
        engine in `pending_prompt="shoot_path_len"`. The next `step("<int>")`
        validates the path length (range 1-5) and either re-prompts or
        advances to per-slot prompts. The crooked-arrow rule
        `P(K) == P(K-2)` is enforced at K > 2 with `CrookedPathRejected` +
        slot-specific re-prompt. When all slots are collected, `ArrowFired`
        fires and the pending state clears (no arrow walk — that is R1-S06).

        R1-S07: post-terminal SAME SET-UP=Y/N handling. After any GameEnded
        the engine parks in `pending_prompt="same_setup"`. `step("Y")` restores
        `_initial_layout` and emits a fresh `GameStarted` (same layout_hash).
        `step("N")` emits `SessionEnded`; further actions become no-ops.
        """
        # R1-S07: clear the per-step event buffer at the start of every step
        # so `_render_observation()` only sees events from THIS step.
        self._step_events = []

        # R1-S08: pre-game INSTRUCTIONS (Y-N)? takes precedence over every
        # other dispatcher — the engine is awaiting a Y/N answer before the
        # first turn can begin.
        if self._world.pending_prompt == "instructions":
            return self._step_instructions(action)
        # R1-S07: post-terminal SAME SET-UP=Y/N takes precedence over the
        # shoot/move dispatchers — the engine is awaiting a Y/N answer, not
        # a move target or shoot input.
        if self._world.pending_prompt == "same_setup":
            return self._step_same_setup(action)
        # R1-S07: if the player is in a terminal session-ended state, ignore
        # further actions (return an empty-rendered Observation). This
        # forecloses the "what if the harness keeps poking after the game
        # ends" failure mode.
        if not self._world.alive and self._world.pending_prompt is None:
            return self._render_observation()

        # Route on pending_prompt FIRST: if the engine is mid-shoot, the
        # action is a path-length or room-slot integer string, not a move.
        if self._world.pending_prompt is not None:
            return self._step_shoot_subroutine(action)
        # Top-level: "S" enters the shoot sub-state-machine; everything else
        # goes through the existing move parser (which also defends the
        # action-grammar invariants — see `_parse_move_action`).
        if action == "S":
            return self._enter_shoot_mode()

        target_room = self._parse_move_action(action)
        rng_cursor = self._encode_rng_cursor()
        next_world, events = resolve_move(
            self._world, target_room, rng_cursor, self._random, cave=self._cave
        )
        self._world = next_world
        for event in events:
            self._emit(event)

        move_resolved = any(isinstance(event, MoveResolved) for event in events)
        if not (self._cave == _CAVE_YOB and move_resolved):
            return self._render_observation()

        hazard_outcome = self._resolve_post_move_hazards()
        if hazard_outcome == _HazardOutcome.NONE:
            self._emit_senses_and_location(target_room)
            return self._render_observation()
        if hazard_outcome == _HazardOutcome.TERMINAL:
            # GameEnded fired (eaten_after_bump or fell_in_pit). No sense+location.
            return self._render_observation()
        # SAFE_TELEPORT — bat snatch landed the player in a hazard-free
        # room. Re-emit sense+location for the new room (Yob 4280-4290).
        self._emit_senses_and_location(self._world.player_room)
        return self._render_observation()

    def _resolve_post_move_hazards(self) -> _HazardOutcome:
        """Drive `hazard_resolve` for the player's current room.

        Returns a `_HazardOutcome` discriminating the three cases the shell
        cares about:
          - `NONE`: no hazard fired; the shell continues with sense+location.
          - `TERMINAL`: `GameEnded` fired; the shell skips sense+location.
          - `SAFE_TELEPORT`: a bat snatch teleported the player to a safe
            room (no GameEnded); the shell emits sense+location for the new
            room (Yob 4280-4290 prints sense+location for the destination).

        The Game shell stamps `GameEnded.final_snapshot` with the engine's
        real Snapshot metadata (overrides the resolver's placeholder) before
        emission.
        """
        post_move_world, hazard_events = hazard_resolve(self._world, self._random)
        if not hazard_events:
            return _HazardOutcome.NONE

        self._world = post_move_world
        rng_cursor = self._encode_rng_cursor()
        for event in hazard_events:
            self._emit(self._stamp_engine_metadata(event, rng_cursor=rng_cursor))

        if any(isinstance(e, GameEnded) for e in hazard_events):
            return _HazardOutcome.TERMINAL
        if any(isinstance(e, PlayerTeleported) for e in hazard_events):
            # Bat snatch with no terminal outcome — the recursion landed
            # the player in a safe room (or a chain that bottomed out in
            # a safe room). Shell should emit sense+location for the
            # final destination.
            return _HazardOutcome.SAFE_TELEPORT
        # Non-terminal wumpus bump (startle moved the wumpus away). Treat
        # as TERMINAL-skip: the player's room state is "just bumped a
        # wumpus" — Yob does NOT re-emit sense lines for this case
        # (the player has not "entered a new room" from the sense engine's
        # perspective, even though they technically did).
        return _HazardOutcome.TERMINAL

    def _stamp_engine_metadata(self, event: Event, *, rng_cursor: str) -> Event:
        """Replace the resolver's placeholder Game-shell fields (rng_cursor;
        for GameEnded, also `final_snapshot` metadata) with the engine's real
        values. The resolver is pure-functional and doesn't know the Game's
        seed/engine_version/surface_id; the shell fills those in here.

        Per ADR-003 every emitted event carries the post-effect rng_cursor;
        the resolver leaves the field at its default ("") and the shell
        rewrites it before emission so downstream replay/ledger consumers see
        a complete chain.
        """
        from dataclasses import replace

        if isinstance(event, GameEnded):
            real_snapshot = self.snapshot()
            return replace(event, rng_cursor=rng_cursor, final_snapshot=real_snapshot)
        # HazardTriggered + WumpusStartled both leave rng_cursor=""; stamp them.
        return replace(event, rng_cursor=rng_cursor)

    def _emit_senses_and_location(self, entered_room: int) -> None:
        """Emit SenseEmitted events for `entered_room` (Yob L-array order),
        then exactly one LocationReported. Called from `step()` after a
        successful move resolves.

        R2-S03: the pure `emit_senses_for_room` leaves `rng_cursor=""` on each
        returned SenseEmitted (the pure function doesn't know the Game's
        RNG). The shell stamps the current cursor here so SenseEmitted events
        carry a non-placeholder rng_cursor downstream — matching the
        treatment of hazard_resolve / arrow_walk events via
        `_stamp_engine_metadata`.
        """
        sense_events = emit_senses_for_room(self._world, entered_room)
        rng_cursor = self._encode_rng_cursor()
        for sense_event in sense_events:
            self._emit(self._stamp_engine_metadata(sense_event, rng_cursor=rng_cursor))

        adjacencies = _adjacent_rooms_for_cave(self._cave, entered_room)
        # Dodecahedron is 3-regular; narrow the variable-length tuple to the
        # LocationReported field's `tuple[int, int, int]` invariant. An
        # assertion documents the invariant in case any future cave topology
        # violates it (e.g. test-only toy caves would re-enter sense emission).
        assert len(adjacencies) == 3, (
            f"LocationReported requires a 3-regular cave; room {entered_room} "
            f"under cave {self._cave!r} has {len(adjacencies)} neighbors."
        )
        location_event = LocationReported(
            schema_version=SCHEMA_VERSION,
            turn=self._world.turn,
            surface_variant=_R0_SURFACE_VARIANT,
            internal_state_hash=internal_state_hash(self._world),
            rng_cursor=self._encode_rng_cursor(),
            room=entered_room,
            adjacencies=(adjacencies[0], adjacencies[1], adjacencies[2]),
        )
        self._emit(location_event)

    def snapshot(self) -> Snapshot:
        """Return a serializable Snapshot of the current engine state.

        Per SC6 the snapshot is fully serializable (no `random.Random` object;
        the RNG state is base64-encoded). Calling `snapshot()` is side-effect-
        free: no RNG consumption, no event emission.

        R3-S01: the snapshot now carries `initial_layout` (the World at
        construction-time, pinned for SAME SET-UP=Y restore) and `cave` (the
        toy/yob discriminator). Without these the snapshot/restore round-trip
        was broken for SAME SET-UP=Y after a snapshot-restore: `from_snapshot`
        used to set `_initial_layout = world` (the mid-game world), so a
        subsequent SAME SET-UP=Y would restore the mid-game cave, not the
        original new-game layout.
        """
        return Snapshot(
            schema_version=SCHEMA_VERSION,
            engine_version=_R0_ENGINE_VERSION,
            seed=self._seed,
            rng_cursor=self._encode_rng_cursor(),
            surface_id=self._surface.surface_id,
            world=self._world,
            active_escalation_rules=self._active_escalation_rules,
            initial_layout=self._initial_layout,
            cave=self._cave,
        )

    def world_state(self) -> World:
        """Return the current internal World. Side-effect-free (Goal 5.2).

        The World is a frozen dataclass; callers cannot mutate it. Calling
        `world_state()` MUST NOT advance the RNG cursor and MUST NOT emit
        events (asserted by R0 scenario 3).
        """
        return self._world

    def subscribe(self, sink: Sink) -> None:
        """Register `sink` to receive events in engine-emission order.

        On subscription the engine replays the full historical event sequence
        to `sink` synchronously, so the sink's recorded events ALWAYS equal
        `_debug_events` regardless of when in the Game's lifetime it attached
        (per ADR-008 + R0 scenario 2's observer-effect-absent claim). Replay
        is synchronous on the engine's thread; ordering matches engine order.
        """
        for past_event in self._debug_events:
            sink.emit(past_event)
        self._subscribers.append(sink)

    def unsubscribe(self, sink: Sink) -> None:
        """Remove `sink`. No-op if not currently subscribed."""
        if sink in self._subscribers:
            self._subscribers.remove(sink)

    # ---- internals -------------------------------------------------------

    def _emit(self, event: Event) -> None:
        """Emit `event` to all subscribers in engine-order, then record it
        in `_debug_events`.

        Per ADR-008 emission is synchronous + engine-ordered. The `_debug_events`
        list is populated AFTER subscriber emission so the two lists are
        ordering-equivalent (and so the "no sinks attached" scenario can compare
        them directly).

        R1-S07: also appends to `_step_events` (the per-step buffer feeding
        `Observation.rendered_lines` via the surface seam). The buffer is
        cleared at the top of every `step()` call.

        R4-S02: the engine consults `VariantConfig.escalation_rules` here, the
        single event-emission funnel. Each rule's `filter_events` hook is
        applied in left-to-right order; a rule may rewrite/drop/augment the
        event stream. This is the smallest honest wiring of the escalation
        slot (caveat C-R4-S02): the funnel is the one place every event
        passes through, so consultation order is observable and survives the
        snapshot round-trip via `active_escalation_rules`. With the default
        (no rules) or `IdentityRule`, the stream is unchanged — a no-rules run
        is byte-identical to an `IdentityRule` run (R4-S02 interim gate).
        Downstream L3/L4 features own the real rule logic.
        """
        for emitted in self._apply_escalation_rules(event):
            self._emit_one(emitted)

    def _apply_escalation_rules(self, event: Event) -> list[Event]:
        """Fold the active escalation rules over `[event]` left-to-right via
        their `filter_events` hook. Returns the (possibly rewritten) event
        list to actually emit. No rules → the single-element list unchanged."""
        events: list[Event] = [event]
        for rule in self._variant.escalation_rules:
            events = list(rule.filter_events(events, self._world))
        return events

    def _emit_one(self, event: Event) -> None:
        """Deliver a single (post-rule) event to subscribers + the internal
        logs, and run the R1-S07 post-terminal SAME SET-UP hook."""
        for sink in self._subscribers:
            sink.emit(event)
        self._debug_events.append(event)
        # `_step_events` may not yet exist on Game instances constructed
        # before R1-S07 wired it in (snapshot reconstruction path, for
        # example, runs `__new__` without `__init__`). Defensive init.
        if not hasattr(self, "_step_events"):
            self._step_events = []
        self._step_events.append(event)

        # R1-S07: post-terminal hook — when a GameEnded fires, immediately
        # follow with a SAME SET-UP prompt so the engine is parked awaiting
        # a Y/N answer. The prompt issuance is synthesized here (NOT in
        # hazard_resolve / arrow_walk) because those are pure functions
        # that don't know about post-terminal UI state. Parking the engine
        # in `pending_prompt="same_setup"` is the Game shell's responsibility.
        if isinstance(event, GameEnded) and self._world.pending_prompt != "same_setup":
            self._enter_same_setup_state()

    def _encode_rng_cursor(self) -> str:
        """Base64-encoded pickled `random.Random.getstate()` per ADR-001/SC6."""
        state_bytes = pickle.dumps(self._random.getstate())
        return base64.b64encode(state_bytes).decode("ascii")

    def _render_observation(self) -> Observation:
        """Surface-translated rendered lines for THIS step's events.

        R4-S03 routes the render through the injected Surface object
        (`self._surface`) at the output boundary — `render_terminal` dispatches
        each event to the active surface. The terminal + hazard + instructions
        + prompt arms render; R1-S02-render adds the per-turn gameplay arms
        (SenseEmitted → sense lines, LocationReported → "YOU ARE IN ROOM  <n>"
        + "TUNNELS LEAD TO  <a>  <b>  <c>"). Rendering is strictly downstream of
        event emission: it maps already-emitted events to display lines and
        does not change which events fire, their payloads, internal_state_hash,
        rng_cursor, or determinism. Other event kinds (MoveResolved, ...) still
        contribute zero lines.

        Per SC8 (surface seam) no Yob text lives in engine code — the
        translator is `wumpus.engine.render_terminal`, which reads strings from
        the Surface (`wumpus.surfaces.yob.YobSurface` by default).
        """
        adjacencies = _adjacent_rooms_for_cave(self._cave, self._world.player_room)
        # `_step_events` is the per-step emission buffer. May be absent on
        # snapshot-resurrected instances (Game.__new__ path); defensive default.
        step_events = getattr(self, "_step_events", ())
        surface = getattr(self, "_surface", None)
        rendered_lines = lines_for_events(step_events, surface)
        return Observation(
            rendered_lines=rendered_lines,
            prompt=None,
            outcome=None,
            player_room=self._world.player_room,
            adjacencies=adjacencies,
            senses=(),
        )

    # ---- R1-S08 INSTRUCTIONS state machine -------------------------------

    def _step_instructions(self, action: str) -> Observation:
        """Handle a step from the pre-game `pending_prompt="instructions"`
        state. Accepts case-insensitive 'Y' / 'N'; any other input
        re-prompts (and the turn counter does not advance — the pre-game
        prompt is not an action-completing event per the monotonic_turn
        discipline).

        On Y: emit `InstructionsShown` with the full verbatim Yob
        instructions block; the surface renders the block followed by the
        HUNT THE WUMPUS banner.

        On N: emit `InstructionsShown` with an empty lines payload; the
        surface renders just the banner (skipping the instructions text).
        This single event-shape handles both arms — the lines payload
        discriminates them.

        On invalid input: re-emit `PromptIssued(kind="instructions")`.
        """
        answer = action.strip().upper()
        if answer == "Y":
            return self._reveal_instructions(lines=self._surface.instructions_block())
        if answer == "N":
            return self._reveal_instructions(lines=())
        # Malformed answer — re-prompt by re-emitting the INSTRUCTIONS prompt.
        self._reissue_prompt("instructions", context=None)
        return self._render_observation()

    def _reveal_instructions(self, *, lines: tuple[str, ...]) -> Observation:
        """Emit InstructionsShown and clear `pending_prompt` so the engine
        leaves the pre-game state.

        On Y the `lines` payload carries the full verbatim Yob block; on N
        it is empty (the surface renders just the banner). After emission
        the engine is in its normal turn-zero state ready for the first
        player action; the first-turn sense+location lands at R4-S03.
        """
        new_world = World(
            player_room=self._world.player_room,
            wumpus_rooms=self._world.wumpus_rooms,
            pit_rooms=self._world.pit_rooms,
            bat_rooms=self._world.bat_rooms,
            arrows=self._world.arrows,
            turn=self._world.turn,
            alive=self._world.alive,
            pending_prompt=None,
            pending_arrow_path=self._world.pending_arrow_path,
            pending_path_length=self._world.pending_path_length,
        )
        self._world = new_world
        self._emit(
            InstructionsShown(
                schema_version=SCHEMA_VERSION,
                turn=new_world.turn,
                surface_variant=_R0_SURFACE_VARIANT,
                internal_state_hash=internal_state_hash(new_world),
                rng_cursor=self._encode_rng_cursor(),
                lines=lines,
            )
        )
        return self._render_observation()

    # ---- R1-S07 SAME SET-UP state machine --------------------------------

    def _enter_same_setup_state(self) -> None:
        """Park the engine in the post-terminal `pending_prompt="same_setup"`
        state and emit a `PromptIssued(kind="same_setup")` so the caller
        (renderer, harness, agent) knows a Y/N answer is awaited.

        Called from `_emit` immediately after any `GameEnded` event.
        """
        terminal_world = self._world
        new_world = World(
            player_room=terminal_world.player_room,
            wumpus_rooms=terminal_world.wumpus_rooms,
            pit_rooms=terminal_world.pit_rooms,
            bat_rooms=terminal_world.bat_rooms,
            arrows=terminal_world.arrows,
            turn=terminal_world.turn,
            alive=terminal_world.alive,
            pending_prompt="same_setup",
            pending_arrow_path=terminal_world.pending_arrow_path,
            pending_path_length=terminal_world.pending_path_length,
        )
        self._world = new_world
        self._emit(
            PromptIssued(
                schema_version=SCHEMA_VERSION,
                turn=new_world.turn,
                surface_variant=_R0_SURFACE_VARIANT,
                internal_state_hash=internal_state_hash(new_world),
                rng_cursor=self._encode_rng_cursor(),
                kind="same_setup",
                context=None,
            )
        )

    def _step_same_setup(self, action: str) -> Observation:
        """Handle a step from the post-terminal `pending_prompt="same_setup"`
        state. Accepts case-insensitive 'Y' / 'N'; any other input re-prompts."""
        answer = action.strip().upper()
        if answer == "Y":
            return self._restore_initial_layout()
        if answer == "N":
            return self._end_session()
        # Malformed answer — re-prompt by re-emitting the SAME SET-UP prompt.
        self._emit(
            PromptIssued(
                schema_version=SCHEMA_VERSION,
                turn=self._world.turn,
                surface_variant=_R0_SURFACE_VARIANT,
                internal_state_hash=internal_state_hash(self._world),
                rng_cursor=self._encode_rng_cursor(),
                kind="same_setup",
                context=None,
            )
        )
        return self._render_observation()

    def _restore_initial_layout(self) -> Observation:
        """Restore `_initial_layout` and emit a fresh `GameStarted` with the
        same `layout_hash`. The RNG is NOT reseeded — Yob's same-setup replay
        continues the RNG cursor where the prior game left it (subsequent
        startle / bat-teleport draws differ across replays).

        Per the R1-S07 brief: turn counter zeroed, arrow count restored to
        the initial, alive=True, no pending prompt.
        """
        self._world = self._initial_layout
        self._emit(
            GameStarted(
                schema_version=SCHEMA_VERSION,
                turn=self._world.turn,
                surface_variant=_R0_SURFACE_VARIANT,
                internal_state_hash=internal_state_hash(self._world),
                rng_cursor=self._encode_rng_cursor(),
                seed=self._seed,
                engine_version=_R0_ENGINE_VERSION,
                surface_id=self._surface.surface_id,
                layout_hash=internal_state_hash(self._world),
                variant_config=self._variant.as_dict(),
                active_escalation_rules=self._active_escalation_rules,
            )
        )
        return self._render_observation()

    def _end_session(self) -> Observation:
        """Emit `SessionEnded` and park the engine in a no-op terminal state.

        Per the R1-S07 brief: SAME SET-UP=N is the minimal "session close"
        for the experiment matrix. The fresh-cave-from-the-rolling-RNG
        behavior Yob does is generalizable to a downstream slice (or to the
        harness layer driving multi-game replay sequences).
        """
        # Clear pending_prompt and leave alive=False so the early-return in
        # step() short-circuits any further action.
        new_world = World(
            player_room=self._world.player_room,
            wumpus_rooms=self._world.wumpus_rooms,
            pit_rooms=self._world.pit_rooms,
            bat_rooms=self._world.bat_rooms,
            arrows=self._world.arrows,
            turn=self._world.turn,
            alive=False,
            pending_prompt=None,
            pending_arrow_path=self._world.pending_arrow_path,
            pending_path_length=self._world.pending_path_length,
        )
        self._world = new_world
        self._emit(
            SessionEnded(
                schema_version=SCHEMA_VERSION,
                turn=new_world.turn,
                surface_variant=_R0_SURFACE_VARIANT,
                internal_state_hash=internal_state_hash(new_world),
                rng_cursor=self._encode_rng_cursor(),
            )
        )
        return self._render_observation()

    def _build_initial_world(self, cave: str) -> World:
        """Construct the initial World per the selected cave topology.

        - `"yob"`: roll Yob's FNB rejection-loop layout from the seeded RNG
          against the 20-room dodecahedron (R1-S01 canonical path).
        - `"toy"`: return the R0 walking-skeleton 3-room linear cave fixture
          (test-only; no RNG consumed).
        """
        if cave == _CAVE_YOB:
            # R4-S01: cave generation is parameterized by the VariantConfig
            # (entity counts + room_count); arrows initialize from
            # `arrow_count`. The default VariantConfig() reproduces the Yob
            # FNB layout byte-identically for a given seed.
            layout = generate_initial_layout(self._random, self._variant)
            return World(
                player_room=layout.player_start,
                wumpus_rooms=layout.wumpus_rooms,
                pit_rooms=layout.pit_rooms,
                bat_rooms=layout.bat_rooms,
                arrows=self._variant.arrow_count,
                turn=0,
                alive=True,
                pending_prompt=None,
                pending_arrow_path=(),
            )
        if cave == _CAVE_TOY:
            return _r0_toy_initial_world()
        raise ValueError(f"Unknown cave topology: {cave!r}. Expected 'yob' or 'toy'.")

    @staticmethod
    def _parse_move_action(action: str) -> int:
        """Parse a `move <N>` action string into the target room int.

        R0 accepts only the literal prefix `"move "` followed by a positive
        integer. Anything else raises ValueError — this is the engine's
        defense against R1+ action types leaking back into R0.
        """
        parts = action.split()
        if len(parts) != 2 or parts[0] != "move":
            raise ValueError(
                f"R0 engine accepts only 'move <N>' actions; got: {action!r}"
            )
        try:
            return int(parts[1])
        except ValueError as exc:
            raise ValueError(
                f"R0 move action target must be an integer; got: {parts[1]!r}"
            ) from exc

    # ---- R1-S05 shoot sub-state-machine ----------------------------------

    def _enter_shoot_mode(self) -> Observation:
        """Handle `step("S")` from the base state.

        Emits `ActionChosen("S")` + `PromptIssued("shoot_path_len")` and
        parks the World in `pending_prompt="shoot_path_len"`. The turn
        counter does NOT advance — picking S is not an action-completing
        event; the action completes on `ArrowFired`.
        """
        new_world = self._with_pending(
            pending_prompt="shoot_path_len",
            pending_arrow_path=(),
            pending_path_length=None,
        )
        self._world = new_world
        rng_cursor = self._encode_rng_cursor()
        self._emit(
            ActionChosen(
                schema_version=SCHEMA_VERSION,
                turn=new_world.turn,
                surface_variant=_R0_SURFACE_VARIANT,
                internal_state_hash=internal_state_hash(new_world),
                rng_cursor=rng_cursor,
                action="S",
            )
        )
        self._emit(
            PromptIssued(
                schema_version=SCHEMA_VERSION,
                turn=new_world.turn,
                surface_variant=_R0_SURFACE_VARIANT,
                internal_state_hash=internal_state_hash(new_world),
                rng_cursor=rng_cursor,
                kind="shoot_path_len",
                context=None,
            )
        )
        return self._render_observation()

    def _step_shoot_subroutine(self, action: str) -> Observation:
        """Dispatch a shoot-mode `step(action)` based on `pending_prompt`."""
        pending = self._world.pending_prompt
        if pending == "shoot_path_len":
            return self._handle_path_length_entry(action)
        if pending == "shoot_path_room":
            return self._handle_room_slot_entry(action)
        raise ValueError(f"Unknown pending_prompt {pending!r}; engine routing bug.")

    def _handle_path_length_entry(self, action: str) -> Observation:
        """Validate a NO. OF ROOMS(1-5)? entry. Out-of-range re-prompts;
        valid → advance to per-slot collection."""
        path_length = _parse_int_or_none(action)
        if path_length is None or not (1 <= path_length <= 5):
            self._reissue_prompt("shoot_path_len", context=None)
            return self._render_observation()
        # Valid path length: advance to slot-1 collection.
        new_world = self._with_pending(
            pending_prompt="shoot_path_room",
            pending_arrow_path=(),
            pending_path_length=path_length,
        )
        self._world = new_world
        self._reissue_prompt(
            "shoot_path_room",
            context={"slot": 1, "of": path_length},
        )
        return self._render_observation()

    def _handle_room_slot_entry(self, action: str) -> Observation:
        """Validate a ROOM #? slot entry. Crooked at K>2 re-prompts the
        same slot; valid → append to path and advance (or finalize)."""
        attempted_room = _parse_int_or_none(action)
        current_path = self._world.pending_arrow_path
        slot = len(current_path) + 1  # 1-indexed
        path_length = self._world.pending_path_length
        assert path_length is not None, (
            "pending_path_length must be set during shoot_path_room phase; "
            "this is an engine routing invariant."
        )
        if attempted_room is None:
            # Malformed entry: re-prompt the same slot.
            self._reissue_prompt(
                "shoot_path_room",
                context={"slot": slot, "of": path_length},
            )
            return self._render_observation()
        # Crooked-arrow check: P(K) == P(K-2) only at K > 2.
        if slot > 2 and attempted_room == current_path[slot - 3]:
            self._emit_crooked_rejection(slot, attempted_room)
            self._reissue_prompt(
                "shoot_path_room",
                context={"slot": slot, "of": path_length},
            )
            return self._render_observation()
        # Accept the slot. Append to path.
        new_path = current_path + (attempted_room,)
        if slot < path_length:
            # More slots to collect.
            new_world = self._with_pending(
                pending_prompt="shoot_path_room",
                pending_arrow_path=new_path,
                pending_path_length=path_length,
            )
            self._world = new_world
            self._reissue_prompt(
                "shoot_path_room",
                context={"slot": slot + 1, "of": path_length},
            )
            return self._render_observation()
        # Final slot: emit ArrowFired and clear pending state.
        # Turn counter advances here per the action-completing-events rule.
        cleared_world = World(
            player_room=self._world.player_room,
            wumpus_rooms=self._world.wumpus_rooms,
            pit_rooms=self._world.pit_rooms,
            bat_rooms=self._world.bat_rooms,
            arrows=self._world.arrows,
            turn=self._world.turn + 1,
            alive=self._world.alive,
            pending_prompt=None,
            pending_arrow_path=(),
            pending_path_length=None,
        )
        self._world = cleared_world
        self._emit(
            ArrowFired(
                schema_version=SCHEMA_VERSION,
                turn=cleared_world.turn,
                surface_variant=_R0_SURFACE_VARIANT,
                internal_state_hash=internal_state_hash(cleared_world),
                rng_cursor=self._encode_rng_cursor(),
                path=new_path,
            )
        )
        # R1-S06: walk the arrow through the dodecahedron. The walk emits
        # ArrowPathStep events, then a terminal arm (hit / self-shot / miss).
        self._fire_arrow_walk(new_path)
        return self._render_observation()

    def _fire_arrow_walk(self, path: tuple[int, ...]) -> None:
        """Drive `walk_arrow` for the collected `path`. The walk is pure;
        the shell stamps `rng_cursor` (and `GameEnded.final_snapshot`) onto
        each emitted event before pushing to subscribers.

        Per ADR-001/SC6, the rng_cursor is the post-walk cursor (it advances
        as `walk_arrow` consumes randint draws). The walk does not advance
        the turn counter (that already happened on ArrowFired)."""
        new_world, walk_events = walk_arrow(self._world, path, self._random)
        self._world = new_world
        rng_cursor = self._encode_rng_cursor()
        for event in walk_events:
            self._emit(self._stamp_engine_metadata(event, rng_cursor=rng_cursor))

    def _emit_crooked_rejection(self, slot: int, attempted_room: int) -> None:
        self._emit(
            CrookedPathRejected(
                schema_version=SCHEMA_VERSION,
                turn=self._world.turn,
                surface_variant=_R0_SURFACE_VARIANT,
                internal_state_hash=internal_state_hash(self._world),
                rng_cursor=self._encode_rng_cursor(),
                slot=slot,
                attempted_room=attempted_room,
            )
        )

    def _reissue_prompt(
        self,
        kind: PromptKind,
        *,
        context: dict[str, int | str] | None,
    ) -> None:
        self._emit(
            PromptIssued(
                schema_version=SCHEMA_VERSION,
                turn=self._world.turn,
                surface_variant=_R0_SURFACE_VARIANT,
                internal_state_hash=internal_state_hash(self._world),
                rng_cursor=self._encode_rng_cursor(),
                kind=kind,
                context=context,
            )
        )

    def _with_pending(
        self,
        *,
        pending_prompt: str | None,
        pending_arrow_path: tuple[int, ...],
        pending_path_length: int | None,
    ) -> World:
        """Return a copy of `self._world` with the three pending-state fields
        replaced. Used by the shoot sub-state-machine transitions."""
        return World(
            player_room=self._world.player_room,
            wumpus_rooms=self._world.wumpus_rooms,
            pit_rooms=self._world.pit_rooms,
            bat_rooms=self._world.bat_rooms,
            arrows=self._world.arrows,
            turn=self._world.turn,
            alive=self._world.alive,
            pending_prompt=pending_prompt,
            pending_arrow_path=pending_arrow_path,
            pending_path_length=pending_path_length,
        )

    # ---- R1-S05 from_snapshot --------------------------------------------

    @classmethod
    def from_snapshot(cls, snapshot: Snapshot) -> "Game":
        """Reconstruct a Game from a Snapshot.

        Per SC6 the snapshot is fully serializable and round-trippable. The
        reconstructed Game:
          - has its World restored verbatim (including any mid-shoot pending
            state: `pending_prompt`, `pending_arrow_path`, `pending_path_length`)
          - has its RNG restored from the encoded `rng_cursor`
          - emits a `GameStarted` event tagged with the snapshot's seed
          - if the World is mid-shoot, re-emits the awaiting `PromptIssued`
            so the resurrected event stream tells a downstream consumer
            (renderer, agent, ledger reader) what input the engine awaits

        The seed on the emitted `GameStarted` is the snapshot's seed; replay
        consumers reconstruct the full event chain by combining the prior
        event log (from a sink) with the post-resurrection stream.
        """
        game = cls.__new__(cls)
        game._seed = snapshot.seed
        game._random = _decode_rng_cursor(snapshot.rng_cursor)
        # R4-S01: the Snapshot does NOT carry a variant_config field (adding
        # one would change the Snapshot field set — scenario 4's no-schema-
        # change canary forbids that). A resurrected Game uses the default
        # VariantConfig() for its header; the World it restores already
        # carries whatever tuple shapes the variant produced (the variant
        # never adds fields, so the restored World is complete on its own).
        game._variant = VariantConfig()
        # R4-S02: the rule OBJECTS cannot be reconstructed from a snapshot
        # (they are arbitrary callables), but the engine preserves their
        # ordered NAMES so the consultation-order contract survives the
        # round-trip. A resurrected Game reports the same active rule names in
        # its header + subsequent snapshots. (Re-attaching live rule objects
        # to a resurrected Game is a downstream-feature concern.)
        game._active_escalation_rules = snapshot.active_escalation_rules
        # R4-S03: the Snapshot records only the surface_id string (a Surface
        # object is arbitrary and not serializable, same as escalation rules).
        # A resurrected Game renders through the default Yob surface; if the
        # snapshot recorded a non-Yob surface_id, re-attaching the live surface
        # object is a downstream-feature concern (the engine's internal
        # trajectory is surface-independent by SC9, so replay determinism does
        # not depend on it). The header still reports the surface's own id.
        game._surface = YobSurface()
        # R3-S01: cave topology now round-trips. Snapshots from pre-R3-S01
        # call sites (constructed without `cave`) default to "yob" per the
        # Snapshot dataclass default — the historical behavior.
        game._cave = snapshot.cave
        game._world = snapshot.world
        # R3-S01: initial_layout now round-trips. The Snapshot dataclass
        # default is `None` for back-compat with pre-R3-S01 fixtures; when
        # absent we fall back to the resurrected world (matching the
        # pre-R3-S01 behavior — broken for SAME SET-UP=Y after a
        # snapshot/restore, but no worse than what shipped at R1-S07).
        game._initial_layout = (
            snapshot.initial_layout
            if snapshot.initial_layout is not None
            else snapshot.world
        )
        game._step_events = []
        game._subscribers = []
        game._debug_events = []

        start_event = GameStarted(
            schema_version=SCHEMA_VERSION,
            turn=game._world.turn,
            surface_variant=_R0_SURFACE_VARIANT,
            internal_state_hash=internal_state_hash(game._world),
            rng_cursor=game._encode_rng_cursor(),
            seed=snapshot.seed,
            engine_version=_R0_ENGINE_VERSION,
            surface_id=game._surface.surface_id,
            layout_hash=internal_state_hash(game._world),
            variant_config=game._variant.as_dict(),
            active_escalation_rules=snapshot.active_escalation_rules,
        )
        game._emit(start_event)

        # Re-emit the pending prompt so the resurrected event stream reflects
        # what the engine awaits next. Mid-shoot snapshots replay the
        # awaiting-slot context.
        if game._world.pending_prompt == "shoot_path_room":
            slot = len(game._world.pending_arrow_path) + 1
            of = game._world.pending_path_length
            assert of is not None, (
                "Snapshot in shoot_path_room state must have a path length."
            )
            game._emit(
                PromptIssued(
                    schema_version=SCHEMA_VERSION,
                    turn=game._world.turn,
                    surface_variant=_R0_SURFACE_VARIANT,
                    internal_state_hash=internal_state_hash(game._world),
                    rng_cursor=game._encode_rng_cursor(),
                    kind="shoot_path_room",
                    context={"slot": slot, "of": of},
                )
            )
        elif game._world.pending_prompt == "shoot_path_len":
            game._emit(
                PromptIssued(
                    schema_version=SCHEMA_VERSION,
                    turn=game._world.turn,
                    surface_variant=_R0_SURFACE_VARIANT,
                    internal_state_hash=internal_state_hash(game._world),
                    rng_cursor=game._encode_rng_cursor(),
                    kind="shoot_path_len",
                    context=None,
                )
            )
        return game


def _parse_int_or_none(action: str) -> int | None:
    """Parse `action` as a bare integer; return None if it fails. Used by
    the shoot sub-state-machine where a non-integer input is treated as a
    malformed entry that simply re-prompts (Yob's BASIC `INPUT` parses on
    type)."""
    try:
        return int(action)
    except ValueError:
        return None


def _decode_rng_cursor(rng_cursor: str) -> random.Random:
    """Inverse of `Game._encode_rng_cursor`: base64-decode + unpickle the
    `random.Random.getstate()` tuple and rebuild a Random instance."""
    state_bytes = base64.b64decode(rng_cursor.encode("ascii"))
    state = pickle.loads(state_bytes)
    rng = random.Random()
    rng.setstate(state)
    return rng
