"""Determinism golden-master regression suite (R1-S10, redefined).

R1-S10 was originally specified as a *byte-identical BASIC transcript* suite
(goals-doc done-criterion #1 / KPI K-1). That premise was dropped on
2026-05-27 (see ADR-011 in `docs/feature/wumpus/feature-delta.md`): the engine
draws randomness from Python's ``random.Random`` (Mersenne Twister) while
PC-BASIC uses GW-BASIC's ``RND`` (a different algorithm), so a shared seed
*cannot* yield byte-identical transcripts — and even a hand-aligned layout
would diverge on the first in-game draw (startle / bat-teleport / arrow walk).

What the harness actually needs is **determinism**, not BASIC parity, and that
is what this suite pins. Two layers:

  Layer 1 — CPython RNG-stability canary. ``random.Random``'s integer-draw
    streams for the *exact* methods the engine consumes. The engine touches RNG
    ONLY via these: ``cave_gen`` (``randrange``), ``startle`` (``randint(1, 4)``
    — Yob's FNC), ``hazard_resolve`` bat-teleport (``randint(1, 20)`` — FNB),
    and ``arrow_walk`` deflection (``randint(1, 3)`` — FNB). If a future CPython
    ever changes these streams, THESE tests fail first and loudest, instead of
    determinism silently rotting. Verified byte-identical on CPython 3.12.13
    and 3.14.3; ``requires-python >= 3.11``.

  Layer 2 — engine characterization (golden master). ``Game(seed=k)`` produces
    a pinned layout + ``layout_hash``, and a fixed scripted run produces a
    pinned terminal ``internal_state_hash``. Catches BOTH RNG drift AND
    accidental engine-logic changes. Re-bless the constants deliberately when a
    behavioral change is intended.

The broader determinism *properties* (paired-sink emission equality, cross-run
hash equality, parallel-instance isolation, snapshot round-trip) live in
``tests/property/`` and ``tests/audits/``; this file pins the concrete
constants those property tests don't.

Engine emission is read via ``Game._debug_events`` — the same engine-emission
record the property suite treats as the observable (see
``tests/property/test_determinism.py``). ``GameStarted`` fires during
``__init__`` (before any external sink can subscribe), so the debug record is
the only way to read the opening event's ``layout_hash``.
"""

from __future__ import annotations

import random

from wumpus import Game

# ---------------------------------------------------------------------------
# Layer 1 — CPython RNG-stability canary
# ---------------------------------------------------------------------------
# Frozen on CPython 3.12.13 and 3.14.3 (identical streams). These guard the
# determinism contract against a CPython version bumping the integer-draw
# algorithm out from under the engine.


def test_randrange_20_stream_is_stable() -> None:
    """cave_gen consumes ``rng.randrange(20) + 1`` for FNB entity placement."""
    rng = random.Random(42)
    assert [rng.randrange(20) + 1 for _ in range(8)] == [4, 1, 9, 8, 8, 5, 4, 18]


def test_randint_1_4_stream_is_stable() -> None:
    """startle consumes ``rng.randint(1, 4)`` for the Yob FNC distribution."""
    rng = random.Random(7)
    assert [rng.randint(1, 4) for _ in range(8)] == [3, 2, 4, 1, 1, 1, 3, 1]


def test_randint_1_20_stream_is_stable() -> None:
    """hazard_resolve consumes ``rng.randint(1, 20)`` for the bat-teleport
    target (Yob FNB over the full room space)."""
    rng = random.Random(99)
    assert [rng.randint(1, 20) for _ in range(8)] == [13, 13, 7, 20, 6, 8, 8, 5]


def test_randint_1_3_stream_is_stable() -> None:
    """arrow_walk consumes ``rng.randint(1, 3)`` for the missing-tunnel
    deflection (Yob FNB over the three adjacent rooms)."""
    rng = random.Random(123)
    assert [rng.randint(1, 3) for _ in range(8)] == [1, 2, 1, 2, 2, 1, 1, 2]


# ---------------------------------------------------------------------------
# Layer 2 — engine characterization (golden master)
# ---------------------------------------------------------------------------


def test_seed42_initial_layout_is_pinned() -> None:
    """``Game(seed=42)`` yob-cave layout is deterministic.

    The Layer-1 ``randrange(20) + 1`` canary stream ``[4, 1, 9, 8, 8, 5, 4,
    18]`` maps directly through Yob's FNB placement order — wumpus, pit, pit,
    bat, bat, player, re-rolling on collision:

        4  -> wumpus
        1  -> pit #1
        9  -> pit #2
        8  -> bat #1
        8  -> collision with bat #1, re-roll
        5  -> bat #2
        4  -> collision with wumpus, re-roll
        18 -> player start

    So this layout and the RNG canary above are two views of the same fact.
    """
    world = Game(seed=42).world_state()
    assert world.player_room == 18
    assert world.wumpus_rooms == (4,)
    assert world.pit_rooms == (1, 9)
    assert world.bat_rooms == (8, 5)


def test_seed42_layout_hash_is_pinned() -> None:
    """The opening ``GameStarted.layout_hash`` for seed=42 is stable."""
    game = Game(seed=42)
    game_started = game._debug_events[0]
    assert game_started.layout_hash == "b327aa423f0522067922d1217a67fc2c"


def test_seed3_forced_pit_fall_run_is_pinned() -> None:
    """Full-pipeline determinism: seed=3 + ``[N, move 19]`` walks straight
    into pit room 19 (adjacent to the seed=3 player start), ending the game.

    Pins the emitted-event count, the terminal state, and the final
    ``internal_state_hash`` — so any drift in the layout, the move/hazard
    resolution, or the event chain surfaces here.

    Re-blessed 2026-05-27 (R1-S11): the event count rose 8 -> 9. R1-S11 (G2)
    parks the engine at the top-level ``SHOOT OR MOVE (S-M)?`` action prompt
    after instructions, so a ``PromptIssued(kind="action")`` now fires between
    ``InstructionsShown`` (index 2) and ``MoveAttempted`` (index 4). The
    terminal ``internal_state_hash`` is UNCHANGED (cfbbdcd4...): the action
    prompt does not alter the terminal World (player in the pit, alive=False,
    pending_prompt="same_setup"), and the hash is taken over World fields. The
    seed=42 layout / ``layout_hash`` (a pure RNG product) are likewise
    untouched — confirmed by ``test_seed42_layout_hash_is_pinned`` above and
    the determinism property suite (paired-run + cross-run equality).
    """
    game = Game(seed=3)
    for action in ("N", "move 19"):
        game.step(action)

    events = game._debug_events
    assert len(events) == 9
    assert type(events[-1]).__name__ == "PromptIssued"
    assert events[-1].internal_state_hash == "cfbbdcd4fcae8e4369ff9a2bce7aed9c"
    assert game.world_state().alive is False
