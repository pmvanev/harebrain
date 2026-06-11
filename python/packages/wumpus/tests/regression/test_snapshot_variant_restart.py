"""Regression: Snapshot must persist the game's VariantConfig (2026-06-11).

Root cause (RCA-confirmed): `Snapshot` carried no `variant_config`, so
`Game.from_snapshot` hardcoded `game._variant = VariantConfig()` (Yob
defaults) at `game.py:1396`. A resurrected NON-Yob game therefore lost its
variant: behavioral params with no World footprint (`arrow_max_range`,
`wumpus_move_prob`) and zero-collapsed counts (`pit_count=0`, `bat_count=0`)
vanished across a snapshot hop. The observable break: a SAME SET-UP ('Y')
restart on the restored game re-reads `self._variant.as_dict()`
(`game.py:927`) and emits Yob defaults in the restart `GameStarted`, not the
custom variant — directly corrupting the cell-D host-import path (R5-S01)
which drives variant games turn-by-turn via snapshots.

This file pins the fix with explicit, deterministic examples (it does NOT
rely on the gitignored `.hypothesis/` example database). The matching
property test is `tests/property/test_variant_sweep.py::
test_variant_snapshot_round_trip_holds`.

Port-to-port: enters through the `Game(...)` / `Game.from_snapshot(...)` /
`Game.step(...)` driving ports and the public `snapshot()` + emitted
`GameStarted` projections. No private engine internals are inspected beyond
the engine-emission record `_debug_events` already used as the observable by
the determinism + variant-sweep suites.
"""

from __future__ import annotations

from wumpus import Game
from wumpus.events import GameStarted
from wumpus.serialization import snapshot_from_json, snapshot_to_json
from wumpus.types import VariantConfig

# The RCA's minimal non-Yob variant. Every dimension diverges from
# `VariantConfig()` in a way the OLD code silently dropped:
#   - pit_count=0 / bat_count=0   -> zero-collapsed hazard tuples
#   - arrow_count=1               -> different out-of-arrows terminal
#   - arrow_max_range=1           -> no World footprint at all (Yob default 5)
#   - wumpus_move_prob=0.0        -> no World footprint at all (Yob default 0.75)
_CUSTOM_VARIANT = VariantConfig(
    room_count=20,
    wumpus_count=1,
    pit_count=0,
    bat_count=0,
    arrow_count=1,
    arrow_max_range=1,
    wumpus_move_prob=0.0,
)

_SEED = 0


def _round_trip(snap_source: Game) -> Game:
    """Snapshot `snap_source`, JSON-round-trip it (SC6 serializability), and
    resurrect a fresh Game from the decoded Snapshot."""
    restored_snapshot = snapshot_from_json(snapshot_to_json(snap_source.snapshot()))
    return Game.from_snapshot(restored_snapshot)


def test_restored_game_snapshot_preserves_custom_variant() -> None:
    """A non-Yob game, snapshotted -> JSON round-tripped -> resurrected, must
    report the SAME `variant_config` in its own snapshot. Pre-fix the restored
    game's snapshot reports Yob defaults (the hardcoded `VariantConfig()`)."""
    original = Game(seed=_SEED, variant=_CUSTOM_VARIANT)
    restored = _round_trip(original)

    assert restored.snapshot().variant_config == original.snapshot().variant_config, (
        "Restored game's variant_config diverged from the original.\n"
        f"  original: {original.snapshot().variant_config!r}\n"
        f"  restored: {restored.snapshot().variant_config!r}"
    )
    # And it must specifically equal the custom variant, not Yob defaults.
    assert restored.snapshot().variant_config == _CUSTOM_VARIANT.as_dict(), (
        "Restored game's variant_config is not the custom variant.\n"
        f"  expected (custom): {_CUSTOM_VARIANT.as_dict()!r}\n"
        f"  got:               {restored.snapshot().variant_config!r}\n"
        f"  Yob default:       {VariantConfig().as_dict()!r}"
    )


def _drive_to_same_setup(game: Game) -> None:
    """Drive `game` from the pre-game INSTRUCTIONS state into a terminal so it
    parks at the post-terminal SAME SET-UP prompt.

    Path: dismiss instructions (N), then fire a single one-room arrow at an
    adjacent room. With `arrow_count=1` the shot's decrement runs the player
    out of arrows -> `GameEnded(out_of_arrows)` -> the engine parks at
    `pending_prompt="same_setup"`. (A startled-wumpus eat is an equally-valid
    terminal; either way the engine parks at same_setup.) The adjacent room is
    read from the public LocationReported in the event stream so the path is a
    valid single tunnel regardless of the seed's layout.
    """
    game.step("N")  # dismiss the pre-game INSTRUCTIONS (Y-N)? prompt
    located = [e for e in game._debug_events if type(e).__name__ == "LocationReported"]
    assert located, "Expected a LocationReported in the opening event stream."
    adjacent_room = located[-1].adjacencies[0]
    game.step("S")  # SHOOT
    game.step("1")  # NO. OF ROOMS = 1
    game.step(str(adjacent_room))  # the single arrow-path room


def test_same_setup_restart_on_restored_game_emits_custom_variant() -> None:
    """The RCA's headline break: after a snapshot round-trip, a SAME SET-UP
    ('Y') restart must emit a restart `GameStarted` whose `variant_config`
    matches the custom variant, NOT Yob defaults.

    We drive the ORIGINAL game to a same-setup terminal, snapshot THERE,
    JSON-round-trip, resurrect, then `step("Y")` and read the restart
    `GameStarted` from the resurrected game's event stream.
    """
    original = Game(seed=_SEED, variant=_CUSTOM_VARIANT)
    _drive_to_same_setup(original)
    assert original.world_state().pending_prompt == "same_setup", (
        "Test precondition failed: original game did not park at same_setup "
        f"(pending_prompt={original.world_state().pending_prompt!r})."
    )

    restored = _round_trip(original)
    pre_restart = len(restored._debug_events)
    restored.step("Y")  # SAME SET-UP=Y -> _restore_initial_layout -> GameStarted

    restart_events = [
        e
        for e in restored._debug_events[pre_restart:]
        if isinstance(e, GameStarted)
    ]
    assert len(restart_events) == 1, (
        f"SAME SET-UP=Y must emit exactly one restart GameStarted; "
        f"got {len(restart_events)}: {restart_events!r}"
    )
    assert restart_events[0].variant_config == _CUSTOM_VARIANT.as_dict(), (
        "SAME SET-UP=Y restart emitted the WRONG variant_config on a restored "
        "non-Yob game (the RCA bug).\n"
        f"  expected (custom): {_CUSTOM_VARIANT.as_dict()!r}\n"
        f"  got:               {restart_events[0].variant_config!r}\n"
        f"  Yob default:       {VariantConfig().as_dict()!r}"
    )
