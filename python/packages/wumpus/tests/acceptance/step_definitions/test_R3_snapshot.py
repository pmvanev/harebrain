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

import base64
import random
import subprocess
import sys
from dataclasses import fields, is_dataclass
from typing import Any

from pytest_bdd import given, scenarios, then, when

from wumpus import Game
from wumpus.events import (
    Event,
    GameEnded,
    PlayerTeleported,
    PromptIssued,
    WumpusStartled,
)
from wumpus.serialization import snapshot_from_json, snapshot_to_json
from wumpus.sinks import InMemorySink
from wumpus.types import World

# Bind the .feature file. Path is relative to this step-defs file's parent.
scenarios("../features/R3_snapshot.feature")


# ---------------------------------------------------------------------------
# R3-S02 shared helpers. The CANONICAL 6-fixture suite + the subprocess proof
# live in `tests/audits/test_snapshot_serializability.py` (the path audits.yml
# runs). The test tree has no importable top-level `tests` package (only leaf
# __init__ markers), so the BDD scenarios re-state a representative subset of
# the same fixtures here through the public `Game` driving port — they are a
# thin acceptance-layer wrapper, not the audit-gate's source of truth.
# ---------------------------------------------------------------------------


def _base_world(**overrides: Any) -> World:
    payload: dict[str, Any] = dict(
        player_room=1,
        wumpus_rooms=(13,),
        pit_rooms=(7, 8),
        bat_rooms=(15, 16),
        arrows=5,
        turn=0,
        alive=True,
        pending_prompt=None,
        pending_arrow_path=(),
        pending_path_length=None,
    )
    payload.update(overrides)
    return World(**payload)


def _script_randint(game: Game, values: list[int]) -> None:
    sequence = iter(values)
    game._random.randint = lambda a, b: next(sequence)  # type: ignore[method-assign]


def _step_events(game: Game, action: str) -> list[Event]:
    pre_count = len(game._debug_events)
    game.step(action)
    return list(game._debug_events[pre_count:])


def _build_turn_0() -> tuple[Game, str]:
    game = Game(seed=42)
    game.step("N")
    return game, "move 99"


def _build_mid_arrow_path() -> tuple[Game, str]:
    game = Game(seed=42)
    game.step("N")
    game.step("S")
    game.step("3")
    game.step("7")
    game.step("14")
    return game, "12"


def _build_post_bat_teleport() -> tuple[Game, str]:
    game = Game._from_world(_base_world(player_room=14), seed=0)
    _script_randint(game, [5])
    game.step("move 15")
    assert any(isinstance(e, PlayerTeleported) for e in game._debug_events)
    return game, "move 99"


def _build_post_startle() -> tuple[Game, str]:
    game = Game._from_world(_base_world(player_room=12), seed=0)
    _script_randint(game, [1])
    game.step("move 13")
    startles = [e for e in game._debug_events if isinstance(e, WumpusStartled)]
    assert startles and not startles[-1].ate_player
    return game, "move 99"


def _build_terminal_win() -> tuple[Game, str]:
    game = Game._from_world(_base_world(player_room=1, wumpus_rooms=(2,)), seed=0)
    game.step("S")
    game.step("1")
    game.step("2")
    ended = [e for e in game._debug_events if isinstance(e, GameEnded)]
    assert ended and ended[-1].outcome == "wumpus_shot"
    return game, "X"


def _build_terminal_lose() -> tuple[Game, str]:
    game = Game._from_world(_base_world(player_room=1, pit_rooms=(8, 7)), seed=0)
    game.step("move 8")
    ended = [e for e in game._debug_events if isinstance(e, GameEnded)]
    assert ended and ended[-1].outcome == "fell_in_pit"
    return game, "move 99"


_FIXTURE_BUILDERS = {
    "turn-0": _build_turn_0,
    "mid-arrow-path": _build_mid_arrow_path,
    "post-bat-teleport": _build_post_bat_teleport,
    "post-startle": _build_post_startle,
    "terminal-win": _build_terminal_win,
    "terminal-lose": _build_terminal_lose,
}


# Child program for the cross-process scenario — mirrors the audit suite's
# _CHILD_PROGRAM. Reads a snapshot JSON path + action from argv, reconstructs
# the Game, steps once, prints the emitted event slice on a marker line.
_CHILD_PROGRAM = r"""
import sys
from wumpus.engine.game import Game
from wumpus.serialization import snapshot_from_json

with open(sys.argv[1], encoding="utf-8") as handle:
    game = Game.from_snapshot(snapshot_from_json(handle.read()))
pre_count = len(game._debug_events)
game.step(sys.argv[2])
sys.stdout.write("WUMPUS_P2_EVENTS:" + repr(game._debug_events[pre_count:]))
"""


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


# ---------------------------------------------------------------------------
# Scenario 3 (R3-S02) — Six fixture snapshots round-trip through JSON
# byte-identically. The canonical fixture suite lives in
# tests/audits/test_snapshot_serializability.py; this scenario does a
# representative round-trip over all six builders inline.
# ---------------------------------------------------------------------------


@given(
    "the six canonical snapshot fixtures (turn-0, mid-arrow-path, "
    "post-bat-teleport, post-startle, terminal-win, terminal-lose)",
    target_fixture="r3s02_fixture_snapshots",
)
def _r3s02_fixture_snapshots() -> dict[str, Any]:
    """Build each of the six canonical fixtures; record the in-memory
    Snapshot + the deterministic next action used for the step-equivalence
    half of the AC."""
    built: dict[str, Any] = {}
    for fixture_id, builder in _FIXTURE_BUILDERS.items():
        game, action = builder()
        built[fixture_id] = {"snapshot": game.snapshot(), "action": action}
    return built


@when(
    "each is serialized to JSON and deserialized back",
    target_fixture="r3s02_round_tripped",
)
def _r3s02_round_trip(r3s02_fixture_snapshots: dict[str, Any]) -> dict[str, Any]:
    round_tripped: dict[str, Any] = {}
    for fixture_id, payload in r3s02_fixture_snapshots.items():
        snap = payload["snapshot"]
        round_tripped[fixture_id] = snapshot_from_json(snapshot_to_json(snap))
    return round_tripped


@then(
    "each round-tripped snapshot equals the original (deep equality "
    "including rng_cursor and initial_layout)"
)
def _r3s02_round_trip_equal(
    r3s02_fixture_snapshots: dict[str, Any],
    r3s02_round_tripped: dict[str, Any],
) -> None:
    for fixture_id, payload in r3s02_fixture_snapshots.items():
        original = payload["snapshot"]
        restored = r3s02_round_tripped[fixture_id]
        assert restored == original, (
            f"[{fixture_id}] JSON round-trip not byte-identical.\n"
            f"  original: {original!r}\n  restored: {restored!r}"
        )


@then(
    "a step against the round-tripped snapshot produces the same event "
    "as a step against the in-memory snapshot"
)
def _r3s02_step_equivalence(r3s02_fixture_snapshots: dict[str, Any]) -> None:
    for fixture_id, payload in r3s02_fixture_snapshots.items():
        snap = payload["snapshot"]
        action = payload["action"]
        in_memory = Game.from_snapshot(snap)
        json_restored = Game.from_snapshot(snapshot_from_json(snapshot_to_json(snap)))
        in_memory_events = _step_events(in_memory, action)
        json_events = _step_events(json_restored, action)
        assert json_events == in_memory_events, (
            f"[{fixture_id}] step events diverged between JSON-restored and "
            f"in-memory snapshot.\n  in-memory: {in_memory_events!r}\n"
            f"  json: {json_events!r}"
        )


# ---------------------------------------------------------------------------
# Scenario 4 (R3-S02) — Snapshot holds no live RNG object.
# ---------------------------------------------------------------------------


def _walk_dataclass_values(value: Any) -> list[Any]:
    """Recursively yield every nested value reachable from `value` through
    dataclass fields, tuples, lists, and dict values."""
    found: list[Any] = [value]
    if is_dataclass(value) and not isinstance(value, type):
        for f in fields(value):
            found.extend(_walk_dataclass_values(getattr(value, f.name)))
    elif isinstance(value, (tuple, list)):
        for item in value:
            found.extend(_walk_dataclass_values(item))
    elif isinstance(value, dict):
        for item in value.values():
            found.extend(_walk_dataclass_values(item))
    return found


@given("any Snapshot instance", target_fixture="r3s02_any_snapshot")
def _r3s02_any_snapshot() -> Any:
    """A representative Snapshot — the turn-0 fixture suffices; the recursive
    introspection claim holds for any instance regardless of corner."""
    game, _action = _FIXTURE_BUILDERS["turn-0"]()
    return game.snapshot()


@then("no field (recursively) holds a random.Random instance")
def _r3s02_no_live_rng(r3s02_any_snapshot: Any) -> None:
    for nested in _walk_dataclass_values(r3s02_any_snapshot):
        assert not isinstance(nested, random.Random), (
            "Snapshot graph holds a live random.Random instance — SC6 "
            "forbids it (the RNG must be encoded)."
        )


@then("the rng_cursor field is a base64-encoded string")
def _r3s02_rng_cursor_base64(r3s02_any_snapshot: Any) -> None:
    cursor = r3s02_any_snapshot.rng_cursor
    assert isinstance(cursor, str), (
        f"rng_cursor must be a str (base64 per ADR-007); got {type(cursor).__name__}."
    )
    # Round-trips through base64 — proves it is the encoded RNG state.
    base64.b64decode(cursor.encode("ascii"))


# ---------------------------------------------------------------------------
# Scenario 5 (R3-S02) — Cross-process JSON round-trip preserves the next
# event. The representative cross-process proof; the full subprocess proof
# (real sys.executable spawn) lives in the audit suite.
# ---------------------------------------------------------------------------


@given(
    "Game(seed=42) snapshotted after a sequence of actions, written to a "
    "temp JSON file",
    target_fixture="r3s02_cross_process",
)
def _r3s02_cross_process(tmp_path: Any) -> dict[str, Any]:
    game = Game(seed=42)
    game.step("N")
    for action in ("move 99", "move 99"):
        game.step(action)
    snap = game.snapshot()
    snapshot_file = tmp_path / "snap.json"
    snapshot_file.write_text(snapshot_to_json(snap), encoding="utf-8")
    return {"snapshot_file": snapshot_file, "next_action": "move 99"}


@when(
    "a separate Python process reads the JSON, reconstructs the Game, and "
    "steps once",
    target_fixture="r3s02_subprocess_events",
)
def _r3s02_run_subprocess(r3s02_cross_process: dict[str, Any]) -> str:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            _CHILD_PROGRAM,
            str(r3s02_cross_process["snapshot_file"]),
            r3s02_cross_process["next_action"],
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, (
        f"Subprocess failed (rc={completed.returncode}).\n"
        f"  stdout: {completed.stdout!r}\n  stderr: {completed.stderr!r}"
    )
    marker = "WUMPUS_P2_EVENTS:"
    assert marker in completed.stdout, completed.stdout
    return completed.stdout.split(marker, 1)[1].strip()


@then(
    "the event produced by the separate process equals the event an "
    "in-process from_snapshot would produce for the same action"
)
def _r3s02_cross_process_equal(
    r3s02_cross_process: dict[str, Any],
    r3s02_subprocess_events: str,
) -> None:
    snapshot_json = r3s02_cross_process["snapshot_file"].read_text(encoding="utf-8")
    in_process = Game.from_snapshot(snapshot_from_json(snapshot_json))
    baseline_events = _step_events(in_process, r3s02_cross_process["next_action"])
    assert r3s02_subprocess_events == repr(baseline_events), (
        "Cross-process next-event mismatch.\n"
        f"  in-process: {repr(baseline_events)}\n"
        f"  subprocess: {r3s02_subprocess_events}"
    )
