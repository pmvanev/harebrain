"""Unit tests for `wumpus.engine.arrow_walk.walk_arrow` (R1-S06).

Behaviors covered (8 distinct; budget = 16):
    B1. Connecting path emits one ArrowPathStep per slot (deflected=False).
    B2. Final-room == wumpus_room → ArrowHitWumpus + GameEnded(wumpus_shot).
        Arrow count NOT decremented (Yob bug-for-bug D11).
    B3. Final-room == player_room → ArrowHitPlayer + ArrowCountChanged
        (decrement-as-if-missed). Game continues if arrows > 0.
    B4. Mid-path-through-player does NOT emit ArrowHitPlayer (Yob D11 canary).
    B5. Missing-tunnel slot deflects via randint(1,3) into sorted_adjacents[K-1];
        remaining slots are discarded.
    B6. Miss (final ∉ {wumpus, player}) emits ArrowMissed + startle +
        ArrowCountChanged decrement.
    B7. Miss startle that lands wumpus on player → GameEnded(eaten_after_bump).
    B8. Arrow count reaching 0 → GameEnded(out_of_arrows).

Tests address the pure function `walk_arrow` as its driving port (port-to-port
at domain scope; the function signature IS the port).

The dodecahedron used:
    8 -> {1, 7, 9}
    7 -> {6, 8, 17}
    17 -> {7, 16, 18}
    9 -> {8, 10, 18}
"""

from __future__ import annotations

import pytest

from wumpus.constants import DODECAHEDRON
from wumpus.engine.arrow_walk import walk_arrow
from wumpus.events import (
    ArrowCountChanged,
    ArrowHitPlayer,
    ArrowHitWumpus,
    ArrowMissed,
    ArrowPathStep,
    GameEnded,
    WumpusStartled,
)
from wumpus.types import World


def _world(
    *,
    player_room: int,
    wumpus_room: int,
    arrows: int = 5,
) -> World:
    """Minimal Tier-A1 World for walk_arrow tests. Hazards parked away from
    8/7/17/9 (the rooms most tests walk through) so no incidental adjacency
    surprises."""
    return World(
        player_room=player_room,
        wumpus_rooms=(wumpus_room,),
        pit_rooms=(11, 13),
        bat_rooms=(15, 19),
        arrows=arrows,
        turn=0,
        alive=True,
        pending_prompt=None,
        pending_arrow_path=(),
    )


class _ScriptedRng:
    """RNG double that returns scripted values from a list. Records each
    call's (a, b) pair so tests can assert the engine consumed RNG with the
    expected ranges (randint(1, 3) for deflection, randint(1, 4) for startle)."""

    def __init__(self, values: list[int]) -> None:
        self._values: list[int] = list(values)
        self._index: int = 0
        self.calls: list[tuple[int, int]] = []

    def randint(self, a: int, b: int) -> int:
        self.calls.append((a, b))
        if self._index >= len(self._values):
            raise AssertionError(
                f"_ScriptedRng exhausted: only {len(self._values)} scripted "
                f"values for randint({a}, {b})."
            )
        value = self._values[self._index]
        self._index += 1
        if not (a <= value <= b):
            raise AssertionError(
                f"_ScriptedRng value {value} outside randint({a}, {b}) range."
            )
        return value


# ---------------------------------------------------------------------------
# B1. Connecting path emits one ArrowPathStep per slot (deflected=False)
# ---------------------------------------------------------------------------


def test_b1_connecting_path_emits_one_step_per_slot_with_deflected_false() -> None:
    # Player at 8, wumpus far at 13. Path [7, 17] — 8→7 adj, 7→17 adj.
    # Final = 17 != wumpus(13), != player(8) → miss arm, but B1 only cares
    # about the path-step prefix. Script randint(1, 4) = 4 for the startle.
    world = _world(player_room=8, wumpus_room=13)
    rng = _ScriptedRng([4])
    _, events = walk_arrow(world, (7, 17), rng)
    steps = [e for e in events if isinstance(e, ArrowPathStep)]
    assert len(steps) == 2, (
        f"Expected 2 ArrowPathStep events for 2-room connecting path; got {len(steps)}."
    )
    assert steps[0].room == 7 and steps[0].deflected is False
    assert steps[1].room == 17 and steps[1].deflected is False


# ---------------------------------------------------------------------------
# B2. Hit wumpus → ArrowHitWumpus + GameEnded(wumpus_shot); arrows NOT decremented
# ---------------------------------------------------------------------------


def test_b2_hit_wumpus_emits_hit_then_game_ended_no_arrow_decrement() -> None:
    world = _world(player_room=8, wumpus_room=17, arrows=5)
    rng = _ScriptedRng([])  # No RNG draws expected on hit path.
    new_world, events = walk_arrow(world, (7, 17), rng)

    hit = [e for e in events if isinstance(e, ArrowHitWumpus)]
    ended = [e for e in events if isinstance(e, GameEnded)]
    counts = [e for e in events if isinstance(e, ArrowCountChanged)]

    assert hit and hit[0].room == 17, "Expected ArrowHitWumpus(room=17)."
    assert ended and ended[0].outcome == "wumpus_shot", (
        "Expected GameEnded(wumpus_shot)."
    )
    assert ended[0].message_kind == "win", "Expected message_kind='win'."
    assert counts == [], (
        f"Yob bug-for-bug: ArrowCountChanged MUST NOT fire on wumpus hit. "
        f"Got: {counts!r}"
    )
    assert new_world.arrows == 5, "Arrows must be unchanged on wumpus hit."
    assert new_world.alive is False, "World must be marked dead on terminal."


# ---------------------------------------------------------------------------
# B3. Self-shot (final == player) → ArrowHitPlayer + decrement; game continues
# ---------------------------------------------------------------------------


def test_b3_self_shot_emits_hit_player_and_decrements_arrow_count() -> None:
    # Path [7, 8]: 8→7 adj, 7→8 adj. Final = 8 = player. Self-shot.
    world = _world(player_room=8, wumpus_room=17, arrows=5)
    rng = _ScriptedRng([])  # No startle on self-shot.
    new_world, events = walk_arrow(world, (7, 8), rng)

    hits = [e for e in events if isinstance(e, ArrowHitPlayer)]
    counts = [e for e in events if isinstance(e, ArrowCountChanged)]
    ended = [e for e in events if isinstance(e, GameEnded)]

    assert hits and hits[0].room == 8, "Expected ArrowHitPlayer(room=8)."
    assert counts and counts[0].new_count == 4, "Expected arrow decrement to 4."
    assert ended == [], "Game must continue while arrows > 0 after self-shot."
    assert new_world.arrows == 4
    assert new_world.alive is True


# ---------------------------------------------------------------------------
# B4. Mid-path through player does NOT kill (Yob D11 canary)
# ---------------------------------------------------------------------------


def test_b4_midpath_through_player_does_not_kill() -> None:
    # Path [7, 8, 9]: 8→7 adj, 7→8 adj, 8→9 adj. Final = 9 (NOT player).
    # ArrowPathStep(room=8) fires mid-path, but ArrowHitPlayer must NOT.
    world = _world(player_room=8, wumpus_room=17, arrows=5)
    rng = _ScriptedRng([4])  # K=4 stay-put on miss-startle.
    _, events = walk_arrow(world, (7, 8, 9), rng)

    # Mid-path step into player's room is present.
    steps = [e for e in events if isinstance(e, ArrowPathStep)]
    midpath_room_8 = [s for s in steps if s.room == 8]
    assert midpath_room_8, (
        f"Expected an ArrowPathStep(room=8) mid-path; got steps: "
        f"{[(s.room, s.deflected) for s in steps]}"
    )

    # The canary: NO ArrowHitPlayer.
    hits = [e for e in events if isinstance(e, ArrowHitPlayer)]
    assert hits == [], (
        f"Yob D11 bug-for-bug: ArrowHitPlayer MUST fire ONLY on FINAL room match. "
        f"Hits: {hits!r}"
    )


# ---------------------------------------------------------------------------
# B5. Missing-tunnel slot deflects + discards remaining slots
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("draw,expected_room_index", [(1, 0), (2, 1), (3, 2)])
def test_b5_deflection_emits_random_adjacent_and_discards_remaining(
    draw: int, expected_room_index: int
) -> None:
    # Player at 8 (neighbors {1, 7, 9}, sorted [1, 7, 9]). Path [14, 17, 5].
    # 14 NOT adj to 8 → deflect. randint(1, 3) = draw → sorted[draw-1].
    # Remaining path [17, 5] discarded.
    world = _world(player_room=8, wumpus_room=20)
    rng = _ScriptedRng([draw, 4])  # deflect-pick, then startle stay-put.
    _, events = walk_arrow(world, (14, 17, 5), rng)

    expected_room = sorted(DODECAHEDRON[8])[expected_room_index]
    steps = [e for e in events if isinstance(e, ArrowPathStep)]
    assert len(steps) == 1, (
        f"Expected exactly 1 ArrowPathStep (deflection truncates walk); "
        f"got {len(steps)}: {[(s.room, s.deflected) for s in steps]}"
    )
    assert steps[0].room == expected_room
    assert steps[0].deflected is True
    # First randint call must be the (1, 3) deflection draw.
    assert rng.calls[0] == (1, 3), (
        f"First randint range was {rng.calls[0]}; expected (1, 3) deflection draw."
    )


# ---------------------------------------------------------------------------
# B6. Miss emits ArrowMissed + startle + decrement
# ---------------------------------------------------------------------------


def test_b6_miss_emits_missed_startle_and_decrement() -> None:
    # Path [7]: 8→7. Final = 7 != wumpus(17), != player(8) → miss.
    world = _world(player_room=8, wumpus_room=17, arrows=5)
    rng = _ScriptedRng([4])  # K=4 stay-put.
    new_world, events = walk_arrow(world, (7,), rng)

    missed = [e for e in events if isinstance(e, ArrowMissed)]
    startled = [e for e in events if isinstance(e, WumpusStartled)]
    counts = [e for e in events if isinstance(e, ArrowCountChanged)]

    assert missed, "Expected ArrowMissed on miss."
    assert startled, "Expected WumpusStartled (startle) on miss."
    assert startled[0].from_room == startled[0].to_room == 17, (
        f"Expected stay-put startle at room 17; got from={startled[0].from_room}, "
        f"to={startled[0].to_room}."
    )
    assert counts and counts[0].new_count == 4, "Expected arrow decrement to 4."
    # Event order: ArrowMissed → WumpusStartled → ArrowCountChanged.
    indices = {type(e).__name__: i for i, e in enumerate(events)}
    assert (
        indices["ArrowMissed"]
        < indices["WumpusStartled"]
        < indices["ArrowCountChanged"]
    )
    assert new_world.arrows == 4
    assert new_world.alive is True


# ---------------------------------------------------------------------------
# B7. Miss startle landing on player → GameEnded(eaten_after_bump)
# ---------------------------------------------------------------------------


def test_b7_miss_startle_landing_on_player_ends_game_eaten_after_bump() -> None:
    # Player at 8, wumpus at 7. Path [6]: 8→6? room 6 NOT adj to 8 ({1,7,9}).
    # Hmm — use a path that lands NOT on wumpus and NOT on player but where
    # the startle CAN land on the player. Wumpus at 7 (neighbors [6,8,17]).
    # K=2 sends wumpus to sorted_neighbors(7)[1] = 8 = player. Path that
    # misses both: walk to 1 (8→1 adj). Final 1 != wumpus(7), != player(8).
    world = _world(player_room=8, wumpus_room=7, arrows=5)
    rng = _ScriptedRng([2])  # K=2 → wumpus moves to neighbor[1] = 8 (player).
    new_world, events = walk_arrow(world, (1,), rng)

    missed = [e for e in events if isinstance(e, ArrowMissed)]
    startled = [e for e in events if isinstance(e, WumpusStartled)]
    counts = [e for e in events if isinstance(e, ArrowCountChanged)]
    ended = [e for e in events if isinstance(e, GameEnded)]

    assert missed, "Expected ArrowMissed."
    assert startled and startled[0].to_room == 8 and startled[0].ate_player is True
    assert counts and counts[0].new_count == 4
    assert ended and ended[0].outcome == "eaten_after_bump", (
        f"Expected GameEnded(eaten_after_bump); got {ended!r}"
    )
    assert new_world.alive is False


# ---------------------------------------------------------------------------
# B8. Arrow count reaching 0 → GameEnded(out_of_arrows)
# ---------------------------------------------------------------------------


def test_b8_out_of_arrows_terminal_on_decrement_to_zero_after_miss() -> None:
    world = _world(player_room=8, wumpus_room=17, arrows=1)
    rng = _ScriptedRng([4])  # K=4 stay-put.
    new_world, events = walk_arrow(world, (7,), rng)

    counts = [e for e in events if isinstance(e, ArrowCountChanged)]
    ended = [e for e in events if isinstance(e, GameEnded)]
    assert counts and counts[-1].new_count == 0, "Expected final arrow count 0."
    assert ended and ended[0].outcome == "out_of_arrows", (
        f"Expected GameEnded(out_of_arrows); got {ended!r}"
    )
    assert ended[0].message_kind == "lose"
    assert new_world.alive is False


def test_b8_self_shot_to_zero_also_ends_out_of_arrows() -> None:
    """Self-shot decrements arrows just like a miss; if it lands at 0, the
    game ends (same out_of_arrows arm). Path [7, 8] from player at 8 with
    arrows=1 → self-shot decrements to 0 → terminal."""
    world = _world(player_room=8, wumpus_room=17, arrows=1)
    rng = _ScriptedRng([])  # No startle on self-shot.
    new_world, events = walk_arrow(world, (7, 8), rng)

    hits = [e for e in events if isinstance(e, ArrowHitPlayer)]
    counts = [e for e in events if isinstance(e, ArrowCountChanged)]
    ended = [e for e in events if isinstance(e, GameEnded)]
    assert hits, "Expected ArrowHitPlayer on self-shot."
    assert counts and counts[-1].new_count == 0
    assert ended and ended[0].outcome == "out_of_arrows", (
        f"Self-shot decrement-to-0 must also end with out_of_arrows; got {ended!r}"
    )


# ---------------------------------------------------------------------------
# Edge: single-room path that connects + final equals wumpus
# ---------------------------------------------------------------------------


def test_edge_single_room_path_hits_wumpus() -> None:
    # Player at 8, wumpus at 7 (8's adjacent). Path [7] → 1 step → hit wumpus.
    world = _world(player_room=8, wumpus_room=7, arrows=5)
    rng = _ScriptedRng([])
    new_world, events = walk_arrow(world, (7,), rng)

    steps = [e for e in events if isinstance(e, ArrowPathStep)]
    hits = [e for e in events if isinstance(e, ArrowHitWumpus)]
    assert len(steps) == 1 and steps[0].room == 7 and steps[0].deflected is False
    assert hits and hits[0].room == 7
    assert new_world.arrows == 5  # No decrement on wumpus hit.


# ---------------------------------------------------------------------------
# Edge: 5-slot connecting path
# ---------------------------------------------------------------------------


def test_edge_five_slot_connecting_path_emits_five_steps() -> None:
    # Walk 8 → 7 → 17 → 18 → 9 → 8. 18 adj to {9, 17, 19}. 9 adj to {8, 10, 18}.
    # Wumpus parked at 20 so the walk doesn't hit it. Final = 8 = player → self-shot.
    # B1 contract: 5 ArrowPathStep events, all deflected=False.
    world = _world(player_room=8, wumpus_room=20, arrows=5)
    rng = _ScriptedRng([])
    _, events = walk_arrow(world, (7, 17, 18, 9, 8), rng)
    steps = [e for e in events if isinstance(e, ArrowPathStep)]
    assert len(steps) == 5
    assert [s.room for s in steps] == [7, 17, 18, 9, 8]
    assert all(s.deflected is False for s in steps)
