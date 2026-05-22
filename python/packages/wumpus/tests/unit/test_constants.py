"""Unit tests for `wumpus.constants` (R1-S01).

The DODECAHEDRON adjacency table is the single source of truth for cave
geometry per the archived shared-artifacts-registry. These tests pin two
structural invariants the table MUST satisfy:

    1. Every room has exactly 3 tunnels (Yob's audited shape).
    2. Adjacency is symmetric (if 1 -> 2 then 2 -> 1).

The verbatim-table comparison lives in the R1-S01 acceptance scenario
(test_R1_yob_fidelity.py); these unit tests cover the structural properties.
"""

from __future__ import annotations

import pytest

from wumpus.constants import DODECAHEDRON


def _neighbors(room: int) -> frozenset[int]:
    """Indirection that works whether DODECAHEDRON is a dict or a sequence
    indexed 1-20 (or a 21-tuple with slot 0 unused)."""
    if isinstance(DODECAHEDRON, dict):
        return frozenset(DODECAHEDRON[room])
    if len(DODECAHEDRON) == 21:
        return frozenset(DODECAHEDRON[room])
    return frozenset(DODECAHEDRON[room - 1])


@pytest.mark.parametrize("room", list(range(1, 21)))
def test_every_room_has_exactly_three_tunnels(room: int) -> None:
    """Yob's audited dodecahedron: each of 20 rooms has exactly 3 neighbors."""
    assert len(_neighbors(room)) == 3, (
        f"Room {room} has {len(_neighbors(room))} tunnels; expected 3."
    )


def test_adjacency_is_symmetric() -> None:
    """If room A links to room B then room B links back to room A.
    Asymmetric adjacency would let Yob's `WHERE TO?` move validation diverge
    from arrow-path walking — phantom geography (parent-note divergence event).
    """
    asymmetries: list[tuple[int, int]] = []
    for room in range(1, 21):
        for neighbor in _neighbors(room):
            if room not in _neighbors(neighbor):
                asymmetries.append((room, neighbor))
    assert asymmetries == [], (
        f"DODECAHEDRON has asymmetric edges: {asymmetries}. Yob-fidelity break."
    )


def test_neighbors_are_in_valid_room_range() -> None:
    """Every neighbor reference is a room in 1..20 (no off-by-ones, no
    accidental room 0 or 21)."""
    for room in range(1, 21):
        for neighbor in _neighbors(room):
            assert 1 <= neighbor <= 20, (
                f"Room {room} references neighbor {neighbor}, outside 1..20."
            )
            assert neighbor != room, (
                f"Room {room} lists itself as a neighbor (self-loop)."
            )
