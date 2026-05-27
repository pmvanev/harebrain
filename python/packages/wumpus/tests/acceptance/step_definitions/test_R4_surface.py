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

from typing import get_args

from pytest_bdd import given, scenarios, then, when

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
