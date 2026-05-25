# R2 ledger — JSONL event stream
#
# R2-S01 ships the JSONL persistence layer + the schema-validation discipline
# that makes downstream replay safe. Each R2 slice appends its scenarios to
# this file. R2-S01 ships scenarios 1-4 (schema + JsonlSink + functional
# --ledger flag + no-background-thread audit); R2-S02 (replay) + R2-S03
# (determinism-source audit script) will append their own scenarios.
#
# Per ADR-002 (schema evolution policy) every emitted event is validated
# against `wumpus/schemas/v<SCHEMA_VERSION>.json` at emit time by JsonlSink.
# Per SC4 emission is synchronous + ordered.

Feature: R2 ledger — JSONL event stream

  As a harness operator
  I want a typed, schema-validated, append-only JSONL ledger from every session
  So that divergence-event metrics and post-hoc analysis are computable without re-running games.

  # ---------------------------------------------------------------------------
  # R2-S01 — Schema v1 + JsonlSink + functional --ledger flag
  # ---------------------------------------------------------------------------

  Scenario: Every event type is emittable and JSON-serializable
    Given the wumpus.events module's complete v1 event set
    When each event type is instantiated with valid payload and emitted via JsonlSink
    Then each event serializes to a valid JSON line
    And each line conforms to the wumpus/schemas/v1.json contract

  Scenario: Schema-drift events fail fast at emission
    Given a JsonlSink attached to a Game
    When the engine (hypothetically) emits an event with a missing required field
    Then a SchemaValidationError is raised synchronously at emit time
    And the JSONL file does not gain a partial/corrupt line

  Scenario: JSONL ledger is append-only and one-event-per-line
    Given a 50-turn session is run with --ledger=session.jsonl
    When session.jsonl is read
    Then it contains exactly one JSON object per line
    And the total line count equals the number of events emitted during the session
    And the schema_version field on every line equals 1

  Scenario: No background-thread event emission
    Given a static AST audit of wumpus.events and wumpus.sinks
    Then no threading.Thread is instantiated for event emission
    And no asyncio.create_task or concurrent.futures.submit is invoked for event emission

  # ---------------------------------------------------------------------------
  # R2-S02 — Ledger header (full context on GameStarted) + replay() module
  # ---------------------------------------------------------------------------

  Scenario: GameStarted carries everything needed to replay
    Given Game(seed=42) is constructed with a JsonlSink writing to a fresh ledger file
    When the first line of the ledger is read
    Then it parses as GameStarted with schema_version=1 and type="GameStarted"
    And the GameStarted header carries seed=42, a non-empty layout_hash, engine_version matching wumpus.__version__, variant_config as a dict, and surface_id="yob"

  Scenario: replay(ledger_path) reconstructs world at turn k
    Given a Game(seed=42, cave="toy") ran an action sequence to turn 2 with a JsonlSink writing session.jsonl
    When replay(session_path).advance_to(turn=2).world_state() is called
    Then the returned world_state equals the original Game.world_state() at turn 2

  Scenario: Replay refuses on engine-version major-mismatch
    Given a synthetic ledger whose GameStarted carries engine_version="99.0.0"
    When replay(synthetic_path) is called
    Then a VersionCompatibilityError is raised naming both the written and current versions
