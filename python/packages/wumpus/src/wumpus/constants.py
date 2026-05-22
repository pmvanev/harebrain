"""Engine constants — single source of truth for Yob-fidelity tables.

Per the archived `shared-artifacts-registry.md`, every constant referenced from
multiple call sites lives here. Drift between callers produces "phantom
geography" (the divergence-event class the parent note cites).

Per ADR-007 (stdlib dataclasses) and SC7 (no module-level mutable state),
the constants in this module are immutable tuples / frozensets / strings.

R1-S01 ships:
    - DODECAHEDRON: the 20x3 adjacency table

Future slices append:
    - SENSE_ORDER (R1-S02): the L-array order for sense emission
    - HAZARD_ORDER (R1-S04): the move-resolution order (wumpus, pit, bat)
"""

from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------------
# Dodecahedron adjacency (Yob wumpus.gwbasic.bas lines 0130-0160)
# ---------------------------------------------------------------------------
#
# Yob's BASIC source pins this exact 20x3 adjacency via DATA statements.
# Each room has exactly 3 tunnels; adjacency is symmetric. The audited table
# lives verbatim in the archived shared-artifacts-registry — any change here
# is a Yob-fidelity break and requires a rule-coverage audit re-run.
#
# Representation choice: a `dict[int, frozenset[int]]` keyed by 1-indexed
# room number. The frozenset values are immutable (SC7), and the dict
# encoding avoids the "slot 0 is unused" awkwardness a 21-tuple would carry.

DODECAHEDRON: Final[dict[int, frozenset[int]]] = {
    1: frozenset({2, 5, 8}),
    2: frozenset({1, 3, 10}),
    3: frozenset({2, 4, 12}),
    4: frozenset({3, 5, 14}),
    5: frozenset({1, 4, 6}),
    6: frozenset({5, 7, 15}),
    7: frozenset({6, 8, 17}),
    8: frozenset({1, 7, 9}),
    9: frozenset({8, 10, 18}),
    10: frozenset({2, 9, 11}),
    11: frozenset({10, 12, 19}),
    12: frozenset({3, 11, 13}),
    13: frozenset({12, 14, 20}),
    14: frozenset({4, 13, 15}),
    15: frozenset({6, 14, 16}),
    16: frozenset({15, 17, 20}),
    17: frozenset({7, 16, 18}),
    18: frozenset({9, 17, 19}),
    19: frozenset({11, 18, 20}),
    20: frozenset({13, 16, 19}),
}


__all__ = ["DODECAHEDRON"]
