"""Event → rendered-line translator for terminal + hazard events.

Per SC8 the engine emits structured events, never literal Yob strings.
This module sits BETWEEN the engine and the surface — it walks an event
stream and dispatches each renderable event to the appropriate Surface
function, accumulating the resulting lines into the
`Observation.rendered_lines` tuple.

R1-S07 shipped the terminal + hazard arms (HazardTriggered, GameEnded,
PromptIssued(kind="same_setup"/"instructions"), InstructionsShown). The
per-turn gameplay arms (SenseEmitted → "I SMELL A WUMPUS!" etc.,
LocationReported → "YOU ARE IN ROOM  <n>" + "TUNNELS LEAD TO  <a>  <b>  <c>")
were deferred at R4-S03 and land here — the engine emits the structured events
and this translator maps them to display lines through the surface (SC8).
Other event kinds (MoveResolved, ArrowFired, ...) still contribute zero lines.

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
    ArrowHitPlayer,
    ArrowMissed,
    Event,
    GameEnded,
    HazardTriggered,
    InstructionsShown,
    LocationReported,
    MoveAttempted,
    PromptIssued,
    SenseEmitted,
)
from wumpus.surfaces import yob as yob_surface

# PromptKind values the renderer maps to a single surface prompt line. Every
# kind the engine parks at must render so the prompt is observable before the
# engine awaits input (SC3). R1-S07 shipped same_setup + instructions; R1-S11
# adds the top-level action prompt, the WHERE TO? move-target prompt, and the
# two shoot sub-prompts (NO. OF ROOMS(1-5)? / ROOM #?) which were emitted at
# R1-S05 but never rendered (G3).
_RENDERED_PROMPT_KINDS: frozenset[str] = frozenset(
    {
        "action",
        "move_target",
        "shoot_path_len",
        "shoot_path_room",
        "same_setup",
        "instructions",
    }
)

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

    Events without a surface mapping (MoveResolved, ArrowFired, ...) contribute
    zero lines. SenseEmitted + LocationReported now render the per-turn
    gameplay lines (R1-S02-render). The shell's fallback to `("<placeholder>",)`
    only fires when the resulting tuple is empty AND the turn had no renderable
    events at all.
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
    if isinstance(event, SenseEmitted):
        # Per-turn sense line ("I SMELL A WUMPUS!" / "I FEEL A DRAFT" /
        # "BATS NEARBY!"). The kind→string mapping lives behind the surface
        # (SC8); rendering is downstream of emission — it does not change which
        # SenseEmitted events fire or their payloads.
        return (surface.sense_string(event.kind),)
    if isinstance(event, LocationReported):
        # Per-turn location lines ("YOU ARE IN ROOM  <n>" + "TUNNELS LEAD TO
        # <a>  <b>  <c>"). The surface owns the Yob literals + GW-BASIC numeric
        # spacing; the engine only forwards the already-emitted room +
        # adjacencies.
        return surface.render_location(event.room, event.adjacencies)
    if isinstance(event, ArrowMissed):
        # R1-S12 (G4): the arrow walked its path without hitting the wumpus or
        # the player. Render Yob's "MISSED" line through the surface (SC8). The
        # wumpus-hit WIN line and any out-of-arrows terminal render via the
        # GameEnded arm, so this arm renders ONLY the per-turn miss narration.
        return (surface.arrow_outcome_string("MISSED"),)
    if isinstance(event, ArrowHitPlayer):
        # R1-S12 (G4): the arrow's FINAL room was the player's room (Yob D11
        # self-shot). Render "OUCH! ARROW GOT YOU!" through the surface. The
        # arrow-count decrement / out-of-arrows terminal (if any) renders via
        # the ArrowCountChanged / GameEnded arms, so this arm renders ONLY the
        # per-turn self-shot narration.
        return (surface.arrow_outcome_string("SELF_SHOT"),)
    if isinstance(event, HazardTriggered):
        # Delegate to the module free function: it is defensive about
        # variant-config-driven hazard kinds outside the known set (returns
        # () rather than raising), and `YobSurface.hazard_name` wraps the same
        # table for the known kinds — so the rendered output is identical.
        return yob_surface.render_hazard(event)
    if isinstance(event, GameEnded):
        return yob_surface.render_terminal(event)
    if isinstance(event, MoveAttempted) and not event.accepted:
        # Off-graph move (G6): render Yob's "NOT POSSIBLE -" line. The engine
        # re-prompts WHERE TO? / the action prompt right after (a separate
        # PromptIssued event), so the rendered turn reads "NOT POSSIBLE -"
        # then the re-prompt. An accepted MoveAttempted renders nothing
        # (LocationReported carries the per-turn location lines).
        return yob_surface.render_off_graph_move()
    if isinstance(event, PromptIssued) and event.kind in _RENDERED_PROMPT_KINDS:
        # Every parked prompt renders through the Surface Protocol's
        # `prompt_text` so a non-Yob surface renders prompts without touching
        # this module (SC8). R1-S11 generalized this from the same_setup /
        # instructions special-cases to the full PromptKind set.
        return (surface.prompt_text(event.kind),)
    if isinstance(event, InstructionsShown):
        return yob_surface.render_instructions(event)
    return ()


__all__ = ["lines_for_events"]
