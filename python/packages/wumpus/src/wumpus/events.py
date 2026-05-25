"""Event dataclasses for the wumpus engine.

Per ADR-010 (Event shape): one frozen dataclass per event type, each with a
`type: Literal["..."]` discriminator. Shared fields are composed via a private
`_BaseEventFields` helper; this is field-declaration sharing only, not a
polymorphic base. Consumers pattern-match on the discriminated union `Event`.

R0 ships only the events the walking skeleton needs:
    - GameStarted
    - MoveAttempted
    - MoveResolved

R1-S02 adds:
    - SenseEmitted     (one per adjacent wumpus/pit/bat on room entry)
    - LocationReported (fires after all SenseEmitted on a successful move)

R1-S03 adds:
    - HazardTriggered  (player walks onto a hazard room)
    - WumpusStartled   (FNC(0) startle PMF outcome after a wumpus bump)
    - GameEnded        (terminal state — win or lose)

R1-S04 adds:
    - PlayerTeleported (bat snatch + Yob FNB(1) destination)

Additional event types (ArrowPathStep, SinkFailure, ...) land in subsequent
releases per their respective slices.

Per ADR-002 (schema evolution) this module pins SCHEMA_VERSION; R0 ships v1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from wumpus.types import PromptKind, Snapshot

SCHEMA_VERSION: int = 1


# ---------------------------------------------------------------------------
# Shared field declaration (NOT a polymorphic base; per ADR-010)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _BaseEventFields:
    """Shared fields composed into each Event subtype.

    Consumers MUST NOT type-annotate against this class. Use the `Event` union
    or a specific subtype. Per ADR-010, this exists ONLY to share field
    declarations across the ~21 event dataclasses; it has no virtual methods
    and no dispatch role.
    """

    schema_version: int
    turn: int
    surface_variant: str
    internal_state_hash: str
    rng_cursor: str
    # R2-S01: monotonic_turn ships at R2-S01 (per Tier A4 amendment), defaulting
    # to `turn` so existing call sites stay compatible. The field is integral
    # to the schema document — replays will compare it across paired sessions.
    monotonic_turn: int = 0
    # Optional harness-supplied fields (HARNESS_PRIVATE per ADR-004 / taxonomy):
    wall_clock_ts: float | None = None
    actor_node: str | None = None
    back_prompted: bool | None = None
    actor_scratchpad: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    # R2-S01: per Tier A4 amendment — raw bytes of the player's input that
    # triggered this event (when applicable). HARNESS_PRIVATE (ADR-004).
    raw_input_bytes: str | None = None


# ---------------------------------------------------------------------------
# Per-type event dataclasses (R0 subset)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GameStarted(_BaseEventFields):
    """Emitted once when `Game(seed=k)` is constructed.

    Carries everything `replay(ledger_path)` needs to reconstruct the
    session from the header alone (R2-S02): the seed, the engine version,
    the initial layout hash, the variant config (parametric handling lands
    at R4-S01; R2-S02 ships the placeholder shape), and the surface_id
    (`"yob"` today; `"mystery"` / `"french"` arrive at R4-S03+).

    Per ADR-002 (additive schema evolution) `variant_config` is typed as a
    flexible dict so R4-S01 can add fields without breaking the v1
    contract.
    """

    type: Literal["GameStarted"] = "GameStarted"
    seed: int = 0
    engine_version: str = ""
    surface_id: str = ""
    layout_hash: str = ""
    # R2-S02: placeholder shape `{"name": "yob"}`. R4-S01 lands the
    # parametric VariantConfig; the schema permits additive fields here.
    variant_config: dict[str, object] = field(default_factory=lambda: {"name": "yob"})
    active_escalation_rules: tuple[str, ...] = ()


@dataclass(frozen=True)
class MoveAttempted(_BaseEventFields):
    """Emitted when the player issues a `move <N>` action.

    `accepted=True` means the target room is adjacent and the move will be
    resolved; `accepted=False` means the engine rejected the action (target
    not adjacent / not a valid room) and would re-prompt.
    """

    type: Literal["MoveAttempted"] = "MoveAttempted"
    target_room: int = -1
    accepted: bool = False


@dataclass(frozen=True)
class MoveResolved(_BaseEventFields):
    """Emitted after a `MoveAttempted(accepted=True)` is applied to the world.

    Carries the resulting player room. R0 does NOT resolve hazards here; that
    lands at R1 with pits/bats/multiple wumpuses.
    """

    type: Literal["MoveResolved"] = "MoveResolved"
    player_room: int = -1


@dataclass(frozen=True)
class SenseEmitted(_BaseEventFields):
    """Emitted on room entry for each adjacent wumpus/pit/bat, in Yob's
    L-array order (see `wumpus.constants.SENSE_ORDER`).

    `kind` is a discriminator (enum-like) the engine emits; surface translation
    to "I SMELL A WUMPUS!" / "I FEEL A DRAFT" / "BATS NEARBY!" lives at R4-S03
    behind the Surface seam (SC8). `cause_room` records the room number of
    the adjacent hazard whose presence fired this event — pedagogically useful
    for downstream replay analysis.
    """

    type: Literal["SenseEmitted"] = "SenseEmitted"
    kind: Literal["WUMPUS_SMELL", "PIT_DRAFT", "BAT_NEARBY"] = "WUMPUS_SMELL"
    cause_room: int = -1


@dataclass(frozen=True)
class LocationReported(_BaseEventFields):
    """Emitted on every successful move AFTER any SenseEmitted events for the
    newly-entered room.

    Carries the room number plus the room's tuple of adjacent rooms (the
    dodecahedron is 3-regular, so always three). Yob's BASIC source prints
    `YOU ARE IN ROOM <n>` + `TUNNELS LEAD TO <a> <b> <c>` immediately after
    the sense lines; this event packages the structured ground truth that
    feeds those two render lines.
    """

    type: Literal["LocationReported"] = "LocationReported"
    room: int = -1
    adjacencies: tuple[int, int, int] = (-1, -1, -1)


@dataclass(frozen=True)
class HazardTriggered(_BaseEventFields):
    """Emitted when the player enters a room containing a hazard.

    R1-S03 ships only `kind="WUMPUS"`; R1-S04 extends with `"PIT"` and
    `"BAT"`. The event fires BEFORE the kind-specific follow-up
    (WumpusStartled for wumpus, GameEnded for pit, PlayerTeleported for bat —
    last two land at R1-S04). Surface translation of the kind to Yob's
    `...OOPS! BUMPED A WUMPUS!` / `YYYIIIIEEEE` / `ZAP--SUPER BAT SNATCH!`
    happens at R4-S03 behind the Surface seam (SC8).

    The `room` field records the room the hazard was triggered in (the
    player's post-move room). Carrying it on the event keeps the event
    stream self-contained for replay analysis.
    """

    type: Literal["HazardTriggered"] = "HazardTriggered"
    kind: Literal["WUMPUS", "PIT", "BAT"] = "WUMPUS"
    room: int = -1


@dataclass(frozen=True)
class WumpusStartled(_BaseEventFields):
    """Emitted after `HazardTriggered(WUMPUS)` to record the FNC(0) startle
    outcome (Yob `bas` 3370-3440).

    `FNC(0)` draws K ∈ {1, 2, 3, 4}. For K ∈ {1, 2, 3} the wumpus moves to
    `S(L(2), K)` — its K-th adjacent room (in Yob's adjacency-table order;
    here, `sorted(DODECAHEDRON[from_room])[K-1]`). For K=4 the wumpus stays.

    If the destination room equals the player's room, `ate_player=True` and
    a downstream `GameEnded(outcome=eaten_after_bump)` fires.
    """

    type: Literal["WumpusStartled"] = "WumpusStartled"
    from_room: int = -1
    to_room: int = -1
    ate_player: bool = False


@dataclass(frozen=True)
class PlayerTeleported(_BaseEventFields):
    """Emitted after `HazardTriggered(BAT)` to record a bat-snatch teleport
    (Yob `bas` 4270-4300; `FNB(1)` → uniform random over rooms 1..20).

    `from_room` is the room the bat snatched the player from; `to_room` is
    the bat's chosen destination (which may itself be a hazard — Yob recurses
    via `GOTO 4130`). `cause` is currently always `"bat"`; the field exists
    per L18 (sense-history pollution from counterfactual rollouts) and the
    Tier A4 amendment, so downstream metric analysis can distinguish
    bat-induced location changes from voluntary moves.

    The destination may be the player's CURRENT room (no-op teleport), the
    wumpus's room (bump-startle chain), another bat's room (recurse), or a
    pit (game-ending). Yob handles all four uniformly via the GOTO 4130
    recursion.
    """

    type: Literal["PlayerTeleported"] = "PlayerTeleported"
    from_room: int = -1
    to_room: int = -1
    cause: Literal["bat"] = "bat"


@dataclass(frozen=True)
class ActionChosen(_BaseEventFields):
    """Emitted when the player picks an action at the top-level prompt
    (S = shoot, M = move). Lands at R1-S05 as the first event of the shoot
    sub-state-machine; the move-side analog is implicit in the existing
    MoveAttempted chain (R0 / R1-S01) — a future slice may emit it
    explicitly on the move path for symmetry.

    Per ADR-010 / DESIGN A4 event-family, this event is part of the
    canonical event-stream alphabet; carries no additional state beyond the
    chosen action.
    """

    type: Literal["ActionChosen"] = "ActionChosen"
    action: Literal["S", "M"] = "S"


@dataclass(frozen=True)
class PromptIssued(_BaseEventFields):
    """Emitted when the engine becomes ready to receive its next input.

    `kind` discriminates which prompt is being issued:
      - "action"          — top-level SHOOT OR MOVE (S-M)?
      - "move_target"     — after the player picks M, awaiting a room number
      - "shoot_path_len"  — after the player picks S, awaiting NO. OF ROOMS(1-5)?
      - "shoot_path_room" — once path length is set, awaiting each slot's ROOM #?

    `context` carries prompt-specific structured data for downstream consumers:
      - "shoot_path_room": {"slot": K, "of": N} — current slot index and total
      - others: None or {} as appropriate

    Surface rendering of the prompt text lives at R4-S03 (SC8); the engine
    only emits the structured discriminator + context.
    """

    type: Literal["PromptIssued"] = "PromptIssued"
    kind: PromptKind = "action"
    # `context` is a dict mapping str → primitive (int, str, etc). We use a
    # tuple of (key, value) pairs internally is more dataclass-friendly, but
    # the simpler dict suffices here — frozen dataclasses don't deeply freeze
    # mutable defaults; we use a default_factory to avoid the shared-mutable
    # trap, and `None` to mean "no context".
    context: dict[str, int | str] | None = None


@dataclass(frozen=True)
class CrookedPathRejected(_BaseEventFields):
    """Emitted when a player-supplied shoot-path entry violates Yob's
    crooked-arrow rule `P(K) == P(K-2)` (K > 2).

    `slot` is the 1-indexed slot that was rejected; `attempted_room` is the
    room the player typed. The engine re-prompts ONLY that slot (the
    previously-accepted slots are preserved). Yob's surface text
    `ARROWS AREN'T THAT CROOKED - TRY ANOTHER ROOM` is rendered at R4-S03.
    """

    type: Literal["CrookedPathRejected"] = "CrookedPathRejected"
    slot: int = -1
    attempted_room: int = -1


@dataclass(frozen=True)
class ArrowFired(_BaseEventFields):
    """Emitted when the shoot-collection sub-state-machine finishes
    accepting all slots of a path. Marks the end of the input-collection
    phase; the actual arrow-walk through the dodecahedron lands at R1-S06.

    `path` is the full collected path (1-indexed slots in order). At R1-S05
    no walking happens — the event records the path; R1-S06's arrow walk
    consumes it.
    """

    type: Literal["ArrowFired"] = "ArrowFired"
    path: tuple[int, ...] = ()


@dataclass(frozen=True)
class ArrowPathStep(_BaseEventFields):
    """Emitted once per room the arrow visits during the R1-S06 walk.

    `room` is the room the arrow has just entered. `deflected=False` means
    the room came from the player's submitted path (the previous room was
    adjacent to it). `deflected=True` means the previous room was NOT
    adjacent to the path's next slot, so the arrow took a uniform-random
    adjacent room per Yob's `FNB(1)` (BASIC source 3170-3210). When a
    deflection fires, all remaining path slots are discarded.
    """

    type: Literal["ArrowPathStep"] = "ArrowPathStep"
    room: int = -1
    deflected: bool = False


@dataclass(frozen=True)
class ArrowMissed(_BaseEventFields):
    """Emitted when the collected arrow path has been fully walked and the
    final room is NOT the wumpus's and NOT the player's. Followed by a
    wumpus startle (reusing R1-S03's `move_wumpus_startle`) and an
    `ArrowCountChanged` decrement. If the startled wumpus lands on the
    player, a `GameEnded(eaten_after_bump)` follows. If the arrow count
    reaches 0, a `GameEnded(out_of_arrows)` follows.

    Carries no payload beyond the shared `_BaseEventFields` — Yob's
    `MISSED` line is a fixed string, so the structured event simply
    discriminates the case.
    """

    type: Literal["ArrowMissed"] = "ArrowMissed"


@dataclass(frozen=True)
class ArrowHitWumpus(_BaseEventFields):
    """Emitted when the arrow's final room equals the wumpus's room.

    Followed by `GameEnded(outcome="wumpus_shot", message_kind="win")`.
    Per Yob bug-for-bug (D11), the arrow count is NOT decremented on a
    hit-wumpus — the game ends first. `room` is the wumpus's room (the
    arrow's terminal resting room).
    """

    type: Literal["ArrowHitWumpus"] = "ArrowHitWumpus"
    room: int = -1


@dataclass(frozen=True)
class ArrowHitPlayer(_BaseEventFields):
    """Emitted ONLY when the arrow's FINAL room equals the player's room.

    Yob's bug-for-bug rule (D11): a crooked arrow that passes through the
    player's room mid-path does NOT kill the player. Only a final-room
    match triggers `ArrowHitPlayer`. The arrow count is decremented as
    if the shot had missed; the game continues unless the decrement
    reaches 0 (`GameEnded(out_of_arrows)`).

    `room` is the arrow's final room (== player's room).
    """

    type: Literal["ArrowHitPlayer"] = "ArrowHitPlayer"
    room: int = -1


@dataclass(frozen=True)
class ArrowCountChanged(_BaseEventFields):
    """Emitted when the arrow count changes — on miss or self-shot.

    Per Yob bug-for-bug, a hit-wumpus does NOT decrement (the game ends
    first). The event carries the post-change count; consumers compute
    the delta from the prior `ArrowCountChanged` (or from `GameStarted`'s
    implicit starting count of 5).
    """

    type: Literal["ArrowCountChanged"] = "ArrowCountChanged"
    new_count: int = -1


@dataclass(frozen=True)
class InstructionsShown(_BaseEventFields):
    """Emitted when the player answers Y at the pre-game INSTRUCTIONS
    (Y-N)? prompt (R1-S08). Carries the full verbatim Yob instructions
    block as a tuple of lines so downstream consumers (renderer, ledger,
    LLM-actor harness) have the structured payload, not just the
    surface-translated render lines.

    Per SC8 the engine emits this structured event; the surface
    (`wumpus.surfaces.yob.render_instructions`) translates `lines` into
    output text. Yob's BASIC source emits the instructions via PRINT
    statements at lines 1010-1400; the `lines` field stores those verbatim
    in BASIC-source order, one tuple entry per PRINT (with bare PRINT
    becoming an empty string).

    The `RAMDOM` typo (BASIC line 1300) is preserved bug-for-bug per D11.
    """

    type: Literal["InstructionsShown"] = "InstructionsShown"
    lines: tuple[str, ...] = ()


@dataclass(frozen=True)
class SessionEnded(_BaseEventFields):
    """Emitted when the player declines SAME SET-UP=N at the post-terminal
    prompt (R1-S07).

    Per the R1-S07 decision: Yob's source generates a fresh cave on
    SAME SET-UP=N (rolling a new FNB layout from the continuing RNG).
    R1-S07's minimal design treats N as a clean session close — the engine
    emits `SessionEnded`, parks in a terminal state, and ignores further
    actions. The fresh-cave behavior is generalizable to a downstream
    slice (or to the harness layer) and is NOT needed by R0-R4 (the
    experiment matrix runs one game per Game instance).

    The event carries no payload beyond `_BaseEventFields`; the
    discriminator alone suffices for downstream consumers to recognize
    the session-close intent.
    """

    type: Literal["SessionEnded"] = "SessionEnded"


@dataclass(frozen=True)
class GameEnded(_BaseEventFields):
    """Emitted exactly once on any terminal state — win or lose.

    `outcome` discriminates the terminal cause; `message_kind` records the
    Yob win/lose-swap (HEE HEE HEE on lose vs HA HA HA on win, per Yob's
    famously-bugged BASIC). Surface translation of `message_kind` to the
    actual rendered text lives at R1-S07 / R4-S03; the engine just emits
    the structured discriminator (SC8).

    `final_snapshot` captures the engine's full state at the moment the
    game ends — used by R1-S07's `SAME SET-UP=Y` reset (restoring the
    initial layout) and by replay analysis. The Snapshot is value-typed
    (ADR-001/SC6), so the capture is cheap and serialization-safe.
    """

    type: Literal["GameEnded"] = "GameEnded"
    outcome: Literal[
        "wumpus_shot", "eaten_after_bump", "fell_in_pit", "out_of_arrows"
    ] = "eaten_after_bump"
    message_kind: Literal["win", "lose"] = "lose"
    final_snapshot: Snapshot | None = None


# ---------------------------------------------------------------------------
# Discriminated union — pattern matching at consumers uses this alias.
# ---------------------------------------------------------------------------


Event = (
    GameStarted
    | MoveAttempted
    | MoveResolved
    | SenseEmitted
    | LocationReported
    | HazardTriggered
    | WumpusStartled
    | PlayerTeleported
    | ActionChosen
    | PromptIssued
    | CrookedPathRejected
    | ArrowFired
    | ArrowPathStep
    | ArrowMissed
    | ArrowHitWumpus
    | ArrowHitPlayer
    | ArrowCountChanged
    | GameEnded
    | SessionEnded
    | InstructionsShown
)
