"""Acceptance-layer fixtures + pytest-bdd configuration for the wumpus engine.

Per DISTILL wave decisions:
  - Test framework: pytest-bdd (Gherkin .feature files + step definitions)
  - File layout: features at `tests/acceptance/features/`; step defs at `tests/acceptance/step_definitions/`
  - One .feature file per release (test_R0, test_R1, ...) at the granularity the
    Outside-In TDD rhythm requires.

Fixtures here are scoped to the acceptance test layer. Cross-layer fixtures
(seeds, fixture-files) live in `tests/conftest.py`.
"""

from __future__ import annotations

import pytest

# pytest-bdd uses scenarios() loaders in the test files themselves; no global
# bdd_strict_gherkin or other settings needed at this stage. Settings live
# alongside the scenarios in `step_definitions/test_R<N>_*.py` files.


@pytest.fixture
def in_memory_sink_factory():
    """Returns a factory that produces a fresh in-memory sink each time it's called.

    Used by R0 acceptance scenarios that need to compare event sequences between
    two paired runs (with sink vs. without sink, or between two independent Game
    instances).

    The actual InMemorySink class is implemented by DELIVER's R0 slice; this
    fixture imports it lazily so DISTILL can pin the contract before the
    implementation lands.
    """

    def _factory():
        # Lazy import: this will fail with ImportError until DELIVER R0 lands.
        # That failure is the Outside-In TDD red state.
        from wumpus.sinks import InMemorySink  # noqa: F401

        return InMemorySink()

    return _factory


@pytest.fixture
def make_game():
    """Factory that constructs a Game with the R0 toy-cave fixture.

    R0 uses a hardcoded 3-room linear cave with one wumpus; this is NOT the
    real dodecahedron (that lands at R1-S01). The fixture is intentional: R0
    locks the abstractions on the cheapest substrate.

    Post R1-S01, `Game(seed=k)` defaults to the real Yob dodecahedron. The
    R0 acceptance scenarios still rely on the toy cave's deterministic
    "move 1 -> 2 -> 3" path, so this factory threads `cave="toy"` through.
    """

    def _make(seed: int = 42):
        from wumpus import Game  # noqa: F401

        return Game(seed=seed, cave="toy")

    return _make
