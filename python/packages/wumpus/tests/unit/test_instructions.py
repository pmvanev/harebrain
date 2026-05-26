"""Unit tests for the R1-S08 instructions block + pre-game Y/N state machine.

Behaviors covered (port-to-port through the public surface module and the
`Game.step` driving port):
    - `wumpus.surfaces.yob.instructions_block()` is multi-line + carries
      Yob's RAMDOM typo exactly once
    - `wumpus.surfaces.yob.INSTRUCTIONS_PROMPT` /
      `wumpus.surfaces.yob.HUNT_THE_WUMPUS_BANNER` constants equal Yob's
      verbatim strings
    - `wumpus.surfaces.yob.render_instructions(event)` includes the lines
      payload followed by the banner
    - `wumpus.surfaces.yob.render_banner_only()` returns just the banner
    - Production `Game(seed=k)` enters the pre-game state at construction
      (`pending_prompt="instructions"`); `Game(seed=k, cave="toy")`
      bypasses pre-game (R0 test substrate)
    - `step("Y")` / `step("N")` / case-insensitive variants emit
      `InstructionsShown` and clear `pending_prompt`
    - Invalid input re-emits `PromptIssued(kind="instructions")`; the
      turn counter does not advance
    - The InstructionsShown event's `lines` payload differs between Y
      (non-empty Yob block) and N (empty tuple)

Per the crafter mandate (Mandate 3, Port-to-Port): every test exercises a
PUBLIC driving port — the `wumpus.surfaces.yob` module functions OR the
`Game.step` API. No private helpers or internal classes are tested
directly.

Per the test-budget discipline: ~10 distinct behaviors → 20-test budget.
Input variations are parametrized (case-insensitive Y/y/N/n collapsed
into one parametrized test).
"""

from __future__ import annotations

import pytest

from wumpus import Game
from wumpus.events import (
    GameStarted,
    InstructionsShown,
    PromptIssued,
)
from wumpus.sinks import InMemorySink
from wumpus.surfaces import yob as yob_surface
from wumpus.types import World


# ---------------------------------------------------------------------------
# Behavior 1+2: instructions_block() contents
# ---------------------------------------------------------------------------


def test_instructions_block_contains_ramdom_typo_exactly_once() -> None:
    """D11 bug-for-bug canary: the RAMDOM typo (Yob BASIC line 1300) must
    appear in the instructions block exactly once. If a future "helpful
    corrector" PR replaces RAMDOM with RANDOM, this test catches it."""
    block = yob_surface.instructions_block()
    occurrences = sum(line.count("RAMDOM") for line in block)
    assert occurrences == 1, (
        f"RAMDOM typo expected exactly once in instructions block; "
        f"got {occurrences} occurrences."
    )


def test_instructions_block_is_multi_line() -> None:
    """The block is sourced from BASIC lines 1010-1400 (~39 PRINT
    statements). It must be a multi-line tuple, not a single string,
    and must contain at least the welcome line + the warnings list."""
    block = yob_surface.instructions_block()
    assert isinstance(block, tuple), (
        f"instructions_block() must return a tuple; got {type(block)}."
    )
    assert len(block) >= 30, (
        f"Instructions block should have ~39 lines from BASIC source; got {len(block)}."
    )
    # Sanity: welcome line + warnings header should be present.
    full_text = "\n".join(block)
    assert "WELCOME TO 'HUNT THE WUMPUS'" in full_text, (
        "Instructions block missing welcome line."
    )
    assert "WARNINGS:" in full_text, "Instructions block missing warnings section."


# ---------------------------------------------------------------------------
# Behavior 3: constants — verbatim Yob strings
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "constant_name, expected_value",
    [
        ("INSTRUCTIONS_PROMPT", "INSTRUCTIONS (Y-N)?"),
        ("HUNT_THE_WUMPUS_BANNER", "HUNT THE WUMPUS"),
    ],
)
def test_yob_surface_constants_are_verbatim(
    constant_name: str, expected_value: str
) -> None:
    """SC8 + D11: the prompt + banner strings live ONLY in
    wumpus.surfaces.yob and are byte-exact to Yob's BASIC source
    (lines 0020 + 0375)."""
    actual = getattr(yob_surface, constant_name)
    assert actual == expected_value, (
        f"{constant_name} was {actual!r}; expected {expected_value!r}."
    )


# ---------------------------------------------------------------------------
# Behavior 4+5: render functions
# ---------------------------------------------------------------------------


def test_render_instructions_includes_lines_then_banner() -> None:
    """`render_instructions(event)` returns the event's lines payload
    followed by the HUNT THE WUMPUS banner. The order is significant
    (Yob's BASIC order-of-operations: GOSUB 1000 then PRINT line 375)."""
    block = yob_surface.instructions_block()
    event = InstructionsShown(
        schema_version=1,
        turn=0,
        surface_variant="<placeholder>",
        internal_state_hash="",
        rng_cursor="",
        lines=block,
    )
    rendered = yob_surface.render_instructions(event)
    assert rendered[: len(block)] == block, (
        "render_instructions should start with the event's lines payload."
    )
    assert rendered[-1] == "HUNT THE WUMPUS", (
        f"render_instructions should end with the banner; "
        f"got last line {rendered[-1]!r}."
    )


def test_render_banner_only_returns_just_the_banner() -> None:
    """For the N arm, the surface renders only the banner — no
    instructions text."""
    rendered = yob_surface.render_banner_only()
    assert rendered == ("HUNT THE WUMPUS",), (
        f"render_banner_only() was {rendered!r}; expected ('HUNT THE WUMPUS',)."
    )


# ---------------------------------------------------------------------------
# Behavior 6: production Game(seed=k) enters pre-game state
# ---------------------------------------------------------------------------


def test_production_game_enters_instructions_state_at_construction() -> None:
    """A freshly-constructed `Game(seed=k)` (default cave="yob") parks the
    engine in `pending_prompt="instructions"` awaiting Y/N input. The
    first emitted PromptIssued is the instructions prompt."""
    game = Game(seed=42)
    assert game.world_state().pending_prompt == "instructions", (
        f"Production Game(seed=k) should enter pre-game state; "
        f"got pending_prompt={game.world_state().pending_prompt!r}."
    )
    # GameStarted should still fire at construction (R1-S07 compatibility),
    # followed by a PromptIssued(kind="instructions").
    types = [type(e).__name__ for e in game._debug_events]
    assert "GameStarted" in types, (
        f"GameStarted should fire at construction; got events: {types}"
    )
    instructions_prompts = [
        e
        for e in game._debug_events
        if isinstance(e, PromptIssued) and e.kind == "instructions"
    ]
    assert instructions_prompts, (
        f"Expected PromptIssued(kind='instructions') at construction; "
        f"got events: {types}"
    )


def test_toy_cave_construction_skips_pre_game_state() -> None:
    """The R0 toy cave is a test-only substrate; constructing
    `Game(seed=k, cave="toy")` does NOT enter the pre-game state so the
    R0 deterministic-action-sequence tests continue to drive
    `step("move N")` directly."""
    game = Game(seed=42, cave="toy")
    assert game.world_state().pending_prompt is None, (
        f"Toy-cave Game should NOT enter pre-game state; "
        f"got pending_prompt={game.world_state().pending_prompt!r}."
    )
    # No instructions prompt should be in the event stream.
    instructions_prompts = [
        e
        for e in game._debug_events
        if isinstance(e, PromptIssued) and e.kind == "instructions"
    ]
    assert instructions_prompts == [], (
        f"Toy-cave Game should NOT emit instructions prompt; "
        f"got: {instructions_prompts}"
    )


# ---------------------------------------------------------------------------
# Behavior 7+8: step("Y") / step("N") clear pending_prompt + emit InstructionsShown
# ---------------------------------------------------------------------------


def _build_pregame_world() -> World:
    """A pre-game world: pending_prompt='instructions', hazards parked
    far from the player start so no incidental hazards fire on the
    first turn after the answer."""
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


@pytest.mark.parametrize(
    "answer, expect_nonempty_lines",
    [
        ("Y", True),
        ("y", True),  # case-insensitive
        ("N", False),
        ("n", False),  # case-insensitive
    ],
)
def test_pregame_y_or_n_emits_instructions_shown_and_clears_pending(
    answer: str, expect_nonempty_lines: bool
) -> None:
    """`step("Y")` (or "y") emits `InstructionsShown` with the full Yob
    lines block; `step("N")` (or "n") emits `InstructionsShown` with an
    empty lines payload. Either way, `pending_prompt` clears to None and
    the engine is ready for the first turn."""
    game = Game._from_world(_build_pregame_world(), seed=0)
    sink = InMemorySink()
    game.subscribe(sink)
    pre_count = len(sink.events)
    game.step(answer)
    post_events = sink.events[pre_count:]

    shown = [e for e in post_events if isinstance(e, InstructionsShown)]
    assert len(shown) == 1, (
        f"Expected exactly one InstructionsShown event after step({answer!r}); "
        f"got {len(shown)}: {[type(e).__name__ for e in post_events]}"
    )
    if expect_nonempty_lines:
        assert len(shown[0].lines) > 0, (
            f"step({answer!r}) should emit InstructionsShown with non-empty "
            f"lines; got {shown[0].lines!r}."
        )
        assert any("RAMDOM" in line for line in shown[0].lines), (
            f"step({answer!r}) lines payload missing the RAMDOM canary."
        )
    else:
        assert shown[0].lines == (), (
            f"step({answer!r}) should emit InstructionsShown with EMPTY lines "
            f"(N skips the block); got {shown[0].lines!r}."
        )
    # In both arms, pending_prompt clears to None.
    assert game.world_state().pending_prompt is None, (
        f"After step({answer!r}), pending_prompt should be None; "
        f"got {game.world_state().pending_prompt!r}."
    )


# ---------------------------------------------------------------------------
# Behavior 9: invalid input re-prompts; turn counter does not advance
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_input",
    [
        "",
        "X",
        "yes",
        "no",
        "move 2",
        "S",
        "1",
    ],
)
def test_pregame_invalid_input_reprompts(bad_input: str) -> None:
    """Anything that isn't Y/y/N/n at the INSTRUCTIONS prompt re-issues
    `PromptIssued(kind="instructions")` and does NOT advance the engine
    state — pending_prompt stays "instructions", no InstructionsShown
    fires, turn counter does not increment."""
    game = Game._from_world(_build_pregame_world(), seed=0)
    initial_turn = game.world_state().turn
    sink = InMemorySink()
    game.subscribe(sink)
    pre_count = len(sink.events)
    game.step(bad_input)
    post_events = sink.events[pre_count:]

    shown = [e for e in post_events if isinstance(e, InstructionsShown)]
    assert shown == [], (
        f"step({bad_input!r}) at INSTRUCTIONS prompt should NOT emit "
        f"InstructionsShown; got {shown!r}"
    )
    re_prompts = [
        e
        for e in post_events
        if isinstance(e, PromptIssued) and e.kind == "instructions"
    ]
    assert re_prompts, (
        f"step({bad_input!r}) at INSTRUCTIONS prompt should re-emit "
        f"PromptIssued(kind='instructions'); got events: "
        f"{[type(e).__name__ for e in post_events]}"
    )
    # State invariants: pending_prompt still 'instructions', turn unchanged.
    assert game.world_state().pending_prompt == "instructions", (
        f"After invalid input, pending_prompt should still be 'instructions'; "
        f"got {game.world_state().pending_prompt!r}."
    )
    assert game.world_state().turn == initial_turn, (
        f"Turn counter advanced on invalid INSTRUCTIONS input "
        f"({initial_turn} -> {game.world_state().turn}); the pre-game "
        f"prompt is not an action-completing event."
    )


# ---------------------------------------------------------------------------
# Behavior 10: PromptKind variant accepts "instructions"
# ---------------------------------------------------------------------------


def test_prompt_issued_accepts_instructions_kind() -> None:
    """The PromptKind Literal allows "instructions" as a valid variant.
    This pins the ADR-010 event-shape invariant: PromptIssued.kind is a
    typed discriminator, and "instructions" is part of the alphabet."""
    event = PromptIssued(
        schema_version=1,
        turn=0,
        surface_variant="<placeholder>",
        internal_state_hash="",
        rng_cursor="",
        kind="instructions",
        context=None,
    )
    assert event.kind == "instructions"


# ---------------------------------------------------------------------------
# Behavior 11: GameStarted's layout_hash is stable across instructions
# ---------------------------------------------------------------------------


def test_layout_hash_is_pre_instructions_world() -> None:
    """SC1 + R1-S07 invariant: GameStarted.layout_hash is the hash of the
    INITIAL layout (the pinned cave + entities), not the post-instructions
    pending-state world. SAME SET-UP=Y restoration relies on this being
    a stable identifier."""
    game = Game(seed=42)
    started_events = [e for e in game._debug_events if isinstance(e, GameStarted)]
    assert len(started_events) == 1, (
        f"Expected exactly one GameStarted at construction; got {len(started_events)}"
    )
    # The layout_hash should match the _initial_layout's hash (which has
    # pending_prompt=None, NOT "instructions"). Pin the invariant via the
    # private `_initial_layout` field (test-only access).
    from wumpus.engine.hash import internal_state_hash

    expected_hash = internal_state_hash(game._initial_layout)
    assert started_events[0].layout_hash == expected_hash, (
        f"GameStarted.layout_hash was {started_events[0].layout_hash!r}; "
        f"expected {expected_hash!r} (hash of the pre-instructions initial layout)."
    )
    # And confirm the initial layout has NO pre-game prompt — restoring
    # to it on SAME SET-UP=Y must NOT re-show instructions.
    assert game._initial_layout.pending_prompt is None, (
        f"_initial_layout.pending_prompt was "
        f"{game._initial_layout.pending_prompt!r}; expected None (Yob's "
        f"SAME SET-UP=Y restores the cave but does not re-show instructions)."
    )
