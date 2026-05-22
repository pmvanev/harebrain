"""R0 walking-skeleton step definitions.

Each scenario in the R0_walking_skeleton.feature has matching step functions here.
At DISTILL-wave-complete time, these step definitions are SYNTACTICALLY VALID
and PYTEST-DISCOVERABLE, but they will FAIL FOR BUSINESS REASONS when run:

  - `from wumpus import Game` raises ImportError because DELIVER hasn't built it yet
  - That's the Outside-In TDD "red" state — DELIVER's R0 slice makes these green

Per pytest-bdd convention:
  - `scenarios(...)` at module top-level binds the .feature scenarios to this module
  - Step functions decorated with @given / @when / @then implement each step
  - Step functions use `target_fixture=` to expose state to subsequent steps
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, scenarios, then, when

# Bind the .feature file. Path is relative to this step-defs file's parent.
scenarios("../features/R0_walking_skeleton.feature")


# ---------------------------------------------------------------------------
# Background steps
# ---------------------------------------------------------------------------


@given("the engine uses a 3-room linear cave with one wumpus")
def _background_toy_cave():
    """R0 fixture: hardcoded 3-room linear cave (NOT the dodecahedron — that's R1-S01).

    The toy cave's adjacency:
        room 1 <-> room 2 <-> room 3
        wumpus in room 3 (or wherever the canonical R0 fixture pins it)
        player starts in room 1.

    DELIVER's R0 slice implements this in wumpus.engine._r0_toy_cave or similar.
    """
    # No-op at DISTILL time; the actual cave is constructed when Game() is called.
    return None


@given("no module-level mutable state has been initialized in wumpus.engine")
def _background_no_module_state():
    """SC7 invariant precondition. Verified by the R3-S03 audit; here it's
    asserted as a precondition the test relies on. At DISTILL-time this is
    trivially true (no engine code exists yet).
    """
    # Lazy: defer the real check to the R3-S03 module-state audit script.
    # At R0 we trust SC7 is upheld by construction.
    return None


# ---------------------------------------------------------------------------
# Scenario 1: Deterministic-from-seed event sequence
# ---------------------------------------------------------------------------


@given(
    "two independent Game(seed=42) instances",
    target_fixture="paired_games",
)
def _two_independent_games(make_game) -> dict[str, Any]:
    """Construct two Game instances with the same seed. They should be
    observationally equivalent throughout their lives (SC1)."""
    g1 = make_game(seed=42)
    g2 = make_game(seed=42)
    return {"g1": g1, "g2": g2, "events1": [], "events2": []}


@given(
    'both will run the action sequence ["move 2", "move 3"]',
    target_fixture="action_sequence",
)
def _action_sequence() -> list[str]:
    """The canonical R0 action sequence. Two move actions; no shoot, no hazards
    triggered. Should produce a deterministic event sequence."""
    return ["move 2", "move 3"]


@when("both instances execute the action sequence to completion")
def _execute_paired_runs(paired_games: dict[str, Any], action_sequence: list[str]) -> None:
    """Drive both Games through the action sequence, collecting their events.

    At DISTILL-time, paired_games['g1'].step doesn't exist yet — this will
    AttributeError or fail at the `from wumpus import Game` import in conftest.
    DELIVER R0 makes this work.
    """
    from wumpus.sinks import InMemorySink  # ImportError at DISTILL-time

    sink1 = InMemorySink()
    sink2 = InMemorySink()
    paired_games["g1"].subscribe(sink1)
    paired_games["g2"].subscribe(sink2)
    for action in action_sequence:
        paired_games["g1"].step(action)
        paired_games["g2"].step(action)
    paired_games["events1"] = sink1.events
    paired_games["events2"] = sink2.events


@then("both produce equal event sequences (deep equality)")
def _events_equal_deep(paired_games: dict[str, Any]) -> None:
    """The structural invariant. SC1 determinism contract."""
    assert paired_games["events1"] == paired_games["events2"], (
        "Paired Game(seed=42) instances produced different event sequences. "
        "SC1 (determinism) violated."
    )


@then("both produce equal final Snapshots")
def _snapshots_equal(paired_games: dict[str, Any]) -> None:
    """Final-state equality — equivalent to event-sequence equality but
    asserted separately to catch snapshot-reconstruction bugs that wouldn't
    show in event diff."""
    snap1 = paired_games["g1"].snapshot()
    snap2 = paired_games["g2"].snapshot()
    assert snap1 == snap2, "Final Snapshots from paired runs differ. SC1 violated."


@then("neither instance has any module-level side effect on the engine package")
def _no_module_side_effect() -> None:
    """SC7 — no module-level mutable state in the engine package.

    At DISTILL-time this defers to the R3-S03 audit script. Here we sanity-check
    that the wumpus package's known-mutable-state markers (None at R0) are unchanged.
    The full audit happens out-of-band; this step's job is to assert what's checkable
    in a unit-style test.
    """
    import wumpus

    # If wumpus.engine module exists, walk its globals looking for mutable containers.
    # At R0 this is structural; at R3-S03 the full audit script provides the real check.
    if hasattr(wumpus, "engine"):
        for name in dir(wumpus.engine):  # type: ignore[attr-defined]
            if name.startswith("_"):
                continue
            obj = getattr(wumpus.engine, name)  # type: ignore[attr-defined]
            assert not isinstance(obj, (list, dict, set)), (
                f"wumpus.engine.{name} is a module-level mutable container. "
                f"SC7 violated."
            )


# ---------------------------------------------------------------------------
# Scenario 2: In-memory sink does not change emission
# ---------------------------------------------------------------------------


@given(
    'a Game(seed=42) running the action sequence ["move 2", "move 3"]',
    target_fixture="game_and_actions",
)
def _game_and_actions(make_game) -> dict[str, Any]:
    return {"action_sequence": ["move 2", "move 3"], "make_game": make_game}


@when(
    "the run is performed once with no sinks attached",
    target_fixture="no_sink_events",
)
def _run_no_sink(game_and_actions: dict[str, Any]) -> list[Any]:
    """Run the canonical action sequence without any sink subscribed.

    The engine still emits events internally — they're just not delivered to any
    consumer. We assert against the internal emission via a backdoor: the engine
    exposes a `_debug_events` list or similar. R0 DELIVER picks the exact API.
    """
    g = game_and_actions["make_game"](seed=42)
    for action in game_and_actions["action_sequence"]:
        g.step(action)
    # R0 DELIVER decides whether `_debug_events` is real or whether this test
    # uses a different mechanism (e.g., always-attached implicit in-memory sink).
    return g._debug_events  # type: ignore[no-any-return]


@when(
    "the run is performed once with an InMemorySink attached",
    target_fixture="sink_events",
)
def _run_with_sink(game_and_actions: dict[str, Any], in_memory_sink_factory) -> list[Any]:
    g = game_and_actions["make_game"](seed=42)
    sink = in_memory_sink_factory()
    g.subscribe(sink)
    for action in game_and_actions["action_sequence"]:
        g.step(action)
    return sink.events


@then("the in-engine event sequences emitted are identical between the two runs")
def _emission_unchanged(no_sink_events: list[Any], sink_events: list[Any]) -> None:
    """The observer-effect-absent claim. CC-AC-1 + SC4."""
    assert no_sink_events == sink_events, (
        "Attaching a sink changed the engine's event emission sequence. "
        "SC4 (sink is downstream of emission) violated."
    )


@then("the in-memory sink's recorded events equal the engine's internal emission order")
def _sink_order_matches(no_sink_events: list[Any], sink_events: list[Any]) -> None:
    """Sinks observe in engine-emission order; no reordering."""
    assert sink_events == no_sink_events, (
        "InMemorySink recorded events in different order than engine emission. "
        "SC4 (sink ordering) violated."
    )


# ---------------------------------------------------------------------------
# Scenario 3: Game.world_state() exposes full internal state without mutation
# ---------------------------------------------------------------------------


@given(
    "a Game(seed=42) instance in any state",
    target_fixture="game_for_inspection",
)
def _game_for_inspection(make_game):
    return make_game(seed=42)


@when(
    "Game.world_state() is called twice in succession",
    target_fixture="world_state_results",
)
def _call_world_state_twice(game_for_inspection) -> dict[str, Any]:
    """Capture world_state() output + the engine's internal state before/after
    to verify no mutation."""
    # Capture rng_cursor before, world_state twice, rng_cursor after.
    # If world_state advances the cursor, the before/after will differ.
    before_cursor = game_for_inspection.snapshot().rng_cursor
    ws1 = game_for_inspection.world_state()
    ws2 = game_for_inspection.world_state()
    after_cursor = game_for_inspection.snapshot().rng_cursor
    return {
        "ws1": ws1,
        "ws2": ws2,
        "before_cursor": before_cursor,
        "after_cursor": after_cursor,
    }


@then("both calls return structurally equal world states")
def _world_states_equal(world_state_results: dict[str, Any]) -> None:
    assert world_state_results["ws1"] == world_state_results["ws2"], (
        "Two consecutive Game.world_state() calls returned different structures. "
        "Goal 5.2 inspection-API contract violated."
    )


@then("neither call advances the engine's RNG cursor")
def _rng_cursor_unchanged(world_state_results: dict[str, Any]) -> None:
    assert world_state_results["before_cursor"] == world_state_results["after_cursor"], (
        "Game.world_state() advanced the RNG cursor. "
        "Goal 5.2 'API is inspectable' implies side-effect-free reads; SC1 also at risk."
    )


@then("neither call emits any event to attached sinks")
def _no_emission_on_inspection(game_for_inspection, in_memory_sink_factory) -> None:
    """Inspection doesn't emit. Sink count before + after should be equal."""
    sink = in_memory_sink_factory()
    game_for_inspection.subscribe(sink)
    events_before = len(sink.events)
    game_for_inspection.world_state()
    game_for_inspection.world_state()
    events_after = len(sink.events)
    assert events_before == events_after, (
        "Game.world_state() emitted events to attached sinks. "
        "Goal 5.2 'API is inspectable' contract violated."
    )


@then(
    "the returned world state contains the player room, wumpus room, arrow count, "
    "alive/dead flag, turn counter, pending_prompt, and pending_arrow_path"
)
def _world_state_fields(world_state_results: dict[str, Any]) -> None:
    """The full-state-export contract. world_state() returns a structured object
    (likely the same World dataclass that Game._world holds, or a read-only view)."""
    ws = world_state_results["ws1"]
    required_fields = (
        "player_room",
        "wumpus_rooms",
        "arrows",
        "alive",
        "turn",
        "pending_prompt",
        "pending_arrow_path",
    )
    for field in required_fields:
        assert hasattr(ws, field), (
            f"Game.world_state() return value is missing required field: {field}. "
            f"Tier A1 World contract violated."
        )
