"""French-Wumpus surface — the second, non-Mystery variant surface (R4-S06).

WHY-NEW-FILE: python/packages/wumpus/src/wumpus/surfaces/french.py
  CLOSEST-EXISTING: python/packages/wumpus/src/wumpus/surfaces/mystery.py
  EXTENSION-COST: MysterySurface's tables are an arbitrary *scrambled* glyph
    set whose whole purpose is the obfuscation-gap probe (the SC8 audit + the
    Mystery property pin those exact alien bytes). Folding a real-language
    translation into the same module would couple a localization table to the
    obfuscation probe and force every Mystery test to re-reason about which
    literals are "the Mystery surface" vs. "the French translation".
  PARALLEL-RATIONALE: the yob.py module docstring + DESIGN A5 component table
    already adjudicated the split — "Future variant surfaces (Mystery-Wumpus at
    R4-S05, French at R4-S06) will follow the same shape: a sibling module under
    wumpus.surfaces with the same public-function signatures". Each surface is
    an independent translation table with the same Protocol shape but a divergent
    (and deliberately byte-disjoint) string set; French is a real-language
    localization, Mystery is a scrambled obfuscation, Yob is the verbatim 1973
    catalogue. Three independent surfaces, one Protocol.

The point of THIS surface (Story R4-S06 / journey J2): prove the R4-S05 seam
generalization was NOT Mystery-shaped. A second, non-Mystery surface drops in
with NO engine changes, and a paired Yob-vs-French run from the same seed with
translation-equivalent inputs produces an IDENTICAL internal trajectory (equal
`internal_state_hash` + `rng_cursor` every turn). Only the bytes the player
reads differ. To hold that equality this surface, like MysterySurface:

  - Is stateless, RNG-free, and reads no engine state (SC9). Construction takes
    no arguments and holds no mutable state.
  - Is a bijection wherever invertibility is needed: `room_label` / `room_id`
    round-trip for every room id, and `command_token` / `command_parse`
    round-trip for every CommandVerb.
  - Duck-types `wumpus.types.Surface` (composition over inheritance, ADR-001);
    it does NOT subclass the Protocol and shares no code path with YobSurface
    or MysterySurface.

Room labels — French uses Arabic numerals
------------------------------------------
French (like English) writes room numbers in Arabic numerals, so the natural
French room label is the decimal id itself — the SAME shape as YobSurface's
`room_label`/`room_id` (decimal int parsing). The brief explicitly permits this:
"decimal labels are acceptable — French uses Arabic numerals". The bijection is
plain decimal: `room_id(room_label(n)) == n` for every positive int n, RNG-free,
no range assumption. This is deliberate: a paired Yob/French run that types the
SAME decimal room labels still inverts (via the engine's surface-routed
`room_id`) to the SAME internal room id, so the trajectories stay identical.
(The Mystery surface scrambles its labels; French does not need to — the
obfuscation it provides is the *prose* and the *command tokens*, which is a
real translation, not a cipher.)

Command tokens — French verbs
------------------------------
The four CommandVerbs map to French single-letter answers, distinct across
verbs so `command_parse` is unambiguous, and deliberately NOT Yob's S/M/Y/N:

  - SHOOT -> "T"  (tirer — to shoot)
  - MOVE  -> "D"  (déplacer — to move)
  - YES   -> "O"  (oui)
  - NO    -> "N"  (non)

NOTE: French NO is "N" — the SAME byte as Yob's NO token. That overlap is
harmless: tokens only need to be distinct *within* a surface (so `command_parse`
is unambiguous), and they are (T/D/O/N are four distinct letters). Cross-surface
token overlap does not affect the trajectory-equality proof — each run parses
its OWN surface's tokens. (The rendered *prose* is what must be byte-disjoint
from Yob, and it is — see below.)

The senses / hazards / prompts / terminals / instructions / arrow outcomes are
a real French translation, byte-disjoint from the verbatim Yob catalogue (so the
SC8 Yob-prose audit never confuses a French literal for a Yob one) and distinct
from Mystery's alien glyphs. Fixed and arbitrary-but-deterministic (RNG-free).
"""

from __future__ import annotations

from wumpus.types import CommandVerb, ParsedCommand

# ---------------------------------------------------------------------------
# Sense / hazard / prompt / arrow-outcome / terminal relabelling — French prose.
#
# A real French translation of every surface-form string. Deliberately share NO
# bytes with the verbatim Yob strings (the obfuscation is a genuine translation,
# and the SC8 surface-leak audit — harvested from wumpus.surfaces.yob — never
# confuses a French literal for a Yob one). Fixed + deterministic (RNG-free).
# ---------------------------------------------------------------------------

_SENSE_BY_KIND: dict[str, str] = {
    "WUMPUS_SMELL": "JE SENS UN WUMPUS !",
    "PIT_DRAFT": "JE SENS UN COURANT D'AIR",
    "BAT_NEARBY": "DES CHAUVES-SOURIS A PROXIMITE !",
}

_HAZARD_BY_KIND: dict[str, str] = {
    "WUMPUS": "...OUPS ! VOUS AVEZ HEURTE UN WUMPUS !",
    "PIT": "AAAAÏÏÏE . . . TOMBE DANS LA FOSSE",
    "BAT": "ZAP--ENLEVEMENT PAR CHAUVE-SOURIS ! DIRECTION L'AILLEURS !",
}

_ARROW_OUTCOME_BY_KIND: dict[str, str] = {
    "MISSED": "MANQUE",
    "SELF_SHOT": "AÏE ! LA FLECHE VOUS A TOUCHE !",
}

# Terminal reason lines (one per GameEnded.outcome). out_of_arrows carries no
# extra reason — the prior arrow narration covered it (mirrors Yob's structure).
_TERMINAL_REASON_BY_OUTCOME: dict[str, str] = {
    "wumpus_shot": "AH HA ! VOUS AVEZ EU LE WUMPUS !",
    "eaten_after_bump": "TSK TSK TSK- LE WUMPUS VOUS A EU !",
    "fell_in_pit": "AAAAÏÏÏE . . . TOMBE DANS LA FOSSE",
    "out_of_arrows": "",
}

# Win/lose swap tags — the French analog of Yob's D11 swap (the win line is
# the taunting "the Wumpus will get you next time", the lose line is the laugh).
# The swap is chosen by message_kind, not outcome (mirrors Yob).
_WIN_TAG: str = "HE HE HE - LE WUMPUS VOUS AURA LA PROCHAINE FOIS !!"
_LOSE_TAG: str = "HA HA HA - VOUS AVEZ PERDU !"

# Post-instructions banner (Yob: "HUNT THE WUMPUS").
_BANNER: str = "CHASSEZ LE WUMPUS"

# Off-graph move line (Yob: "NOT POSSIBLE -").
_OFF_GRAPH_MOVE: str = "IMPOSSIBLE -"

_PROMPT_TEXT_BY_KIND: dict[str, str] = {
    "action": "TIRER OU DEPLACER (T-D) ?",
    "move_target": "OU ALLER ?",
    "shoot_path_len": "NB. DE SALLES (1-5) ?",
    "shoot_path_room": "SALLE N° ?",
    "same_setup": "MEME CONFIGURATION (O-N) ?",
    "instructions": "INSTRUCTIONS (O-N) ?",
}

# Per-turn location render affixes (LocationReported -> "where am I" lines).
# French uses decimal room numbers (Arabic numerals), so — like Yob — the label
# is the bare decimal. The double space before each number mirrors Yob's
# GW-BASIC numeric spacing so the structure reads identically (only the French
# prose differs).
_LOCATION_ROOM_PREFIX: str = "VOUS ETES DANS LA SALLE "
_LOCATION_TUNNELS_PREFIX: str = "DES TUNNELS MENENT VERS "

# French command tokens (one per CommandVerb). Distinct French letters so
# `command_parse` is unambiguous; deliberately a French mnemonic set
# (T=tirer, D=déplacer, O=oui, N=non).
_TOKEN_BY_VERB: dict[str, str] = {
    "SHOOT": "T",  # tirer
    "MOVE": "D",  # déplacer
    "YES": "O",  # oui
    "NO": "N",  # non
}
# Inverse, derived once (guaranteed-consistent — no hand-maintained 2nd table).
# Case-insensitive on parse (matches Yob's INPUT semantics).
_VERB_BY_TOKEN: dict[str, str] = {
    token.upper(): verb for verb, token in _TOKEN_BY_VERB.items()
}

# French instructions block — a real translation, byte-disjoint from Yob's.
# One tuple entry per "line"; content is a faithful French retelling. Bare
# entries ("") preserve the paragraph breaks of Yob's block.
_INSTRUCTIONS_LINES: tuple[str, ...] = (
    "BIENVENUE A 'CHASSEZ LE WUMPUS'",
    "  LE WUMPUS VIT DANS UNE GROTTE DE 20 SALLES. CHAQUE",
    "SALLE A 3 TUNNELS MENANT VERS D'AUTRES SALLES.",
    "",
    "     DANGERS :",
    " FOSSES SANS FOND - DEUX SALLES ABRITENT DES FOSSES SANS FOND.",
    "     SI VOUS Y ALLEZ, VOUS TOMBEZ DEDANS (& PERDEZ !)",
    " CHAUVES-SOURIS GEANTES - DEUX AUTRES SALLES EN ABRITENT. SI",
    "     VOUS Y ALLEZ, UNE CHAUVE-SOURIS VOUS EMPORTE AILLEURS",
    "     AU HASARD. (CE QUI PEUT ETRE GENANT)",
    "",
    "     WUMPUS :",
    " LE WUMPUS N'EST PAS GENE PAR LES DANGERS. D'HABITUDE",
    " IL DORT. DEUX CHOSES LE REVEILLENT : VOTRE ENTREE DANS",
    " SA SALLE OU VOTRE TIR DE FLECHE.",
    "     S'IL SE REVEILLE, IL BOUGE (P=.75) D'UNE SALLE",
    " OU RESTE IMMOBILE (P=.25). ENSUITE, S'IL EST LA OU VOUS",
    " ETES, IL VOUS DEVORE (& VOUS PERDEZ !)",
    "",
    "     VOUS :",
    " A CHAQUE TOUR VOUS POUVEZ DEPLACER OU TIRER UNE FLECHE TORDUE",
    "   DEPLACEMENT : VOUS POUVEZ ALLER DANS UNE SALLE (UN TUNNEL)",
    "   FLECHES : VOUS AVEZ 5 FLECHES. VOUS PERDEZ QUAND IL N'EN RESTE PLUS.",
    "   CHAQUE FLECHE VA DE 1 A 5 SALLES. VOUS VISEZ EN INDIQUANT",
    "   A L'ORDINATEUR LES N° DE SALLES OU LA FLECHE DOIT ALLER.",
    "     SI LA FLECHE TOUCHE LE WUMPUS, VOUS GAGNEZ.",
    "     SI LA FLECHE VOUS TOUCHE, VOUS PERDEZ.",
    "",
    "    AVERTISSEMENTS :",
    "     QUAND VOUS ETES A UNE SALLE D'UN WUMPUS OU D'UN DANGER,",
    "    L'ORDINATEUR DIT :",
    " WUMPUS-  'JE SENS UN WUMPUS'",
    " CHAUVE-SOURIS - 'DES CHAUVES-SOURIS A PROXIMITE'",
    " FOSSE - 'JE SENS UN COURANT D'AIR'",
    "",
)


class FrenchSurface:
    """French-Wumpus surface — the second, non-Mystery variant (R4-S06).

    A real French translation of every surface-form string the engine emits,
    plus the command-token bijection. Room labels are decimal (French uses
    Arabic numerals, like Yob) so `room_id`/`room_label` round-trip is plain
    decimal parsing. No engine state, no RNG (SC9). `surface_id="french"`.
    Duck-types `wumpus.types.Surface` without inheriting it (composition,
    ADR-001); shares no code path with YobSurface or MysterySurface.
    """

    surface_id: str = "french"

    def room_label(self, room_id: int) -> str:
        """French renders rooms as their decimal number (Arabic numerals).

        The same shape as YobSurface: the label IS the decimal id, so a paired
        Yob/French run that types the same room labels inverts to the same
        internal room id. A total bijection on the positive integers; the
        inverse is `room_id`."""
        return str(room_id)

    def room_id(self, label: str) -> int | None:
        """Inverse of `room_label`: parse a player-typed decimal room label.

        Plain `int` parsing (French room labels are Arabic numerals). Returns
        None on a non-integer token so the engine re-prompts without consuming
        the turn (G6) — exactly as Yob's `room_id` does. This is the routing
        hook that lets a French player type a room number and the engine
        recover the internal room id."""
        try:
            return int(label.strip())
        except (ValueError, AttributeError):
            return None

    def render_location(
        self, room_id: int, adjacents: tuple[int, ...]
    ) -> tuple[str, ...]:
        """French per-turn location lines for a LocationReported event. Pure
        translation of room ids -> French prose + decimal labels; no engine
        state, no RNG (SC9). Mirrors YobSurface.render_location's two-line shape
        (and its GW-BASIC double-space numeric format) with French prefixes."""
        room_line = _LOCATION_ROOM_PREFIX + " " + self.room_label(room_id)
        tunnels = " ".join(" " + self.room_label(room) for room in adjacents)
        tunnels_line = _LOCATION_TUNNELS_PREFIX + tunnels
        return (room_line, tunnels_line)

    def sense_string(self, kind: str) -> str:
        """Translate a SenseEmitted.kind to its French sense line."""
        line = _SENSE_BY_KIND.get(kind)
        if line is None:
            raise ValueError(
                f"FrenchSurface.sense_string: unknown sense kind {kind!r}. "
                f"Expected one of {tuple(_SENSE_BY_KIND)!r}."
            )
        return line

    def hazard_name(self, kind: str) -> str:
        """Translate a HazardTriggered.kind to its French reason line."""
        name = _HAZARD_BY_KIND.get(kind)
        if name is None:
            raise ValueError(
                f"FrenchSurface.hazard_name: unknown hazard kind {kind!r}. "
                f"Expected one of {tuple(_HAZARD_BY_KIND)!r}."
            )
        return name

    def arrow_outcome_string(self, kind: str) -> str:
        """Translate a non-terminal arrow-walk outcome to its French line."""
        line = _ARROW_OUTCOME_BY_KIND.get(kind)
        if line is None:
            raise ValueError(
                f"FrenchSurface.arrow_outcome_string: unknown arrow outcome "
                f"{kind!r}. Expected one of {tuple(_ARROW_OUTCOME_BY_KIND)!r}."
            )
        return line

    def command_token(self, verb: CommandVerb) -> str:
        """Translate a CommandVerb to its player-facing French input token."""
        token = _TOKEN_BY_VERB.get(verb)
        if token is None:
            raise ValueError(
                f"FrenchSurface.command_token: unknown verb {verb!r}. "
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
                f"FrenchSurface.command_parse: unrecognized token {token!r}. "
                f"Expected one of {tuple(_TOKEN_BY_VERB.values())!r}."
            )
        return ParsedCommand(verb=verb)  # type: ignore[arg-type]

    def prompt_text(self, kind: str) -> str:
        """Translate a PromptKind discriminator to its French prompt text."""
        text = _PROMPT_TEXT_BY_KIND.get(kind)
        if text is None:
            raise ValueError(
                f"FrenchSurface.prompt_text: unknown prompt kind {kind!r}. "
                f"Expected one of {tuple(_PROMPT_TEXT_BY_KIND)!r}."
            )
        return text

    def instructions_block(self) -> tuple[str, ...]:
        """Return the French instructions block (real translation, byte-disjoint
        from Yob's verbatim block)."""
        return _INSTRUCTIONS_LINES

    def banner(self) -> str:
        """Return the French post-instructions banner."""
        return _BANNER

    def terminal_lines(self, outcome: str, message_kind: str) -> tuple[str, ...]:
        """Render a GameEnded(outcome, message_kind) to the French terminal
        lines: the outcome-specific reason (if any) + the win/lose swap tag.
        Mirrors YobSurface.terminal_lines' shape (reason chosen by outcome, tag
        by message_kind — D11 swap) with French prose."""
        reason = _TERMINAL_REASON_BY_OUTCOME.get(outcome, "")
        tag = _WIN_TAG if message_kind == "win" else _LOSE_TAG
        if reason:
            return (reason, tag)
        return (tag,)

    def off_graph_move_line(self) -> str:
        """Return the French off-graph move line."""
        return _OFF_GRAPH_MOVE


__all__ = ["FrenchSurface"]
