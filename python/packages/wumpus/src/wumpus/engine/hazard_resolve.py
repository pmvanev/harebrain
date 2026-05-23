"""Hazard resolution — Yob `bas` 4140-4310 dispatcher.

Pure function over `World` per ADR-001 (hybrid paradigm). The engine calls
`hazard_resolve` from `Game.step` after `MoveResolved` fires for a successful
move; if the player's new room contains a hazard, the function emits the
hazard-kind-specific event chain and (if terminal) `GameEnded`.

R1-S03 ships ONLY the wumpus arm (4150-4200):
    1. Emit `HazardTriggered(WUMPUS, room=player_room)`.
    2. Call `move_wumpus_startle` → emit `WumpusStartled`.
    3. If the startled wumpus landed on the player, emit
       `GameEnded(outcome="eaten_after_bump", message_kind="lose")`.

R1-S04 extends with the pit arm (4220-4250 → `GameEnded(fell_in_pit)`) and
the bat arm (4270-4300 → `PlayerTeleported` + recursive re-entry). The
dispatcher walks `HAZARD_ORDER` so the slice extension is a per-kind handler
addition, not a re-write.

`hazard_resolve` is a no-op when the player's room contains none of the
recognized hazards. Pit / bat at the player's room at R1-S03 are explicitly
silenced (no events emitted, world unchanged) — the R1-S04 slice's tests
will fail when they add pit/bat resolution and find the no-op.
"""

from __future__ import annotations

import random

from wumpus.constants import HAZARD_ORDER
from wumpus.engine.hash import internal_state_hash
from wumpus.engine.startle import move_wumpus_startle
from wumpus.events import (
    SCHEMA_VERSION,
    Event,
    GameEnded,
    HazardTriggered,
)
from wumpus.types import Snapshot, World

# Surface placeholder per SC8 — no Yob strings in engine code.
_R1S03_SURFACE_VARIANT: str = "<placeholder>"

# Engine-version + surface-id placeholders mirror the Game shell. Real values
# flow through `Game._build_game_ended_snapshot` when the engine wires this
# function; the pure-function path defaults to placeholder strings (used by
# unit tests that exercise `hazard_resolve` in isolation).
_R1S03_ENGINE_VERSION: str = "0.0.0"
_R1S03_SURFACE_ID: str = "<placeholder>"


def hazard_resolve(world: World, rng: random.Random) -> tuple[World, list[Event]]:
    """Resolve any hazard at `world.player_room` per HAZARD_ORDER.

    Returns the new World value and an ordered event list. The event list
    is empty (and the world unchanged) when no recognized hazard occupies
    the player's room.

    At R1-S03 the dispatcher recognizes "wumpus", "pit", and "bat" by name
    (per HAZARD_ORDER) but only the "wumpus" handler is implemented — pit
    and bat are no-ops until R1-S04 lands.
    """
    events: list[Event] = []
    current_world = world

    for kind in HAZARD_ORDER:
        if kind == "wumpus" and world.player_room in world.wumpus_rooms:
            current_world, kind_events = _resolve_wumpus(current_world, rng)
            events.extend(kind_events)
            # If the player died, no later hazard fires.
            if any(isinstance(e, GameEnded) for e in kind_events):
                break
        # "pit" and "bat" handlers land at R1-S04. Intentional fall-through.

    return current_world, events


def _resolve_wumpus(world: World, rng: random.Random) -> tuple[World, list[Event]]:
    """Yob `bas` 4150-4200: bump triggers HazardTriggered + startle; if the
    startled wumpus lands on the player, the game ends (eaten_after_bump)."""
    bump_event = HazardTriggered(
        schema_version=SCHEMA_VERSION,
        turn=world.turn,
        surface_variant=_R1S03_SURFACE_VARIANT,
        internal_state_hash=internal_state_hash(world),
        rng_cursor="",
        kind="WUMPUS",
        room=world.player_room,
    )

    new_world, startled_event = move_wumpus_startle(world, rng)
    events: list[Event] = [bump_event, startled_event]

    if startled_event.ate_player:
        ended_event = GameEnded(
            schema_version=SCHEMA_VERSION,
            turn=new_world.turn,
            surface_variant=_R1S03_SURFACE_VARIANT,
            internal_state_hash=internal_state_hash(new_world),
            rng_cursor="",
            outcome="eaten_after_bump",
            message_kind="lose",
            final_snapshot=_snapshot_for_terminal(new_world),
        )
        events.append(ended_event)
        # Mark the world dead so callers can short-circuit.
        new_world = World(
            player_room=new_world.player_room,
            wumpus_rooms=new_world.wumpus_rooms,
            pit_rooms=new_world.pit_rooms,
            bat_rooms=new_world.bat_rooms,
            arrows=new_world.arrows,
            turn=new_world.turn,
            alive=False,
            pending_prompt=new_world.pending_prompt,
            pending_arrow_path=new_world.pending_arrow_path,
        )

    return new_world, events


def _snapshot_for_terminal(world: World) -> Snapshot:
    """Build a Snapshot for `GameEnded.final_snapshot` from the terminal world.

    Pure-function tests exercise `hazard_resolve` directly; in that path the
    seed / rng_cursor / surface_id metadata is unknown to the resolver, so
    the snapshot carries placeholder values for those fields. The engine
    shell (`Game._wire_hazard_resolve`) may override the snapshot with the
    Game's real metadata before emission if a richer terminal snapshot is
    needed; R1-S03's contract only pins `final_snapshot.world.player_room`.
    """
    return Snapshot(
        schema_version=SCHEMA_VERSION,
        engine_version=_R1S03_ENGINE_VERSION,
        seed=0,
        rng_cursor="",
        surface_id=_R1S03_SURFACE_ID,
        world=world,
        active_escalation_rules=(),
    )


__all__ = ["hazard_resolve"]
