# R5 host-import — drive the engine one turn at a time from a serialized snapshot
#
# R5-S01 promotes the validated host-import spike into the production seam
# `wumpus.host_import.step_from_snapshot(snap_json, action) -> StepResult`.
# This is the engine side of goals-doc done-criterion #3 / KPI K-4 and lands
# SC12 (the snapshot is the host-import floor): an MPL chart leaf — or any host
# whose OS process exits between turns — drives the engine by passing the
# *serialized* snapshot in and getting the next serialized snapshot back.
#
# The seam is built entirely on the public `wumpus` exports + the `subscribe()`
# port (a fresh Sink captures ONLY this turn's events, so the `from_snapshot`
# GameStarted/PromptIssued preamble never leaks). Zero `engine/*` edits.
#
# Walking skeleton: ONE acceptance test, thinnest end-to-end slice, real
# subprocess + real serialized-snapshot I/O for the exit-between-turns proof.

@walking_skeleton @driving_port @wiring_e2e
Feature: R5 host-import — drive the engine from a serialized snapshot

  As an mpl-cell-consumer
  I want to drive the engine one turn at a time from a serialized snapshot string
  So that a host whose process exits between turns can play the game (job: drive-engine-from-host-import)

  # ---------------------------------------------------------------------------
  # Scenario 1 — Host-import round-trip progresses one turn
  # ---------------------------------------------------------------------------

  Scenario: Host-import round-trip progresses one turn
    Given a captured snapshot from Game(seed=4) with the instructions prompt answered
    When a host calls step_from_snapshot(snap, "move <adjacent>") and writes the returned snapshot back
    Then the game has progressed one turn
    And this turn's events were emitted without the resurrection preamble
    And the returned snapshot is canonical JSON

  # ---------------------------------------------------------------------------
  # Scenario 2 — Process can exit between turns without affecting the next call
  # ---------------------------------------------------------------------------

  Scenario: Process can exit between turns without affecting the next call
    Given an initial snapshot from Game(seed=4) with the instructions prompt answered
    When each of the legal adjacent moves ["move 1", "move 2"] is applied in a FRESH subprocess feeding snap(i) to snap(i+1)
    Then the resulting state-hash sequence equals a single-in-process baseline of the same actions
