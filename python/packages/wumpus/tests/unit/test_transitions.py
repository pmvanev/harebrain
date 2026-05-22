"""Unit tests for `wumpus.engine.transitions.resolve_move`.

Two distinct behaviors:
    - accepted (adjacent) move advances world + emits MoveAttempted + MoveResolved
    - rejected (non-adjacent) move leaves world unchanged + emits MoveAttempted(accepted=False)
"""

from __future__ import annotations

import random

from wumpus.engine._r0_toy_cave import initial_world
from wumpus.engine.transitions import resolve_move
from wumpus.events import MoveAttempted, MoveResolved


def test_accepted_move_advances_world_and_emits_two_events() -> None:
    """Move from room 1 to adjacent room 2 in the toy cave: player_room updates,
    turn+=1, two events emitted (MoveAttempted accepted=True, then MoveResolved)."""
    world = initial_world()
    rng = random.Random(42)
    next_world, events = resolve_move(
        world, target_room=2, rng_cursor="x", rng=rng, cave="toy"
    )

    assert next_world.player_room == 2
    assert next_world.turn == world.turn + 1
    assert len(events) == 2
    assert isinstance(events[0], MoveAttempted)
    assert events[0].accepted is True
    assert events[0].target_room == 2
    assert isinstance(events[1], MoveResolved)
    assert events[1].player_room == 2


def test_rejected_move_leaves_world_unchanged_and_emits_rejection() -> None:
    """Move from room 1 to non-adjacent room 3 in the toy cave: world stays put,
    single MoveAttempted(accepted=False) event emitted."""
    world = initial_world()
    rng = random.Random(42)
    next_world, events = resolve_move(
        world, target_room=3, rng_cursor="x", rng=rng, cave="toy"
    )

    assert next_world == world
    assert len(events) == 1
    assert isinstance(events[0], MoveAttempted)
    assert events[0].accepted is False
    assert events[0].target_room == 3
