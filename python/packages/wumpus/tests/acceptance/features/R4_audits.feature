# R4-S04 — surface-leak static audit (SC8).
#
# The fourth K-5 audit gate lands here: the surface-leak audit enforces that
# engine code (wumpus.engine.* + wumpus.types) references NO Yob surface-form
# string literal. R4-S03 consolidated every such string into
# wumpus.surfaces.yob; this audit keeps the seam clean on every PR.
#
# The audit's detection rule is the *precise* approach: a literal is a leak iff
# it is byte-exact to a Yob PROSE catalogue entry (harvested at runtime from
# wumpus.surfaces.yob), MINUS the discriminator alphabet (mapping-dict keys +
# the single-letter command tokens "S"/"M"/"Y"/"N"). It excludes comments (not
# AST nodes) and docstrings (skipped by position) so the engine's legitimate
# mentions of Yob phrases in prose are not false positives.
#
# Like the R3-S03 audits, the surface-leak audit additionally ships a
# "tests-the-tester" self-test (tests/audits/test_surface_leak_self.py) that
# injects a synthetic leak and asserts the audit flags it — guarding against an
# audit that silently no-ops.

Feature: R4 audits — surface-leak (SC8)

  As harness-harriet running Mystery probes
  I want an automated audit that catches accidental surface-string leaks into
  engine code
  So that the obfuscation-gap measurement claim (SC9) can't silently rot when a
  future PR inlines a Yob string instead of routing it through the surface.

  # ---------------------------------------------------------------------------
  # R4-S04 — Scenario 1: audit passes clean on the real engine + types (SC8)
  # ---------------------------------------------------------------------------

  Scenario: Surface-leak audit finds zero Yob-string hits in engine + types
    Given the surface-leak audit runs over wumpus.engine and wumpus.types
    Then it exits 0 with no surface-form string leaks
    And the engine's docstring + comment mentions of Yob phrases are not flagged

  # ---------------------------------------------------------------------------
  # R4-S04 — Scenario 2: audit fails fast on an injected regression
  # ---------------------------------------------------------------------------

  Scenario: Surface-leak audit fails fast on an injected leak
    Given an engine module that inlines the Yob string "I SMELL A WUMPUS!"
    When the surface-leak audit runs over it
    Then it exits non-zero
    And the failure message points at the file and line of the violation
