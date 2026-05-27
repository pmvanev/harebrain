"""Surface-leak audit — SC8 / K-5 (R4-S04).

Walks the AST of every ``.py`` file under the named source roots (typically
``wumpus/engine`` + ``wumpus/types``) and flags any **operative** string
literal that matches a Yob *surface-form* string. Per SC8 the engine operates
on internal IDs (``int`` rooms, enum-ish ``kind`` discriminators, command
verbs); every player-facing Yob string lives behind ``wumpus.surfaces.yob``.
A surface-form literal in engine code is a leak — it means a future variant
surface (Mystery R4-S05, French R4-S06) would NOT obscure that line, silently
rotting the obfuscation-gap measurement (SC9).

The detection rule — "what is a surface-form string"
-----------------------------------------------------
We take the **precise** approach (a) from the R4-S04 brief: a literal is a
surface-form string iff it is byte-exact to an entry in the Yob *prose*
catalogue. The catalogue is harvested at runtime from ``wumpus.surfaces.yob``
itself (its module-level upper-case ``str`` constants, the values of its
kind→line mapping tables, and the verbatim instructions block) so it can never
drift from the canonical home — the audit's reference set IS the surface.

From that harvested set we SUBTRACT the *discriminator* strings: the keys of
the surface's mapping dicts (``"MISSED"``, ``"SELF_SHOT"``, ``"WUMPUS"``,
``"action"``, ...) and the single-letter command tokens (``"S"`` / ``"M"`` /
``"Y"`` / ``"N"``). Those byte-sequences double as the engine's programmatic
protocol alphabet: the engine compares the player's typed token against
``"Y"`` and passes ``"MISSED"`` as the ``kind`` argument to
``surface.arrow_outcome_string(...)``. They are NOT rendered surface prose, so
flagging them would be a false positive (the brief calls this out explicitly:
``"M"``, ``PromptKind`` discriminators, dict keys are legitimate). The
subtracted set is exactly ``{"M", "MISSED", "N", "S", "Y"}`` — every catalogue
entry that is also a discriminator. What remains is 57 entries of distinctive
multi-word Yob prose (``"I SMELL A WUMPUS!"``, ``"HA HA HA - YOU LOSE!"``,
``"NO. OF ROOMS(1-5)?"``, the instructions block, ...).

Comment + docstring exclusion (the subtle part)
-----------------------------------------------
The engine legitimately *mentions* Yob phrases (``SAME SET-UP``,
``HUNT THE WUMPUS``, ``"I SMELL A WUMPUS!"``) in two non-operative places:

  - **Comments** — these are NOT AST nodes (Python's ``ast`` discards them), so
    they are excluded for free. A comment can never be a leak.
  - **Docstrings** — these ARE ``ast.Constant`` (str) nodes living as the first
    statement of a module / class / function body. We must skip them, or a
    docstring quoting ``"I SMELL A WUMPUS!"`` (see ``render_terminal.py``'s
    module docstring) would false-positive. We collect every docstring node's
    identity up front (positional check: first ``Expr``→``Constant``-str
    statement of any ``Module`` / ``ClassDef`` / ``FunctionDef`` /
    ``AsyncFunctionDef`` body, the same position ``ast.get_docstring`` reads)
    and exclude those node identities from the scan.

Only OPERATIVE string literals remain candidates: assigned values, return
values, call arguments, f-string parts, dict/list/tuple members, comparison
operands — anything that is a ``str`` ``ast.Constant`` and is NOT a docstring
position. The whole point of the slice is that a naive grep / docstring-blind
AST would false-positive on the real engine; this one passes it clean.

Files under a ``surfaces`` path segment are never scanned for leaks — that IS
the surface, the one legitimate home of these strings. (In practice the
``audits.yml`` roots are ``engine`` + ``types`` so ``surfaces`` is never even
visited, but the guard keeps the module safe if pointed at the whole package.)

Invocation::

    python -m wumpus.audits.surface_leak <root> [<root> ...]

Exit code 0 + a ``PASS`` summary on a clean scan; exit code 1 + a diagnostic
(``file:line`` + the offending string) on every hit.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Iterator
from pathlib import Path

from wumpus.surfaces import yob

# Mapping tables on the Yob surface whose VALUES are rendered surface prose and
# whose KEYS are programmatic discriminators. We harvest values into the
# catalogue and subtract keys from it.
_SURFACE_MAPPING_NAMES: tuple[str, ...] = (
    "_HAZARD_LINE_BY_KIND",
    "_TERMINAL_REASON_BY_OUTCOME",
    "_SENSE_LINE_BY_KIND",
    "_HAZARD_NAME_BY_KIND",
    "_ARROW_OUTCOME_BY_KIND",
    "_PROMPT_TEXT_BY_KIND",
    "_TOKEN_BY_VERB",
    "_VERB_BY_TOKEN",
)


def _build_surface_catalogue() -> frozenset[str]:
    """Harvest the Yob *prose* catalogue from ``wumpus.surfaces.yob``.

    The catalogue is every rendered surface-form string the Yob surface can
    emit, MINUS the programmatic discriminator alphabet (mapping-dict keys +
    single-letter command tokens). Built at runtime from the surface module so
    it cannot drift from the canonical home.
    """
    rendered: set[str] = set()

    # Module-level UPPER_CASE str constants (HAZARD_PIT, WIN_TAG, PROMPT_*, ...).
    for name in dir(yob):
        value = getattr(yob, name)
        if isinstance(value, str) and name.isupper():
            rendered.add(value)

    # Values of the kind→line mapping tables (rendered prose).
    for mapping_name in _SURFACE_MAPPING_NAMES:
        mapping = getattr(yob, mapping_name, {})
        for value in mapping.values():
            if isinstance(value, str):
                rendered.add(value)

    # The verbatim instructions block (one entry per Yob BASIC PRINT line).
    for line in yob.instructions_block():
        if isinstance(line, str):
            rendered.add(line)

    # Discriminators to subtract: every mapping-dict KEY + the command tokens.
    # These byte-sequences double as the engine's protocol alphabet (the engine
    # compares typed tokens against "Y" and passes "MISSED" as a `kind` arg).
    discriminators: set[str] = set()
    for mapping_name in _SURFACE_MAPPING_NAMES:
        mapping = getattr(yob, mapping_name, {})
        discriminators.update(str(key) for key in mapping.keys())
    discriminators.update(getattr(yob, "_TOKEN_BY_VERB", {}).values())

    # Empty/whitespace-only lines (the instructions block's blank separators)
    # carry no surface identity and would match incidental "" literals.
    prose = {s for s in (rendered - discriminators) if s.strip()}
    return frozenset(prose)


# The reference set, built once at import. Equality-only — no substring match,
# so a legitimate engine literal that merely CONTAINS a catalogue word (it does
# not, in the real engine) would not trip the audit; only a byte-exact leak does.
SURFACE_CATALOGUE: frozenset[str] = _build_surface_catalogue()


class Violation:
    """A single audit hit: where it is + the offending surface string."""

    def __init__(self, path: Path, lineno: int, leaked: str) -> None:
        self.path = path
        self.lineno = lineno
        self.leaked = leaked

    def render(self) -> str:
        return (
            f"Surface-leak audit: FAIL. Found {self.leaked!r} at "
            f"{self.path.as_posix()}:{self.lineno}. "
            f"Engine code must not reference Yob string literals; "
            f"lift to wumpus.surfaces.yob."
        )


def _is_surface_file(path: Path) -> bool:
    """True if the file lives under a ``surfaces`` path segment (the one
    legitimate home of surface strings — never scanned for leaks)."""
    return "surfaces" in {part.lower() for part in path.parts}


def _docstring_node_ids(tree: ast.Module) -> set[int]:
    """Collect the ``id()`` of every docstring ``Constant`` node.

    A docstring is the first statement of a Module / ClassDef / FunctionDef /
    AsyncFunctionDef body when that statement is an ``Expr`` wrapping a ``str``
    ``Constant`` — the exact position ``ast.get_docstring`` reads. We skip these
    so a docstring quoting a Yob phrase is not a false positive.
    """
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        body = node.body
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            docstrings.add(id(first.value))
    return docstrings


def scan_file(path: Path) -> list[Violation]:
    """Parse + scan a single ``.py`` file, returning its surface-leak hits.

    Files under a ``surfaces`` path segment are skipped (that IS the surface).
    """
    if _is_surface_file(path):
        return []

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    docstrings = _docstring_node_ids(tree)

    violations: list[Violation] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        if not isinstance(node.value, str):
            continue
        if id(node) in docstrings:
            continue  # docstring — a mention, not an operative literal.
        if node.value in SURFACE_CATALOGUE:
            lineno = getattr(node, "lineno", 0)
            violations.append(Violation(path, lineno, node.value))
    return violations


def _iter_python_files(roots: list[str]) -> Iterator[Path]:
    for root in roots:
        root_path = Path(root)
        if root_path.is_file() and root_path.suffix == ".py":
            yield root_path
        else:
            yield from sorted(root_path.rglob("*.py"))


def audit(roots: list[str]) -> list[Violation]:
    """Scan every ``.py`` file under ``roots`` and return all violations."""
    violations: list[Violation] = []
    for path in _iter_python_files(roots):
        violations.extend(scan_file(path))
    return violations


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(
            "Surface-leak audit: usage: "
            "python -m wumpus.audits.surface_leak <root> [<root> ...]",
            file=sys.stderr,
        )
        return 2
    files = list(_iter_python_files(args))
    violations = audit(args)
    if violations:
        for violation in violations:
            print(violation.render(), file=sys.stderr)
        return 1
    print(f"Surface-leak audit: 0 hits across {len(files)} files scanned. PASS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
