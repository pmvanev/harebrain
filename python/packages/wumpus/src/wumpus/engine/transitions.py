"""Pure transition functions on `World` values.

Per ADR-001 (hybrid paradigm) all state changes flow through pure functions
here. Each transition takes a `World` (and optionally an RNG) and returns
`(new_world, events_to_emit)`. The functions never read or write module-level
state; they never mutate the input World.

R0 ships only `resolve_move`. R1+ adds `resolve_shoot`, `resolve_hazard`,
`walk_arrow`, `startle_wumpus` per the DESIGN module sketch.
"""

from __future__ import annotations

import random

from wumpus.constants import DODECAHEDRON
from wumpus.engine._r0_toy_cave import adjacent_rooms as _toy_adjacent_rooms
from wumpus.engine.hash import internal_state_hash
from wumpus.events import (
    SCHEMA_VERSION,
    Event,
    MoveAttempted,
    MoveResolved,
)
from wumpus.types import World

# R0 surface placeholder — see SC8 ("don't seed Yob text into engine code").
_R0_SURFACE_VARIANT: str = "<placeholder>"

_CAVE_YOB: str = "yob"
_CAVE_TOY: str = "toy"


def _adjacent_rooms_for_cave(cave: str, room: int) -> tuple[int, ...]:
    """Return the neighbors of `room` under the named cave topology.

    - `"yob"`: the audited 20-room dodecahedron from `wumpus.constants`.
    - `"toy"`: the R0 walking-skeleton 3-room linear cave.

    Yob neighbor sets are returned in sorted order so the tuple is stable
    across runs (frozenset iteration order is not guaranteed).
    """
    if cave == _CAVE_YOB:
        return tuple(sorted(DODECAHEDRON[room]))
    if cave == _CAVE_TOY:
        return _toy_adjacent_rooms(room)
    raise ValueError(f"Unknown cave topology: {cave!r}. Expected 'yob' or 'toy'.")


def resolve_move(
    world: World,
    target_room: int,
    rng_cursor: str,
    rng: random.Random,
    cave: str = _CAVE_YOB,
) -> tuple[World, list[Event]]:
    """Resolve a `move <target_room>` action on `world`.

    Returns the new World value and the list of events the engine should emit.
    The `rng` parameter is threaded through unused at R1-S01 (no startle / no
    hazard resolution), but the signature is in place for R1-S03 (startle PMF)
    and R1-S04 (bat teleport) which consume RNG.

    Adjacency check uses the named cave's adjacency table. If `target_room`
    is not adjacent to `world.player_room`, the engine emits
    `MoveAttempted(accepted=False)` and the world is otherwise unchanged
    (player remains in place; turn counter does NOT advance — Yob 1973
    re-prompt semantics). If adjacent, the engine emits
    `MoveAttempted(accepted=True)` followed by `MoveResolved(player_room=target_room)`,
    and the world's `player_room` updates + `turn` advances.

    R1-S01 does NOT resolve the case "player walked into a wumpus / pit / bat
    room" beyond leaving the player there alive. Hazard resolution lands at
    R1-S03 / R1-S04.
    """
    # rng is part of the contract surface (later slices use it); silence the
    # unused warning explicitly so SC1 stays grep-clean of speculative random calls.
    del rng

    if target_room not in _adjacent_rooms_for_cave(cave, world.player_room):
        rejected_event = MoveAttempted(
            schema_version=SCHEMA_VERSION,
            turn=world.turn,
            surface_variant=_R0_SURFACE_VARIANT,
            internal_state_hash=internal_state_hash(world),
            rng_cursor=rng_cursor,
            target_room=target_room,
            accepted=False,
        )
        return world, [rejected_event]

    # Accepted move: advance turn, relocate player, emit attempt + resolved.
    next_world = World(
        player_room=target_room,
        wumpus_rooms=world.wumpus_rooms,
        pit_rooms=world.pit_rooms,
        bat_rooms=world.bat_rooms,
        arrows=world.arrows,
        turn=world.turn + 1,
        alive=world.alive,
        pending_prompt=world.pending_prompt,
        pending_arrow_path=world.pending_arrow_path,
    )
    post_hash = internal_state_hash(next_world)
    attempted = MoveAttempted(
        schema_version=SCHEMA_VERSION,
        turn=next_world.turn,
        surface_variant=_R0_SURFACE_VARIANT,
        internal_state_hash=post_hash,
        rng_cursor=rng_cursor,
        target_room=target_room,
        accepted=True,
    )
    resolved = MoveResolved(
        schema_version=SCHEMA_VERSION,
        turn=next_world.turn,
        surface_variant=_R0_SURFACE_VARIANT,
        internal_state_hash=post_hash,
        rng_cursor=rng_cursor,
        player_room=target_room,
    )
    return next_world, [attempted, resolved]
