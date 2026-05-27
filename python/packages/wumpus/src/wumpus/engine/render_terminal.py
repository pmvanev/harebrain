"""Event → rendered-line translator for terminal + hazard events.

Per SC8 the engine emits structured events, never literal Yob strings.
This module sits BETWEEN the engine and the surface — it walks an event
stream and dispatches each renderable event to the appropriate Surface
function, accumulating the resulting lines into the
`Observation.rendered_lines` tuple.

R1-S07 shipped the terminal + hazard arms (HazardTriggered, GameEnded,
PromptIssued(kind="same_setup"/"instructions"), InstructionsShown). Other
event kinds yield `("<placeholder>",)` for backwards compatibility with R0's
render placeholder.

R4-S03 routes the dispatch through a `Surface`-Protocol OBJECT
(`YobSurface()` by default) instead of the module's free functions, so a
non-Yob surface (Mystery at R4-S05, French at R4-S06) drops into the same
seam without engine changes. The hazard / terminal / instructions arms still
delegate to the module free functions (which `YobSurface` itself wraps), so
the rendered output is byte-identical to R1-S07; the object hand-off is the
parametric seam the downstream surfaces need.

The module is intentionally stateless + pure (per ADR-001 "FP inside"):
free functions over event iterables; no `Renderer` class. The Game shell
calls `lines_for_events(events_emitted_this_turn, surface)` and passes the
result into the Observation it returns to the caller.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from wumpus.events import (
    Event,
    GameEnded,
    HazardTriggered,
    InstructionsShown,
    PromptIssued,
)
from wumpus.surfaces import yob as yob_surface

if TYPE_CHECKING:
    from wumpus.types import Surface

# R0 render placeholder. Events that have no R1-S07-shipped surface mapping
# fall through to this constant so the Observation contract remains stable.
_R0_PLACEHOLDER: str = "<placeholder>"


def lines_for_events(
    events: Iterable[Event], surface: "Surface | None" = None
) -> tuple[str, ...]:
    """Translate `events` (typically the events emitted by a single
    `Game.step`) into rendered lines via the active surface.

    `surface` is the Surface-Protocol object the engine renders through; when
    omitted it defaults to a `YobSurface()` (the only surface that ships
    today), preserving the R1-S09 call sites that pass no surface.

    Order semantics: lines appear in emission order — i.e., the first
    event's lines come first. The function does NOT collapse duplicates;
    if two HazardTriggered events fire in one turn (theoretically
    possible during a bat→pit chain), both reason lines appear.

    Events without a surface mapping (MoveResolved, SenseEmitted,
    LocationReported, ArrowFired, ...) contribute zero lines. The shell's
    fallback to `("<placeholder>",)` only fires when the resulting tuple
    is empty AND the turn had no renderable events at all.
    """
    active_surface = surface if surface is not None else _default_surface()
    rendered: list[str] = []
    for event in events:
        rendered.extend(_render_event(event, active_surface))
    if not rendered:
        return (_R0_PLACEHOLDER,)
    return tuple(rendered)


def _default_surface() -> "Surface":
    """Lazily build the default YobSurface. Imported inside the function to
    avoid a module-load cycle (`wumpus.surfaces.yob` imports `wumpus.types`,
    which this module type-checks against)."""
    from wumpus.surfaces.yob import YobSurface

    return YobSurface()


def _render_event(event: Event, surface: "Surface") -> tuple[str, ...]:
    """Dispatch a single event to the active surface's renderer.

    Returns an empty tuple for events with no surface mapping. Hazard /
    terminal / instructions arms delegate to the YobSurface module free
    functions (which take the structured event); the prompt arms route
    through the Surface Protocol's `prompt_text` so a non-Yob surface
    renders prompts without touching this module.
    """
    if isinstance(event, HazardTriggered):
        # Delegate to the module free function: it is defensive about
        # variant-config-driven hazard kinds outside the known set (returns
        # () rather than raising), and `YobSurface.hazard_name` wraps the same
        # table for the known kinds — so the rendered output is identical.
        return yob_surface.render_hazard(event)
    if isinstance(event, GameEnded):
        return yob_surface.render_terminal(event)
    if isinstance(event, PromptIssued) and event.kind == "same_setup":
        return (surface.prompt_text("same_setup"),)
    if isinstance(event, PromptIssued) and event.kind == "instructions":
        return (surface.prompt_text("instructions"),)
    if isinstance(event, InstructionsShown):
        return yob_surface.render_instructions(event)
    return ()


__all__ = ["lines_for_events"]
