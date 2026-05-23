"""Unit tests for `wumpus.engine.hazard_resolve.hazard_resolve` (R1-S03).

At R1-S03 the resolver handles ONLY the wumpus hazard (Yob `bas` 4150-4200).
R1-S04 extends with pit + bat handlers (4220-4250 + 4270-4300). The function
walks `HAZARD_ORDER` and dispatches per-kind; for kinds not yet implemented
the dispatcher is a no-op at R1-S03.

Behaviors covered (2 distinct; budget = 4):
    B1. Wumpus co-located with player → HazardTriggered(WUMPUS) + startle.
    B2. No hazard at player's room → empty event list, world unchanged.

Pit/bat at the player's room produce no events at R1-S03 — that's R1-S04
territory. The R1-S03 contract is "wumpus-only resolution, pit/bat skipped".
"""

from __future__ import annotations

from wumpus.engine.hazard_resolve import hazard_resolve
from wumpus.events import GameEnded, HazardTriggered, WumpusStartled
from wumpus.types import World


class _ScriptedRandint:
    """Tiny RNG double — fixed randint(1, 4) value."""

    def __init__(self, value: int) -> None:
        self.value = value

    def randint(self, a: int, b: int) -> int:
        return self.value


def _world_player_on_wumpus(*, wumpus_room: int = 7) -> World:
    """Player and wumpus in the same room — bump configuration."""
    return World(
        player_room=wumpus_room,
        wumpus_rooms=(wumpus_room,),
        pit_rooms=(11, 14),
        bat_rooms=(15, 19),
        arrows=5,
        turn=1,
        alive=True,
        pending_prompt=None,
        pending_arrow_path=(),
    )


def _world_safe_room(*, player_room: int = 1) -> World:
    """Player in a hazard-free room."""
    return World(
        player_room=player_room,
        wumpus_rooms=(7,),
        pit_rooms=(11, 14),
        bat_rooms=(15, 19),
        arrows=5,
        turn=1,
        alive=True,
        pending_prompt=None,
        pending_arrow_path=(),
    )


# ---------------------------------------------------------------------------
# B1 — Wumpus co-located → HazardTriggered + startle path
# ---------------------------------------------------------------------------


def test_b1_wumpus_in_player_room_emits_hazard_and_startle_events() -> None:
    """Player walked into wumpus's room (player_room == wumpus_rooms[0]).
    Resolver emits HazardTriggered(WUMPUS) then drives `move_wumpus_startle`
    and emits WumpusStartled. K=1 → wumpus moves to first sorted neighbor of 7
    (room 6), NOT the player's room → no GameEnded.
    """
    world = _world_player_on_wumpus(wumpus_room=7)
    rng = _ScriptedRandint(1)

    new_world, events = hazard_resolve(world, rng)  # type: ignore[arg-type]

    kinds = [type(e).__name__ for e in events]
    assert kinds == ["HazardTriggered", "WumpusStartled"], (
        f"Expected [HazardTriggered, WumpusStartled] for non-eat bump; got {kinds}."
    )
    assert isinstance(events[0], HazardTriggered) and events[0].kind == "WUMPUS"
    assert isinstance(events[1], WumpusStartled) and events[1].ate_player is False
    assert new_world.wumpus_rooms == (6,), (
        f"Wumpus should be at room 6 after K=1 startle from 7; got {new_world.wumpus_rooms}."
    )


def test_b1_wumpus_startled_onto_player_emits_game_ended() -> None:
    """K=4 keeps the wumpus on the player's room (player just bumped into it).
    Resolver emits HazardTriggered, WumpusStartled(ate_player=True), then
    GameEnded(outcome='eaten_after_bump', message_kind='lose')."""
    world = _world_player_on_wumpus(wumpus_room=7)
    rng = _ScriptedRandint(4)

    new_world, events = hazard_resolve(world, rng)  # type: ignore[arg-type]

    kinds = [type(e).__name__ for e in events]
    assert kinds == ["HazardTriggered", "WumpusStartled", "GameEnded"], (
        f"Expected [HazardTriggered, WumpusStartled, GameEnded] for eat-bump; got {kinds}."
    )
    startled = events[1]
    assert isinstance(startled, WumpusStartled)
    assert startled.ate_player is True
    ended = events[2]
    assert isinstance(ended, GameEnded)
    assert ended.outcome == "eaten_after_bump"
    assert ended.message_kind == "lose"
    # GameEnded carries a snapshot at the moment the game ends.
    assert ended.final_snapshot is not None
    assert ended.final_snapshot.world.player_room == 7


# ---------------------------------------------------------------------------
# B2 — No hazard at player's room → empty result, world unchanged
# ---------------------------------------------------------------------------


def test_b2_no_hazard_at_player_room_emits_no_events() -> None:
    """Player in room 1; wumpus at 7, pits at {11, 14}, bats at {15, 19}.
    No co-located hazard → resolver returns (world, []). Pit/bat presence
    elsewhere is irrelevant; sense events fire from a different code path."""
    world = _world_safe_room(player_room=1)
    rng = _ScriptedRandint(1)

    new_world, events = hazard_resolve(world, rng)  # type: ignore[arg-type]

    assert events == [], f"Expected no events for hazard-free room; got {events!r}."
    assert new_world == world, "World should be unchanged when no hazard fires."


def test_b2_pit_or_bat_at_player_room_is_skipped_at_r1s03() -> None:
    """R1-S03 ships ONLY the wumpus arm of hazard_resolve. A pit or bat at the
    player's room is recognized by HAZARD_ORDER but the dispatcher emits no
    events for those kinds at R1-S03 (R1-S04 fills them in). This test pins
    the explicit no-op so the R1-S04 implementer sees a failing test when
    they add pit/bat handling.
    """
    # Player on a pit room (room 11 has player + pit), no wumpus at player's room.
    world = World(
        player_room=11,
        wumpus_rooms=(7,),
        pit_rooms=(11, 14),
        bat_rooms=(15, 19),
        arrows=5,
        turn=1,
        alive=True,
        pending_prompt=None,
        pending_arrow_path=(),
    )
    rng = _ScriptedRandint(1)
    new_world, events = hazard_resolve(world, rng)  # type: ignore[arg-type]
    # No wumpus co-located → no events at R1-S03.
    assert events == [], (
        f"R1-S03 hazard_resolve should be a no-op for pit/bat at player room; got {events!r}."
    )
    assert new_world == world
