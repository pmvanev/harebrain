"""Unit tests for `wumpus.sinks.JsonlSink` (R2-S01).

Behavior under test:
  - Construction opens the file in append mode + line-buffered.
  - `emit(event)` validates against schema v1, writes one JSON line + flushes.
  - Schema-drift events raise `SchemaValidationError` synchronously without
    leaving a partial line in the file.
  - `close()` flushes + closes; idempotent; subsequent emits raise SinkIOError.
  - Append mode: re-opening a sink on an existing file does NOT truncate.

Port-to-port testing: enter through `JsonlSink.emit` (driving port), assert
on file contents (driven port = filesystem).
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import pytest
from hypothesis import given, settings, strategies as st

from wumpus.events import (
    SCHEMA_VERSION,
    ArrowFired,
    GameStarted,
    MoveAttempted,
    PromptIssued,
)
from wumpus.sinks import JsonlSink, SchemaValidationError, SinkIOError


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
# Behavior 1: emit writes a valid JSON line for a well-formed event
# ---------------------------------------------------------------------------


def test_jsonl_sink_writes_one_json_line_per_emit(tmp_path: pathlib.Path) -> None:
    """A single valid event becomes a single newline-terminated JSON line."""
    path = tmp_path / "out.jsonl"
    sink = JsonlSink(path)
    sink.emit(MoveAttempted(**_base_kwargs(), target_room=5, accepted=True))
    sink.close()
    text = path.read_text(encoding="utf-8")
    assert text.endswith("\n"), f"Line not newline-terminated: {text!r}"
    payload = json.loads(text.rstrip("\n"))
    assert payload["type"] == "MoveAttempted"
    assert payload["target_room"] == 5
    assert payload["accepted"] is True


def test_jsonl_sink_appends_each_subsequent_event_on_its_own_line(
    tmp_path: pathlib.Path,
) -> None:
    """Three emits => three JSON lines in emission order."""
    path = tmp_path / "out.jsonl"
    sink = JsonlSink(path)
    sink.emit(
        GameStarted(
            **_base_kwargs(),
            seed=7,
            engine_version="0.0.0",
            surface_id="<placeholder>",
            layout_hash="abc",
            active_escalation_rules=(),
        )
    )
    sink.emit(MoveAttempted(**_base_kwargs(), target_room=2, accepted=True))
    sink.emit(ArrowFired(**_base_kwargs(), path=(5, 6, 7)))
    sink.close()
    lines = [ln for ln in path.read_text(encoding="utf-8").split("\n") if ln]
    assert [json.loads(ln)["type"] for ln in lines] == [
        "GameStarted",
        "MoveAttempted",
        "ArrowFired",
    ]


# ---------------------------------------------------------------------------
# Behavior 2: schema-drift raises SchemaValidationError + file unchanged
# ---------------------------------------------------------------------------


def test_jsonl_sink_raises_schema_validation_error_for_wrong_field_type(
    tmp_path: pathlib.Path,
) -> None:
    """A non-integer `target_room` violates schema. Emit raises; file stays empty."""
    path = tmp_path / "drift.jsonl"
    sink = JsonlSink(path)
    bad_event = MoveAttempted(
        **_base_kwargs(),
        target_room="not-an-integer",  # type: ignore[arg-type]
        accepted=True,
    )
    with pytest.raises(SchemaValidationError):
        sink.emit(bad_event)
    sink.close()
    contents = path.read_text(encoding="utf-8")
    assert contents == "", (
        f"Schema-drift emit must not leave a partial line; got: {contents!r}"
    )


def test_jsonl_sink_continues_emitting_after_a_caught_validation_error(
    tmp_path: pathlib.Path,
) -> None:
    """A SchemaValidationError on one event does NOT poison subsequent valid
    emits — the sink remains usable. This matches ADR-008's distinction
    between SchemaValidationError (propagates) and SinkIOError (terminal)."""
    path = tmp_path / "mixed.jsonl"
    sink = JsonlSink(path)
    bad = MoveAttempted(
        **_base_kwargs(),
        target_room="bad",  # type: ignore[arg-type]
        accepted=True,
    )
    good = MoveAttempted(**_base_kwargs(), target_room=5, accepted=True)
    try:
        sink.emit(bad)
    except SchemaValidationError:
        pass
    sink.emit(good)
    sink.close()
    lines = [ln for ln in path.read_text(encoding="utf-8").split("\n") if ln]
    assert len(lines) == 1
    assert json.loads(lines[0])["target_room"] == 5


# ---------------------------------------------------------------------------
# Behavior 3: close is idempotent + subsequent emit is SinkIOError
# ---------------------------------------------------------------------------


def test_jsonl_sink_close_is_idempotent(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "out.jsonl"
    sink = JsonlSink(path)
    sink.close()
    sink.close()  # Should not raise


def test_jsonl_sink_emit_after_close_raises_sink_io_error(
    tmp_path: pathlib.Path,
) -> None:
    path = tmp_path / "out.jsonl"
    sink = JsonlSink(path)
    sink.close()
    with pytest.raises(SinkIOError):
        sink.emit(MoveAttempted(**_base_kwargs(), target_room=2, accepted=True))


# ---------------------------------------------------------------------------
# Behavior 4: append mode preserves prior contents
# ---------------------------------------------------------------------------


def test_jsonl_sink_opens_in_append_mode(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "out.jsonl"
    sink_a = JsonlSink(path)
    sink_a.emit(MoveAttempted(**_base_kwargs(), target_room=1, accepted=True))
    sink_a.close()
    sink_b = JsonlSink(path)
    sink_b.emit(MoveAttempted(**_base_kwargs(), target_room=2, accepted=True))
    sink_b.close()
    lines = [ln for ln in path.read_text(encoding="utf-8").split("\n") if ln]
    assert len(lines) == 2, (
        f"Append mode invariant: re-opening the sink must NOT truncate. "
        f"Got {len(lines)} lines (expected 2)."
    )
    assert [json.loads(ln)["target_room"] for ln in lines] == [1, 2]


# ---------------------------------------------------------------------------
# Behavior 5: PBT — round-trip via event_to_dict / event_from_dict
# ---------------------------------------------------------------------------


@given(
    target_room=st.integers(min_value=1, max_value=20),
    accepted=st.booleans(),
)
@settings(max_examples=50, deadline=None)
def test_jsonl_sink_round_trips_arbitrary_move_attempted_events(
    target_room: int,
    accepted: bool,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """PBT invariant: any MoveAttempted with a 1..20 target round-trips
    through the ledger and the decoded line matches the original payload."""
    tmp_dir = tmp_path_factory.mktemp("rt")
    path = tmp_dir / "out.jsonl"
    original = MoveAttempted(
        **_base_kwargs(), target_room=target_room, accepted=accepted
    )
    sink = JsonlSink(path)
    sink.emit(original)
    sink.close()
    line = path.read_text(encoding="utf-8").rstrip("\n")
    decoded = json.loads(line)
    assert decoded["target_room"] == target_room
    assert decoded["accepted"] is accepted
    assert decoded["type"] == "MoveAttempted"
    assert decoded["schema_version"] == SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Behavior 6: opening on a nonexistent parent directory raises SinkIOError
# ---------------------------------------------------------------------------


def test_jsonl_sink_raises_sink_io_error_for_missing_parent_directory(
    tmp_path: pathlib.Path,
) -> None:
    bad_path = tmp_path / "does_not_exist" / "out.jsonl"
    with pytest.raises(SinkIOError):
        JsonlSink(bad_path)


# ---------------------------------------------------------------------------
# Behavior 7: SCHEMA_VERSION field on first emitted line equals 1
# ---------------------------------------------------------------------------


def test_jsonl_sink_writes_schema_version_one_on_every_event(
    tmp_path: pathlib.Path,
) -> None:
    path = tmp_path / "out.jsonl"
    sink = JsonlSink(path)
    sink.emit(MoveAttempted(**_base_kwargs(), target_room=5, accepted=True))
    sink.emit(
        PromptIssued(**_base_kwargs(), kind="action", context=None)
    )
    sink.close()
    for line in (ln for ln in path.read_text(encoding="utf-8").split("\n") if ln):
        payload = json.loads(line)
        assert payload["schema_version"] == 1, (
            f"schema_version must equal 1 on every emitted event; "
            f"got {payload['schema_version']!r}."
        )
