"""Unit tests for the R1-S07 SAME SET-UP=N session-close arm.

The Y arm (restore initial layout) is covered by the R1-S07 acceptance
scenario `test_same_setupy_restores_the_initial_layout_exactly`. This file
covers the N arm — `step("N")` after a GameEnded emits `SessionEnded` and
parks the engine in a no-op terminal state where further actions are
ignored.

Per the crafter mandate: port-to-port testing — these tests drive the
engine via the `Game.step` driving port and observe outcomes via the
emitted event stream (the driven-port boundary of `Sink.emit`).
"""

from __future__ import annotations

from wumpus import Game
from wumpus.events import GameEnded, GameStarted, SessionEnded
from wumpus.sinks import InMemorySink
from wumpus.types import World


def _build_pit_terminal_world() -> World:
    """Player one step from a pit room — same shape as the R1-S04 scenario 1
    fixture (player at 3, pit at 4)."""
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


def _drive_to_terminal_then(action: str) -> tuple[Game, InMemorySink, int]:
    """Construct a Game, drive into a pit (GameEnded fires), then step the
    given post-terminal action. Returns the game + sink + the event index
    that marks the start of post-terminal events (immediately after the
    SAME SET-UP prompt emission that follows the GameEnded)."""
    game = Game._from_world(_build_pit_terminal_world(), seed=0)
    sink = InMemorySink()
    game.subscribe(sink)
    game.step("move 4")  # walk into pit → GameEnded(fell_in_pit) + SAME SET-UP prompt
    pre_n_count = len(sink.events)
    game.step(action)
    return game, sink, pre_n_count


def test_same_setup_N_emits_session_ended_event() -> None:
    """After a terminal state, `step("N")` emits exactly one `SessionEnded`
    event and does NOT emit a fresh `GameStarted` (only Y restarts)."""
    _game, sink, pre_n_count = _drive_to_terminal_then("N")
    post_n = sink.events[pre_n_count:]
    session_ended = [e for e in post_n if isinstance(e, SessionEnded)]
    fresh_started = [e for e in post_n if isinstance(e, GameStarted)]
    assert len(session_ended) == 1, (
        f"Expected exactly one SessionEnded event after SAME SET-UP=N; "
        f"got {len(session_ended)}: {post_n!r}"
    )
    assert fresh_started == [], (
        f"SAME SET-UP=N must NOT emit a fresh GameStarted (only Y restarts); "
        f"got: {fresh_started!r}"
    )


def test_same_setup_N_subsequent_steps_are_noops() -> None:
    """After SAME SET-UP=N parks the engine, further `step(...)` calls
    do nothing — no events emitted, no exceptions raised."""
    game, sink, _pre_n_count = _drive_to_terminal_then("N")
    pre_followup_count = len(sink.events)
    # Try several action shapes; all must be no-ops.
    game.step("Y")
    game.step("N")
    game.step("move 3")
    game.step("S")
    post_followup = sink.events[pre_followup_count:]
    assert post_followup == [], (
        f"Expected zero events emitted after SAME SET-UP=N session close; "
        f"got: {[type(e).__name__ for e in post_followup]}"
    )


def test_game_ended_synthesizes_same_setup_prompt() -> None:
    """The R1-S07 design: any GameEnded event is immediately followed by a
    `PromptIssued(kind="same_setup")` so the caller knows a Y/N answer is
    awaited. The engine state's `pending_prompt` becomes "same_setup".
    Covered indirectly by the acceptance test but pinned here for the
    engine-state invariant."""
    from wumpus.events import PromptIssued

    game = Game._from_world(_build_pit_terminal_world(), seed=0)
    sink = InMemorySink()
    game.subscribe(sink)
    game.step("move 4")  # GameEnded(fell_in_pit) fires
    # The LAST emitted event should be the SAME SET-UP prompt; the GameEnded
    # immediately precedes it.
    types = [type(e).__name__ for e in sink.events]
    assert "GameEnded" in types, f"Expected GameEnded in events: {types}"
    ended_index = max(
        i for i, e in enumerate(sink.events) if isinstance(e, GameEnded)
    )
    # Find the PromptIssued AFTER the GameEnded; the kind must be "same_setup".
    same_setup_prompts = [
        e
        for e in sink.events[ended_index:]
        if isinstance(e, PromptIssued) and e.kind == "same_setup"
    ]
    assert same_setup_prompts, (
        f"Expected a PromptIssued(kind='same_setup') after GameEnded; "
        f"got events: {types}"
    )
    # Engine state pinned: pending_prompt == 'same_setup' awaiting Y/N.
    assert game.world_state().pending_prompt == "same_setup", (
        f"Expected pending_prompt='same_setup' after GameEnded; "
        f"got {game.world_state().pending_prompt!r}"
    )
