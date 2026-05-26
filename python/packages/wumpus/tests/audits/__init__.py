"""Audit-gate test suites for the wumpus engine (K-5).

Each file here is a CI audit gate referenced by `.github/workflows/audits.yml`:

  - `test_snapshot_serializability.py` — SC6 snapshot-serializability gate
    (R3-S02): the 6 canonical fixture snapshots round-trip byte-identically
    through JSON, including a real cross-process subprocess proof.
  - `test_determinism_source_self.py` / `test_module_state_self.py` /
    `test_surface_leak_self.py` — the AST-audit self-tests land at R3-S03
    and R4-S04.

Per the harebrain test-layout convention these audit suites are runnable
pytest tests (not standalone scripts), so the CI workflow invokes them via
`pytest tests/audits/<file>.py`.
"""
