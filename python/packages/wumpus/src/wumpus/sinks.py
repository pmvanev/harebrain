"""Sink Protocol + R0 + R1-S09 + R2-S01 reference implementations.

Per ADR-008 (Sink contract): `Sink` is a `typing.Protocol` with synchronous
`emit(event)`. Engine calls `emit()` in subscription order on the engine's
thread; sinks MUST NOT assume multi-thread coordination.

R0 ships `InMemorySink`. R1-S09 adds `RendererSink` — a stream sink that
translates each emitted event through the YobSurface seam and writes the
resulting lines to a TextIO. R2-S01 adds `JsonlSink` — the append-only,
schema-validated JSONL ledger sink. The error classes pin the shape for
downstream slices.
"""

from __future__ import annotations

import json
import pathlib
from typing import TYPE_CHECKING, Any, Protocol, TextIO, runtime_checkable

from wumpus.engine.render_terminal import lines_for_events
from wumpus.events import SCHEMA_VERSION, Event
from wumpus.schema import load_schema
from wumpus.serialization import event_to_dict

if TYPE_CHECKING:
    pass


@runtime_checkable
class Sink(Protocol):
    """Outbound port for event emission. Synchronous; subscription-ordered.

    R2-S01 extension: sinks MAY implement an optional `close()` method for
    file-backed implementations. `Game._teardown` (or the CLI's session exit)
    calls `close()` on every subscribed sink that supports it.
    """

    name: str

    def emit(self, event: Event) -> None: ...


class SchemaValidationError(Exception):
    """Event fails JSON Schema validation. Always propagates; session aborts.

    Per ADR-008: schema-drift is a programming error — silently corrupting
    the ledger would defeat the purpose. `JsonlSink.emit` raises this
    synchronously at emit time, BEFORE writing to disk.
    """


class SinkIOError(Exception):
    """Sink's underlying I/O fails. Engine emits SinkFailure + unsubscribes.

    Recoverable per ADR-008 — distinct from `SchemaValidationError`.
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


class JsonlSink:
    """Append-only JSONL ledger sink. R2-S01.

    Construction:
      - `JsonlSink(path)` opens `path` in line-buffered append mode. The
        path's parent must exist; the file itself is created on open if
        missing. (Per ADR-008 fail-fast: a bad parent is a SinkIOError.)
      - The JSON Schema for `SCHEMA_VERSION` is loaded ONCE at construction
        and cached on the instance.

    `emit(event)`:
      1. Serialize via `wumpus.serialization.event_to_dict`.
      2. Validate the dict against the cached schema. On failure, raise
         `SchemaValidationError` synchronously — the line is NOT written.
      3. On success, write `json.dumps(d) + "\\n"` and flush.

    Header: there is NO separate header API call. The first emitted event
    (typically `GameStarted` or `PromptIssued("instructions")`) IS the
    first line of the ledger.

    `close()`: flush + close the file handle. Idempotent — calling close on
    an already-closed sink is a no-op.

    Per SC4 (synchronous + ordered emission) `emit` writes synchronously on
    the engine's thread; ordering matches engine order. No background
    threads, no async tasks (audited statically — see R2_ledger.feature
    Scenario 4).
    """

    name: str = "jsonl"

    def __init__(
        self,
        path: pathlib.Path | str,
        *,
        schema_version: int = SCHEMA_VERSION,
    ) -> None:
        self._path: pathlib.Path = pathlib.Path(path)
        # buffering=1 → line-buffered. Per SC4 every event reaches disk
        # before `emit` returns control, so replay analyses can race the
        # producer cleanly.
        try:
            self._file = open(self._path, mode="a", buffering=1, encoding="utf-8")
        except OSError as exc:
            raise SinkIOError(
                f"JsonlSink could not open {self._path!r} for append: {exc}"
            ) from exc
        self._schema: dict[str, Any] = load_schema(schema_version)
        # Import jsonschema lazily so test rigs that exercise just the
        # Protocol or RendererSink don't pay the import cost. Library lacks
        # type stubs; the import is `type: ignore`d at this single point
        # (the rest of the file is fully typed).
        import jsonschema  # type: ignore[import-untyped]

        self._validator = jsonschema.Draft202012Validator(self._schema)
        self._closed: bool = False

    def emit(self, event: Event) -> None:
        if self._closed:
            raise SinkIOError(
                f"JsonlSink({self._path!r}) is closed; cannot emit further events."
            )
        payload: dict[str, Any] = event_to_dict(event)
        errors = sorted(self._validator.iter_errors(payload), key=lambda e: e.path)
        if errors:
            # Pre-format the most-specific error first; downstream operators
            # see the schema field that failed, not the top-level oneOf miss.
            primary = errors[0]
            raise SchemaValidationError(
                f"Event of type {type(event).__name__} failed schema "
                f"v{self._schema.get('$id', 'unknown')} validation at "
                f"path {list(primary.absolute_path)!r}: {primary.message}"
            )
        line = json.dumps(payload, separators=(",", ":"))
        try:
            self._file.write(line)
            self._file.write("\n")
            self._file.flush()
        except OSError as exc:
            raise SinkIOError(
                f"JsonlSink({self._path!r}) write failed: {exc}"
            ) from exc

    def close(self) -> None:
        """Flush and close the underlying file. Idempotent."""
        if self._closed:
            return
        try:
            self._file.flush()
            self._file.close()
        finally:
            self._closed = True

    @property
    def path(self) -> pathlib.Path:
        """Return the path the sink is appending to. Read-only."""
        return self._path
