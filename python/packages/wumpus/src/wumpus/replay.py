"""Ledger replay — reconstruct World from a JSONL event stream.

R2-S02 ships the `replay(ledger_path)` driving port that re-builds the
engine's World value at any turn by walking events from a ledger.

The contract:
  1. The first line of the ledger MUST be a `GameStarted` event. It
     carries the seed + engine_version + layout_hash + variant_config +
     surface_id sufficient to bootstrap the initial layout via
     `wumpus.engine.cave_gen.generate_initial_layout(random.Random(seed))`
     (proving the seed-determinism contract end-to-end).
  2. Every subsequent line is a v1 event (validated against the schema by
     `JsonlSink` at WRITE time; replay re-deserializes via
     `event_from_dict` and applies a state-delta to a running World value).
  3. `replay(...)` returns a `Replay` cursor. `Replay.advance_to(turn=k)`
     walks events until the cumulative turn count reaches `k` (turn-level
     granularity per the R2-S02 scope; sub-turn replay is deferred).
  4. Engine-version compatibility per ADR-002: equal versions proceed,
     different MAJOR raises `VersionCompatibilityError`, different
     MINOR/PATCH proceeds (additive schema evolution).

Replay does NOT duplicate engine state-transition logic. Events fully
describe their state delta (Yob 1973's BASIC source `bas` lines 4140-4310
prove this — every state-mutating event in the ledger has a self-contained
payload). Replay's apply-event-to-world dispatch is a thin reducer; the
canonical engine logic stays in `Game.step` and `wumpus.engine.transitions`.
"""

from __future__ import annotations

import json
import pathlib
import random
from dataclasses import replace
from typing import Iterator

from wumpus.engine.cave_gen import generate_initial_layout
from wumpus.events import (
    ArrowCountChanged,
    Event,
    GameEnded,
    GameStarted,
    MoveResolved,
    PlayerTeleported,
    SessionEnded,
    WumpusStartled,
)
from wumpus.serialization import event_from_dict
from wumpus.types import World


class VersionCompatibilityError(Exception):
    """Raised by `replay()` when the ledger's `GameStarted.engine_version`
    has a different MAJOR component than the current `wumpus.__version__`.

    Per ADR-002 (schema-evolution policy): major-version mismatches are
    genuinely breaking. Minor/patch differences are recoverable via
    additive schema evolution and do NOT raise.

    The exception message names both versions so downstream operators can
    cite the exact mismatch in bug reports.
    """

    def __init__(self, *, written: str, current: str) -> None:
        self.written = written
        self.current = current
        super().__init__(
            f"VersionCompatibilityError: ledger written by wumpus "
            f"engine_version={written!r}; current engine_version={current!r}. "
            f"Major-version mismatch — per ADR-002 these are genuinely "
            f"breaking changes. Minor/patch differences are recoverable; "
            f"a cross-version shim ships only when schema v2 lands."
        )


def replay(ledger_path: pathlib.Path | str) -> "Replay":
    """Open `ledger_path`, parse the header (first line), and return a
    `Replay` cursor positioned at turn 0 (i.e. just after GameStarted has
    bootstrapped the initial layout).

    Raises:
      VersionCompatibilityError: when the header's `engine_version` has a
        different MAJOR component than `wumpus.__version__`.
      ValueError: when the first line is not a `GameStarted` event or the
        ledger is empty.
    """
    return Replay(pathlib.Path(ledger_path))


class Replay:
    """Cursor over a wumpus ledger. Exposes the rebuilt World at any turn.

    The Replay reads events lazily — `advance_to(turn=k)` consumes lines
    from the ledger file one-by-one until the cumulative turn count
    reaches `k`. The internal `_world` value mutates through `dataclasses.
    replace()` calls as each event is applied; the canonical engine logic
    is NOT duplicated here.

    R2-S02 ships turn-level granularity. Sub-turn precision (replay to a
    specific event mid-turn) is deferred.
    """

    def __init__(self, ledger_path: pathlib.Path) -> None:
        self._path: pathlib.Path = ledger_path
        # Read all lines up front (replay is offline; lazy iteration buys
        # little vs. read-all simplicity, and tests want deterministic
        # iteration). Open + close happens in this constructor.
        with ledger_path.open("r", encoding="utf-8") as fh:
            raw_lines = [line for line in fh.read().split("\n") if line]
        if not raw_lines:
            raise ValueError(
                f"replay({ledger_path!r}): ledger is empty; "
                f"expected a GameStarted header on the first line."
            )

        header_payload = json.loads(raw_lines[0])
        header_event = event_from_dict(header_payload)
        if not isinstance(header_event, GameStarted):
            raise ValueError(
                f"replay({ledger_path!r}): first line is "
                f"{type(header_event).__name__!r}; expected 'GameStarted'."
            )

        # ADR-002 engine-version compatibility gate. Equal versions proceed;
        # MAJOR mismatch raises; MINOR/PATCH mismatch proceeds silently
        # (additive schema evolution). Lazy import of wumpus.__version__
        # avoids the circular-import trap (wumpus/__init__.py imports
        # replay).
        import wumpus

        _check_version_compatibility(
            written=header_event.engine_version,
            current=wumpus.__version__,
        )

        self._header: GameStarted = header_event
        self._engine_version: str = header_event.engine_version
        self._seed: int = header_event.seed
        # Bootstrap World from the seed (proves the seed-determinism
        # contract end-to-end). The layout MUST match what `Game.__init__`
        # produces given the same seed — confirmed by the round-trip
        # property test.
        layout = generate_initial_layout(random.Random(header_event.seed))
        self._world: World = World(
            player_room=layout.player_start,
            wumpus_rooms=layout.wumpus_rooms,
            pit_rooms=layout.pit_rooms,
            bat_rooms=layout.bat_rooms,
            arrows=0,
            turn=0,
            alive=True,
            pending_prompt=None,
            pending_arrow_path=(),
            pending_path_length=None,
        )
        # Iterator over the post-header events.
        self._tail_events: Iterator[Event] = iter(
            _deserialize_tail(raw_lines[1:])
        )
        # Bookkeeping for the "consumed but not yet beyond target" lookahead.
        self._pending_event: Event | None = None

    # ---- public read-only header surface ---------------------------------

    @property
    def engine_version(self) -> str:
        """Engine version recorded in the ledger header."""
        return self._engine_version

    @property
    def seed(self) -> int:
        """Seed recorded in the ledger header."""
        return self._seed

    # ---- cursor advance --------------------------------------------------

    def advance_to(self, turn: int) -> "Replay":
        """Apply events from the ledger until the World's `turn` reaches
        `turn` AND all events tagged with `turn` have been consumed (so
        the World reflects the full post-turn state, not the first event
        that happens to be tagged with the target turn).

        Idempotent if the cursor is already past the target (advancing
        backwards is NOT supported in R2-S02 — replay is forward-only;
        create a fresh `Replay` instance to rewind).

        Returns `self` so callers can chain
        `replay(...).advance_to(15).world_state()`.
        """
        if turn < self._world.turn:
            raise ValueError(
                f"Replay.advance_to(turn={turn}): cursor is already at "
                f"turn {self._world.turn}; rewinding is not supported in "
                f"R2-S02. Construct a fresh Replay() to start over."
            )
        while True:
            next_event = self._peek_event()
            if next_event is None:
                if self._world.turn < turn:
                    raise ValueError(
                        f"Replay.advance_to(turn={turn}): ledger exhausted "
                        f"at turn {self._world.turn}; target turn not "
                        f"reachable."
                    )
                return self
            if next_event.turn > turn:
                # The next event belongs to a future turn — stop here so
                # the World reflects the END of the target turn.
                return self
            # next_event.turn <= turn → consume + apply it.
            self._consume_peeked()
            self._apply_event(next_event)

    def world_state(self) -> World:
        """Return the current World value (post-applied events through the
        most recent `advance_to`)."""
        return self._world

    # ---- internals -------------------------------------------------------

    def _peek_event(self) -> Event | None:
        """Peek at the next event without consuming it. Returns None when
        the tail iterator is exhausted. Subsequent calls return the same
        event until `_consume_peeked` is called."""
        if self._pending_event is not None:
            return self._pending_event
        try:
            self._pending_event = next(self._tail_events)
        except StopIteration:
            return None
        return self._pending_event

    def _consume_peeked(self) -> None:
        """Drop the peeked event from the lookahead slot. Must be called
        AFTER `_peek_event` returned a non-None event the caller intends
        to consume."""
        self._pending_event = None

    def _apply_event(self, event: Event) -> None:
        """Update `self._world` per the event's state delta.

        Events that do NOT mutate World (PromptIssued, InstructionsShown,
        SenseEmitted, LocationReported, ActionChosen, CrookedPathRejected,
        ArrowFired, ArrowPathStep, ArrowHitWumpus, ArrowHitPlayer,
        ArrowMissed, HazardTriggered, MoveAttempted) pass through here as
        no-ops — they're observable in the ledger but the World fields
        they care about are already updated by the paired state-mutating
        event (e.g. MoveResolved sets `player_room` + `turn`; SenseEmitted
        is informational).
        """
        if isinstance(event, MoveResolved):
            self._world = replace(
                self._world,
                player_room=event.player_room,
                turn=event.turn,
            )
            return
        if isinstance(event, WumpusStartled):
            # Yob FNC(0): startle moves the wumpus from `from_room` to
            # `to_room` (or stays put if to_room == from_room). World's
            # wumpus_rooms tuple is a single-wumpus singleton at R2-S02.
            new_wumpus_rooms = tuple(
                event.to_room if r == event.from_room else r
                for r in self._world.wumpus_rooms
            )
            self._world = replace(self._world, wumpus_rooms=new_wumpus_rooms)
            return
        if isinstance(event, PlayerTeleported):
            self._world = replace(self._world, player_room=event.to_room)
            return
        if isinstance(event, ArrowCountChanged):
            self._world = replace(self._world, arrows=event.new_count)
            return
        if isinstance(event, GameEnded):
            self._world = replace(self._world, alive=False)
            return
        if isinstance(event, SessionEnded):
            self._world = replace(self._world, alive=False)
            return
        # Other events (MoveAttempted, SenseEmitted, ...) carry no
        # additional World delta beyond what the canonical state-mutating
        # event already encoded. Bump the turn counter only when the
        # event's `turn` field is strictly greater (MoveAttempted accepted
        # AFTER MoveResolved would already have advanced it; rejected
        # MoveAttempted has turn unchanged).
        if event.turn > self._world.turn:
            self._world = replace(self._world, turn=event.turn)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_version_compatibility(*, written: str, current: str) -> None:
    """Raise VersionCompatibilityError if `written` and `current` differ in
    MAJOR. Minor/patch differences are silent (additive evolution per
    ADR-002).

    Version parsing is intentionally minimal — a `MAJOR.MINOR.PATCH` split
    is sufficient for the policy. Non-conformant strings fall through to
    equality check; if they match, no error.
    """
    if written == current:
        return
    written_major = _major_component(written)
    current_major = _major_component(current)
    if written_major != current_major:
        raise VersionCompatibilityError(written=written, current=current)


def _major_component(version: str) -> str:
    """Return the major component of a semver-shaped string. Returns the
    full string if it doesn't contain a `.` (defensive — unknown shapes
    compare by full string)."""
    head, _, _ = version.partition(".")
    return head


def _deserialize_tail(raw_lines: list[str]) -> list[Event]:
    """Parse each JSONL line in `raw_lines` to an Event."""
    return [event_from_dict(json.loads(line)) for line in raw_lines]


__all__ = ["replay", "Replay", "VersionCompatibilityError"]
