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
from wumpus.types import VariantConfig


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


# ---------------------------------------------------------------------------
# R4-S01 — VariantConfig parameterization of cave generation
# ---------------------------------------------------------------------------


@given(
    seed=st.integers(),
    wumpus_count=st.integers(min_value=1, max_value=4),
    pit_count=st.integers(min_value=0, max_value=4),
    bat_count=st.integers(min_value=0, max_value=4),
)
@settings(max_examples=100, deadline=None)
def test_layout_counts_follow_variant(
    seed: int, wumpus_count: int, pit_count: int, bat_count: int
) -> None:
    """The placed entity-collection sizes equal the VariantConfig counts, and
    every placed room is distinct (the FNB rejection invariant). This is the
    parameterization property: tuple LENGTHS track the config; the field SET
    never changes (goals.md Goal 2)."""
    variant = VariantConfig(
        room_count=20,
        wumpus_count=wumpus_count,
        pit_count=pit_count,
        bat_count=bat_count,
    )
    layout = generate_initial_layout(random.Random(seed), variant)

    assert len(layout.wumpus_rooms) == wumpus_count
    assert len(layout.pit_rooms) == pit_count
    assert len(layout.bat_rooms) == bat_count

    placed = (
        layout.player_start,
        *layout.wumpus_rooms,
        *layout.pit_rooms,
        *layout.bat_rooms,
    )
    assert len(set(placed)) == len(placed), (
        f"seed={seed}: FNB rejection loop placed colliding rooms: {placed!r}."
    )
    for room in placed:
        assert 1 <= room <= variant.room_count


@pytest.mark.parametrize("seed", [0, 1, 42, 1337, 2**31 - 1])
def test_default_variant_layout_matches_no_arg(seed: int) -> None:
    """`VariantConfig()` (Yob defaults) reproduces the pre-R4-S01 single-arg
    layout byte-identically — the same RNG-consumption order, same rooms.
    This pins the Yob-fidelity claim: the default variant is a no-op over the
    original FNB placement."""
    with_default = generate_initial_layout(random.Random(seed), VariantConfig())
    no_arg = generate_initial_layout(random.Random(seed))
    assert with_default == no_arg, (
        f"seed={seed}: default-VariantConfig layout diverged from the no-arg "
        f"layout. The Yob default must be byte-identical."
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"room_count": 3},
        {"arrow_count": 0},
        {"wumpus_count": -1},
        {"pit_count": -1},
        {"wumpus_move_prob": 1.5},
        {"wumpus_move_prob": -0.1},
        {"topology": "complete"},
        {"room_count": 4, "wumpus_count": 2, "pit_count": 1, "bat_count": 1},
    ],
)
def test_variant_config_rejects_invalid(overrides: dict[str, object]) -> None:
    """VariantConfig.__post_init__ rejects out-of-range / unsupported configs
    with a ValueError. Input variations of the SAME behavior (validation) are
    parametrized per Mandate 5. The last case is the occupants-fit invariant
    (2 wumpus + 1 pit + 1 bat + 1 player = 5 > room_count=4)."""
    with pytest.raises(ValueError):
        VariantConfig(**overrides)  # type: ignore[arg-type]
