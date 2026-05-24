"""Unit tests for `wumpus.schema.load_schema` (R2-S01).

Behavior under test: `load_schema(version)` returns the parsed JSON Schema
document for the given version, sourced from `wumpus/schemas/v<N>.json`.
Unknown versions raise FileNotFoundError.
"""

from __future__ import annotations

import pytest

from wumpus.events import SCHEMA_VERSION
from wumpus.schema import load_schema


def test_load_schema_v1_returns_dict_with_oneof_discriminator() -> None:
    schema = load_schema(SCHEMA_VERSION)
    assert isinstance(schema, dict)
    assert schema.get("title") == "wumpus event schema v1"
    assert "oneOf" in schema, (
        "Schema v1 must declare a top-level `oneOf` discriminating per-event "
        "subschemas (per ADR-010)."
    )
    assert "$defs" in schema
    assert "BaseEventFields" in schema["$defs"]


def test_load_schema_unknown_version_raises_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        load_schema(999)
