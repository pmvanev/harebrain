"""R1 Yob-fidelity acceptance step definitions.

Each R1 slice appends its step definitions to this file. R1-S01 ships the
first batch (dodecahedron + cave gen from seed); subsequent R1 slices append.

Per pytest-bdd convention:
  - `scenarios(...)` at module top-level binds the .feature scenarios to this module
  - Step functions decorated with @given / @when / @then implement each step
  - Lazy imports of production modules (wumpus.constants, wumpus.engine.cave_gen)
    let DELIVER's outside-in red state show up as ImportError before the slice lands.
"""

from __future__ import annotations

import random
from typing import Any

from hypothesis import given as hyp_given
from hypothesis import settings, strategies as st
from pytest_bdd import given, scenarios, then, when

# Bind the .feature file. Path is relative to this step-defs file's parent.
scenarios("../features/R1_yob_fidelity.feature")


# ---------------------------------------------------------------------------
# R1-S01 — Scenario 1: Layout is determined by seed
# ---------------------------------------------------------------------------


@given("seed = 42", target_fixture="r1s01_seed")
def _r1s01_seed() -> int:
    return 42


@when(
    "Game(seed=42) is constructed twice in separate Python processes",
    target_fixture="r1s01_paired_layouts",
)
def _r1s01_paired_layouts(r1s01_seed: int) -> dict[str, Any]:
    """Per the slice's note: 'separate processes' in this acceptance test
    means two independent Game instances in the same test. The cross-process
    determinism claim is exercised by the K-2 CI matrix (DEVOPS); structural
    determinism is what this scenario asserts.
    """
    from wumpus import Game

    game_a = Game(seed=r1s01_seed)
    game_b = Game(seed=r1s01_seed)
    return {
        "world_a": game_a.world_state(),
        "world_b": game_b.world_state(),
    }


@then(
    "both constructions produce identical _initial_layout "
    "(wumpus room, pit rooms, bat rooms, player start)"
)
def _r1s01_layouts_equal(r1s01_paired_layouts: dict[str, Any]) -> None:
    world_a = r1s01_paired_layouts["world_a"]
    world_b = r1s01_paired_layouts["world_b"]
    assert world_a.wumpus_rooms == world_b.wumpus_rooms, (
        "Paired Game(seed=42) instances produced different wumpus rooms. "
        "SC1 (determinism) violated."
    )
    assert world_a.pit_rooms == world_b.pit_rooms, (
        "Paired Game(seed=42) instances produced different pit rooms."
    )
    assert world_a.bat_rooms == world_b.bat_rooms, (
        "Paired Game(seed=42) instances produced different bat rooms."
    )
    assert world_a.player_room == world_b.player_room, (
        "Paired Game(seed=42) instances produced different player starts."
    )


# ---------------------------------------------------------------------------
# R1-S01 — Scenario 2: All entity rooms are distinct
# ---------------------------------------------------------------------------


@given("Game(seed=k) for any integer k", target_fixture="r1s01_distinct_property_holds")
def _r1s01_distinct_property() -> bool:
    """Use Hypothesis to assert the property holds across many seeds. We run
    the property check eagerly inside the Given step so the Then step is a
    pure assertion (pytest-bdd doesn't natively wrap @given properties).

    Default hypothesis settings give ~100 examples which the slice brief
    deems sufficient.
    """
    from wumpus import Game

    @hyp_given(seed=st.integers())
    @settings(max_examples=100, deadline=None)
    def _all_distinct(seed: int) -> None:
        world = Game(seed=seed).world_state()
        rooms = (
            world.player_room,
            *world.wumpus_rooms,
            *world.pit_rooms,
            *world.bat_rooms,
        )
        # Yob's FNB rejection loop guarantees: wumpus(1) + pits(2) + bats(2)
        # + player(1) = 6 entities in 6 distinct rooms.
        assert len(rooms) == 6, (
            f"seed={seed}: layout has {len(rooms)} entity slots; expected 6 "
            f"(1 wumpus + 2 pits + 2 bats + 1 player)."
        )
        assert len(set(rooms)) == 6, (
            f"seed={seed}: entity rooms not distinct. "
            f"player={world.player_room}, wumpus={world.wumpus_rooms}, "
            f"pits={world.pit_rooms}, bats={world.bat_rooms}"
        )

    _all_distinct()
    return True


@then(
    "the wumpus room, both pit rooms, both bat rooms, and the player start "
    "are all distinct rooms"
)
def _r1s01_distinct_then(r1s01_distinct_property_holds: bool) -> None:
    assert r1s01_distinct_property_holds, (
        "The distinct-entity-rooms property failed under hypothesis exploration."
    )


# ---------------------------------------------------------------------------
# R1-S01 — Scenario 3: Adjacency is the audited 20x3 dodecahedron
# ---------------------------------------------------------------------------


_AUDITED_DODECAHEDRON: dict[int, frozenset[int]] = {
    1: frozenset({2, 5, 8}),
    2: frozenset({1, 3, 10}),
    3: frozenset({2, 4, 12}),
    4: frozenset({3, 5, 14}),
    5: frozenset({1, 4, 6}),
    6: frozenset({5, 7, 15}),
    7: frozenset({6, 8, 17}),
    8: frozenset({1, 7, 9}),
    9: frozenset({8, 10, 18}),
    10: frozenset({2, 9, 11}),
    11: frozenset({10, 12, 19}),
    12: frozenset({3, 11, 13}),
    13: frozenset({12, 14, 20}),
    14: frozenset({4, 13, 15}),
    15: frozenset({6, 14, 16}),
    16: frozenset({15, 17, 20}),
    17: frozenset({7, 16, 18}),
    18: frozenset({9, 17, 19}),
    19: frozenset({11, 18, 20}),
    20: frozenset({13, 16, 19}),
}


@given(
    "the wumpus.constants.DODECAHEDRON table",
    target_fixture="r1s01_dodecahedron_module_table",
)
def _r1s01_dodecahedron_module_table() -> Any:
    from wumpus.constants import DODECAHEDRON

    return DODECAHEDRON


@then(
    "it matches the 20x3 table in the archived shared-artifacts-registry "
    "(rooms 1-20 with their three tunnels each)"
)
def _r1s01_dodecahedron_matches(r1s01_dodecahedron_module_table: Any) -> None:
    """Assert the constant equals the archived audit table room-by-room.

    The constant's exact Python shape (tuple vs dict) is the implementer's
    choice per ADR-007 (stdlib types). This step normalizes both sides to
    `dict[int, frozenset[int]]` for comparison.
    """
    actual = _normalize_to_room_map(r1s01_dodecahedron_module_table)
    assert actual == _AUDITED_DODECAHEDRON, (
        "wumpus.constants.DODECAHEDRON does not match the audited 20x3 table. "
        "Yob-fidelity break — see archived shared-artifacts-registry."
    )


def _normalize_to_room_map(table: Any) -> dict[int, frozenset[int]]:
    """Accept either a dict[int, frozenset[int]] or a 21-tuple indexed 1-20
    (slot 0 unused; rooms are 1-indexed)."""
    if isinstance(table, dict):
        return {int(room): frozenset(neighbors) for room, neighbors in table.items()}
    # Treat as a 1-indexed sequence; ignore slot 0 if present.
    rooms = list(range(1, 21))
    if len(table) == 21:
        return {room: frozenset(table[room]) for room in rooms}
    if len(table) == 20:
        return {room: frozenset(table[room - 1]) for room in rooms}
    raise AssertionError(
        f"DODECAHEDRON constant has unexpected length {len(table)}; expected 20 or 21."
    )


# ---------------------------------------------------------------------------
# R1-S01 — Scenario 4: random.Random stability regression
# ---------------------------------------------------------------------------


# Python's stdlib `random.Random(42).randrange(20)` is deterministic across
# Python 3.x; the slice brief asks us to pin whatever Python 3.11+ produces.
# Empirically verified at COMMIT time on Python 3.12.13.
_PINNED_RANDRANGE_42 = 3


@given(
    "a Python 3.11+ interpreter",
    target_fixture="r1s01_python_interpreter",
)
def _r1s01_python_interpreter() -> None:
    import sys

    assert sys.version_info >= (3, 11), (
        f"Python 3.11+ required; got {sys.version_info}."
    )


@when(
    "random.Random(42).randrange(20) is invoked",
    target_fixture="r1s01_randrange_result",
)
def _r1s01_randrange_result(r1s01_python_interpreter: None) -> int:
    return random.Random(42).randrange(20)


@then("the result equals a pinned constant (catches Python-stdlib drift at CI time)")
def _r1s01_randrange_pinned(r1s01_randrange_result: int) -> None:
    assert r1s01_randrange_result == _PINNED_RANDRANGE_42, (
        f"random.Random(42).randrange(20) returned {r1s01_randrange_result}; "
        f"expected {_PINNED_RANDRANGE_42}. Python stdlib RNG algorithm changed. "
        f"This is a CI-time canary for Yob-fidelity replay determinism (SC1, K-2)."
    )
