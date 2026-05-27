"""R4 variant + surface acceptance step definitions (R4-S01).

R4-S01 ships the parametric `VariantConfig` type (Yob defaults from the
no-args constructor), cave-gen parameterization by the config's counts, the
`Game(seed=k, variant=...)` constructor parameter, the structural
`GameStarted.variant_config`, and the arrow_count→out-of-arrows wiring.

Per the crafter mandate: port-to-port testing — these scenarios enter through
driving ports (`VariantConfig(...)`, `Game(...)`, `Game.snapshot()`,
`JsonlSink` ledger lines) and assert on observable outcomes (config field
values, emitted GameEnded events, ledger JSON, snapshot World shape). They do
not introspect private engine internals.

The CRITICAL constraint (goals.md § Goal 2, SC: "no variant changes the
internal state schema") is the scenario-4 canary: `wumpus_count=2` widens the
`World.wumpus_rooms` TUPLE to length 2, but adds NO field to World/Snapshot.
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
from typing import Any

from pytest_bdd import given, scenarios, then, when

from wumpus import Game, VariantConfig
from wumpus.events import ArrowMissed, GameEnded
from wumpus.sinks import InMemorySink, JsonlSink
from wumpus.types import World

# Bind the .feature file. Path is relative to this step-defs file's parent.
scenarios("../features/R4_variant_surface.feature")


# ---------------------------------------------------------------------------
# Forced-miss helper — reuses the R1-S06 _from_world + scripted-RNG pattern.
# A pinned World with the player and wumpus in non-adjacent rooms, plus a
# 1-room path that lands the arrow somewhere that is neither the wumpus nor
# the player → a deterministic MISS. The startle draw (randint(1, 4)) is
# scripted to K=4 (stay-put) so the miss does not become eaten_after_bump.
# Each miss decrements World.arrows by 1; after `arrow_count` misses the
# decrement reaches 0 → GameEnded(out_of_arrows).
# ---------------------------------------------------------------------------


class _ScriptedStayRandom:
    """RNG double scripting an unbounded sequence of K=4 (wumpus stays-put)
    startle draws, so every arrow miss is a plain miss (never eaten). Other
    RNG methods are intentionally absent — accessing one raises immediately,
    catching engine RNG consumption the slice did not script for."""

    def randint(self, a: int, b: int) -> int:
        # The only randint the miss path draws is the FNC(0) startle on (1, 4).
        assert (a, b) == (1, 4), f"Unexpected randint range ({a}, {b})."
        return 4  # stay-put

    def getstate(self) -> tuple[Any, ...]:
        return ("scripted_stay_random",)


def _miss_world(*, arrows: int) -> World:
    """Pin a shoot geometry where a 1-room path [7] from room 8 misses.

    Player at 8, wumpus parked at 17 (8→7 is a tunnel; 7 is neither the
    wumpus's room nor the player's). Hazards parked far from the path rooms
    so nothing fires incidentally."""
    return World(
        player_room=8,
        wumpus_rooms=(17,),
        pit_rooms=(11, 13),
        bat_rooms=(15, 19),
        arrows=arrows,
        turn=0,
        alive=True,
        pending_prompt=None,
        pending_arrow_path=(),
    )


def _drive_three_misses(*, arrows: int) -> list[Any]:
    """Drive three shoot-and-miss cycles on a pinned World seeded with
    `arrows`. Returns every event emitted across the three shots."""
    game = Game._from_world(_miss_world(arrows=arrows), seed=0)
    game._random = _ScriptedStayRandom()  # type: ignore[assignment]
    sink = InMemorySink()
    game.subscribe(sink)
    pre = len(sink.events)
    for _ in range(3):
        if not game.world_state().alive:
            break
        game.step("S")
        game.step("1")  # NO. OF ROOMS = 1
        game.step("7")  # slot 1 → arrow walks to room 7 → miss
    return sink.events[pre:]


# ---------------------------------------------------------------------------
# Scenario 1 — VariantConfig() yields Yob 1973 defaults
# ---------------------------------------------------------------------------


@given(
    "a VariantConfig constructed with no arguments",
    target_fixture="r4s01_default_config",
)
def _r4s01_default_config() -> VariantConfig:
    return VariantConfig()


@then(
    "room_count is 20, wumpus_count is 1, pit_count is 2, bat_count is 2"
)
def _r4s01_counts(r4s01_default_config: VariantConfig) -> None:
    cfg = r4s01_default_config
    assert (cfg.room_count, cfg.wumpus_count, cfg.pit_count, cfg.bat_count) == (
        20,
        1,
        2,
        2,
    ), (
        f"Yob default counts wrong: room={cfg.room_count}, wumpus="
        f"{cfg.wumpus_count}, pit={cfg.pit_count}, bat={cfg.bat_count}."
    )


@then("arrow_count is 5, arrow_max_range is 5, wumpus_move_prob is 0.75")
def _r4s01_arrow_and_prob(r4s01_default_config: VariantConfig) -> None:
    cfg = r4s01_default_config
    assert (cfg.arrow_count, cfg.arrow_max_range, cfg.wumpus_move_prob) == (
        5,
        5,
        0.75,
    ), (
        f"Yob arrow/prob defaults wrong: arrow_count={cfg.arrow_count}, "
        f"arrow_max_range={cfg.arrow_max_range}, "
        f"wumpus_move_prob={cfg.wumpus_move_prob}."
    )


@then("escalation_rules is empty")
def _r4s01_escalation_empty(r4s01_default_config: VariantConfig) -> None:
    assert r4s01_default_config.escalation_rules == (), (
        f"escalation_rules default must be the empty tuple; got "
        f"{r4s01_default_config.escalation_rules!r}."
    )


# ---------------------------------------------------------------------------
# Scenario 2 — arrow_count variant changes the out-of-arrows terminal
# ---------------------------------------------------------------------------


@given(
    "Game(seed=42, variant=VariantConfig(arrow_count=3))",
    target_fixture="r4s01_arrow3_construction",
)
def _r4s01_arrow3_construction() -> Game:
    """Construct the real variant Game (proves arrow_count threads to
    World.arrows at construction) — the forced-miss geometry is pinned in
    the When step via the _from_world hatch so the misses are deterministic."""
    return Game(seed=42, variant=VariantConfig(arrow_count=3))


@when("the player misses three times", target_fixture="r4s01_three_miss_runs")
def _r4s01_three_miss(r4s01_arrow3_construction: Game) -> dict[str, list[Any]]:
    # The constructed variant Game seeds World.arrows from arrow_count=3.
    assert r4s01_arrow3_construction.world_state().arrows == 3, (
        "arrow_count=3 must thread to World.arrows at construction; got "
        f"{r4s01_arrow3_construction.world_state().arrows}."
    )
    return {
        "arrows_3": _drive_three_misses(arrows=3),
        "arrows_5": _drive_three_misses(arrows=5),
    }


@then("GameEnded(outcome=out_of_arrows) fires after the third miss")
def _r4s01_out_of_arrows_after_three(
    r4s01_three_miss_runs: dict[str, list[Any]],
) -> None:
    events = r4s01_three_miss_runs["arrows_3"]
    misses = [e for e in events if isinstance(e, ArrowMissed)]
    assert len(misses) == 3, (
        f"Expected exactly three ArrowMissed events with arrow_count=3; got "
        f"{len(misses)}."
    )
    ended = [e for e in events if isinstance(e, GameEnded)]
    assert ended, "No GameEnded fired after three misses with arrow_count=3."
    assert ended[-1].outcome == "out_of_arrows", (
        f"GameEnded.outcome was {ended[-1].outcome!r}; expected 'out_of_arrows'."
    )


@then(
    "the same scenario with default arrow_count=5 does NOT end after three misses"
)
def _r4s01_arrow5_survives_three(
    r4s01_three_miss_runs: dict[str, list[Any]],
) -> None:
    events = r4s01_three_miss_runs["arrows_5"]
    misses = [e for e in events if isinstance(e, ArrowMissed)]
    assert len(misses) == 3, (
        f"Expected three ArrowMissed events with arrow_count=5; got {len(misses)}."
    )
    out_of_arrows = [
        e
        for e in events
        if isinstance(e, GameEnded) and e.outcome == "out_of_arrows"
    ]
    assert not out_of_arrows, (
        "arrow_count=5 must still have arrows remaining after three misses; "
        f"got premature out_of_arrows: {out_of_arrows!r}."
    )


# ---------------------------------------------------------------------------
# Scenario 3 — VariantConfig is recorded structurally in GameStarted
# ---------------------------------------------------------------------------


@given(
    "Game(seed=42, variant=VariantConfig(arrow_count=3)) with a JsonlSink",
    target_fixture="r4s01_ledger_path",
)
def _r4s01_variant_with_jsonl(tmp_path: pathlib.Path) -> pathlib.Path:
    ledger_path = tmp_path / "variant_header.jsonl"
    sink = JsonlSink(ledger_path)
    # Toy-style header isolation is not available for variant cave-gen, so we
    # subscribe AFTER construction; the subscriber replays the historical
    # GameStarted as the first line. The pre-game InstructionsShown/PromptIssued
    # follow it, but the FIRST line is the GameStarted header.
    game = Game(seed=42, variant=VariantConfig(arrow_count=3))
    game.subscribe(sink)
    sink.close()
    del game
    return ledger_path


@when(
    "the first ledger line is read",
    target_fixture="r4s01_first_line_event",
)
def _r4s01_read_first_line(r4s01_ledger_path: pathlib.Path) -> dict[str, Any]:
    text = r4s01_ledger_path.read_text(encoding="utf-8")
    lines = [ln for ln in text.split("\n") if ln]
    assert lines, f"Ledger {r4s01_ledger_path!r} is empty."
    first = json.loads(lines[0])
    assert first["type"] == "GameStarted", (
        f"First ledger line type is {first.get('type')!r}; expected 'GameStarted'."
    )
    return first


@then("GameStarted.variant_config contains arrow_count=3 and room_count=20")
def _r4s01_variant_config_structural(
    r4s01_first_line_event: dict[str, Any],
) -> None:
    variant_config = r4s01_first_line_event["variant_config"]
    assert isinstance(variant_config, dict), (
        f"variant_config must be a dict; got {type(variant_config).__name__}."
    )
    assert variant_config.get("arrow_count") == 3, (
        f"variant_config.arrow_count was {variant_config.get('arrow_count')!r}; "
        f"expected 3 (the structural config, not the {{'name': 'yob'}} placeholder)."
    )
    assert variant_config.get("room_count") == 20, (
        f"variant_config.room_count was {variant_config.get('room_count')!r}; "
        f"expected 20."
    )


# ---------------------------------------------------------------------------
# Scenario 4 — Variants do not change the internal state schema (CANARY)
# ---------------------------------------------------------------------------


@given(
    "Game(seed=42, variant=VariantConfig(wumpus_count=2))",
    target_fixture="r4s01_two_wumpus_game",
)
def _r4s01_two_wumpus_game() -> Game:
    return Game(seed=42, variant=VariantConfig(wumpus_count=2))


@when("game.snapshot() is taken", target_fixture="r4s01_two_wumpus_snapshot")
def _r4s01_take_snapshot(r4s01_two_wumpus_game: Game) -> Any:
    return r4s01_two_wumpus_game.snapshot()


@then("snap.world.wumpus_rooms has length 2")
def _r4s01_wumpus_rooms_length_2(r4s01_two_wumpus_snapshot: Any) -> None:
    wumpus_rooms = r4s01_two_wumpus_snapshot.world.wumpus_rooms
    assert len(wumpus_rooms) == 2, (
        f"wumpus_count=2 must widen the wumpus_rooms TUPLE to length 2; got "
        f"{wumpus_rooms!r}."
    )


@then(
    "the snapshot's field set is identical to a wumpus_count=1 snapshot's field set"
)
def _r4s01_field_set_identical(r4s01_two_wumpus_snapshot: Any) -> None:
    """The no-schema-change canary: a wumpus_count=2 game's Snapshot + World
    must have the SAME field set as a wumpus_count=1 game's — only the
    wumpus_rooms tuple LENGTH differs, never the field SET (goals.md Goal 2:
    'two wumpuses means a list of length two, not a new field')."""
    one_wumpus_snapshot = Game(
        seed=42, variant=VariantConfig(wumpus_count=1)
    ).snapshot()

    two_snap_fields = {f.name for f in dataclasses.fields(r4s01_two_wumpus_snapshot)}
    one_snap_fields = {f.name for f in dataclasses.fields(one_wumpus_snapshot)}
    assert two_snap_fields == one_snap_fields, (
        f"Snapshot field set changed under wumpus_count=2.\n"
        f"  wumpus_count=2: {sorted(two_snap_fields)}\n"
        f"  wumpus_count=1: {sorted(one_snap_fields)}"
    )

    two_world_fields = {
        f.name for f in dataclasses.fields(r4s01_two_wumpus_snapshot.world)
    }
    one_world_fields = {f.name for f in dataclasses.fields(one_wumpus_snapshot.world)}
    assert two_world_fields == one_world_fields, (
        f"World field set changed under wumpus_count=2.\n"
        f"  wumpus_count=2: {sorted(two_world_fields)}\n"
        f"  wumpus_count=1: {sorted(one_world_fields)}"
    )
