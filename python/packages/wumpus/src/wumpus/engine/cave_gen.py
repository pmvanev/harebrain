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

The function consumes RNG via `random.Random.randrange(room_count) + 1` to
match Yob's 1-indexed room space. Determinism follows from the contract that
the caller passes a freshly-seeded `random.Random(seed)` instance.

R4-S01 parameterizes placement counts by `VariantConfig`: `wumpus_count`
wumpuses, `pit_count` pits, `bat_count` bats, then the player start — all via
the same FNB rejection loop. The placement ORDER is preserved (wumpuses,
pits, bats, player) so a `VariantConfig()` (Yob defaults) layout is
byte-identical to the pre-R4-S01 single-arg layout for the same seed. The
counts size the corresponding tuples; they never add World fields (goals.md
§ Goal 2 — "two wumpuses means a list of length two, not a new field").
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from wumpus.types import VariantConfig


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


def generate_initial_layout(
    rng: random.Random, variant: VariantConfig | None = None
) -> InitialLayout:
    """Roll the FNB rejection-loop layout from `rng`, sized by `variant`.

    Consumes RNG in a fixed order: each wumpus, each pit, each bat, then the
    player start. Each roll uses `rng.randrange(variant.room_count) + 1` to
    land in the 1..room_count space; on collision with any prior placement,
    the loop re-rolls.

    `variant=None` defaults to `VariantConfig()` (Yob 1973): one wumpus, two
    pits, two bats, 20 rooms — byte-identical RNG consumption to the
    pre-R4-S01 single-arg path. The counts size the returned tuples; they
    never add fields (goals.md § Goal 2). The `wumpus_rooms` tuple has length
    `variant.wumpus_count` (was always 1 at Yob), so `wumpus_count=2` yields a
    length-2 tuple, NOT a new field.
    """
    config = variant if variant is not None else VariantConfig()
    placed: set[int] = set()

    wumpus_rooms = _roll_many(rng, placed, config.wumpus_count, config.room_count)
    pit_rooms = _roll_many(rng, placed, config.pit_count, config.room_count)
    bat_rooms = _roll_many(rng, placed, config.bat_count, config.room_count)
    player_start = _roll_distinct(rng, placed, config.room_count)

    return InitialLayout(
        wumpus_rooms=wumpus_rooms,
        pit_rooms=pit_rooms,
        bat_rooms=bat_rooms,
        player_start=player_start,
    )


def _roll_many(
    rng: random.Random, placed: set[int], count: int, room_count: int
) -> tuple[int, ...]:
    """Roll `count` distinct rooms via the FNB rejection loop, registering each
    into `placed` so subsequent rolls (and later collections) stay disjoint."""
    rooms: list[int] = []
    for _ in range(count):
        room = _roll_distinct(rng, placed, room_count)
        placed.add(room)
        rooms.append(room)
    return tuple(rooms)


def _roll_distinct(rng: random.Random, already_placed: set[int], room_count: int) -> int:
    """Roll `rng.randrange(room_count) + 1` until the result is not in
    `already_placed`.

    This is Yob's `FNB` rejection loop: the BASIC source uses a `GOTO`-based
    loop that re-rolls on collision; we use a `while` loop with the same
    effect. The expected number of re-rolls is bounded (the
    `VariantConfig.__post_init__` occupants-fit-in-room_count invariant keeps
    the loop from spinning), so a naive loop is fine.
    """
    while True:
        room = rng.randrange(room_count) + 1
        if room not in already_placed:
            return room


__all__ = ["InitialLayout", "generate_initial_layout"]
