"""R1-S09 acceptance — wexpect drives `python -m wumpus` on Windows.

Mirrors `test_pexpect_smoke.py` but uses the wexpect Windows fork instead
of POSIX pexpect. Windows-only (skips on Linux/macOS); the CI matrix in
`.github/workflows/subprocess.yml` runs this on `windows-latest`.

Per `[REF] Wave Decisions` L4 wexpect on Windows is known finicky; the
workflow marks this job `continue-on-error: true` on PRs (hard gate on
nightly). If the test surfaces a Windows-specific stdio bug, the failure
mode is "test fails on CI Windows row" — not "test fails in the
crafter's POSIX sandbox" (which can't run wexpect anyway).
"""

from __future__ import annotations

import sys

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="wexpect is Windows-only; POSIX uses pexpect (test_pexpect_smoke.py)",
)

wexpect = pytest.importorskip("wexpect")


# Forced-loss seed for the Yob cave. See test_pexpect_smoke.py for the
# discovery note (seed=3, pit room 19 adjacent to player start 20).
_FORCED_LOSS_SEED: str = "3"


def test_wexpect_drives_wumpus_to_forced_loss() -> None:
    """Windows mirror of the pexpect forced-loss smoke. Drives a
    `python -m wumpus --seed 3` subprocess to the fell_in_pit terminal
    state, expects the lose-tag, then EOF + exit 0.

    wexpect's `spawn` and `expect`/`sendline`/`expect(EOF)` shape matches
    pexpect's POSIX API closely enough that the test body reads identically.
    The main differences (Windows stdio buffering, ConPTY behavior) are
    invisible at this layer; the platform-specific work happens inside
    wexpect.
    """
    child = wexpect.spawn(
        sys.executable,
        ["-m", "wumpus", "--seed", _FORCED_LOSS_SEED],
        timeout=15,
    )
    try:
        # SC3 line-buffering check — read the prompt BEFORE writing anything.
        child.expect_exact("INSTRUCTIONS (Y-N)?", timeout=15)
        child.sendline("N")  # skip the verbatim instructions
        child.sendline("move 19")  # walk into pit 19
        child.expect_exact("HA HA HA - YOU LOSE!", timeout=15)
        child.sendline("N")  # SAME SET-UP=N to end the session
        child.expect(wexpect.EOF, timeout=15)
    finally:
        child.close()

    assert child.exitstatus == 0, (
        f"wumpus subprocess exited with status {child.exitstatus}; expected 0."
    )
