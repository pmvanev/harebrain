"""Property tests for the wumpus engine.

The K-2 (determinism) KPI is measured here. R2-S03 ships the first property
test (`test_determinism.py`); subsequent slices land additional property
files (R3-S01 snapshot round-trip, R4-S05 mystery seam, R5-S02 variant
parametric).

Per ADR-009, every property test in this directory runs in every PR-gate
CI cell. Speed-budget for the `ci` hypothesis profile is set in
`tests/conftest.py`; the `ci-nightly` profile is exercised by the nightly
matrix sweep.
"""
