"""Unit tests for `wumpus.surfaces.yob` — the R1-S07 terminal/hazard subset.

Per SC8 these tests are the canary that no Yob string drifts from the verbatim
table in `wumpus/docs/wumpus_python_goals.md` § Goal 1 "Messages — verbatim".
Each parametrized row pins one string-byte-for-byte; future surface changes
(R4-S03 full Protocol, R4-S05 Mystery surface, R4-S06 French surface) MUST
either preserve these strings (YobSurface) or be authored against a sibling
module.

Per the crafter mandate: port-to-port testing — these tests call the surface's
PUBLIC module functions (`render_terminal`, `render_hazard`,
`render_same_setup_prompt`), not internal helpers. The module IS the driving
port at the surface-seam scope.
"""

from __future__ import annotations

import pytest

from wumpus.events import SCHEMA_VERSION, GameEnded, HazardTriggered
from wumpus.surfaces import yob as yob_surface


# ---------------------------------------------------------------------------
# Test helpers — build minimal valid event payloads for the surface to render.
# ---------------------------------------------------------------------------


def _make_hazard(kind: str) -> HazardTriggered:
    return HazardTriggered(
        schema_version=SCHEMA_VERSION,
        turn=0,
        surface_variant="<placeholder>",
        internal_state_hash="",
        rng_cursor="",
        kind=kind,  # type: ignore[arg-type]
        room=1,
    )


def _make_terminal(outcome: str, message_kind: str) -> GameEnded:
    return GameEnded(
        schema_version=SCHEMA_VERSION,
        turn=0,
        surface_variant="<placeholder>",
        internal_state_hash="",
        rng_cursor="",
        outcome=outcome,  # type: ignore[arg-type]
        message_kind=message_kind,  # type: ignore[arg-type]
        final_snapshot=None,
    )


# ---------------------------------------------------------------------------
# YobSurface — hazard rendering
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kind, expected_line",
    [
        ("WUMPUS", "...OOPS! BUMPED A WUMPUS!"),
        ("PIT", "YYYIIIIEEEE . . . FELL IN PIT"),
        ("BAT", "ZAP--SUPER BAT SNATCH! ELSEWHEREVILLE FOR YOU!"),
    ],
)
def test_yob_surface_renders_hazard_kind_to_yob_verbatim_string(
    kind: str, expected_line: str
) -> None:
    """YobSurface.render_hazard renders each HazardTriggered.kind to its
    verbatim Yob line per the goals-doc § Goal 1 table. SC8 + SC2 contract:
    byte-exact preservation."""
    rendered = yob_surface.render_hazard(_make_hazard(kind))
    assert rendered == (expected_line,), (
        f"render_hazard({kind!r}) was {rendered!r}; expected {(expected_line,)!r}"
    )


# ---------------------------------------------------------------------------
# YobSurface — terminal rendering (outcome + win/lose swap)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "outcome, message_kind, expected_lines",
    [
        # Win: AHA + the SWAPPED win tag (HEE HEE HEE per D11).
        (
            "wumpus_shot",
            "win",
            (
                "AHA! YOU GOT THE WUMPUS!",
                "HEE HEE HEE - THE WUMPUS'LL GETCHA NEXT TIME!!",
            ),
        ),
        # Loss: eaten by wumpus after a bump.
        (
            "eaten_after_bump",
            "lose",
            ("TSK TSK TSK- WUMPUS GOT YOU!", "HA HA HA - YOU LOSE!"),
        ),
        # Loss: fell in a pit.
        (
            "fell_in_pit",
            "lose",
            ("YYYIIIIEEEE . . . FELL IN PIT", "HA HA HA - YOU LOSE!"),
        ),
        # Loss: out of arrows — no extra reason line, just the lose tag
        # (the prior ArrowMissed/ArrowCountChanged narrated the run-out).
        ("out_of_arrows", "lose", ("HA HA HA - YOU LOSE!",)),
    ],
)
def test_yob_surface_renders_terminal_outcome_to_yob_verbatim_lines(
    outcome: str, message_kind: str, expected_lines: tuple[str, ...]
) -> None:
    """YobSurface.render_terminal renders each (outcome, message_kind) pair
    to its verbatim Yob lines per the goals-doc § Goal 1 table.

    The win/lose swap (D11) is structural: the tag is chosen by
    `message_kind`, NOT by `outcome`. A win prints HEE HEE HEE; a loss
    prints HA HA HA. This is the recognition signal of the 1973 game."""
    rendered = yob_surface.render_terminal(_make_terminal(outcome, message_kind))
    assert rendered == expected_lines, (
        f"render_terminal({outcome!r}, {message_kind!r}) was {rendered!r}; "
        f"expected {expected_lines!r}"
    )


def test_yob_surface_same_setup_prompt_renders_yob_verbatim_string() -> None:
    """The post-terminal SAME SET-UP prompt renders to its verbatim Yob line."""
    rendered = yob_surface.render_same_setup_prompt()
    assert rendered == ("SAME SET-UP (Y-N)?",), (
        f"render_same_setup_prompt() was {rendered!r}; "
        f"expected ('SAME SET-UP (Y-N)?',)"
    )
