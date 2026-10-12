#!/usr/bin/env python3
"""Pre-commit check for the theme-adaptive SVG convention (CLAUDE.md § SVG).

- Every SVG must parse as XML and carry an
  `@media (prefers-color-scheme: dark)` block, because Phil reads markdown in
  dark mode and a single-mode palette disappears there.
- Markdown must reference SVGs as images, never inline `<svg>`: GitHub's
  sanitizer strips inline SVG and its embedded <style>.

Usage: check_svg_theme.py FILE... (pre-commit passes staged .svg/.md files).
Tests: test_check_svg_theme.py.
"""

from __future__ import annotations

import re
import sys
import xml.dom.minidom
from pathlib import Path
from xml.parsers.expat import ExpatError

DARK_BLOCK = re.compile(r"@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)")
INLINE_SVG = re.compile(r"<svg[\s>]", re.IGNORECASE)
FENCE = re.compile(r"^(```|~~~).*?^\1", re.MULTILINE | re.DOTALL)
CODE_SPAN = re.compile(r"`[^`\n]*`")


def problems(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".svg":
        try:
            xml.dom.minidom.parseString(text)
        except ExpatError as err:
            return [f"{path}: not valid XML ({err})"]
        if not DARK_BLOCK.search(text):
            return [f"{path}: no @media (prefers-color-scheme: dark) block"]
    elif path.suffix == ".md":
        prose = CODE_SPAN.sub("", FENCE.sub("", text))
        if INLINE_SVG.search(prose):
            return [f"{path}: inline <svg>; reference it with ![alt](path.svg)"]
    return []


def main(argv: list[str]) -> int:
    found = [msg for arg in argv for msg in problems(Path(arg))]
    for msg in found:
        print(msg, file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
