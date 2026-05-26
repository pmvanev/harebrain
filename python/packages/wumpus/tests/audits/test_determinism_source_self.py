"""Self-test for the determinism-source audit (SC1 / R3-S03).

The "tests-the-tester" pattern: an audit that silently no-ops is
indistinguishable from a passing audit, so each audit ships with a self-test
that injects a SYNTHETIC violation into a temp file and asserts the audit
flags it (non-zero exit + the offending file path in the message). The
self-test ALSO asserts the REAL engine + surfaces source passes clean — the
two directions together prove the audit discriminates rather than always-pass
or always-fail.

Port-to-port: the audit's CLI entry (`main(argv)`) IS the driving port; we
invoke it directly and assert on its observable outcomes (exit code +
stderr-rendered violations via the `audit()` collector). No engine internals
are inspected.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from wumpus.audits import determinism_source as audit

# Repo-root-relative source roots the audits.yml workflow scans.
_REPO_ROOT = Path(__file__).resolve().parents[5]
_ENGINE_ROOT = (
    _REPO_ROOT / "python" / "packages" / "wumpus" / "src" / "wumpus" / "engine"
)
_SURFACES_ROOT = (
    _REPO_ROOT / "python" / "packages" / "wumpus" / "src" / "wumpus" / "surfaces"
)


# A synthetic violating module per forbidden entropy source. Each is written
# into a temp file; the audit must flag it. Parametrized: input variations of
# the SAME behavior ("audit flags a forbidden entropy source").
_VIOLATING_SOURCES: dict[str, str] = {
    "time.time": "import time\n\n\ndef tick() -> float:\n    return time.time()\n",
    "time.monotonic": (
        "import time\n\n\ndef tick() -> float:\n    return time.monotonic()\n"
    ),
    "time.perf_counter": (
        "import time\n\n\ndef tick() -> float:\n    return time.perf_counter()\n"
    ),
    "os.urandom": "import os\n\n\ndef noise() -> bytes:\n    return os.urandom(8)\n",
    "bare random.randint": (
        "import random\n\n\ndef roll() -> int:\n    return random.randint(1, 6)\n"
    ),
    "bare random.choice": (
        "import random\n\n\ndef pick(xs):\n    return random.choice(xs)\n"
    ),
    "secrets outside carve-out": (
        "import secrets\n\n\ndef other() -> bytes:\n    return secrets.token_bytes(8)\n"
    ),
    "datetime.now outside sinks": (
        "from datetime import datetime\n\n\ndef stamp():\n    return datetime.now()\n"
    ),
}


@pytest.mark.parametrize("label", sorted(_VIOLATING_SOURCES))
def test_audit_flags_synthetic_violation(label: str, tmp_path: Path) -> None:
    """For each forbidden entropy source the audit must exit non-zero and the
    diagnostic must name the offending file."""
    fake = tmp_path / "fake_engine.py"
    fake.write_text(_VIOLATING_SOURCES[label], encoding="utf-8")

    violations = audit.audit([str(fake)])
    exit_code = audit.main([str(fake)])

    assert exit_code == 1, (
        f"[{label}] audit exited {exit_code}; expected 1. The audit no-op'd on a "
        f"genuine violation — it is broken."
    )
    assert violations, f"[{label}] audit found zero violations on a violating file."
    assert any(fake.as_posix() in v.render() for v in violations), (
        f"[{label}] no violation names the offending file {fake.as_posix()}."
    )


def test_secrets_carve_out_allows_bootstrap_seed(tmp_path: Path) -> None:
    """The carve-out (approach a) must ALLOW `secrets.*` inside the dedicated
    `_bootstrap_seed` helper while FLAGGING the identical call elsewhere — the
    discriminating-power proof in one test."""
    allowed = tmp_path / "allowed.py"
    allowed.write_text(
        "import secrets\n\n\ndef _bootstrap_seed() -> int:\n"
        "    return secrets.randbits(63)\n",
        encoding="utf-8",
    )
    forbidden = tmp_path / "forbidden.py"
    forbidden.write_text(
        "import secrets\n\n\ndef _roll() -> int:\n    return secrets.randbits(63)\n",
        encoding="utf-8",
    )

    assert audit.audit([str(allowed)]) == [], (
        "secrets.randbits inside _bootstrap_seed must be permitted (the "
        "seed-bootstrap carve-out)."
    )
    assert audit.main([str(allowed)]) == 0

    forbidden_violations = audit.audit([str(forbidden)])
    assert forbidden_violations, (
        "secrets.randbits inside a non-carve-out helper (_roll) must be flagged."
    )
    assert audit.main([str(forbidden)]) == 1


def test_datetime_allowed_in_sinks_file(tmp_path: Path) -> None:
    """`datetime.now()` is the SC1 ledger wall-clock carve-out: permitted only
    in a file under a `sinks` path / named `sinks`."""
    sinks_dir = tmp_path / "sinks"
    sinks_dir.mkdir()
    sink_file = sinks_dir / "jsonl.py"
    sink_file.write_text(
        "from datetime import datetime\n\n\ndef stamp():\n    return datetime.now()\n",
        encoding="utf-8",
    )

    assert audit.audit([str(sink_file)]) == [], (
        "datetime.now() must be permitted inside a sinks/ file (ledger "
        "wall-clock metadata carve-out)."
    )
    assert audit.main([str(sink_file)]) == 0


def test_real_engine_and_surfaces_pass_clean() -> None:
    """The REAL engine + surfaces source MUST pass clean (exit 0). This is the
    other half of the discrimination proof: the audit is not always-fail."""
    violations = audit.audit([str(_ENGINE_ROOT), str(_SURFACES_ROOT)])
    assert violations == [], (
        "Real engine/surfaces source has a determinism-source violation:\n  "
        + "\n  ".join(v.render() for v in violations)
    )
    assert audit.main([str(_ENGINE_ROOT), str(_SURFACES_ROOT)]) == 0
