#!/usr/bin/env python3
"""PreToolUse guard for the docs layout conventions in CLAUDE.md.

Enforces two rules that used to live only as prose:

- Single-file feature convention: prose wave artifacts (.md, .yaml) belong in
  docs/feature/<feature>/feature-delta.md, never in per-wave folders. Machine
  state (.json, e.g. deliver/roadmap.json), deliver/mutation/ and .archive/
  stay writable.
- Product SSOT: files under docs/product/ belong to the orchestrator, so any
  write there asks the user first.

Reads the hook payload on stdin and prints a PreToolUse decision; prints
nothing (allow) when no rule applies. Tests: test_docs_guard.py.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import PurePosixPath

WAVES = {"discover", "discuss", "design", "distill", "devops", "deliver"}
PROSE_SUFFIXES = {".md", ".markdown", ".yaml", ".yml"}

DENY_REASON = (
    "Blocked by .claude/hooks/docs_guard.py. This repo keeps each feature's "
    "wave artifacts inline in docs/feature/<feature>/feature-delta.md (CLAUDE.md "
    "§ Feature documentation convention). Append a `## Wave: <WAVE> / [REF] ...` "
    "section there instead. Per-wave folders hold machine state only (.json, "
    "deliver/mutation/). If this file truly must live here, ask the user to "
    "extend the allowlist in docs_guard.py."
)
ASK_REASON = (
    "docs/product/ holds the product-level SSOT; the orchestrator updates it "
    "(CLAUDE.md § Feature documentation convention). Confirm this edit was "
    "directed."
)


def decide(rel: PurePosixPath) -> tuple[str, str] | None:
    """Return (decision, reason) for a repo-relative path, or None to allow."""
    parts = rel.parts
    if len(parts) > 2 and parts[:2] == ("docs", "product"):
        return "ask", ASK_REASON
    if len(parts) >= 5 and parts[:2] == ("docs", "feature"):
        feature, wave = parts[2], parts[3]
        if feature.startswith("."):
            return None
        if wave == "deliver" and parts[4] == "mutation":
            return None
        if wave in WAVES and rel.suffix.lower() in PROSE_SUFFIXES:
            return "deny", DENY_REASON
    return None


def repo_relative(file_path: str, root: str) -> PurePosixPath | None:
    absolute = os.path.normpath(os.path.join(root, file_path))
    rel = os.path.relpath(absolute, os.path.normpath(root))
    if rel == os.pardir or rel.startswith(os.pardir + os.sep):
        return None
    return PurePosixPath(rel.replace(os.sep, "/"))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as err:
        print(f"docs_guard: unreadable hook payload: {err}", file=sys.stderr)
        return 1
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not file_path:
        return 0
    root = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
    rel = repo_relative(file_path, root)
    verdict = decide(rel) if rel else None
    if verdict:
        decision, reason = verdict
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": decision,
                        "permissionDecisionReason": reason,
                    }
                }
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
