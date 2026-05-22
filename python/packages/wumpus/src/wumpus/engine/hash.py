"""State-hashing helpers; deterministic across processes.

Per ADR-003 (per-effect events carry `internal_state_hash`), every event the
engine emits is post-stamped with `internal_state_hash(world)` — a blake2b
digest over a canonical World serialization. The hash is the chain CC-AC-6
relies on for ledger / engine-state agreement detection.

R0 ships `internal_state_hash` only; `layout_hash` (for SAME SET-UP=Y replay)
arrives with R3.
"""

from __future__ import annotations

import hashlib

from wumpus.types import World


def internal_state_hash(world: World) -> str:
    """Deterministic blake2b digest of `world`.

    The canonical serialization walks World fields in declaration order and
    encodes each as a stable byte string. Tuple fields (`wumpus_rooms`,
    `pit_rooms`, `bat_rooms`, `pending_arrow_path`) are joined by a separator
    that cannot appear inside an int repr (`b"|"`). The same World value
    always produces the same digest in any Python process.

    The hex digest is truncated to 32 chars (128 bits) — collision-resistant
    for the ledger's chain-integrity use case and short enough not to bloat
    JSONL events.
    """
    hasher = hashlib.blake2b(digest_size=16)
    hasher.update(_canonical_world_bytes(world))
    return hasher.hexdigest()


def _canonical_world_bytes(world: World) -> bytes:
    """Internal: stable byte encoding of a World value."""
    parts: list[bytes] = [
        b"player_room=" + str(world.player_room).encode("ascii"),
        b"wumpus_rooms=" + _tuple_bytes(world.wumpus_rooms),
        b"pit_rooms=" + _tuple_bytes(world.pit_rooms),
        b"bat_rooms=" + _tuple_bytes(world.bat_rooms),
        b"arrows=" + str(world.arrows).encode("ascii"),
        b"turn=" + str(world.turn).encode("ascii"),
        b"alive=" + (b"1" if world.alive else b"0"),
        b"pending_prompt=" + _opt_str_bytes(world.pending_prompt),
        b"pending_arrow_path=" + _tuple_bytes(world.pending_arrow_path),
    ]
    return b";".join(parts)


def _tuple_bytes(values: tuple[int, ...]) -> bytes:
    return b"|".join(str(v).encode("ascii") for v in values)


def _opt_str_bytes(value: str | None) -> bytes:
    if value is None:
        return b"<none>"
    return value.encode("utf-8")
