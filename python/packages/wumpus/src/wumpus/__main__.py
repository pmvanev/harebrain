"""Module entry point — `python -m wumpus` invokes `wumpus.cli.main`.

Per the R1-S09 subprocess-safety contract (SC3): this is the entry point
that pexpect/wexpect smoke tests spawn. The implementation is intentionally
trivial — all the CLI logic lives in `wumpus.cli` so it remains testable
in-process via injected `argv` / `stdin` / `stdout`.
"""

from __future__ import annotations

from wumpus.cli import main

if __name__ == "__main__":
    main()
