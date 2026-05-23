"""Unit tests for `wumpus.engine.startle.move_wumpus_startle` (R1-S03).

Behaviors covered (3 distinct; budget = 6):
    B1. K ∈ {1, 2, 3} moves the wumpus to sorted_adjacent[K-1] (Yob FNC(0) move arm).
    B2. K == 4 leaves the wumpus in place (Yob FNC(0) stay arm).
    B3. ate_player is True iff the destination room equals the player's room.

Tests address the pure function `move_wumpus_startle` as its driving port
(port-to-port testing at domain scope; per the skill, the function signature
IS the port for pure domain helpers).

`HAZARD_ORDER` is unit-pinned in test_constants.py (single constant pin —
matching the R1-S01 / R1-S02 pattern); the startle module itself imports it
only via constants.
"""

from __future__ import annotations

import pytest

from wumpus.engine.startle import move_wumpus_startle
from wumpus.events import WumpusStartled
from wumpus.types import World


def _world(*, player_room: int, wumpus_room: int) -> World:
    """Minimal Tier-A1 World for startle tests. Hazards parked away from
    sorted_neighbors(7) = [6, 8, 17] so the test surface stays pure."""
    return World(
        player_room=player_room,
        wumpus_rooms=(wumpus_room,),
        pit_rooms=(11, 14),
        bat_rooms=(15, 19),
        arrows=5,
        turn=3,
        alive=True,
        pending_prompt=None,
        pending_arrow_path=(),
    )


class _ScriptedRandint:
    """Tiny RNG double that records the (a, b) arg pair and returns a fixed value."""

    def __init__(self, value: int) -> None:
        self.value = value
        self.calls: list[tuple[int, int]] = []

    def randint(self, a: int, b: int) -> int:
        self.calls.append((a, b))
        return self.value


# ---------------------------------------------------------------------------
# B1 — K ∈ {1, 2, 3} → wumpus moves to sorted_adjacent[K - 1]
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "draw,expected_destination",
    [
        (1, 6),  # sorted_neighbors(7) = [6, 8, 17]; K=1 → 6
        (2, 8),  # K=2 → 8
        (3, 17),  # K=3 → 17
    ],
)
def test_b1_startle_moves_wumpus_to_kth_sorted_adjacent(
    draw: int, expected_destination: int
) -> None:
    """K ∈ {1,2,3}: wumpus moves to sorted_neighbors[K-1]. Sorted order matches
    transitions._adjacent_rooms_for_cave (sorted(DODECAHEDRON[room]))."""
    world = _world(player_room=1, wumpus_room=7)
    rng = _ScriptedRandint(draw)
    new_world, event = move_wumpus_startle(world, rng)  # type: ignore[arg-type]

    assert new_world.wumpus_rooms == (expected_destination,), (
        f"After K={draw} startle, wumpus_rooms was {new_world.wumpus_rooms}; "
        f"expected ({expected_destination},)."
    )
    assert isinstance(event, WumpusStartled)
    assert event.from_room == 7
    assert event.to_room == expected_destination
    # Engine RNG contract: a single randint(1, 4) call (FNC(0) ∈ 1..4).
    assert rng.calls == [(1, 4)], (
        f"Expected exactly one randint(1, 4) call; got {rng.calls!r}."
    )


# ---------------------------------------------------------------------------
# B2 — K == 4 → wumpus stays in place
# ---------------------------------------------------------------------------


def test_b2_startle_stay_keeps_wumpus_in_place() -> None:
    """K=4: wumpus stays. New world's wumpus_rooms equals input's wumpus_rooms."""
    world = _world(player_room=1, wumpus_room=7)
    rng = _ScriptedRandint(4)
    new_world, event = move_wumpus_startle(world, rng)  # type: ignore[arg-type]

    assert new_world.wumpus_rooms == (7,), (
        f"After K=4 startle, wumpus_rooms should be unchanged; got {new_world.wumpus_rooms}."
    )
    assert event.from_room == 7
    assert event.to_room == 7


# ---------------------------------------------------------------------------
# B3 — ate_player True iff destination equals player's room
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "draw,player_room,expected_ate",
    [
        # Wumpus startles to room 6; player is not in 6 → ate_player=False.
        (1, 99, False),
        # Player IS in room 8; K=2 moves wumpus to 8 → ate_player=True.
        (2, 8, True),
        # Player IS in room 7 (i.e. just bumped); K=4 keeps wumpus at 7 → ate.
        (4, 7, True),
        # Player at 17; K=3 → wumpus also at 17 → ate.
        (3, 17, True),
        # Player at 17; K=1 → wumpus at 6 (not 17) → not ate.
        (1, 17, False),
    ],
)
def test_b3_ate_player_iff_destination_equals_player_room(
    draw: int, player_room: int, expected_ate: bool
) -> None:
    """The WumpusStartled.ate_player flag is True iff the post-startle wumpus
    room equals the player's current room. The engine uses this to decide
    whether to emit GameEnded(eaten_after_bump) downstream."""
    world = _world(player_room=player_room, wumpus_room=7)
    rng = _ScriptedRandint(draw)
    _, event = move_wumpus_startle(world, rng)  # type: ignore[arg-type]
    assert event.ate_player is expected_ate, (
        f"For K={draw}, player_room={player_room}: ate_player was {event.ate_player}; "
        f"expected {expected_ate}."
    )
