"""R4 surface-seam acceptance step definitions (R4-S03).

R4-S03 lands the `Surface` Protocol (Tier A5 shape) + the `YobSurface`
implementation that consolidates every surface-form string the engine emits
behind one clean interface. The engine reads strings from the surface at the
output boundary; the surface never reads engine state and never consumes RNG
(SC8 / SC9).

Per the crafter mandate: port-to-port testing — these scenarios enter through
driving ports (`YobSurface(...)` public methods, the structural Surface
Protocol, and the verb round-trip contract) and assert observable outcomes
(rendered strings, Protocol membership, inverse-translation completeness).
They do not introspect private surface internals.

AC scenario 1 is REDEFINED per ADR-011: the 10 BASIC byte-parity fixtures do
not exist. The regression net for "did the strings survive the move" is the
R1 yob-fidelity acceptance suite + the determinism golden master, both of
which run in the same `pytest --ignore=tests/subprocess` invocation as this
file. Scenario 1 here asserts the surface seam preserves Yob's canonical
strings byte-for-byte (the structural Yob-fidelity claim ADR-011 leaves in
place); the cross-suite green bar is enforced by running the full suite.
"""

from __future__ import annotations

import io
from typing import get_args

from pytest_bdd import given, scenarios, then, when

from wumpus import FrenchSurface, Game, GameStarted, MysterySurface
from wumpus.sinks import RendererSink
from wumpus.types import CommandVerb, Surface
from wumpus.surfaces.yob import YobSurface

# Bind the .feature file. Path is relative to this step-defs file's parent.
scenarios("../features/R4_surface.feature")


# The canonical Yob strings R4-S04's grep audit will look for; scenario 1
# asserts YobSurface still emits each one byte-for-byte after the refactor.
_CANONICAL_YOB_STRINGS: tuple[str, ...] = (
    "I SMELL A WUMPUS!",
    "I FEEL A DRAFT",
    "BATS NEARBY!",
    "HA HA HA - YOU LOSE!",
    "HEE HEE HEE - THE WUMPUS'LL GETCHA NEXT TIME!!",
    "AHA! YOU GOT THE WUMPUS!",
    "NO. OF ROOMS(1-5)?",
    "SHOOT OR MOVE (S-M)?",
    "WHERE TO?",
    "ROOM #?",
    "...OOPS! BUMPED A WUMPUS!",
    "YYYIIIIEEEE . . . FELL IN PIT",
    "ZAP--SUPER BAT SNATCH! ELSEWHEREVILLE FOR YOU!",
    "TSK TSK TSK- WUMPUS GOT YOU!",
    "OUCH! ARROW GOT YOU!",
    "MISSED",
    "ARROWS AREN'T THAT CROOKED - TRY ANOTHER ROOM",
    "SAME SET-UP (Y-N)?",
    "INSTRUCTIONS (Y-N)?",
)


# ---------------------------------------------------------------------------
# Scenario 1 — the Yob-fidelity regression net survives the refactor
# ---------------------------------------------------------------------------


@given(
    "the surface refactor has landed (Surface Protocol + YobSurface)",
    target_fixture="r4s03_surface",
)
def _r4s03_surface() -> YobSurface:
    surface = YobSurface()
    # The surface MUST structurally satisfy the Surface Protocol (duck-typed,
    # composition over inheritance per ADR-001).
    bound: Surface = surface
    assert bound is surface
    return surface


@when(
    "the R1 yob-fidelity acceptance suite and the determinism golden master are re-run"
)
def _r4s03_suites_rerun() -> None:
    # The cross-suite green bar is enforced by the FULL non-subprocess pytest
    # run (the R1 acceptance suite + golden master collect in the same
    # invocation as this file). This step documents the contract; the
    # byte-for-byte string survival is asserted in the Then below.
    pass


@then("both suites pass without modification")
def _r4s03_suites_pass(r4s03_surface: YobSurface) -> None:
    # Falsifiable proxy: the engine's render path (which both the R1 acceptance
    # suite and the golden master exercise indirectly) still renders Yob's
    # terminal/hazard strings, AND the new YobSurface object form agrees with
    # the legacy free-function render path byte-for-byte. If the surface
    # refactor had silently changed a string, these would diverge.
    from wumpus.events import SCHEMA_VERSION, GameEnded, HazardTriggered
    from wumpus.surfaces import yob as yob_module

    hazard = HazardTriggered(
        schema_version=SCHEMA_VERSION,
        turn=0,
        surface_variant="<placeholder>",
        internal_state_hash="",
        rng_cursor="",
        kind="WUMPUS",
        room=1,
    )
    # Legacy free-function render path (used by render_terminal / RendererSink)
    # and the new object-form method must agree.
    assert yob_module.render_hazard(hazard) == (r4s03_surface.hazard_name("WUMPUS"),), (
        "YobSurface.hazard_name diverged from the legacy render_hazard path."
    )

    terminal = GameEnded(
        schema_version=SCHEMA_VERSION,
        turn=0,
        surface_variant="<placeholder>",
        internal_state_hash="",
        rng_cursor="",
        outcome="wumpus_shot",
        message_kind="win",
        final_snapshot=None,
    )
    assert yob_module.render_terminal(terminal) == (
        "AHA! YOU GOT THE WUMPUS!",
        "HEE HEE HEE - THE WUMPUS'LL GETCHA NEXT TIME!!",
    ), "The legacy terminal render path changed — Yob-fidelity regression."


@then("YobSurface still emits every canonical Yob string byte-for-byte")
def _r4s03_canonical_strings_survive(r4s03_surface: YobSurface) -> None:
    """Collect every string the YobSurface can emit and assert the canonical
    Yob set is a subset. This is the structural Yob-fidelity claim ADR-011
    leaves in place after dropping BASIC byte-parity."""
    emitted: set[str] = set()
    # Prompts.
    for kind in (
        "action",
        "move_target",
        "shoot_path_len",
        "shoot_path_room",
        "same_setup",
        "instructions",
    ):
        emitted.add(r4s03_surface.prompt_text(kind))
    # Senses.
    for sense_kind in ("WUMPUS_SMELL", "PIT_DRAFT", "BAT_NEARBY"):
        emitted.add(r4s03_surface.sense_string(sense_kind))
    # Hazards + terminal/miss/self-shot/swap-tag strings, plus the crooked line.
    for hazard_kind in ("WUMPUS", "PIT", "BAT"):
        emitted.add(r4s03_surface.hazard_name(hazard_kind))
    emitted.update(r4s03_surface.terminal_strings())
    missing = [s for s in _CANONICAL_YOB_STRINGS if s not in emitted]
    assert not missing, (
        "YobSurface no longer emits these canonical Yob strings after the "
        f"surface refactor: {missing!r}. SC8 / Yob-fidelity break."
    )


# ---------------------------------------------------------------------------
# Scenario 2 — Surface interface covers every surface-form string
# ---------------------------------------------------------------------------


@given(
    "a YobSurface instance bound to the Surface Protocol",
    target_fixture="r4s03_bound_surface",
)
def _r4s03_bound_surface() -> YobSurface:
    surface = YobSurface()
    bound: Surface = surface  # structural Protocol satisfaction
    assert bound is surface
    return surface


@then(
    "it exposes room_label, sense_string, hazard_name, command_token, "
    "command_parse, prompt_text, and instructions_block"
)
def _r4s03_method_set(r4s03_bound_surface: YobSurface) -> None:
    for method in (
        "room_label",
        "sense_string",
        "hazard_name",
        "command_token",
        "command_parse",
        "prompt_text",
        "instructions_block",
    ):
        assert callable(getattr(r4s03_bound_surface, method, None)), (
            f"YobSurface is missing the {method!r} Surface-Protocol method "
            f"(AC scenario 2 enumerates the full method set)."
        )
    assert isinstance(r4s03_bound_surface.surface_id, str), (
        "YobSurface must carry a `surface_id` str attribute (Surface Protocol)."
    )
    assert r4s03_bound_surface.surface_id == "yob", (
        f"YobSurface.surface_id was {r4s03_bound_surface.surface_id!r}; expected 'yob'."
    )


@then("every prompt the engine awaits has a non-empty prompt_text rendering")
def _r4s03_prompts_non_empty(r4s03_bound_surface: YobSurface) -> None:
    # PromptKind is the engine's discriminator of every prompt it awaits; every
    # value MUST render to a non-empty string (no silent placeholder gaps).
    from wumpus.types import PromptKind

    for kind in get_args(PromptKind):
        rendered = r4s03_bound_surface.prompt_text(kind)
        assert isinstance(rendered, str) and rendered, (
            f"prompt_text({kind!r}) rendered empty/non-str: {rendered!r}. "
            f"Every PromptKind must have a surface rendering (SC8)."
        )


@then("every sense and hazard kind the engine emits has a non-empty surface rendering")
def _r4s03_senses_hazards_non_empty(r4s03_bound_surface: YobSurface) -> None:
    for sense_kind in ("WUMPUS_SMELL", "PIT_DRAFT", "BAT_NEARBY"):
        rendered = r4s03_bound_surface.sense_string(sense_kind)
        assert isinstance(rendered, str) and rendered, (
            f"sense_string({sense_kind!r}) rendered empty/non-str: {rendered!r}."
        )
    for hazard_kind in ("WUMPUS", "PIT", "BAT"):
        rendered = r4s03_bound_surface.hazard_name(hazard_kind)
        assert isinstance(rendered, str) and rendered, (
            f"hazard_name({hazard_kind!r}) rendered empty/non-str: {rendered!r}."
        )


# ---------------------------------------------------------------------------
# Scenario 3 — command translation round-trips for every verb
# ---------------------------------------------------------------------------


@given(
    "a YobSurface instance bound to the Surface Protocol for the round-trip",
    target_fixture="r4s03_roundtrip_surface",
)
def _r4s03_roundtrip_surface_unused() -> YobSurface:  # pragma: no cover
    # Kept distinct so the round-trip scenario can reuse the bound-surface
    # Given if pytest-bdd step-text dedup ever changes; the active binding is
    # the shared "a YobSurface instance bound to the Surface Protocol" Given.
    return YobSurface()


@when(
    "command_parse(command_token(verb)) is invoked for every CommandVerb",
    target_fixture="r4s03_roundtrip_results",
)
def _r4s03_invoke_roundtrip(
    r4s03_bound_surface: YobSurface,
) -> dict[str, str]:
    """For every CommandVerb, token-encode then parse, recording the parsed
    verb. The contract `command_parse(command_token(v)).verb == v` is the
    inverse-translation completeness AC."""
    results: dict[str, str] = {}
    for verb in get_args(CommandVerb):
        token = r4s03_bound_surface.command_token(verb)
        assert isinstance(token, str) and token, (
            f"command_token({verb!r}) must be a non-empty str; got {token!r}."
        )
        results[verb] = r4s03_bound_surface.command_parse(token).verb
    return results


@then("the result equals the original verb")
def _r4s03_roundtrip_identity(
    r4s03_roundtrip_results: dict[str, str],
) -> None:
    verbs = get_args(CommandVerb)
    assert verbs, "CommandVerb enumerates no verbs; the round-trip is vacuous."
    for verb, parsed_verb in r4s03_roundtrip_results.items():
        assert parsed_verb == verb, (
            f"command_parse(command_token({verb!r})).verb returned "
            f"{parsed_verb!r}; inverse-translation completeness (AC scenario 3) "
            f"violated."
        )
    # Tokens must be distinguishable per verb (no two verbs share a token —
    # else the inverse would be ambiguous). This guards the MEDIUM integration
    # risk in A5 ("two distinct verbs must produce distinguishable tokens").
    surface = YobSurface()
    tokens = [surface.command_token(v) for v in verbs]
    assert len(set(tokens)) == len(tokens), (
        f"YobSurface command tokens are not distinct across verbs: {tokens!r}. "
        f"Ambiguous tokens break inverse-translation."
    )


# ---------------------------------------------------------------------------
# R4-S05 — obfuscation-gap measurement (journey J2)
#
# Paired Yob/Mystery runs from the same seed with translation-equivalent
# inputs share an identical internal trajectory (equal internal_state_hash +
# rng_cursor at every turn), but the rendered bytes genuinely differ. These
# scenarios drive through the `Game(...)` driving port (port-to-port) and assert
# on the public `_debug_events` + the RendererSink transcript boundary. The
# property suite (`tests/property/test_obfuscation_gap.py`) explores the
# equivalence classes; these scenarios pin one canonical example walkthrough.
# ---------------------------------------------------------------------------

# A fixed internal action plan rendered into BOTH surfaces' input alphabets.
# Intent: answer INSTRUCTIONS=NO, then — cleanly from the action prompt — a
# SHOOT of path length 2 to internal rooms [2, 3]. Rendered VIA each surface's
# own command_token / room_label — no engine-internal peeking (brief 3b). The
# shoot exercises the arrow walk + the wumpus startle RNG, so the trajectory
# equality is a meaningful SC9 proof (a surface that touched RNG would desync
# the startle draw and the rng_cursor would diverge).
#
# Why a shoot (not a move) for the canonical example: a shoot issued from the
# action prompt is interpreted identically by both surfaces (SHOOT token ->
# SHOOT verb; bare path-length count; room labels invert to the same ids).
# A move CAN go off-graph and leave the engine at WHERE TO?, where a following
# bare count would be (mis)read as a Yob room but rejected by Mystery — that is
# the risk-note asymmetry: a bare path-length COUNT is not a surface concept.
# We therefore pin the SHOOT path here (clean action-prompt state) and cover
# the MOVE equivalence (incl. off-graph re-prompts + hazard RNG) in the
# property suite (tests/property/test_obfuscation_gap.py).
_R4S05_SEED: int = 1973


def _render_plan(surface: Surface) -> list[str]:
    """Render the canonical R4-S05 internal action plan into `surface`'s input
    tokens using only the surface's public translation methods."""
    return [
        surface.command_token("NO"),  # answer INSTRUCTIONS prompt
        surface.command_token("SHOOT"),  # at the action prompt -> shoot
        "2",  # path length (a bare count — surface-independent)
        surface.room_label(2),  # internal room ids 2, 3 as the arrow path
        surface.room_label(3),
    ]


def _drive_paired(surface: Surface) -> Game:
    game = Game(seed=_R4S05_SEED, surface=surface)
    for token in _render_plan(surface):
        game.step(token)
    return game


def _rendered_transcript(surface: Surface) -> str:
    stream = io.StringIO()
    game = Game(seed=_R4S05_SEED, surface=surface)
    game.subscribe(RendererSink(stream=stream, surface=surface))
    for token in _render_plan(surface):
        game.step(token)
    return stream.getvalue()


@given(
    "the same seed and a sequence of internal action intents",
    target_fixture="r4s05_seed",
)
def _r4s05_seed() -> int:
    return _R4S05_SEED


@when(
    "the engine is driven once via the Yob surface and once via the Mystery "
    "surface with translation-equivalent inputs",
    target_fixture="r4s05_paired",
)
def _r4s05_paired(r4s05_seed: int) -> dict[str, object]:
    yob_game = _drive_paired(YobSurface())
    mystery_game = _drive_paired(MysterySurface())
    return {
        "yob_events": list(yob_game._debug_events),
        "mystery_events": list(mystery_game._debug_events),
        "yob_transcript": _rendered_transcript(YobSurface()),
        "mystery_transcript": _rendered_transcript(MysterySurface()),
    }


@then("the emitted internal_state_hash sequence is identical at every turn")
def _r4s05_hash_identical(r4s05_paired: dict[str, object]) -> None:
    yob_events = r4s05_paired["yob_events"]
    mystery_events = r4s05_paired["mystery_events"]
    assert len(yob_events) == len(mystery_events), (
        f"Paired runs produced different event counts: yob={len(yob_events)}, "
        f"mystery={len(mystery_events)} — internal trajectories diverged."
    )
    for index, (yob_event, mystery_event) in enumerate(zip(yob_events, mystery_events)):
        assert yob_event.internal_state_hash == mystery_event.internal_state_hash, (
            f"Event {index} ({type(yob_event).__name__}) internal_state_hash "
            f"diverged: yob={yob_event.internal_state_hash!r}, "
            f"mystery={mystery_event.internal_state_hash!r}. SC9 violated."
        )


@then("the emitted rng_cursor sequence is identical at every turn")
def _r4s05_rng_identical(r4s05_paired: dict[str, object]) -> None:
    yob_events = r4s05_paired["yob_events"]
    mystery_events = r4s05_paired["mystery_events"]
    assert len(yob_events) == len(mystery_events)
    for index, (yob_event, mystery_event) in enumerate(zip(yob_events, mystery_events)):
        assert yob_event.rng_cursor == mystery_event.rng_cursor, (
            f"Event {index} ({type(yob_event).__name__}) rng_cursor diverged — "
            f"the Mystery surface consumed engine RNG. SC9 violated."
        )


@then("the rendered player-visible output of the Mystery run differs from the Yob run")
def _r4s05_rendered_differs(r4s05_paired: dict[str, object]) -> None:
    yob_transcript = r4s05_paired["yob_transcript"]
    mystery_transcript = r4s05_paired["mystery_transcript"]
    assert mystery_transcript != yob_transcript, (
        "The Mystery rendered transcript is byte-identical to the Yob one — "
        "the surface is cosmetic, not obfuscating."
    )
    assert "SHOOT OR MOVE (S-M)?" not in mystery_transcript, (
        "The Mystery transcript leaked Yob's verbatim action prompt — the "
        "surface relabelling is incomplete."
    )


# ---------------------------------------------------------------------------
# R4-S06 — surface-generality smoke (FrenchSurface drops in, no engine changes)
#
# A SECOND, non-Mystery surface (a real French translation) drops into the SAME
# seam R4-S05 built, with NO engine changes, and the SAME structural equality
# holds: a paired Yob/French run from the same seed with translation-equivalent
# inputs shares an identical internal trajectory (equal internal_state_hash +
# rng_cursor every turn), while the rendered bytes genuinely differ. The header
# records surface_id="french". These reuse the canonical R4-S05 action plan
# (`_render_plan`) and helpers (`_drive_paired`, `_rendered_transcript`), which
# already accept any Surface — that reuse is itself part of the generality proof
# (the same driving code drives French without modification). The property suite
# (tests/property/test_obfuscation_gap.py, now parametrized over Mystery AND
# French) explores the equivalence classes; these pin one canonical example.
# ---------------------------------------------------------------------------


@given(
    "a Game driven via the French surface",
    target_fixture="r4s06_french_started",
)
def _r4s06_french_started() -> GameStarted:
    """Drive a fresh French Game through the canonical plan and return the
    GameStarted event from its emission record (the ledger header)."""
    game = _drive_paired(FrenchSurface())
    started = next(
        event for event in game._debug_events if isinstance(event, GameStarted)
    )
    return started


@then('the GameStarted header records surface_id "french"')
def _r4s06_header_surface_id(r4s06_french_started: GameStarted) -> None:
    assert r4s06_french_started.surface_id == "french", (
        f"GameStarted.surface_id was {r4s06_french_started.surface_id!r}; "
        f"expected 'french'. The French surface's variant id is not recorded "
        f'in the ledger header — the demo target (surface_variant="french") '
        f"is not met."
    )


@when(
    "the engine is driven once via the Yob surface and once via the French "
    "surface with translation-equivalent inputs",
    target_fixture="r4s06_paired",
)
def _r4s06_paired(r4s05_seed: int) -> dict[str, object]:
    yob_game = _drive_paired(YobSurface())
    french_game = _drive_paired(FrenchSurface())
    return {
        "yob_events": list(yob_game._debug_events),
        "french_events": list(french_game._debug_events),
        "yob_transcript": _rendered_transcript(YobSurface()),
        "french_transcript": _rendered_transcript(FrenchSurface()),
    }


@then("the Yob and French internal_state_hash sequence is identical at every turn")
def _r4s06_hash_identical(r4s06_paired: dict[str, object]) -> None:
    yob_events = r4s06_paired["yob_events"]
    french_events = r4s06_paired["french_events"]
    assert len(yob_events) == len(french_events), (
        f"Paired runs produced different event counts: yob={len(yob_events)}, "
        f"french={len(french_events)} — internal trajectories diverged. The "
        f"French surface altered the trajectory; the R4-S05 seam was "
        f"Mystery-shaped."
    )
    for index, (yob_event, french_event) in enumerate(zip(yob_events, french_events)):
        assert yob_event.internal_state_hash == french_event.internal_state_hash, (
            f"Event {index} ({type(yob_event).__name__}) internal_state_hash "
            f"diverged: yob={yob_event.internal_state_hash!r}, "
            f"french={french_event.internal_state_hash!r}. SC9 violated / the "
            f"seam is not surface-general."
        )


@then("the Yob and French rng_cursor sequence is identical at every turn")
def _r4s06_rng_identical(r4s06_paired: dict[str, object]) -> None:
    yob_events = r4s06_paired["yob_events"]
    french_events = r4s06_paired["french_events"]
    assert len(yob_events) == len(french_events)
    for index, (yob_event, french_event) in enumerate(zip(yob_events, french_events)):
        assert yob_event.rng_cursor == french_event.rng_cursor, (
            f"Event {index} ({type(yob_event).__name__}) rng_cursor diverged — "
            f"the French surface consumed engine RNG. SC9 violated."
        )


@then("the rendered player-visible output of the French run differs from the Yob run")
def _r4s06_rendered_differs(r4s06_paired: dict[str, object]) -> None:
    yob_transcript = r4s06_paired["yob_transcript"]
    french_transcript = r4s06_paired["french_transcript"]
    assert french_transcript != yob_transcript, (
        "The French rendered transcript is byte-identical to the Yob one — "
        "the French surface is not translating anything."
    )
    assert "SHOOT OR MOVE (S-M)?" not in french_transcript, (
        "The French transcript leaked Yob's verbatim action prompt — the "
        "French translation is incomplete."
    )
