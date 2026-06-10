"""Host-import seam (R5-S01) — drive the engine from a serialized snapshot.

Goals-doc done-criterion #3 / KPI K-4 / SC12: an MPL chart leaf (or any host
that exits between turns) drives the engine one turn at a time by passing the
*serialized* snapshot in and getting the next serialized snapshot back — the
snapshot string is the entire carry-over.

`step_from_snapshot(snap_json, action) -> StepResult` is a single PURE function
with no module-level state: it resurrects a fresh `Game` from the JSON string,
subscribes a fresh `Sink` AFTER resurrection (so the `from_snapshot`
GameStarted/PromptIssued preamble does NOT leak as a turn event), applies the
action, and returns the new serialized snapshot + flattened observation +
this-turn events. Built entirely on the public `wumpus` exports + the public
`subscribe()` port; zero `engine/*` edits; no new dependencies. The full spike
rationale lives in feature-delta.md § Wave: SPIKE.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Iterator

from wumpus import (
    Game,
    event_to_dict,
    snapshot_from_json,
    snapshot_to_json,
)
from wumpus.sinks import InMemorySink


@dataclass(frozen=True)
class StepResult:
    """JSON-serializable result of one host-import turn.

    - `snapshot_json`: the NEW serialized snapshot (canonical sort_keys JSON
      via `snapshot_to_json`). The host writes this back and feeds it to the
      next `step_from_snapshot` call.
    - `observation`: the per-turn `Observation` flattened to JSON-safe
      primitives (`player_room`, `adjacencies`, `rendered_lines`).
    - `events`: this turn's emitted events as dicts (via `event_to_dict`),
      capturing ONLY the events `step(action)` produced — not the
      `from_snapshot` resurrection preamble.
    """

    snapshot_json: str
    observation: dict[str, Any]
    events: list[dict[str, Any]]


def step_from_snapshot(snap_json: str, action: str) -> StepResult:
    """Apply ONE `action` to the game serialized in `snap_json`.

    Pure: builds a fresh `Game` from the snapshot string, applies the action,
    and returns the new serialized snapshot + observation + this-turn events.
    No module-level state — exiting the process between calls is equivalent to
    keeping a live `Game` (the cross-process equivalence the spike proved).

    This-turn events are captured via a fresh `InMemorySink` subscribed AFTER
    resurrection. `Game.from_snapshot` re-emits a `GameStarted` (and, for a
    mid-prompt snapshot, a `PromptIssued`) preamble BEFORE we subscribe, so
    that preamble is never delivered to the sink — only the events `step`
    emits are. (We deliberately do NOT read the `_debug_events` backdoor.)
    """
    game = Game.from_snapshot(snapshot_from_json(snap_json))
    sink = InMemorySink()
    game.subscribe(sink)
    pre_step = len(sink.events)
    observation = game.step(action)
    turn_events = [event_to_dict(event) for event in sink.events[pre_step:]]
    return StepResult(
        snapshot_json=snapshot_to_json(game.snapshot()),
        observation={
            "player_room": observation.player_room,
            "adjacencies": list(observation.adjacencies),
            "rendered_lines": list(observation.rendered_lines),
        },
        events=turn_events,
    )


def iter_steps(initial_snap_json: str, actions: Iterable[str]) -> Iterator[StepResult]:
    """Persistent-worker convenience: drive `actions` in ONE process, threading
    each turn's `snapshot_json` into the next `step_from_snapshot` call.

    Avoids the ~150 ms/turn cold-start the spike measured for process-per-turn,
    while preserving the exact same per-turn semantics (the snapshot string is
    still the only carry-over). Yields one `StepResult` per action.
    """
    snap_json = initial_snap_json
    for action in actions:
        result = step_from_snapshot(snap_json, action)
        snap_json = result.snapshot_json
        yield result
