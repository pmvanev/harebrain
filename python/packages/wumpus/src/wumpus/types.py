"""Immutable value types for the wumpus engine.

Per ADR-001 (hybrid paradigm) the engine's internal state-of-record (`World`),
serialization snapshot (`Snapshot`), and per-turn render contract
(`Observation`) are all `@dataclass(frozen=True)`. Transitions return new
World values; Game is the OOP shell that holds the current World.

Per ADR-007 (stdlib dataclasses) no pydantic — `__post_init__` validators
defend invariants instead.

R0 ships:
    - World (Tier A1)
    - Snapshot (Tier A2)
    - Observation (Tier A3)
    - Sink Protocol (Tier A8) — re-exported via wumpus.sinks for the public API

R0 does NOT ship VariantConfig parametric handling (R4-S01), Surface Protocol
(R4-S03), or EscalationRule Protocol (R5+).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, Protocol, Sequence, runtime_checkable

if TYPE_CHECKING:
    from wumpus.events import Event

# ---------------------------------------------------------------------------
# A7 — EscalationRule (Protocol — per Decision 4 + ADR-005, R4-S02)
# ---------------------------------------------------------------------------
#
# The public extension slot for downstream L3 (partial observability) and L4
# (graph-variant) features. Rules are pure functions on values; the engine
# composes them left-to-right at its event-emission funnel (see
# `Game._emit`). R4-S02 ships the Protocol + the no-op `IdentityRule`; the
# real rule logic is owned by the first downstream L3/L4 feature
# (caveat C-R4-S02 — "punch the hole" is acceptable).
#
# `runtime_checkable` so harness-side code may `isinstance(rule, EscalationRule)`
# at composition boundaries. Per ADR-005 rules MUST NOT consume RNG; if a
# downstream rule needs entropy the engine will thread a RuleContext via an
# additive Protocol extension.


@runtime_checkable
class EscalationRule(Protocol):
    """Hook surface for downstream L3/L4 features (ADR-005 / Tier A7).

    Rules are pure functions on values; composition is left-to-right. Both
    hooks default to identity (see `IdentityRule`). Implementations duck-type
    this Protocol — they need not inherit it (composition over inheritance).
    """

    name: str  # for ledger logging in GameStarted.active_escalation_rules

    def filter_observation(self, obs: "Observation", world: "World") -> "Observation":
        """Modify what the player sees this turn. L3 implements this.
        Default: identity."""
        ...

    def filter_events(
        self, events: "Sequence[Event]", world: "World"
    ) -> "Sequence[Event]":
        """Modify the event stream emitted this turn. Allows adding/dropping/
        rewriting events. Default: identity."""
        ...


class IdentityRule:
    """No-op default escalation rule; explicitly identity on both hooks.

    Structurally satisfies `EscalationRule` without inheriting it. A
    `VariantConfig(escalation_rules=(IdentityRule(),))` run is byte-identical
    to a no-rules run (R4-S02 interim byte-fidelity gate)."""

    name = "identity"

    def filter_observation(self, obs: "Observation", world: "World") -> "Observation":
        return obs

    def filter_events(
        self, events: "Sequence[Event]", world: "World"
    ) -> "Sequence[Event]":
        return events


# ---------------------------------------------------------------------------
# A5 — VariantConfig (R4-S01)
# ---------------------------------------------------------------------------
#
# The non-surface dimensions of a Wumpus game, parameterizing the engine
# without touching engine code (goals.md § Goal 2). Construction with no
# arguments yields Yob 1973 defaults; `Game(seed=k)` is equivalent to
# `Game(seed=k, variant=VariantConfig())`.
#
# CRITICAL CONSTRAINT (goals.md § Goal 2): no variant changes the *internal*
# state schema. `wumpus_count=2` means `World.wumpus_rooms` is a length-2
# tuple, NOT a new field. The World/Snapshot/Event field SET is identical
# across all VariantConfig values.
#
# R4-S01 ships the parametric type + Yob defaults + cave-gen parameterization
# (room_count, wumpus_count, pit_count, bat_count, arrow_count) and wires
# arrow_count to the out-of-arrows terminal. `escalation_rules` is an
# empty-tuple placeholder field ONLY — the EscalationRule Protocol + hooks
# land at R4-S02. `topology` accepts only "dodecahedron" at R4-S01; other
# topologies are R5-S02 (rejected here with a clear error).


@dataclass(frozen=True)
class VariantConfig:
    """Parametric, frozen game configuration. `VariantConfig()` = Yob 1973.

    Per ADR-007 (stdlib dataclasses, no pydantic) `__post_init__` defends the
    invariants. Per ADR-001 the type is `frozen=True` so it round-trips in the
    Snapshot (SC6) and carries no hidden state.

    Fields (Yob defaults from goals.md § Goal 2):
      - room_count: number of rooms in the cave (>= 4).
      - topology: cave topology. R4-S01 supports only "dodecahedron"; other
        3-regular topologies arrive at R5-S02.
      - wumpus_count / pit_count / bat_count: hazard placement counts. They
        size the corresponding `World.*_rooms` tuples; they never add fields.
      - arrow_count: starting arrow count; wired to `World.arrows` and the
        out-of-arrows terminal (>= 1).
      - arrow_max_range: max rooms an arrow path may span (Yob: 5).
      - wumpus_move_prob: P(wumpus moves on startle) (Yob FNC: 0.75); must be
        in [0.0, 1.0]. R4-S01 stores it; the startle PMF parameterization is
        deferred (Yob baseline already moves with the FNC distribution).
      - escalation_rules: empty-tuple placeholder slot (R4-S02 lands the
        Protocol). Do NOT populate at R4-S01.
    """

    room_count: int = 20
    topology: str = "dodecahedron"
    wumpus_count: int = 1
    pit_count: int = 2
    bat_count: int = 2
    arrow_count: int = 5
    arrow_max_range: int = 5
    wumpus_move_prob: float = 0.75
    # R4-S02: the public extension slot now carries `EscalationRule`s (the
    # R4-S01 `tuple[object, ...]` placeholder is replaced by the real type).
    #
    # The AC ("VariantConfig.escalation_rules: list[EscalationRule]") names a
    # `list`, but the codebase models frozen configs with TUPLES (every other
    # VariantConfig collection field, and `World.*_rooms`, are tuples). A
    # `list` would break `VariantConfig`'s `frozen=True` hashability contract
    # (lists are unhashable) and the Snapshot round-trip (SC6). We therefore
    # keep this an immutable tuple — matching the R4-S01 style — and treat the
    # AC's "list" as "ordered collection". Order is load-bearing: rules are
    # consulted left-to-right (see `Game._emit`).
    escalation_rules: tuple[EscalationRule, ...] = ()

    def __post_init__(self) -> None:
        if self.room_count < 4:
            raise ValueError(
                f"VariantConfig.room_count must be >= 4; got {self.room_count}."
            )
        if self.topology != "dodecahedron":
            raise ValueError(
                f"VariantConfig.topology {self.topology!r} is unsupported at "
                f"R4-S01; only 'dodecahedron' is wired (other topologies are "
                f"R5-S02)."
            )
        for name in ("wumpus_count", "pit_count", "bat_count", "arrow_max_range"):
            value = getattr(self, name)
            if value < 0:
                raise ValueError(
                    f"VariantConfig.{name} must be non-negative; got {value}."
                )
        if self.arrow_count < 1:
            raise ValueError(
                f"VariantConfig.arrow_count must be >= 1; got {self.arrow_count}."
            )
        if not (0.0 <= self.wumpus_move_prob <= 1.0):
            raise ValueError(
                f"VariantConfig.wumpus_move_prob must be in [0.0, 1.0]; "
                f"got {self.wumpus_move_prob}."
            )
        # Entity placement must fit in the cave alongside the player start.
        occupants = (
            self.wumpus_count + self.pit_count + self.bat_count + 1  # +player_start
        )
        if occupants > self.room_count:
            raise ValueError(
                f"VariantConfig entity counts (wumpus={self.wumpus_count}, "
                f"pits={self.pit_count}, bats={self.bat_count}, +1 player) sum "
                f"to {occupants}, exceeding room_count={self.room_count}."
            )

    def as_dict(self) -> dict[str, object]:
        """Serialize to a plain dict for `GameStarted.variant_config` + the
        ledger schema. `escalation_rules` serializes to the ordered list of
        rule `name`s (R4-S02) so the ledger header records which rules were
        active and in what order; an empty config still serializes to `[]`."""
        return {
            "room_count": self.room_count,
            "topology": self.topology,
            "wumpus_count": self.wumpus_count,
            "pit_count": self.pit_count,
            "bat_count": self.bat_count,
            "arrow_count": self.arrow_count,
            "arrow_max_range": self.arrow_max_range,
            "wumpus_move_prob": self.wumpus_move_prob,
            "escalation_rules": [rule.name for rule in self.escalation_rules],
        }

    def rule_names(self) -> tuple[str, ...]:
        """Ordered tuple of the active rules' `name`s — the value the engine
        records in `GameStarted.active_escalation_rules` /
        `Snapshot.active_escalation_rules` (left-to-right)."""
        return tuple(rule.name for rule in self.escalation_rules)


# ---------------------------------------------------------------------------
# PromptKind — the engine's discriminator for which prompt it's awaiting next.
# ---------------------------------------------------------------------------
#
# Used in two places:
#   - `Observation.prompt` (player-visible hint of next input shape)
#   - `PromptIssued.kind` (event-stream signal of what the engine awaits)
#
# Values:
#   "action"           — top-level prompt: SHOOT OR MOVE (S-M)?
#   "move_target"      — after the player picks M, the engine awaits a room number
#   "shoot_path_len"   — after the player picks S, the engine awaits NO. OF ROOMS(1-5)?
#   "shoot_path_room"  — once path length is set, the engine awaits each slot's ROOM #?
PromptKind = Literal[
    "action",
    "move_target",
    "shoot_path_len",
    "shoot_path_room",
    # R1-S07 — post-terminal "SAME SET-UP (Y-N)?" prompt. The engine parks
    # in this state after any GameEnded so the caller can answer Y (restore
    # the initial layout) or N (end the session via SessionEnded).
    "same_setup",
    # R1-S08 — pre-game "INSTRUCTIONS (Y-N)?" prompt. The engine parks in
    # this state at construction (before any GameStarted-driven turn so
    # the caller can answer Y (print the verbatim Yob instructions block +
    # banner) or N (just print the banner). Invalid input re-prompts; the
    # turn counter does not advance until the answer is accepted.
    "instructions",
]


# ---------------------------------------------------------------------------
# A1 — World
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class World:
    """Engine's internal state-of-record.

    Value-typed; transitions in `wumpus.engine.transitions` return new World
    instances. `Game._world` holds the current value.

    R0 carries the full Tier-A1 field set so subsequent slices extend without
    schema break. R0's toy-cave fixture populates `pit_rooms=()`, `bat_rooms=()`,
    `wumpus_rooms=(<single room>,)`, `arrows=0`.
    """

    player_room: int
    wumpus_rooms: tuple[int, ...]
    pit_rooms: tuple[int, ...]
    bat_rooms: tuple[int, ...]
    arrows: int
    turn: int
    alive: bool
    pending_prompt: str | None
    pending_arrow_path: tuple[int, ...]
    # R1-S05: when a shoot path is being collected, this records the total
    # length committed by the player at the NO. OF ROOMS(1-5)? prompt. None
    # outside of shoot-path collection. The snapshot round-trip depends on
    # this field so a resurrected Game knows it's at slot K of N.
    pending_path_length: int | None = None


# ---------------------------------------------------------------------------
# A2 — Snapshot
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Snapshot:
    """Serializable engine snapshot.

    Per ADR-001/SC6: `rng_cursor` is a base64-encoded pickled
    `random.Random.getstate()` string — NOT a `random.Random` object — so the
    whole snapshot is JSON-round-trippable.

    R0 carries `variant_config=None` (R4-S01 ships the parametric type) and
    `surface_id="<placeholder>"` (R4-S03 ships the real Yob surface).

    R3-S01 extends the shape with everything a `Game.from_snapshot(snap)`
    needs to reconstruct an observationally-equivalent Game instance:

      - `initial_layout: World` — the original layout at construction-time
        (Game._initial_layout). Restored on SAME SET-UP=Y; pre R3-S01,
        `from_snapshot` set `_initial_layout = world` which broke
        SAME SET-UP=Y after a snapshot-restore (it would restore the
        mid-game world instead of the original layout).
      - `cave: str` — toy/yob distinguisher (Game._cave). R0's toy cave
        bypasses hazard_resolve + the Yob-cave pre-game INSTRUCTIONS state;
        a resurrected Game must know which mode to run in.

    Both fields land with a sensible default for backward-compat: existing
    Snapshot constructors that don't pass them still build, but the Game
    round-trip is only correct when they're populated by `Game.snapshot()`.
    """

    schema_version: int
    engine_version: str
    seed: int
    rng_cursor: str
    surface_id: str
    world: World
    active_escalation_rules: tuple[str, ...] = ()
    # R3-S01: full round-trip fields. `initial_layout` defaults to a sentinel
    # `None` so existing test fixtures still construct; the round-trip path
    # in `Game.from_snapshot` falls back to `world` when the field is None
    # (matching the pre-R3-S01 behavior — broken for SAME SET-UP=Y after a
    # snapshot/restore, but no worse than what shipped at R1-S07).
    initial_layout: World | None = None
    # R3-S01: cave topology selector. Defaults to "yob" (the Yob-default
    # cave from R1-S01); explicit "toy" is required for toy-cave snapshots.
    cave: str = "yob"


# ---------------------------------------------------------------------------
# A3 — Observation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Observation:
    """What the player (or LLM) sees this turn.

    Surface-translated lines live in `rendered_lines`. Parsed fields below
    (`player_room`, `adjacencies`, `senses`) are HARNESS_PRIVATE per ADR-004:
    LLM agents must derive these from `rendered_lines`. R0's surface seam is
    deferred (R4-S03); R0 emits `<placeholder>` strings.
    """

    rendered_lines: tuple[str, ...]
    prompt: str | None
    outcome: str | None
    player_room: int
    adjacencies: tuple[int, ...]
    senses: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# A8 — Sink (re-exported by wumpus.sinks)
# ---------------------------------------------------------------------------


class Sink(Protocol):
    """Outbound port for event emission. Called synchronously on the engine's
    thread. Sinks MUST NOT assume multi-thread coordination."""

    name: str

    def emit(self, event: object) -> None: ...


# ---------------------------------------------------------------------------
# A5/A6 — CommandVerb + ParsedCommand + Surface (R4-S03)
# ---------------------------------------------------------------------------
#
# CommandVerb is the engine's internal alphabet of player intents. The engine
# routes on these enum-like tags; the Surface translates between them and the
# player-facing input tokens ("S", "M", "Y", "N") and back (command_parse).
# The token<->verb pair is what R4-S05's MysterySurface obfuscates: a Mystery
# run reads/writes scrambled tokens but the engine sees the identical verbs,
# so the internal trajectory is byte-identical (SC9).
#
# The Yob verbs (the only ones today):
#   SHOOT / MOVE      — top-level SHOOT OR MOVE (S-M)? answers ("S" / "M")
#   YES / NO          — the Y/N answers at INSTRUCTIONS + SAME SET-UP prompts
# Bare integers (room numbers, path lengths) are NOT verbs — they are numeric
# payloads the engine parses directly; the surface does not translate digits.

CommandVerb = Literal["SHOOT", "MOVE", "YES", "NO"]


@dataclass(frozen=True)
class ParsedCommand:
    """Result of `Surface.command_parse` — a verb plus optional numeric payload.

    R4-S03 ships the `verb`-only shape (the surface translates the verb token;
    the engine parses any trailing room number itself). `argument` is reserved
    for surfaces that fuse a verb + a number into one token (none do today);
    it defaults to None so the round-trip contract is `verb`-only.
    """

    verb: CommandVerb
    argument: int | None = None


class Surface(Protocol):
    """Translation layer between engine internals (IDs, enum tags) and the
    player-facing strings. The engine reads strings from a Surface at the
    output boundary; the Surface never reads engine state and never consumes
    RNG (SC8, SC9).

    Reconciliation note (R4-S03): the DESIGN A6 Protocol sketch listed five
    GENERIC dispatch methods (`render_room` / `render_sense` / `render_message`
    / `render_prompt` / `parse_command`). The Story R4-S03 AC (scenario 2) and
    the earlier A5 artifact sketch instead enumerate SEMANTIC methods
    (`room_label`, `sense_string`, `hazard_name`, `command_token`,
    `command_parse`, `prompt_text`, `instructions_block`). We adopt the
    A5/AC semantic shape: it is the authoritative test contract, it names every
    surface-form string the engine emits, and it adds the `command_token` /
    `command_parse` inverse pair R4-S05's Mystery obfuscation needs. The A6
    generic methods are subsumed — `render_sense`/`render_message` collapse to
    `sense_string`/`hazard_name`, `render_prompt` to `prompt_text`,
    `render_room` to `room_label`, and `parse_command` to the
    `command_token`/`command_parse` pair.
    """

    surface_id: str  # "yob" | "mystery" | "french" | ...

    def room_label(self, room_id: int) -> str:
        """Player-facing label for a room id (Yob: the decimal number)."""
        ...

    def sense_string(self, kind: str) -> str:
        """Player-facing line for a SenseEmitted.kind
        ("WUMPUS_SMELL" / "PIT_DRAFT" / "BAT_NEARBY")."""
        ...

    def hazard_name(self, kind: str) -> str:
        """Player-facing reason line for a HazardTriggered.kind
        ("WUMPUS" / "PIT" / "BAT")."""
        ...

    def command_token(self, verb: CommandVerb) -> str:
        """Player-facing input token for a CommandVerb (Yob: "S"/"M"/"Y"/"N")."""
        ...

    def command_parse(self, token: str) -> ParsedCommand:
        """Inverse of `command_token`: parse a player-supplied token into a
        ParsedCommand. The contract: `command_parse(command_token(v)).verb == v`
        for every CommandVerb (inverse-translation completeness)."""
        ...

    def prompt_text(self, kind: str) -> str:
        """Player-facing prompt text for a PromptKind discriminator."""
        ...

    def instructions_block(self) -> tuple[str, ...]:
        """The verbatim instructions block, one tuple entry per line."""
        ...
