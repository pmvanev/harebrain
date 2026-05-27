"""Unit tests for `wumpus.engine.game.Game` (R0 driving-port surface).

Behaviors covered (not duplicates of acceptance tests):
    - constructor emits GameStarted once
    - step() rejects malformed action strings with ValueError
    - subscribe() replays historical events to the new sink
"""

from __future__ import annotations

import pytest

from wumpus import Game
from wumpus.events import GameStarted, MoveAttempted, MoveResolved
from wumpus.sinks import InMemorySink


def test_construction_emits_game_started() -> None:
    """A freshly-constructed Game has exactly one event in its debug log:
    a GameStarted carrying the seed."""
    game = Game(seed=42, cave="toy")
    assert len(game._debug_events) == 1
    event = game._debug_events[0]
    assert isinstance(event, GameStarted)
    assert event.seed == 42


@pytest.mark.parametrize(
    "bad_action",
    [
        "",
        "shoot 1 2 3",
        "move",
        "move two",
        "MOVE 2",
        "go 2",
    ],
)
def test_step_never_raises_on_unrecognized_action(bad_action: str) -> None:
    """R1-S11 (G6): unrecognized input must NEVER raise an uncaught exception
    to the caller — it re-prompts without consuming the turn. This replaces
    the R0 contract (which raised ValueError on non-`move <N>` input); raising
    crashed `python -m wumpus` whenever the player typed a bare letter.

    The behavioral assertion is observable through the driving port: the call
    returns an Observation (no exception) and the turn counter does not
    advance (the input was not an action-completing event)."""
    game = Game(seed=42, cave="toy")
    turn_before = game.world_state().turn
    observation = game.step(bad_action)  # must not raise (G6)
    assert observation is not None
    assert game.world_state().turn == turn_before, (
        f"Unrecognized input {bad_action!r} advanced the turn counter from "
        f"{turn_before} to {game.world_state().turn}; G6 requires the turn "
        f"to be unconsumed on unrecognized input."
    )


def test_subscribe_replays_history_to_late_sink() -> None:
    """A sink attached AFTER `GameStarted` still records that event,
    because subscribe() replays history. This is the contract scenario 2
    of the R0 acceptance suite depends on."""
    game = Game(seed=42, cave="toy")
    game.step("move 2")  # turn 1: MoveAttempted + MoveResolved
    sink = InMemorySink()
    game.subscribe(sink)

    # On subscribe, sink should have received: GameStarted + MoveAttempted + MoveResolved
    assert len(sink.events) == 3
    assert isinstance(sink.events[0], GameStarted)
    assert isinstance(sink.events[1], MoveAttempted)
    assert isinstance(sink.events[2], MoveResolved)
    assert sink.events == game._debug_events
