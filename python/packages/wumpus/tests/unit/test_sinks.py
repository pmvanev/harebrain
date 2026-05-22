"""Unit tests for `wumpus.sinks.InMemorySink`.

Behavior under test: `emit(event)` appends to `.events` preserving order.
"""

from __future__ import annotations

from dataclasses import dataclass

from wumpus.sinks import InMemorySink


@dataclass(frozen=True)
class _FakeEvent:
    """Local stand-in event; InMemorySink is duck-typed and doesn't care."""

    tag: str


def test_in_memory_sink_records_events_in_emit_order() -> None:
    """The sink's `.events` reflects emit-order without reordering."""
    sink = InMemorySink()
    e1 = _FakeEvent(tag="first")
    e2 = _FakeEvent(tag="second")
    e3 = _FakeEvent(tag="third")

    sink.emit(e1)  # type: ignore[arg-type]
    sink.emit(e2)  # type: ignore[arg-type]
    sink.emit(e3)  # type: ignore[arg-type]

    assert sink.events == [e1, e2, e3]
