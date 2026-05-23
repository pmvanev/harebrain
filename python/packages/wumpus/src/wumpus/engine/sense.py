"""Sense emission — Yob's L-array iteration on room entry.

Per ADR-001 (hybrid paradigm) this is a pure function over `World`. The engine
calls `emit_senses_for_room` after a successful move resolves; the returned
events are emitted (in order) before `LocationReported`.

Yob's BASIC source (lines 2020-2120) walks `FOR J=2 TO 6` over the L-array:

    L(2) = wumpus
    L(3) = pit #1
    L(4) = pit #2
    L(5) = bat #1
    L(6) = bat #2

For each L(J), the inner `FOR K=1 TO 3` checks whether any tunnel from L(1)
(the player's room) leads to that hazard. The `ON J-1 GOTO` jumps to the
matching print statement.

Reduced to kind+per-room iteration: walk `SENSE_ORDER` (wumpus, pit, bat),
then walk that kind's room collection on the World in placement order. The
per-room walk recovers Yob's L(3)-before-L(4) / L(5)-before-L(6) ordering.

Hazards co-located with the entered room do NOT fire a sense — sense events
fire on ADJACENCY only. Co-located hazards are R1-S03 (wumpus bump) / R1-S04
(pit / bat) territory.
"""

from __future__ import annotations

from typing import Literal

from wumpus.constants import DODECAHEDRON, SENSE_ORDER
from wumpus.engine.hash import internal_state_hash
from wumpus.events import SCHEMA_VERSION, SenseEmitted
from wumpus.types import World

# Surface placeholder per SC8 — no Yob strings in engine code. The kind
# discriminator on the event is what downstream surfaces translate.
_R1S02_SURFACE_VARIANT: str = "<placeholder>"

_KIND_TO_EVENT_KIND: dict[str, Literal["WUMPUS_SMELL", "PIT_DRAFT", "BAT_NEARBY"]] = {
    "wumpus": "WUMPUS_SMELL",
    "pit": "PIT_DRAFT",
    "bat": "BAT_NEARBY",
}


def _rooms_for_kind(world: World, kind: str) -> tuple[int, ...]:
    """Return the World's room tuple for a SENSE_ORDER kind. Placement order
    is preserved (matching Yob's L(3)-before-L(4) iteration)."""
    if kind == "wumpus":
        return world.wumpus_rooms
    if kind == "pit":
        return world.pit_rooms
    if kind == "bat":
        return world.bat_rooms
    raise ValueError(f"Unknown sense kind: {kind!r}. Expected one of {SENSE_ORDER!r}.")


def emit_senses_for_room(world: World, room: int) -> tuple[SenseEmitted, ...]:
    """Return the SenseEmitted events fired on entering `room`, in L-array order.

    Iterates `SENSE_ORDER` (wumpus, pit, bat); for each kind, walks the
    World's placement-order room collection and emits one SenseEmitted per
    hazard adjacent to `room`. A hazard co-located with `room` (i.e. the
    player just walked onto it) does NOT trigger a sense — adjacency only.

    Returns an immutable tuple (frozen value type per SC7) so callers can
    splice the result into an event stream without defensive copying.
    """
    adjacent_rooms: frozenset[int] = DODECAHEDRON[room]
    pre_hash: str = internal_state_hash(world)

    emitted: list[SenseEmitted] = []
    for kind in SENSE_ORDER:
        event_kind = _KIND_TO_EVENT_KIND[kind]
        for hazard_room in _rooms_for_kind(world, kind):
            if hazard_room in adjacent_rooms:
                emitted.append(
                    SenseEmitted(
                        schema_version=SCHEMA_VERSION,
                        turn=world.turn,
                        surface_variant=_R1S02_SURFACE_VARIANT,
                        internal_state_hash=pre_hash,
                        rng_cursor="",
                        kind=event_kind,
                        cause_room=hazard_room,
                    )
                )

    return tuple(emitted)


__all__ = ["emit_senses_for_room"]
