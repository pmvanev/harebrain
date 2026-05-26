"""Static-audit scripts enforcing the engine's non-functional contract.

Each audit is an AST-based (stdlib ``ast``) scanner invokable as
``python -m wumpus.audits.<name> <source-roots...>``. The ``audits.yml`` CI
workflow calls each audit directly; a paired self-test fixture under
``tests/audits/test_<name>_self.py`` injects a synthetic violation to prove
the audit is not silently no-op'ing.

R3-S03 ships two of the four K-5 audits:

  - ``determinism_source`` — SC1: forbids non-seed entropy sources in engine
    + surface code (``time.time``, ``os.urandom``, bare ``random.X`` calls,
    ``secrets.*`` outside the seed-bootstrap carve-out, ``datetime.now``
    outside ``sinks/``).
  - ``module_state`` — SC7: forbids module-level mutable containers that are
    written to, and singleton-cached ``random.Random`` instances.

The remaining two (``surface_leak`` for SC8 / R4-S04, and the pytest-based
``snapshot_serializability`` for SC6 / R3-S02) ship in their own slices.
"""
