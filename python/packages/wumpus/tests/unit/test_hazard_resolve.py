"""Unit tests for `wumpus.engine.hazard_resolve.hazard_resolve` (R1-S03/S04).

R1-S03 wired the wumpus arm (Yob `bas` 4150-4200). R1-S04 adds:
    - Pit arm (4220-4250): HazardTriggered(PIT) + GameEnded(fell_in_pit).
    - Bat arm (4270-4300): HazardTriggered(BAT) + PlayerTeleported, with
      recursive re-entry on the new room (Yob's `GOTO 4130`).

Behaviors covered (6 distinct; budget = 12):
    B1. Wumpus co-located with player → HazardTriggered(WUMPUS) + startle.
    B2. No hazard at player's room → empty event list, world unchanged.
    B3. Pit at player's room → HazardTriggered(PIT) + GameEnded(fell_in_pit).
    B4. Bat at player's room → HazardTriggered(BAT) + PlayerTeleported,
        new player_room equals scripted destination, no recursion when
        destination is safe.
    B5. Bat → pit recursion → BAT events + PIT events + GameEnded.
    B6. Bat → bat → safe-room recursion + MAX_BAT_CHAIN safeguard.
"""

from __future__ import annotations

import pytest

from wumpus.engine.hazard_resolve import MAX_BAT_CHAIN, hazard_resolve
from wumpus.events import (
    GameEnded,
    HazardTriggered,
    PlayerTeleported,
    WumpusStartled,
)
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


# ---------------------------------------------------------------------------
# R1-S04 helpers
# ---------------------------------------------------------------------------


class _ScriptedRandintList:
    """RNG double scripted with a sequence of `randint(a, b)` return values.

    Raises on exhaustion so tests catch any case where the engine consumed
    more RNG than the test expected (e.g. an accidental extra teleport draw).
    """

    def __init__(self, values: list[int]) -> None:
        self._values = list(values)
        self._index = 0

    def randint(self, a: int, b: int) -> int:
        if self._index >= len(self._values):
            raise AssertionError(
                f"_ScriptedRandintList exhausted: only {len(self._values)} "
                f"scripted values for randint({a}, {b})."
            )
        value = self._values[self._index]
        self._index += 1
        if not (a <= value <= b):
            raise AssertionError(
                f"_ScriptedRandintList value {value} outside randint({a}, {b}) range."
            )
        return value


# ---------------------------------------------------------------------------
# B3 — Pit at player's room → HazardTriggered(PIT) + GameEnded(fell_in_pit)
# ---------------------------------------------------------------------------


def test_b3_pit_at_player_room_emits_hazard_and_game_ended() -> None:
    """Player walks into a pit (player_room == pit_rooms[0]). Resolver emits
    HazardTriggered(PIT) + GameEnded(outcome='fell_in_pit', message_kind='lose').
    The world is marked dead (alive=False). No RNG draws (pit fall is
    deterministic — no startle, no teleport)."""
    world = World(
        player_room=4,
        wumpus_rooms=(11,),
        pit_rooms=(4, 14),
        bat_rooms=(15, 19),
        arrows=5,
        turn=1,
        alive=True,
        pending_prompt=None,
        pending_arrow_path=(),
    )
    rng = _ScriptedRandintList([])

    new_world, events = hazard_resolve(world, rng)  # type: ignore[arg-type]

    kinds = [type(e).__name__ for e in events]
    assert kinds == ["HazardTriggered", "GameEnded"], (
        f"Expected [HazardTriggered, GameEnded] for pit fall; got {kinds}."
    )
    assert isinstance(events[0], HazardTriggered) and events[0].kind == "PIT"
    assert events[0].room == 4
    ended = events[1]
    assert isinstance(ended, GameEnded)
    assert ended.outcome == "fell_in_pit"
    assert ended.message_kind == "lose"
    assert ended.final_snapshot is not None
    assert ended.final_snapshot.world.player_room == 4
    assert new_world.alive is False


# ---------------------------------------------------------------------------
# B4 — Bat at player's room → HazardTriggered(BAT) + PlayerTeleported (safe)
# ---------------------------------------------------------------------------


def test_b4_bat_at_player_room_teleports_to_scripted_safe_room() -> None:
    """Player walks into a bat (player_room == bat_rooms[0]). Resolver emits
    HazardTriggered(BAT) + PlayerTeleported(from=5, to=17, cause='bat').
    Room 17's neighbors {7, 16, 18} contain no hazards in this layout, so
    no recursive hazard events fire. The world's player_room updates to 17."""
    # Bats at 5, 12. Wumpus at 11, pits at 13, 14 — none in {17} ∪ {7,16,18}.
    world = World(
        player_room=5,
        wumpus_rooms=(11,),
        pit_rooms=(13, 14),
        bat_rooms=(5, 12),
        arrows=5,
        turn=1,
        alive=True,
        pending_prompt=None,
        pending_arrow_path=(),
    )
    rng = _ScriptedRandintList([17])  # bat draw → destination room 17

    new_world, events = hazard_resolve(world, rng)  # type: ignore[arg-type]

    kinds = [type(e).__name__ for e in events]
    assert kinds == ["HazardTriggered", "PlayerTeleported"], (
        f"Expected [HazardTriggered, PlayerTeleported] for safe bat snatch; got {kinds}."
    )
    assert isinstance(events[0], HazardTriggered) and events[0].kind == "BAT"
    assert events[0].room == 5
    teleport = events[1]
    assert isinstance(teleport, PlayerTeleported)
    assert teleport.from_room == 5
    assert teleport.to_room == 17
    assert teleport.cause == "bat"
    assert new_world.player_room == 17
    assert new_world.alive is True


# ---------------------------------------------------------------------------
# B5 — Bat → pit recursion → BAT events + PIT events + GameEnded
# ---------------------------------------------------------------------------


def test_b5_bat_teleport_into_pit_recursively_ends_game() -> None:
    """Bat at 5 snatches the player to room 17, which contains a pit. The
    resolver's recursive re-entry on the new room fires the pit arm. Final
    event sequence: BAT, PlayerTeleported, PIT, GameEnded(fell_in_pit)."""
    world = World(
        player_room=5,
        wumpus_rooms=(11,),
        pit_rooms=(17, 14),
        bat_rooms=(5, 9),
        arrows=5,
        turn=1,
        alive=True,
        pending_prompt=None,
        pending_arrow_path=(),
    )
    rng = _ScriptedRandintList([17])

    new_world, events = hazard_resolve(world, rng)  # type: ignore[arg-type]

    kinds = [type(e).__name__ for e in events]
    assert kinds == [
        "HazardTriggered",
        "PlayerTeleported",
        "HazardTriggered",
        "GameEnded",
    ], f"Expected bat → pit recursion sequence; got {kinds}."
    assert isinstance(events[0], HazardTriggered) and events[0].kind == "BAT"
    assert isinstance(events[2], HazardTriggered) and events[2].kind == "PIT"
    assert isinstance(events[3], GameEnded)
    assert events[3].outcome == "fell_in_pit"
    assert new_world.alive is False
    assert new_world.player_room == 17


# ---------------------------------------------------------------------------
# B6 — Bat → bat → safe recursion + MAX_BAT_CHAIN safeguard
# ---------------------------------------------------------------------------


def test_b6_bat_chain_to_safe_room_recurses_until_safe() -> None:
    """Bat at 5 snatches player to room 12 (also a bat); the recursive
    re-entry fires another BAT arm that teleports to room 2 (safe). Final
    event sequence: BAT, PlayerTeleported(5→12), BAT, PlayerTeleported(12→2).

    Room 2 neighbors {1, 3, 10}; we keep those clear of hazards. Player
    starts at 5; bats at (5, 12); wumpus at 11, pits at 13, 14."""
    world = World(
        player_room=5,
        wumpus_rooms=(11,),
        pit_rooms=(13, 14),
        bat_rooms=(5, 12),
        arrows=5,
        turn=1,
        alive=True,
        pending_prompt=None,
        pending_arrow_path=(),
    )
    rng = _ScriptedRandintList(
        [12, 2]
    )  # first bat → 12 (another bat); second → 2 (safe)

    new_world, events = hazard_resolve(world, rng)  # type: ignore[arg-type]

    kinds = [type(e).__name__ for e in events]
    assert kinds == [
        "HazardTriggered",
        "PlayerTeleported",
        "HazardTriggered",
        "PlayerTeleported",
    ], f"Expected bat → bat → safe sequence; got {kinds}."
    assert isinstance(events[0], HazardTriggered) and events[0].kind == "BAT"
    assert isinstance(events[1], PlayerTeleported) and events[1].to_room == 12
    assert isinstance(events[2], HazardTriggered) and events[2].kind == "BAT"
    assert isinstance(events[3], PlayerTeleported) and events[3].to_room == 2
    assert new_world.player_room == 2
    assert new_world.alive is True


def test_b6_bat_chain_exceeding_max_chain_raises_recursion_error() -> None:
    """Pathological case: every teleport target is also a bat (which is
    forbidden by Yob's cave-gen invariant, but we engineer it here to
    exercise the safeguard). The dispatcher raises RecursionError once
    `depth > MAX_BAT_CHAIN`. This should never fire under a real Yob layout."""
    # Place a bat at every room 1..20 — the worst-case invariant violation.
    # The teleport target is always a bat-room, so the chain never bottoms out.
    all_rooms = tuple(range(1, 21))
    world = World(
        player_room=1,
        wumpus_rooms=(),  # No wumpus so the only hazard is bat at every room.
        pit_rooms=(),
        bat_rooms=all_rooms,
        arrows=5,
        turn=1,
        alive=True,
        pending_prompt=None,
        pending_arrow_path=(),
    )
    # Script MAX_BAT_CHAIN + 5 teleport draws so the safeguard fires.
    rng = _ScriptedRandintList([1] * (MAX_BAT_CHAIN + 5))

    with pytest.raises(RecursionError, match="MAX_BAT_CHAIN"):
        hazard_resolve(world, rng)  # type: ignore[arg-type]
