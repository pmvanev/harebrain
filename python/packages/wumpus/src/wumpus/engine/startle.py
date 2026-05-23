"""Wumpus startle — Yob FNC(0) distribution.

Pure function over `World` per ADR-001 (hybrid paradigm). The engine calls
`move_wumpus_startle` after `HazardTriggered(WUMPUS)` fires (R1-S03's bump
branch); later slices (R1-S06 arrow-miss) call the same function from the
arrow-resolution path.

Yob's BASIC source defines the startle PMF in lines 3370-3440 via the FN
declaration `DEF FNC(X)=INT(4*RND(1))+1` — uniform `randint(1, 4)`. The
outcome map:
    K = 1 → wumpus moves to S(L(2), 1) (first adjacent of wumpus's room)
    K = 2 → wumpus moves to S(L(2), 2) (second adjacent)
    K = 3 → wumpus moves to S(L(2), 3) (third adjacent)
    K = 4 → wumpus stays

The "adjacent" ordering matches the rest of the engine's adjacency surface
(`sorted(DODECAHEDRON[room])` — see `transitions._adjacent_rooms_for_cave`).
The wumpus is single-occupant in Yob v1 (`world.wumpus_rooms` length 1);
multi-wumpus variants belong to a future variant config and would land
their own startle helper.
"""

from __future__ import annotations

import random

from wumpus.constants import DODECAHEDRON
from wumpus.engine.hash import internal_state_hash
from wumpus.events import SCHEMA_VERSION, WumpusStartled
from wumpus.types import World

# Surface placeholder per SC8 — no Yob strings in engine code.
_R1S03_SURFACE_VARIANT: str = "<placeholder>"


def move_wumpus_startle(
    world: World, rng: random.Random
) -> tuple[World, WumpusStartled]:
    """Compute the FNC(0) startle outcome for the wumpus.

    Consumes exactly one `rng.randint(1, 4)` draw. K ∈ {1, 2, 3} moves the
    wumpus to `sorted(DODECAHEDRON[wumpus_room])[K-1]`; K = 4 leaves the
    wumpus in place.

    Returns the new World value (with the wumpus relocated if K ∈ 1..3) and
    a `WumpusStartled` event recording `from_room`, `to_room`, and the
    `ate_player` flag (True iff the destination room equals the player's
    current room — used by the caller to decide whether to emit
    `GameEnded(outcome=eaten_after_bump)`).
    """
    from_room = world.wumpus_rooms[0]
    draw = rng.randint(1, 4)

    if draw == 4:
        to_room = from_room
        new_wumpus_rooms = world.wumpus_rooms
    else:
        sorted_adjacent = sorted(DODECAHEDRON[from_room])
        to_room = sorted_adjacent[draw - 1]
        # World keeps a tuple to leave room for future multi-wumpus variants;
        # at R1-S03 Yob v1 there is exactly one wumpus.
        new_wumpus_rooms = (to_room,) + world.wumpus_rooms[1:]

    new_world = World(
        player_room=world.player_room,
        wumpus_rooms=new_wumpus_rooms,
        pit_rooms=world.pit_rooms,
        bat_rooms=world.bat_rooms,
        arrows=world.arrows,
        turn=world.turn,
        alive=world.alive,
        pending_prompt=world.pending_prompt,
        pending_arrow_path=world.pending_arrow_path,
    )

    event = WumpusStartled(
        schema_version=SCHEMA_VERSION,
        turn=new_world.turn,
        surface_variant=_R1S03_SURFACE_VARIANT,
        internal_state_hash=internal_state_hash(new_world),
        rng_cursor="",
        from_room=from_room,
        to_room=to_room,
        ate_player=(to_room == new_world.player_room),
    )
    return new_world, event


__all__ = ["move_wumpus_startle"]
