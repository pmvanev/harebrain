"""wumpus — the engine the harebrain experiment matrix runs on.

Faithful Yob 1973 at the core, extensible at the seams, observable by construction.

Public API surfaces here as the wave artifacts (DESIGN [REF] Engine module layout)
implement each slice. At R0 (walking skeleton), only `Game` + minimal types are exported.
"""

__version__ = "0.0.0"

# Public API — re-exports land here as DELIVER implements each slice.
# At R0, the imports below should resolve once R0's implementation lands.
# Currently empty: DELIVER's R0 slice is responsible for the first commit
# that makes the acceptance tests pass.

# Intentionally NOT exporting at this point. The acceptance tests should fail
# with `ImportError: cannot import name 'Game' from 'wumpus'` until DELIVER
# lands the R0 slice — that's the Outside-In TDD "red" state.
