"""R3 snapshot acceptance step definitions (R3-S01).

R3-S01 ships the in-memory snapshot/restore round-trip + the mid-prompt
state coverage. The 1000-trial property test lands as
`tests/property/test_snapshot.py` (NOT as a BDD scenario, mirroring
R2-S03's K-2 hypothesis test convention).

Per pytest-bdd convention:
  - `scenarios(...)` at module top-level binds the .feature scenarios to this
    module.
  - Step functions decorated with @given / @when / @then implement each step.

Per the crafter mandate: port-to-port testing — these tests enter through
driving ports (Game(...), Game.snapshot(), Game.from_snapshot(...)) and
assert on observable outcomes (events, World fields, PromptIssued context).
They do not introspect private internals beyond what the public Snapshot
dataclass exposes.
"""

from __future__ import annotations

from typing import Any

from pytest_bdd import given, scenarios, then, when

from wumpus import Game
from wumpus.events import PromptIssued
from wumpus.sinks import InMemorySink

# Bind the .feature file. Path is relative to this step-defs file's parent.
scenarios("../features/R3_snapshot.feature")


# ---------------------------------------------------------------------------
# Scenario 1 — Snapshot round-trip preserves next event byte-identically
# ---------------------------------------------------------------------------


@given(
    'Game(seed=42, cave="toy") is stepped through actions ["move 2", "move 3"]',
    target_fixture="r3s01_baseline_game",
)
def _r3s01_baseline_game() -> dict[str, Any]:
    """Build the baseline single-process Game and record events for each
    action. We pin both the per-action event slices (so scenario step 3 can
    compare action-2 events on the restored vs. baseline) AND the
    after-action-1 snapshot (so scenario step 2 can resurrect from it).
    """
    game = Game(seed=42, cave="toy")
    pre_action_1_count = len(game._debug_events)
    game.step("move 2")
    snap_after_action_1 = game.snapshot()
    pre_action_2_count = len(game._debug_events)
    game.step("move 3")
    final_event_count = len(game._debug_events)

    action_2_events = list(game._debug_events[pre_action_2_count:final_event_count])

    return {
        "snap_after_action_1": snap_after_action_1,
        "action_2_events_baseline": action_2_events,
        "pre_action_1_count": pre_action_1_count,
    }


@given("the snapshot is taken after action 1: snap = game.snapshot()")
def _r3s01_snap_taken(r3s01_baseline_game: dict[str, Any]) -> None:
    """Grammar requirement — the snapshot is already taken in the setup."""
    assert r3s01_baseline_game["snap_after_action_1"] is not None


@when(
    'Game.from_snapshot(snap) is constructed and stepped through action 2 ("move 3")',
    target_fixture="r3s01_restored_action_2_events",
)
def _r3s01_restore_and_step(r3s01_baseline_game: dict[str, Any]) -> list[Any]:
    """Resurrect the Game from the snapshot and step through action 2.

    `from_snapshot` re-emits a GameStarted (and, for mid-prompt snapshots, a
    PromptIssued); those events are NOT part of action 2's event stream
    in the single-process baseline. Capture only the events emitted by the
    `step("move 3")` call itself by snapshotting the debug-event count
    BEFORE the step and slicing the tail.
    """
    restored = Game.from_snapshot(r3s01_baseline_game["snap_after_action_1"])
    pre_step_count = len(restored._debug_events)
    restored.step("move 3")
    return list(restored._debug_events[pre_step_count:])


@when("the same Game(seed=42) is stepped through both actions in one process")
def _r3s01_single_process_pre_recorded(r3s01_baseline_game: dict[str, Any]) -> None:
    """Grammar requirement — the single-process baseline already ran in the
    setup. The setup pre-recorded the action-2 event slice for comparison."""
    assert r3s01_baseline_game["action_2_events_baseline"]


@then(
    "the events from the restored Game's action 2 step equal the single-process Game's action 2 step events byte-for-byte"
)
def _r3s01_event_equality(
    r3s01_baseline_game: dict[str, Any],
    r3s01_restored_action_2_events: list[Any],
) -> None:
    baseline = r3s01_baseline_game["action_2_events_baseline"]
    restored = r3s01_restored_action_2_events
    assert restored == baseline, (
        f"Action-2 event slice differs between restored Game and single-process "
        f"Game.\n  restored ({len(restored)} events): {restored!r}\n"
        f"  baseline ({len(baseline)} events): {baseline!r}"
    )


# ---------------------------------------------------------------------------
# Scenario 2 — Snapshot covers mid-prompt state (pending_arrow_path)
# ---------------------------------------------------------------------------


@given(
    'a session in mid-shoot with pending_arrow_path=[7, 14] and pending_path_length=3 and pending_prompt="shoot_path_room" (slot 3 awaited)',
    target_fixture="r3s01_mid_shoot_game",
)
def _r3s01_mid_shoot_game() -> Game:
    """Drive a Yob-cave Game to mid-shoot state awaiting slot 3 of a 3-slot
    path: instructions=N -> S -> 3 -> 7 -> 14. The engine parks in
    pending_prompt='shoot_path_room' with pending_arrow_path=(7, 14) and
    pending_path_length=3, awaiting the third ROOM #? entry.
    """
    game = Game(seed=42)  # default cave="yob"
    # Acknowledge the pre-game INSTRUCTIONS prompt (N — skip instructions).
    game.step("N")
    # Enter shoot mode + commit a 3-slot path length, then enter slots 1 + 2.
    game.step("S")
    game.step("3")  # NO. OF ROOMS = 3
    game.step("7")  # slot 1
    game.step("14")  # slot 2
    # Verify the engine is parked at slot 3, awaiting input.
    world = game.world_state()
    assert world.pending_prompt == "shoot_path_room", (
        f"Expected pending_prompt='shoot_path_room'; got {world.pending_prompt!r}"
    )
    assert world.pending_arrow_path == (7, 14), (
        f"Expected pending_arrow_path=(7, 14); got {world.pending_arrow_path!r}"
    )
    assert world.pending_path_length == 3, (
        f"Expected pending_path_length=3; got {world.pending_path_length!r}"
    )
    return game


@when(
    "game.snapshot() is taken and Game.from_snapshot(snap) is constructed",
    target_fixture="r3s01_resurrected_mid_shoot",
)
def _r3s01_resurrect_mid_shoot(r3s01_mid_shoot_game: Game) -> Game:
    snap = r3s01_mid_shoot_game.snapshot()
    return Game.from_snapshot(snap)


@then("the resurrected game's world has pending_arrow_path=[7, 14]")
def _r3s01_pending_arrow_path(r3s01_resurrected_mid_shoot: Game) -> None:
    world = r3s01_resurrected_mid_shoot.world_state()
    assert world.pending_arrow_path == (7, 14), (
        f"Resurrected pending_arrow_path: {world.pending_arrow_path!r}; "
        f"expected (7, 14). Snapshot did NOT round-trip mid-shoot state."
    )


@then("the resurrected game's world has pending_path_length=3")
def _r3s01_pending_path_length(r3s01_resurrected_mid_shoot: Game) -> None:
    world = r3s01_resurrected_mid_shoot.world_state()
    assert world.pending_path_length == 3, (
        f"Resurrected pending_path_length: {world.pending_path_length!r}; expected 3."
    )


@then("the resurrected game prompts for ROOM #? at slot 3 on next step")
def _r3s01_next_prompt_is_slot_3(r3s01_resurrected_mid_shoot: Game) -> None:
    """The resurrected game replays its history on subscribe; the last
    PromptIssued emitted by `from_snapshot` must mention slot 3 + total 3.

    We assert by subscribing a fresh InMemorySink and checking the last
    PromptIssued in the replayed history.
    """
    sink = InMemorySink()
    r3s01_resurrected_mid_shoot.subscribe(sink)
    prompts = [e for e in sink.events if isinstance(e, PromptIssued)]
    assert prompts, (
        "Resurrected mid-shoot Game replayed no PromptIssued events. "
        "The snapshot/restore path must re-emit the awaiting prompt so a "
        "downstream renderer/agent knows what input is required."
    )
    last_prompt = prompts[-1]
    assert last_prompt.kind == "shoot_path_room", (
        f"Last PromptIssued kind: {last_prompt.kind!r}; expected 'shoot_path_room'."
    )
    assert last_prompt.context == {"slot": 3, "of": 3}, (
        f"Last PromptIssued context: {last_prompt.context!r}; "
        f"expected {{'slot': 3, 'of': 3}}."
    )
