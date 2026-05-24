"""Event <-> dict serialization for the JSONL ledger (R2-S01).

Per ADR-002 (schema evolution policy) every emitted event is serialized to a
dict that conforms to `wumpus/schemas/v<SCHEMA_VERSION>.json`. R2-S02 will use
the inverse `event_from_dict` for replay.

Per ADR-010 (per-type frozen Event dataclasses) we don't subclass Event into
a polymorphic hierarchy; this module dispatches on the `type` discriminator
literal at the boundary instead.

The serialization is JSON-encodable:
  - Tuples become lists (json.dumps does this implicitly)
  - Literal-typed string fields stay as strings
  - Snapshot / World are recursed
  - None stays as None
  - Base64 RNG cursor is already a str

Per SC5 (schema additivity), this module is forward-compatible: unknown
extra fields in an input dict are tolerated by `event_from_dict` only when
the corresponding event dataclass accepts them; otherwise a TypeError
surfaces (caller's responsibility to bump SCHEMA_VERSION + ship a migration
shim in a future slice).
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any

from wumpus.events import (
    ActionChosen,
    ArrowCountChanged,
    ArrowFired,
    ArrowHitPlayer,
    ArrowHitWumpus,
    ArrowMissed,
    ArrowPathStep,
    CrookedPathRejected,
    Event,
    GameEnded,
    GameStarted,
    HazardTriggered,
    InstructionsShown,
    LocationReported,
    MoveAttempted,
    MoveResolved,
    PlayerTeleported,
    PromptIssued,
    SenseEmitted,
    SessionEnded,
    WumpusStartled,
)
from wumpus.types import Snapshot, World

# Discriminator-to-class registry. Maps the `type` Literal value to the
# Event dataclass that owns it. Keep aligned with `wumpus.events.Event`
# union (R2-S01 covers all R0/R1 event types).
_EVENT_REGISTRY: dict[str, type] = {
    "GameStarted": GameStarted,
    "MoveAttempted": MoveAttempted,
    "MoveResolved": MoveResolved,
    "SenseEmitted": SenseEmitted,
    "LocationReported": LocationReported,
    "HazardTriggered": HazardTriggered,
    "WumpusStartled": WumpusStartled,
    "PlayerTeleported": PlayerTeleported,
    "ActionChosen": ActionChosen,
    "PromptIssued": PromptIssued,
    "CrookedPathRejected": CrookedPathRejected,
    "ArrowFired": ArrowFired,
    "ArrowPathStep": ArrowPathStep,
    "ArrowMissed": ArrowMissed,
    "ArrowHitWumpus": ArrowHitWumpus,
    "ArrowHitPlayer": ArrowHitPlayer,
    "ArrowCountChanged": ArrowCountChanged,
    "GameEnded": GameEnded,
    "SessionEnded": SessionEnded,
    "InstructionsShown": InstructionsShown,
}


def event_to_dict(event: Event) -> dict[str, Any]:
    """Serialize `event` to a JSON-encodable dict.

    Handles:
      - Per-event frozen-dataclass fields via `dataclasses.fields`
      - Literal `type` discriminator (the dataclass's `type` attribute)
      - Tuples (converted to lists for JSON)
      - Nested Snapshot / World (recursed)
      - None passthrough
    """
    return _dataclass_to_dict(event)


def event_from_dict(payload: dict[str, Any]) -> Event:
    """Inverse of `event_to_dict`. Dispatches on the `type` discriminator
    and rebuilds the corresponding frozen-dataclass event.

    Raises:
      ValueError: when `type` is missing or unknown.
      TypeError: when required fields are absent / unexpected fields present.
    """
    type_tag = payload.get("type")
    if type_tag is None:
        raise ValueError("event_from_dict: payload missing required 'type' field.")
    event_cls = _EVENT_REGISTRY.get(type_tag)
    if event_cls is None:
        raise ValueError(
            f"event_from_dict: unknown event type {type_tag!r}; "
            f"known: {sorted(_EVENT_REGISTRY)}"
        )
    kwargs = _dict_to_dataclass_kwargs(event_cls, payload)
    return event_cls(**kwargs)  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _dataclass_to_dict(value: Any) -> Any:
    """Recursive JSON-safe converter for frozen dataclasses (Event,
    Snapshot, World) and their nested tuples/lists/primitives."""
    if value is None:
        return None
    if is_dataclass(value) and not isinstance(value, type):
        result: dict[str, Any] = {}
        for f in fields(value):
            attr_value = getattr(value, f.name)
            result[f.name] = _dataclass_to_dict(attr_value)
        return result
    if isinstance(value, (tuple, list)):
        return [_dataclass_to_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: _dataclass_to_dict(item) for key, item in value.items()}
    # Primitives (int, str, bool, float, None) and Literal-typed strings pass
    # through unchanged. json.dumps will accept them directly.
    return value


def _dict_to_dataclass_kwargs(cls: type, payload: dict[str, Any]) -> dict[str, Any]:
    """Build the constructor kwargs for `cls` from `payload`.

    Drops the `type` discriminator (it's set by the dataclass default).
    Recurses on nested dataclass fields (Snapshot / World / nested dicts).
    """
    type_hints = {f.name: f.type for f in fields(cls)}
    kwargs: dict[str, Any] = {}
    for field_name, raw_value in payload.items():
        if field_name not in type_hints:
            # Unknown field — surface a TypeError when the dataclass init
            # receives it (we do not silently drop; replay's contract is
            # exact round-trip).
            kwargs[field_name] = raw_value
            continue
        kwargs[field_name] = _coerce_field_value(field_name, raw_value, cls)
    return kwargs


def _coerce_field_value(field_name: str, raw_value: Any, owner_cls: type) -> Any:
    """Convert a JSON-decoded value back to the dataclass field's type.

    R2-S01 handles the nested-dataclass cases (Snapshot, World) and tuples
    of primitives. Per ADR-007 (stdlib dataclasses) we don't reach for a
    schema-driven hydrator; the surface is small and explicit.
    """
    if raw_value is None:
        return None
    # GameEnded.final_snapshot — dict → Snapshot
    if owner_cls is GameEnded and field_name == "final_snapshot":
        return _dict_to_snapshot(raw_value)
    # Snapshot.world — dict → World
    if owner_cls is Snapshot and field_name == "world":
        return _dict_to_world(raw_value)
    # Tuple fields land as lists from json.loads; restore the tuple shape
    # so the frozen-dataclass equality (tuple == tuple) stays consistent.
    if field_name in _TUPLE_FIELDS_BY_CLASS.get(owner_cls, set()):
        if isinstance(raw_value, list):
            return tuple(raw_value)
    return raw_value


def _dict_to_snapshot(payload: dict[str, Any]) -> Snapshot:
    kwargs = _dict_to_dataclass_kwargs(Snapshot, payload)
    return Snapshot(**kwargs)


def _dict_to_world(payload: dict[str, Any]) -> World:
    kwargs = _dict_to_dataclass_kwargs(World, payload)
    return World(**kwargs)


# Fields whose declared type is a tuple — they need list→tuple coercion on
# the from_dict path. Hand-maintained; the alternative (reflecting on the
# generic parameter via typing.get_args) is overkill for the R0-R1 event
# family's small surface.
_TUPLE_FIELDS_BY_CLASS: dict[type, set[str]] = {
    GameStarted: {"active_escalation_rules"},
    LocationReported: {"adjacencies"},
    ArrowFired: {"path"},
    InstructionsShown: {"lines"},
    World: {"wumpus_rooms", "pit_rooms", "bat_rooms", "pending_arrow_path"},
    Snapshot: {"active_escalation_rules"},
}


__all__ = ["event_to_dict", "event_from_dict"]
