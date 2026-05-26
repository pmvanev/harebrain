"""R3-S03 acceptance step definitions — determinism-source + module-state
audits + parallel-instance isolation.

The audit scenarios enter through each audit's driving port (the
`audit(roots)` collector / `main(argv)` CLI entry) and assert on observable
outcomes (exit code + returned violations) — exactly what the audits.yml CI
job observes. The carve-out scenario additionally asserts the engine's real
`secrets.randbits` seed-bootstrap is NOT among the violations.

Scenario 3 (100 parallel instances) delegates to the canonical property test
at tests/property/test_parallel_isolation.py — the concurrency proof lives
there (it does not fit pytest-bdd well); this acceptance scenario is a thin
wrapper invoking the same functions so the BDD suite documents the SC7
runtime contract.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from pytest_bdd import given, scenarios, then, when

from wumpus.audits import determinism_source, module_state

# Import the canonical property-test helpers so scenario 3 delegates rather
# than re-implementing the concurrency proof.
import sys

_PROPERTY_DIR = Path(__file__).resolve().parents[2] / "property"
if str(_PROPERTY_DIR) not in sys.path:
    sys.path.insert(0, str(_PROPERTY_DIR))

import test_parallel_isolation as parallel  # noqa: E402

scenarios("../features/R3_audits.feature")

# Source roots the audits.yml workflow scans (repo-root relative).
_REPO_ROOT = Path(__file__).resolve().parents[6]
_SRC = _REPO_ROOT / "python" / "packages" / "wumpus" / "src" / "wumpus"
_ENGINE_ROOT = _SRC / "engine"
_SURFACES_ROOT = _SRC / "surfaces"
_WUMPUS_ROOT = _SRC


# ---------------------------------------------------------------------------
# Scenario 1 — determinism-source audit passes clean
# ---------------------------------------------------------------------------


@given(
    "the determinism-source audit runs over wumpus.engine and wumpus.surfaces",
    target_fixture="determinism_result",
)
def _determinism_result() -> dict[str, Any]:
    roots = [str(_ENGINE_ROOT), str(_SURFACES_ROOT)]
    return {
        "violations": determinism_source.audit(roots),
        "exit_code": determinism_source.main(roots),
    }


@then("it exits 0 with no violations")
def _determinism_clean(determinism_result: dict[str, Any]) -> None:
    assert determinism_result["exit_code"] == 0, (
        "Determinism-source audit exited non-zero on real engine/surfaces:\n  "
        + "\n  ".join(v.render() for v in determinism_result["violations"])
    )
    assert determinism_result["violations"] == []


@then("the secrets.randbits seed-bootstrap carve-out is respected (not flagged)")
def _carve_out_respected(determinism_result: dict[str, Any]) -> None:
    # No violation mentions `secrets` — the engine's legitimate
    # `secrets.randbits` seed-bootstrap (inside `_bootstrap_seed`) is allowed.
    secret_hits = [v for v in determinism_result["violations"] if "secrets" in v.reason]
    assert secret_hits == [], (
        "The secrets.randbits seed-bootstrap carve-out was flagged:\n  "
        + "\n  ".join(v.render() for v in secret_hits)
    )


# ---------------------------------------------------------------------------
# Scenario 2 — module-state audit passes clean
# ---------------------------------------------------------------------------


@given("the module-state audit runs over wumpus", target_fixture="module_state_result")
def _module_state_result() -> dict[str, Any]:
    roots = [str(_WUMPUS_ROOT)]
    return {
        "violations": module_state.audit(roots),
        "exit_code": module_state.main(roots),
    }


@then("it exits 0 with no module-level mutable state written by engine code")
def _module_state_clean(module_state_result: dict[str, Any]) -> None:
    assert module_state_result["exit_code"] == 0, (
        "Module-state audit exited non-zero on real wumpus package:\n  "
        + "\n  ".join(v.render() for v in module_state_result["violations"])
    )
    assert module_state_result["violations"] == []


# ---------------------------------------------------------------------------
# Scenario 3 — 100 parallel instances do not share state
# ---------------------------------------------------------------------------


@given(
    "100 Game instances constructed with distinct seeds",
    target_fixture="parallel_seeds",
)
def _parallel_seeds() -> list[int]:
    return list(range(1, parallel._INSTANCE_COUNT + 1))


@when(
    "all 100 are stepped concurrently through random action sequences",
    target_fixture="parallel_run",
)
def _parallel_run(parallel_seeds: list[int]) -> dict[str, Any]:
    action_sequences = {
        seed: parallel._action_sequence_for(seed) for seed in parallel_seeds
    }
    serial = {
        seed: parallel._run_to_snapshot_json(seed, action_sequences[seed])
        for seed in parallel_seeds
    }
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = {
            seed: pool.submit(
                parallel._run_to_snapshot_json, seed, action_sequences[seed]
            )
            for seed in parallel_seeds
        }
        concurrent = {seed: f.result() for seed, f in futures.items()}
    return {"serial": serial, "concurrent": concurrent, "seeds": parallel_seeds}


@then("each instance's final snapshot equals its serial-only equivalent")
def _snapshots_match_serial(parallel_run: dict[str, Any]) -> None:
    mismatches = [
        seed
        for seed in parallel_run["seeds"]
        if parallel_run["concurrent"][seed] != parallel_run["serial"][seed]
    ]
    assert not mismatches, (
        f"{len(mismatches)} concurrent instances diverged from their serial "
        f"baseline (seeds: {mismatches[:10]}). SC7 runtime isolation violated."
    )


@then("no instance observes another instance's state")
def _no_cross_observation(parallel_run: dict[str, Any]) -> None:
    for seed in parallel_run["seeds"]:
        snapshot_json = parallel_run["concurrent"][seed]
        assert f'"seed": {seed}' in snapshot_json, (
            f"Concurrent Game(seed={seed}) snapshot does not carry its own "
            f"seed — it observed another instance's state."
        )
