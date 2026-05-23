"""Unit tests for `wumpus.engine.sense.emit_senses_for_room` (R1-S02).

Behaviors covered (3 distinct, budget = 6):
    B1. Multi-kind adjacent hazards emit SenseEmitted in L-array order
        (WUMPUS, then PIT, then BAT — per SENSE_ORDER).
    B2. Multiple same-kind adjacent hazards emit the sense once per match
        (per-room iteration inside the kind).
    B3. No adjacent hazards emits an empty event tuple.

Additionally, SENSE_ORDER itself is the L-array tabulation Yob's BASIC source
pins (`bas` lines 2020-2120). It is structurally tested once for shape; the
verbatim value lives in the constant and a single pin test is sufficient.

All tests address the pure-function driving port `emit_senses_for_room`
directly: that signature IS the driving port for this domain function
(per port-to-port testing at domain scope — see SKILL).
"""

from __future__ import annotations

import pytest

from wumpus.constants import SENSE_ORDER
from wumpus.engine.sense import emit_senses_for_room
from wumpus.events import SenseEmitted
from wumpus.types import World


def _world(
    *,
    player_room: int = 1,
    wumpus_rooms: tuple[int, ...] = (),
    pit_rooms: tuple[int, ...] = (),
    bat_rooms: tuple[int, ...] = (),
) -> World:
    """Construct a minimal Tier-A1 World for sense-emission tests.

    Sense emission cares only about which rooms hold which hazards relative
    to the entered room. arrows / turn / alive are irrelevant to sense logic.
    """
    return World(
        player_room=player_room,
        wumpus_rooms=wumpus_rooms,
        pit_rooms=pit_rooms,
        bat_rooms=bat_rooms,
        arrows=5,
        turn=0,
        alive=True,
        pending_prompt=None,
        pending_arrow_path=(),
    )


# ---------------------------------------------------------------------------
# SENSE_ORDER constant — single pin (L-array kind order, Yob BASIC 2020-2120)
# ---------------------------------------------------------------------------


def test_sense_order_is_yob_l_array_kind_order() -> None:
    """Yob's `FOR J=2 TO 6` walks L(2)=wumpus, L(3..4)=pits, L(5..6)=bats.
    Reduced to distinct kinds in L-array order: (wumpus, pit, bat). The
    per-room iteration over `world.pit_rooms` / `world.bat_rooms` recovers
    the L(3) before L(4), L(5) before L(6) ordering."""
    assert SENSE_ORDER == ("wumpus", "pit", "bat"), (
        f"SENSE_ORDER changed shape: {SENSE_ORDER!r}. Yob-fidelity break — "
        f"see archived shared-artifacts-registry section 'Sense order on room entry'."
    )


# ---------------------------------------------------------------------------
# B1 — L-array order across kinds
# ---------------------------------------------------------------------------


def test_b1_emits_wumpus_smell_before_pit_draft_before_bat_nearby() -> None:
    """Room 1 (dodecahedron neighbors {2, 5, 8}). Place one of each hazard
    on each neighbor. Expect three SenseEmitted in L-array kind order:
    WUMPUS_SMELL, PIT_DRAFT, BAT_NEARBY."""
    world = _world(
        player_room=1,
        wumpus_rooms=(2,),
        pit_rooms=(5, 11),  # only pit@5 is adjacent to room 1
        bat_rooms=(8, 14),  # only bat@8 is adjacent to room 1
    )
    events = emit_senses_for_room(world, room=1)

    assert tuple(e.kind for e in events) == (
        "WUMPUS_SMELL",
        "PIT_DRAFT",
        "BAT_NEARBY",
    ), (
        f"Sense events were emitted in {[e.kind for e in events]!r}; "
        f"expected ('WUMPUS_SMELL', 'PIT_DRAFT', 'BAT_NEARBY') per SENSE_ORDER."
    )


def test_b1_carries_cause_room_for_each_hazard() -> None:
    """Each SenseEmitted carries `cause_room`: the room number of the hazard
    that triggered it. Pedagogically useful for replay analysis."""
    world = _world(
        player_room=1,
        wumpus_rooms=(2,),
        pit_rooms=(5, 11),
        bat_rooms=(8, 14),
    )
    events = emit_senses_for_room(world, room=1)

    by_kind = {e.kind: e.cause_room for e in events}
    assert by_kind == {
        "WUMPUS_SMELL": 2,
        "PIT_DRAFT": 5,
        "BAT_NEARBY": 8,
    }, (
        f"SenseEmitted.cause_room values were {by_kind!r}; "
        f"expected each kind's adjacent hazard room."
    )


# ---------------------------------------------------------------------------
# B2 — Same-kind repetition (per-room iteration within a kind)
# ---------------------------------------------------------------------------


def test_b2_two_adjacent_pits_emit_two_pit_drafts_in_placement_order() -> None:
    """Both pits (rooms 2 and 5) adjacent to room 1. Yob's L(3) before L(4)
    iteration becomes per-room iteration over `world.pit_rooms` — placement
    order. The two PIT_DRAFT events MUST carry cause_room=2 then cause_room=5."""
    world = _world(
        player_room=1,
        wumpus_rooms=(11,),  # not adjacent to 1
        pit_rooms=(2, 5),  # both adjacent
        bat_rooms=(14, 17),  # neither adjacent
    )
    events = emit_senses_for_room(world, room=1)

    assert all(isinstance(e, SenseEmitted) for e in events), (
        f"Non-SenseEmitted event slipped in: {events!r}"
    )
    pit_drafts = [e for e in events if e.kind == "PIT_DRAFT"]
    assert len(pit_drafts) == 2, (
        f"Expected 2 PIT_DRAFT events for two adjacent pits; got {len(pit_drafts)}."
    )
    assert tuple(e.cause_room for e in pit_drafts) == (2, 5), (
        f"PIT_DRAFT cause_room order was {[e.cause_room for e in pit_drafts]!r}; "
        f"expected (2, 5) per world.pit_rooms placement order."
    )


# ---------------------------------------------------------------------------
# B3 — Empty result when no adjacency
# ---------------------------------------------------------------------------


def test_b3_no_adjacent_hazards_emits_empty_tuple() -> None:
    """Room 2 (neighbors {1, 3, 10}). Park every hazard far from there:
    wumpus@20, pits@15/6, bats@11/12. No adjacency → no events."""
    world = _world(
        player_room=2,
        wumpus_rooms=(20,),
        pit_rooms=(15, 6),
        bat_rooms=(11, 12),
    )
    events = emit_senses_for_room(world, room=2)
    assert events == (), (
        f"Expected empty tuple when no hazards are adjacent; got {events!r}."
    )


# ---------------------------------------------------------------------------
# B3 (paired variation) — hazard in entered room itself is NOT a sense source
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field_name,layout_kwargs,expected_kind",
    [
        ("wumpus_at_target", {"wumpus_rooms": (1,)}, "WUMPUS_SMELL"),
        ("pit_at_target", {"pit_rooms": (1, 11)}, "PIT_DRAFT"),
        ("bat_at_target", {"bat_rooms": (1, 14)}, "BAT_NEARBY"),
    ],
)
def test_b3_hazard_in_target_room_itself_does_not_emit_sense(
    field_name: str,
    layout_kwargs: dict[str, tuple[int, ...]],
    expected_kind: str,
) -> None:
    """Sense events fire on ADJACENCY, not co-location. A hazard sitting in
    the room the player just entered MUST NOT produce a SenseEmitted of its
    kind (that would double-count once R1-S03/R1-S04 land HazardTriggered).

    All other hazards parked non-adjacent to room 1 to isolate the contract.
    """
    base_kwargs: dict[str, tuple[int, ...]] = {
        "wumpus_rooms": (11,),  # non-adjacent to 1
        "pit_rooms": (14, 17),  # non-adjacent to 1
        "bat_rooms": (15, 16),  # non-adjacent to 1
    }
    base_kwargs.update(layout_kwargs)
    world = _world(player_room=1, **base_kwargs)
    events = emit_senses_for_room(world, room=1)

    kinds_emitted = {e.kind for e in events}
    assert expected_kind not in kinds_emitted, (
        f"Hazard at the entered room (room 1) erroneously triggered a "
        f"{expected_kind} sense. Field under test: {field_name}. "
        f"Emitted kinds: {kinds_emitted!r}."
    )
