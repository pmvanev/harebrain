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
from wumpus.engine.cave_gen import generate_initial_layout
from wumpus.engine.hash import internal_state_hash
from wumpus.engine.hazard_resolve import hazard_resolve
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
    LocationReported,
    MoveResolved,
    PlayerTeleported,
    PromptIssued,
)
from wumpus.types import Observation, PromptKind, Snapshot, World

if TYPE_CHECKING:
    from wumpus.sinks import Sink

# R0 placeholder constants — see SC8. Real Yob surface text lives in
# `wumpus.surfaces.yob` (R4-S03), NOT in the engine module.
_R0_ENGINE_VERSION: str = "0.0.0"
_R0_SURFACE_ID: str = "<placeholder>"
_R0_SURFACE_VARIANT: str = "<placeholder>"

# Cave-topology selector. "yob" is the canonical 20-room dodecahedron + FNB
# rejection-loop layout (R1-S01 default). "toy" is the R0 walking-skeleton
# 3-room linear cave, retained for the R0 acceptance + unit tests that pin
# the engine's deterministic-from-seed abstractions on the cheapest substrate.
_CAVE_YOB: str = "yob"
_CAVE_TOY: str = "toy"


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

    def __init__(self, seed: int, cave: str = _CAVE_YOB) -> None:
        self._seed: int = seed
        self._random: random.Random = random.Random(seed)
        self._cave: str = cave
        self._world: World = self._build_initial_world(cave)
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
            surface_id=_R0_SURFACE_ID,
            layout_hash=internal_state_hash(self._world),
            active_escalation_rules=(),
        )
        self._emit(start_event)

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
        game._world = world
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
            surface_id=_R0_SURFACE_ID,
            layout_hash=internal_state_hash(game._world),
            active_escalation_rules=(),
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
        """
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
        successful move resolves."""
        sense_events = emit_senses_for_room(self._world, entered_room)
        for sense_event in sense_events:
            self._emit(sense_event)

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
        """
        return Snapshot(
            schema_version=SCHEMA_VERSION,
            engine_version=_R0_ENGINE_VERSION,
            seed=self._seed,
            rng_cursor=self._encode_rng_cursor(),
            surface_id=_R0_SURFACE_ID,
            world=self._world,
            active_escalation_rules=(),
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
        """
        for sink in self._subscribers:
            sink.emit(event)
        self._debug_events.append(event)

    def _encode_rng_cursor(self) -> str:
        """Base64-encoded pickled `random.Random.getstate()` per ADR-001/SC6."""
        state_bytes = pickle.dumps(self._random.getstate())
        return base64.b64encode(state_bytes).decode("ascii")

    def _render_observation(self) -> Observation:
        """Placeholder rendered lines + ground-truth fields.

        The real Yob render lands at R4-S03; until then the engine emits
        `<placeholder>` lines so no Yob text leaks into engine code (SC8).
        """
        adjacencies = _adjacent_rooms_for_cave(self._cave, self._world.player_room)
        return Observation(
            rendered_lines=("<placeholder>",),
            prompt=None,
            outcome=None,
            player_room=self._world.player_room,
            adjacencies=adjacencies,
            senses=(),
        )

    def _build_initial_world(self, cave: str) -> World:
        """Construct the initial World per the selected cave topology.

        - `"yob"`: roll Yob's FNB rejection-loop layout from the seeded RNG
          against the 20-room dodecahedron (R1-S01 canonical path).
        - `"toy"`: return the R0 walking-skeleton 3-room linear cave fixture
          (test-only; no RNG consumed).
        """
        if cave == _CAVE_YOB:
            layout = generate_initial_layout(self._random)
            return World(
                player_room=layout.player_start,
                wumpus_rooms=layout.wumpus_rooms,
                pit_rooms=layout.pit_rooms,
                bat_rooms=layout.bat_rooms,
                arrows=0,
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
        raise ValueError(
            f"Unknown pending_prompt {pending!r}; engine routing bug."
        )

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
        return self._render_observation()

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
        game._cave = _CAVE_YOB
        game._world = snapshot.world
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
            surface_id=_R0_SURFACE_ID,
            layout_hash=internal_state_hash(game._world),
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
