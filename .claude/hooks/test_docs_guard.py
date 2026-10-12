"""Negative witnesses for docs_guard.py.

Each case replays a hook payload through the real script, the way Claude Code
invokes it, and asserts the decision. The deny cases replay the historical
wound: the per-wave docs/feature/wumpus-classic/discuss/ folder that was later
archived. Run: python3 -m unittest discover -s .claude/hooks
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

GUARD = Path(__file__).with_name("docs_guard.py")
ROOT = "/repo"


def run_guard(file_path: str, tool: str = "Write", key: str = "file_path"):
    payload = {"tool_name": tool, "tool_input": {key: file_path}, "cwd": ROOT}
    env = {**os.environ, "CLAUDE_PROJECT_DIR": ROOT}
    proc = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    decision = None
    if proc.stdout.strip():
        decision = json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"]
    return proc.returncode, decision


class DeniesPerWaveProse(unittest.TestCase):
    def test_historical_discuss_folder(self):
        path = f"{ROOT}/docs/feature/wumpus-classic/discuss/user-stories.md"
        self.assertEqual(run_guard(path), (0, "deny"))

    def test_yaml_in_design_folder(self):
        path = f"{ROOT}/docs/feature/wumpus/design/adr-002.yaml"
        self.assertEqual(run_guard(path, tool="Edit"), (0, "deny"))

    def test_relative_path(self):
        self.assertEqual(run_guard("docs/feature/x/distill/notes.md"), (0, "deny"))


class AsksBeforeProductSsot(unittest.TestCase):
    def test_architecture_brief(self):
        path = f"{ROOT}/docs/product/architecture/brief.md"
        self.assertEqual(run_guard(path, tool="Edit"), (0, "ask"))


class AllowsEverythingElse(unittest.TestCase):
    def test_allowed_paths(self):
        allowed = [
            "docs/feature/wumpus/feature-delta.md",
            "docs/feature/wumpus/deliver/roadmap.json",
            "docs/feature/wumpus/deliver/mutation/mutation-report.md",
            "docs/feature/wumpus/deliver/mutation/cosmic-ray.toml",
            "docs/feature/.archive/wumpus-classic-2026-05-20/discuss/story-map.md",
            "docs/feature/wumpus/play-sessions/README.md",
            "docs/research-summaries/llm-modulo/llm-modulo.md",
            "docs/product",
            "/elsewhere/docs/feature/x/discuss/a.md",
        ]
        for rel in allowed:
            path = rel if rel.startswith("/") else f"{ROOT}/{rel}"
            with self.subTest(path=path):
                self.assertEqual(run_guard(path), (0, None))

    def test_notebook_path_key(self):
        path = f"{ROOT}/python/notebooks/scratch.ipynb"
        result = run_guard(path, tool="NotebookEdit", key="notebook_path")
        self.assertEqual(result, (0, None))


class FailsOpenLoudly(unittest.TestCase):
    def test_malformed_payload_reports_error(self):
        proc = subprocess.run(
            [sys.executable, str(GUARD)],
            input="not json",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("unreadable hook payload", proc.stderr)


if __name__ == "__main__":
    unittest.main()
