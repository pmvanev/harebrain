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

from wumpus.constants import DODECAHEDRON

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


# ---------------------------------------------------------------------------
# R1-S04 — Move + pit + bat teleport (recursive)
# ---------------------------------------------------------------------------
#
# Strategy mirrors R1-S03: pin the layout via `Game._from_world`, swap
# `game._random` with a `_MockRandom` whose scripted `randint` values control
# the bat-teleport target (Yob's FNB(1) for bat snatch draws over rooms
# 1..20 — uniform per the archived journey yaml step 4 spec, NOT just adjacents).
#
# Each scenario constructs its own World fixture in its Given step. The When
# step (`the player moves to room <N>`) drives the move and captures the
# event stream emitted after construction.


def _drive_move_with_scripted_rng(
    *,
    world: Any,
    target_room: int,
    scripted_randint: list[int],
) -> list[Any]:
    """Construct a Game pinned to `world`, swap its RNG with `_MockRandom`
    scripted by `scripted_randint`, attach a fresh InMemorySink, step the
    player into `target_room`, and return events emitted after construction."""
    from wumpus import Game
    from wumpus.sinks import InMemorySink

    game = Game._from_world(world, seed=0)
    game._random = _MockRandom(scripted_randint)  # type: ignore[assignment]

    sink = InMemorySink()
    game.subscribe(sink)
    pre_move_count = len(sink.events)
    game.step(f"move {target_room}")
    return sink.events[pre_move_count:]


# ---------------------------------------------------------------------------
# R1-S04 — Scenario 1: Falling into a pit ends the game
# ---------------------------------------------------------------------------


@given(
    "a pit is in room 4 and the player is in room 3 (adjacent to 4)",
    target_fixture="r1s04_pit_scenario_events",
)
def _r1s04_pit_scenario_events() -> list[Any]:
    # Room 3 has neighbors {2, 4, 12}. Player at 3, pit at 4 (adjacent).
    # Wumpus parked at 11 (not in {2,4,12} and not in room 4's neighbors
    # {3,5,14} either — irrelevant since the pit-fall fires first). Second
    # pit at 14, bats at 15, 19 — all distinct, none in the pit-fall path.
    from wumpus.types import World

    world = World(
        player_room=3,
        wumpus_rooms=(11,),
        pit_rooms=(4, 14),
        bat_rooms=(15, 19),
        arrows=5,
        turn=0,
        alive=True,
        pending_prompt=None,
        pending_arrow_path=(),
    )
    # No RNG draws expected for a pure pit fall (no startle, no teleport).
    return _drive_move_with_scripted_rng(
        world=world, target_room=4, scripted_randint=[]
    )


@when("the player moves to room 4")
def _r1s04_when_move_to_4() -> None:
    """No-op: the Given step already drove the move and captured events.
    pytest-bdd needs a When binding for the step text to resolve."""


@then("HazardTriggered(PIT) fires")
def _r1s04_hazard_triggered_pit(request: Any) -> None:
    """Shared across scenarios 1 (direct pit fall) and 3 (bat→pit chain).
    Probes for the active scenario's fixture."""
    events = _pull_r1s04_any_scenario_events(request)
    from wumpus.events import HazardTriggered

    pit_events = [
        e for e in events if isinstance(e, HazardTriggered) and e.kind == "PIT"
    ]
    assert pit_events, (
        f"No HazardTriggered(PIT) event after pit fall. "
        f"Events seen: {[type(e).__name__ for e in events]}"
    )


@then("GameEnded(outcome=fell_in_pit) fires")
def _r1s04_game_ended_fell_in_pit(request: Any) -> None:
    """Shared across scenarios 1 and 3."""
    events = _pull_r1s04_any_scenario_events(request)
    from wumpus.events import GameEnded

    ended_events = [e for e in events if isinstance(e, GameEnded)]
    assert ended_events, "No GameEnded event after pit fall (direct or recursive)."
    assert ended_events[0].outcome == "fell_in_pit", (
        f"GameEnded.outcome was {ended_events[0].outcome!r}; expected 'fell_in_pit'."
    )
    assert ended_events[0].message_kind == "lose", (
        f"GameEnded.message_kind was {ended_events[0].message_kind!r}; expected 'lose'."
    )


# ---------------------------------------------------------------------------
# R1-S04 — Scenario 2: Bat teleport to a safe room re-emits senses for new room
# ---------------------------------------------------------------------------


@given(
    "a bat is in room 5 and the engine's next bat-teleport target is room 17",
    target_fixture="r1s04_bat_safe_scenario_events",
)
def _r1s04_bat_safe_scenario_events() -> list[Any]:
    # Room 5 neighbors {1, 4, 6}; player starts at 1 and moves to 5.
    # Bat at 5; second bat parked at 12 (NOT in room 17's neighbors {7,16,18},
    # NOT room 17 itself).
    # Room 17 neighbors {7, 16, 18}. To make room 17 hazard-free + safe:
    #   wumpus at 11 (not in {7,16,18}, not room 17)
    #   pits at 13, 14 (neither in {7,16,18}, neither is 17)
    # Verified: no entity is in {17}∪{7,16,18}.
    from wumpus.types import World

    world = World(
        player_room=1,
        wumpus_rooms=(11,),
        pit_rooms=(13, 14),
        bat_rooms=(5, 12),
        arrows=5,
        turn=0,
        alive=True,
        pending_prompt=None,
        pending_arrow_path=(),
    )
    # One bat draw: randint(1, 20) → 17 (the bat-teleport target).
    return _drive_move_with_scripted_rng(
        world=world, target_room=5, scripted_randint=[17]
    )


@given("room 17 is adjacent to no hazards")
def _r1s04_room_17_safe_assertion() -> None:
    """Layout assertion: the prior Given already constructed a world where
    room 17's neighbors {7, 16, 18} contain no entity rooms. No fixture state
    to propagate; pytest-bdd just needs the binding."""


@when("the player moves to room 5")
def _r1s04_when_move_to_5() -> None:
    """No-op: the Given step already drove the move."""


@then("PlayerTeleported(from=5, to=17) fires")
def _r1s04_player_teleported_5_to_17(request: Any) -> None:
    """Shared across scenarios 2 and 3."""
    events = _pull_r1s04_bat_scenario_events(request)
    from wumpus.events import PlayerTeleported

    tps = [e for e in events if isinstance(e, PlayerTeleported)]
    assert tps, (
        f"No PlayerTeleported event emitted on bat snatch. "
        f"Events seen: {[type(e).__name__ for e in events]}"
    )
    event = tps[0]
    assert event.from_room == 5, (
        f"PlayerTeleported.from_room was {event.from_room}; expected 5."
    )
    assert event.to_room == 17, (
        f"PlayerTeleported.to_room was {event.to_room}; expected 17 "
        f"(scripted randint(1, 20) → 17)."
    )
    assert event.cause == "bat", (
        f"PlayerTeleported.cause was {event.cause!r}; expected 'bat' "
        f"(per L18 + Tier A4 amendment)."
    )


@then("LocationReported(room=17) fires")
def _r1s04_location_reported_room_17(
    r1s04_bat_safe_scenario_events: list[Any],
) -> None:
    from wumpus.events import LocationReported

    location_events = [
        e for e in r1s04_bat_safe_scenario_events if isinstance(e, LocationReported)
    ]
    assert location_events, (
        "No LocationReported event after bat teleport into a safe room. "
        "Sense+location re-emission contract violated."
    )
    # The LAST LocationReported should be for the teleport destination.
    final_location = location_events[-1]
    assert final_location.room == 17, (
        f"Final LocationReported.room was {final_location.room}; "
        f"expected 17 (the teleport destination)."
    )


@then("no SenseEmitted event fires for the new room")
def _r1s04_no_sense_for_new_room(
    r1s04_bat_safe_scenario_events: list[Any],
) -> None:
    from wumpus.events import LocationReported, PlayerTeleported, SenseEmitted

    # Find the slice of events BETWEEN PlayerTeleported and the final
    # LocationReported. Any SenseEmitted in that slice would mean sense
    # events fired for the new room. Room 17's neighbors {7, 16, 18} contain
    # no hazards in our layout, so the engine should emit ZERO SenseEmitted
    # for the teleport destination.
    teleport_indices = [
        i
        for i, e in enumerate(r1s04_bat_safe_scenario_events)
        if isinstance(e, PlayerTeleported)
    ]
    location_indices = [
        i
        for i, e in enumerate(r1s04_bat_safe_scenario_events)
        if isinstance(e, LocationReported)
    ]
    assert teleport_indices and location_indices, (
        "Missing PlayerTeleported or LocationReported events; cannot validate "
        "sense-emission window for the teleport destination."
    )
    window_start = teleport_indices[-1]
    window_end = location_indices[-1]
    new_room_senses = [
        e
        for e in r1s04_bat_safe_scenario_events[window_start:window_end]
        if isinstance(e, SenseEmitted)
    ]
    assert new_room_senses == [], (
        f"Expected zero SenseEmitted events for safe teleport destination "
        f"(room 17 has no adjacent hazards); got {new_room_senses!r}."
    )


# ---------------------------------------------------------------------------
# R1-S04 — Scenario 3: Bat teleport into a pit ends the game (recursive)
# ---------------------------------------------------------------------------


@given(
    "a bat is in room 5 and a pit is in room 17",
    target_fixture="r1s04_bat_pit_scenario_events",
)
def _r1s04_bat_pit_scenario_setup() -> dict[str, Any]:
    """Build the world fixture for scenario 3. The events list is filled in
    by the second Given step (which scripts the RNG draw)."""
    from wumpus.types import World

    # Player at 1 (neighbor of 5), bat at 5, pit at 17 (the teleport destination).
    # Wumpus parked at 11 (not adjacent to 5 or 17). Second pit at 14, second
    # bat at 9 — all distinct, all far from the recursive-hazard chain.
    world = World(
        player_room=1,
        wumpus_rooms=(11,),
        pit_rooms=(17, 14),
        bat_rooms=(5, 9),
        arrows=5,
        turn=0,
        alive=True,
        pending_prompt=None,
        pending_arrow_path=(),
    )
    return {"world": world, "events": []}


@given("the engine's next bat-teleport target is room 17")
def _r1s04_bat_target_is_17(
    r1s04_bat_pit_scenario_events: dict[str, Any],
) -> None:
    """Drive the move with randint(1, 20) → 17 and capture the resulting
    events into the shared scenario fixture."""
    world = r1s04_bat_pit_scenario_events["world"]
    events = _drive_move_with_scripted_rng(
        world=world, target_room=5, scripted_randint=[17]
    )
    r1s04_bat_pit_scenario_events["events"] = events


def _pull_r1s04_any_scenario_events(request: Any) -> list[Any]:
    """Probe scenario 3's dict fixture first (recursive bat→pit), then
    scenarios 1 and 2 in order."""
    try:
        bag = request.getfixturevalue("r1s04_bat_pit_scenario_events")
        if isinstance(bag, dict) and bag.get("events"):
            return list(bag["events"])
    except pytest.FixtureLookupError:
        pass
    try:
        return list(request.getfixturevalue("r1s04_pit_scenario_events"))
    except pytest.FixtureLookupError:
        pass
    try:
        return list(request.getfixturevalue("r1s04_bat_safe_scenario_events"))
    except pytest.FixtureLookupError:
        pass
    raise AssertionError(
        "No r1s04_*_scenario_events fixture resolved; scenario Given steps did "
        "not populate one."
    )


def _pull_r1s04_bat_scenario_events(request: Any) -> list[Any]:
    """Probe scenario 3's dict fixture first (bat→pit), then scenario 2's
    list fixture (safe bat teleport)."""
    try:
        bag = request.getfixturevalue("r1s04_bat_pit_scenario_events")
        if isinstance(bag, dict) and bag.get("events"):
            return list(bag["events"])
    except pytest.FixtureLookupError:
        pass
    try:
        return list(request.getfixturevalue("r1s04_bat_safe_scenario_events"))
    except pytest.FixtureLookupError:
        pass
    raise AssertionError("No bat-scenario events fixture resolved (scenario 2 or 3).")


# ---------------------------------------------------------------------------
# R1-S05 — Shoot path collection + crooked-arrow rejection
# ---------------------------------------------------------------------------
#
# Strategy: the shoot sub-state-machine is driven entirely through `step()`
# calls; no monkeypatch is required. We construct a pinned World via
# `Game._from_world` (so we get a stable layout), then drive the sub-state-
# machine via `step("S")` → `step("<path-len>")` → `step("<room>")` chains
# and inspect the post-step event streams on a subscribed InMemorySink.


def _build_default_shoot_world() -> Any:
    """Pin a layout suitable for R1-S05's shoot-collection scenarios. The
    actual room numbers chosen for slots don't matter for the state-machine
    behavior — what matters is that the engine accepts the chain and emits
    the right events. We keep all entities far away from the player so no
    incidental hazards fire during the test setup."""
    from wumpus.types import World

    return World(
        player_room=1,
        wumpus_rooms=(11,),
        pit_rooms=(13, 14),
        bat_rooms=(15, 19),
        arrows=5,
        turn=0,
        alive=True,
        pending_prompt=None,
        pending_arrow_path=(),
    )


def _capture_post_step_events(game: Any, sink: Any, action: str) -> list[Any]:
    """Run a single `step(action)` and return only the events emitted by
    that step (not the historical replay the sink received on subscribe)."""
    pre_count = len(sink.events)
    game.step(action)
    return sink.events[pre_count:]


# ---------------------------------------------------------------------------
# R1-S05 — Scenario 1: Path-length out of range re-prompts
# ---------------------------------------------------------------------------


@given(
    "the player has chosen S",
    target_fixture="r1s05_after_S_state",
)
def _r1s05_after_S_state() -> dict[str, Any]:
    """Construct a Game and run `step("S")` so the engine enters shoot mode
    and is awaiting the path length. Return the game + sink for follow-up."""
    from wumpus import Game
    from wumpus.sinks import InMemorySink

    game = Game._from_world(_build_default_shoot_world(), seed=0)
    sink = InMemorySink()
    game.subscribe(sink)
    _capture_post_step_events(game, sink, "S")
    return {
        "game": game,
        "sink": sink,
        "turn_at_S": game.world_state().turn,
    }


@when(
    "the player enters 0 for NO. OF ROOMS(1-5)?",
    target_fixture="r1s05_path_len_zero_events",
)
def _r1s05_path_len_zero(r1s05_after_S_state: dict[str, Any]) -> list[Any]:
    return _capture_post_step_events(
        r1s05_after_S_state["game"],
        r1s05_after_S_state["sink"],
        "0",
    )


@then("NO. OF ROOMS(1-5)? is re-prompted")
def _r1s05_path_len_zero_reprompt(
    r1s05_path_len_zero_events: list[Any],
    r1s05_after_S_state: dict[str, Any],
) -> None:
    from wumpus.events import PromptIssued

    prompt_events = [
        e for e in r1s05_path_len_zero_events if isinstance(e, PromptIssued)
    ]
    assert prompt_events, (
        "No PromptIssued event emitted after invalid path length. "
        f"Events seen: {[type(e).__name__ for e in r1s05_path_len_zero_events]}"
    )
    assert prompt_events[-1].kind == "shoot_path_len", (
        f"Re-prompt PromptIssued.kind was {prompt_events[-1].kind!r}; "
        f"expected 'shoot_path_len' (path-length re-prompt)."
    )
    # pending_prompt must still be the path-length prompt — not advanced.
    assert (
        r1s05_after_S_state["game"].world_state().pending_prompt == "shoot_path_len"
    ), (
        "After rejecting an out-of-range path length, pending_prompt should "
        "still be 'shoot_path_len'; got "
        f"{r1s05_after_S_state['game'].world_state().pending_prompt!r}."
    )


@then("no turn counter advance has occurred")
def _r1s05_no_turn_advance(
    r1s05_after_S_state: dict[str, Any],
) -> None:
    assert (
        r1s05_after_S_state["game"].world_state().turn
        == r1s05_after_S_state["turn_at_S"]
    ), (
        "Turn counter advanced on a path-length re-prompt; per Yob 1973 + the "
        "monotonic_turn discipline, only action-completing events advance the "
        "turn counter."
    )


# ---------------------------------------------------------------------------
# R1-S05 — Scenario 2: Crooked path triggers slot-specific re-prompt
# ---------------------------------------------------------------------------


@given(
    "the player has entered path entries [7, 14] for a 3-room shoot",
    target_fixture="r1s05_mid_shoot_state",
)
def _r1s05_mid_shoot_state() -> dict[str, Any]:
    """Drive the engine through `S` → `3` → `7` → `14` so it is awaiting
    slot 3 of a 3-room shoot, with [7, 14] already accepted."""
    from wumpus import Game
    from wumpus.sinks import InMemorySink

    game = Game._from_world(_build_default_shoot_world(), seed=0)
    sink = InMemorySink()
    game.subscribe(sink)
    _capture_post_step_events(game, sink, "S")
    _capture_post_step_events(game, sink, "3")
    _capture_post_step_events(game, sink, "7")
    _capture_post_step_events(game, sink, "14")
    return {"game": game, "sink": sink}


@when(
    "the player enters 7 for the third slot",
    target_fixture="r1s05_crooked_events",
)
def _r1s05_crooked_third_slot(
    r1s05_mid_shoot_state: dict[str, Any],
) -> list[Any]:
    return _capture_post_step_events(
        r1s05_mid_shoot_state["game"],
        r1s05_mid_shoot_state["sink"],
        "7",
    )


@then("a CrookedPathRejected(slot=3, attempted_room=7) event fires")
def _r1s05_crooked_event_fires(
    r1s05_crooked_events: list[Any],
) -> None:
    from wumpus.events import CrookedPathRejected

    crooked = [e for e in r1s05_crooked_events if isinstance(e, CrookedPathRejected)]
    assert crooked, (
        "No CrookedPathRejected event emitted. "
        f"Events seen: {[type(e).__name__ for e in r1s05_crooked_events]}"
    )
    assert crooked[0].slot == 3, (
        f"CrookedPathRejected.slot was {crooked[0].slot}; expected 3."
    )
    assert crooked[0].attempted_room == 7, (
        f"CrookedPathRejected.attempted_room was {crooked[0].attempted_room}; "
        f"expected 7."
    )


@then("ROOM #? is re-prompted ONLY for slot 3")
def _r1s05_reprompt_slot_3_only(
    r1s05_crooked_events: list[Any],
    r1s05_mid_shoot_state: dict[str, Any],
) -> None:
    from wumpus.events import PromptIssued

    prompts = [e for e in r1s05_crooked_events if isinstance(e, PromptIssued)]
    assert prompts, "No PromptIssued event emitted after crooked path rejection."
    last = prompts[-1]
    assert last.kind == "shoot_path_room", (
        f"Re-prompt PromptIssued.kind was {last.kind!r}; expected 'shoot_path_room'."
    )
    assert last.context is not None and last.context.get("slot") == 3, (
        f"Re-prompt PromptIssued.context.slot was {last.context}; expected slot=3."
    )


@then("the previously-entered rooms 7 and 14 remain unchanged")
def _r1s05_path_preserved(
    r1s05_mid_shoot_state: dict[str, Any],
) -> None:
    world = r1s05_mid_shoot_state["game"].world_state()
    assert world.pending_arrow_path == (7, 14), (
        f"After crooked rejection at slot 3, pending_arrow_path should still "
        f"be (7, 14); got {world.pending_arrow_path!r}."
    )


# ---------------------------------------------------------------------------
# R1-S05 — Scenario 3: Mid-shoot snapshot round-trips
# ---------------------------------------------------------------------------


@given(
    "the player is mid-shoot, has entered NO. OF ROOMS=3 and ROOM #=7 for slot 1",
    target_fixture="r1s05_mid_shoot_for_snapshot",
)
def _r1s05_mid_shoot_for_snapshot() -> Any:
    """Drive the engine to mid-shoot state: S → 3 → 7, awaiting slot 2 of 3."""
    from wumpus import Game
    from wumpus.sinks import InMemorySink

    game = Game._from_world(_build_default_shoot_world(), seed=0)
    sink = InMemorySink()
    game.subscribe(sink)
    _capture_post_step_events(game, sink, "S")
    _capture_post_step_events(game, sink, "3")
    _capture_post_step_events(game, sink, "7")
    return game


@when(
    "game.snapshot() is taken and Game.from_snapshot(snap) is constructed",
    target_fixture="r1s05_resurrected_game",
)
def _r1s05_resurrect_from_snapshot(
    r1s05_mid_shoot_for_snapshot: Any,
) -> Any:
    from wumpus import Game

    snap = r1s05_mid_shoot_for_snapshot.snapshot()
    return Game.from_snapshot(snap)


@then("the resurrected game prompts for ROOM #? at slot 2")
def _r1s05_resurrected_prompts_slot_2(
    r1s05_resurrected_game: Any,
) -> None:
    world = r1s05_resurrected_game.world_state()
    assert world.pending_prompt == "shoot_path_room", (
        f"Resurrected game's pending_prompt was {world.pending_prompt!r}; "
        f"expected 'shoot_path_room'."
    )
    # After feeding a fresh step("8") (an arbitrary non-crooked room), the
    # next prompt context must mention slot 2 + total length 3. Instead of
    # introspecting hidden state, we check the prompt context emitted by the
    # resurrected game on its next subscribe replay.
    # The snapshot must encode enough state that the engine knows it's at
    # slot 2; we observe this via the next emitted PromptIssued.
    from wumpus.events import PromptIssued
    from wumpus.sinks import InMemorySink

    sink = InMemorySink()
    r1s05_resurrected_game.subscribe(sink)
    # Find the last PromptIssued in the replay (which should be the
    # awaiting-slot-2 prompt that was emitted before snapshot).
    prompts = [e for e in sink.events if isinstance(e, PromptIssued)]
    assert prompts, (
        "Resurrected game replayed no PromptIssued events; snapshot must "
        "preserve enough state to re-emit the pending prompt."
    )
    last = prompts[-1]
    assert last.kind == "shoot_path_room", (
        f"Resurrected game's last replayed prompt was {last.kind!r}; "
        f"expected 'shoot_path_room'."
    )
    assert last.context is not None and last.context.get("slot") == 2, (
        f"Resurrected prompt context was {last.context!r}; expected slot=2."
    )


@then("the pending_arrow_path is [7]")
def _r1s05_resurrected_path_is_7(
    r1s05_resurrected_game: Any,
) -> None:
    world = r1s05_resurrected_game.world_state()
    assert world.pending_arrow_path == (7,), (
        f"Resurrected game's pending_arrow_path was {world.pending_arrow_path!r}; "
        f"expected (7,)."
    )


# ---------------------------------------------------------------------------
# R1-S06 — Arrow walk + hit/miss/self-shot + out-of-arrows
# ---------------------------------------------------------------------------
#
# Strategy: drive the shoot sub-state-machine via `step("S")` → path-length
# → per-slot rooms; the engine fires `ArrowFired` on the final slot and
# (R1-S06 wires this) immediately calls `walk_arrow`. We pin the World with
# `Game._from_world` so the player/wumpus rooms are deterministic, then
# monkeypatch `game._random` with `_MockRandom` for any RNG-consuming step.
#
# RNG draws consumed by R1-S06:
#   - on deflection: one `randint(1, 3)` per missing-tunnel hop
#   - on miss: one `randint(1, 4)` for the FNC(0) startle


def _drive_shoot_through_path(
    *,
    world: Any,
    path: tuple[int, ...],
    scripted_randint: list[int],
) -> list[Any]:
    """Drive a full S → path-length → per-slot chain on a pinned World and
    return all events emitted from the moment `step("S")` runs. The Mock
    RNG is installed BEFORE the chain begins so any randint draws made
    by the arrow walk (deflection / startle) consume scripted values."""
    from wumpus import Game
    from wumpus.sinks import InMemorySink

    game = Game._from_world(world, seed=0)
    game._random = _MockRandom(scripted_randint)  # type: ignore[assignment]
    sink = InMemorySink()
    game.subscribe(sink)
    pre = len(sink.events)
    game.step("S")
    game.step(str(len(path)))
    for room in path:
        game.step(str(room))
    return sink.events[pre:]


def _build_shoot_world(
    *,
    player_room: int,
    wumpus_rooms: tuple[int, ...],
    arrows: int = 5,
) -> Any:
    """Pin a layout for R1-S06 shoot scenarios. Hazards parked far from any
    path-walked room so they cannot fire incidentally on `step()` calls.
    The shoot sub-state-machine does not invoke hazard resolution; this is
    belt-and-braces."""
    from wumpus.types import World

    return World(
        player_room=player_room,
        wumpus_rooms=wumpus_rooms,
        pit_rooms=(11, 13),  # Not adjacent to 7/8/9/17 path rooms.
        bat_rooms=(15, 19),
        arrows=arrows,
        turn=0,
        alive=True,
        pending_prompt=None,
        pending_arrow_path=(),
    )


# ---------------------------------------------------------------------------
# R1-S06 — Scenario 1: Successful shot kills the wumpus
# ---------------------------------------------------------------------------


@given(
    "the player is in room 8 with 5 arrows",
    target_fixture="r1s06_scenario_state",
)
def _r1s06_player_in_8_with_5_arrows() -> dict[str, Any]:
    """Shared by scenarios 1 and 2 (both Givens read 'in room 8 with 5
    arrows'). The dict acts as a scenario bag the subsequent Given/When/Then
    steps populate."""
    return {"player_room": 8, "arrows": 5}


@given("the wumpus is in room 17 and rooms 8-7, 7-17 are connected")
def _r1s06_wumpus_in_17_path_connected(
    r1s06_scenario_state: dict[str, Any],
) -> None:
    # Sanity-check the dodecahedron — fails loudly if Yob-fidelity drift.
    assert 7 in DODECAHEDRON[8], "Room 7 must be adjacent to room 8."
    assert 17 in DODECAHEDRON[7], "Room 17 must be adjacent to room 7."
    r1s06_scenario_state["wumpus_rooms"] = (17,)


@when("the player shoots a 2-room path through rooms 7, 17")
def _r1s06_shoot_path_7_17(
    r1s06_scenario_state: dict[str, Any],
) -> None:
    world = _build_shoot_world(
        player_room=r1s06_scenario_state["player_room"],
        wumpus_rooms=r1s06_scenario_state["wumpus_rooms"],
        arrows=r1s06_scenario_state["arrows"],
    )
    r1s06_scenario_state["events"] = _drive_shoot_through_path(
        world=world, path=(7, 17), scripted_randint=[]
    )


@then("ArrowFired(path=[7, 17]) fires")
def _r1s06_arrow_fired_7_17(r1s06_scenario_state: dict[str, Any]) -> None:
    from wumpus.events import ArrowFired

    fired = [e for e in r1s06_scenario_state["events"] if isinstance(e, ArrowFired)]
    assert fired, "No ArrowFired event emitted."
    assert fired[0].path == (7, 17), (
        f"ArrowFired.path was {fired[0].path!r}; expected (7, 17)."
    )


@then("ArrowPathStep(room=7, deflected=False) fires")
def _r1s06_path_step_7(r1s06_scenario_state: dict[str, Any]) -> None:
    from wumpus.events import ArrowPathStep

    steps = [e for e in r1s06_scenario_state["events"] if isinstance(e, ArrowPathStep)]
    assert steps, "No ArrowPathStep emitted."
    assert steps[0].room == 7 and steps[0].deflected is False, (
        f"First ArrowPathStep was room={steps[0].room}, deflected={steps[0].deflected}; "
        f"expected room=7, deflected=False."
    )


@then("ArrowPathStep(room=17, deflected=False) fires")
def _r1s06_path_step_17(r1s06_scenario_state: dict[str, Any]) -> None:
    from wumpus.events import ArrowPathStep

    steps = [e for e in r1s06_scenario_state["events"] if isinstance(e, ArrowPathStep)]
    assert len(steps) >= 2, f"Expected >=2 ArrowPathStep events; got {len(steps)}."
    assert steps[1].room == 17 and steps[1].deflected is False, (
        f"Second ArrowPathStep was room={steps[1].room}, "
        f"deflected={steps[1].deflected}; expected room=17, deflected=False."
    )


@then("ArrowHitWumpus(room=17) fires")
def _r1s06_arrow_hit_wumpus_17(r1s06_scenario_state: dict[str, Any]) -> None:
    from wumpus.events import ArrowHitWumpus

    hits = [e for e in r1s06_scenario_state["events"] if isinstance(e, ArrowHitWumpus)]
    assert hits, "No ArrowHitWumpus event emitted."
    assert hits[0].room == 17, f"ArrowHitWumpus.room was {hits[0].room}; expected 17."


@then("GameEnded(outcome=wumpus_shot) fires")
def _r1s06_game_ended_wumpus_shot(r1s06_scenario_state: dict[str, Any]) -> None:
    from wumpus.events import GameEnded

    ended = [e for e in r1s06_scenario_state["events"] if isinstance(e, GameEnded)]
    assert ended, "No GameEnded event emitted after wumpus hit."
    assert ended[0].outcome == "wumpus_shot", (
        f"GameEnded.outcome was {ended[0].outcome!r}; expected 'wumpus_shot'."
    )
    assert ended[0].message_kind == "win", (
        f"GameEnded.message_kind was {ended[0].message_kind!r}; expected 'win'."
    )


# ---------------------------------------------------------------------------
# R1-S06 — Scenario 2: Crooked arrow through player's room mid-path does NOT kill
# ---------------------------------------------------------------------------


@given(
    "the arrow path walks rooms 7, then 8 (mid-path, passing through player), then 9"
)
def _r1s06_midpath_through_player(
    r1s06_scenario_state: dict[str, Any],
) -> None:
    # Player at 8. Path: [7, 8, 9]. 8→7 adj, 7→8 adj, 8→9 adj. Final = 9.
    # 9 != wumpus (parked at 17), 9 != player (8) → miss.
    # The canary: ArrowPathStep(room=8) fires mid-path but no ArrowHitPlayer.
    assert 7 in DODECAHEDRON[8] and 8 in DODECAHEDRON[7] and 9 in DODECAHEDRON[8], (
        "Path 8→7→8→9 must all be adjacent steps."
    )
    r1s06_scenario_state["wumpus_rooms"] = (17,)
    # The arrow misses → wumpus startle consumes randint(1, 4); script K=4
    # (stay-put) so the wumpus doesn't move onto the player.
    r1s06_scenario_state["path"] = (7, 8, 9)
    r1s06_scenario_state["scripted_randint"] = [4]


@when("the arrow walks the path")
def _r1s06_walk_path(r1s06_scenario_state: dict[str, Any]) -> None:
    world = _build_shoot_world(
        player_room=r1s06_scenario_state["player_room"],
        wumpus_rooms=r1s06_scenario_state["wumpus_rooms"],
        arrows=r1s06_scenario_state["arrows"],
    )
    r1s06_scenario_state["events"] = _drive_shoot_through_path(
        world=world,
        path=r1s06_scenario_state["path"],
        scripted_randint=r1s06_scenario_state["scripted_randint"],
    )


@then("ArrowPathStep(room=8, deflected=False) fires (no ArrowHitPlayer)")
def _r1s06_step_room_8_no_hit_player(
    r1s06_scenario_state: dict[str, Any],
) -> None:
    from wumpus.events import ArrowHitPlayer, ArrowPathStep

    events = r1s06_scenario_state["events"]
    steps = [e for e in events if isinstance(e, ArrowPathStep)]
    # The mid-path step into room 8 (player's room) must be present.
    room_8_steps = [s for s in steps if s.room == 8 and s.deflected is False]
    assert room_8_steps, (
        f"Expected an ArrowPathStep(room=8, deflected=False) mid-path; "
        f"got steps: {[(s.room, s.deflected) for s in steps]}"
    )
    # The canary: no ArrowHitPlayer was emitted (Yob D11 bug-for-bug).
    hits = [e for e in events if isinstance(e, ArrowHitPlayer)]
    assert hits == [], (
        f"ArrowHitPlayer fired mid-path; Yob bug-for-bug rule violated. "
        f"Self-shot must fire ONLY on FINAL room match. Hits: {hits!r}"
    )


@then("ArrowPathStep(room=9, ...) fires")
def _r1s06_step_room_9_fires(
    r1s06_scenario_state: dict[str, Any],
) -> None:
    from wumpus.events import ArrowPathStep

    steps = [e for e in r1s06_scenario_state["events"] if isinstance(e, ArrowPathStep)]
    room_9_steps = [s for s in steps if s.room == 9]
    assert room_9_steps, (
        f"Expected an ArrowPathStep(room=9, ...) for the final hop; got steps: "
        f"{[(s.room, s.deflected) for s in steps]}"
    )


@then("the player is unharmed at this step")
def _r1s06_player_unharmed(
    r1s06_scenario_state: dict[str, Any],
) -> None:
    from wumpus.events import ArrowHitPlayer, GameEnded

    events = r1s06_scenario_state["events"]
    # The scenario's contract: no self-shot fired. (A GameEnded for any
    # OTHER reason is acceptable — e.g. out_of_arrows from the decrement
    # if arrows started low — but in this scenario arrows=5, so no
    # terminal should fire.)
    assert not any(isinstance(e, ArrowHitPlayer) for e in events), (
        "Player was hit mid-path — Yob D11 bug-for-bug violation."
    )
    # With arrows=5 starting count, a miss leaves arrows=4 → no terminal.
    terminal = [e for e in events if isinstance(e, GameEnded)]
    assert terminal == [], (
        f"Unexpected terminal event in mid-path-through-player scenario: {terminal!r}"
    )


# ---------------------------------------------------------------------------
# R1-S06 — Scenario 3: Arrow's FINAL room matches player → self-shot
# ---------------------------------------------------------------------------


@given(
    "the player is in room 8 and the arrow's final room is room 8",
    target_fixture="r1s06_selfshot_state",
)
def _r1s06_selfshot_setup() -> dict[str, Any]:
    """Build a path whose FINAL room equals player's room 8.
    Path [7, 8]: 8→7 adj, 7→8 adj. Final = 8 = player. Self-shot."""
    assert 7 in DODECAHEDRON[8] and 8 in DODECAHEDRON[7], (
        "Path 8→7→8 must be a valid 2-step walk."
    )
    world = _build_shoot_world(
        player_room=8,
        wumpus_rooms=(17,),  # parked away — not on path
        arrows=5,
    )
    events = _drive_shoot_through_path(world=world, path=(7, 8), scripted_randint=[])
    return {"events": events}


@then("ArrowHitPlayer(room=8) fires")
def _r1s06_arrow_hit_player_8(
    r1s06_selfshot_state: dict[str, Any],
) -> None:
    from wumpus.events import ArrowHitPlayer

    hits = [e for e in r1s06_selfshot_state["events"] if isinstance(e, ArrowHitPlayer)]
    assert hits, "No ArrowHitPlayer event emitted after final-room match."
    assert hits[0].room == 8, (
        f"ArrowHitPlayer.room was {hits[0].room}; expected 8 (player's room)."
    )


@then("ArrowCountChanged(new_count=4) fires (decrement-as-if-missed)")
def _r1s06_arrow_count_4(
    r1s06_selfshot_state: dict[str, Any],
) -> None:
    from wumpus.events import ArrowCountChanged

    changes = [
        e for e in r1s06_selfshot_state["events"] if isinstance(e, ArrowCountChanged)
    ]
    assert changes, "No ArrowCountChanged event emitted after self-shot."
    assert changes[0].new_count == 4, (
        f"ArrowCountChanged.new_count was {changes[0].new_count}; "
        f"expected 4 (decrement from 5)."
    )


@then("the game continues unless arrow count is now 0")
def _r1s06_game_continues(
    r1s06_selfshot_state: dict[str, Any],
) -> None:
    from wumpus.events import GameEnded

    ended = [e for e in r1s06_selfshot_state["events"] if isinstance(e, GameEnded)]
    # With arrows=5 starting, decrement to 4 → no terminal.
    assert ended == [], (
        f"Unexpected GameEnded event on self-shot with arrows=5→4: {ended!r}"
    )


# ---------------------------------------------------------------------------
# R1-S06 — Scenario 4: Arrow takes random tunnel on missing connection
# ---------------------------------------------------------------------------


@given(
    "the player is in room 8 and shoots a path beginning with room 14 (not adjacent to 8)",
    target_fixture="r1s06_deflect_state",
)
def _r1s06_deflect_setup() -> dict[str, Any]:
    """Player in 8 (neighbors {1, 7, 9}). Path starts with 14 — NOT
    adjacent to 8. Engine deflects via randint(1, 3) into sorted_adjacents[K-1].
    Script K=1 → arrow goes to sorted_adjacents(8)[0] = 1 (sorted of {1,7,9}).
    Remaining path slots are discarded."""
    assert 14 not in DODECAHEDRON[8], "Room 14 must NOT be adjacent to room 8."
    world = _build_shoot_world(
        player_room=8,
        wumpus_rooms=(17,),
        arrows=5,
    )
    # Path = [14, 17, 5] — 14 forces deflect; remaining 17, 5 should be
    # discarded by the engine. Script randint(1, 3) = 1 for the deflect
    # (sends arrow to room 1), then randint(1, 4) = 4 for the startle.
    events = _drive_shoot_through_path(
        world=world, path=(14, 17, 5), scripted_randint=[1, 4]
    )
    return {"events": events, "expected_deflect_room": sorted(DODECAHEDRON[8])[0]}


@when("the arrow is walked")
def _r1s06_arrow_walked() -> None:
    """No-op: the prior Given already drove the chain."""


@then("ArrowPathStep(room=<random-adjacent-of-8>, deflected=True) fires")
def _r1s06_deflected_step(
    r1s06_deflect_state: dict[str, Any],
) -> None:
    from wumpus.events import ArrowPathStep

    steps = [e for e in r1s06_deflect_state["events"] if isinstance(e, ArrowPathStep)]
    assert steps, "No ArrowPathStep emitted under deflection scenario."
    first = steps[0]
    expected = r1s06_deflect_state["expected_deflect_room"]
    assert first.deflected is True, (
        f"First ArrowPathStep.deflected was {first.deflected}; expected True."
    )
    assert first.room == expected, (
        f"Deflected room was {first.room}; expected {expected} "
        f"(sorted_adjacents(8)[0] under scripted randint=1)."
    )


@then("no further path rooms are consulted (remaining slots discarded)")
def _r1s06_remaining_slots_discarded(
    r1s06_deflect_state: dict[str, Any],
) -> None:
    from wumpus.events import ArrowPathStep

    steps = [e for e in r1s06_deflect_state["events"] if isinstance(e, ArrowPathStep)]
    # Exactly ONE ArrowPathStep should fire — the deflection. Remaining
    # path slots [17, 5] are discarded.
    assert len(steps) == 1, (
        f"Expected exactly 1 ArrowPathStep (deflection terminates walk); "
        f"got {len(steps)}: {[(s.room, s.deflected) for s in steps]}"
    )


# ---------------------------------------------------------------------------
# R1-S06 — Scenario 5: Miss → startle + decrement
# ---------------------------------------------------------------------------


@given(
    "the player misses and the next startle draw will leave the wumpus in place",
    target_fixture="r1s06_miss_state",
)
def _r1s06_miss_setup() -> dict[str, Any]:
    """Player at 8, wumpus at 17. Shoot path [7] → final = 7. 7 != wumpus(17),
    7 != player(8) → miss. Startle draw K=4 keeps the wumpus at 17."""
    world = _build_shoot_world(
        player_room=8,
        wumpus_rooms=(17,),
        arrows=5,
    )
    events = _drive_shoot_through_path(world=world, path=(7,), scripted_randint=[4])
    return {"events": events, "prev_arrows": 5}


def _pull_r1s06_miss_or_oom_events(request: Any) -> list[Any]:
    """Probe miss-scenario fixtures (scenario 5 / scenario 6) in order."""
    for name in ("r1s06_miss_state", "r1s06_out_of_arrows_state"):
        try:
            bag = request.getfixturevalue(name)
        except pytest.FixtureLookupError:
            continue
        return list(bag["events"])
    raise AssertionError(
        "No r1s06_miss_state or r1s06_out_of_arrows_state fixture resolved."
    )


@then("ArrowMissed fires")
def _r1s06_arrow_missed(request: Any) -> None:
    from wumpus.events import ArrowMissed

    events = _pull_r1s06_miss_or_oom_events(request)
    missed = [e for e in events if isinstance(e, ArrowMissed)]
    assert missed, (
        f"No ArrowMissed event emitted. Events: {[type(e).__name__ for e in events]}"
    )


@then("WumpusStartled(moved=False) fires")
def _r1s06_startled_no_move(
    r1s06_miss_state: dict[str, Any],
) -> None:
    from wumpus.events import WumpusStartled

    startled = [e for e in r1s06_miss_state["events"] if isinstance(e, WumpusStartled)]
    assert startled, "No WumpusStartled event emitted on arrow miss."
    # K=4 in FNC(0) means from_room == to_room (stay-put).
    assert startled[0].from_room == startled[0].to_room, (
        f"Expected stay-put startle (K=4); got from_room={startled[0].from_room}, "
        f"to_room={startled[0].to_room}."
    )
    assert startled[0].ate_player is False, (
        f"WumpusStartled.ate_player was {startled[0].ate_player}; expected False "
        f"(wumpus stayed at room 17, player is in room 8)."
    )


@then("ArrowCountChanged(new_count=<prev-1>) fires")
def _r1s06_arrow_decrement_after_miss(
    r1s06_miss_state: dict[str, Any],
) -> None:
    from wumpus.events import ArrowCountChanged

    changes = [
        e for e in r1s06_miss_state["events"] if isinstance(e, ArrowCountChanged)
    ]
    assert changes, "No ArrowCountChanged event emitted after miss."
    assert changes[0].new_count == r1s06_miss_state["prev_arrows"] - 1, (
        f"ArrowCountChanged.new_count was {changes[0].new_count}; expected "
        f"{r1s06_miss_state['prev_arrows'] - 1}."
    )


# ---------------------------------------------------------------------------
# R1-S06 — Scenario 6: Out of arrows ends the game
# ---------------------------------------------------------------------------


@given(
    "the player has 1 arrow remaining and misses",
    target_fixture="r1s06_out_of_arrows_state",
)
def _r1s06_out_of_arrows_setup() -> dict[str, Any]:
    """Player at 8, wumpus at 17, arrows=1. Path [7] misses → startle (K=4
    stay-put). Arrow count decrements to 0 → GameEnded(out_of_arrows)."""
    world = _build_shoot_world(
        player_room=8,
        wumpus_rooms=(17,),
        arrows=1,
    )
    events = _drive_shoot_through_path(world=world, path=(7,), scripted_randint=[4])
    return {"events": events}


@then("ArrowCountChanged(new_count=0) fires")
def _r1s06_arrow_count_zero(
    r1s06_out_of_arrows_state: dict[str, Any],
) -> None:
    from wumpus.events import ArrowCountChanged

    changes = [
        e
        for e in r1s06_out_of_arrows_state["events"]
        if isinstance(e, ArrowCountChanged)
    ]
    assert changes, "No ArrowCountChanged event emitted on out-of-arrows path."
    assert changes[-1].new_count == 0, (
        f"Final ArrowCountChanged.new_count was {changes[-1].new_count}; expected 0."
    )


@then("GameEnded(outcome=out_of_arrows) fires")
def _r1s06_game_ended_out_of_arrows(
    r1s06_out_of_arrows_state: dict[str, Any],
) -> None:
    from wumpus.events import GameEnded

    ended = [e for e in r1s06_out_of_arrows_state["events"] if isinstance(e, GameEnded)]
    assert ended, "No GameEnded event emitted after out-of-arrows."
    assert ended[0].outcome == "out_of_arrows", (
        f"GameEnded.outcome was {ended[0].outcome!r}; expected 'out_of_arrows'."
    )
    assert ended[0].message_kind == "lose", (
        f"GameEnded.message_kind was {ended[0].message_kind!r}; expected 'lose'."
    )


# ---------------------------------------------------------------------------
# R1-S07 — Terminal state + Yob win/lose message swap + SAME SET-UP
# ---------------------------------------------------------------------------
#
# Strategy: drive a Game to a terminal state via the existing shoot or move
# infrastructure, then inspect:
#   1. The Observation.rendered_lines emitted on the terminal turn
#   2. (for SAME SET-UP) the post-terminal step("Y") behavior + the
#      reconstructed game's _initial_layout / layout_hash
#
# YobSurface is a stateless module-level mapping (per ADR-001 "FP inside") in
# wumpus.surfaces.yob. The engine wires it via wumpus.engine.render_terminal.


def _build_win_scenario_world() -> Any:
    """Pin a layout where the player can shoot the wumpus deterministically.
    Mirrors R1-S06 scenario 1: player at 8, wumpus at 17, path through 7->17."""
    from wumpus.types import World

    return World(
        player_room=8,
        wumpus_rooms=(17,),
        pit_rooms=(11, 13),  # parked away
        bat_rooms=(15, 19),
        arrows=5,
        turn=0,
        alive=True,
        pending_prompt=None,
        pending_arrow_path=(),
    )


def _build_pit_scenario_world() -> Any:
    """Pin a layout where the player steps into a pit (no shoot needed)."""
    from wumpus.types import World

    return World(
        player_room=3,
        wumpus_rooms=(11,),
        pit_rooms=(4, 14),
        bat_rooms=(15, 19),
        arrows=5,
        turn=0,
        alive=True,
        pending_prompt=None,
        pending_arrow_path=(),
    )


def _drive_to_terminal_capture_observations(
    *,
    world: Any,
    actions: tuple[str, ...],
) -> dict[str, Any]:
    """Construct a Game pinned to `world`, attach an InMemorySink, drive
    through `actions`, and return both the captured events and the FINAL
    step's Observation (which carries rendered_lines for the terminal turn)."""
    from wumpus import Game
    from wumpus.sinks import InMemorySink

    game = Game._from_world(world, seed=0)
    sink = InMemorySink()
    game.subscribe(sink)
    pre_count = len(sink.events)
    last_observation = None
    for action in actions:
        last_observation = game.step(action)
    return {
        "game": game,
        "sink": sink,
        "last_observation": last_observation,
        "post_construction_events": sink.events[pre_count:],
    }


# ---------------------------------------------------------------------------
# R1-S07 — Scenario 1: Win message is Yob's swapped HEE HEE HEE text
# ---------------------------------------------------------------------------


@given(
    "the player has just shot the wumpus",
    target_fixture="r1s07_win_state",
)
def _r1s07_win_state() -> dict[str, Any]:
    """Drive shoot path 7->17 against pinned wumpus@17 layout. Yields the
    captured event list + the FINAL observation (which carries the win turn's
    rendered_lines)."""
    return _drive_to_terminal_capture_observations(
        world=_build_win_scenario_world(),
        actions=("S", "2", "7", "17"),
    )


@then("GameEnded(outcome=wumpus_shot, message_kind=win) fires")
def _r1s07_win_game_ended(r1s07_win_state: dict[str, Any]) -> None:
    from wumpus.events import GameEnded

    ended = [
        e
        for e in r1s07_win_state["post_construction_events"]
        if isinstance(e, GameEnded)
    ]
    assert ended, "No GameEnded event emitted after wumpus shot."
    assert ended[0].outcome == "wumpus_shot", (
        f"GameEnded.outcome was {ended[0].outcome!r}; expected 'wumpus_shot'."
    )
    assert ended[0].message_kind == "win", (
        f"GameEnded.message_kind was {ended[0].message_kind!r}; expected 'win'."
    )


@then('the rendered_lines for the win turn contain "AHA! YOU GOT THE WUMPUS!"')
def _r1s07_win_contains_aha(r1s07_win_state: dict[str, Any]) -> None:
    lines = r1s07_win_state["last_observation"].rendered_lines
    assert any("AHA! YOU GOT THE WUMPUS!" in line for line in lines), (
        f"Expected 'AHA! YOU GOT THE WUMPUS!' in rendered_lines on the win turn; "
        f"got: {lines!r}"
    )


@then(
    "the rendered_lines for the win turn contain "
    '"HEE HEE HEE - THE WUMPUS\'LL GETCHA NEXT TIME!!"'
)
def _r1s07_win_contains_hee_hee(r1s07_win_state: dict[str, Any]) -> None:
    lines = r1s07_win_state["last_observation"].rendered_lines
    assert any(
        "HEE HEE HEE - THE WUMPUS'LL GETCHA NEXT TIME!!" in line for line in lines
    ), (
        f"Expected Yob's swapped win tag 'HEE HEE HEE - THE WUMPUS'LL GETCHA "
        f"NEXT TIME!!' in rendered_lines on the win turn; got: {lines!r}"
    )


# ---------------------------------------------------------------------------
# R1-S07 — Scenario 2: Loss message is Yob's swapped HA HA HA text
# ---------------------------------------------------------------------------


@given(
    "the player has just fallen in a pit",
    target_fixture="r1s07_pit_state",
)
def _r1s07_pit_state() -> dict[str, Any]:
    """Drive a single move into a pit room. Yields events + final observation."""
    return _drive_to_terminal_capture_observations(
        world=_build_pit_scenario_world(),
        actions=("move 4",),
    )


@then("GameEnded(outcome=fell_in_pit, message_kind=lose) fires")
def _r1s07_pit_game_ended(r1s07_pit_state: dict[str, Any]) -> None:
    from wumpus.events import GameEnded

    ended = [
        e
        for e in r1s07_pit_state["post_construction_events"]
        if isinstance(e, GameEnded)
    ]
    assert ended, "No GameEnded event emitted after pit fall."
    assert ended[0].outcome == "fell_in_pit", (
        f"GameEnded.outcome was {ended[0].outcome!r}; expected 'fell_in_pit'."
    )
    assert ended[0].message_kind == "lose", (
        f"GameEnded.message_kind was {ended[0].message_kind!r}; expected 'lose'."
    )


@then('the rendered_lines for the loss turn contain "YYYIIIIEEEE . . . FELL IN PIT"')
def _r1s07_loss_contains_pit_reason(r1s07_pit_state: dict[str, Any]) -> None:
    lines = r1s07_pit_state["last_observation"].rendered_lines
    assert any("YYYIIIIEEEE . . . FELL IN PIT" in line for line in lines), (
        f"Expected pit-fall reason 'YYYIIIIEEEE . . . FELL IN PIT' in "
        f"rendered_lines on the loss turn; got: {lines!r}"
    )


@then('the rendered_lines for the loss turn contain "HA HA HA - YOU LOSE!"')
def _r1s07_loss_contains_ha_ha(r1s07_pit_state: dict[str, Any]) -> None:
    lines = r1s07_pit_state["last_observation"].rendered_lines
    assert any("HA HA HA - YOU LOSE!" in line for line in lines), (
        f"Expected Yob's swapped loss tag 'HA HA HA - YOU LOSE!' in "
        f"rendered_lines on the loss turn; got: {lines!r}"
    )


# ---------------------------------------------------------------------------
# R1-S07 — Scenario 3: SAME SET-UP=Y restores the initial layout exactly
# ---------------------------------------------------------------------------


@given(
    "the player has just finished a game with wumpus in 14, pits in 4 and 17, "
    "bats in 5 and 9, start 8",
    target_fixture="r1s07_same_setup_finished_game",
)
def _r1s07_finished_game_for_same_setup() -> dict[str, Any]:
    """Pin the exact layout the scenario specifies, drive the player to a
    terminal state, and return the game + the captured initial layout + the
    captured layout_hash from the original GameStarted event."""
    from wumpus import Game
    from wumpus.events import GameStarted
    from wumpus.sinks import InMemorySink
    from wumpus.types import World

    initial_world = World(
        player_room=8,
        wumpus_rooms=(14,),
        pit_rooms=(4, 17),
        bat_rooms=(5, 9),
        arrows=5,
        turn=0,
        alive=True,
        pending_prompt=None,
        pending_arrow_path=(),
    )
    game = Game._from_world(initial_world, seed=0)
    sink = InMemorySink()
    game.subscribe(sink)

    # Capture the original GameStarted layout_hash + the Game._initial_layout.
    original_started = next(e for e in sink.events if isinstance(e, GameStarted))
    original_layout_hash = original_started.layout_hash
    original_initial_layout = game._initial_layout  # noqa: SLF001 — test-only

    # Drive to a deterministic terminal: shoot self at room 8 via path (1, 8).
    # 8->1 adj (room 8 neighbors {1, 7, 9}), 1->8 adj. Final = 8 = player → self-shot.
    # arrows=5 → 4 after self-shot; game continues; need to deplete arrows.
    # Easier: drive into a pit at room 4 (player at 8 adjacent? 8->{1,7,9} — no).
    # Player at 8 -> move 7 -> 7 neighbors {6, 8, 17}. Pit at 17! Move 7, then 17.
    game.step("move 7")
    game.step("move 17")  # walk into pit at 17 → GameEnded(fell_in_pit)
    return {
        "game": game,
        "sink": sink,
        "original_initial_layout": original_initial_layout,
        "original_layout_hash": original_layout_hash,
    }


@when(
    "the player answers Y to SAME SET-UP (Y-N)?",
    target_fixture="r1s07_same_setup_after_Y",
)
def _r1s07_same_setup_after_Y(
    r1s07_same_setup_finished_game: dict[str, Any],
) -> dict[str, Any]:
    from wumpus.events import GameStarted

    game = r1s07_same_setup_finished_game["game"]
    sink = r1s07_same_setup_finished_game["sink"]
    pre_count = len(sink.events)
    game.step("Y")
    post_events = sink.events[pre_count:]
    new_started = [e for e in post_events if isinstance(e, GameStarted)]
    return {
        "game": game,
        "post_events": post_events,
        "new_started_event": new_started[0] if new_started else None,
    }


@then("a new GameStarted event fires")
def _r1s07_new_game_started_fires(
    r1s07_same_setup_after_Y: dict[str, Any],
) -> None:
    assert r1s07_same_setup_after_Y["new_started_event"] is not None, (
        "Expected a fresh GameStarted event after SAME SET-UP=Y; none emitted. "
        f"Post-Y events: "
        f"{[type(e).__name__ for e in r1s07_same_setup_after_Y['post_events']]}"
    )


@then("the new game's _initial_layout equals the just-finished game's _initial_layout")
def _r1s07_initial_layout_matches(
    r1s07_same_setup_after_Y: dict[str, Any],
    r1s07_same_setup_finished_game: dict[str, Any],
) -> None:
    new_game = r1s07_same_setup_after_Y["game"]
    original = r1s07_same_setup_finished_game["original_initial_layout"]
    restored = new_game._initial_layout  # noqa: SLF001 — test-only
    assert restored == original, (
        f"After SAME SET-UP=Y, _initial_layout was {restored!r}; "
        f"expected the original {original!r}."
    )
    # Also verify the world has been reset to the initial layout (player_room,
    # arrows, alive, turn).
    current_world = new_game.world_state()
    assert current_world.player_room == original.player_room, (
        f"Restored player_room was {current_world.player_room}; expected "
        f"{original.player_room}."
    )
    assert current_world.wumpus_rooms == original.wumpus_rooms
    assert current_world.pit_rooms == original.pit_rooms
    assert current_world.bat_rooms == original.bat_rooms
    assert current_world.arrows == original.arrows, (
        f"Restored arrows was {current_world.arrows}; expected {original.arrows}."
    )
    assert current_world.alive is True, (
        "Restored alive was False; SAME SET-UP=Y must reset alive=True."
    )
    assert current_world.turn == original.turn, (
        f"Restored turn was {current_world.turn}; expected {original.turn} (0)."
    )


@then("the new game's layout_hash equals the just-finished game's layout_hash")
def _r1s07_layout_hash_matches(
    r1s07_same_setup_after_Y: dict[str, Any],
    r1s07_same_setup_finished_game: dict[str, Any],
) -> None:
    new_started = r1s07_same_setup_after_Y["new_started_event"]
    assert new_started is not None, "No fresh GameStarted to compare layout_hash."
    original_hash = r1s07_same_setup_finished_game["original_layout_hash"]
    assert new_started.layout_hash == original_hash, (
        f"New GameStarted.layout_hash was {new_started.layout_hash!r}; "
        f"expected {original_hash!r} (the original layout's hash)."
    )


# ---------------------------------------------------------------------------
# R1-S08 — Instructions block + RAMDOM typo preservation
# ---------------------------------------------------------------------------
#
# Strategy: construct a Game (which now enters pre-game state with
# pending_prompt="instructions"), step("Y") or step("N"), and inspect the
# resulting Observation.rendered_lines for the instructions text + banner.
# The pre-game state machine is the engine's new top-level dispatch: before
# any other action, the engine awaits a Y/N answer at the INSTRUCTIONS
# prompt.
#
# Per SC8 the instructions text + banner live ONLY in wumpus.surfaces.yob;
# the engine emits structured InstructionsShown events that the surface
# translates to rendered lines.


def _build_r1s08_pregame_world() -> Any:
    """Pin a layout for R1-S08 acceptance: hazards parked far from the player
    start so no incidental hazards fire on the first turn. Only the
    instructions + banner + opening turn are exercised."""
    from wumpus.types import World

    return World(
        player_room=1,
        wumpus_rooms=(11,),
        pit_rooms=(13, 14),
        bat_rooms=(15, 19),
        arrows=5,
        turn=0,
        alive=True,
        pending_prompt="instructions",
        pending_arrow_path=(),
    )


def _drive_pregame_with_answer(answer: str) -> tuple[str, ...]:
    """Construct a Game pinned to the R1-S08 pre-game world, attach a sink,
    step the given answer ('Y' or 'N'), and return the concatenated
    rendered_lines emitted across all observations from construction through
    the answer step. The returned tuple represents the "printed output"
    the acceptance scenarios assert on."""
    from wumpus import Game
    from wumpus.sinks import InMemorySink

    game = Game._from_world(_build_r1s08_pregame_world(), seed=0)
    sink = InMemorySink()
    game.subscribe(sink)
    observation = game.step(answer)
    return observation.rendered_lines


# ---------------------------------------------------------------------------
# R1-S08 — Scenario 1: Instructions block contains Yob's RAMDOM typo
# ---------------------------------------------------------------------------


@given(
    'the user answers Y to "INSTRUCTIONS (Y-N)?"',
    target_fixture="r1s08_y_rendered_lines",
)
def _r1s08_y_rendered_lines() -> tuple[str, ...]:
    return _drive_pregame_with_answer("Y")


@then('the printed output contains the exact substring "RAMDOM" exactly once')
def _r1s08_ramdom_appears_exactly_once(
    r1s08_y_rendered_lines: tuple[str, ...],
) -> None:
    full_output = "\n".join(r1s08_y_rendered_lines)
    occurrences = full_output.count("RAMDOM")
    assert occurrences == 1, (
        f"Expected 'RAMDOM' to appear exactly once in the instructions block "
        f"(D11 bug-for-bug); got {occurrences} occurrences. "
        f"Rendered output:\n{full_output}"
    )


@then(
    'the printed output ends with the "HUNT THE WUMPUS" banner '
    "before any game text begins"
)
def _r1s08_banner_after_instructions(
    r1s08_y_rendered_lines: tuple[str, ...],
) -> None:
    # The instructions block lines come first, then the banner.
    # The banner is the EXACT-MATCH line "HUNT THE WUMPUS" — distinct from
    # the instructions' welcome line "WELCOME TO 'HUNT THE WUMPUS'" which
    # also contains the substring. The banner must appear AFTER the RAMDOM
    # line (the canary that lives inside the instructions block).
    banner_indices = [
        i for i, line in enumerate(r1s08_y_rendered_lines) if line == "HUNT THE WUMPUS"
    ]
    assert banner_indices, (
        f"Expected exact 'HUNT THE WUMPUS' banner line in rendered output "
        f"after instructions; got: {r1s08_y_rendered_lines!r}"
    )
    ramdom_indices = [
        i for i, line in enumerate(r1s08_y_rendered_lines) if "RAMDOM" in line
    ]
    assert ramdom_indices, "Sanity: expected RAMDOM line in instructions."
    assert banner_indices[0] > ramdom_indices[0], (
        f"'HUNT THE WUMPUS' banner appeared before the instructions block "
        f"(RAMDOM line). Banner index={banner_indices[0]}, "
        f"RAMDOM index={ramdom_indices[0]}. Order-of-operations violated."
    )


# ---------------------------------------------------------------------------
# R1-S08 — Scenario 2: Answering N skips the instructions
# ---------------------------------------------------------------------------


@given(
    'the user answers N to "INSTRUCTIONS (Y-N)?"',
    target_fixture="r1s08_n_rendered_lines",
)
def _r1s08_n_rendered_lines() -> tuple[str, ...]:
    return _drive_pregame_with_answer("N")


@then('the next printed output contains the "HUNT THE WUMPUS" banner')
def _r1s08_n_banner_present(
    r1s08_n_rendered_lines: tuple[str, ...],
) -> None:
    # Look for the EXACT banner line — not the welcome-instruction substring
    # variant — so the N-path can never be satisfied by a stray instructions
    # line leaking through.
    assert any(line == "HUNT THE WUMPUS" for line in r1s08_n_rendered_lines), (
        f"Expected exact 'HUNT THE WUMPUS' banner line in N-path output; "
        f"got: {r1s08_n_rendered_lines!r}"
    )


@then('the captured output does NOT contain "RAMDOM"')
def _r1s08_n_no_ramdom(
    r1s08_n_rendered_lines: tuple[str, ...],
) -> None:
    full_output = "\n".join(r1s08_n_rendered_lines)
    assert "RAMDOM" not in full_output, (
        f"N-path output unexpectedly contains 'RAMDOM' (instructions should "
        f"have been skipped). Got:\n{full_output}"
    )


# ---------------------------------------------------------------------------
# R1-S09 — CLI subprocess-safe (in-process line-buffering check)
# ---------------------------------------------------------------------------
#
# Strategy: drive `wumpus.cli.main` in-process with StringIO stdin/stdout.
# The pre-game state of `Game(seed=0, cave="yob")` enters
# `pending_prompt="instructions"` and emits a `PromptIssued(instructions)`
# whose surface rendering is the verbatim Yob "INSTRUCTIONS (Y-N)?" line.
# The captured stdout must contain that line BEFORE the CLI loop consumes
# any stdin character — the in-process equivalent of the pexpect "read
# prompt without sending anything first" check.


@given(
    "a CLI invocation with seed 0 and a captured stdout stream",
    target_fixture="r1s09_cli_streams",
)
def _r1s09_cli_streams() -> dict[str, Any]:
    import io

    return {"stdin": io.StringIO("N\n"), "stdout": io.StringIO()}


@when('the CLI loop runs with a stdin that answers "N" to the instructions prompt')
def _r1s09_run_cli(r1s09_cli_streams: dict[str, Any]) -> None:
    from wumpus import cli

    cli.main(
        argv=["--seed", "0"],
        stdin=r1s09_cli_streams["stdin"],
        stdout=r1s09_cli_streams["stdout"],
    )


@then(
    'the captured stdout contains "INSTRUCTIONS (Y-N)?" '
    "as a complete newline-terminated line"
)
def _r1s09_prompt_visible_as_complete_line(
    r1s09_cli_streams: dict[str, Any],
) -> None:
    output: str = r1s09_cli_streams["stdout"].getvalue()
    # The prompt must appear as a full line — i.e. text + newline. A bare
    # write with no newline can sit in the underlying line-buffered stdio
    # and create the exact deadlock SC3 forbids.
    assert "INSTRUCTIONS (Y-N)?\n" in output, (
        f"Expected the INSTRUCTIONS prompt as a newline-terminated line "
        f"on captured stdout (SC3 line-buffering). Got: {output!r}"
    )


@then("the prompt line appears before any further game text")
def _r1s09_prompt_before_other_text(
    r1s09_cli_streams: dict[str, Any],
) -> None:
    output: str = r1s09_cli_streams["stdout"].getvalue()
    prompt_index = output.find("INSTRUCTIONS (Y-N)?")
    banner_index = output.find("HUNT THE WUMPUS")
    assert prompt_index >= 0, "INSTRUCTIONS prompt missing from output."
    # The banner is what fires AFTER the player answers N (i.e. after the
    # CLI consumed input). The prompt MUST precede the banner; if it
    # doesn't, the loop emitted the banner before the prompt was flushed —
    # the exact ordering bug SC3 forbids.
    if banner_index >= 0:
        assert prompt_index < banner_index, (
            f"INSTRUCTIONS prompt appeared at {prompt_index} after banner at "
            f"{banner_index}; prompt must be flushed BEFORE input is read."
        )


# ---------------------------------------------------------------------------
# R1-S02-render — Per-turn rendered output (sense lines + location/tunnels)
# ---------------------------------------------------------------------------
#
# R4-S03 deferred wiring SenseEmitted / LocationReported through the surface
# into Observation.rendered_lines. These scenarios assert that a successful
# move's Observation now carries the player-facing per-turn lines, in Yob's
# order and spacing: senses (in SENSE_ORDER) then "YOU ARE IN ROOM  <n>" then
# "TUNNELS LEAD TO  <a>  <b>  <c>" (double spaces deliberate).
#
# Strategy mirrors R1-S02's event-stream scenarios: pin a layout via
# `Game._from_world`, drive the player into the target room with a single
# `step("move N")`, and read the returned Observation.rendered_lines (the
# per-turn render the CLI / harness shows the player).


def _render_lines_for_move(
    *,
    player_start: int,
    target_room: int,
    wumpus_rooms: tuple[int, ...],
    pit_rooms: tuple[int, ...],
    bat_rooms: tuple[int, ...],
) -> tuple[str, ...]:
    """Construct a Game pinned to the given layout, step the player into the
    target room, and return the Observation.rendered_lines for that turn."""
    from wumpus import Game

    world = _build_world_for_r1s02(
        player_room=player_start,
        wumpus_rooms=wumpus_rooms,
        pit_rooms=pit_rooms,
        bat_rooms=bat_rooms,
    )
    game = Game._from_world(world, seed=0)
    observation = game.step(f"move {target_room}")
    return tuple(observation.rendered_lines)


@given(
    "the player moves into room 2 (neighbors 1, 3, 10) with no adjacent hazards",
    target_fixture="r1s02render_safe_lines",
)
def _r1s02render_safe_room_lines() -> tuple[str, ...]:
    # Room 2 neighbors {1, 3, 10}. Park every hazard far away (mirrors the
    # R1-S02 "no adjacent hazard" layout): wumpus@20, pits@15/6, bats@11/12.
    # Player starts at room 1 (neighbor of 2) and moves to room 2.
    return _render_lines_for_move(
        player_start=1,
        target_room=2,
        wumpus_rooms=(20,),
        pit_rooms=(15, 6),
        bat_rooms=(11, 12),
    )


@then('the rendered_lines for that turn contain "YOU ARE IN ROOM  2"')
def _r1s02render_safe_contains_location(
    r1s02render_safe_lines: tuple[str, ...],
) -> None:
    assert "YOU ARE IN ROOM  2" in r1s02render_safe_lines, (
        f"Expected the verbatim Yob location line 'YOU ARE IN ROOM  2' (two "
        f"spaces before the room number) in rendered_lines; got: "
        f"{r1s02render_safe_lines!r}"
    )


@then('the rendered_lines for that turn contain "TUNNELS LEAD TO  1  3  10"')
def _r1s02render_safe_contains_tunnels(
    r1s02render_safe_lines: tuple[str, ...],
) -> None:
    assert "TUNNELS LEAD TO  1  3  10" in r1s02render_safe_lines, (
        f"Expected the verbatim Yob tunnels line 'TUNNELS LEAD TO  1  3  10' "
        f"(double spaces, sorted neighbors of room 2) in rendered_lines; got: "
        f"{r1s02render_safe_lines!r}"
    )


@then("no sense line precedes the location line")
def _r1s02render_safe_no_sense(
    r1s02render_safe_lines: tuple[str, ...],
) -> None:
    # Room 2 has no adjacent hazards, so none of Yob's sense lines may appear
    # before the location line.
    sense_lines = {"I SMELL A WUMPUS!", "I FEEL A DRAFT", "BATS NEARBY!"}
    leaked = [line for line in r1s02render_safe_lines if line in sense_lines]
    assert leaked == [], (
        f"Expected zero sense lines for a hazard-free room; got {leaked!r} in "
        f"{r1s02render_safe_lines!r}"
    )


@given(
    "the player moves into room 1 (neighbors 2, 5, 8) adjacent to a wumpus and a pit",
    target_fixture="r1s02render_mixed_lines",
)
def _r1s02render_mixed_room_lines() -> tuple[str, ...]:
    # Room 1 neighbors {2, 5, 8}. Wumpus@2, pit@5, second pit parked away
    # (room 11). Bats parked at 14/17. Player starts at 8 and moves to 1.
    # Mirrors the R1-S02 "adjacent to wumpus AND pit" layout so the senses
    # fire in SENSE_ORDER (wumpus, then pit).
    return _render_lines_for_move(
        player_start=8,
        target_room=1,
        wumpus_rooms=(2,),
        pit_rooms=(5, 11),
        bat_rooms=(14, 17),
    )


@then(
    'the rendered_lines for that turn are exactly "I SMELL A WUMPUS!", '
    '"I FEEL A DRAFT", "YOU ARE IN ROOM  1", "TUNNELS LEAD TO  2  5  8"'
)
def _r1s02render_mixed_exact_order(
    r1s02render_mixed_lines: tuple[str, ...],
) -> None:
    expected = (
        "I SMELL A WUMPUS!",
        "I FEEL A DRAFT",
        "YOU ARE IN ROOM  1",
        "TUNNELS LEAD TO  2  5  8",
    )
    assert r1s02render_mixed_lines == expected, (
        f"Expected the per-turn render to be senses (SENSE_ORDER: wumpus then "
        f"pit) followed by location then tunnels, in Yob's spacing; got: "
        f"{r1s02render_mixed_lines!r}"
    )
