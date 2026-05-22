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
import pickle
import random
from typing import TYPE_CHECKING

from wumpus.engine._r0_toy_cave import initial_world
from wumpus.engine.hash import internal_state_hash
from wumpus.engine.transitions import resolve_move
from wumpus.events import SCHEMA_VERSION, Event, GameStarted
from wumpus.types import Observation, Snapshot, World

if TYPE_CHECKING:
    from wumpus.sinks import Sink

# R0 placeholder constants — see SC8. Real Yob surface text lives in
# `wumpus.surfaces.yob` (R4-S03), NOT in the engine module.
_R0_ENGINE_VERSION: str = "0.0.0"
_R0_SURFACE_ID: str = "<placeholder>"
_R0_SURFACE_VARIANT: str = "<placeholder>"


class Game:
    """OOP shell over the functional engine core.

    R0 supports `step("move <N>")` only. `shoot`, `arrow walks`, hazard
    resolution, and surface seam land in later releases.
    """

    def __init__(self, seed: int) -> None:
        self._seed: int = seed
        self._random: random.Random = random.Random(seed)
        self._world: World = initial_world()
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

    # ---- public driving-port API -----------------------------------------

    def step(self, action: str) -> Observation:
        """Apply `action` to the engine. R0 supports only `move <N>` actions.

        Returns an `Observation` describing the post-step view. Events are
        emitted to all subscribed sinks (and to `_debug_events`) in the order
        the transition produced them.
        """
        target_room = self._parse_move_action(action)
        rng_cursor = self._encode_rng_cursor()
        next_world, events = resolve_move(
            self._world, target_room, rng_cursor, self._random
        )
        self._world = next_world
        for event in events:
            self._emit(event)
        return self._render_observation()

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
        """R0 observation: placeholder rendered lines + ground-truth fields.

        The real Yob render lands at R4-S03; R0 emits `<placeholder>` lines so
        no Yob text leaks into engine code (SC8).
        """
        from wumpus.engine._r0_toy_cave import adjacent_rooms

        return Observation(
            rendered_lines=("<placeholder>",),
            prompt=None,
            outcome=None,
            player_room=self._world.player_room,
            adjacencies=adjacent_rooms(self._world.player_room),
            senses=(),
        )

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
