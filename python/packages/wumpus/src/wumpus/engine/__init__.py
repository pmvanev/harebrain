"""Engine package marker. Re-exports `Game` for top-level imports.

Per `[REF] Engine module layout`, `wumpus.engine.__init__` exists solely to
make `from wumpus.engine import Game` available alongside the top-level
`from wumpus import Game` re-export.
"""

from __future__ import annotations

from wumpus.engine.game import Game

__all__ = ["Game"]
