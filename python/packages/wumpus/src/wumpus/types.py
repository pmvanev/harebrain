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
from typing import Literal, Protocol

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
    """

    schema_version: int
    engine_version: str
    seed: int
    rng_cursor: str
    surface_id: str
    world: World
    active_escalation_rules: tuple[str, ...] = ()


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
