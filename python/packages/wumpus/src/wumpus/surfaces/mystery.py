"""Mystery-Wumpus surface — the obfuscation-gap probe surface (R4-S05).

WHY-NEW-FILE: python/packages/wumpus/src/wumpus/surfaces/mystery.py
  CLOSEST-EXISTING: python/packages/wumpus/src/wumpus/surfaces/yob.py
  EXTENSION-COST: YobSurface's tables are the *verbatim Yob 1973* strings — the
    one place SC8 permits them; folding a second, scrambled symbol set into the
    same module would couple the canary (yob unit tests pin those exact bytes)
    to the Mystery tables and force the surface-leak audit to re-reason about
    which literals are "the" surface.
  PARALLEL-RATIONALE: the DESIGN A5 component table already adjudicated the
    split ("Future variant surfaces ... will be a sibling module under
    wumpus.surfaces with the same public-function signatures" — yob.py module
    docstring); each surface is an independent translation table with the same
    Protocol shape but a divergent (and deliberately incompatible) string set.

The point of this surface (journey J2 / SC9): run the SAME seed under YobSurface
and MysterySurface with translation-equivalent player inputs and the engine's
internal trajectory is IDENTICAL — only the bytes the player reads differ. That
equality is the validity proof of the obfuscation-gap measurement. To hold it,
this surface:

  - Has a FIXED, arbitrary, deterministic symbol map (no RNG, no engine-state
    reads — SC9). Construction takes no arguments and holds no mutable state.
  - Is a bijection wherever invertibility is needed: `room_label` /
    `room_id` round-trip for every room id, and `command_token` /
    `command_parse` round-trip for every CommandVerb. The engine maps a
    player-typed mystery label back to the internal room id, so a Mystery run
    and a Yob run driven by the same internal *intent* visit the same rooms.
  - Duck-types `wumpus.types.Surface` (composition over inheritance, ADR-001);
    it does NOT subclass the Protocol and shares no code path with YobSurface.

Bijection design — room labels via a digit-substitution cipher
--------------------------------------------------------------
Room ids are arbitrary positive ints (Yob: 1..20; VariantConfig may widen the
cave). Rather than a fixed table bounded to 20 rooms, the room label is the
decimal id with each digit run through a FIXED bijective digit permutation
(`_DIGIT_CIPHER`, a permutation of "0123456789"), wrapped in a mystery affix
(``"glyph-<scrambled-digits>"``). The cipher is its own inverse table
(`_DIGIT_DECIPHER`), so `room_id(room_label(n)) == n` for every n, with no
range assumption and no RNG. Leading-zero ambiguity cannot arise: the decimal
of a positive int never starts with 0, and digit substitution is positional so
the first plaintext digit (1-9) maps to a fixed non-collision cipher digit;
the decipher reads the affix off and inverts each digit.

The senses / hazards / prompts / command tokens are a fixed arbitrary
relabelling — alien glyph-words with no overlap with the Yob byte set (so the
"rendered output genuinely differs" claim is trivially true and the SC8 audit
never confuses a Mystery literal for a Yob one). Command tokens are single
mystery letters distinct across verbs (so `command_parse` is unambiguous).
"""

from __future__ import annotations

from wumpus.types import CommandVerb, ParsedCommand

# ---------------------------------------------------------------------------
# Room-label bijection — a fixed digit-substitution cipher + mystery affix.
# ---------------------------------------------------------------------------
#
# `_DIGIT_CIPHER` is an arbitrary fixed permutation of the decimal digits; it
# is RNG-free and deterministic. `_DIGIT_DECIPHER` is its inverse, derived once
# so the two can never drift. The mystery affix (`_ROOM_PREFIX`) makes a room
# label visibly alien while keeping the scrambled digits parseable on the way
# back. The label is a total bijection on the positive integers.

_ROOM_PREFIX: str = "glyph-"

# Arbitrary fixed digit permutation (a bijection on "0123456789").
_DIGIT_CIPHER: dict[str, str] = {
    "0": "7",
    "1": "3",
    "2": "9",
    "3": "0",
    "4": "5",
    "5": "8",
    "6": "1",
    "7": "4",
    "8": "2",
    "9": "6",
}
# Inverse, derived once (guaranteed-consistent — no hand-maintained 2nd table).
_DIGIT_DECIPHER: dict[str, str] = {
    ciphered: plain for plain, ciphered in _DIGIT_CIPHER.items()
}


# ---------------------------------------------------------------------------
# Sense / hazard / prompt / arrow-outcome relabelling — alien glyph-words.
#
# Deliberately share NO bytes with the verbatim Yob strings: the obfuscation is
# total, and the SC8 surface-leak audit never confuses a Mystery literal for a
# Yob one. These are arbitrary but fixed (deterministic, RNG-free).
# ---------------------------------------------------------------------------

_SENSE_BY_KIND: dict[str, str] = {
    "WUMPUS_SMELL": "ZZ-GLORP TWITCHES",
    "PIT_DRAFT": "VOID-WIND RISES",
    "BAT_NEARBY": "FLUTTERLINGS STIR",
}

_HAZARD_BY_KIND: dict[str, str] = {
    "WUMPUS": "GLORP-MAW CLOSES ON YOU",
    "PIT": "THE VOID SWALLOWS YOU",
    "BAT": "FLUTTERLINGS WHISK YOU OFF",
}

_ARROW_OUTCOME_BY_KIND: dict[str, str] = {
    "MISSED": "BOLT SAILS WIDE",
    "SELF_SHOT": "YOUR OWN BOLT FINDS YOU",
}

# Terminal reason lines (one per GameEnded.outcome). out_of_arrows carries no
# extra reason — the prior bolt narration covered it (mirrors Yob's structure).
_TERMINAL_REASON_BY_OUTCOME: dict[str, str] = {
    "wumpus_shot": "YOUR BOLT PIERCES THE GLORP",
    "eaten_after_bump": "THE GLORP DEVOURS YOU",
    # "fell_in_pit" deliberately omitted to mirror Yob's structure — the pit
    # line is rendered ONCE via HazardTriggered(PIT) -> hazard_name (the Mystery
    # equivalent is "THE VOID SWALLOWS YOU"); a terminal-reason entry here
    # would double-render it. See yob.py for the matching note.
    "out_of_arrows": "",
}

# Win/lose swap tags — the Mystery analog of Yob's D11 swap. Deliberately
# distinct mystery prose; the swap is chosen by message_kind, not outcome.
_WIN_TAG: str = "THE WEAVE HUMS WITH YOUR VICTORY."
_LOSE_TAG: str = "THE WEAVE GOES DARK. YOU FALL."

# Post-instructions banner (Yob: "HUNT THE WUMPUS").
_BANNER: str = "STALK THE GLORP"

# Off-graph move line (Yob: "NOT POSSIBLE -").
_OFF_GRAPH_MOVE: str = "NO WEAVE LEADS THERE -"

_PROMPT_TEXT_BY_KIND: dict[str, str] = {
    "action": "FLEE OR LOOSE (F-L)?",
    "move_target": "WHITHER?",
    "shoot_path_len": "BOLT REACH (1-5)?",
    "shoot_path_room": "GLYPH #?",
    "same_setup": "SAME WEAVE (J-K)?",
    "instructions": "GLYPHS (J-K)?",
}

# Per-turn location render affixes (LocationReported -> "where am I" lines).
_LOCATION_ROOM_PREFIX: str = "YOU STAND AT GLYPH "
_LOCATION_TUNNELS_PREFIX: str = "WEAVES RUN TO "

# Mystery command tokens (one per CommandVerb). Distinct mystery letters so
# `command_parse` is unambiguous; deliberately NOT Yob's S/M/Y/N.
_TOKEN_BY_VERB: dict[str, str] = {
    "SHOOT": "L",  # "loose"
    "MOVE": "F",  # "flee"
    "YES": "J",
    "NO": "K",
}
# Inverse, derived once. Case-insensitive on parse (matches Yob's INPUT).
_VERB_BY_TOKEN: dict[str, str] = {
    token.upper(): verb for verb, token in _TOKEN_BY_VERB.items()
}

# Mystery instructions block — an alien retelling, byte-disjoint from Yob's.
# One tuple entry per "line"; the content is arbitrary but fixed.
_INSTRUCTIONS_LINES: tuple[str, ...] = (
    "GREETINGS, GLYPH-WALKER.",
    "THE GLORP DWELLS IN A WEAVE OF CHAMBERS.",
    "EACH CHAMBER OPENS ON THREE WEAVES.",
    "",
    "PERILS:",
    " VOIDS SWALLOW THE UNWARY.",
    " FLUTTERLINGS WHISK YOU ELSEWHERE.",
    "",
    "THE GLORP:",
    " IT SLUMBERS UNTIL DISTURBED, THEN IT MAY DRIFT ONE WEAVE.",
    " IF IT FINDS YOU, IT FEASTS.",
    "",
    "YOU:",
    " EACH TURN, FLEE A WEAVE OR LOOSE A CROOKED BOLT.",
    " A BOLT MAY CROSS 1 TO 5 CHAMBERS BY GLYPH.",
    "",
)


class MysterySurface:
    """Mystery-Wumpus surface — the obfuscation-gap probe surface (R4-S05).

    A fixed, arbitrary, deterministic relabelling of every surface-form string
    the engine emits, plus an invertible room-label / command-token bijection.
    No engine state, no RNG (SC9). `surface_id="mystery"`. Duck-types
    `wumpus.types.Surface` without inheriting it (composition, ADR-001).
    """

    surface_id: str = "mystery"

    def room_label(self, room_id: int) -> str:
        """Scramble a room id into a mystery glyph label via the fixed digit
        cipher + affix. A total bijection on the positive integers; the inverse
        is `room_id`."""
        scrambled = "".join(_DIGIT_CIPHER[digit] for digit in str(room_id))
        return _ROOM_PREFIX + scrambled

    def room_id(self, label: str) -> int | None:
        """Inverse of `room_label`: strip the mystery affix and decipher each
        digit back to the internal room id. Returns None on a label that is
        not a valid mystery room reference, so the engine re-prompts without
        consuming the turn (G6) — exactly as Yob's `room_id` returns None on a
        non-integer token. This is the routing hook that lets a player type a
        mystery label and the engine recover the internal room id."""
        token = label.strip()
        if not token.startswith(_ROOM_PREFIX):
            return None
        scrambled = token[len(_ROOM_PREFIX) :]
        if not scrambled or any(digit not in _DIGIT_DECIPHER for digit in scrambled):
            return None
        plain = "".join(_DIGIT_DECIPHER[digit] for digit in scrambled)
        try:
            return int(plain)
        except ValueError:
            return None

    def render_location(
        self, room_id: int, adjacents: tuple[int, ...]
    ) -> tuple[str, ...]:
        """Mystery per-turn location lines for a LocationReported event. Pure
        translation of room ids -> mystery glyph labels; no engine state, no
        RNG (SC9). Mirrors YobSurface.render_location's two-line shape but with
        mystery affixes and scrambled labels."""
        room_line = _LOCATION_ROOM_PREFIX + self.room_label(room_id)
        tunnels = " ".join(self.room_label(room) for room in adjacents)
        tunnels_line = _LOCATION_TUNNELS_PREFIX + tunnels
        return (room_line, tunnels_line)

    def sense_string(self, kind: str) -> str:
        """Translate a SenseEmitted.kind to its mystery sense glyph-line."""
        line = _SENSE_BY_KIND.get(kind)
        if line is None:
            raise ValueError(
                f"MysterySurface.sense_string: unknown sense kind {kind!r}. "
                f"Expected one of {tuple(_SENSE_BY_KIND)!r}."
            )
        return line

    def hazard_name(self, kind: str) -> str:
        """Translate a HazardTriggered.kind to its mystery reason glyph-line."""
        name = _HAZARD_BY_KIND.get(kind)
        if name is None:
            raise ValueError(
                f"MysterySurface.hazard_name: unknown hazard kind {kind!r}. "
                f"Expected one of {tuple(_HAZARD_BY_KIND)!r}."
            )
        return name

    def arrow_outcome_string(self, kind: str) -> str:
        """Translate a non-terminal arrow-walk outcome to its mystery line."""
        line = _ARROW_OUTCOME_BY_KIND.get(kind)
        if line is None:
            raise ValueError(
                f"MysterySurface.arrow_outcome_string: unknown arrow outcome "
                f"{kind!r}. Expected one of {tuple(_ARROW_OUTCOME_BY_KIND)!r}."
            )
        return line

    def command_token(self, verb: CommandVerb) -> str:
        """Translate a CommandVerb to its player-facing mystery input token."""
        token = _TOKEN_BY_VERB.get(verb)
        if token is None:
            raise ValueError(
                f"MysterySurface.command_token: unknown verb {verb!r}. "
                f"Expected one of {tuple(_TOKEN_BY_VERB)!r}."
            )
        return token

    def command_parse(self, token: str) -> ParsedCommand:
        """Inverse of `command_token` — parse a player token to a ParsedCommand.

        Round-trip contract: `command_parse(command_token(v)).verb == v` for
        every CommandVerb. Case-insensitive (matches Yob's INPUT semantics).
        Raises on an unrecognized token; the engine's routing layer catches the
        no-match case and re-prompts (G6) — it never passes an unknown token in.
        """
        verb = _VERB_BY_TOKEN.get(token.strip().upper())
        if verb is None:
            raise ValueError(
                f"MysterySurface.command_parse: unrecognized token {token!r}. "
                f"Expected one of {tuple(_TOKEN_BY_VERB.values())!r}."
            )
        return ParsedCommand(verb=verb)  # type: ignore[arg-type]

    def prompt_text(self, kind: str) -> str:
        """Translate a PromptKind discriminator to its mystery prompt glyph."""
        text = _PROMPT_TEXT_BY_KIND.get(kind)
        if text is None:
            raise ValueError(
                f"MysterySurface.prompt_text: unknown prompt kind {kind!r}. "
                f"Expected one of {tuple(_PROMPT_TEXT_BY_KIND)!r}."
            )
        return text

    def instructions_block(self) -> tuple[str, ...]:
        """Return the mystery instructions block (alien retelling, byte-disjoint
        from Yob's verbatim block)."""
        return _INSTRUCTIONS_LINES

    def banner(self) -> str:
        """Return the mystery post-instructions banner."""
        return _BANNER

    def terminal_lines(self, outcome: str, message_kind: str) -> tuple[str, ...]:
        """Render a GameEnded(outcome, message_kind) to the mystery terminal
        lines: the outcome-specific reason (if any) + the win/lose swap tag.
        Mirrors YobSurface.terminal_lines' shape (reason chosen by outcome, tag
        by message_kind) with mystery prose."""
        reason = _TERMINAL_REASON_BY_OUTCOME.get(outcome, "")
        tag = _WIN_TAG if message_kind == "win" else _LOSE_TAG
        if reason:
            return (reason, tag)
        return (tag,)

    def off_graph_move_line(self) -> str:
        """Return the mystery off-graph move line."""
        return _OFF_GRAPH_MOVE


__all__ = ["MysterySurface"]
