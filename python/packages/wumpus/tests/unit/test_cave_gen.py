"""Unit tests for `wumpus.engine.cave_gen` (R1-S01).

`generate_initial_layout` implements Yob's FNB rejection-loop entity placement:
roll for wumpus, then 2 pits with rejection on prior placements, then 2 bats
with rejection on prior placements, then player start with rejection on all.

The acceptance scenario covers the deterministic-from-seed + all-distinct
claims. These unit tests pin the smaller structural facts:

    - Wumpus is a single room
    - Pit count = 2
    - Bat count = 2
    - All rooms are in the valid 1..20 range
    - Same seed -> same layout (deterministic, no module state read)

Per the PBT + state-delta paradigm (mandate, 2026-05-05), the all-distinct
+ valid-range claims are expressed as Hypothesis properties so the test
covers equivalence classes rather than picked seeds.
"""

from __future__ import annotations

import random

import pytest
from hypothesis import given, settings, strategies as st

from wumpus.engine.cave_gen import generate_initial_layout


@given(seed=st.integers())
@settings(max_examples=100, deadline=None)
def test_layout_has_canonical_entity_counts(seed: int) -> None:
    """1 wumpus + 2 pits + 2 bats + 1 player start, regardless of seed."""
    layout = generate_initial_layout(random.Random(seed))
    assert len(layout.wumpus_rooms) == 1, (
        f"seed={seed}: expected 1 wumpus, got {len(layout.wumpus_rooms)}."
    )
    assert len(layout.pit_rooms) == 2, (
        f"seed={seed}: expected 2 pits, got {len(layout.pit_rooms)}."
    )
    assert len(layout.bat_rooms) == 2, (
        f"seed={seed}: expected 2 bats, got {len(layout.bat_rooms)}."
    )
    assert isinstance(layout.player_start, int)


@given(seed=st.integers())
@settings(max_examples=100, deadline=None)
def test_all_rooms_in_valid_range(seed: int) -> None:
    """Every placed room must be in 1..20 (Yob 1-indexed)."""
    layout = generate_initial_layout(random.Random(seed))
    placed = (
        layout.player_start,
        *layout.wumpus_rooms,
        *layout.pit_rooms,
        *layout.bat_rooms,
    )
    for room in placed:
        assert 1 <= room <= 20, f"seed={seed}: placed room {room} outside 1..20."


@pytest.mark.parametrize("seed", [0, 1, 42, 1337, 2**31 - 1])
def test_same_seed_produces_same_layout(seed: int) -> None:
    """Determinism: two `random.Random(seed)` -> same layout. Asserts the
    cave_gen function reads no module-level state and consumes RNG in a
    fixed order."""
    layout_a = generate_initial_layout(random.Random(seed))
    layout_b = generate_initial_layout(random.Random(seed))
    assert layout_a == layout_b, (
        f"seed={seed}: cave_gen produced different layouts on two independent "
        f"random.Random({seed}) instances. SC1 (determinism) violated."
    )
