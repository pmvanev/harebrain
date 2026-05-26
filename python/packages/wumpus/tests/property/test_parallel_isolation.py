"""R3-S03 parallel-instance isolation — SC7 enforcement at RUNTIME.

The module-state audit proves SC7 STATICALLY (no shared module-level mutable
state in the source). This test proves the same contract DYNAMICALLY: 100
`Game(seed=k_i)` instances constructed with distinct seeds and stepped
CONCURRENTLY through random action sequences must each end in EXACTLY the
snapshot a serial-only `Game(seed=k_i)` would have produced. If any two
instances shared a slot, concurrent interleaving would corrupt at least one
final snapshot, and the serial-vs-concurrent equality would break.

This is a concurrency test, not a thread-safety-within-an-instance test: the
engine is single-threaded per instance (one thread owns each Game). What's
under test is that distinct instances do not influence each other — i.e. the
engine carries no shared mutable state between instances (SC7 / SC12 "parallel
Game instances with no shared state").

Per the R3-S03 brief + DISTILL per-slice procedure, the 100-instance proof
ships as a plain pytest test (concurrency does not fit pytest-bdd well); the
matching acceptance scenario in `R3_audits.feature` is a thin wrapper that
delegates here.

Port-to-port: enters through the `Game(...)` driving port and asserts on the
public `Snapshot` value (serialized to JSON for a byte-level comparison) —
never on engine internals.
"""

from __future__ import annotations

import random
from concurrent.futures import ThreadPoolExecutor

from wumpus import Game
from wumpus.serialization import snapshot_to_json

# 100 distinct seeds; 50 actions each (the AC's "50 random actions each").
_INSTANCE_COUNT = 100
_ACTIONS_PER_INSTANCE = 50
_TOY_ACTIONS = ("move 1", "move 2", "move 3", "move 99")


def _action_sequence_for(seed: int) -> tuple[str, ...]:
    """Deterministically derive a per-seed action sequence. A dedicated
    `random.Random(seed)` (NOT the engine's RNG) picks the actions so the
    serial baseline and the concurrent run drive each Game_i through the
    SAME sequence — the only difference between the two is whether the steps
    are interleaved with other instances."""
    chooser = random.Random(seed)
    return tuple(chooser.choice(_TOY_ACTIONS) for _ in range(_ACTIONS_PER_INSTANCE))


def _run_to_snapshot_json(seed: int, actions: tuple[str, ...]) -> str:
    """Drive a fresh `Game(seed, cave="toy")` through `actions`, return its
    final snapshot serialized to JSON (a byte-level equality oracle)."""
    game = Game(seed=seed, cave="toy")
    for action in actions:
        game.step(action)
    return snapshot_to_json(game.snapshot())


def test_100_parallel_instances_match_serial_equivalents() -> None:
    """Each concurrently-stepped Game_i's final snapshot equals its
    serial-only equivalent, byte-for-byte. Proves SC7 at runtime: no shared
    mutable state between instances."""
    seeds = list(range(1, _INSTANCE_COUNT + 1))
    action_sequences = {seed: _action_sequence_for(seed) for seed in seeds}

    # Serial baseline: each Game_i run alone, no concurrency.
    serial = {
        seed: _run_to_snapshot_json(seed, action_sequences[seed]) for seed in seeds
    }

    # Concurrent run: all 100 instances stepped on a thread pool. If any
    # instance leaked state into a sibling, at least one concurrent snapshot
    # would diverge from its serial baseline.
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = {
            seed: pool.submit(_run_to_snapshot_json, seed, action_sequences[seed])
            for seed in seeds
        }
        concurrent = {seed: future.result() for seed, future in futures.items()}

    mismatches = [seed for seed in seeds if concurrent[seed] != serial[seed]]
    assert not mismatches, (
        f"{len(mismatches)} of {_INSTANCE_COUNT} concurrent Game instances "
        f"produced a final snapshot differing from their serial baseline "
        f"(seeds: {mismatches[:10]}{'...' if len(mismatches) > 10 else ''}). "
        f"Concurrent interleaving corrupted state — instances share mutable "
        f"state (SC7 violation)."
    )


def test_no_instance_observes_another_instances_snapshot() -> None:
    """Each instance's final snapshot is unique to its own seed: no Game_i
    ends up holding a snapshot field belonging to Game_j (i != j). With
    distinct seeds and the same action vocabulary, distinct RNG streams +
    distinct layouts produce distinct snapshots; a collision would mean one
    instance overwrote another's state."""
    seeds = list(range(1, _INSTANCE_COUNT + 1))
    action_sequences = {seed: _action_sequence_for(seed) for seed in seeds}

    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = {
            seed: pool.submit(_run_to_snapshot_json, seed, action_sequences[seed])
            for seed in seeds
        }
        concurrent = {seed: future.result() for seed, future in futures.items()}

    # Every snapshot carries its own seed; assert each instance reports its
    # OWN seed back (not a sibling's), which is the observable form of "no
    # instance observes another's state".
    for seed in seeds:
        assert (
            f'"seed": {seed}' in concurrent[seed]
            or f'"seed":{seed}' in concurrent[seed]
        ), (
            f"Concurrent Game(seed={seed}) snapshot does not carry its own "
            f"seed — it observed another instance's state."
        )
