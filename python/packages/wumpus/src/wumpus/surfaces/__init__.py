"""Surface package — the only place Yob (or any variant) strings may live.

Per SC8 (surface seam): engine code MUST NOT contain Yob string literals;
all rendered text flows through a Surface module that translates structured
events into output lines.

R1-S07 ships only the YobSurface terminal + hazard subset (the strings
needed by the win/lose swap and SAME SET-UP=Y restore acceptance). The
full Surface Protocol from Tier A5 (room labels, sense strings, command
verbs, instructions block, prompt text) lands at R4-S03; R1-S08 ships
the instructions block intermediate step.

Per ADR-001 (hybrid paradigm) surfaces are pure-functional: module-level
constants + free functions. No classes, no state, no side effects.
"""

from __future__ import annotations
