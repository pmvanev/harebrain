"""Unit tests for `wumpus.engine.hash.internal_state_hash`.

Tests cover the two distinct behaviors:
    - equal World values produce equal hashes (determinism contract)
    - non-equal World values produce non-equal hashes (no collision on R0
      state changes; CC-AC-6 needs this for ledger chain-integrity)
"""

from __future__ import annotations

import pytest

from wumpus.engine.hash import internal_state_hash
from wumpus.types import World


def _make_world(**overrides: object) -> World:
    defaults: dict[str, object] = {
        "player_room": 1,
        "wumpus_rooms": (3,),
        "pit_rooms": (),
        "bat_rooms": (),
        "arrows": 0,
        "turn": 0,
        "alive": True,
        "pending_prompt": None,
        "pending_arrow_path": (),
    }
    defaults.update(overrides)
    return World(**defaults)  # type: ignore[arg-type]


def test_internal_state_hash_equal_for_equal_worlds() -> None:
    """Two structurally equal Worlds hash to the same digest."""
    world_a = _make_world()
    world_b = _make_world()
    assert internal_state_hash(world_a) == internal_state_hash(world_b)


@pytest.mark.parametrize(
    "overrides",
    [
        {"player_room": 2},
        {"wumpus_rooms": (2,)},
        {"turn": 1},
        {"alive": False},
        {"pending_prompt": "SHOOT OR MOVE?"},
        {"arrows": 5},
        {"pending_arrow_path": (1, 2)},
    ],
)
def test_internal_state_hash_differs_when_any_field_differs(
    overrides: dict[str, object],
) -> None:
    """Any single-field change yields a different hash. Defends CC-AC-6's
    chain-integrity claim against silent state-bit loss."""
    baseline = _make_world()
    changed = _make_world(**overrides)
    assert internal_state_hash(baseline) != internal_state_hash(changed)
