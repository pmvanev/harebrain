"""Self-test for the surface-leak audit (SC8 / R4-S04).

The "tests-the-tester" pattern: an audit that silently no-ops is
indistinguishable from a passing audit, so each audit ships with a self-test
that injects a SYNTHETIC leak into a temp file and asserts the audit flags it
(non-zero exit + the offending file path in the message). The self-test ALSO
asserts the REAL engine + types source passes clean — the two directions
together prove the audit discriminates rather than always-pass / always-fail.

This audit has a third discrimination axis the others lack: it must FLAG an
operative Yob-string literal while NOT flagging (a) the same phrase appearing
only in a docstring and (b) the programmatic discriminator strings
(``"MISSED"``, ``"S"`` / ``"M"`` / ``"Y"`` / ``"N"``) the engine legitimately
uses as ``kind`` args / typed-token comparisons. Those carve-outs are the
whole subtlety of R4-S04, so they get dedicated assertions.

Port-to-port: the audit's CLI entry (``main(argv)``) and collector
(``audit(roots)``) ARE the driving port; we invoke them directly and assert on
observable outcomes (exit code + rendered violations). No engine internals are
inspected.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from wumpus.audits import surface_leak as audit

# Repo-root-relative source roots the audits.yml workflow scans.
_REPO_ROOT = Path(__file__).resolve().parents[5]
_SRC = _REPO_ROOT / "python" / "packages" / "wumpus" / "src" / "wumpus"
_ENGINE_ROOT = _SRC / "engine"
_TYPES_FILE = _SRC / "types.py"


# A synthetic engine module per leak shape. Each plants a distinct Yob prose
# string in an OPERATIVE position (return / assign / call-arg / f-string).
# Parametrized: input variations of the SAME behavior ("audit flags an
# operative surface-form literal in engine code").
_LEAKING_SOURCES: dict[str, str] = {
    "sense line returned": ('def render():\n    return "I SMELL A WUMPUS!"\n'),
    "lose tag assigned": (
        'def tag() -> str:\n    line = "HA HA HA - YOU LOSE!"\n    return line\n'
    ),
    "win swap tag in call": (
        "def emit(sink):\n"
        '    sink.write("HEE HEE HEE - THE WUMPUS\'LL GETCHA NEXT TIME!!")\n'
    ),
    "win reason line": ('def win():\n    return "AHA! YOU GOT THE WUMPUS!"\n'),
    "prompt text in f-string": (
        # The catalogue phrase is a contiguous literal SEGMENT of the f-string
        # (an ast.Constant str node). The {n} interpolation leads so the
        # trailing phrase segment is byte-exact to the catalogue entry — a leak
        # embedded in an f-string is still a leak.
        'def prompt(n: int) -> str:\n    return f"{n}NO. OF ROOMS(1-5)?"\n'
    ),
    "hazard line in list": ('def lines():\n    return ["...OOPS! BUMPED A WUMPUS!"]\n'),
    "banner literal": ('def banner():\n    return "HUNT THE WUMPUS"\n'),
}


@pytest.mark.parametrize("label", sorted(_LEAKING_SOURCES))
def test_audit_flags_synthetic_leak(label: str, tmp_path: Path) -> None:
    """For each operative Yob-string leak the audit must exit non-zero and the
    diagnostic must name the offending file."""
    fake = tmp_path / "fake_engine.py"
    fake.write_text(_LEAKING_SOURCES[label], encoding="utf-8")

    violations = audit.audit([str(fake)])
    exit_code = audit.main([str(fake)])

    assert exit_code == 1, (
        f"[{label}] audit exited {exit_code}; expected 1. The audit no-op'd on a "
        f"genuine surface-string leak — it is broken."
    )
    assert violations, f"[{label}] audit found zero violations on a leaking file."
    assert any(fake.as_posix() in v.render() for v in violations), (
        f"[{label}] no violation names the offending file {fake.as_posix()}."
    )


def test_docstring_mention_is_not_flagged(tmp_path: Path) -> None:
    """A Yob phrase appearing ONLY in a docstring (module / class / function)
    is a mention, not an operative literal — it must NOT be flagged. This is
    the core R4-S04 carve-out: the real engine quotes these phrases in its
    docstrings (e.g. render_terminal.py's module docstring)."""
    module_doc = tmp_path / "module_doc.py"
    module_doc.write_text(
        '"""Renders the "I SMELL A WUMPUS!" sense line via the surface."""\n'
        "\n\ndef render(surface, kind):\n    return surface.sense_string(kind)\n",
        encoding="utf-8",
    )
    func_doc = tmp_path / "func_doc.py"
    func_doc.write_text(
        "def render(surface):\n"
        '    """Emit "HA HA HA - YOU LOSE!" through the surface on a loss."""\n'
        "    return surface.terminal_strings()\n",
        encoding="utf-8",
    )

    assert audit.audit([str(module_doc)]) == [], (
        "A Yob phrase in a MODULE docstring must not be flagged (mention, "
        "not operative literal)."
    )
    assert audit.main([str(module_doc)]) == 0
    assert audit.audit([str(func_doc)]) == [], (
        "A Yob phrase in a FUNCTION docstring must not be flagged."
    )
    assert audit.main([str(func_doc)]) == 0


def test_docstring_carve_out_discriminates(tmp_path: Path) -> None:
    """The discriminating-power proof in one test: the SAME Yob phrase is
    flagged when operative but NOT when it is only a docstring — in the same
    file. Proves the exclusion is positional, not a blanket allow-list."""
    mixed = tmp_path / "mixed.py"
    mixed.write_text(
        '"""This module mentions "AHA! YOU GOT THE WUMPUS!" in prose."""\n'
        "\n\ndef leak():\n"
        '    return "AHA! YOU GOT THE WUMPUS!"\n',
        encoding="utf-8",
    )

    violations = audit.audit([str(mixed)])
    assert len(violations) == 1, (
        "Exactly the OPERATIVE occurrence must be flagged (the docstring "
        f"mention must be skipped); got {len(violations)} hits."
    )
    assert violations[0].lineno == 5, (
        f"The flagged line should be the operative return (line 5), not the "
        f"docstring (line 1); got line {violations[0].lineno}."
    )
    assert audit.main([str(mixed)]) == 1


def test_discriminator_literals_are_not_flagged(tmp_path: Path) -> None:
    """The engine's protocol-alphabet literals (kind discriminators + typed
    command tokens) double as catalogue byte-sequences but are NOT rendered
    surface prose — they must NOT be flagged. ``"MISSED"`` passed as a `kind`
    arg and ``"S"`` / ``"Y"`` compared against a typed token are the real
    engine's legitimate uses (render_terminal.py / game.py)."""
    disc = tmp_path / "discriminators.py"
    disc.write_text(
        "def render(surface):\n"
        '    return surface.arrow_outcome_string("MISSED")\n'
        "\n\ndef parse(token: str):\n"
        '    if token == "S":\n        return "shoot"\n'
        '    if token == "M":\n        return "move"\n'
        '    if token == "Y":\n        return True\n'
        '    if token == "N":\n        return False\n',
        encoding="utf-8",
    )

    assert audit.audit([str(disc)]) == [], (
        "Discriminator literals (MISSED / S / M / Y / N) must not be flagged — "
        "they are the engine's protocol alphabet, not rendered surface prose."
    )
    assert audit.main([str(disc)]) == 0


def test_real_engine_and_types_pass_clean() -> None:
    """The REAL engine + types source MUST pass clean (exit 0). This is the
    other half of the discrimination proof: the audit is not always-fail.
    R4-S03 moved every Yob string literal into wumpus.surfaces.yob; only
    comments + docstrings reference these phrases in the engine now."""
    roots = [str(_ENGINE_ROOT), str(_TYPES_FILE)]
    violations = audit.audit(roots)
    assert violations == [], (
        "Real engine/types source has a surface-leak violation:\n  "
        + "\n  ".join(v.render() for v in violations)
    )
    assert audit.main(roots) == 0
