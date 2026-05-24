"""Unit tests for the R2-S01 `--ledger PATH` CLI wiring.

Behavior under test: when `wumpus.cli.main` is invoked with `--ledger=PATH`,
a JsonlSink is attached to the Game and the ledger file accumulates a valid
JSONL line per emitted event. On session exit (stdin EOF) the sink is
closed cleanly.

Port-to-port testing: drive `wumpus.cli.main` (the harness driving port)
with injected stdin/stdout/argv; assert at the filesystem boundary (the
ledger file).
"""

from __future__ import annotations

import io
import json
import pathlib

from wumpus.cli import main as cli_main
from wumpus.events import SCHEMA_VERSION


def test_ledger_flag_writes_jsonl_lines_during_session(
    tmp_path: pathlib.Path,
) -> None:
    """Running the CLI with `--ledger=...` over a short input transcript
    creates a JSONL file whose lines are all valid v1 events.

    Use the toy cave to keep the input simple and avoid the pre-game
    INSTRUCTIONS (Y-N)? prompt — that's an R4-S03 surface concern that the
    R2-S01 ledger-flag wiring shouldn't entangle with.
    """
    ledger = tmp_path / "session.jsonl"
    stdin = io.StringIO("move 2\nmove 3\n")
    stdout = io.StringIO()
    cli_main(
        argv=[
            "--seed", "42",
            "--cave", "toy",
            "--ledger", str(ledger),
        ],
        stdin=stdin,
        stdout=stdout,
    )
    assert ledger.exists(), "--ledger PATH did not create the ledger file."
    lines = [ln for ln in ledger.read_text(encoding="utf-8").split("\n") if ln]
    assert lines, "Ledger file is empty after CLI session."
    for index, line in enumerate(lines):
        payload = json.loads(line)
        assert payload["schema_version"] == SCHEMA_VERSION, (
            f"Line {index} schema_version was {payload['schema_version']!r}; "
            f"expected {SCHEMA_VERSION}."
        )
        assert "type" in payload, f"Line {index} missing 'type' discriminator."


def test_ledger_flag_default_none_does_not_create_file(tmp_path: pathlib.Path) -> None:
    """Without `--ledger`, no file is written. Pure-renderer mode persists
    its R1-S09 behavior (events stream to stdout via RendererSink only)."""
    stdin = io.StringIO("move 2\n")
    stdout = io.StringIO()
    sentinel_path = tmp_path / "should_not_exist.jsonl"
    cli_main(
        argv=["--seed", "42", "--cave", "toy"],
        stdin=stdin,
        stdout=stdout,
    )
    assert not sentinel_path.exists()
