"""R1-S09 acceptance — pexpect drives `python -m wumpus` to a known terminal.

pexpect spawns the CLI as a real subprocess, reads the INSTRUCTIONS prompt
without writing anything first (line-buffering check), then drives a fixed
action sequence on the canonical Yob dodecahedron to a forced pit-fall loss.
The terminal "HA HA HA - YOU LOSE!" tag must appear before EOF; the process
must exit 0.

POSIX-only (Linux + macOS). The Windows counterpart lives at
`test_wexpect_smoke.py` and skips on non-Windows.

Why a Yob-cave forced loss (not toy cave): the engine's hazard_resolve path
is yob-only — the toy cave can't drive to GameEnded via gameplay. Seed=3
was discovered by exhaustive search over seed ∈ [0, 200): it generates a
layout where pit room 19 is adjacent to the player's starting room (20),
so a single "move 19" walks straight into the pit.

The R1-S10 BASIC fixture suite (downstream slice) will provide canonical
seeds + transcripts for byte-for-byte regression; this smoke test only
pins the subprocess-driveability claim (SC3).
"""

from __future__ import annotations

import sys

import pytest

pexpect = pytest.importorskip("pexpect")

# pexpect's POSIX module imports `fcntl`, which is unavailable on Windows.
# The skip protects pytest collection on Windows even though the wexpect
# smoke test lives in a sibling file.
pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="pexpect is POSIX-only; Windows uses wexpect (test_wexpect_smoke.py)",
)


# Forced-loss seed for the Yob cave. Seed=3 has pit room 19 adjacent to
# player start 20; the action "move 19" walks into the pit and emits
# GameEnded(fell_in_pit, lose). See test_cli.py for the discovery note.
_FORCED_LOSS_SEED: str = "3"


def test_pexpect_drives_wumpus_to_forced_loss() -> None:
    """Spawn `python -m wumpus --seed 3` under pexpect, drive a forced
    pit-fall sequence, expect the lose-tag, then EOF + exit 0.

    The Yob cave enters the pre-game INSTRUCTIONS (Y-N)? state at
    construction. The harness answers N to skip the verbatim instructions,
    then `move 19` to walk into the pit, then N to SAME SET-UP=N to end
    the session.
    """
    child = pexpect.spawn(
        sys.executable,
        ["-m", "wumpus", "--seed", _FORCED_LOSS_SEED],
        timeout=10,
        encoding="utf-8",
    )
    try:
        # SC3 line-buffering check — read the prompt BEFORE writing anything.
        child.expect_exact("INSTRUCTIONS (Y-N)?", timeout=10)
        child.sendline("N")  # skip the verbatim instructions
        # "move 19" walks straight into pit room 19. The surface renders:
        #   "YYYIIIIEEEE . . . FELL IN PIT" (hazard line)
        #   "YYYIIIIEEEE . . . FELL IN PIT" (terminal reason)
        #   "HA HA HA - YOU LOSE!"          (D11 swap tag)
        #   "SAME SET-UP (Y-N)?"
        child.sendline("move 19")
        # Read up to the lose-tag — this is the assertion the AC pins.
        child.expect_exact("HA HA HA - YOU LOSE!", timeout=10)
        # Answer SAME SET-UP=N to end the session cleanly. SessionEnded
        # fires, the loop terminates, the subprocess exits.
        child.sendline("N")
        child.expect(pexpect.EOF, timeout=10)
    finally:
        child.close()

    assert child.exitstatus == 0, (
        f"wumpus subprocess exited with status {child.exitstatus}; expected 0. "
        f"Signal: {child.signalstatus}."
    )


def test_pexpect_observes_instructions_prompt_without_writing_first() -> None:
    """SC3 line-buffering AC: the harness reads the INSTRUCTIONS prompt
    BEFORE writing anything. If the CLI buffered the prompt across the
    pre-input boundary, this expect would deadlock until the timeout fires.

    Uses the default yob cave (where the pre-game INSTRUCTIONS state is
    active) instead of toy cave (which skips it).
    """
    child = pexpect.spawn(
        sys.executable,
        ["-m", "wumpus", "--seed", "0"],
        timeout=5,
        encoding="utf-8",
    )
    try:
        # No sendline first — read the prompt straight from the spawned
        # subprocess's stdout. If line-buffering is broken, this will time
        # out and pexpect will raise pexpect.TIMEOUT.
        child.expect_exact("INSTRUCTIONS (Y-N)?", timeout=5)
        # Answer N to skip the verbatim instructions and reach the post-prompt
        # state quickly. The session has no more prompts at R1-S09 (the full
        # gameplay loop renders are R4-S03 territory) so the next read should
        # block awaiting input; we send EOF by closing stdin.
        child.sendline("N")
    finally:
        # We don't care about exit status for THIS test — the line-buffering
        # observation is the whole point. close() will SIGHUP the process if
        # it's still running.
        child.close(force=True)
