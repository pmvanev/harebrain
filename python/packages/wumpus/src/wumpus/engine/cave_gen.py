"""Seeded cave generation — Yob's FNB rejection-loop entity placement.

Per Yob's BASIC source (subroutine `FNB`), entity placement is a rejection
loop: roll a room in 1..20; if it collides with any prior placement, re-roll.
The placement order is fixed:

    1. wumpus
    2. pit #1
    3. pit #2
    4. bat #1
    5. bat #2
    6. player start

This is the *only* RNG-consuming step in `Game.__init__` at R1-S01. Future
slices (R1-S03 startle, R1-S04 bat teleport) consume additional RNG inside
`step()`, but those are tied to the action flow — not constructor state.

The function consumes RNG via `random.Random.randrange(20) + 1` to match
Yob's 1-indexed room space. Determinism follows from the contract that
the caller passes a freshly-seeded `random.Random(seed)` instance.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class InitialLayout:
    """The output of seeded cave generation — distinct room assignments for
    the wumpus, the two pits, the two bats, and the player start.

    Frozen so callers (e.g. `Game.__init__`) cannot mutate after construction.
    Tuples are used for pit / bat collections to match the Tier A1 `World`
    field shapes (`pit_rooms: tuple[int, ...]`).
    """

    wumpus_rooms: tuple[int, ...]
    pit_rooms: tuple[int, ...]
    bat_rooms: tuple[int, ...]
    player_start: int


def generate_initial_layout(rng: random.Random) -> InitialLayout:
    """Roll the canonical Yob FNB rejection-loop layout from `rng`.

    Consumes RNG in a fixed order: wumpus, pit, pit, bat, bat, player. Each
    roll uses `rng.randrange(20) + 1` to land in the 1..20 room space; on
    collision with any prior placement, the loop re-rolls.

    The single-wumpus / two-pits / two-bats / single-player counts are
    pinned by Yob (room counts are not parametric until R4-S01's
    VariantConfig). The `wumpus_rooms` tuple wraps the single wumpus to
    match the Tier A1 World plural-shaped field (forward-compat with
    multi-wumpus variants).
    """
    placed: set[int] = set()

    wumpus = _roll_distinct(rng, placed)
    placed.add(wumpus)

    pit_a = _roll_distinct(rng, placed)
    placed.add(pit_a)
    pit_b = _roll_distinct(rng, placed)
    placed.add(pit_b)

    bat_a = _roll_distinct(rng, placed)
    placed.add(bat_a)
    bat_b = _roll_distinct(rng, placed)
    placed.add(bat_b)

    player_start = _roll_distinct(rng, placed)

    return InitialLayout(
        wumpus_rooms=(wumpus,),
        pit_rooms=(pit_a, pit_b),
        bat_rooms=(bat_a, bat_b),
        player_start=player_start,
    )


def _roll_distinct(rng: random.Random, already_placed: set[int]) -> int:
    """Roll `rng.randrange(20) + 1` until the result is not in `already_placed`.

    This is Yob's `FNB` rejection loop: the BASIC source uses a `GOTO`-based
    loop that re-rolls on collision; we use a `while` loop with the same
    effect. The expected number of re-rolls is bounded (collisions are rare
    with 6 placements in 20 rooms — birthday-paradox-style analysis gives
    ~1 re-roll on average), so a naive loop is fine.
    """
    while True:
        room = rng.randrange(20) + 1
        if room not in already_placed:
            return room


__all__ = ["InitialLayout", "generate_initial_layout"]
