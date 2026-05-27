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

from wumpus.events import GameEnded, HazardTriggered, InstructionsShown
from wumpus.types import CommandVerb, ParsedCommand

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

# Crooked-arrow rejection line (path entry where P(K) == P(K-2)).
CROOKED_REJECTION: str = "ARROWS AREN'T THAT CROOKED - TRY ANOTHER ROOM"

# Off-graph move line (player tried to move to a non-adjacent room). Verbatim
# from `wumpus.gwbasic.bas` line 4100 (`PRINT "NOT POSSIBLE -";`). Yob then
# GOTO 4020 to re-print the WHERE TO? prompt without consuming the turn (G6 /
# goals.md § Goal 1 "off-graph moves re-prompt without consuming the turn").
OFF_GRAPH_MOVE: str = "NOT POSSIBLE -"

# ---------------------------------------------------------------------------
# R4-S03 — sense lines + prompt text + command tokens.
#
# These complete the Surface seam: every surface-form string the engine emits
# now lives behind this module (SC8). The sense lines were deferred at R1-S07
# (the R1-S07 brief recommended deferring them); R4-S03 lands them so the full
# Surface Protocol covers them. Verbatim from `wumpus_python_goals.md`
# § Goal 1 "Messages — verbatim".
# ---------------------------------------------------------------------------

# Sense lines (one per SenseEmitted.kind).
SENSE_WUMPUS_SMELL: str = "I SMELL A WUMPUS!"
SENSE_PIT_DRAFT: str = "I FEEL A DRAFT"
SENSE_BAT_NEARBY: str = "BATS NEARBY!"

# Location render prefixes (LocationReported → the per-turn "where am I" lines).
# Verbatim from `wumpus.gwbasic.bas` line 2130 (`PRINT "YOU ARE IN ROOM "L(1)`)
# and line 2140 (`PRINT "TUNNELS LEAD TO "S(L,1);S(L,2);S(L,3)`). Each literal
# carries ONE trailing space; GW-BASIC prefixes a positive number with a second
# (sign-position) space when PRINTing it, yielding the deliberate DOUBLE space
# in "YOU ARE IN ROOM  <n>" / "TUNNELS LEAD TO  <a>  <b>  <c>" (goals.md
# § Goal 1: "the double spaces ... are deliberate"). `render_location` rebuilds
# that GW-BASIC numeric spacing without embedding the rendered digits here.
LOCATION_ROOM_PREFIX: str = "YOU ARE IN ROOM "
LOCATION_TUNNELS_PREFIX: str = "TUNNELS LEAD TO "

# Prompt text (one per PromptKind discriminator). The double space in
# "YOU ARE IN ROOM  <n>" / "TUNNELS LEAD TO  <a>  <b>  <c>" is deliberate
# (goals.md § Goal 1); those are LocationReported renders, not prompts.
PROMPT_ACTION: str = "SHOOT OR MOVE (S-M)?"
PROMPT_MOVE_TARGET: str = "WHERE TO?"
PROMPT_SHOOT_PATH_LEN: str = "NO. OF ROOMS(1-5)?"
PROMPT_SHOOT_PATH_ROOM: str = "ROOM #?"

# Command tokens (one per CommandVerb). Yob's single-letter answers.
COMMAND_TOKEN_SHOOT: str = "S"
COMMAND_TOKEN_MOVE: str = "M"
COMMAND_TOKEN_YES: str = "Y"
COMMAND_TOKEN_NO: str = "N"


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


def render_off_graph_move() -> tuple[str, ...]:
    """Translate a rejected (off-graph) move to its Yob `NOT POSSIBLE -` line.

    Emitted on a `MoveAttempted(accepted=False)` event in the yob cave (the
    player typed a non-adjacent room at the WHERE TO? prompt). Yob prints this
    then re-prompts WHERE TO? without consuming the turn (G6)."""
    return (OFF_GRAPH_MOVE,)


# ---------------------------------------------------------------------------
# R1-S08 — Instructions block + RAMDOM typo + HUNT THE WUMPUS banner.
#
# Verbatim from the Yob BASIC source
# (`wumpus/experiments/g_wild_baseline/wumpus.gwbasic.bas`, lines 1010-1400 +
# line 375). Each BASIC `PRINT` becomes one tuple entry; bare `PRINT` (no
# argument) becomes an empty string. The `RAMDOM` typo at BASIC line 1300
# is preserved bug-for-bug per D11 — it is the canary signaling the
# instructions block has not been "corrected" by a future PR.
#
# DO NOT edit without consulting `wumpus/docs/wumpus_python_goals.md`
# § Goal 1 "Mistakes — verbatim" (RAMDOM call-out). Full byte-for-byte
# regression against a PC-BASIC transcript lands at R1-S10.
# ---------------------------------------------------------------------------

INSTRUCTIONS_PROMPT: str = "INSTRUCTIONS (Y-N)?"

HUNT_THE_WUMPUS_BANNER: str = "HUNT THE WUMPUS"

# The instructions block — one tuple entry per Yob BASIC PRINT statement.
# Bare `PRINT` statements (no argument) appear as empty strings, preserving
# Yob's intended line breaks. Sourced verbatim from BASIC source lines
# 1010-1400 (the GOSUB 1000 instructions routine).
_INSTRUCTIONS_LINES: tuple[str, ...] = (
    "WELCOME TO 'HUNT THE WUMPUS'",
    "  THE WUMPUS LIVES IN A CAVE OF 20 ROOMS. EACH ROOM",
    "HAS 3 TUNNELS LEADING TO OTHER ROOMS. (LOOK AT A",
    "DODECAHEDRON TO SEE HOW THIS WORKS-IF YOU DON'T KNOW",
    "WHAT A DODECAHEDRON IS, ASK SOMEONE)",
    "",
    "     HAZARDS:",
    " BOTTOMLESS PITS - TWO ROOMS HAVE BOTTOMLESS PITS IN THEM",
    "     IF YOU GO THERE, YOU FALL INTO THE PIT (& LOSE!)",
    " SUPER BATS - TWO OTHER ROOMS HAVE SUPER BATS. IF YOU",
    "     GO THERE, A BAT GRABS YOU AND TAKES YOU TO SOME OTHER",
    "     ROOM AT RANDOM. (WHICH MIGHT BE TROUBLESOME)",
    "",
    "     WUMPUS:",
    " THE WUMPUS IS NOT BOTHERED BY THE HAZARDS (HE HAS SUCKER",
    " FEET AND IS TOO BIG FOR A BAT TO LIFT).  USUALLY",
    " HE IS ASLEEP. TWO THINGS WAKE HIM UP: YOUR ENTERING",
    " HIS ROOM OR YOUR SHOOTING AN ARROW.",
    "     IF THE WUMPUS WAKES, HE MOVES (P=.75) ONE ROOM",
    " OR STAYS STILL (P=.25). AFTER THAT, IF HE IS WHERE YOU",
    " ARE, HE EATS YOU UP (& YOU LOSE!)",
    "",
    "     YOU:",
    " EACH TURN YOU MAY MOVE OR SHOOT A CROOKED ARROW",
    "   MOVING: YOU CAN GO ONE ROOM (THRU ONE TUNNEL)",
    "   ARROWS: YOU HAVE 5 ARROWS. YOU LOSE WHEN YOU RUN OUT.",
    "   EACH ARROW CAN GO FROM 1 TO 5 ROOMS. YOU AIM BY TELLING",
    "   THE COMPUTER THE ROOM#S YOU WANT THE ARROW TO GO TO.",
    "   IF THE ARROW CAN'T GO THAT WAY (IE NO TUNNEL) IT MOVES",
    "   AT RAMDOM TO THE NEXT ROOM.",
    "     IF THE ARROW HITS THE WUMPUS, YOU WIN.",
    "     IF THE ARROW HITS YOU, YOU LOSE.",
    "",
    "    WARNINGS:",
    "     WHEN YOU ARE ONE ROOM AWAY FROM WUMPUS OR HAZARD,",
    "    THE COMPUTER SAYS:",
    " WUMPUS-  'I SMELL A WUMPUS'",
    " BAT   -  'BATS NEARBY'",
    " PIT   -  'I FEEL A DRAFT'",
    "",
)


def instructions_block() -> tuple[str, ...]:
    """Return Yob's verbatim instructions text as a tuple of lines.

    Sourced from BASIC source lines 1010-1400 (the GOSUB 1000 instructions
    routine). Each BASIC `PRINT` becomes one tuple entry; bare `PRINT`
    (line 1060, 1130, 1220, 1330, 1400) becomes an empty string.

    The `RAMDOM` typo (BASIC line 1300, in the arrow-deflection sentence)
    is preserved bug-for-bug per D11 — it is the canary signaling the
    instructions block has not been "corrected" by a future PR.

    Per SC2 + D11 the text is byte-exact to Yob's source; the full
    byte-for-byte regression against PC-BASIC transcripts lands at R1-S10.
    """
    return _INSTRUCTIONS_LINES


def render_instructions(event: InstructionsShown) -> tuple[str, ...]:
    """Translate an InstructionsShown event to its rendered lines.

    Returns the instructions block followed by an empty separator line and
    the HUNT THE WUMPUS banner — the BASIC source emits `PRINT "HUNT THE
    WUMPUS"` at line 375 immediately after the instructions routine
    returns (or, if the player answered N, immediately after the welcome
    block at line 0052-0066). The banner is part of the post-instructions
    render path; emitting it through the same surface call keeps the
    order-of-operations invariant from drifting.

    The event itself carries the lines payload (per ADR-010 the engine
    emits a structured event; the surface translates). The `lines` field
    is sourced from `instructions_block()` at emission time."""
    return tuple(event.lines) + (HUNT_THE_WUMPUS_BANNER,)


def render_instructions_prompt() -> tuple[str, ...]:
    """Render the pre-game INSTRUCTIONS (Y-N)? prompt."""
    return (INSTRUCTIONS_PROMPT,)


def render_banner_only() -> tuple[str, ...]:
    """Render the HUNT THE WUMPUS banner without the instructions block.

    Used when the player answers N at the INSTRUCTIONS prompt — Yob jumps
    past the GOSUB 1000 instructions routine (BASIC line 0040 IF I$="N"
    THEN 52) and prints just the welcome additions + the banner. R1-S08
    ships the banner-only path; the WUMPUS LOVERS welcome additions land
    later (they are not part of Yob's original 1973 source — they are
    Dave's addition per BASIC line 0052)."""
    return (HUNT_THE_WUMPUS_BANNER,)


# ---------------------------------------------------------------------------
# R4-S03 — YobSurface: the Surface-Protocol object form.
#
# Per ADR-001 (hybrid paradigm) the surface strings are module-level constants
# + free functions (above); `YobSurface` is the thin OOP shell that satisfies
# the Tier-A5 `Surface` Protocol by delegating to those module-level tables.
# It carries NO mutable state, holds NO engine reference, and never touches an
# RNG (SC9). The Mystery (R4-S05) and French (R4-S06) surfaces will be sibling
# classes with the same shape but different backing tables.
#
# The class duck-types `wumpus.types.Surface` (composition over inheritance —
# it does NOT subclass the Protocol).
# ---------------------------------------------------------------------------

_SENSE_LINE_BY_KIND: dict[str, str] = {
    "WUMPUS_SMELL": SENSE_WUMPUS_SMELL,
    "PIT_DRAFT": SENSE_PIT_DRAFT,
    "BAT_NEARBY": SENSE_BAT_NEARBY,
}

_HAZARD_NAME_BY_KIND: dict[str, str] = {
    "WUMPUS": HAZARD_BUMP_WUMPUS,
    "PIT": HAZARD_PIT,
    "BAT": HAZARD_BAT,
}

_PROMPT_TEXT_BY_KIND: dict[str, str] = {
    "action": PROMPT_ACTION,
    "move_target": PROMPT_MOVE_TARGET,
    "shoot_path_len": PROMPT_SHOOT_PATH_LEN,
    "shoot_path_room": PROMPT_SHOOT_PATH_ROOM,
    "same_setup": PROMPT_SAME_SETUP,
    "instructions": INSTRUCTIONS_PROMPT,
}

_TOKEN_BY_VERB: dict[str, str] = {
    "SHOOT": COMMAND_TOKEN_SHOOT,
    "MOVE": COMMAND_TOKEN_MOVE,
    "YES": COMMAND_TOKEN_YES,
    "NO": COMMAND_TOKEN_NO,
}

# Inverse map, derived once from _TOKEN_BY_VERB so the round-trip is
# guaranteed-consistent (no hand-maintained second table to drift). Tokens are
# matched case-insensitively on parse (the engine accepts "y"/"Y"); the
# verbatim token table itself is upper-case to match Yob's prompts.
_VERB_BY_TOKEN: dict[str, str] = {
    token.upper(): verb for verb, token in _TOKEN_BY_VERB.items()
}


class YobSurface:
    """Yob 1973 surface — the Surface-Protocol object form (R4-S03).

    Pure translation layer: structured engine tags → verbatim Yob strings, and
    the inverse for command tokens. No engine state, no RNG (SC9). Delegates to
    this module's verbatim constant tables; the class is a thin Protocol shell.
    """

    surface_id: str = "yob"

    def room_label(self, room_id: int) -> str:
        """Yob renders rooms as their decimal number (Mystery scrambles this)."""
        return str(room_id)

    def render_location(
        self, room_id: int, adjacents: tuple[int, ...]
    ) -> tuple[str, ...]:
        """Render a LocationReported into Yob's two per-turn lines.

        Produces (verbatim from `wumpus.gwbasic.bas` lines 2130-2140):
            "YOU ARE IN ROOM  <n>"
            "TUNNELS LEAD TO  <a>  <b>  <c>"

        The double space before each number reproduces GW-BASIC's `PRINT`
        numeric format (a positive number is emitted with a leading sign-space):
        the literal prefix carries one trailing space, then each room label is
        prefixed with the sign-space. Room labels come from `room_label`, so a
        Mystery surface that scrambles room ids scrambles these lines too. No
        trailing punctuation/space follows the last room (goals.md § Goal 1).
        """
        room_line = LOCATION_ROOM_PREFIX + " " + self.room_label(room_id)
        tunnels = " ".join(" " + self.room_label(room) for room in adjacents)
        tunnels_line = LOCATION_TUNNELS_PREFIX + tunnels
        return (room_line, tunnels_line)

    def sense_string(self, kind: str) -> str:
        """Translate a SenseEmitted.kind to its verbatim Yob sense line."""
        line = _SENSE_LINE_BY_KIND.get(kind)
        if line is None:
            raise ValueError(
                f"YobSurface.sense_string: unknown sense kind {kind!r}. "
                f"Expected one of {tuple(_SENSE_LINE_BY_KIND)!r}."
            )
        return line

    def hazard_name(self, kind: str) -> str:
        """Translate a HazardTriggered.kind to its verbatim Yob reason line."""
        name = _HAZARD_NAME_BY_KIND.get(kind)
        if name is None:
            raise ValueError(
                f"YobSurface.hazard_name: unknown hazard kind {kind!r}. "
                f"Expected one of {tuple(_HAZARD_NAME_BY_KIND)!r}."
            )
        return name

    def command_token(self, verb: CommandVerb) -> str:
        """Translate a CommandVerb to its player-facing Yob input token."""
        token = _TOKEN_BY_VERB.get(verb)
        if token is None:
            raise ValueError(
                f"YobSurface.command_token: unknown verb {verb!r}. "
                f"Expected one of {tuple(_TOKEN_BY_VERB)!r}."
            )
        return token

    def command_parse(self, token: str) -> ParsedCommand:
        """Inverse of `command_token` — parse a player token to a ParsedCommand.

        Round-trip contract: `command_parse(command_token(v)).verb == v` for
        every CommandVerb. Case-insensitive (Yob's INPUT accepts "y" and "Y").
        """
        verb = _VERB_BY_TOKEN.get(token.strip().upper())
        if verb is None:
            raise ValueError(
                f"YobSurface.command_parse: unrecognized token {token!r}. "
                f"Expected one of {tuple(_TOKEN_BY_VERB.values())!r}."
            )
        return ParsedCommand(verb=verb)  # type: ignore[arg-type]

    def prompt_text(self, kind: str) -> str:
        """Translate a PromptKind discriminator to its verbatim Yob prompt."""
        text = _PROMPT_TEXT_BY_KIND.get(kind)
        if text is None:
            raise ValueError(
                f"YobSurface.prompt_text: unknown prompt kind {kind!r}. "
                f"Expected one of {tuple(_PROMPT_TEXT_BY_KIND)!r}."
            )
        return text

    def instructions_block(self) -> tuple[str, ...]:
        """Return Yob's verbatim instructions block (delegates to the module
        free function so the R1-S08 strings have a single home)."""
        return instructions_block()

    def terminal_strings(self) -> tuple[str, ...]:
        """Every terminal / miss / self-shot / swap-tag string the surface can
        emit. Used by the R4-S03 acceptance fidelity check (and harmless for
        the engine, which renders terminals via `render_terminal`). NOT part of
        the Surface Protocol — a convenience aggregator for the canary."""
        return (
            TERMINAL_WUMPUS_SHOT,
            TERMINAL_WUMPUS_GOT_YOU,
            TERMINAL_SELF_SHOT,
            WIN_TAG,
            LOSE_TAG,
            ARROW_MISSED,
            CROOKED_REJECTION,
            OFF_GRAPH_MOVE,
        )


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
    "CROOKED_REJECTION",
    "OFF_GRAPH_MOVE",
    "SENSE_WUMPUS_SMELL",
    "SENSE_PIT_DRAFT",
    "SENSE_BAT_NEARBY",
    "LOCATION_ROOM_PREFIX",
    "LOCATION_TUNNELS_PREFIX",
    "PROMPT_ACTION",
    "PROMPT_MOVE_TARGET",
    "PROMPT_SHOOT_PATH_LEN",
    "PROMPT_SHOOT_PATH_ROOM",
    "PROMPT_SAME_SETUP",
    "INSTRUCTIONS_PROMPT",
    "HUNT_THE_WUMPUS_BANNER",
    "COMMAND_TOKEN_SHOOT",
    "COMMAND_TOKEN_MOVE",
    "COMMAND_TOKEN_YES",
    "COMMAND_TOKEN_NO",
    "YobSurface",
    "instructions_block",
    "render_hazard",
    "render_terminal",
    "render_same_setup_prompt",
    "render_off_graph_move",
    "render_instructions",
    "render_instructions_prompt",
    "render_banner_only",
]
