"""R0 toy-cave fixture — explicitly NOT the canonical dodecahedron.

A 3-room linear cave used SOLELY for the R0 walking skeleton. R1-S01 ships
the real 20-room dodecahedron topology in `wumpus.engine.cave_gen`. This
module is intentionally named with an `_r0_` prefix so the codebase shows
its toy-substrate intent at the import site, and so it can be deleted /
quarantined when R1 lands without grep-finding the canonical engine paths.

Layout:
    rooms = {1, 2, 3}
    adjacency:  1 <-> 2 <-> 3   (linear, NOT cyclic; room 1 and 3 are leaves)
    player_start = 1
    wumpus_start = 3            (no other hazards at R0)
    arrows = 0                   (shoot lands at R1-S05; R0 cannot shoot)

Per SC1 the toy cave doesn't actually consume RNG — its layout is fixed by
construction. R0 still threads `random.Random` through `Game.__init__` so the
abstraction is in place for R1's seeded cave-gen.
"""

from __future__ import annotations

from typing import Final

from wumpus.types import World

# Adjacency as a frozen tuple-of-tuples; SC7-compliant module-level constant.
TOY_ADJACENCY: Final[tuple[tuple[int, ...], ...]] = (
    (),  # placeholder for room 0 (unused; Yob rooms are 1-indexed)
    (2,),  # room 1 -> room 2
    (1, 3),  # room 2 -> rooms 1, 3
    (2,),  # room 3 -> room 2
)

TOY_PLAYER_START: Final[int] = 1
TOY_WUMPUS_START: Final[int] = 3


def initial_world() -> World:
    """Construct the R0 toy-cave initial World.

    Deterministic by construction; no RNG required at R0. The function exists
    so the Game constructor has the same "build initial World" shape it will
    have at R1 (where `generate_initial_world(rng, variant)` actually uses
    the RNG for FNB rejection-loop layout).
    """
    return World(
        player_room=TOY_PLAYER_START,
        wumpus_rooms=(TOY_WUMPUS_START,),
        pit_rooms=(),
        bat_rooms=(),
        arrows=0,
        turn=0,
        alive=True,
        pending_prompt=None,
        pending_arrow_path=(),
    )


def adjacent_rooms(room: int) -> tuple[int, ...]:
    """Return the rooms adjacent to `room` in the toy cave.

    Raises IndexError if `room` is outside {1, 2, 3} — callers validate first.
    """
    return TOY_ADJACENCY[room]
