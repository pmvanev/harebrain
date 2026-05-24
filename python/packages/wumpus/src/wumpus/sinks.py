"""Sink Protocol + R0 + R1-S09 reference implementations.

Per ADR-008 (Sink contract): `Sink` is a `typing.Protocol` with synchronous
`emit(event)`. Engine calls `emit()` in subscription order on the engine's
thread; sinks MUST NOT assume multi-thread coordination.

R0 ships `InMemorySink`. R1-S09 adds `RendererSink` — a stream sink that
translates each emitted event through the YobSurface seam and writes the
resulting lines to a TextIO. `JsonlSink` lands at R2-S01. The error classes
ship here so the shape is pinned for downstream slices even though R0
doesn't raise them.
"""

from __future__ import annotations

from typing import Protocol, TextIO

from wumpus.engine.render_terminal import lines_for_events
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


class RendererSink:
    """Sink that translates each event through YobSurface and writes the
    resulting lines (newline-terminated) to a TextIO.

    R1-S09: this is the sink the CLI registers in `wumpus.cli.main`; the
    same shape is injectable into other harnesses that need to capture
    rendered output programmatically (StringIO for in-process tests,
    file-like streams for tee-to-disk wrappers).

    Per SC8 the rendering goes through `wumpus.engine.render_terminal.
    lines_for_events`, which dispatches to `wumpus.surfaces.yob`. No Yob
    literals live in this module.

    Events without an R1-S07 surface mapping (MoveResolved, SenseEmitted,
    LocationReported, ArrowFired, ...) emit zero lines to the stream — the
    sink does NOT write the `<placeholder>` fallback that
    `lines_for_events` uses for whole-turn renders. The fallback would
    smear the same string across the stream every event; harnesses
    expecting clean output would have to filter it out. The cleaner
    contract is "no surface mapping = no output".
    """

    name: str = "renderer"

    def __init__(self, stream: TextIO) -> None:
        self._stream: TextIO = stream

    def emit(self, event: Event) -> None:
        rendered = lines_for_events([event])
        # Suppress the whole-turn placeholder fallback for single-event
        # emissions (see class docstring): if the only line is the R0
        # placeholder, the event has no surface mapping and nothing should
        # reach the stream.
        if rendered == ("<placeholder>",):
            return
        for line in rendered:
            self._stream.write(line)
            self._stream.write("\n")
        # Best-effort flush so line-buffered underlying streams (sys.stdout
        # under `reconfigure(line_buffering=True)`) push the bytes before
        # `input()` blocks. StringIO has flush() too (no-op); arbitrary
        # TextIOs may not — defend with hasattr.
        flush = getattr(self._stream, "flush", None)
        if callable(flush):
            flush()
