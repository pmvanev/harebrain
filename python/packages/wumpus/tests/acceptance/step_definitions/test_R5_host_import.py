"""R5 host-import acceptance step definitions (R5-S01) — walking skeleton.

Promotes the validated host-import spike into the production seam
`wumpus.host_import.step_from_snapshot`. Two scenarios mirror the R5-S01 AC:

  1. Host-import round-trip progresses one turn (in-process driving-port call).
  2. The process may EXIT between turns: each turn runs in a freshly spawned
     `sys.executable` interpreter, snap(i) feeding snap(i+1), and the resulting
     state-hash sequence equals a single-in-process baseline of the same
     actions. This is the contract's defining property — exit-between-turns
     equivalence — and it crosses a REAL process boundary (the SC12 proof).

Port-to-port (crafter mandate): the test enters through the host-import
driving port (`step_from_snapshot`) and the public `Game` / serialization
ports, and asserts on observable outcomes (the returned `StepResult`, the
serialized snapshot, the emitted events, and the cross-process state-hash
sequence). It does NOT introspect engine internals.

Seed + action sequence: seed=4 starts the player at room 5 with hazards at
{4, 8, 10, 13, 16}; the path `move 1 -> move 2` is legal (adjacent, on-graph)
and hazard-free, so the player genuinely progresses (room 5 -> 1 -> 2) with no
RNG-consuming hazard arm firing. The legality was confirmed by reading the
dodecahedron adjacencies (the spike warned off-graph moves silently no-op and
can fake-pass).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from typing import Any

from pytest_bdd import given, scenarios, then, when

from wumpus import Game, snapshot_from_json, snapshot_to_json
from wumpus.engine.hash import internal_state_hash
from wumpus.host_import import step_from_snapshot

# Bind the .feature file. Path is relative to this step-defs file's parent.
scenarios("../features/R5_host_import.feature")

_SEED = 4
# Legal (adjacent, on-graph), hazard-free path for seed=4 (start room 5):
# 5 -> 1 -> 2. Confirmed against the dodecahedron adjacency table.
_ACTIONS = ["move 1", "move 2"]


def _state_hash(snap_json: str) -> str:
    """Stable hash of a turn's observable universe: the canonical serialized
    snapshot text AND the engine's internal_state_hash of its World. Mirrors
    the spike's state-hash so the cross-process == in-process claim is the same
    one the probe validated."""
    world = snapshot_from_json(snap_json).world
    return hashlib.sha256(
        (snap_json + "|" + internal_state_hash(world)).encode()
    ).hexdigest()[:16]


def _initial_snapshot_json() -> str:
    """Capture a snapshot from Game(seed=4) with the INSTRUCTIONS prompt
    answered (N), parked at the first action prompt — the host's starting
    carry-over string."""
    game = Game(seed=_SEED)
    game.step("N")
    return snapshot_to_json(game.snapshot())


# Child program for scenario 2 — a FRESH interpreter per turn. Reads
# {"snap_json": ..., "action": ...} on stdin, drives ONE turn through the
# production `step_from_snapshot`, and writes the new snapshot + player_room
# back as JSON. Stands in for an MPL chart leaf whose OS process exits between
# turns. Invokes ONLY the public production seam (no test code).
_CHILD_PROGRAM = r"""
import json
import sys
from wumpus.host_import import step_from_snapshot

payload = json.loads(sys.stdin.read())
result = step_from_snapshot(payload["snap_json"], payload["action"])
sys.stdout.write(
    json.dumps(
        {
            "snap_json": result.snapshot_json,
            "player_room": result.observation["player_room"],
        }
    )
)
"""


# ---------------------------------------------------------------------------
# Scenario 1 — Host-import round-trip progresses one turn
# ---------------------------------------------------------------------------


@given(
    "a captured snapshot from Game(seed=4) with the instructions prompt answered",
    target_fixture="r5s01_capture",
)
def _r5s01_capture() -> dict[str, Any]:
    snap_json = _initial_snapshot_json()
    before = snapshot_from_json(snap_json).world
    return {"snap_json": snap_json, "before_room": before.player_room, "before_turn": before.turn}


@when(
    'a host calls step_from_snapshot(snap, "move <adjacent>") and writes the '
    "returned snapshot back",
    target_fixture="r5s01_result",
)
def _r5s01_step(r5s01_capture: dict[str, Any]) -> Any:
    # "move 1" is the legal adjacent move from the seed=4 start room (5 -> 1).
    return step_from_snapshot(r5s01_capture["snap_json"], "move 1")


@then("the game has progressed one turn")
def _r5s01_progressed(r5s01_capture: dict[str, Any], r5s01_result: Any) -> None:
    after = snapshot_from_json(r5s01_result.snapshot_json).world
    assert after.turn == r5s01_capture["before_turn"] + 1, (
        f"Turn did not advance by one: {r5s01_capture['before_turn']} -> {after.turn}."
    )
    assert r5s01_result.observation["player_room"] == 1, (
        f"Player did not move to the targeted adjacent room 1; "
        f"got {r5s01_result.observation['player_room']} (off-graph no-op?)."
    )
    assert after.player_room != r5s01_capture["before_room"], (
        "Player room unchanged — the move did not genuinely progress the game."
    )


@then("this turn's events were emitted without the resurrection preamble")
def _r5s01_no_preamble(r5s01_result: Any) -> None:
    kinds = [event["type"] for event in r5s01_result.events]
    assert kinds, "No events captured for the turn."
    # `from_snapshot` re-emits GameStarted (and possibly PromptIssued) BEFORE
    # the fresh sink subscribes; none of that preamble may leak into the turn.
    assert "GameStarted" not in kinds, (
        f"Resurrection preamble leaked into the turn events: {kinds}."
    )
    assert "MoveResolved" in kinds, (
        f"Expected the move to resolve this turn; got event kinds {kinds}."
    )


@then("the returned snapshot is canonical JSON")
def _r5s01_canonical(r5s01_result: Any) -> None:
    snap_json = r5s01_result.snapshot_json
    # Parses as JSON.
    json.loads(snap_json)
    # Canonical: re-serializing the parsed snapshot reproduces the same bytes
    # (snapshot_to_json uses sort_keys=True), so the string is stable.
    assert snapshot_to_json(snapshot_from_json(snap_json)) == snap_json, (
        "Returned snapshot is not canonical (re-serialization differs)."
    )


# ---------------------------------------------------------------------------
# Scenario 2 — Process can exit between turns without affecting the next call
# ---------------------------------------------------------------------------


@given(
    "an initial snapshot from Game(seed=4) with the instructions prompt answered",
    target_fixture="r5s02_initial_snap",
)
def _r5s02_initial_snap() -> str:
    return _initial_snapshot_json()


@when(
    'each of the legal adjacent moves ["move 1", "move 2"] is applied in a '
    "FRESH subprocess feeding snap(i) to snap(i+1)",
    target_fixture="r5s02_cross_process_sequence",
)
def _r5s02_run_cross_process(r5s02_initial_snap: str) -> list[tuple[int, str]]:
    """Drive each action in a freshly spawned interpreter, threading the
    returned snapshot into the next process. Returns the per-turn
    (player_room, state_hash) sequence."""
    sequence: list[tuple[int, str]] = []
    snap_json = r5s02_initial_snap
    for action in _ACTIONS:
        completed = subprocess.run(
            [sys.executable, "-c", _CHILD_PROGRAM],
            input=json.dumps({"snap_json": snap_json, "action": action}),
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert completed.returncode == 0, (
            f"Fresh-process turn failed (rc={completed.returncode}).\n"
            f"  stdout: {completed.stdout!r}\n  stderr: {completed.stderr!r}"
        )
        out = json.loads(completed.stdout)
        snap_json = out["snap_json"]
        sequence.append((out["player_room"], _state_hash(snap_json)))
    return sequence


@then(
    "the resulting state-hash sequence equals a single-in-process baseline of "
    "the same actions"
)
def _r5s02_equals_baseline(
    r5s02_initial_snap: str,
    r5s02_cross_process_sequence: list[tuple[int, str]],
) -> None:
    # In-process baseline: same actions, one live process, no exit between turns.
    baseline: list[tuple[int, str]] = []
    snap_json = r5s02_initial_snap
    for action in _ACTIONS:
        result = step_from_snapshot(snap_json, action)
        snap_json = result.snapshot_json
        baseline.append((result.observation["player_room"], _state_hash(snap_json)))

    assert r5s02_cross_process_sequence == baseline, (
        "Exit-between-turns sequence diverged from the single-in-process "
        "baseline.\n"
        f"  cross-process: {r5s02_cross_process_sequence}\n"
        f"  in-process:    {baseline}"
    )
    # Defensive: the path must genuinely progress (distinct rooms), not silently
    # no-op on off-graph moves (the spike's fake-pass warning).
    rooms = [room for room, _ in baseline]
    assert rooms == [1, 2], (
        f"Player did not progress through the expected legal path; rooms={rooms}."
    )
