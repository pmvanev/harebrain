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


# ---------------------------------------------------------------------------
# R1-S02 — Sense emit on entry (Yob L-array order)
# ---------------------------------------------------------------------------
#
# Strategy: use the `Game._from_world` test hatch to construct a Game whose
# initial layout exactly matches each scenario's "player adjacent to ..."
# precondition, then drive the player into the target room via `step("move N")`
# and inspect the post-move event stream on a subscribed InMemorySink.
#
# Room 1 has dodecahedron neighbors {2, 5, 8}. We place the player one
# neighbor away (e.g. room 8), park hazards on the OTHER neighbors of room 1,
# and move the player into room 1. The events emitted on that move's
# resolution are the ones the scenario asserts about.
#
# Adjacent helpers (read from the audited DODECAHEDRON):
#   room 1 -> {2, 5, 8}
#   room 2 -> {1, 3, 10}
# Layouts chosen to make every hazard non-adjacent to the no-hazard scenario's
# destination room (room 2, neighbors {1, 3, 10}).


def _build_world_for_r1s02(
    *,
    player_room: int,
    wumpus_rooms: tuple[int, ...],
    pit_rooms: tuple[int, ...],
    bat_rooms: tuple[int, ...],
) -> Any:
    """Helper that constructs a Tier-A1 World pinned to the given hazard layout
    for use with `Game._from_world`. All entity slots must be distinct and
    within rooms 1..20 (Yob FNB invariant)."""
    from wumpus.types import World

    return World(
        player_room=player_room,
        wumpus_rooms=wumpus_rooms,
        pit_rooms=pit_rooms,
        bat_rooms=bat_rooms,
        arrows=5,  # Yob default; not used by R1-S02
        turn=0,
        alive=True,
        pending_prompt=None,
        pending_arrow_path=(),
    )


def _drive_into_target_and_capture(
    *,
    player_start: int,
    target_room: int,
    wumpus_rooms: tuple[int, ...],
    pit_rooms: tuple[int, ...],
    bat_rooms: tuple[int, ...],
) -> list[Any]:
    """Construct a Game pinned to the given layout, attach a fresh InMemorySink,
    step the player into the target room, and return the events emitted
    AFTER the construction-time GameStarted event."""
    from wumpus import Game
    from wumpus.sinks import InMemorySink

    world = _build_world_for_r1s02(
        player_room=player_start,
        wumpus_rooms=wumpus_rooms,
        pit_rooms=pit_rooms,
        bat_rooms=bat_rooms,
    )
    game = Game._from_world(world, seed=0)
    sink = InMemorySink()
    game.subscribe(sink)
    # Snapshot how many events the GameStarted replay drops into the sink so
    # the assertions below address ONLY the post-move event stream.
    pre_move_count = len(sink.events)
    game.step(f"move {target_room}")
    return sink.events[pre_move_count:]


# ---------------------------------------------------------------------------
# R1-S02 — Scenario 1: Senses fire in L-array order
# ---------------------------------------------------------------------------


@given(
    "the player enters a room adjacent to the wumpus AND adjacent to a pit",
    target_fixture="r1s02_post_move_events_mixed",
)
def _r1s02_enter_room_adjacent_wumpus_and_pit() -> list[Any]:
    # Target room 1 has neighbors {2, 5, 8}. Wumpus at 2, pit at 5, second pit
    # parked away (room 11 — not adjacent to room 1). Bats parked at 14/17.
    # Player starts at 8 (neighbor of 1) and moves to 1.
    return _drive_into_target_and_capture(
        player_start=8,
        target_room=1,
        wumpus_rooms=(2,),
        pit_rooms=(5, 11),
        bat_rooms=(14, 17),
    )


@then("a SenseEmitted(WUMPUS_SMELL) event fires")
def _r1s02_wumpus_smell_fired_first(
    r1s02_post_move_events_mixed: list[Any],
) -> None:
    from wumpus.events import SenseEmitted

    sense_events = [
        e for e in r1s02_post_move_events_mixed if isinstance(e, SenseEmitted)
    ]
    assert sense_events, (
        "No SenseEmitted event was emitted when player entered a room adjacent "
        "to the wumpus and a pit. R1-S02 contract violated."
    )
    assert sense_events[0].kind == "WUMPUS_SMELL", (
        f"First SenseEmitted.kind was {sense_events[0].kind!r}; "
        f"expected 'WUMPUS_SMELL' per Yob L-array order."
    )


@then("then a SenseEmitted(PIT_DRAFT) event fires")
def _r1s02_pit_draft_fired_second(
    r1s02_post_move_events_mixed: list[Any],
) -> None:
    from wumpus.events import SenseEmitted

    sense_events = [
        e for e in r1s02_post_move_events_mixed if isinstance(e, SenseEmitted)
    ]
    assert len(sense_events) >= 2, (
        f"Expected at least two SenseEmitted events; got {len(sense_events)}."
    )
    assert sense_events[1].kind == "PIT_DRAFT", (
        f"Second SenseEmitted.kind was {sense_events[1].kind!r}; "
        f"expected 'PIT_DRAFT' per Yob L-array order."
    )


@then("then a LocationReported event fires")
def _r1s02_location_reported_fires_after_senses(
    r1s02_post_move_events_mixed: list[Any],
) -> None:
    from wumpus.events import LocationReported, SenseEmitted

    # LocationReported MUST appear AFTER the last SenseEmitted in the event stream.
    location_indices = [
        i
        for i, e in enumerate(r1s02_post_move_events_mixed)
        if isinstance(e, LocationReported)
    ]
    sense_indices = [
        i
        for i, e in enumerate(r1s02_post_move_events_mixed)
        if isinstance(e, SenseEmitted)
    ]
    assert len(location_indices) == 1, (
        f"Expected exactly one LocationReported event after move; "
        f"got {len(location_indices)}."
    )
    if sense_indices:
        assert location_indices[0] > sense_indices[-1], (
            "LocationReported fired before/between SenseEmitted events. "
            "Yob's order (senses, then location) violated."
        )


# ---------------------------------------------------------------------------
# R1-S02 — Scenario 2: Repeated same-kind hazards repeat the sense
# ---------------------------------------------------------------------------


@given(
    "the player enters a room adjacent to two pits",
    target_fixture="r1s02_post_move_events_two_pits",
)
def _r1s02_enter_room_adjacent_two_pits() -> list[Any]:
    # Target room 1 (neighbors {2, 5, 8}). Both pits adjacent: pit_a=2, pit_b=5.
    # Wumpus parked at non-adjacent room 11; bats parked at 14/17.
    # Player starts at 8 and moves to 1.
    return _drive_into_target_and_capture(
        player_start=8,
        target_room=1,
        wumpus_rooms=(11,),
        pit_rooms=(2, 5),
        bat_rooms=(14, 17),
    )


@then("two SenseEmitted(PIT_DRAFT) events fire (one per adjacency match)")
def _r1s02_two_pit_drafts_emit(
    r1s02_post_move_events_two_pits: list[Any],
) -> None:
    from wumpus.events import SenseEmitted

    pit_drafts = [
        e
        for e in r1s02_post_move_events_two_pits
        if isinstance(e, SenseEmitted) and e.kind == "PIT_DRAFT"
    ]
    assert len(pit_drafts) == 2, (
        f"Expected 2 SenseEmitted(PIT_DRAFT) events for two adjacent pits; "
        f"got {len(pit_drafts)}. R1-S02 repetition contract violated."
    )


# ---------------------------------------------------------------------------
# R1-S02 — Scenario 3: No sense fires for a non-adjacent hazard
# ---------------------------------------------------------------------------


@given(
    "the player enters a room with no adjacent hazards",
    target_fixture="r1s02_post_move_events_no_hazards",
)
def _r1s02_enter_room_no_adjacent_hazards() -> list[Any]:
    # Target room 2 has neighbors {1, 3, 10}. Park every hazard far from there:
    # wumpus at 20 (neighbors {13, 16, 19}); pits at 15 and 6; bats at 11 and 12.
    # None of those are in {1, 3, 10}, so room 2 has zero adjacent hazards.
    # Player starts at room 1 (neighbor of 2) and moves to room 2.
    return _drive_into_target_and_capture(
        player_start=1,
        target_room=2,
        wumpus_rooms=(20,),
        pit_rooms=(15, 6),
        bat_rooms=(11, 12),
    )


@then("no SenseEmitted event fires before LocationReported")
def _r1s02_no_sense_before_location(
    r1s02_post_move_events_no_hazards: list[Any],
) -> None:
    from wumpus.events import LocationReported, SenseEmitted

    location_indices = [
        i
        for i, e in enumerate(r1s02_post_move_events_no_hazards)
        if isinstance(e, LocationReported)
    ]
    assert len(location_indices) == 1, (
        f"Expected exactly one LocationReported event; got {len(location_indices)}."
    )
    location_index = location_indices[0]
    senses_before_location = [
        e
        for e in r1s02_post_move_events_no_hazards[:location_index]
        if isinstance(e, SenseEmitted)
    ]
    assert senses_before_location == [], (
        f"Expected no SenseEmitted events before LocationReported when entering "
        f"a room with no adjacent hazards; got {senses_before_location}."
    )
