"""Unit tests for `wumpus.sinks.RendererSink` — the R1-S09 stream sink.

`RendererSink` is the harness-facing sink that translates each emitted event
into Yob surface lines and writes them to a TextIO (default `sys.stdout`).
It is the sink the CLI registers in `wumpus.cli.main` and the same shape
downstream harnesses use to capture rendered output programmatically.

Per the crafter mandate: port-to-port testing — these tests invoke the sink
through its public `emit(event)` driving port and assert at the driven-port
boundary (the TextIO `write`-stream).

Per SC8 the rendered text comes through `wumpus.engine.render_terminal`
+ `wumpus.surfaces.yob` — the sink never embeds Yob literals itself; the
test fixtures pin the verbatim Yob strings against the surface module, not
the sink.
"""

from __future__ import annotations

import io

import pytest

from wumpus.events import (
    SCHEMA_VERSION,
    GameEnded,
    HazardTriggered,
    PromptIssued,
)
from wumpus.sinks import RendererSink
from wumpus.surfaces import yob as yob_surface


def _make_prompt(kind: str) -> PromptIssued:
    return PromptIssued(
        schema_version=SCHEMA_VERSION,
        turn=0,
        surface_variant="<placeholder>",
        internal_state_hash="",
        rng_cursor="",
        kind=kind,  # type: ignore[arg-type]
        context=None,
    )


def _make_hazard(kind: str) -> HazardTriggered:
    return HazardTriggered(
        schema_version=SCHEMA_VERSION,
        turn=0,
        surface_variant="<placeholder>",
        internal_state_hash="",
        rng_cursor="",
        kind=kind,  # type: ignore[arg-type]
        room=1,
    )


def test_renderer_sink_writes_prompt_text_to_attached_stream() -> None:
    """A PromptIssued(kind="instructions") event must produce the verbatim
    Yob prompt line on the sink's stream.

    This is the SC3 line-buffering insurance: the rendered prompt MUST appear
    in the stream as a complete line BEFORE the harness reads input. The
    sink's job is to translate the event AND flush its writes; whether the
    underlying stream is line-buffered is a separate stdio config concern
    (`sys.stdout.reconfigure(line_buffering=True)` in the CLI entry point).
    """
    buffer = io.StringIO()
    sink = RendererSink(stream=buffer)

    sink.emit(_make_prompt("instructions"))

    output = buffer.getvalue()
    assert yob_surface.INSTRUCTIONS_PROMPT in output, (
        f"Expected the verbatim Yob INSTRUCTIONS prompt line on the sink's "
        f"stream after emit(); got: {output!r}"
    )
    # Each rendered line must be newline-terminated so a line-buffered
    # underlying stream actually flushes BEFORE the harness reads. A bare
    # write with no newline can sit in the stdio buffer and create the
    # exact deadlock SC3 forbids.
    assert output.endswith("\n"), (
        f"RendererSink output must end with a newline so the line-buffered "
        f"sys.stdout flushes the prompt before input(). Got: {output!r}"
    )


@pytest.mark.parametrize(
    "hazard_kind, expected_line",
    [
        ("WUMPUS", yob_surface.HAZARD_BUMP_WUMPUS),
        ("PIT", yob_surface.HAZARD_PIT),
        ("BAT", yob_surface.HAZARD_BAT),
    ],
)
def test_renderer_sink_writes_hazard_lines_through_surface(
    hazard_kind: str, expected_line: str
) -> None:
    """Each HazardTriggered kind round-trips through the YobSurface and lands
    as its verbatim Yob line on the sink's stream. Parametrized input
    variation of the same behavior (Mandate M5 — input variations of same
    behavior = one parametrized test)."""
    buffer = io.StringIO()
    sink = RendererSink(stream=buffer)

    sink.emit(_make_hazard(hazard_kind))

    output = buffer.getvalue()
    assert expected_line in output


def test_renderer_sink_skips_events_with_no_surface_mapping() -> None:
    """An event with no R1-S07-shipped surface mapping (e.g., a MoveResolved
    payload — handled by the R4-S03 surface seam) emits nothing to the stream.

    This pins the "events without rendering contribute zero lines" invariant
    from `render_terminal.lines_for_events` — the sink must NOT smear
    placeholders over the stream.
    """
    from wumpus.events import MoveResolved

    buffer = io.StringIO()
    sink = RendererSink(stream=buffer)

    sink.emit(
        MoveResolved(
            schema_version=SCHEMA_VERSION,
            turn=0,
            surface_variant="<placeholder>",
            internal_state_hash="",
            rng_cursor="",
            player_room=2,
        )
    )

    # Empty buffer — no placeholder smear.
    assert buffer.getvalue() == ""


def test_renderer_sink_records_terminal_outcome_lines() -> None:
    """A GameEnded(fell_in_pit, lose) event lands as JUST the lose-tag on the
    sink's stream — the pit reason line is rendered by the prior
    HazardTriggered(PIT) (wumpus.gwbasic.bas:4230 prints it once), not by the
    terminal event. This is the same path the pexpect smoke test asserts on
    (the harness sees the lose-tag before EOF)."""
    buffer = io.StringIO()
    sink = RendererSink(stream=buffer)

    sink.emit(
        GameEnded(
            schema_version=SCHEMA_VERSION,
            turn=1,
            surface_variant="<placeholder>",
            internal_state_hash="",
            rng_cursor="",
            outcome="fell_in_pit",
            message_kind="lose",
            final_snapshot=None,  # type: ignore[arg-type]
        )
    )

    output = buffer.getvalue()
    assert yob_surface.LOSE_TAG in output
    # The pit hazard line is rendered by HazardTriggered(PIT), not duplicated
    # here. Guards the fix for the original double-render fidelity bug.
    assert yob_surface.HAZARD_PIT not in output
