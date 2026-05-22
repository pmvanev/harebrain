"""Unit tests for `wumpus.engine._r0_toy_cave`.

R0's toy 3-room linear cave is the cheapest substrate the engine runs on.
These tests pin the canonical fixture shape so R1's dodecahedron migration
has a known-good starting point to delete from.
"""

from __future__ import annotations

import pytest

from wumpus.engine._r0_toy_cave import (
    TOY_PLAYER_START,
    TOY_WUMPUS_START,
    adjacent_rooms,
    initial_world,
)


def test_initial_world_canonical_layout() -> None:
    """The R0 initial World has player in room 1, wumpus in room 3,
    no other hazards, no arrows, turn 0, alive=True."""
    world = initial_world()
    assert world.player_room == TOY_PLAYER_START == 1
    assert world.wumpus_rooms == (TOY_WUMPUS_START,) == (3,)
    assert world.pit_rooms == ()
    assert world.bat_rooms == ()
    assert world.arrows == 0
    assert world.turn == 0
    assert world.alive is True


@pytest.mark.parametrize(
    "room,expected_neighbors",
    [
        (1, (2,)),
        (2, (1, 3)),
        (3, (2,)),
    ],
)
def test_adjacent_rooms_returns_linear_3_room_neighbors(
    room: int, expected_neighbors: tuple[int, ...]
) -> None:
    """The linear-cave adjacency: 1-2-3, with rooms 1 and 3 as leaves."""
    assert adjacent_rooms(room) == expected_neighbors
