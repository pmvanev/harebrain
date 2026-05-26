"""Self-test for the module-state audit (SC7 / R3-S03).

"Tests-the-tester": injects synthetic module-level mutable-state violations
into temp files, asserts the audit flags each (non-zero exit + offending file
path), and asserts the REAL `wumpus` package source passes clean. The two
directions prove the audit discriminates.

Also pins the EXEMPTIONS the audit must honour (read-only lookup-table dicts,
`Final[...]` values, immutable `tuple`/`frozenset`) so a future over-eager
rewrite of the audit can't start failing the legitimate engine constants.

Port-to-port: `main(argv)` / `audit(roots)` is the driving port.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from wumpus.audits import module_state as audit

_REPO_ROOT = Path(__file__).resolve().parents[5]
_WUMPUS_ROOT = _REPO_ROOT / "python" / "packages" / "wumpus" / "src" / "wumpus"


# Each source has a module-level mutable container WRITTEN by a function, or a
# module-level Random() instance. Parametrized: variations of the SAME
# behavior ("audit flags shared module-level mutable state").
_VIOLATING_SOURCES: dict[str, str] = {
    "dict.append-style update": (
        "_CACHE: dict[int, int] = {}\n\n\n"
        "def remember(k: int, v: int) -> None:\n    _CACHE[k] = v\n"
    ),
    "list.append": (
        "_SEEN: list[int] = []\n\n\ndef record(x: int) -> None:\n    _SEEN.append(x)\n"
    ),
    "set.add": (
        "_VISITED: set[int] = set()\n\n\n"
        "def mark(x: int) -> None:\n    _VISITED.add(x)\n"
    ),
    "dict.update": (
        "_CONF: dict[str, int] = {}\n\n\n"
        "def merge(other: dict) -> None:\n    _CONF.update(other)\n"
    ),
    "dict.clear": (
        "_CACHE: dict[int, int] = {}\n\n\ndef reset() -> None:\n    _CACHE.clear()\n"
    ),
    "list augmented assign": (
        "_LOG: list[int] = []\n\n\n"
        "def append_all(xs: list[int]) -> None:\n    _LOG += xs\n"
    ),
    "module-level Random instance": (
        "import random\n\n_RNG = random.Random(42)\n\n\n"
        "def roll() -> int:\n    return _RNG.randint(1, 6)\n"
    ),
}


@pytest.mark.parametrize("label", sorted(_VIOLATING_SOURCES))
def test_audit_flags_synthetic_violation(label: str, tmp_path: Path) -> None:
    fake = tmp_path / "fake_module.py"
    fake.write_text(_VIOLATING_SOURCES[label], encoding="utf-8")

    violations = audit.audit([str(fake)])
    exit_code = audit.main([str(fake)])

    assert exit_code == 1, (
        f"[{label}] audit exited {exit_code}; expected 1. The audit no-op'd on a "
        f"genuine module-state violation — it is broken."
    )
    assert violations, f"[{label}] audit found zero violations on a violating file."
    assert any(fake.as_posix() in v.render() for v in violations), (
        f"[{label}] no violation names the offending file {fake.as_posix()}."
    )


# Each source has module-level state the audit must NOT flag: a read-only
# lookup-table dict, a Final[...] container, an immutable tuple/frozenset.
_ALLOWED_SOURCES: dict[str, str] = {
    "read-only lookup dict": (
        "_TABLE: dict[str, int] = {'a': 1, 'b': 2}\n\n\n"
        "def look(k: str) -> int:\n    return _TABLE.get(k, 0)\n"
    ),
    "Final dict (read-only by contract)": (
        "from typing import Final\n\n"
        "TABLE: Final[dict[int, int]] = {1: 2}\n\n\n"
        "def look(k: int) -> int:\n    return TABLE[k]\n"
    ),
    "immutable tuple": (
        "ORDER: tuple[int, ...] = (1, 2, 3)\n\n\n"
        "def first() -> int:\n    return ORDER[0]\n"
    ),
    "immutable frozenset": (
        "ALLOWED: frozenset[int] = frozenset({1, 2, 3})\n\n\n"
        "def ok(x: int) -> bool:\n    return x in ALLOWED\n"
    ),
    "dict copied not mutated": (
        "_DEFAULT: dict[str, int] = {'k': 1}\n\n\n"
        "def fresh() -> dict[str, int]:\n    return dict(_DEFAULT)\n"
    ),
}


@pytest.mark.parametrize("label", sorted(_ALLOWED_SOURCES))
def test_audit_allows_immutable_or_readonly_module_state(
    label: str, tmp_path: Path
) -> None:
    fake = tmp_path / "fake_module.py"
    fake.write_text(_ALLOWED_SOURCES[label], encoding="utf-8")

    assert audit.audit([str(fake)]) == [], (
        f"[{label}] audit flagged legitimate read-only / immutable module "
        f"state — it is over-eager."
    )
    assert audit.main([str(fake)]) == 0


def test_real_wumpus_package_passes_clean() -> None:
    """The REAL `wumpus` package MUST pass clean (the other half of the
    discrimination proof: the audit is not always-fail). The engine's
    lookup-table dicts (DODECAHEDRON, _EVENT_REGISTRY, ...) are read-only."""
    violations = audit.audit([str(_WUMPUS_ROOT)])
    assert violations == [], (
        "Real wumpus package source has a module-state violation:\n  "
        + "\n  ".join(v.render() for v in violations)
    )
    assert audit.main([str(_WUMPUS_ROOT)]) == 0
