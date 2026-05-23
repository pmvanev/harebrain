"""Unit tests for R1-S05 shoot path collection.

Behaviors covered (port-to-port at `Game.step`, the driving port):
    - B1: `step("S")` emits ActionChosen + PromptIssued and parks the engine
          in `pending_prompt="shoot_path_len"`.
    - B2: path-length range validation (boundary + parametrized invalids).
    - B3: per-slot prompts advance the (slot, of) context monotonically.
    - B4: crooked-arrow rule applies only at K > 2 (slot 1 and slot 2 can
          repeat the player's prior rooms; only K >= 3 triggers the
          P(K) == P(K-2) check).
    - B5: ArrowFired emitted with full path on last slot; pending state
          cleared; turn counter advances by exactly 1.
    - B6: from_snapshot preserves pending_path_length.

Acceptance tests already cover: path-length=0 re-prompt; crooked at slot 3;
mid-shoot snapshot round-trip preserves pending_arrow_path. Tests here focus
on edge cases / event-shape verification the acceptance suite does not check
directly.
"""

from __future__ import annotations

import pytest

from wumpus import Game
from wumpus.events import (
    ActionChosen,
    ArrowFired,
    CrookedPathRejected,
    PromptIssued,
)
from wumpus.sinks import InMemorySink
from wumpus.types import World


def _shoot_test_world() -> World:
    """A pinned layout with all hazards far away from the player so the
    shoot sub-state-machine can be exercised without incidental hazard
    triggers."""
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


def _drive(actions: list[str]) -> tuple[Game, list]:
    """Construct a Game, drive it through `actions`, return (game, events)
    where `events` are the post-construction events emitted on the sink."""
    game = Game._from_world(_shoot_test_world(), seed=0)
    sink = InMemorySink()
    game.subscribe(sink)
    pre_count = len(sink.events)
    for action in actions:
        game.step(action)
    return game, sink.events[pre_count:]


# ---------------------------------------------------------------------------
# B1: `step("S")` enters shoot mode and emits the right opening events.
# ---------------------------------------------------------------------------


def test_step_S_emits_action_chosen_and_prompt_issued() -> None:
    """Picking S at the top-level prompt emits ActionChosen("S") immediately,
    followed by PromptIssued(shoot_path_len)."""
    game, events = _drive(["S"])

    action_chosens = [e for e in events if isinstance(e, ActionChosen)]
    prompt_issueds = [e for e in events if isinstance(e, PromptIssued)]

    assert len(action_chosens) == 1, (
        f"Expected exactly one ActionChosen event; got {len(action_chosens)}. "
        f"Events: {[type(e).__name__ for e in events]}"
    )
    assert action_chosens[0].action == "S"
    assert len(prompt_issueds) == 1
    assert prompt_issueds[0].kind == "shoot_path_len"
    # State: pending_prompt is shoot_path_len; no path or length yet.
    world = game.world_state()
    assert world.pending_prompt == "shoot_path_len"
    assert world.pending_arrow_path == ()
    assert world.pending_path_length is None


# ---------------------------------------------------------------------------
# B2: path-length validation boundaries.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value,is_valid",
    [
        ("1", True),
        ("3", True),
        ("5", True),
        ("0", False),
        ("6", False),
        ("-1", False),
        ("abc", False),
        ("", False),
    ],
)
def test_path_length_range_validation(value: str, is_valid: bool) -> None:
    """Path length must be in [1, 5]; everything else re-prompts. Yob's
    BASIC `NO. OF ROOMS(1-5)?` accepts only 1..5; out-of-range loops back.
    """
    game, events = _drive(["S", value])
    prompts = [e for e in events if isinstance(e, PromptIssued)]
    # The last PromptIssued is either still shoot_path_len (invalid) or
    # shoot_path_room (valid; advanced to slot 1).
    last_kind = prompts[-1].kind
    if is_valid:
        assert last_kind == "shoot_path_room", (
            f"Valid path length {value!r} should advance to shoot_path_room; "
            f"last prompt was {last_kind!r}."
        )
        # Pending path length is now set on the World.
        assert game.world_state().pending_path_length == int(value)
    else:
        assert last_kind == "shoot_path_len", (
            f"Invalid path length {value!r} should re-prompt shoot_path_len; "
            f"last prompt was {last_kind!r}."
        )
        assert game.world_state().pending_path_length is None


# ---------------------------------------------------------------------------
# B3: per-slot prompts advance (slot, of) context monotonically.
# ---------------------------------------------------------------------------


def test_per_slot_prompt_context_advances() -> None:
    """After `S → 3 → 7 → 14`, the engine awaits slot 3 of 3. The prompt
    context emitted on each acceptance carries `slot=K+1, of=N`."""
    game, events = _drive(["S", "3", "7", "14"])
    prompts = [e for e in events if isinstance(e, PromptIssued)]
    # Expected prompt sequence: shoot_path_len, then 3 × shoot_path_room
    # carrying slot=1/2/3 of 3.
    room_prompts = [p for p in prompts if p.kind == "shoot_path_room"]
    assert [p.context for p in room_prompts] == [
        {"slot": 1, "of": 3},
        {"slot": 2, "of": 3},
        {"slot": 3, "of": 3},
    ]


# ---------------------------------------------------------------------------
# B4: crooked-arrow rule applies only at K > 2.
# ---------------------------------------------------------------------------


def test_slot_2_can_repeat_slot_zero_concept() -> None:
    """P(K) == P(K-2) is the crooked rule, but for K=2 there is no slot 0.
    Slot 2 must accept ANY room (even the same as slot 1), because the rule
    starts checking at K=3."""
    game, events = _drive(["S", "3", "7", "7"])
    # No CrookedPathRejected should fire for the slot-2 entry.
    crooked = [e for e in events if isinstance(e, CrookedPathRejected)]
    assert crooked == [], (
        f"Slot 2 entering room=7 (same as slot 1) should NOT be crooked; "
        f"the rule starts at K>2. Got rejection events: {crooked!r}."
    )
    # Path now has (7, 7); engine awaits slot 3.
    assert game.world_state().pending_arrow_path == (7, 7)


def test_crooked_check_only_at_K_greater_than_2() -> None:
    """At K=3, P(3) == P(1) → crooked. Same room at K=2 is fine."""
    # Path [7, 14, 7]: P(3)==P(1) → crooked at slot 3.
    _, events = _drive(["S", "3", "7", "14", "7"])
    crooked = [e for e in events if isinstance(e, CrookedPathRejected)]
    assert len(crooked) == 1
    assert crooked[0].slot == 3
    assert crooked[0].attempted_room == 7


# ---------------------------------------------------------------------------
# B5: ArrowFired emitted on final slot; state cleared; turn advances.
# ---------------------------------------------------------------------------


def test_arrow_fired_on_final_slot() -> None:
    """Completing the last slot emits ArrowFired with the full path, clears
    all pending state, and advances the turn counter by exactly 1."""
    game, events = _drive(["S", "2", "7", "14"])
    arrow_fireds = [e for e in events if isinstance(e, ArrowFired)]
    assert len(arrow_fireds) == 1
    assert arrow_fireds[0].path == (7, 14)
    # State cleared; turn advanced from 0 to 1 (action completed).
    world = game.world_state()
    assert world.pending_prompt is None
    assert world.pending_arrow_path == ()
    assert world.pending_path_length is None
    assert world.turn == 1


def test_arrow_fired_single_room_path() -> None:
    """Smallest valid path: a 1-room shoot fires immediately after the
    first slot entry."""
    game, events = _drive(["S", "1", "7"])
    arrow_fireds = [e for e in events if isinstance(e, ArrowFired)]
    assert len(arrow_fireds) == 1
    assert arrow_fireds[0].path == (7,)
    assert game.world_state().turn == 1


# ---------------------------------------------------------------------------
# B6: snapshot round-trip preserves pending_path_length.
# ---------------------------------------------------------------------------


def test_snapshot_roundtrip_preserves_pending_path_length() -> None:
    """The acceptance scenario exercises pending_prompt + pending_arrow_path
    survival across `from_snapshot`. This unit test pins the third sibling
    field `pending_path_length` — without which the resurrected engine
    cannot know N for the `slot K of N` re-prompt."""
    game, _ = _drive(["S", "4", "7", "14"])
    snap = game.snapshot()
    assert snap.world.pending_path_length == 4
    resurrected = Game.from_snapshot(snap)
    rw = resurrected.world_state()
    assert rw.pending_path_length == 4
    assert rw.pending_arrow_path == (7, 14)
    assert rw.pending_prompt == "shoot_path_room"
