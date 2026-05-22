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
def test_step_rejects_malformed_action(bad_action: str) -> None:
    """The engine supports `move <int>` ONLY; everything else raises ValueError
    so no R1+ action types accidentally execute before their slice lands."""
    game = Game(seed=42, cave="toy")
    with pytest.raises(ValueError):
        game.step(bad_action)


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
