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

Additional event types (HazardResolved, ArrowPathStep, GameEnded,
SinkFailure, ...) land in subsequent releases per their respective slices.

Per ADR-002 (schema evolution) this module pins SCHEMA_VERSION; R0 ships v1.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from wumpus.types import Snapshot

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
    # Optional harness-supplied fields (HARNESS_PRIVATE per ADR-004 / taxonomy):
    wall_clock_ts: float | None = None
    actor_node: str | None = None
    back_prompted: bool | None = None
    actor_scratchpad: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None


# ---------------------------------------------------------------------------
# Per-type event dataclasses (R0 subset)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GameStarted(_BaseEventFields):
    """Emitted once when `Game(seed=k)` is constructed.

    Carries the constructor's seed, the engine version, and a layout hash so
    downstream replays can verify SAME SET-UP=Y semantics (R3 territory; R0
    just ships the field).
    """

    type: Literal["GameStarted"] = "GameStarted"
    seed: int = 0
    engine_version: str = ""
    surface_id: str = ""
    layout_hash: str = ""
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
    | GameEnded
)
