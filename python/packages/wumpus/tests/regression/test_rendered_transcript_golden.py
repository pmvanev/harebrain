"""Golden rendered-transcript regression net (R1-S13).

The structural successor to the withdrawn R1-S10 BASIC fixtures (see ADR-011 in
``docs/feature/wumpus/feature-delta.md`` and the ``## Wave: DELIVER / [REF] R1
CLI-Fidelity Completion`` § "Acceptance-net approach" subsection). This pins the
engine's OWN full rendered stdout for a few fixed ``(seed, input-script)`` CLI
sessions that run to distinct terminals, and characterization-tests that
re-running reproduces them byte-for-byte. **Engine-vs-pinned-self**, NOT
engine-vs-BASIC — ADR-011 dropped BASIC byte-parity (GW-BASIC ``RND`` ≠ CPython
Mersenne Twister), so the only thing a transcript can faithfully pin is the
engine's own rendering. Analogous in philosophy + directory to
``tests/regression/test_determinism_golden_master.py``.

How it drives + compares
------------------------
Each session is driven **in-process** through the production driving port
``wumpus.cli.main(argv, stdin, stdout)``, with ``io.StringIO`` substituting for
both stdin (the Yob two-step input script) and stdout (the captured transcript).
No subprocess, no pexpect/wexpect — the wexpect harness hangs on Windows, so the
subprocess contract lives at ``tests/subprocess/`` and is excluded from the
default run. Driving ``cli.main`` directly with StringIO gets a full transcript
without that risk.

The captured stdout is compared byte-for-byte against the pinned ``.txt`` golden
file under ``transcripts/``, **after normalizing newlines to ``\\n`` on both
sides** (the engine's ``RendererSink`` writes pure ``\\n``; newline
normalization defends against a ``core.autocrlf`` checkout turning the golden
file's line endings into ``\\r\\n`` on a contributor's machine — same posture
the determinism suite documents). On mismatch, ``assertEqual``-style line diffs
make the divergence obvious.

Re-blessing
-----------
These fixtures pin the engine's CURRENT faithful rendering. On an **intentional**
rendering change, re-bless by regenerating the ``.txt`` files from the same
``(argv, input-script)`` sessions::

    uv run python - <<'PY'
    import io, pathlib
    from wumpus import cli
    from tests.regression.test_rendered_transcript_golden import SESSIONS, TRANSCRIPTS_DIR
    for s in SESSIONS:
        out = io.StringIO()
        cli.main(argv=list(s.argv), stdin=io.StringIO(s.input_script), stdout=out)
        (TRANSCRIPTS_DIR / s.golden_file).write_text(out.getvalue(), encoding="utf-8", newline="")
    PY

and commit the regenerated fixtures with a message documenting WHY the rendering
changed. An UNINTENTIONAL diff is a regression — fix the engine/render code, not
the fixture.

The ``SESSIONS`` tuple below is the single source of truth for the
``(seed, argv, input-script, terminal-kind)`` of each transcript; the
human-readable table lives in ``transcripts/MANIFEST.md``.
"""

from __future__ import annotations

import io
import pathlib
from dataclasses import dataclass

import pytest

from wumpus import cli

TRANSCRIPTS_DIR = pathlib.Path(__file__).parent / "transcripts"


@dataclass(frozen=True)
class TranscriptSession:
    """A pinned ``(seed, input-script) -> terminal`` golden session.

    ``input_script`` is the Yob two-step CLI input form — what a player types:
    single-letter ``N``/``S``/``M``/``Y`` and bare integers, one per line,
    ending with the ``SAME SET-UP (Y-N)?`` -> ``N`` exit.
    """

    name: str
    argv: tuple[str, ...]
    input_script: str
    golden_file: str
    terminal_kind: str


# Single source of truth for the pinned sessions. Mirrors transcripts/MANIFEST.md.
SESSIONS: tuple[TranscriptSession, ...] = (
    TranscriptSession(
        name="pit_fall_seed3",
        argv=("--seed", "3"),
        input_script="N\nM\n19\nN\n",
        golden_file="pit_fall_seed3.txt",
        terminal_kind="pit-fall loss",
    ),
    TranscriptSession(
        name="wumpus_kill_seed15",
        argv=("--seed", "15"),
        input_script="N\nS\n1\n7\nN\n",
        golden_file="wumpus_kill_seed15.txt",
        terminal_kind="wumpus-kill win",
    ),
    TranscriptSession(
        name="bump_eaten_seed18",
        argv=("--seed", "18"),
        input_script="N\nM\n6\nN\n",
        golden_file="bump_eaten_seed18.txt",
        terminal_kind="wumpus-bump-eaten loss",
    ),
)


def _normalize_newlines(text: str) -> str:
    """Collapse ``\\r\\n`` / lone ``\\r`` to ``\\n`` so the comparison is
    line-ending agnostic (defends against ``core.autocrlf`` checkout)."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _capture_transcript(session: TranscriptSession) -> str:
    """Drive ``cli.main`` in-process for ``session`` and return captured stdout.

    The driving port is the real production CLI entry point; only the I/O
    streams are substituted (StringIO). This is the same path a player or the
    pexpect harness exercises, minus the subprocess boundary.
    """
    stdin = io.StringIO(session.input_script)
    stdout = io.StringIO()
    cli.main(argv=list(session.argv), stdin=stdin, stdout=stdout)
    return stdout.getvalue()


@pytest.mark.parametrize("session", SESSIONS, ids=[s.name for s in SESSIONS])
def test_rendered_transcript_matches_golden(session: TranscriptSession) -> None:
    """Re-driving each pinned session reproduces its golden transcript exactly.

    Characterization (golden master): the engine's own rendered stdout for a
    fixed ``(seed, input-script)`` must equal the pinned ``.txt`` byte-for-byte
    (newline-normalized). A diff here means the rendered Yob experience changed
    — re-bless deliberately on an intended change, fix the code on a regression.
    """
    golden_path = TRANSCRIPTS_DIR / session.golden_file
    assert golden_path.exists(), (
        f"Golden transcript {golden_path} is missing. Re-bless by regenerating "
        f"the transcripts/ fixtures (see this module's docstring)."
    )

    expected = _normalize_newlines(golden_path.read_text(encoding="utf-8"))
    actual = _normalize_newlines(_capture_transcript(session))

    # Compare line-by-line so a divergence reports the first differing line
    # rather than dumping two opaque blobs.
    expected_lines = expected.splitlines()
    actual_lines = actual.splitlines()
    assert actual_lines == expected_lines, (
        f"Rendered transcript for session {session.name!r} "
        f"({session.terminal_kind}, argv={list(session.argv)}, "
        f"input_script={session.input_script!r}) diverged from the pinned "
        f"golden {session.golden_file}.\n"
        f"--- expected (golden) ---\n{expected}\n"
        f"--- actual (engine) ---\n{actual}\n"
        f"If this rendering change is INTENTIONAL, re-bless the fixture "
        f"(see module docstring). Otherwise it is a rendering REGRESSION — "
        f"fix the engine/render code, not the fixture."
    )
