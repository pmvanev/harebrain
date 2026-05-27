"""R4-S05/R4-S06 property tests — the obfuscation-gap measurement (journey J2).

The surface seam is STRUCTURAL, not cosmetic. This is the validity proof of the
obfuscation-gap measurement: ANY non-Yob surface and the default `YobSurface`,
run from the SAME seed with translation-equivalent player inputs, produce an
IDENTICAL internal trajectory — equal `internal_state_hash` AND equal
`rng_cursor` on every emitted event at every turn. Only the bytes the player
reads differ (the rendered output genuinely diverges, proving real obfuscation).

R4-S06 generalizes the pairing: every property is parametrized over the
non-Yob surfaces `[MysterySurface(), FrenchSurface()]` via `_VARIANT_SURFACES`.
The SAME property body drives both — that reuse IS the surface-generality proof
(the R4-S05 seam was not Mystery-shaped: a second, independent, non-Mystery
surface satisfies the identical invariants with no special-casing). The Mystery
case keeps R4-S05 green; the French case lands R4-S06.

Why this proves SC9
-------------------
SC9: the surface never reads engine state and never consumes RNG. If a variant
surface drew from the engine's RNG (or branched the engine on a surface-form
decision), the paired `rng_cursor` sequences would DESYNC — a single extra draw
shifts every subsequent cursor. Equal cursors at every event is the falsifiable
proof that the variant surface is RNG-inert. Equal `internal_state_hash` proves
the internal World trajectory is surface-independent.

Honest paired driving (brief 3b)
---------------------------------
Both runs are driven from the SAME surface-independent *internal action plan*
(a tuple of `_Intent`s). Each intent is rendered into the respective surface's
input tokens VIA that surface's own `command_token` / `room_label` — the test
never peeks at engine internals to "fix up" divergence. A move intent names an
internal room id directly (1..20); the Yob run types its decimal label, the
Mystery run types its scrambled label, and both invert (via the engine's
surface-routed `room_id`) back to the SAME internal room id. So the two runs
express the same intent in two alphabets and must share the trajectory.

The gameplay strategy generates MOVE intents (the action prompt -> WHERE TO?
-> room-label two-step). Moves exhaustively exercise the engine's RNG paths —
wumpus startle on a bump, bat-teleport, off-graph re-prompt — so the
rng_cursor-equality claim is meaningful. Moves are issued only from the action
prompt and an off-graph move re-prompts WHERE TO? identically in both runs
(both surfaces invert the SAME room label to the SAME off-graph id). The SHOOT
path's equivalence is pinned by the dedicated clean-action-prompt shoot in the
R4_surface acceptance suite — see the risk-note discussion there: a bare
path-length COUNT is not a surface concept, so a property that interleaved
shoots after a possibly-off-graph move would conflate "bare count misread as a
room at WHERE TO?" with a surface bug. Keeping the property move-only is the
honest scoping (brief 3b: don't peek to fix up divergence).

Port-to-port: enters through the `Game(...)` driving port, asserts on the
public `_debug_events` (the engine-emission record the determinism suite also
treats as the observable). No engine internals are inspected.

Profile-controlled (matching `tests/property/test_determinism.py`): the `ci`
profile bounds the PR-gate cost; the `ci-nightly` profile lifts the example
count toward the brief's "100 seeds × 50 turns" nightly target.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from hypothesis import given, settings, strategies as st

from wumpus import FrenchSurface, Game, MysterySurface, YobSurface
from wumpus.events import Event
from wumpus.types import Surface


# The non-Yob surfaces the paired properties pair Yob AGAINST. R4-S05 shipped
# Mystery; R4-S06 adds French — a SECOND, independent, non-Mystery surface that
# must satisfy the identical invariants through the same property bodies. The
# parametrize id is the surface_id so a failure names which variant desynced.
_VARIANT_SURFACES: tuple[Surface, ...] = (MysterySurface(), FrenchSurface())


def _variant_id(surface: Surface) -> str:
    return surface.surface_id


# ---------------------------------------------------------------------------
# Internal action plan — a surface-independent sequence of intents.
# ---------------------------------------------------------------------------
#
# Each intent expresses WHAT the player wants in engine-internal terms (a room
# id, a shoot path of room ids, a Y/N answer). `render(surface)` turns the
# intent into the input token(s) for a specific surface, using ONLY that
# surface's public translation methods — never engine internals. Feeding the
# Yob-rendered tokens to a Yob run and the Mystery-rendered tokens to a Mystery
# run expresses the SAME intent in two alphabets.


@dataclass(frozen=True)
class _Intent:
    """A single surface-independent player intent."""

    kind: str  # "instructions_no" | "move"
    room: int = 0  # for "move": the target internal room id

    def render(self, surface: Surface) -> tuple[str, ...]:
        """Render this intent into the input token(s) for `surface`.

        Uses only the surface's PUBLIC translation methods (`command_token`,
        `room_label`) — the round-trip inverse the engine applies on the way
        in. This keeps the paired runs honest: the same internal intent, two
        alphabets, no engine-internal peeking."""
        if self.kind == "instructions_no":
            return (surface.command_token("NO"),)
        if self.kind == "move":
            # Two-step move: the MOVE token, then the target room's LABEL. An
            # off-graph target re-prompts WHERE TO? identically in both runs
            # (both surfaces invert the same label to the same off-graph id).
            return (surface.command_token("MOVE"), surface.room_label(self.room))
        raise AssertionError(f"unknown intent kind {self.kind!r}")


def _room_id_strategy() -> st.SearchStrategy[int]:
    """A target room id in the Yob 20-room dodecahedron range. Some targets
    are non-adjacent (off-graph) — those re-prompt identically in both runs,
    which is itself part of the trajectory equality."""
    return st.integers(min_value=1, max_value=20)


def _gameplay_intent() -> st.SearchStrategy[_Intent]:
    """A single move gameplay intent. Moves exercise the engine's RNG paths
    (startle, bat-teleport) and the off-graph re-prompt; the SHOOT path's
    equivalence is pinned by the dedicated acceptance shoot (see module
    docstring + the R4_surface risk note)."""
    return st.builds(_Intent, kind=st.just("move"), room=_room_id_strategy())


def _action_plan_strategy() -> st.SearchStrategy[tuple[_Intent, ...]]:
    """A full plan: answer the INSTRUCTIONS prompt with NO, then 0..12 gameplay
    intents. The leading instructions_no clears Yob's pre-game state in BOTH
    runs identically. The `ci` profile bounds example breadth; `ci-nightly`
    lifts it toward the brief's nightly target."""
    head = st.just(_Intent(kind="instructions_no"))
    body = st.lists(_gameplay_intent(), min_size=0, max_size=12).map(tuple)
    return st.tuples(head, body).map(lambda hb: (hb[0],) + hb[1])


def _seed_strategy() -> st.SearchStrategy[int]:
    return st.integers(min_value=0, max_value=(1 << 31) - 1)


def _drive(seed: int, plan: tuple[_Intent, ...], surface: Surface) -> list[Event]:
    """Drive a fresh `Game(seed=k, surface=...)` through `plan`, rendering each
    intent into `surface`'s input tokens. Return `Game._debug_events`.

    The yob cave is used so the real RNG hazards (startle, bat-teleport, arrow
    deflection) are exercised — making the rng_cursor-equality claim meaningful
    (a surface that touched RNG would desync the hazard draws)."""
    game = Game(seed=seed, surface=surface)
    for intent in plan:
        for token in intent.render(surface):
            game.step(token)
    return list(game._debug_events)


def _rendered_output(seed: int, plan: tuple[_Intent, ...], surface: Surface) -> str:
    """Drive a fresh game capturing the player-visible rendered transcript via
    a RendererSink — what the player actually reads. Used to prove the Mystery
    bytes genuinely differ from the Yob bytes."""
    import io

    from wumpus.sinks import RendererSink

    stream = io.StringIO()
    game = Game(seed=seed, surface=surface)
    game.subscribe(RendererSink(stream=stream, surface=surface))
    for intent in plan:
        for token in intent.render(surface):
            game.step(token)
    return stream.getvalue()


# ---------------------------------------------------------------------------
# Property 1 — paired runs share an identical internal_state_hash trajectory
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("variant_surface", _VARIANT_SURFACES, ids=_variant_id)
@given(seed=_seed_strategy(), plan=_action_plan_strategy())
@settings(deadline=None)
def test_paired_runs_have_identical_internal_state_hash(
    variant_surface: Surface, seed: int, plan: tuple[_Intent, ...]
) -> None:
    """For any (seed, internal action plan), the Yob and variant runs emit an
    identical `internal_state_hash` on every event at every turn. The surface
    is a pure output relabelling; the internal World trajectory is surface-
    independent (SC9). This IS the obfuscation-gap validity proof — and, run
    over BOTH Mystery and French, the surface-generality proof (R4-S06)."""
    variant = variant_surface.surface_id
    yob_events = _drive(seed, plan, YobSurface())
    variant_events = _drive(seed, plan, variant_surface)

    assert len(yob_events) == len(variant_events), (
        f"Paired runs produced different event counts at seed={seed}: "
        f"yob={len(yob_events)}, {variant}={len(variant_events)}. The internal "
        f"trajectories diverged — the surface is not purely cosmetic."
    )
    for index, (yob_event, variant_event) in enumerate(zip(yob_events, variant_events)):
        assert yob_event.internal_state_hash == variant_event.internal_state_hash, (
            f"Event {index} ({type(yob_event).__name__}) internal_state_hash "
            f"diverged between the Yob and {variant} runs at seed={seed}: "
            f"yob={yob_event.internal_state_hash!r}, "
            f"{variant}={variant_event.internal_state_hash!r}. The surface "
            f"altered the internal trajectory — SC9 violated."
        )


# ---------------------------------------------------------------------------
# Property 2 — the Mystery surface consumes no engine RNG (rng_cursor equality)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("variant_surface", _VARIANT_SURFACES, ids=_variant_id)
@given(seed=_seed_strategy(), plan=_action_plan_strategy())
@settings(deadline=None)
def test_variant_surface_consumes_no_engine_rng(
    variant_surface: Surface, seed: int, plan: tuple[_Intent, ...]
) -> None:
    """For any (seed, internal action plan), the Yob and variant runs emit an
    identical `rng_cursor` on every event. A surface that drew from the
    engine's RNG would shift every subsequent cursor (one extra draw desyncs
    the whole tail), so equal cursors at every event is the falsifiable proof
    the variant surface is RNG-inert (SC9). Run over Mystery AND French."""
    variant = variant_surface.surface_id
    yob_events = _drive(seed, plan, YobSurface())
    variant_events = _drive(seed, plan, variant_surface)

    assert len(yob_events) == len(variant_events), (
        f"Paired runs produced different event counts at seed={seed}: "
        f"yob={len(yob_events)}, {variant}={len(variant_events)}."
    )
    for index, (yob_event, variant_event) in enumerate(zip(yob_events, variant_events)):
        assert yob_event.rng_cursor == variant_event.rng_cursor, (
            f"Event {index} ({type(yob_event).__name__}) rng_cursor diverged "
            f"between the Yob and {variant} runs at seed={seed}. The {variant} "
            f"surface consumed engine RNG (a draw desynced the cursor) — "
            f"SC9 violated."
        )


# ---------------------------------------------------------------------------
# Property 3 — the Mystery surface genuinely obfuscates the rendered bytes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("variant_surface", _VARIANT_SURFACES, ids=_variant_id)
@given(seed=_seed_strategy(), plan=_action_plan_strategy())
@settings(deadline=None)
def test_variant_rendered_output_differs_from_yob(
    variant_surface: Surface, seed: int, plan: tuple[_Intent, ...]
) -> None:
    """The variant run's player-visible rendered transcript must NOT equal the
    Yob run's. Equal internal trajectory + DIVERGENT rendered bytes is exactly
    what "the seam is structural, not cosmetic" means — the variant surface is
    actually relabelling (Mystery obfuscates, French translates), not a no-op
    clone of Yob.

    Even the shortest plan (just the instructions_no answer) renders the banner
    + opening room + first prompt, all of which the variant surface relabels, so
    the transcripts always differ."""
    variant = variant_surface.surface_id
    yob_output = _rendered_output(seed, plan, YobSurface())
    variant_output = _rendered_output(seed, plan, variant_surface)

    assert variant_output != yob_output, (
        f"The {variant} rendered output is byte-identical to the Yob output at "
        f"seed={seed} — the {variant} surface is not relabelling anything. The "
        f"seam is cosmetic, not structural."
    )
    # Stronger: the variant output must not contain Yob's canonical action
    # prompt (it should render its own prompt instead). This guards against a
    # partial relabelling that leaves engine-emitted prompts in Yob bytes.
    assert "SHOOT OR MOVE (S-M)?" not in variant_output, (
        f"The {variant} rendered output leaked Yob's verbatim action prompt at "
        f"seed={seed} — the surface relabelling is incomplete."
    )
