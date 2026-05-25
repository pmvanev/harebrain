"""wumpus — the engine the harebrain experiment matrix runs on.

Faithful Yob 1973 at the core, extensible at the seams, observable by construction.

Public API surfaces here as the wave artifacts (DESIGN [REF] Engine module layout)
implement each slice. At R0 (walking skeleton), only `Game` + minimal types are
exported.
"""

from __future__ import annotations

from wumpus.engine.game import Game
from wumpus.events import (
    SCHEMA_VERSION,
    ActionChosen,
    ArrowCountChanged,
    ArrowFired,
    ArrowHitPlayer,
    ArrowHitWumpus,
    ArrowMissed,
    ArrowPathStep,
    CrookedPathRejected,
    Event,
    GameEnded,
    GameStarted,
    HazardTriggered,
    InstructionsShown,
    LocationReported,
    MoveAttempted,
    MoveResolved,
    PlayerTeleported,
    PromptIssued,
    SenseEmitted,
    SessionEnded,
    WumpusStartled,
)
from wumpus.replay import Replay, VersionCompatibilityError, replay
from wumpus.serialization import event_from_dict, event_to_dict
from wumpus.types import Observation, PromptKind, Snapshot, World

__version__ = "0.0.0"

__all__ = [
    "Game",
    "World",
    "Snapshot",
    "Observation",
    "PromptKind",
    "Event",
    "GameStarted",
    "MoveAttempted",
    "MoveResolved",
    "SenseEmitted",
    "LocationReported",
    "HazardTriggered",
    "WumpusStartled",
    "PlayerTeleported",
    "ActionChosen",
    "PromptIssued",
    "CrookedPathRejected",
    "ArrowFired",
    "ArrowPathStep",
    "ArrowMissed",
    "ArrowHitWumpus",
    "ArrowHitPlayer",
    "ArrowCountChanged",
    "GameEnded",
    "SessionEnded",
    "InstructionsShown",
    "SCHEMA_VERSION",
    "event_to_dict",
    "event_from_dict",
    "replay",
    "Replay",
    "VersionCompatibilityError",
]
