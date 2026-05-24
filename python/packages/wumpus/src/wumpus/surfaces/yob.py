"""Yob 1973 surface — verbatim strings from Gregory Yob's BASIC source.

This module is the ONLY place Yob's literal strings may appear in the
codebase (SC8). All other modules — engine, transitions, hazard_resolve,
arrow_walk — emit structured events (`HazardTriggered`, `GameEnded`, etc.)
and rely on this module to translate them into rendered lines.

R1-S07 ships the terminal + hazard subset:

    - HazardTriggered(kind) → "...OOPS! BUMPED A WUMPUS!" / "YYYIIIIEEEE . . .
      FELL IN PIT" / "ZAP--SUPER BAT SNATCH! ELSEWHEREVILLE FOR YOU!"
    - GameEnded(outcome, message_kind) → outcome-specific reason line + the
      Yob win/lose-swap tag ("HEE HEE HEE - THE WUMPUS'LL GETCHA NEXT TIME!!"
      on win, "HA HA HA - YOU LOSE!" on lose)

The full Surface Protocol (room labels, sense strings, command verbs,
instructions block, prompt text) lands at R4-S03; the R1-S08 instructions
block + RAMDOM typo lands separately. Sense-event Yob strings
("I SMELL A WUMPUS!", "I FEEL A DRAFT", "BATS NEARBY!") are deferred per
the R1-S07 brief's recommendation.

Per ADR-001 (hybrid paradigm) this module is pure-functional: module-level
constants + free functions. There is no `YobSurface` class — the module IS
the surface. Future variant surfaces (Mystery-Wumpus at R4-S05,
French at R4-S06) will follow the same shape: a sibling module under
`wumpus.surfaces` with the same public-function signatures.

Per D11 wave decision: the win/lose swap is structural. Yob's BASIC source
famously prints "HEE HEE HEE" on win (not "HA HA HA" as one would expect
from a "you lose" tag); the swap is the recognition signal of the 1973
game. We preserve it bug-for-bug.
"""

from __future__ import annotations

from wumpus.events import GameEnded, HazardTriggered

# ---------------------------------------------------------------------------
# Verbatim Yob strings — DO NOT edit without consulting
# `wumpus/docs/wumpus_python_goals.md` § Goal 1 "Messages — verbatim" table.
# Each constant traces to a specific line of the Yob BASIC source; the
# bug-for-bug fidelity contract (SC2) depends on byte-exact preservation.
# ---------------------------------------------------------------------------

# Hazard reason lines (one per HazardTriggered.kind variant).
HAZARD_BUMP_WUMPUS: str = "...OOPS! BUMPED A WUMPUS!"
HAZARD_PIT: str = "YYYIIIIEEEE . . . FELL IN PIT"
HAZARD_BAT: str = "ZAP--SUPER BAT SNATCH! ELSEWHEREVILLE FOR YOU!"

# Wumpus-kills-player (eaten_after_bump terminal reason).
TERMINAL_WUMPUS_GOT_YOU: str = "TSK TSK TSK- WUMPUS GOT YOU!"

# Win reason (arrow hits wumpus) — paired with the swapped win tag below.
TERMINAL_WUMPUS_SHOT: str = "AHA! YOU GOT THE WUMPUS!"

# Self-shot reason (arrow's final room == player's room).
TERMINAL_SELF_SHOT: str = "OUCH! ARROW GOT YOU!"

# Win/lose swap tags — D11 "the swap is the recognition signal".
WIN_TAG: str = "HEE HEE HEE - THE WUMPUS'LL GETCHA NEXT TIME!!"
LOSE_TAG: str = "HA HA HA - YOU LOSE!"

# Miss line (arrow walked the path without hitting wumpus or player).
ARROW_MISSED: str = "MISSED"


# ---------------------------------------------------------------------------
# Hazard kind → reason line mapping.
# ---------------------------------------------------------------------------

_HAZARD_LINE_BY_KIND: dict[str, str] = {
    "WUMPUS": HAZARD_BUMP_WUMPUS,
    "PIT": HAZARD_PIT,
    "BAT": HAZARD_BAT,
}


def render_hazard(event: HazardTriggered) -> tuple[str, ...]:
    """Translate a HazardTriggered event to its Yob reason line.

    Returns a 1-tuple of the verbatim Yob string for the hazard kind.
    Unknown kinds yield an empty tuple (defensive — the engine's literal
    set is constrained by the HazardTriggered.kind type alias, but the
    surface is paranoid about variant-config-driven extensions)."""
    line = _HAZARD_LINE_BY_KIND.get(event.kind)
    if line is None:
        return ()
    return (line,)


# ---------------------------------------------------------------------------
# Terminal outcome → reason line mapping.
#
# Each outcome maps to ONE reason line (the "what killed you" or "what won"
# narration) followed by the swap tag. The swap tag is determined by
# `GameEnded.message_kind`, NOT by the outcome, so a hypothetical variant
# that swaps message_kind to message_kind="win" on a loss would still get
# the WIN_TAG appended — which is exactly the D11 swap behavior.
# ---------------------------------------------------------------------------


_TERMINAL_REASON_BY_OUTCOME: dict[str, str] = {
    "wumpus_shot": TERMINAL_WUMPUS_SHOT,
    "eaten_after_bump": TERMINAL_WUMPUS_GOT_YOU,
    "fell_in_pit": HAZARD_PIT,
    # out_of_arrows has no extra reason line in Yob's source — the prior
    # ArrowMissed + ArrowCountChanged(new_count=0) chain already narrated
    # what happened. The terminal turn just gets the lose tag.
    "out_of_arrows": "",
}


def render_terminal(event: GameEnded) -> tuple[str, ...]:
    """Translate a GameEnded event to its Yob lines.

    Returns a tuple of (reason_line, swap_tag) — or just (swap_tag,) if the
    outcome carries no extra reason narration (out_of_arrows).
    """
    reason = _TERMINAL_REASON_BY_OUTCOME.get(event.outcome, "")
    tag = WIN_TAG if event.message_kind == "win" else LOSE_TAG
    if reason:
        return (reason, tag)
    return (tag,)


# ---------------------------------------------------------------------------
# Prompt text (R1-S07 ships just the SAME SET-UP prompt; the rest land at R4-S03).
# ---------------------------------------------------------------------------

PROMPT_SAME_SETUP: str = "SAME SET-UP (Y-N)?"


def render_same_setup_prompt() -> tuple[str, ...]:
    """Translate the post-terminal SAME SET-UP prompt to its Yob line."""
    return (PROMPT_SAME_SETUP,)


__all__ = [
    "HAZARD_BUMP_WUMPUS",
    "HAZARD_PIT",
    "HAZARD_BAT",
    "TERMINAL_WUMPUS_GOT_YOU",
    "TERMINAL_WUMPUS_SHOT",
    "TERMINAL_SELF_SHOT",
    "WIN_TAG",
    "LOSE_TAG",
    "ARROW_MISSED",
    "PROMPT_SAME_SETUP",
    "render_hazard",
    "render_terminal",
    "render_same_setup_prompt",
]
