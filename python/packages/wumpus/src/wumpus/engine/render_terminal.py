"""Event → rendered-line translator for terminal + hazard events.

Per SC8 the engine emits structured events, never literal Yob strings.
This module sits BETWEEN the engine and the surface — it walks an event
stream and dispatches each renderable event to the appropriate Surface
function, accumulating the resulting lines into the
`Observation.rendered_lines` tuple.

R1-S07 ships only the terminal + hazard arms (HazardTriggered, GameEnded,
PromptIssued(kind="same_setup")). Other event kinds yield `("<placeholder>",)`
for backwards compatibility with R0's render placeholder — the full
sense/location/prompt rendering lands at R4-S03.

The module is intentionally stateless + pure (per ADR-001 "FP inside"):
free functions over event iterables; no `Renderer` class. The Game shell
calls `lines_for_events(events_emitted_this_turn)` and passes the result
into the Observation it returns to the caller.

Surface selection is hard-wired to YobSurface at R1-S07 (the only surface
that exists). The Tier A5 Surface Protocol that admits parametric surface
selection lands at R4-S03.
"""

from __future__ import annotations

from typing import Iterable

from wumpus.events import (
    Event,
    GameEnded,
    HazardTriggered,
    InstructionsShown,
    PromptIssued,
)
from wumpus.surfaces import yob as yob_surface

# R0 render placeholder. Events that have no R1-S07-shipped surface mapping
# fall through to this constant so the Observation contract remains stable.
_R0_PLACEHOLDER: str = "<placeholder>"


def lines_for_events(events: Iterable[Event]) -> tuple[str, ...]:
    """Translate `events` (typically the events emitted by a single
    `Game.step`) into rendered lines via the active surface (YobSurface
    at R1-S07).

    Order semantics: lines appear in emission order — i.e., the first
    event's lines come first. The function does NOT collapse duplicates;
    if two HazardTriggered events fire in one turn (theoretically
    possible during a bat→pit chain), both reason lines appear.

    Events without an R1-S07 surface mapping (MoveResolved, SenseEmitted,
    LocationReported, ArrowFired, ...) contribute zero lines. The shell's
    fallback to `("<placeholder>",)` only fires when the resulting tuple
    is empty AND the turn had no renderable events at all.
    """
    rendered: list[str] = []
    for event in events:
        rendered.extend(_render_event(event))
    if not rendered:
        return (_R0_PLACEHOLDER,)
    return tuple(rendered)


def _render_event(event: Event) -> tuple[str, ...]:
    """Dispatch a single event to its surface renderer.

    Returns an empty tuple for events with no R1-S07 surface mapping.
    Reviewer note: the dispatch chain uses isinstance checks rather than
    a registry dict because pattern-matching on dataclasses is the
    canonical approach in Python 3.10+ and the event taxonomy is small
    + fixed (~18 event types at R1-S07).
    """
    if isinstance(event, HazardTriggered):
        return yob_surface.render_hazard(event)
    if isinstance(event, GameEnded):
        return yob_surface.render_terminal(event)
    if isinstance(event, PromptIssued) and event.kind == "same_setup":
        return yob_surface.render_same_setup_prompt()
    if isinstance(event, PromptIssued) and event.kind == "instructions":
        return yob_surface.render_instructions_prompt()
    if isinstance(event, InstructionsShown):
        return yob_surface.render_instructions(event)
    return ()


__all__ = ["lines_for_events"]
