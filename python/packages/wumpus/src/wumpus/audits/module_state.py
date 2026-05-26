"""Module-state audit — SC7 / K-5 (R3-S03).

Walks the AST of every ``.py`` file under the named source roots and flags
shared mutable module state. ``Game()`` construction must have no side
effects on import-time state, and two co-resident ``Game`` instances must
never share a slot — so the engine package may hold no module-level mutable
container that engine code subsequently writes to, and no singleton-cached
``random.Random``.

What it flags
-------------
1. A module-level assignment whose value is a mutable container literal
   (``ast.List`` / ``ast.Dict`` / ``ast.Set``, or the ``list()`` / ``dict()``
   / ``set()`` builtins) that is SUBSEQUENTLY WRITTEN TO by any function in
   the same module — via ``.append`` / ``.extend`` / ``.update`` / ``.clear``
   / ``.pop`` / ``.add`` / ``.setdefault`` / ... or subscript assignment
   (``NAME[k] = v``) or augmented assignment (``NAME += ...``).
2. A module-level ``random.Random(...)`` instance (the "no singleton-cached
   RNG" rule) regardless of whether it is written to — a shared RNG instance
   IS shared mutable state by construction.

What is explicitly allowed
--------------------------
- Module-level IMMUTABLE values: ``tuple`` / ``frozenset`` literals, scalars
  (``int`` / ``float`` / ``bool`` / ``None``), ``str``.
- A value annotated ``Final[...]`` (the author has pinned it read-only).
- A module-level mutable container that is only ever READ (lookup tables:
  ``.get(...)``, ``NAME[k]`` reads, ``in NAME`` membership, ``sorted(NAME)``,
  ``dict(NAME)`` copies). These are constant-by-convention and never mutate,
  so two instances cannot observe each other through them.

Invocation::

    python -m wumpus.audits.module_state <root> [<root> ...]

Exit code 0 + a ``PASS`` summary on a clean scan; exit code 1 + a diagnostic
on hit.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Iterator
from pathlib import Path

# Mutating method names that imply a write to the receiver container.
_MUTATING_METHODS: frozenset[str] = frozenset(
    {
        "append",
        "extend",
        "insert",
        "remove",
        "pop",
        "clear",
        "update",
        "setdefault",
        "popitem",
        "add",
        "discard",
        "sort",
        "reverse",
        "__setitem__",
        "__delitem__",
    }
)

_MUTABLE_BUILTIN_CONSTRUCTORS: frozenset[str] = frozenset({"list", "dict", "set"})


class Violation:
    def __init__(self, path: Path, lineno: int, reason: str) -> None:
        self.path = path
        self.lineno = lineno
        self.reason = reason

    def render(self) -> str:
        return (
            f"Module-state audit: FAIL. {self.reason} at "
            f"{self.path.as_posix()}:{self.lineno}. "
            f"SC7 forbids shared module-level mutable state in engine code."
        )


def _is_final_annotation(annotation: ast.expr | None) -> bool:
    """True if the annotation is ``Final`` or ``Final[...]`` / ``typing.Final``."""
    if annotation is None:
        return False
    target: ast.expr = annotation
    if isinstance(target, ast.Subscript):
        target = target.value
    if isinstance(target, ast.Name):
        return target.id == "Final"
    if isinstance(target, ast.Attribute):
        return target.attr == "Final"
    return False


def _is_mutable_container_value(value: ast.expr) -> bool:
    """True if the assigned value is a mutable container literal or a
    ``list()`` / ``dict()`` / ``set()`` constructor call."""
    if isinstance(value, (ast.List, ast.Dict, ast.Set)):
        return True
    if isinstance(value, ast.ListComp | ast.DictComp | ast.SetComp):
        return True
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
        return value.func.id in _MUTABLE_BUILTIN_CONSTRUCTORS
    return False


def _is_random_instance_value(value: ast.expr) -> bool:
    """True if the value is a ``random.Random(...)`` / ``Random(...)``
    instantiation (a singleton-cached RNG instance)."""
    if not isinstance(value, ast.Call):
        return False
    func = value.func
    if isinstance(func, ast.Attribute):
        return func.attr == "Random"
    if isinstance(func, ast.Name):
        return func.id == "Random"
    return False


def _assign_targets(node: ast.Assign | ast.AnnAssign) -> Iterator[tuple[str, int]]:
    """Yield ``(name, lineno)`` for every simple-name assignment target."""
    if isinstance(node, ast.AnnAssign):
        if isinstance(node.target, ast.Name):
            yield node.target.id, node.lineno
        return
    for target in node.targets:
        if isinstance(target, ast.Name):
            yield target.id, node.lineno


class _ModuleLevelCollector(ast.NodeVisitor):
    """Records module-level (top-of-module) assignments only. Does NOT
    descend into function/class bodies — those are not module scope."""

    def __init__(self) -> None:
        # name -> (lineno, value_node, is_final)
        self.mutable_names: dict[str, tuple[int, ast.expr]] = {}
        self.random_instances: dict[str, int] = {}

    def visit_Module(self, node: ast.Module) -> None:
        for stmt in node.body:
            self._consider(stmt)

    def _consider(self, stmt: ast.stmt) -> None:
        if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            self._consider_assign(stmt)

    def _consider_assign(self, stmt: ast.Assign | ast.AnnAssign) -> None:
        value = stmt.value
        if value is None:
            return
        is_final = isinstance(stmt, ast.AnnAssign) and _is_final_annotation(
            stmt.annotation
        )
        for name, lineno in _assign_targets(stmt):
            if _is_random_instance_value(value):
                self.random_instances[name] = lineno
                continue
            if is_final:
                continue
            if _is_mutable_container_value(value):
                self.mutable_names[name] = (lineno, value)


class _WriteFinder(ast.NodeVisitor):
    """Finds writes to any of the watched module-level names occurring inside
    function/method bodies (or anywhere)."""

    def __init__(self, watched: set[str]) -> None:
        self._watched = watched
        # name -> first write lineno + describing-context line
        self.writes: dict[str, int] = {}

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in _MUTATING_METHODS:
            receiver = func.value
            if isinstance(receiver, ast.Name) and receiver.id in self._watched:
                self._record(receiver.id, node.lineno)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            self._check_subscript_target(target, node.lineno)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._check_subscript_target(node.target, node.lineno)
        if isinstance(node.target, ast.Name) and node.target.id in self._watched:
            self._record(node.target.id, node.lineno)
        self.generic_visit(node)

    def visit_Delete(self, node: ast.Delete) -> None:
        for target in node.targets:
            self._check_subscript_target(target, node.lineno)
        self.generic_visit(node)

    def _check_subscript_target(self, target: ast.expr, lineno: int) -> None:
        if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
            if target.value.id in self._watched:
                self._record(target.value.id, lineno)

    def _record(self, name: str, lineno: int) -> None:
        self.writes.setdefault(name, lineno)


def scan_file(path: Path) -> list[Violation]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))

    collector = _ModuleLevelCollector()
    collector.visit(tree)

    violations: list[Violation] = []

    # Rule 2 — module-level Random() instances are always flagged.
    for name, lineno in sorted(
        collector.random_instances.items(), key=lambda kv: kv[1]
    ):
        violations.append(
            Violation(
                path,
                lineno,
                f"Module-level random.Random() instance ({name}) "
                f"(no singleton-cached RNG)",
            )
        )

    # Rule 1 — module-level mutable containers written to by any function.
    if collector.mutable_names:
        write_finder = _WriteFinder(set(collector.mutable_names))
        write_finder.visit(tree)
        for name, (decl_lineno, _value) in sorted(
            collector.mutable_names.items(), key=lambda kv: kv[1][0]
        ):
            if name in write_finder.writes:
                write_lineno = write_finder.writes[name]
                violations.append(
                    Violation(
                        path,
                        decl_lineno,
                        f"Module-level mutable state ({name}) declared here is "
                        f"written at line {write_lineno}",
                    )
                )

    return violations


def _iter_python_files(roots: list[str]) -> Iterator[Path]:
    for root in roots:
        root_path = Path(root)
        if root_path.is_file() and root_path.suffix == ".py":
            yield root_path
        else:
            yield from sorted(root_path.rglob("*.py"))


def audit(roots: list[str]) -> list[Violation]:
    violations: list[Violation] = []
    for path in _iter_python_files(roots):
        violations.extend(scan_file(path))
    return violations


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(
            "Module-state audit: usage: "
            "python -m wumpus.audits.module_state <root> [<root> ...]",
            file=sys.stderr,
        )
        return 2
    files = list(_iter_python_files(args))
    violations = audit(args)
    if violations:
        for violation in violations:
            print(violation.render(), file=sys.stderr)
        return 1
    print(f"Module-state audit: 0 hits across {len(files)} files scanned. PASS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
