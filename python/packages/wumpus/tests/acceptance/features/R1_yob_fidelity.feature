# R1 Yob fidelity — acceptance criteria
#
# Each R1 slice appends its scenarios to this file. R1-S01 ships the first 4
# scenarios (dodecahedron + cave gen from seed); subsequent R1 slices append
# their own scenarios as they land.
#
# Pre-conditions all R1 scenarios share:
#   - The real 20-room dodecahedron (NOT the R0 toy cave)
#   - Yob's FNB rejection-loop entity placement
#   - Seeded RNG via the engine's internal random.Random instance
#   - Placeholder surface strings (real Yob surface lands at R4-S03)

Feature: R1 Yob fidelity — dodecahedron cave + Yob mechanics

  As a researcher driving harness experiments
  I want Game(seed=k) to produce a deterministic dodecahedron layout
  with the audited 20x3 adjacency and Yob's FNB entity placement
  So that seeded replays and cross-cell comparisons share a known geometry
  without any per-run regeneration drift.

  # ---------------------------------------------------------------------------
  # R1-S01 — Dodecahedron + cave gen from seed
  # ---------------------------------------------------------------------------

  Scenario: Layout is determined by seed
    Given seed = 42
    When Game(seed=42) is constructed twice in separate Python processes
    Then both constructions produce identical _initial_layout (wumpus room, pit rooms, bat rooms, player start)

  Scenario: All entity rooms are distinct
    Given Game(seed=k) for any integer k
    Then the wumpus room, both pit rooms, both bat rooms, and the player start are all distinct rooms

  Scenario: Adjacency is the audited 20x3 dodecahedron
    Given the wumpus.constants.DODECAHEDRON table
    Then it matches the 20x3 table in the archived shared-artifacts-registry (rooms 1-20 with their three tunnels each)

  Scenario: random.Random stability regression
    Given a Python 3.11+ interpreter
    When random.Random(42).randrange(20) is invoked
    Then the result equals a pinned constant (catches Python-stdlib drift at CI time)
