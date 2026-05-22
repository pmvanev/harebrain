"""Top-level pytest fixtures for the wumpus package.

Per the harebrain convention + DISTILL wave file layout:
  - `tests/conftest.py` — fixtures available to ALL test types (unit, integration, acceptance)
  - `tests/acceptance/conftest.py` — fixtures specific to the acceptance (BDD) layer
  - Acceptance .feature files live at `tests/acceptance/features/`
  - Step definitions live at `tests/acceptance/step_definitions/`
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Seeds — fixed values used across acceptance tests to keep them deterministic.
# These are NOT magic; they're the canonical "show what happens" seeds.
# ---------------------------------------------------------------------------


@pytest.fixture
def canonical_seed() -> int:
    """The default seed used in R0 walking-skeleton scenarios."""
    return 42


@pytest.fixture
def forced_loss_seed() -> int:
    """Seed chosen during R1-S10 fixture capture that produces a forced loss
    within ~3 turns. Used by acceptance + subprocess smoke tests once R1 lands.
    """
    return 17  # placeholder; actual value pinned during R1-S10 BASIC capture


@pytest.fixture
def forced_win_seed() -> int:
    """Seed chosen during R1-S10 fixture capture that produces a forced win.
    Placeholder; actual value pinned during R1-S10 BASIC capture.
    """
    return 99  # placeholder
