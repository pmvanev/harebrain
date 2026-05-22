# Shared Artifacts Registry: wumpus-classic

Every `${variable}` in the journey mockups and every constant referenced from
multiple call sites has a single source of truth here. Untracked artifacts are
the primary cause of horizontal integration failures and rule-fidelity drift.

## Engine constants

### Dodecahedron adjacency

**Source of truth:** `wumpus_classic.constants.DODECAHEDRON` (Python tuple of 20 frozensets, indexed 1-20)

**Origin:** Yob `wumpus.gwbasic.bas` lines 0130-0160 (DATA statements). The exact 20x3 adjacency:

| Room | Tunnels to |
|---|---|
| 1 | 2, 5, 8 |
| 2 | 1, 3, 10 |
| 3 | 2, 4, 12 |
| 4 | 3, 5, 14 |
| 5 | 1, 4, 6 |
| 6 | 5, 7, 15 |
| 7 | 6, 8, 17 |
| 8 | 1, 7, 9 |
| 9 | 8, 10, 18 |
| 10 | 2, 9, 11 |
| 11 | 10, 12, 19 |
| 12 | 3, 11, 13 |
| 13 | 12, 14, 20 |
| 14 | 4, 13, 15 |
| 15 | 6, 14, 16 |
| 16 | 15, 17, 20 |
| 17 | 7, 16, 18 |
| 18 | 9, 17, 19 |
| 19 | 11, 18, 20 |
| 20 | 13, 16, 19 |

**Consumers:**
- cave generation (place player + hazards into valid rooms; verify no crossovers)
- sense emitter (check whether L(1) is adjacent to each L(j) for j=2..6)
- move validation (`WHERE TO?` answer must be in adjacency of current room or equal current room — Yob 4050-4110)
- arrow path walk (`ROOM #?` answer must be in current arrow position's adjacency, else random tunnel per FNB(1))
- wumpus startle (on miss, wumpus moves to S(L(2), FNC(0)) for FNC ∈ {1,2,3} or stays for FNC=4 — uses the same table)

**Integration risk:** HIGH. A drift between any two consumers produces "phantom geography" — the exact divergence-event kind the parent note cites (`wumpus_idea.md:55`). Any change to this table is a Yob-fidelity break and requires a rule-coverage audit re-run.

**Validation:** All callers MUST import from `wumpus_classic.constants.DODECAHEDRON`. No literal adjacency tables anywhere else. Unit test: import the table, assert it matches the audited 20x3 above.

### Sense order on room entry

**Source of truth:** `wumpus_classic.constants.SENSE_ORDER`

**Origin:** Yob lines 2020-2120. The `FOR J=2 TO 6` loop iterates entities in L-array order: L(2)=wumpus, L(3)=pit, L(4)=pit, L(5)=bat, L(6)=bat. For each entity, the `FOR K=1 TO 3` inner loop checks if any tunnel from L(1) leads to it. The `ON J-1 GOTO` jumps to the matching print statement.

Effective effect: senses print in the order **wumpus, pit, pit, bat, bat**, with multiple of the same hazard producing the same text repeated (once per tunnel-entity match).

**Consumers:**
- sense emitter (engine)
- CLI renderer (preserves emission order verbatim)
- `SenseEmitted` event field `kind` (typed enum: `WUMPUS_SMELL | PIT_DRAFT | BAT_NEARBY`)
- transcript JSONL ordering

**Integration risk:** MEDIUM. Order-of-printing differences from Yob would not change game outcomes but would fail byte-comparison fidelity tests against `wexpect`-driven PC-BASIC transcripts.

**Validation:** Acceptance test compares engine output for a fixed seeded layout against the PC-BASIC transcript for the same scenario (oracle parity test, see `outcome-kpis.md` KPI 3).

### Hazard-check order on move

**Source of truth:** `wumpus_classic.constants.HAZARD_ORDER`

**Origin:** Yob `_MOVE ROUTINE` lines 4140-4310. Checks in order:
1. Wumpus collision (4150-4200) — bump triggers startle; if startled wumpus lands on player, eaten
2. Pit (4220-4250) — fall, lose
3. Bat (4270-4300) — teleport to random room, recursively re-enter (GOTO 4130)

**Consumers:** move resolution only.

**Integration risk:** MEDIUM. Reordering would change semantics for the rare case where a room contains multiple co-located hazards — but cave gen forbids co-location (INV-2), so under spec the order is unobservable. Still: replicate Yob's order verbatim so any cave-gen bug surfaces predictably.

### Prompt strings

**Source of truth:** `wumpus_classic.constants.PROMPTS`

**Origin:** Yob source.

| Key | Text | Yob line |
|---|---|---|
| `INSTRUCTIONS` | `INSTRUCTIONS (Y-N)?` | 0020 |
| `ACTION` | `SHOOT OR MOVE (S-M)?` | 2510 |
| `MOVE_TARGET` | `WHERE TO?` | 4020 |
| `SHOOT_PATH_LEN` | `NO. OF ROOMS(1-5)?` | 3040 |
| `SHOOT_PATH_ROOM` | `ROOM #?` | 3080 |
| `SAME_SETUP` | `SAME SET-UP (Y-N)?` | 0590 |

**Consumers:** CLI renderer only. Engine emits `PromptIssued(kind)` events; renderer maps `kind` to text.

**Integration risk:** LOW for engine, HIGH for CLI fidelity. A typo in any prompt breaks oracle-parity tests.

**Validation:** Unit test asserts each prompt string exactly equals the Yob source line.

### Outcome messages

**Source of truth:** `wumpus_classic.constants.MESSAGES`

**Origin:** Yob source — including the famous swap.

| Key | Text | Yob line | Trigger |
|---|---|---|---|
| `LOSE` | `HA HA HA - YOU LOSE!` | 0520 | F<0 from any source (eaten / pit / out-of-arrows) |
| `WIN` | `HEE HEE HEE - THE WUMPUS'LL GETCHA NEXT TIME!!` | 0550 | F>0 from arrow-shot-wumpus |
| `BUMPED_WUMPUS` | `...OOPS! BUMPED A WUMPUS!` | 4160 | move into wumpus's room |
| `WUMPUS_EATS` | `TSK TSK TSK- WUMPUS GOT YOU!` | 3420 | startled or bumped wumpus lands on player |
| `FELL_IN_PIT` | `YYYIIIIEEEE . . . FELL IN PIT` | 4230 | move into pit |
| `BAT_SNATCH` | `ZAP--SUPER BAT SNATCH! ELSEWHEREVILLE FOR YOU!` | 4280 | move into bat room |
| `SMELL_WUMPUS` | `I SMELL A WUMPUS!` | 2060 | adjacent to wumpus |
| `FEEL_DRAFT` | `I FEEL A DRAFT` | 2080 | adjacent to pit |
| `BATS_NEARBY` | `BATS NEARBY!` | 2100 | adjacent to bat |
| `MISSED` | `MISSED` | 3220 | arrow exhausts path without hitting wumpus or player |
| `GOT_WUMPUS` | `AHA! YOU GOT THE WUMPUS!` | 3310 | arrow lands on wumpus |
| `ARROW_GOT_YOU` | `OUCH! ARROW GOT YOU!` | 3350 | arrow lands on player |
| `CROOKED` | `ARROWS AREN'T THAT CROOKED - TRY ANOTHER ROOM` | 3105 | path entry equals K-2 entry |
| `NOT_POSSIBLE` | `NOT POSSIBLE -` | 4100 | move target not adjacent and not current room |
| `BANNER` | `HUNT THE WUMPUS` | 0375 | game start |
| `TUNNELS_LEAD_TO` | `TUNNELS LEAD TO ` + room numbers | 2140 | room entry |
| `YOU_ARE_IN_ROOM` | `YOU ARE IN ROOM ` + room number | 2130 | room entry |

**Consumers:** CLI renderer only.

**Integration risk:** HIGH. The win/lose swap (Decision 3) is the recognition signal for returning players. Any "helpful corrector" who fixes the swap breaks the fidelity claim.

**Validation:** Unit test asserts MESSAGES exactly matches the byte-strings above. Acceptance test asserts CLI output on a forced-win seeded scenario contains `HEE HEE HEE` and on a forced-loss seeded scenario contains `HA HA HA`.

## Engine runtime artifacts

### Seed

**Source of truth:** `Game.__init__(seed: int | None = None)` constructor arg.

**Lifecycle:**
- `seed=None` (default): engine draws an int from OS entropy at construction. The drawn int is stored on the instance.
- `seed=<int>`: stored as-is.
- The stored seed is always available as `Game.seed` and is always written to the transcript header.

**Consumers:**
- internal `random.Random(seed)` instance used by every RNG call (cave gen, bat teleport, wumpus startle, arrow random tunnel)
- `GameStarted` event payload
- transcript header line: `# wumpus_classic v${version}  seed=${seed}  layout-hash=${layout_hash}`
- replay loader (reads header, instantiates `Game(seed=seed)`, asserts layout-hash matches)

**Integration risk:** HIGH. If any RNG call bypasses the instance's `random.Random` (e.g., calls `random.randint` at module level, or `os.urandom`, or `time.time()`), determinism breaks silently and Harriet's replays diverge.

**Validation:** Code-search audit at handoff to DESIGN — no `import random; random.X(...)` at module scope, no `os.urandom`, no `time.time()` in engine code paths.

### Layout hash

**Source of truth:** `Game._layout_hash` — computed as a stable hash (suggested: `hashlib.blake2b(digest_size=8).update(struct.pack('6B', wumpus, pit1, pit2, bat1, bat2, player_start))`)

**Consumers:**
- `GameStarted` event payload
- transcript header line
- replay verification (replayer asserts the second instance's layout hashes to the same value)

**Integration risk:** LOW (it's an integrity check, not a correctness driver).

### Arrow count

**Source of truth:** `Game._arrows` (initialized to 5 from Yob line 0360).

**Consumers:**
- arrow resolution (decrement on miss or self-shot, never on hit)
- `ArrowCountChanged` event
- terminal-state check: `_arrows == 0` after a decrement → `GameEnded(outcome=out_of_arrows)`

**Integration risk:** MEDIUM. Yob does NOT decrement on a wumpus-hit (the game ends first), but DOES decrement on a self-shot — the engine must replicate.

## Event schema

**Source of truth:** `wumpus_classic.events` module (dataclasses or Pydantic models — DESIGN to choose).

Tentative event types (DISTILL will refine; DESIGN will lock the schema):

| Event | Payload | Emitted when |
|---|---|---|
| `GameStarted` | seed, layout_hash, snapshot | `Game()` constructor finishes |
| `PromptIssued` | kind (enum), context | engine is awaiting input |
| `ActionChosen` | action (S \| M) | valid action input parsed |
| `MoveAttempted` | from_room, to_room | move command parsed |
| `MoveRejected` | from_room, attempted_room, reason | target not adjacent and not current room |
| `MoveResolved` | room | player position updated |
| `SenseEmitted` | kind (WUMPUS_SMELL \| PIT_DRAFT \| BAT_NEARBY), room | room entry triggers a sense |
| `LocationReported` | room, adjacencies | YOU ARE IN ROOM / TUNNELS LEAD TO line printed |
| `HazardTriggered` | kind (WUMPUS \| PIT \| BAT), room | player enters hazard room |
| `WumpusStartled` | from_room, to_room or None, ate_player (bool) | bumped or shot-missed |
| `PlayerTeleported` | from_room, to_room | bat snatch resolved |
| `PlayerEaten` | room | startled or bumped wumpus lands on player |
| `ArrowFired` | path (list[int]) | shoot command parsed |
| `ArrowPathStep` | room, deflected (bool) | arrow advances one room |
| `ArrowMissed` | (none) | path consumed without hitting wumpus or player |
| `ArrowHitWumpus` | room | wumpus killed |
| `ArrowHitPlayer` | room | self-shot |
| `ArrowCountChanged` | new_count | on miss or self-shot |
| `CrookedPathRejected` | slot_index, attempted_room | path entry equals K-2 entry |
| `GameEnded` | outcome (enum), message_kind (win\|lose), final_snapshot | terminal state reached |
| `SessionAborted` | reason | Ctrl-C or EOF on stdin |

**Consumers:**
- `CliRenderer` (translates events to Yob-faithful text)
- `JsonlSink` (writes one event per line to transcript file)
- harness queue sinks
- replay verifier (compares event sequences)

**Integration risk:** HIGH. The event schema is a published API once the engine ships — see CLI/TUI Anti-Pattern "Breaking JSON output between versions." DESIGN should treat changes to event names, payload field names, or enum values as breaking.

**Validation:** Schema versioned (`schema_version` field on every event). DISTILL writes acceptance tests that pin specific event sequences for specific seeded scenarios.

## CLI surface

### Command

**Source of truth:** `python/packages/wumpus_classic/pyproject.toml` entry-points table → `wumpus_classic.cli:main`.

**Invocation:** `wumpus [--seed SEED] [--transcript PATH] [--no-instructions]`

**Consumers:** Pat (interactive), Harriet (with `--transcript=session.jsonl` for tee'd capture).

**Integration risk:** MEDIUM. The flag set is the published CLI contract.

### Version string

**Source of truth:** `python/packages/wumpus_classic/pyproject.toml` → `[project].version`.

**Consumers:** `wumpus --version`, transcript header, `GameStarted` event.

**Integration risk:** MEDIUM (per `nw-shared-artifact-tracking` Common Patterns).

## Cross-feature artifacts (out-of-scope, listed for downstream consumers)

These will become shared artifacts when downstream features (MPL chart, experiment harness) consume the engine. Listed here so DESIGN does not accidentally close them off.

| Artifact | Future consumer | Note |
|---|---|---|
| Snapshot dataclass | MPL chart (compares its own state to engine snapshot for oracle diff) | Public, stable, versioned. |
| Event stream (JSONL) | Cells D, E, F, G replay tools | `pcbasic` + `wexpect` transcripts will be diffed against this. |
| Layout-hash | LangGraph cell E (forces DM to commit to a specific layout up front, per `pure_llm_trust.md`) | Useful for retroactive oracle replay. |

## Validation checklist (for peer review)

- [x] Every constant referenced from multiple call sites has a `wumpus_classic.constants.*` source.
- [x] No CLI prompt or outcome message is duplicated outside `MESSAGES`/`PROMPTS`.
- [x] No adjacency literal exists outside `DODECAHEDRON`.
- [x] Event schema captures every Yob mechanic (cross-referenced against journey YAML invariants).
- [x] Seed is the only entropy input; no module-level `random`, `os.urandom`, or `time.time()` calls are permitted in engine code paths.
- [x] Yob source line citations exist for every constant.
