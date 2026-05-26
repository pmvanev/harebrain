# R3-S03 — static audits (SC1 determinism-source + SC7 module-state) + the
# parallel-instance isolation proof.
#
# Two of the four K-5 audit gates land here:
#   - determinism-source (SC1): the engine + surfaces source has no non-seed
#     entropy. The secrets.randbits seed-bootstrap is the ONE permitted
#     entropy source (carve-out approach a — allowed only inside the
#     `_bootstrap_seed` helper).
#   - module-state (SC7): the `wumpus` package has no module-level mutable
#     state written by engine code, and no singleton-cached random.Random.
#
# The 100-instance parallel-isolation property ships as a plain pytest test
# at tests/property/test_parallel_isolation.py (concurrency does not fit
# pytest-bdd well); scenario 3 below is a thin wrapper that delegates to it.
#
# Each audit additionally ships a "tests-the-tester" self-test
# (tests/audits/test_<audit>_self.py) that injects a synthetic violation and
# asserts the audit flags it — guarding against an audit that silently no-ops.

Feature: R3 audits — determinism-source + module-state + parallel isolation

  As an mpl-cell-consumer
  I want the engine genuinely free of non-seed entropy and shared mutable state
  So that every host-import call starts fresh from snapshot with no surprises
  from a co-resident sibling instance.

  # ---------------------------------------------------------------------------
  # R3-S03 — Scenario 1: determinism-source audit passes clean (SC1)
  # ---------------------------------------------------------------------------

  Scenario: Determinism-source audit passes clean on engine + surfaces
    Given the determinism-source audit runs over wumpus.engine and wumpus.surfaces
    Then it exits 0 with no violations
    And the secrets.randbits seed-bootstrap carve-out is respected (not flagged)

  # ---------------------------------------------------------------------------
  # R3-S03 — Scenario 2: module-state audit passes clean (SC7)
  # ---------------------------------------------------------------------------

  Scenario: Module-state audit passes clean on the engine package
    Given the module-state audit runs over wumpus
    Then it exits 0 with no module-level mutable state written by engine code

  # ---------------------------------------------------------------------------
  # R3-S03 — Scenario 3: 100 parallel instances do not share state (SC7 runtime)
  # ---------------------------------------------------------------------------

  Scenario: 100 parallel Game instances do not share state
    Given 100 Game instances constructed with distinct seeds
    When all 100 are stepped concurrently through random action sequences
    Then each instance's final snapshot equals its serial-only equivalent
    And no instance observes another instance's state
