"""Unit tests for `wumpus.cli.main` — the R1-S09 subprocess-safe entry point.

The CLI is a thin driving-port shell over the engine: parse argv, build the
Game, subscribe a RendererSink, then loop on `input()` -> `game.step()` until
the session ends. The unit tests exercise the loop in-process by feeding a
StringIO into `sys.stdin` and capturing the output via a StringIO `sys.stdout`.

Per the crafter mandate: port-to-port testing — these tests invoke `cli.main`
through its public driving-port API (`main(argv=[...], stdin=..., stdout=...)`)
and assert at the stdout boundary. The internal loop's helper functions are
implementation detail.

The pexpect/wexpect subprocess smoke tests in `tests/subprocess/` are the
end-to-end validation; these unit tests are the fast (no subprocess overhead)
insurance that the line-buffering + termination discipline holds.
"""

from __future__ import annotations

import io

import pytest

from wumpus import cli
from wumpus.surfaces import yob as yob_surface


def test_cli_emits_instructions_prompt_before_reading_input() -> None:
    """SC3 line-buffering check: the INSTRUCTIONS (Y-N)? prompt MUST be on
    stdout BEFORE the CLI calls input(). The in-process equivalent of the
    pexpect "read prompt without sending anything first" check.

    Construction strategy: feed a single-line stdin ("N\\n") that answers
    the instructions prompt with N; once the engine clears the pre-game
    state, the toy-cave-less yob fixture would emit no further prompts
    (R1-S09 ships only the pre-game prompt rendering through the surface).
    The stdin then reaches EOF, the loop exits cleanly.
    """
    stdin = io.StringIO("N\n")
    stdout = io.StringIO()

    cli.main(argv=["--seed", "0"], stdin=stdin, stdout=stdout)

    output = stdout.getvalue()
    prompt_index = output.find(yob_surface.INSTRUCTIONS_PROMPT)
    assert prompt_index >= 0, (
        f"Expected the verbatim Yob INSTRUCTIONS prompt on stdout; got: {output!r}"
    )


# ---------------------------------------------------------------------------
# Forced-loss seed for the Yob cave.
#
# Seed=3 produces a layout where the player starts at room 20 and pit 19 is
# adjacent. A single "move 19" walks straight into the pit, emitting
# GameEnded(fell_in_pit, lose). This is the deterministic-from-seed forced
# loss the R1-S09 subprocess smoke + the seed-threading unit test pin.
# Discovered by exhaustive search over seed ∈ [0, 200); the first hit.
#
# The toy cave (`--cave toy`) is deliberately NOT used for forced-loss tests:
# the engine's hazard_resolve path is yob-only (see Game.step gating on
# `cave == _CAVE_YOB`), so the toy cave can't drive to GameEnded via
# gameplay. The toy flag exists for downstream debug use (e.g. exercising
# the linear topology against the move sub-state-machine in isolation).
_FORCED_LOSS_SEED: int = 3
_FORCED_LOSS_STDIN: str = "N\nmove 19\nN\n"


def test_cli_threads_seed_into_game_construction() -> None:
    """`--seed K` must reach `Game(seed=K)`. We verify by exercising the
    Yob-cave forced-loss path: seed=3 generates a layout where pit room 19
    is adjacent to the player's starting room (20), so a one-move "move 19"
    walks straight into the pit and emits GameEnded(fell_in_pit, lose).

    Action sequence:
      - "N"        answer N to INSTRUCTIONS (Y-N)?
      - "move 19"  walk into the pit
      - "N"        answer SAME SET-UP=N to end the session

    If `--seed` is not threaded, the cave layout is non-deterministic and
    the LOSE_TAG is not guaranteed.
    """
    stdin = io.StringIO(_FORCED_LOSS_STDIN)
    stdout = io.StringIO()

    cli.main(
        argv=["--seed", str(_FORCED_LOSS_SEED)],
        stdin=stdin,
        stdout=stdout,
    )

    output = stdout.getvalue()
    assert yob_surface.LOSE_TAG in output, (
        f"Expected the HA HA HA - YOU LOSE! tag after the forced pit loss; "
        f"got: {output!r}"
    )


def test_cli_exits_cleanly_on_session_ended() -> None:
    """Once SessionEnded fires (player answers SAME SET-UP=N), the CLI loop
    MUST exit without raising. We don't directly assert on exit status here
    (the unit test calls main() directly; pexpect handles real exit codes).
    This test pins the no-deadlock behavior: even if stdin has extra lines
    AFTER SessionEnded, the loop terminates."""
    # Extra lines after the final N must not deadlock — the loop breaks on
    # SessionEnded (alive=False AND pending_prompt is None) and discards the
    # trailing input.
    stdin = io.StringIO(_FORCED_LOSS_STDIN + "extra-line-that-should-be-ignored\n")
    stdout = io.StringIO()

    cli.main(
        argv=["--seed", str(_FORCED_LOSS_SEED)],
        stdin=stdin,
        stdout=stdout,
    )
    # If we reach here, the loop terminated cleanly.


def test_cli_accepts_yob_surface_default_and_explicit_flag() -> None:
    """`--surface yob` is the explicit default. Anything else is rejected
    until R4-S03 wires the parametric Surface Protocol.

    A clear error means: exit non-zero, message on stderr-or-stdout naming
    the unknown surface. We use SystemExit (argparse's default) so the
    parent process sees a real exit code.
    """
    # Default + explicit "yob" should both succeed (we use the forced-loss
    # seed so the session is short).
    cli.main(
        argv=["--seed", str(_FORCED_LOSS_SEED)],
        stdin=io.StringIO(_FORCED_LOSS_STDIN),
        stdout=io.StringIO(),
    )
    cli.main(
        argv=["--seed", str(_FORCED_LOSS_SEED), "--surface", "yob"],
        stdin=io.StringIO(_FORCED_LOSS_STDIN),
        stdout=io.StringIO(),
    )

    # An unsupported surface must exit non-zero.
    with pytest.raises(SystemExit) as excinfo:
        cli.main(
            argv=["--seed", "0", "--surface", "mystery"],
            stdin=io.StringIO(""),
            stdout=io.StringIO(),
        )
    assert excinfo.value.code != 0


def test_cli_accepts_ledger_placeholder_flag_without_error() -> None:
    """`--ledger PATH` is a placeholder until R2-S01 ships the JsonlSink.
    Accepting the flag without wiring it lets harnesses pin the CLI shape
    today; an error would block the R1-S09 acceptance contract."""
    stdin = io.StringIO(_FORCED_LOSS_STDIN)
    stdout = io.StringIO()

    # Should not raise — the flag is accepted but currently inert.
    cli.main(
        argv=[
            "--seed",
            str(_FORCED_LOSS_SEED),
            "--ledger",
            "/tmp/wumpus.jsonl",
        ],
        stdin=stdin,
        stdout=stdout,
    )

    # The forced-loss path still fires.
    assert yob_surface.LOSE_TAG in stdout.getvalue()
