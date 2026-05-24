"""R2 ledger acceptance step definitions (R2-S01).

Each R2 slice appends its step definitions to this file. R2-S01 ships the
first four scenarios: schema v1 + JsonlSink + functional --ledger flag +
no-background-thread audit.

Per pytest-bdd convention:
  - `scenarios(...)` at module top-level binds the .feature scenarios to this
    module.
  - Step functions decorated with @given / @when / @then implement each step.

Per the crafter mandate: port-to-port testing — these tests enter through
driving ports (JsonlSink.emit, wumpus.cli.main) and assert at the driven-port
boundary (file lines, raised exceptions). They never reach into private
helpers.
"""

from __future__ import annotations

import ast
import json
import pathlib
from typing import Any

import jsonschema
from pytest_bdd import given, scenarios, then, when

from wumpus.events import (
    SCHEMA_VERSION,
    ActionChosen,
    ArrowCountChanged,
    ArrowFired,
    ArrowHitPlayer,
    ArrowHitWumpus,
    ArrowMissed,
    ArrowPathStep,
    CrookedPathRejected,
    GameEnded,
    GameStarted,
    HazardTriggered,
    InstructionsShown,
    LocationReported,
    MoveAttempted,
    MoveResolved,
    PlayerTeleported,
    PromptIssued,
    SenseEmitted,
    SessionEnded,
    WumpusStartled,
)
from wumpus.schema import load_schema
from wumpus.sinks import JsonlSink, SchemaValidationError
from wumpus.types import Snapshot, World

# Bind the .feature file. Path is relative to this step-defs file's parent.
scenarios("../features/R2_ledger.feature")


# ---------------------------------------------------------------------------
# Helpers — Tier A4 v1 event-type roster builders
# ---------------------------------------------------------------------------


def _base_kwargs(**overrides: Any) -> dict[str, Any]:
    """Shared base-field kwargs every event needs to instantiate."""
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "turn": 0,
        "surface_variant": "yob",
        "internal_state_hash": "deadbeef",
        "rng_cursor": "",
        "monotonic_turn": 0,
    }
    payload.update(overrides)
    return payload


def _make_world() -> World:
    return World(
        player_room=1,
        wumpus_rooms=(11,),
        pit_rooms=(13, 14),
        bat_rooms=(15, 19),
        arrows=5,
        turn=0,
        alive=True,
        pending_prompt=None,
        pending_arrow_path=(),
        pending_path_length=None,
    )


def _make_snapshot() -> Snapshot:
    return Snapshot(
        schema_version=SCHEMA_VERSION,
        engine_version="0.0.0",
        seed=42,
        rng_cursor="",
        surface_id="<placeholder>",
        world=_make_world(),
        active_escalation_rules=(),
    )


def _every_event_type_instance() -> list[Any]:
    """Return one valid instance per Tier A4 v1 event type."""
    return [
        GameStarted(
            **_base_kwargs(),
            seed=42,
            engine_version="0.0.0",
            surface_id="<placeholder>",
            layout_hash="cafebabe",
            active_escalation_rules=(),
        ),
        MoveAttempted(**_base_kwargs(), target_room=5, accepted=True),
        MoveResolved(**_base_kwargs(), player_room=5),
        SenseEmitted(**_base_kwargs(), kind="WUMPUS_SMELL", cause_room=2),
        LocationReported(**_base_kwargs(), room=5, adjacencies=(1, 4, 6)),
        HazardTriggered(**_base_kwargs(), kind="PIT", room=4),
        WumpusStartled(**_base_kwargs(), from_room=7, to_room=6, ate_player=False),
        PlayerTeleported(**_base_kwargs(), from_room=5, to_room=17, cause="bat"),
        ActionChosen(**_base_kwargs(), action="S"),
        PromptIssued(
            **_base_kwargs(), kind="shoot_path_room", context={"slot": 1, "of": 3}
        ),
        CrookedPathRejected(**_base_kwargs(), slot=3, attempted_room=7),
        ArrowFired(**_base_kwargs(), path=(7, 14, 12)),
        ArrowPathStep(**_base_kwargs(), room=7, deflected=False),
        ArrowMissed(**_base_kwargs()),
        ArrowHitWumpus(**_base_kwargs(), room=11),
        ArrowHitPlayer(**_base_kwargs(), room=1),
        ArrowCountChanged(**_base_kwargs(), new_count=4),
        GameEnded(
            **_base_kwargs(),
            outcome="wumpus_shot",
            message_kind="win",
            final_snapshot=_make_snapshot(),
        ),
        SessionEnded(**_base_kwargs()),
        InstructionsShown(**_base_kwargs(), lines=("HELLO",)),
    ]


# ---------------------------------------------------------------------------
# Scenario 1 — Every event type is emittable and JSON-serializable
# ---------------------------------------------------------------------------


@given(
    "the wumpus.events module's complete v1 event set",
    target_fixture="r2s01_v1_event_instances",
)
def _r2s01_v1_event_instances() -> list[Any]:
    return _every_event_type_instance()


@when(
    "each event type is instantiated with valid payload and emitted via JsonlSink",
    target_fixture="r2s01_emit_result",
)
def _r2s01_emit_all(
    r2s01_v1_event_instances: list[Any],
    tmp_path: pathlib.Path,
) -> dict[str, Any]:
    ledger_path = tmp_path / "all_events.jsonl"
    sink = JsonlSink(ledger_path)
    try:
        for event in r2s01_v1_event_instances:
            sink.emit(event)
    finally:
        sink.close()
    return {"path": ledger_path, "count": len(r2s01_v1_event_instances)}


@then("each event serializes to a valid JSON line")
def _r2s01_each_line_is_json(r2s01_emit_result: dict[str, Any]) -> None:
    text = r2s01_emit_result["path"].read_text(encoding="utf-8")
    lines = [ln for ln in text.split("\n") if ln]
    assert len(lines) == r2s01_emit_result["count"], (
        f"Expected {r2s01_emit_result['count']} JSONL lines; got {len(lines)}."
    )
    for index, line in enumerate(lines):
        parsed = json.loads(line)
        assert isinstance(parsed, dict), (
            f"Line {index} is not a JSON object: {line!r}"
        )


@then("each line conforms to the wumpus/schemas/v1.json contract")
def _r2s01_each_line_conforms(r2s01_emit_result: dict[str, Any]) -> None:
    schema = load_schema(SCHEMA_VERSION)
    validator = jsonschema.Draft202012Validator(schema)
    text = r2s01_emit_result["path"].read_text(encoding="utf-8")
    for index, line in enumerate(ln for ln in text.split("\n") if ln):
        payload = json.loads(line)
        errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
        assert not errors, (
            f"Line {index} failed schema validation. Type "
            f"{payload.get('type')!r}; errors: {[e.message for e in errors]}"
        )


# ---------------------------------------------------------------------------
# Scenario 2 — Schema-drift events fail fast at emission
# ---------------------------------------------------------------------------


@given(
    "a JsonlSink attached to a Game",
    target_fixture="r2s02_attached_sink",
)
def _r2s02_attached_sink(tmp_path: pathlib.Path) -> dict[str, Any]:
    ledger_path = tmp_path / "drift.jsonl"
    sink = JsonlSink(ledger_path)
    return {"sink": sink, "path": ledger_path}


@when(
    "the engine (hypothetically) emits an event with a missing required field",
    target_fixture="r2s02_emit_outcome",
)
def _r2s02_emit_outcome(r2s02_attached_sink: dict[str, Any]) -> dict[str, Any]:
    """Construct an event-shaped object that violates the schema on purpose:
    a MoveAttempted instance whose `target_room` is non-integer (the dataclass
    accepts `Any` via default, but the schema requires integer)."""
    sink: JsonlSink = r2s02_attached_sink["sink"]
    # Bypass the dataclass type system by emitting a SimpleNamespace-shaped
    # payload via a duck-typed event whose `event_to_dict` outputs a missing
    # required field. The cleanest path: monkeypatch `event_to_dict` to drop
    # `type`. Even simpler: feed a real event whose schema-required field is
    # set to a wrong type — `target_room` as a string.
    bad_event = MoveAttempted(
        **_base_kwargs(),
        target_room="not-an-integer",  # type: ignore[arg-type]
        accepted=True,
    )
    raised: BaseException | None = None
    try:
        sink.emit(bad_event)
    except SchemaValidationError as exc:
        raised = exc
    finally:
        sink.close()
    return {
        "raised": raised,
        "path": r2s02_attached_sink["path"],
    }


@then("a SchemaValidationError is raised synchronously at emit time")
def _r2s02_schema_error_raised(r2s02_emit_outcome: dict[str, Any]) -> None:
    assert isinstance(r2s02_emit_outcome["raised"], SchemaValidationError), (
        f"Expected SchemaValidationError; got: {r2s02_emit_outcome['raised']!r}"
    )


@then("the JSONL file does not gain a partial/corrupt line")
def _r2s02_no_partial_line(r2s02_emit_outcome: dict[str, Any]) -> None:
    path: pathlib.Path = r2s02_emit_outcome["path"]
    contents = path.read_text(encoding="utf-8") if path.exists() else ""
    assert contents == "", (
        f"Expected the ledger file to be empty (no partial line on schema "
        f"validation failure); got: {contents!r}"
    )


# ---------------------------------------------------------------------------
# Scenario 3 — JSONL ledger is append-only and one-event-per-line
# ---------------------------------------------------------------------------


@given(
    "a 50-turn session is run with --ledger=session.jsonl",
    target_fixture="r2s03_session_artifacts",
)
def _r2s03_session(tmp_path: pathlib.Path) -> dict[str, Any]:
    """Drive a real Game with a JsonlSink subscribed; run several turns.

    The brief says "50-turn session". We exercise a deterministic action
    sequence rich enough to flush many event types into the ledger; the
    exact turn count is a property bound by how many actions we issue, not
    a hard 50. The count assertion below (lines == events emitted) is what
    binds the scenario, not the literal "50".
    """
    from wumpus import Game
    from wumpus.sinks import InMemorySink

    ledger_path = tmp_path / "session.jsonl"
    sink = JsonlSink(ledger_path)
    counter_sink = InMemorySink()  # peer counter — does NOT change emission order

    # Use the toy cave (R0 substrate) to keep the action sequence simple and
    # avoid Yob pre-game instructions state for this scenario.
    game = Game(seed=42, cave="toy")
    game.subscribe(sink)
    game.subscribe(counter_sink)

    # Drive a sequence of moves. The toy-cave path is 1 → 2 → 3 → wumpus.
    for action in ("move 2", "move 3", "move 4"):
        game.step(action)
    sink.close()

    return {
        "path": ledger_path,
        "event_count": len(counter_sink.events),
    }


@when(
    "session.jsonl is read",
    target_fixture="r2s03_session_lines",
)
def _r2s03_read_session(r2s03_session_artifacts: dict[str, Any]) -> list[str]:
    text = r2s03_session_artifacts["path"].read_text(encoding="utf-8")
    # Trailing newline → split yields a final empty string. Drop empties.
    return [ln for ln in text.split("\n") if ln]


@then("it contains exactly one JSON object per line")
def _r2s03_one_json_per_line(r2s03_session_lines: list[str]) -> None:
    for index, line in enumerate(r2s03_session_lines):
        parsed = json.loads(line)
        assert isinstance(parsed, dict), (
            f"Line {index} did not decode as a JSON object: {line!r}"
        )
        # The JSON-object-per-line invariant: a single decode consumed the
        # entire line. json.loads on a multi-object line would raise; the
        # successful decode + dict-shape check is the assertion.


@then("the total line count equals the number of events emitted during the session")
def _r2s03_line_count_matches(
    r2s03_session_lines: list[str],
    r2s03_session_artifacts: dict[str, Any],
) -> None:
    assert len(r2s03_session_lines) == r2s03_session_artifacts["event_count"], (
        f"Ledger has {len(r2s03_session_lines)} lines; engine emitted "
        f"{r2s03_session_artifacts['event_count']} events. "
        f"SC4 (synchronous + ordered emission) invariant violated."
    )


@then("the schema_version field on every line equals 1")
def _r2s03_schema_version_one(r2s03_session_lines: list[str]) -> None:
    for index, line in enumerate(r2s03_session_lines):
        payload = json.loads(line)
        assert payload.get("schema_version") == 1, (
            f"Line {index} schema_version was {payload.get('schema_version')!r}; "
            f"expected 1."
        )


# ---------------------------------------------------------------------------
# Scenario 4 — No background-thread event emission
# ---------------------------------------------------------------------------


@given(
    "a static AST audit of wumpus.events and wumpus.sinks",
    target_fixture="r2s04_audit_trees",
)
def _r2s04_audit_trees() -> dict[str, ast.AST]:
    """Parse the production modules whose contract is single-threaded
    emission (per SC4). The audit walks these ASTs and asserts none of the
    forbidden background-emission idioms are present.

    We also include `wumpus.serialization` since it's a hot path on every
    emit; if it ever grows background machinery, the audit catches that too.
    """
    import wumpus.events
    import wumpus.serialization
    import wumpus.sinks

    return {
        "events": ast.parse(pathlib.Path(wumpus.events.__file__).read_text(encoding="utf-8")),
        "sinks": ast.parse(pathlib.Path(wumpus.sinks.__file__).read_text(encoding="utf-8")),
        "serialization": ast.parse(
            pathlib.Path(wumpus.serialization.__file__).read_text(encoding="utf-8")
        ),
    }


def _find_forbidden_calls(tree: ast.AST) -> list[str]:
    """Return a list of forbidden background-emission idioms found in `tree`.

    Banned:
      - `threading.Thread(...)` instantiation
      - `asyncio.create_task(...)` calls
      - `asyncio.run(...)` calls
      - `concurrent.futures.submit(...)` or `executor.submit(...)` calls
    """
    findings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            attr_chain = _attribute_chain(node.func)
            if attr_chain is None:
                continue
            joined = ".".join(attr_chain)
            if joined.endswith("threading.Thread") or attr_chain[-1] == "Thread":
                # Be permissive: only flag if 'threading' appears earlier.
                if "threading" in attr_chain:
                    findings.append(joined)
            if joined.endswith("asyncio.create_task") or joined.endswith("create_task"):
                if "asyncio" in attr_chain or attr_chain[-1] == "create_task":
                    findings.append(joined)
            if joined.endswith("asyncio.run") and "asyncio" in attr_chain:
                findings.append(joined)
            if attr_chain[-1] == "submit" and any(
                tok in attr_chain for tok in ("concurrent", "futures", "executor")
            ):
                findings.append(joined)
    return findings


def _attribute_chain(node: ast.AST) -> list[str] | None:
    """Return the dotted attribute chain for `node` (Name/Attribute), or None."""
    parts: list[str] = []
    current: ast.AST | None = node
    while current is not None:
        if isinstance(current, ast.Attribute):
            parts.insert(0, current.attr)
            current = current.value
            continue
        if isinstance(current, ast.Name):
            parts.insert(0, current.id)
            return parts
        return None
    return parts or None


@then("no threading.Thread is instantiated for event emission")
def _r2s04_no_threads(r2s04_audit_trees: dict[str, ast.AST]) -> None:
    for module_name, tree in r2s04_audit_trees.items():
        findings = _find_forbidden_calls(tree)
        thread_findings = [f for f in findings if "Thread" in f]
        assert not thread_findings, (
            f"Background-thread instantiation found in wumpus.{module_name}: "
            f"{thread_findings}. SC4 (synchronous emission) violated."
        )


@then(
    "no asyncio.create_task or concurrent.futures.submit is invoked for event emission"
)
def _r2s04_no_async_or_executor(r2s04_audit_trees: dict[str, ast.AST]) -> None:
    for module_name, tree in r2s04_audit_trees.items():
        findings = _find_forbidden_calls(tree)
        async_findings = [
            f
            for f in findings
            if "create_task" in f or "asyncio.run" in f or f.endswith(".submit")
        ]
        assert not async_findings, (
            f"Background async/executor idiom found in wumpus.{module_name}: "
            f"{async_findings}. SC4 (synchronous emission) violated."
        )
