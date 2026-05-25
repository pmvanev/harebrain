"""Top-level pytest fixtures for the wumpus package.

Per the harebrain convention + DISTILL wave file layout:
  - `tests/conftest.py` — fixtures available to ALL test types (unit, integration, acceptance)
  - `tests/acceptance/conftest.py` — fixtures specific to the acceptance (BDD) layer
  - Acceptance .feature files live at `tests/acceptance/features/`
  - Step definitions live at `tests/acceptance/step_definitions/`

R2-S03: registers hypothesis profiles `ci` (fast: PR-gate latency budget) and
`ci-nightly` (thorough: 100 seeds × 50 actions per the K-2 KPI brief). The
profile selection is driven by `HYPOTHESIS_PROFILE` (defaults to `ci`).
"""

from __future__ import annotations

import os

import pytest
from hypothesis import HealthCheck, settings


# ---------------------------------------------------------------------------
# Hypothesis profiles — R2-S03
# ---------------------------------------------------------------------------
#
# `ci` runs on every PR-gate cell. Budget: small enough that the full wumpus
# suite stays inside the ~5 min PR-gate window (ADR-009). 20 examples per
# property × ~4 property tests = ~80 hypothesis trials. Empirically <10s.
#
# `ci-nightly` is the K-2 measurement profile (100 seeds × 50 actions, per
# the R2-S03 brief and the `nightly.yml` workflow). Larger phase budget but
# still bounded so the nightly job finishes inside the ~30 min cap.
#
# Property tests bind the seed/action bound dynamically from the active
# profile (see `tests/property/test_determinism.py`).

settings.register_profile(
    "ci",
    max_examples=20,
    deadline=None,
    suppress_health_check=(HealthCheck.too_slow, HealthCheck.data_too_large),
)
settings.register_profile(
    "ci-nightly",
    max_examples=100,
    deadline=None,
    suppress_health_check=(HealthCheck.too_slow, HealthCheck.data_too_large),
)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "ci"))


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
