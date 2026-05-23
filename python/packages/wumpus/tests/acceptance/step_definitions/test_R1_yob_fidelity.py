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

import pytest
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


# ---------------------------------------------------------------------------
# R1-S03 — Move + wumpus bump + startle
# ---------------------------------------------------------------------------
#
# Strategy: park the wumpus at room 7 and the player one neighbor away (room 8;
# the audited dodecahedron has 7-{6,8,17}). Use `Game._from_world` to pin the
# layout, then monkeypatch `game._random` with a `MockRandom` instance whose
# `randint(1, 4)` return values are scripted by the scenario's Given step.
#
# Per FNC(0) ∈ {1,2,3,4}: K∈{1,2,3} → wumpus moves to sorted_neighbors[K-1];
# K=4 → wumpus stays. Sorted neighbors of room 7 are [6, 8, 17], so:
#   K=1 → wumpus to 6
#   K=2 → wumpus to 8 (the player's new room → eaten)
#   K=3 → wumpus to 17
#   K=4 → wumpus stays at 7 (also the player's new room → eaten)


class _MockRandom:
    """Test helper that scripts `randint(a, b)` return values.

    The engine also calls `getstate()` during `_encode_rng_cursor` after every
    step (ADR-001/SC6: events carry a base64-pickled RNG cursor). We supply a
    stable sentinel so the cursor encoding still round-trips, but downstream
    consumers cannot use it to reconstruct a real RNG. Tests that care about
    the cursor's value rely on `random.Random`, not `_MockRandom`.

    Other RNG methods are intentionally absent — accessing one (e.g. randrange)
    raises AttributeError immediately, catching any engine code that consumes
    RNG more aggressively than the slice scripted for.
    """

    def __init__(self, randint_values: list[int]) -> None:
        self._randint_values: list[int] = list(randint_values)
        self._index: int = 0

    def randint(self, a: int, b: int) -> int:
        if self._index >= len(self._randint_values):
            raise AssertionError(
                f"_MockRandom exhausted: only {len(self._randint_values)} scripted "
                f"values for randint({a}, {b}). The engine consumed RNG more times "
                f"than the test scripted."
            )
        value = self._randint_values[self._index]
        self._index += 1
        if not (a <= value <= b):
            raise AssertionError(
                f"_MockRandom scripted value {value} is outside randint({a}, {b}) range."
            )
        return value

    def getstate(self) -> tuple[Any, ...]:
        """Stable sentinel cursor so the engine's `_encode_rng_cursor` keeps
        working under a scripted RNG. Pickle-safe; the encoded value is opaque."""
        return ("mock_random", self._index)


def _drive_bump_into_wumpus(scripted_randint: list[int]) -> list[Any]:
    """Construct a Game pinned with wumpus@7 + player@8, monkeypatch the
    RNG with a `_MockRandom` returning `scripted_randint`, step the player
    into room 7, and return the events emitted after construction."""
    from wumpus import Game
    from wumpus.sinks import InMemorySink
    from wumpus.types import World

    world = World(
        player_room=8,
        wumpus_rooms=(7,),
        pit_rooms=(11, 14),  # parked away from room 7's neighbors {6, 8, 17}
        bat_rooms=(15, 19),  # parked away from room 7's neighbors {6, 8, 17}
        arrows=5,
        turn=0,
        alive=True,
        pending_prompt=None,
        pending_arrow_path=(),
    )
    game = Game._from_world(world, seed=0)
    # Cast: _MockRandom duck-types the subset of random.Random methods the
    # engine calls during startle (randint only at R1-S03). mypy would flag
    # the assignment under strict; the inner cast keeps the contract honest.
    game._random = _MockRandom(scripted_randint)  # type: ignore[assignment]

    sink = InMemorySink()
    game.subscribe(sink)
    pre_move_count = len(sink.events)
    game.step("move 7")
    return sink.events[pre_move_count:]


# ---------------------------------------------------------------------------
# R1-S03 — Scenario 1: Bumping the wumpus triggers startle to an adjacent room
# ---------------------------------------------------------------------------


@given(
    "the wumpus is in room 7 and the player is in room 8 (adjacent to 7)",
    target_fixture="r1s03_scripted_randint_scenario1",
)
def _r1s03_layout_scenario1() -> list[int]:
    """Scenario 1 stores the scripted randint sequence; the When step uses it
    to drive the bump and capture events."""
    return []


@given("the engine's next startle draw will be 1 (move to first adjacent room)")
def _r1s03_startle_draw_one(
    r1s03_scripted_randint_scenario1: list[int],
) -> None:
    r1s03_scripted_randint_scenario1.append(1)


@when(
    "the player moves to room 7",
    target_fixture="r1s03_post_move_events",
)
def _r1s03_player_moves_to_room_7(request: Any) -> list[Any]:
    """Pull whichever scripted-randint fixture the active scenario populated.

    Scenarios 2 and 3 share the first Given step text ("the wumpus is in room
    7 and the player is in room 8") and therefore share its target_fixture
    name `r1s03_scripted_randint_scenario2`. Scenario 3's second Given builds
    a separate `r1s03_scripted_randint_scenario3` from that shared base. We
    probe scenario3 BEFORE scenario2 so the derived (richer) list wins when
    both exist.
    """
    candidates = (
        "r1s03_scripted_randint_scenario3",
        "r1s03_scripted_randint_scenario2",
        "r1s03_scripted_randint_scenario1",
    )
    for name in candidates:
        try:
            scripted: list[int] = request.getfixturevalue(name)
        except pytest.FixtureLookupError:
            continue
        return _drive_bump_into_wumpus(scripted)
    raise AssertionError(
        "No r1s03_scripted_randint_* fixture was set up by the Given steps; "
        "the active scenario did not run a Given that primes the RNG."
    )


@then("a HazardTriggered(WUMPUS) event fires")
def _r1s03_hazard_triggered_wumpus(
    r1s03_post_move_events: list[Any],
) -> None:
    from wumpus.events import HazardTriggered

    hazard_events = [
        e for e in r1s03_post_move_events if isinstance(e, HazardTriggered)
    ]
    assert hazard_events, (
        f"No HazardTriggered event emitted on wumpus bump. "
        f"Events seen: {[type(e).__name__ for e in r1s03_post_move_events]}"
    )
    assert hazard_events[0].kind == "WUMPUS", (
        f"First HazardTriggered.kind was {hazard_events[0].kind!r}; expected 'WUMPUS'."
    )


@then(
    "a WumpusStartled(from=7, to=<first-adjacent-of-7>, ate_player=False) event fires"
)
def _r1s03_wumpus_startled_to_first_adjacent(
    r1s03_post_move_events: list[Any],
) -> None:
    from wumpus.events import WumpusStartled

    startled_events = [
        e for e in r1s03_post_move_events if isinstance(e, WumpusStartled)
    ]
    assert startled_events, "No WumpusStartled event emitted on wumpus bump."
    event = startled_events[0]
    # Sorted neighbors of room 7 are [6, 8, 17]. K=1 → adjacent[0] = 6.
    assert event.from_room == 7, (
        f"WumpusStartled.from_room was {event.from_room}; expected 7."
    )
    assert event.to_room == 6, (
        f"WumpusStartled.to_room was {event.to_room}; expected 6 "
        f"(first adjacent of 7 in sorted order [6, 8, 17])."
    )
    assert event.ate_player is False, (
        f"WumpusStartled.ate_player was {event.ate_player}; expected False "
        f"(wumpus moved to room 6, player is in room 7)."
    )


@then("the game continues")
def _r1s03_game_continues(
    r1s03_post_move_events: list[Any],
) -> None:
    from wumpus.events import GameEnded

    game_ended = [e for e in r1s03_post_move_events if isinstance(e, GameEnded)]
    assert game_ended == [], (
        f"Expected the game to continue but GameEnded fired: {game_ended!r}."
    )


# ---------------------------------------------------------------------------
# R1-S03 — Scenario 2: Bumping the wumpus and being eaten
# ---------------------------------------------------------------------------


@given(
    "the wumpus is in room 7 and the player is in room 8",
    target_fixture="r1s03_scripted_randint_scenario2",
)
def _r1s03_layout_scenario2() -> list[int]:
    return []


@given(
    "the engine's next startle draw will leave the wumpus on room 8 (the player's room)"
)
def _r1s03_startle_draw_lands_on_player(
    r1s03_scripted_randint_scenario2: list[int],
) -> None:
    """Brief reads as "the next startle draw lands the wumpus on the player's
    room". After the move resolves, the player occupies room 7 (formerly the
    wumpus's room — the bump). For the startled wumpus to land on the player,
    it must stay at room 7 (K=4 in the FNC(0) distribution). The brief's
    parenthetical "(the player's room)" refers to the player's room AFTER the
    move (room 7), not before (room 8); the scenario's `to_room` assertion is
    omitted on purpose because both K=4 (stay at 7) and any K that lands the
    wumpus on the player's new room satisfy the eat-bump contract.
    """
    r1s03_scripted_randint_scenario2.append(4)


@then("a WumpusStartled(ate_player=True) event fires")
def _r1s03_wumpus_startled_ate_player(
    r1s03_post_move_events: list[Any],
) -> None:
    from wumpus.events import WumpusStartled

    startled_events = [
        e for e in r1s03_post_move_events if isinstance(e, WumpusStartled)
    ]
    assert startled_events, "No WumpusStartled event emitted on wumpus bump."
    assert startled_events[0].ate_player is True, (
        f"WumpusStartled.ate_player was {startled_events[0].ate_player}; "
        f"expected True (wumpus landed on player)."
    )


@then("a GameEnded(outcome=eaten_after_bump) event fires")
def _r1s03_game_ended_eaten(
    r1s03_post_move_events: list[Any],
) -> None:
    from wumpus.events import GameEnded

    ended_events = [e for e in r1s03_post_move_events if isinstance(e, GameEnded)]
    assert ended_events, "No GameEnded event emitted after startled wumpus ate player."
    assert ended_events[0].outcome == "eaten_after_bump", (
        f"GameEnded.outcome was {ended_events[0].outcome!r}; expected 'eaten_after_bump'."
    )
    assert ended_events[0].message_kind == "lose", (
        f"GameEnded.message_kind was {ended_events[0].message_kind!r}; expected 'lose'."
    )


# ---------------------------------------------------------------------------
# R1-S03 — Scenario 3: 25% stay-put rule
# ---------------------------------------------------------------------------


@given(
    "the engine's next startle draw will be 4 (stay)",
    target_fixture="r1s03_scripted_randint_scenario3",
)
def _r1s03_startle_draw_four(
    request: Any,
) -> list[int]:
    """Scenario 3's Given chain: the first Given (wumpus@7, player@8) is shared
    with scenario 2 — pytest-bdd treats identical Given text as the same step
    function. The second Given (the K=4 instruction) is unique to this scenario
    and is the one that target_fixtures the scripted list.

    Because scenarios 2 and 3 share the first Given step, both populate the
    `r1s03_scripted_randint_scenario2` fixture name. To disambiguate at the
    When step, we copy whatever the scenario-2 fixture holds into a fresh
    scenario-3 list, then append K=4.
    """
    # Pull the shared Given's list and copy + extend it locally.
    try:
        shared = request.getfixturevalue("r1s03_scripted_randint_scenario2")
    except pytest.FixtureLookupError:
        shared = []
    fresh: list[int] = list(shared) + [4]
    return fresh


@then(
    "WumpusStartled(from=7, to=7, ate_player=True) fires (the wumpus stays in 7, which is now the player's room)"
)
def _r1s03_wumpus_stays_eats_player(
    r1s03_post_move_events: list[Any],
) -> None:
    from wumpus.events import GameEnded, WumpusStartled

    startled_events = [
        e for e in r1s03_post_move_events if isinstance(e, WumpusStartled)
    ]
    assert startled_events, "No WumpusStartled event emitted on wumpus bump."
    event = startled_events[0]
    assert event.from_room == 7, (
        f"WumpusStartled.from_room was {event.from_room}; expected 7."
    )
    assert event.to_room == 7, (
        f"WumpusStartled.to_room was {event.to_room}; expected 7 (K=4 → stay-put)."
    )
    assert event.ate_player is True, (
        f"WumpusStartled.ate_player was {event.ate_player}; expected True "
        f"(wumpus stayed at 7 = player's new room)."
    )
    # GameEnded should also fire — see brief's note: "the implementation should
    # still emit it — add the assertion to be thorough."
    ended_events = [e for e in r1s03_post_move_events if isinstance(e, GameEnded)]
    assert ended_events, (
        "GameEnded(eaten_after_bump) should also fire after a stay-put startle "
        "that lands the wumpus on the player's room."
    )
    assert ended_events[0].outcome == "eaten_after_bump", (
        f"GameEnded.outcome was {ended_events[0].outcome!r}; expected 'eaten_after_bump'."
    )
