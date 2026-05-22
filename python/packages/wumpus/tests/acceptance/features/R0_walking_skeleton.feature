# R0 Walking Skeleton — acceptance criteria
#
# Pinned by DISCUSS [REF] User Stories § R0 + amended for the world_state() AC.
# At this stage these scenarios should FAIL for business-logic reasons:
#   - `from wumpus import Game` raises ImportError (Game doesn't exist yet)
#   - That's the Outside-In TDD "red" state; DELIVER's R0 slice makes them green.
#
# Pre-conditions all R0 scenarios share:
#   - A toy 3-room linear cave with one wumpus (no other hazards yet)
#   - No CLI (programmatic only)
#   - Placeholder strings (NOT the Yob surface — that lands at R1)
#   - In-memory event sink only (JsonlSink lands at R2)
#   - Seeded RNG via the engine's internal random.Random instance

Feature: R0 walking skeleton — toy-cave engine, deterministic, event-emitting

  As a wumpus-engine maintainer
  I want the engine's core abstractions (Game, Observation, Event, deterministic-from-seed)
  to exist end-to-end on the cheapest possible substrate
  So that R1's Yob-fidelity work has a known-good architectural foundation
  and any architecture surprise surfaces here when refactor cost is minimal.

  Background:
    Given the engine uses a 3-room linear cave with one wumpus
    And no module-level mutable state has been initialized in wumpus.engine

  Scenario: Deterministic-from-seed event sequence (R0 primary AC)
    Given two independent Game(seed=42) instances
    And both will run the action sequence ["move 2", "move 3"]
    When both instances execute the action sequence to completion
    Then both produce equal event sequences (deep equality)
    And both produce equal final Snapshots
    And neither instance has any module-level side effect on the engine package

  Scenario: In-memory sink does not change emission (observer-effect absent)
    Given a Game(seed=42) running the action sequence ["move 2", "move 3"]
    When the run is performed once with no sinks attached
    And the run is performed once with an InMemorySink attached
    Then the in-engine event sequences emitted are identical between the two runs
    And the in-memory sink's recorded events equal the engine's internal emission order

  Scenario: Game.world_state() exposes full internal state without mutation
    Given a Game(seed=42) instance in any state
    When Game.world_state() is called twice in succession
    Then both calls return structurally equal world states
    And neither call advances the engine's RNG cursor
    And neither call emits any event to attached sinks
    And the returned world state contains the player room, wumpus room, arrow count, alive/dead flag, turn counter, pending_prompt, and pending_arrow_path
