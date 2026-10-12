"""Negative witnesses for check_svg_theme.py.

Run: python3 -m unittest discover -s scripts
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CHECK = Path(__file__).with_name("check_svg_theme.py")

THEMED_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">
  <style>
    .ink { color: #1a1810; }
    @media (prefers-color-scheme: dark) { .ink { color: #ede2c4; } }
  </style>
  <g class="ink"><rect width="10" height="10" fill="currentColor"/></g>
</svg>
"""
LIGHT_ONLY_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">
  <rect width="10" height="10" fill="#1a1810"/>
</svg>
"""


class CheckSvgTheme(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def check(self, name: str, text: str) -> subprocess.CompletedProcess:
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(CHECK), str(path)],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_accepts_themed_svg(self):
        self.assertEqual(self.check("ok.svg", THEMED_SVG).returncode, 0)

    def test_rejects_single_mode_palette(self):
        proc = self.check("light.svg", LIGHT_ONLY_SVG)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("prefers-color-scheme", proc.stderr)

    def test_rejects_malformed_svg(self):
        proc = self.check("broken.svg", THEMED_SVG.replace("</svg>", ""))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("not valid XML", proc.stderr)

    def test_rejects_inline_svg_in_markdown(self):
        proc = self.check("page.md", "# Title\n\n" + THEMED_SVG)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("inline <svg>", proc.stderr)

    def test_accepts_svg_mentioned_in_code(self):
        text = "Use `<svg>` via an image.\n\n```html\n<svg></svg>\n```\n"
        self.assertEqual(self.check("doc.md", text).returncode, 0)

    def test_accepts_image_reference(self):
        text = "![glyph](images/glyph.svg)\n"
        self.assertEqual(self.check("doc.md", text).returncode, 0)


if __name__ == "__main__":
    unittest.main()
