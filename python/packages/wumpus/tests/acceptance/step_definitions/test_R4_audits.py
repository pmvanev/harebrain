"""R4-S04 acceptance step definitions — surface-leak audit (SC8).

The audit scenarios enter through the audit's driving port (the `audit(roots)`
collector / `main(argv)` CLI entry) and assert on observable outcomes (exit
code + returned violations) — exactly what the audits.yml CI job observes. No
engine internals are inspected; the audit IS the system under test.

Scenario 1 proves the audit passes clean on the REAL engine + types (and that
the engine's legitimate docstring/comment mentions of Yob phrases are not
flagged). Scenario 2 proves the audit fails fast on an injected leak, naming
the offending file + line. Together they document the SC8 seam contract: the
audit discriminates rather than always-pass / always-fail.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pytest_bdd import given, scenarios, then, when

from wumpus.audits import surface_leak

scenarios("../features/R4_audits.feature")

# Source roots the audits.yml workflow scans (repo-root relative).
_REPO_ROOT = Path(__file__).resolve().parents[6]
_SRC = _REPO_ROOT / "python" / "packages" / "wumpus" / "src" / "wumpus"
_ENGINE_ROOT = _SRC / "engine"
_TYPES_FILE = _SRC / "types.py"

# The canonical Yob string the regression scenario inlines (one of the AC's
# named catalogue strings — feature-delta § Story R4-S04 AC).
_LEAK_STRING = "I SMELL A WUMPUS!"


# ---------------------------------------------------------------------------
# Scenario 1 — surface-leak audit passes clean on engine + types
# ---------------------------------------------------------------------------


@given(
    "the surface-leak audit runs over wumpus.engine and wumpus.types",
    target_fixture="clean_result",
)
def _clean_result() -> dict[str, Any]:
    roots = [str(_ENGINE_ROOT), str(_TYPES_FILE)]
    return {
        "violations": surface_leak.audit(roots),
        "exit_code": surface_leak.main(roots),
    }


@then("it exits 0 with no surface-form string leaks")
def _clean_exit(clean_result: dict[str, Any]) -> None:
    assert clean_result["exit_code"] == 0, (
        "Surface-leak audit exited non-zero on real engine/types:\n  "
        + "\n  ".join(v.render() for v in clean_result["violations"])
    )
    assert clean_result["violations"] == []


@then("the engine's docstring + comment mentions of Yob phrases are not flagged")
def _mentions_not_flagged(clean_result: dict[str, Any]) -> None:
    # The real engine quotes Yob phrases in docstrings/comments (e.g.
    # render_terminal.py's module docstring quotes "I SMELL A WUMPUS!"). A clean
    # run with zero violations IS the proof those mentions were not flagged —
    # otherwise scenario 1 would have surfaced them as hits.
    assert clean_result["violations"] == [], (
        "A docstring/comment mention of a Yob phrase was flagged as a leak — "
        "the docstring exclusion is incomplete:\n  "
        + "\n  ".join(v.render() for v in clean_result["violations"])
    )


# ---------------------------------------------------------------------------
# Scenario 2 — surface-leak audit fails fast on an injected leak
# ---------------------------------------------------------------------------


@given(
    'an engine module that inlines the Yob string "I SMELL A WUMPUS!"',
    target_fixture="leaking_module",
)
def _leaking_module(tmp_path: Path) -> Path:
    module = tmp_path / "leaky_move.py"
    module.write_text(
        f'def render() -> str:\n    return "{_LEAK_STRING}"\n',
        encoding="utf-8",
    )
    return module


@when("the surface-leak audit runs over it", target_fixture="leak_result")
def _leak_result(leaking_module: Path) -> dict[str, Any]:
    roots = [str(leaking_module)]
    return {
        "module": leaking_module,
        "violations": surface_leak.audit(roots),
        "exit_code": surface_leak.main(roots),
    }


@then("it exits non-zero")
def _leak_exit_nonzero(leak_result: dict[str, Any]) -> None:
    assert leak_result["exit_code"] == 1, (
        f"Surface-leak audit exited {leak_result['exit_code']} on an inlined "
        f"{_LEAK_STRING!r} leak; expected 1."
    )
    assert leak_result["violations"], "Audit found zero violations on a leaking module."


@then("the failure message points at the file and line of the violation")
def _leak_message_points_at_site(leak_result: dict[str, Any]) -> None:
    module: Path = leak_result["module"]
    rendered = [v.render() for v in leak_result["violations"]]
    assert any(module.as_posix() in message for message in rendered), (
        f"No violation names the offending file {module.as_posix()}:\n  "
        + "\n  ".join(rendered)
    )
    assert any(f"{module.as_posix()}:2" in message for message in rendered), (
        "The violation must name the operative line (line 2, the return):\n  "
        + "\n  ".join(rendered)
    )
    assert any(_LEAK_STRING in message for message in rendered), (
        f"The failure message must quote the leaked string {_LEAK_STRING!r}."
    )
