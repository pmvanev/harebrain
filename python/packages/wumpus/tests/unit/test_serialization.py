"""Unit tests for `wumpus.serialization.event_to_dict` / `event_from_dict`
(R2-S01).

Behavior under test:
  - `event_to_dict(event)` produces a JSON-encodable dict for every event
    type, including the `type` discriminator and nested
    Snapshot/World/tuple fields.
  - `event_from_dict(d)` round-trips back to the original event value.
  - Unknown `type` discriminators raise ValueError.
  - Tuple fields land as tuples on the from-dict path (not lists).

Port-to-port testing: the public functions ARE the driving ports (per the
nw-tdd-methodology mandate that pure module functions are their own driving
ports). We invoke them directly and assert on return values.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from hypothesis import given, settings, strategies as st

from wumpus.events import (
    SCHEMA_VERSION,
    ArrowFired,
    GameEnded,
    GameStarted,
    LocationReported,
    MoveAttempted,
    PromptIssued,
)
from wumpus.serialization import event_from_dict, event_to_dict
from wumpus.types import Snapshot, World


def _base_kwargs(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "turn": 0,
        "surface_variant": "yob",
        "internal_state_hash": "deadbeef",
        "rng_cursor": "",
        "monotonic_turn": 0,
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# Behavior 1: round-trip equality for simple events
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "event",
    [
        MoveAttempted(**_base_kwargs(), target_room=5, accepted=True),
        ArrowFired(**_base_kwargs(), path=(7, 14, 12)),
        LocationReported(**_base_kwargs(), room=5, adjacencies=(1, 4, 6)),
        PromptIssued(
            **_base_kwargs(), kind="shoot_path_room", context={"slot": 1, "of": 3}
        ),
        GameStarted(
            **_base_kwargs(),
            seed=42,
            engine_version="0.0.0",
            surface_id="<placeholder>",
            layout_hash="abc",
            active_escalation_rules=(),
        ),
    ],
)
def test_event_round_trips_through_to_dict_and_from_dict(event: Any) -> None:
    """For each canonical event, encode->decode->compare yields equality."""
    payload = event_to_dict(event)
    # Survive JSON normalization: dump+load to simulate a real ledger replay
    # (tuples become lists in JSON, etc.).
    normalized = json.loads(json.dumps(payload))
    restored = event_from_dict(normalized)
    assert restored == event, (
        f"Round-trip mismatch.\n  original: {event!r}\n  restored: {restored!r}"
    )


# ---------------------------------------------------------------------------
# Behavior 2: nested Snapshot/World round-trip (GameEnded.final_snapshot)
# ---------------------------------------------------------------------------


def test_game_ended_with_final_snapshot_round_trips() -> None:
    snapshot = Snapshot(
        schema_version=SCHEMA_VERSION,
        engine_version="0.0.0",
        seed=42,
        rng_cursor="b64==",
        surface_id="<placeholder>",
        world=World(
            player_room=1,
            wumpus_rooms=(11,),
            pit_rooms=(13, 14),
            bat_rooms=(15, 19),
            arrows=5,
            turn=0,
            alive=True,
            pending_prompt=None,
            pending_arrow_path=(),
            pending_path_length=None,
        ),
        active_escalation_rules=(),
    )
    event = GameEnded(
        **_base_kwargs(),
        outcome="wumpus_shot",
        message_kind="win",
        final_snapshot=snapshot,
    )
    payload = json.loads(json.dumps(event_to_dict(event)))
    restored = event_from_dict(payload)
    assert restored == event, (
        f"Nested Snapshot round-trip failed.\n  original: {event!r}\n  restored: {restored!r}"
    )
    # Spot-check that nested tuples re-materialized as tuples (not lists).
    assert isinstance(restored.final_snapshot, Snapshot)  # type: ignore[union-attr]
    assert isinstance(restored.final_snapshot.world.wumpus_rooms, tuple)  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Behavior 3: unknown discriminator raises
# ---------------------------------------------------------------------------


def test_event_from_dict_rejects_unknown_type() -> None:
    payload = {"type": "NoSuchEvent", "schema_version": 1}
    with pytest.raises(ValueError, match="unknown event type"):
        event_from_dict(payload)


def test_event_from_dict_rejects_missing_type_field() -> None:
    payload = {"schema_version": 1}
    with pytest.raises(ValueError, match="missing required 'type'"):
        event_from_dict(payload)


# ---------------------------------------------------------------------------
# Behavior 4: tuple fields land as tuples (not lists) on from_dict
# ---------------------------------------------------------------------------


def test_arrow_fired_path_decodes_back_to_tuple() -> None:
    payload = event_to_dict(ArrowFired(**_base_kwargs(), path=(1, 2, 3, 4, 5)))
    payload_after_json = json.loads(json.dumps(payload))
    # JSON has no tuples; the field arrives as a list. The from_dict path
    # must restore the tuple shape so frozen-dataclass equality holds.
    assert isinstance(payload_after_json["path"], list)
    restored = event_from_dict(payload_after_json)
    assert isinstance(restored.path, tuple)  # type: ignore[union-attr]
    assert restored.path == (1, 2, 3, 4, 5)  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Behavior 5: PBT — any valid MoveAttempted round-trips
# ---------------------------------------------------------------------------


@given(
    target_room=st.integers(min_value=-1, max_value=20),
    accepted=st.booleans(),
    turn=st.integers(min_value=0, max_value=1000),
)
@settings(max_examples=100, deadline=None)
def test_pbt_move_attempted_round_trips(
    target_room: int, accepted: bool, turn: int
) -> None:
    original = MoveAttempted(
        **_base_kwargs(turn=turn),
        target_room=target_room,
        accepted=accepted,
    )
    restored = event_from_dict(json.loads(json.dumps(event_to_dict(original))))
    assert restored == original
