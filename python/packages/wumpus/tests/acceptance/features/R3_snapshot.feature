# R3 snapshot — full-state capture + in-memory round-trip
#
# R3-S01 ships full Game-state snapshot/restore. The Snapshot dataclass is
# extended (Tier A2 amendment) with `initial_layout` and `cave` so a Game
# resurrected via `from_snapshot(snap)` is observationally equivalent to the
# original Game — including across SAME SET-UP=Y restores after a snapshot.
#
# Scope:
#   - R3-S01 ships scenarios 1 + 2 (in-memory round-trip + mid-prompt cover).
#   - The 1000-trial property test ships as `tests/property/test_snapshot.py`
#     (NOT a BDD scenario, mirroring R2-S03's K-2 hypothesis test convention).
#   - R3-S02 will add JSON serialization scenarios.
#   - R3-S03 will add the module-state audit + parallel-instance property.
#
# Per ADR-001 (hybrid paradigm) Snapshot is `@dataclass(frozen=True)`.
# Per ADR-002 (additive schema evolution) the new fields are additive — the
# v1 JSON Schema's Snapshot subschema gains optional properties without a
# major-version bump.
# Per SC6 (snapshot serializable) — R3-S01 verifies in-memory round-trip;
# R3-S02 will verify JSON round-trip.
# Per SC12 (snapshot is host-import floor) — R3-S01 establishes the
# in-memory contract; R5-S01 (blocked-on-spike) wires the MPL host-import
# adapter.

Feature: R3 snapshot — full-state capture + round-trip

  As an mpl-cell-consumer (and harness-harriet by inheritance)
  I want Game.snapshot() / Game.from_snapshot() to round-trip byte-identically
  So that experiment harnesses can pause + resume + replay games across processes.

  # ---------------------------------------------------------------------------
  # R3-S01 — Scenario 1: Snapshot round-trip preserves next event byte-identically
  # ---------------------------------------------------------------------------

  Scenario: Snapshot round-trip preserves next event byte-identically
    Given Game(seed=42, cave="toy") is stepped through actions ["move 2", "move 3"]
    And the snapshot is taken after action 1: snap = game.snapshot()
    When Game.from_snapshot(snap) is constructed and stepped through action 2 ("move 3")
    And the same Game(seed=42) is stepped through both actions in one process
    Then the events from the restored Game's action 2 step equal the single-process Game's action 2 step events byte-for-byte

  # ---------------------------------------------------------------------------
  # R3-S01 — Scenario 2: Snapshot covers mid-prompt state (pending_arrow_path)
  # ---------------------------------------------------------------------------

  Scenario: Snapshot covers mid-prompt state (pending_arrow_path)
    Given a session in mid-shoot with pending_arrow_path=[7, 14] and pending_path_length=3 and pending_prompt="shoot_path_room" (slot 3 awaited)
    When game.snapshot() is taken and Game.from_snapshot(snap) is constructed
    Then the resurrected game's world has pending_arrow_path=[7, 14]
    And the resurrected game's world has pending_path_length=3
    And the resurrected game prompts for ROOM #? at slot 3 on next step
