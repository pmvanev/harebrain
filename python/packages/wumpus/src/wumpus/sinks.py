"""Sink Protocol + R0 reference implementations.

Per ADR-008 (Sink contract): `Sink` is a `typing.Protocol` with synchronous
`emit(event)`. Engine calls `emit()` in subscription order on the engine's
thread; sinks MUST NOT assume multi-thread coordination.

R0 ships only `InMemorySink`. `JsonlSink` lands at R2-S01; `RendererSink`
lands with the surface seam at R4-S03. The error classes ship here so the
shape is pinned for downstream slices even though R0 doesn't raise them.
"""

from __future__ import annotations

from typing import Protocol

from wumpus.events import Event


class Sink(Protocol):
    """Outbound port for event emission. Synchronous; subscription-ordered."""

    name: str

    def emit(self, event: Event) -> None: ...


class SchemaValidationError(Exception):
    """Event fails JSON Schema validation. Always propagates; session aborts.

    Not raised at R0 (no schema validation yet — lands at R2-S01).
    """


class SinkIOError(Exception):
    """Sink's underlying I/O fails. Engine emits SinkFailure + unsubscribes.

    Not raised at R0 (no I/O sinks — InMemorySink can't fail this way).
    """


class InMemorySink:
    """Reference sink that collects emitted events in a list.

    The canonical R0 sink — used by acceptance tests to compare event
    sequences across paired Game runs. Per ADR-008 the sink is purely a
    downstream observer; emission is engine-ordered.
    """

    name: str = "in_memory"

    def __init__(self) -> None:
        self.events: list[Event] = []

    def emit(self, event: Event) -> None:
        self.events.append(event)
