"""Arrow walk — Yob `bas` 3170-3360 arrow-resolution dispatcher.

Pure function over `World` per ADR-001 (hybrid paradigm). The engine calls
`walk_arrow` after the shoot-collection sub-state-machine emits `ArrowFired`
(R1-S05). The walk produces an `ArrowPathStep` per visited room, then a
terminal arm based on the final room:

    - final room == wumpus's room → ArrowHitWumpus + GameEnded(wumpus_shot)
      (arrow count NOT decremented — Yob bug-for-bug, the game ends first)
    - final room == player's room  → ArrowHitPlayer + ArrowCountChanged
      (Yob bug-for-bug D11: ONLY on a FINAL room match; mid-path-through-player
      does NOT kill — line 3340-3360 falls through to 3270 which decrements)
    - otherwise                    → ArrowMissed + wumpus startle (FNC(0)) +
      ArrowCountChanged; if the startled wumpus lands on the player,
      GameEnded(eaten_after_bump); if the arrow count reaches 0,
      GameEnded(out_of_arrows).

The walk consumes RNG for:
  - one `rng.randint(1, 3)` per missing-tunnel deflection (Yob `FNB(1)`,
    line 3170-3210), picking the 1st/2nd/3rd of the current room's sorted
    adjacents
  - one `rng.randint(1, 4)` for the FNC(0) startle on a miss (reused from
    `move_wumpus_startle` — R1-S03)

The function is the engine's driving port at the domain scope per the
crafter port-to-port mandate; the `Game.step` shell wires it after the
shoot sub-state-machine emits `ArrowFired`.
"""

from __future__ import annotations

import random

from wumpus.constants import DODECAHEDRON
from wumpus.engine.hash import internal_state_hash
from wumpus.engine.startle import move_wumpus_startle
from wumpus.events import (
    SCHEMA_VERSION,
    ArrowCountChanged,
    ArrowHitPlayer,
    ArrowHitWumpus,
    ArrowMissed,
    ArrowPathStep,
    Event,
    GameEnded,
)
from wumpus.types import Snapshot, World

# Surface placeholder per SC8 — no Yob strings in engine code.
_R1S06_SURFACE_VARIANT: str = "<placeholder>"
_R1S06_ENGINE_VERSION: str = "0.0.0"
_R1S06_SURFACE_ID: str = "<placeholder>"


def walk_arrow(
    world: World, path: tuple[int, ...], rng: random.Random
) -> tuple[World, list[Event]]:
    """Walk the collected arrow `path` through the dodecahedron from
    `world.player_room`. Returns the post-walk World and the event list.

    The function is pure (no I/O, no surface text). The Game shell stamps
    `rng_cursor` and the `GameEnded.final_snapshot` metadata before
    emission.

    Algorithm (Yob `bas` 3170-3360):
      1. Start at `world.player_room`.
      2. For each slot K in the path:
         a. If `path[K]` ∈ adjacents(current), arrow steps there
            (deflected=False).
         b. Else arrow steps to `sorted_adjacents(current)[rng.randint(1,3)-1]`
            (deflected=True) and the remaining path is DISCARDED.
      3. Final room is the arrow's resting room.
      4. If final == wumpus → ArrowHitWumpus + GameEnded(wumpus_shot, win),
         arrow count NOT decremented.
      5. If final == player → ArrowHitPlayer + ArrowCountChanged(arrows-1).
         (Game continues unless arrows is now 0 — out_of_arrows below.)
      6. Else → ArrowMissed + startle + ArrowCountChanged(arrows-1).
         If startled wumpus lands on player → GameEnded(eaten_after_bump).
      7. If arrows is now 0 → GameEnded(out_of_arrows, lose).
    """
    events: list[Event] = []
    current_room = world.player_room

    # 1-2: walk the path slots, emitting one ArrowPathStep per visited room.
    for slot_room in path:
        if slot_room in DODECAHEDRON[current_room]:
            current_room = slot_room
            events.append(_arrow_path_step(world, current_room, deflected=False))
            continue
        # Missing tunnel: take a random adjacent (Yob FNB(1)) and STOP
        # consulting remaining path slots.
        draw = rng.randint(1, 3)
        sorted_adjacent = sorted(DODECAHEDRON[current_room])
        current_room = sorted_adjacent[draw - 1]
        events.append(_arrow_path_step(world, current_room, deflected=True))
        break

    final_room = current_room

    # 4: hit wumpus — game ends first, arrow count NOT decremented.
    if final_room == world.wumpus_rooms[0]:
        events.append(_arrow_hit_wumpus(world, final_room))
        events.append(_game_ended_wumpus_shot(world))
        new_world = _mark_dead(world)
        return new_world, events

    # 5: hit player (FINAL match only) — decrement as if missed.
    if final_room == world.player_room:
        events.append(_arrow_hit_player(world, final_room))
        new_arrows = world.arrows - 1
        new_world = _with_arrows(world, new_arrows)
        events.append(_arrow_count_changed(new_world, new_arrows))
        if new_arrows <= 0:
            events.append(_game_ended_out_of_arrows(new_world))
            new_world = _mark_dead(new_world)
        return new_world, events

    # 6: miss — startle the wumpus, decrement arrow count.
    events.append(_arrow_missed(world))
    startled_world, startled_event = move_wumpus_startle(world, rng)
    events.append(startled_event)

    if startled_event.ate_player:
        # Startled wumpus landed on the player → eaten_after_bump.
        # Per the slice brief: still decrement the arrow count for the miss.
        new_arrows = startled_world.arrows - 1
        new_world = _with_arrows(startled_world, new_arrows)
        events.append(_arrow_count_changed(new_world, new_arrows))
        events.append(_game_ended_eaten_after_bump(new_world))
        new_world = _mark_dead(new_world)
        return new_world, events

    # Plain miss: decrement and check out-of-arrows.
    new_arrows = startled_world.arrows - 1
    new_world = _with_arrows(startled_world, new_arrows)
    events.append(_arrow_count_changed(new_world, new_arrows))
    if new_arrows <= 0:
        events.append(_game_ended_out_of_arrows(new_world))
        new_world = _mark_dead(new_world)
    return new_world, events


# ---------------------------------------------------------------------------
# Event factories — keep `walk_arrow` readable by hoisting ceremony.
# ---------------------------------------------------------------------------


def _arrow_path_step(world: World, room: int, *, deflected: bool) -> ArrowPathStep:
    return ArrowPathStep(
        schema_version=SCHEMA_VERSION,
        turn=world.turn,
        surface_variant=_R1S06_SURFACE_VARIANT,
        internal_state_hash=internal_state_hash(world),
        rng_cursor="",
        room=room,
        deflected=deflected,
    )


def _arrow_hit_wumpus(world: World, room: int) -> ArrowHitWumpus:
    return ArrowHitWumpus(
        schema_version=SCHEMA_VERSION,
        turn=world.turn,
        surface_variant=_R1S06_SURFACE_VARIANT,
        internal_state_hash=internal_state_hash(world),
        rng_cursor="",
        room=room,
    )


def _arrow_hit_player(world: World, room: int) -> ArrowHitPlayer:
    return ArrowHitPlayer(
        schema_version=SCHEMA_VERSION,
        turn=world.turn,
        surface_variant=_R1S06_SURFACE_VARIANT,
        internal_state_hash=internal_state_hash(world),
        rng_cursor="",
        room=room,
    )


def _arrow_missed(world: World) -> ArrowMissed:
    return ArrowMissed(
        schema_version=SCHEMA_VERSION,
        turn=world.turn,
        surface_variant=_R1S06_SURFACE_VARIANT,
        internal_state_hash=internal_state_hash(world),
        rng_cursor="",
    )


def _arrow_count_changed(world: World, new_count: int) -> ArrowCountChanged:
    return ArrowCountChanged(
        schema_version=SCHEMA_VERSION,
        turn=world.turn,
        surface_variant=_R1S06_SURFACE_VARIANT,
        internal_state_hash=internal_state_hash(world),
        rng_cursor="",
        new_count=new_count,
    )


def _game_ended_wumpus_shot(world: World) -> GameEnded:
    return GameEnded(
        schema_version=SCHEMA_VERSION,
        turn=world.turn,
        surface_variant=_R1S06_SURFACE_VARIANT,
        internal_state_hash=internal_state_hash(world),
        rng_cursor="",
        outcome="wumpus_shot",
        message_kind="win",
        final_snapshot=_snapshot_for_terminal(world),
    )


def _game_ended_out_of_arrows(world: World) -> GameEnded:
    return GameEnded(
        schema_version=SCHEMA_VERSION,
        turn=world.turn,
        surface_variant=_R1S06_SURFACE_VARIANT,
        internal_state_hash=internal_state_hash(world),
        rng_cursor="",
        outcome="out_of_arrows",
        message_kind="lose",
        final_snapshot=_snapshot_for_terminal(world),
    )


def _game_ended_eaten_after_bump(world: World) -> GameEnded:
    return GameEnded(
        schema_version=SCHEMA_VERSION,
        turn=world.turn,
        surface_variant=_R1S06_SURFACE_VARIANT,
        internal_state_hash=internal_state_hash(world),
        rng_cursor="",
        outcome="eaten_after_bump",
        message_kind="lose",
        final_snapshot=_snapshot_for_terminal(world),
    )


# ---------------------------------------------------------------------------
# World copy helpers — mirror hazard_resolve._mark_dead / _with_arrows style.
# ---------------------------------------------------------------------------


def _with_arrows(world: World, arrows: int) -> World:
    return World(
        player_room=world.player_room,
        wumpus_rooms=world.wumpus_rooms,
        pit_rooms=world.pit_rooms,
        bat_rooms=world.bat_rooms,
        arrows=arrows,
        turn=world.turn,
        alive=world.alive,
        pending_prompt=world.pending_prompt,
        pending_arrow_path=world.pending_arrow_path,
        pending_path_length=world.pending_path_length,
    )


def _mark_dead(world: World) -> World:
    return World(
        player_room=world.player_room,
        wumpus_rooms=world.wumpus_rooms,
        pit_rooms=world.pit_rooms,
        bat_rooms=world.bat_rooms,
        arrows=world.arrows,
        turn=world.turn,
        alive=False,
        pending_prompt=world.pending_prompt,
        pending_arrow_path=world.pending_arrow_path,
        pending_path_length=world.pending_path_length,
    )


def _snapshot_for_terminal(world: World) -> Snapshot:
    """Placeholder Snapshot for `GameEnded.final_snapshot` from a pure-function
    walk path. The Game shell rewrites this with the engine's real Snapshot
    metadata via `_stamp_engine_metadata` before emission."""
    return Snapshot(
        schema_version=SCHEMA_VERSION,
        engine_version=_R1S06_ENGINE_VERSION,
        seed=0,
        rng_cursor="",
        surface_id=_R1S06_SURFACE_ID,
        world=world,
        active_escalation_rules=(),
    )


__all__ = ["walk_arrow"]
