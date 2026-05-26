"""Snapshot-serializability audit — SC6 / K-5 (R3-S02).

This is the 4th K-5 audit gate (alongside surface-leak, determinism-source,
module-state). It proves the SC6 contract end-to-end:

  snapshot_from_json(snapshot_to_json(snap)) == snap

is byte-identical (deep dataclass equality, including rng_cursor +
initial_layout + the nested World), and that the contract survives an
*actual* process boundary (JSON crosses to a subprocess and back).

Six canonical fixture snapshots cover the engine's state-space corners:

  1. turn-0            — freshly-constructed Game, instructions acknowledged
  2. mid-arrow-path    — mid-shoot with pending_arrow_path populated
  3. post-bat-teleport — right after a bat snatch relocated the player
  4. post-startle      — right after a wumpus startle moved the wumpus
  5. terminal-win      — GameEnded(wumpus_shot)
  6. terminal-lose     — GameEnded(fell_in_pit)

Port-to-port testing (crafter mandate): every fixture is built through the
public `Game(...)` driving port (or the underscore-prefixed `_from_world`
test hatch, which pins a precondition layout the seeded RNG would be
laborious to find). We assert on the public Snapshot dataclass + the events
a `Game.from_snapshot(...).step(action)` emits — never on engine internals.

`snapshot_to_json` / `snapshot_from_json` are the SC6 driving ports (pure
module functions in `wumpus.serialization`); calling them directly IS
port-to-port at the serialization scope.

Per ADR-007 the serialization is stdlib `json`; `rng_cursor` is a
base64-encoded `random.Random.getstate()` string. No msgspec (snapshots are
small; stdlib json is not the bottleneck).
"""

from __future__ import annotations

import json
import random
import subprocess
import sys
from dataclasses import fields, is_dataclass
from typing import Any, Callable

import pytest

from wumpus.engine.game import Game
from wumpus.events import Event, GameEnded, PlayerTeleported, WumpusStartled
from wumpus.serialization import snapshot_from_json, snapshot_to_json
from wumpus.types import World


# ---------------------------------------------------------------------------
# Fixture builders — each returns a (Game, next_action) pair.
#
# `next_action` is the action used to prove the "a step against the
# round-tripped snapshot produces the same event as a step against the
# in-memory snapshot" half of the AC. It is chosen to be deterministic and
# to NOT diverge across the in-memory vs. JSON-restored paths:
#   - For live-game corners we step a concrete move / shoot input.
#   - For terminal corners the engine is parked at the SAME SET-UP (Y-N)?
#     prompt, so the action is a deliberately-invalid "X" that re-prompts
#     (a PromptIssued) without consuming RNG asymmetrically.
# ---------------------------------------------------------------------------


def _base_world(**overrides: Any) -> World:
    """A Yob-invariant-satisfying World with distinct entity rooms. Helper for
    the `_from_world` test-hatch fixtures (post-bat, post-startle, terminals)."""
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
    """Replace `game._random.randint` with a scripted sequence so a hazard
    arm (bat teleport / wumpus startle) lands on a chosen room deterministically.

    This is the established R1-S03/R1-S04 scripted-RNG test pattern: the
    fixture pins the stochastic outcome so the corner state is reproducible.
    The encoded `rng_cursor` still round-trips faithfully (it captures
    `getstate()` of the underlying Random, which the scripting does not
    disturb — only the `randint` method is overridden for the single draw).
    """
    sequence = iter(values)
    game._random.randint = lambda a, b: next(sequence)  # type: ignore[method-assign]


def _build_turn_0() -> tuple[Game, str]:
    """Fixture 1 — freshly-constructed Game, instructions acknowledged (N).
    Parked at turn 0 awaiting the first action. Next action: a rejected move
    (room 99 is never adjacent), which is deterministic and RNG-free."""
    game = Game(seed=42)
    game.step("N")
    return game, "move 99"


def _build_mid_arrow_path() -> tuple[Game, str]:
    """Fixture 2 — mid-shoot with pending_arrow_path=(7, 14), awaiting slot 3
    of a 3-slot path. Next action: the final slot room, which finalizes the
    ArrowFired + walk."""
    game = Game(seed=42)
    game.step("N")
    game.step("S")
    game.step("3")
    game.step("7")
    game.step("14")
    world = game.world_state()
    assert world.pending_arrow_path == (7, 14), world.pending_arrow_path
    assert world.pending_prompt == "shoot_path_room", world.pending_prompt
    # Slot 3 must avoid the crooked rule P(3) == P(1) == 7; room 12 is fine.
    return game, "12"


def _build_post_bat_teleport() -> tuple[Game, str]:
    """Fixture 3 — right after a bat snatch relocated the player. Player at
    room 14 (adjacent to bat room 15); move into 15 triggers the bat arm,
    scripted to teleport to safe room 5. Next action: a rejected move."""
    game = Game._from_world(_base_world(player_room=14), seed=0)
    _script_randint(game, [5])  # teleport destination = room 5 (hazard-free)
    game.step("move 15")
    assert any(isinstance(e, PlayerTeleported) for e in game._debug_events)
    assert game.world_state().player_room == 5
    return game, "move 99"


def _build_post_startle() -> tuple[Game, str]:
    """Fixture 4 — right after a wumpus startle moved the wumpus (not eaten).
    Player at room 12 (adjacent to wumpus room 13); move into 13 bumps the
    wumpus; scripted startle K=1 moves the wumpus to sorted(adj[13])[0]=12
    (the player's old room, NOT the player's current room 13), so the player
    survives. Next action: a rejected move."""
    game = Game._from_world(_base_world(player_room=12), seed=0)
    _script_randint(game, [1])  # startle K=1 -> wumpus to room 12 (not player)
    game.step("move 13")
    startles = [e for e in game._debug_events if isinstance(e, WumpusStartled)]
    assert startles and not startles[-1].ate_player
    assert game.world_state().alive
    return game, "move 99"


def _build_terminal_win() -> tuple[Game, str]:
    """Fixture 5 — GameEnded(wumpus_shot). Player at room 1, wumpus at room 2
    (adjacent); a 1-slot shoot path [2] hits the wumpus. The engine parks at
    the post-terminal SAME SET-UP (Y-N)? prompt. Next action: invalid "X"
    re-prompts deterministically (no RNG consumed)."""
    game = Game._from_world(_base_world(player_room=1, wumpus_rooms=(2,)), seed=0)
    game.step("S")
    game.step("1")
    game.step("2")
    ended = [e for e in game._debug_events if isinstance(e, GameEnded)]
    assert ended and ended[-1].outcome == "wumpus_shot"
    return game, "X"


def _build_terminal_lose() -> tuple[Game, str]:
    """Fixture 6 — GameEnded(fell_in_pit). Player at room 1 (adjacent to pit
    room 8); move into 8 falls into the pit. Engine parks at SAME SET-UP
    (Y-N)?. Next action: invalid "X" re-prompts deterministically."""
    game = Game._from_world(_base_world(player_room=1, pit_rooms=(8, 7)), seed=0)
    game.step("move 8")
    ended = [e for e in game._debug_events if isinstance(e, GameEnded)]
    assert ended and ended[-1].outcome == "fell_in_pit"
    return game, "move 99"


# Registry of the six canonical fixtures: id -> builder.
_FIXTURE_BUILDERS: dict[str, Callable[[], tuple[Game, str]]] = {
    "turn-0": _build_turn_0,
    "mid-arrow-path": _build_mid_arrow_path,
    "post-bat-teleport": _build_post_bat_teleport,
    "post-startle": _build_post_startle,
    "terminal-win": _build_terminal_win,
    "terminal-lose": _build_terminal_lose,
}

_FIXTURE_IDS = list(_FIXTURE_BUILDERS)


def _step_events(game: Game, action: str) -> list[Event]:
    """Step `game` once and return ONLY the events that step emitted (the
    tail slice, excluding any from_snapshot resurrection preamble)."""
    pre_count = len(game._debug_events)
    game.step(action)
    return list(game._debug_events[pre_count:])


# ---------------------------------------------------------------------------
# Behavior 1 — JSON round-trip is byte-identical (deep equality) for all six
# state-space corners. The six fixtures are input variations of ONE behavior
# (Mandate 5: parametrize variations).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture_id", _FIXTURE_IDS)
def test_fixture_snapshot_json_round_trip_is_byte_identical(fixture_id: str) -> None:
    """`snapshot_from_json(snapshot_to_json(snap)) == snap` — deep dataclass
    equality, which transitively includes rng_cursor (the base64 RNG state),
    the nested World, initial_layout, cave, and active_escalation_rules."""
    game, _action = _FIXTURE_BUILDERS[fixture_id]()
    snap = game.snapshot()

    encoded = snapshot_to_json(snap)
    assert isinstance(encoded, str), "snapshot_to_json must return a JSON str."
    # The encoded form is genuinely JSON (parses without error).
    json.loads(encoded)

    restored = snapshot_from_json(encoded)
    assert restored == snap, (
        f"[{fixture_id}] JSON round-trip not byte-identical.\n"
        f"  original: {snap!r}\n  restored: {restored!r}"
    )


# ---------------------------------------------------------------------------
# Behavior 2 — a step against the round-tripped snapshot produces the same
# event as a step against the in-memory snapshot. Parametrized over the six
# corners.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture_id", _FIXTURE_IDS)
def test_step_against_round_tripped_snapshot_matches_in_memory(
    fixture_id: str,
) -> None:
    """For each corner: resurrect from the in-memory Snapshot and from the
    JSON-restored Snapshot, step both through the same action, and assert the
    emitted event slices are byte-for-byte equal. This proves the JSON
    round-trip preserves not just the dataclass shape but the engine's
    forward behavior (RNG cursor included)."""
    game, action = _FIXTURE_BUILDERS[fixture_id]()
    snap = game.snapshot()

    in_memory_game = Game.from_snapshot(snap)
    json_restored_game = Game.from_snapshot(snapshot_from_json(snapshot_to_json(snap)))

    in_memory_events = _step_events(in_memory_game, action)
    json_events = _step_events(json_restored_game, action)

    assert json_events == in_memory_events, (
        f"[{fixture_id}] step events diverged between JSON-restored and "
        f"in-memory snapshot.\n  in-memory ({len(in_memory_events)}): "
        f"{in_memory_events!r}\n  json ({len(json_events)}): {json_events!r}"
    )


# ---------------------------------------------------------------------------
# Behavior 3 — no Snapshot field (recursively) holds a random.Random; the
# rng_cursor field is a base64-encoded str. This is the SC6 structural claim.
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


@pytest.mark.parametrize("fixture_id", _FIXTURE_IDS)
def test_snapshot_holds_no_live_rng_object(fixture_id: str) -> None:
    """No field (recursively, including the nested World + initial_layout)
    holds a `random.Random`; `rng_cursor` is a base64-decodable str."""
    import base64

    game, _action = _FIXTURE_BUILDERS[fixture_id]()
    snap = game.snapshot()

    for nested in _walk_dataclass_values(snap):
        assert not isinstance(nested, random.Random), (
            f"[{fixture_id}] Snapshot graph holds a live random.Random "
            f"instance — SC6 forbids it (the RNG must be encoded)."
        )

    assert isinstance(snap.rng_cursor, str), (
        f"[{fixture_id}] rng_cursor must be a str (base64 per ADR-007); "
        f"got {type(snap.rng_cursor).__name__}."
    )
    # Round-trips through base64 (proves it is the encoded RNG state, not an
    # arbitrary string that merely happens to be a str).
    base64.b64decode(snap.rng_cursor.encode("ascii"))


# ---------------------------------------------------------------------------
# Behavior 4 — cross-process JSON round-trip preserves the next event.
# An ACTUAL subprocess (sys.executable -c ...) reads the JSON from a temp
# file, reconstructs the Game, steps once, and prints the resulting event.
# We assert the subprocess's event equals what an in-process from_snapshot
# would produce for the same action. This is the SC6 cross-process proof.
# ---------------------------------------------------------------------------


# The child program. It reads a snapshot JSON path + an action from argv,
# reconstructs the Game, steps once, and prints the repr of the emitted
# events (tail slice) to stdout on a single marker-delimited line.
_CHILD_PROGRAM = r"""
import sys
from wumpus.engine.game import Game
from wumpus.serialization import snapshot_from_json

snapshot_path = sys.argv[1]
action = sys.argv[2]

with open(snapshot_path, encoding="utf-8") as handle:
    snapshot_json = handle.read()

game = Game.from_snapshot(snapshot_from_json(snapshot_json))
pre_count = len(game._debug_events)
game.step(action)
step_events = game._debug_events[pre_count:]

# repr() of the frozen-dataclass events is a stable, comparable string.
sys.stdout.write("WUMPUS_P2_EVENTS:" + repr(step_events))
"""


def test_cross_process_json_round_trip_preserves_next_event(
    tmp_path: Any,
) -> None:
    """Process P1 snapshots a Game(seed=42) after a sequence of actions and
    writes the snapshot JSON to a temp file. Process P2 (a real subprocess)
    reads the JSON, reconstructs the Game, steps once, and prints the
    resulting events. P1 asserts P2's events equal what an in-process
    from_snapshot produces for the same action.

    The JSON genuinely crosses a process boundary (temp file + subprocess),
    so this is the SC6 end-to-end cross-process proof, not a simulated one.
    """
    # --- P1: build the snapshot + write JSON to disk -----------------------
    game = Game(seed=42)
    game.step("N")  # acknowledge the pre-game INSTRUCTIONS prompt
    # A bounded, deterministic action sequence reaching a mid-game state.
    for action in ("move 99", "move 99"):
        game.step(action)
    snap = game.snapshot()
    next_action = "move 99"  # deterministic (rejected move, RNG-free)

    snapshot_file = tmp_path / "snap.json"
    snapshot_file.write_text(snapshot_to_json(snap), encoding="utf-8")

    # --- P1's in-process baseline for `next_action` ------------------------
    in_process_game = Game.from_snapshot(snapshot_from_json(snapshot_to_json(snap)))
    baseline_events = _step_events(in_process_game, next_action)
    expected_repr = repr(baseline_events)

    # --- P2: spawn a REAL subprocess that reads the JSON + steps -----------
    completed = subprocess.run(
        [sys.executable, "-c", _CHILD_PROGRAM, str(snapshot_file), next_action],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, (
        f"Subprocess P2 failed (rc={completed.returncode}).\n"
        f"  stdout: {completed.stdout!r}\n  stderr: {completed.stderr!r}"
    )

    marker = "WUMPUS_P2_EVENTS:"
    assert marker in completed.stdout, (
        f"Subprocess P2 produced no event marker.\n  stdout: {completed.stdout!r}"
    )
    p2_repr = completed.stdout.split(marker, 1)[1].strip()

    assert p2_repr == expected_repr, (
        "Cross-process next-event mismatch.\n"
        f"  in-process (P1): {expected_repr}\n  subprocess (P2): {p2_repr}"
    )
