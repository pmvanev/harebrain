"""Determinism-source audit — SC1 / K-5 (R3-S03).

Walks the AST of every ``.py`` file under the named source roots and flags
any non-seed entropy source. The engine's only legitimate entropy source is
the integer ``seed`` passed to (or rolled once at) ``Game(seed=...)``; once
rolled the seed is fixed and logged in ``GameStarted.seed``, so determinism
holds from that point. Everything else is forbidden:

  - ``time.time()`` / ``time.monotonic()`` / ``time.perf_counter()`` calls
  - ``os.urandom`` access (call or attribute)
  - ``secrets.*`` calls — EXCEPT the seed-bootstrap carve-out (see below)
  - bare ``random.X(...)`` module-function calls (``random.randint``,
    ``random.random``, ``random.choice``, ...). Only ``random.Random(...)``
    *class* instantiation and ``<instance>.X(...)`` method access (e.g.
    ``self._random.randint(...)``) are permitted — those draw from the
    seeded instance, not the global module RNG.
  - ``datetime.now()`` / ``datetime.today()`` — permitted ONLY in files
    under a ``sinks`` path segment (the SC1 ledger wall-clock carve-out:
    per-event timestamps are ledger-side metadata, emitted by the sink, and
    are never consulted by replay).

The ``secrets.randbits`` seed-bootstrap carve-out
-------------------------------------------------
``Game(seed=None)`` rolls a one-time OS-entropy seed via ``secrets.randbits``
so the unseeded game still has a concrete integer to log + replay. This is
the ONE legitimate use of ``secrets`` in the engine. The carve-out is
approach (a) from the R3-S03 brief: ``secrets.*`` is permitted ONLY inside a
function whose name is in ``SECRETS_CARVE_OUT_FUNCTIONS`` (the dedicated
``_bootstrap_seed`` helper in ``wumpus.engine.game``). A ``secrets`` call
ANYWHERE ELSE — including a different helper, a method, or module scope — is
a violation. The self-test exercises both directions.

Invocation::

    python -m wumpus.audits.determinism_source <root> [<root> ...]

Exit code 0 + a ``PASS`` summary on a clean scan; exit code 1 + a diagnostic
(``file:line`` + what was found) on the first hit reported per violation.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Iterator
from pathlib import Path

# Approach (a): secrets.* is allowed ONLY inside one of these function names.
# `_bootstrap_seed` is the dedicated seed-roller in `wumpus.engine.game`.
SECRETS_CARVE_OUT_FUNCTIONS: frozenset[str] = frozenset({"_bootstrap_seed"})

# Bare `random.<func>(...)` module-level functions that draw from the global
# RNG. Instantiating the `Random` CLASS (`random.Random(seed)`) is allowed;
# only these stateful module-level draws are forbidden.
_FORBIDDEN_RANDOM_FUNCS: frozenset[str] = frozenset(
    {
        "random",
        "randint",
        "randrange",
        "choice",
        "choices",
        "sample",
        "shuffle",
        "uniform",
        "getrandbits",
        "seed",
        "gauss",
        "betavariate",
        "expovariate",
        "triangular",
    }
)

# `time.<func>()` wall-clock / monotonic readers forbidden in engine code.
_FORBIDDEN_TIME_FUNCS: frozenset[str] = frozenset(
    {"time", "monotonic", "perf_counter", "monotonic_ns", "time_ns", "perf_counter_ns"}
)

# `datetime.now()` / `datetime.today()` are wall-clock; allowed only in sinks.
_DATETIME_WALL_CLOCK: frozenset[str] = frozenset({"now", "today", "utcnow"})


class Violation:
    """A single audit hit: where it is + a human-readable reason."""

    def __init__(self, path: Path, lineno: int, reason: str) -> None:
        self.path = path
        self.lineno = lineno
        self.reason = reason

    def render(self) -> str:
        return (
            f"Determinism-source audit: FAIL. Found {self.reason} at "
            f"{self.path.as_posix()}:{self.lineno}. "
            f"SC1 forbids non-seed entropy in engine code."
        )


def _is_sink_file(path: Path) -> bool:
    """True if the file lives under a ``sinks`` path segment OR is a module
    named ``sinks`` (the datetime wall-clock carve-out)."""
    parts = {part.lower() for part in path.parts}
    if "sinks" in parts:
        return True
    return path.stem.lower() == "sinks"


def _attr_chain(node: ast.AST) -> str | None:
    """Render a dotted attribute/name chain (``a.b.c``) as a string, or
    ``None`` if the head is not a bare ``Name`` (e.g. a subscript/call)."""
    parts: list[str] = []
    current: ast.AST = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    parts.append(current.id)
    parts.reverse()
    return ".".join(parts)


class _DeterminismVisitor(ast.NodeVisitor):
    """Walks one module's AST recording determinism-source violations."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._is_sink = _is_sink_file(path)
        # Stack of enclosing function names (for the secrets carve-out).
        self._function_stack: list[str] = []
        self.violations: list[Violation] = []

    # -- function scope tracking (carve-out) --------------------------------

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def _in_secrets_carve_out(self) -> bool:
        return any(name in SECRETS_CARVE_OUT_FUNCTIONS for name in self._function_stack)

    # -- attribute access (os.urandom, datetime.now bare attribute) ---------

    def visit_Attribute(self, node: ast.Attribute) -> None:
        chain = _attr_chain(node)
        if chain == "os.urandom":
            self._record(node, "'os.urandom'")
        self.generic_visit(node)

    # -- call expressions ---------------------------------------------------

    def visit_Call(self, node: ast.Call) -> None:
        self._check_call(node)
        self.generic_visit(node)

    def _check_call(self, node: ast.Call) -> None:
        func = node.func
        if not isinstance(func, ast.Attribute):
            return
        chain = _attr_chain(func)
        if chain is None:
            return
        head, _, tail = chain.partition(".")

        if head == "time" and func.attr in _FORBIDDEN_TIME_FUNCS:
            self._record(node, f"'time.{func.attr}()'")
            return
        if head == "os" and func.attr == "urandom":
            self._record(node, "'os.urandom()'")
            return
        if head == "secrets":
            if not self._in_secrets_carve_out():
                self._record(
                    node,
                    f"'secrets.{func.attr}()' outside the seed-bootstrap "
                    f"carve-out ({sorted(SECRETS_CARVE_OUT_FUNCTIONS)})",
                )
            return
        if head == "random" and func.attr in _FORBIDDEN_RANDOM_FUNCS:
            self._record(node, f"'random.{func.attr}()' (use a seeded Random instance)")
            return
        if func.attr in _DATETIME_WALL_CLOCK and "datetime" in chain.split("."):
            if not self._is_sink:
                self._record(
                    node,
                    f"'datetime.{func.attr}()' outside a sinks/ file "
                    f"(ledger wall-clock carve-out only)",
                )
            return

    def _record(self, node: ast.AST, reason: str) -> None:
        lineno = getattr(node, "lineno", 0)
        self.violations.append(Violation(self._path, lineno, reason))


def scan_file(path: Path) -> list[Violation]:
    """Parse + scan a single ``.py`` file, returning its violations."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    visitor = _DeterminismVisitor(path)
    visitor.visit(tree)
    return visitor.violations


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
            "Determinism-source audit: usage: "
            "python -m wumpus.audits.determinism_source <root> [<root> ...]",
            file=sys.stderr,
        )
        return 2
    files = list(_iter_python_files(args))
    violations = audit(args)
    if violations:
        for violation in violations:
            print(violation.render(), file=sys.stderr)
        return 1
    print(f"Determinism-source audit: 0 hits across {len(files)} files scanned. PASS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
