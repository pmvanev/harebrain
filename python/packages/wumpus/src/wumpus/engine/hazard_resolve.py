"""Hazard resolution — Yob `bas` 4140-4310 dispatcher.

Pure function over `World` per ADR-001 (hybrid paradigm). The engine calls
`hazard_resolve` from `Game.step` after `MoveResolved` fires for a successful
move; if the player's new room contains a hazard, the function emits the
hazard-kind-specific event chain and (if terminal) `GameEnded`.

R1-S03 shipped the wumpus arm (4150-4200). R1-S04 extends with:

    - Pit arm (4220-4250): emit `HazardTriggered(PIT)` + `GameEnded(fell_in_pit)`.
    - Bat arm (4270-4300): pick a uniform-random destination via
      `rng.randint(1, 20)` (Yob's `FNB(1)` for bat snatch is uniform over
      rooms 1..20, NOT just adjacents — see archived journey yaml step 4 spec,
      lines 211-260), emit `HazardTriggered(BAT)` + `PlayerTeleported`,
      then RECURSE into the dispatcher on the new room (Yob's `GOTO 4130`).

The recursion is bounded by `MAX_BAT_CHAIN` — a defensive cap that should
never fire under the cave-gen invariant (bats are not co-located, so a
bat → bat → bat chain to infinity is theoretically impossible). The
safeguard exists for paranoia: if the invariant ever gets violated by a
test fixture or a downstream variant, the engine raises a clear
`RecursionError` rather than looping forever.

After the bat arm RECURSIVELY resolves the new room's hazards, the
returned event list already contains:
    [HazardTriggered(BAT), PlayerTeleported, ...recursive events...]

The Game shell (`Game.step`) is responsible for re-emitting sense events
and `LocationReported` for the final teleport destination, but ONLY if
the recursion did NOT terminate the game. The shell decides this by
inspecting the event list for `GameEnded`.
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
    PlayerTeleported,
)
from wumpus.types import Snapshot, World

# Surface placeholder per SC8 — no Yob strings in engine code.
_R1S04_SURFACE_VARIANT: str = "<placeholder>"

# Engine-version + surface-id placeholders mirror the Game shell. Real values
# flow through `Game._stamp_engine_metadata` when the engine wires this
# function; the pure-function path defaults to placeholder strings (used by
# unit tests that exercise `hazard_resolve` in isolation).
_R1S04_ENGINE_VERSION: str = "0.0.0"
_R1S04_SURFACE_ID: str = "<placeholder>"

# Defensive recursion cap for bat → bat → ... chains. Yob's cave-gen
# invariant forbids co-located bats, so a chain longer than a handful of
# steps is statistically impossible. The cap exists to prevent a pathological
# infinite loop if the invariant ever gets violated by a test fixture or a
# downstream variant config. If the cap fires under a real Yob layout, that
# is itself a Yob-fidelity bug worth investigating.
MAX_BAT_CHAIN: int = 100


def hazard_resolve(world: World, rng: random.Random) -> tuple[World, list[Event]]:
    """Resolve any hazard at `world.player_room` per HAZARD_ORDER.

    Returns the new World value and an ordered event list. The event list
    is empty (and the world unchanged) when no recognized hazard occupies
    the player's room.

    Hazard order is fixed at (wumpus, pit, bat) per Yob `bas` 4140-4310.
    Each arm short-circuits the dispatcher once it fires (Yob ends the move
    on the first hazard match; bat is special — it teleports the player and
    recursively re-enters the dispatcher on the new room).
    """
    return _hazard_resolve_with_depth(world, rng, depth=0)


def _hazard_resolve_with_depth(
    world: World, rng: random.Random, *, depth: int
) -> tuple[World, list[Event]]:
    """Internal hazard dispatcher with bounded bat-recursion depth.

    `depth` counts the number of bat teleports already in flight on the
    current call chain; the top-level entry point passes `depth=0`. The
    bat arm increments and recurses; if `depth` reaches `MAX_BAT_CHAIN`
    the function raises `RecursionError` rather than continue.
    """
    if depth > MAX_BAT_CHAIN:
        raise RecursionError(
            f"Bat-teleport chain exceeded MAX_BAT_CHAIN={MAX_BAT_CHAIN}. "
            f"This indicates a Yob-fidelity bug: the cave-gen invariant "
            f"that forbids co-located bats has been violated, allowing an "
            f"infinite bat → bat → ... chain. Investigate the world layout."
        )

    events: list[Event] = []
    current_world = world

    for kind in HAZARD_ORDER:
        if kind == "wumpus" and current_world.player_room in current_world.wumpus_rooms:
            current_world, kind_events = _resolve_wumpus(current_world, rng)
            events.extend(kind_events)
            break  # Yob ends the move on the first hazard match.
        if kind == "pit" and current_world.player_room in current_world.pit_rooms:
            kind_events = _resolve_pit(current_world)
            events.extend(kind_events)
            current_world = _mark_dead(current_world)
            break
        if kind == "bat" and current_world.player_room in current_world.bat_rooms:
            current_world, kind_events = _resolve_bat(current_world, rng, depth=depth)
            events.extend(kind_events)
            break

    return current_world, events


def _resolve_wumpus(world: World, rng: random.Random) -> tuple[World, list[Event]]:
    """Yob `bas` 4150-4200: bump triggers HazardTriggered + startle; if the
    startled wumpus lands on the player, the game ends (eaten_after_bump)."""
    bump_event = HazardTriggered(
        schema_version=SCHEMA_VERSION,
        turn=world.turn,
        surface_variant=_R1S04_SURFACE_VARIANT,
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
            surface_variant=_R1S04_SURFACE_VARIANT,
            internal_state_hash=internal_state_hash(new_world),
            rng_cursor="",
            outcome="eaten_after_bump",
            message_kind="lose",
            final_snapshot=_snapshot_for_terminal(new_world),
        )
        events.append(ended_event)
        new_world = _mark_dead(new_world)

    return new_world, events


def _resolve_pit(world: World) -> list[Event]:
    """Yob `bas` 4220-4250: pit fall — HazardTriggered(PIT) + GameEnded(fell_in_pit).

    Pit resolution consumes no RNG (Yob just prints the death message). The
    caller is responsible for marking the world dead via `_mark_dead`.
    """
    bump_event = HazardTriggered(
        schema_version=SCHEMA_VERSION,
        turn=world.turn,
        surface_variant=_R1S04_SURFACE_VARIANT,
        internal_state_hash=internal_state_hash(world),
        rng_cursor="",
        kind="PIT",
        room=world.player_room,
    )
    ended_event = GameEnded(
        schema_version=SCHEMA_VERSION,
        turn=world.turn,
        surface_variant=_R1S04_SURFACE_VARIANT,
        internal_state_hash=internal_state_hash(world),
        rng_cursor="",
        outcome="fell_in_pit",
        message_kind="lose",
        final_snapshot=_snapshot_for_terminal(world),
    )
    return [bump_event, ended_event]


def _resolve_bat(
    world: World, rng: random.Random, *, depth: int
) -> tuple[World, list[Event]]:
    """Yob `bas` 4270-4300: bat snatch — HazardTriggered(BAT) + PlayerTeleported
    to a uniform-random destination over rooms 1..20, then RECURSE into the
    dispatcher on the new room (Yob's `GOTO 4130`).

    The destination is drawn via `rng.randint(1, 20)` — uniform over the full
    room range per Yob's `FNB(1)` for bat snatch (NOT restricted to adjacents).
    The recursion may emit further hazard events if the new room has its
    own hazard (another bat, a pit, the wumpus).
    """
    from_room = world.player_room
    bump_event = HazardTriggered(
        schema_version=SCHEMA_VERSION,
        turn=world.turn,
        surface_variant=_R1S04_SURFACE_VARIANT,
        internal_state_hash=internal_state_hash(world),
        rng_cursor="",
        kind="BAT",
        room=from_room,
    )

    to_room = rng.randint(1, 20)
    teleported_world = World(
        player_room=to_room,
        wumpus_rooms=world.wumpus_rooms,
        pit_rooms=world.pit_rooms,
        bat_rooms=world.bat_rooms,
        arrows=world.arrows,
        turn=world.turn,
        alive=world.alive,
        pending_prompt=world.pending_prompt,
        pending_arrow_path=world.pending_arrow_path,
    )
    teleport_event = PlayerTeleported(
        schema_version=SCHEMA_VERSION,
        turn=teleported_world.turn,
        surface_variant=_R1S04_SURFACE_VARIANT,
        internal_state_hash=internal_state_hash(teleported_world),
        rng_cursor="",
        from_room=from_room,
        to_room=to_room,
        cause="bat",
    )
    events: list[Event] = [bump_event, teleport_event]

    # Recurse: the new room may have its own hazard (bat, pit, wumpus). Yob's
    # GOTO 4130 re-enters the move-resolution path. We re-enter the hazard
    # dispatcher directly (not the full move path) because the bat snatch
    # is not a "move" — no MoveResolved fires for the teleport, no turn
    # counter advance, no adjacency check.
    recursive_world, recursive_events = _hazard_resolve_with_depth(
        teleported_world, rng, depth=depth + 1
    )
    events.extend(recursive_events)
    return recursive_world, events


def _mark_dead(world: World) -> World:
    """Return a copy of `world` with `alive=False`. Used by terminal hazard
    arms (wumpus eat-bump, pit fall) so callers can short-circuit further
    turn processing."""
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
    )


def _snapshot_for_terminal(world: World) -> Snapshot:
    """Build a Snapshot for `GameEnded.final_snapshot` from the terminal world.

    Pure-function tests exercise `hazard_resolve` directly; in that path the
    seed / rng_cursor / surface_id metadata is unknown to the resolver, so
    the snapshot carries placeholder values for those fields. The engine
    shell (`Game._stamp_engine_metadata`) overrides the snapshot with the
    Game's real metadata before emission.
    """
    return Snapshot(
        schema_version=SCHEMA_VERSION,
        engine_version=_R1S04_ENGINE_VERSION,
        seed=0,
        rng_cursor="",
        surface_id=_R1S04_SURFACE_ID,
        world=world,
        active_escalation_rules=(),
    )


__all__ = ["hazard_resolve", "MAX_BAT_CHAIN"]
