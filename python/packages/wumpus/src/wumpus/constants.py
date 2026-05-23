"""Engine constants — single source of truth for Yob-fidelity tables.

Per the archived `shared-artifacts-registry.md`, every constant referenced from
multiple call sites lives here. Drift between callers produces "phantom
geography" (the divergence-event class the parent note cites).

Per ADR-007 (stdlib dataclasses) and SC7 (no module-level mutable state),
the constants in this module are immutable tuples / frozensets / strings.

R1-S01 ships:
    - DODECAHEDRON: the 20x3 adjacency table

R1-S02 ships:
    - SENSE_ORDER: the L-array kind order for sense emission

Future slices append:
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


# ---------------------------------------------------------------------------
# SENSE_ORDER (Yob wumpus.gwbasic.bas lines 2020-2120) — R1-S02
# ---------------------------------------------------------------------------
#
# Yob's BASIC source iterates entities in L-array order via `FOR J=2 TO 6`:
#   L(2) = wumpus
#   L(3) = pit #1
#   L(4) = pit #2
#   L(5) = bat #1
#   L(6) = bat #2
# Reduced to distinct kinds in L-array order: (wumpus, pit, bat). The per-room
# iteration inside `wumpus.engine.sense.emit_senses_for_room` walks each
# kind's room collection in placement order, recovering Yob's L(3)-before-L(4)
# / L(5)-before-L(6) ordering without duplicating the kind labels in this
# constant. See the archived shared-artifacts-registry section "Sense order
# on room entry" — any change here is a Yob-fidelity break.

SENSE_ORDER: Final[tuple[str, ...]] = ("wumpus", "pit", "bat")


# ---------------------------------------------------------------------------
# HAZARD_ORDER (Yob wumpus.gwbasic.bas lines 4140-4310) — R1-S03
# ---------------------------------------------------------------------------
#
# Yob's BASIC source resolves co-located hazards in fixed order on entry to
# a new room: wumpus (4150-4200), then pit (4220-4250), then bat (4270-4300).
# R1-S03 wires the wumpus arm; R1-S04 extends with pit + bat handlers. The
# ordering matters because (at R1-S04+) a bat teleport recursively re-enters
# `hazard_resolve` for the destination room — re-using this order.
#
# See archived shared-artifacts-registry section "hazard check order".

HAZARD_ORDER: Final[tuple[str, ...]] = ("wumpus", "pit", "bat")


__all__ = ["DODECAHEDRON", "SENSE_ORDER", "HAZARD_ORDER"]
