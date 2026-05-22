# `wumpus` Python package — goals

*The engine the harebrain experiment matrix runs on. Faithful Yob 1973 at the core, extensible at the seams, observable by construction.*

---

## Where this sits

The parent note (`wumpus_idea.md`) lays out a six-cell experiment matrix — three non-LLM controls (A scripted, B random-legal, C heuristic), one harebrain agent (D), and two trusted-narrator agents (E LangGraph, F LangChain) — plus a wild-baseline cell (G) and three LLM-Modulo probes (Mystery Wumpus, back-prompt loop, verification probe). Every cell except G plays the *same* game. The `wumpus` package is that game.

Its first job is to be Yob's 1973 *Hunt the Wumpus*. Its second job is to remain Yob's game while a chart, a heuristic, a LangGraph agent, and a coding agent all play through it under measurement. The two jobs constrain each other, and this document records the constraints.

The package lives at `python/packages/wumpus/`, alongside `hello_world/` and `embedding_db/`. Source under `src/wumpus/`, tests under `tests/`, `pyproject.toml` matching the workspace conventions (hatchling, `requires-python >= 3.11`).

---

## Goal 1 — Faithful to Yob 1973

The reference implementation is `wumpus/experiments/g_wild_baseline/wumpus.gwbasic.bas` (Yob's source, patched only for GW-BASIC dialect — `patches.diff` records the 14 mechanical edits). When the BASIC source and this package disagree, the BASIC source wins.

### Messages — verbatim

The player-facing strings come from Yob, character for character. The catalogue:

| Event | String |
|---|---|
| Title | `HUNT THE WUMPUS` |
| Smell | `I SMELL A WUMPUS!` |
| Draft | `I FEEL A DRAFT` |
| Bats | `BATS NEARBY!` |
| Position | `YOU ARE IN ROOM  <n>` |
| Tunnels | `TUNNELS LEAD TO  <a>  <b>  <c>` |
| Move/shoot prompt | `SHOOT OR MOVE (S-M)?` |
| Move target prompt | `WHERE TO?` |
| Shoot length prompt | `NO. OF ROOMS(1-5)?` |
| Arrow path prompt | `ROOM #?` (repeated per room) |
| Invalid path | `ARROWS AREN'T THAT CROOKED - TRY ANOTHER ROOM` |
| Miss | `MISSED` |
| Kill | `AHA! YOU GOT THE WUMPUS!` |
| Self-shot | `OUCH! ARROW GOT YOU!` |
| Wumpus kills | `TSK TSK TSK- WUMPUS GOT YOU!` |
| Bumped wumpus | `...OOPS! BUMPED A WUMPUS!` |
| Pit | `YYYIIIIEEEE . . . FELL IN PIT` |
| Bat | `ZAP--SUPER BAT SNATCH! ELSEWHEREVILLE FOR YOU!` |
| Loss tag | `HA HA HA - YOU LOSE!` |
| Re-prompt | `HEE HEE HEE - THE WUMPUS'LL GETCHA NEXT TIME!!` |
| Same setup | `SAME SET-UP (Y-N)?` |
| Instructions | `INSTRUCTIONS (Y-N)?` |

The instruction block (`WELCOME TO 'HUNT THE WUMPUS'` through the warnings list) ships verbatim, including Yob's typo `RAMDOM` in the arrow-deflection line. The package preserves typos.

### Design — verbatim

- Twenty rooms arranged as a dodecahedron — the fixed adjacency table Yob hard-codes in his `DATA` statements. Not regenerated per game.
- One wumpus, two bats, two pits, five arrows.
- Hazard and player placement is uniform-random over rooms with rejection on collision (Yob's `FNB` loop).
- Senses fire on entry to a room adjacent to a hazard. Smell, draft, bats — one line each, suppressed when absent.
- Movement is one room per turn through a connecting tunnel. Off-graph moves return `NOT POSSIBLE -` and re-prompt without consuming the turn.
- Arrows traverse up to five rooms along a player-specified path. Each room must connect to the previous; non-connecting paths trigger the `ARROWS AREN'T THAT CROOKED` re-prompt for that segment, after which Yob's source picks the next room at random (the `RAMDOM` line). Preserve that behavior.
- Firing an arrow startles the wumpus. The wumpus moves with `P = 0.75` to an adjacent room and stays with `P = 0.25` (Yob's `FNC` distribution). If the wumpus lands on the player, the player loses.
- Running out of arrows ends the game. Yob's source loses the player when arrow count hits zero (`L = 0` branch).
- A shot through the player's current room kills the player (`OUCH! ARROW GOT YOU!`).
- After a terminal state, the game prompts `SAME SET-UP (Y-N)?` — replay with the same layout, or fresh.

### Inputs and outputs — verbatim

The CLI shape matches Yob's: line-buffered stdio, prompts ending in `;` so the input cursor sits on the same line, single-letter responses for `Y/N` and `S/M`, integer responses for room numbers. Output uses ALL CAPS, Yob's spacing (the double spaces in `YOU ARE IN ROOM  <n>` are deliberate), and no trailing punctuation where Yob omitted it.

### Mistakes — verbatim

Faithfulness includes Yob's bugs. The package preserves:

- `RAMDOM` in the arrow-deflection text — a typo, not a feature, kept anyway.
- The arrow-self-shot detection that fires only when the *arrow's final room* matches the player's room. A crooked arrow passing through the player's room mid-path does not kill the player in Yob's source. Preserve.
- The `RND(0)` vs `RND(1)` HP-2000 vs GW-BASIC semantic — already resolved in `patches.diff`, captured here as a controlled deviation. The Python package emulates GW-BASIC-corrected behavior because that's what `wumpus.gwbasic.bas` actually runs.

Each preserved mistake gets a one-line comment in the source pointing at the BASIC line it mirrors. Future readers should know what is bug-for-bug fidelity and what is a Python liberty.

---

## Goal 2 — Extensible without breaking faithfulness

Faithful Yob is the default. Variants are opt-in configuration on the same engine.

The configurable dimensions:

| Dimension | Yob default | Range supported |
|---|---|---|
| Room count | 20 | Any `n >= 4` |
| Topology | Dodecahedron | Any 3-regular graph; arbitrary adjacency for `n != 20` |
| Wumpus count | 1 | `1..k` |
| Pit count | 2 | `0..k` |
| Bat count | 2 | `0..k` |
| Arrow count | 5 | `1..k` |
| Arrow max range | 5 | `1..k` |
| Wumpus-move probability on shot | 0.75 | `0.0..1.0` |
| RNG seed | unset | any 64-bit int |

A configuration object holds these. Construction with no arguments yields Yob 1973. The CLI exposes a `--yob` flag (the default) and individual overrides for variant runs.

A separate slot — `escalation_rules` — extends the engine for the ladder in the parent note (`wumpus_idea.md:160-164`): L2 "wumpus moves when startled," L3 "partial observability," L4 "bigger or non-dodecahedron graph." Each escalation level is additive over the same base engine. Adding a rule must not require rewriting the rest.

Constraints on extensions:

- The Yob defaults must remain byte-identical to the BASIC source across all output. Regression tests pin every message against captured BASIC transcripts.
- Variants must declare which Yob invariants they relax (e.g., "L3 removes the on-entry tunnels line"). The package logs the active variant set with every run so analysis knows what game was actually played.
- No variant is allowed to change the *internal* state schema. Senses, room, arrows, hazards are the same fields whether one wumpus or three. Two wumpuses means a list of length two, not a new field.

---

## Goal 3 — Extensible to Mystery Wumpus

Mystery Wumpus (`wumpus_idea.md:128-134`, `docs/research/agents/llm-modulo-benchmarks-as-supplements-deep-dive.md`) relabels the externally-facing strings while leaving the topology and the rules byte-identical. The package supports this through a single seam: a `surface` object.

The surface holds every player-facing string and symbol:

- Room labels (integers 1-20 → `α`, `β`, … or arbitrary tokens).
- Sense strings (`I SMELL A WUMPUS!` → `YOU DETECT RESONANCE ζ`).
- Command verbs (`S`/`M` → arbitrary tokens, as long as they remain distinguishable).
- Hazard names in the instruction block (`WUMPUS` → `RESONANT ENTITY` or similar).

Default surface = Yob 1973. Mystery surface = a relabeling supplied by the experiment harness. The engine never references room numbers or sense names by their surface form — it operates on internal integer IDs and enum tags, and the surface translates at the boundary.

This means a Mystery run uses the same engine, the same seed-determined layout, the same rules. Only the bytes the LLM reads change. That is the structural claim the obfuscation gap rests on.

The surface seam also makes a third variant trivial: localization. A French Wumpus drops in with a French surface. Useful for nothing in particular, but the seam earns its keep by being symmetric.

---

## Goal 4 — Observable by construction

Telemetry is a first-class output, not a debugging afterthought. Every metric in the parent note's table (`wumpus_idea.md:104-122`) and every probe in the LLM-Modulo section (`wumpus_idea.md:128-154`) must be computable from the package's logs without re-running the game.

### What gets logged

For each turn, a structured event:

- **Pre-state** — wumpus location(s), pit locations, bat locations, player room, arrows remaining, alive/dead.
- **Senses fired** — the set of warnings produced this turn, with their causes (`smell because wumpus in room 14`).
- **Player input** — the raw stdin bytes received, the parsed command, validation result.
- **Effects** — moves, kills, teleports, wumpus reactions, hazard activations.
- **Post-state** — same fields as pre-state.
- **Surface variant active** — which `surface` object produced the strings the player saw.
- **Seed and RNG cursor** — enough to replay from this turn forward.
- **Timestamps** — wall-clock per event, plus a monotonic turn counter.

### How it gets logged

- **JSONL ledger** — one event per line, append-only, one file per game. The schema is versioned and frozen across releases of the package; downstream notebooks consume it directly. New fields are additive; existing fields never change meaning.
- **Replay API** — `replay(ledger_path)` reconstructs the world at any turn. The MPL oracle harness for E/F (`wumpus_idea.md:155-185`) replays trusted-narrator transcripts through this API to compute divergence events.
- **Snapshot/restore** — capture full world state at any turn, restore later. Lets the verification probe (`wumpus_idea.md:148-154`) pause mid-game without losing position.

### What the schema must support, by name

- Divergence events — diff between a claimed state (LLM narration) and the ledger's post-state.
- Scaffolding leaks — per-node-per-turn tagging from the LangGraph harness; the engine accepts an optional `actor_node` field on each input event.
- Obfuscation gap — `surface_variant` field on every event makes Classic-vs-Mystery a `GROUP BY`.
- Back-prompt convergence — the harness annotates events with a `back_prompted = true` flag when it has just injected a correction.
- Scratchpad accuracy — the harness logs the agent's claimed working memory; the diff is computed against the ledger's post-state.
- Verification accuracy — out-of-band Q&A is logged as `event_type = "verification"` with the question, the answer, and the oracle ledger row it should have matched.
- Post-bat recovery — bat teleports emit a `cause = "bat"` move event; recovery turns are derived from the next consecutive turn where the agent's actions are consistent with the new room.
- Arrow-shoot accuracy — every shot logs the full sense history available to the player at decision time, alongside the chosen path; optimality is a post-hoc computation.
- Tokens per turn — the harness logs `tokens_in`/`tokens_out` per turn from the model API; the engine has nothing to add here but reserves the fields in the schema.

### Constraints on the telemetry layer

- Logging is **synchronous and ordered**. No background thread, no buffering across turn boundaries. A crash mid-turn loses at most the in-progress event.
- Logging is **complete by default**. The harness can turn down verbosity (production runs), but the default is "log everything." The cost of an over-logged run is disk; the cost of an under-logged run is a re-run.
- Logging is **schema-validated** on write. A schema drift in code surfaces immediately, not three notebooks later.
- The ledger is **the source of truth for analysis**. Notebooks read JSONL, not the live engine. This forces the schema to carry every field analysis needs.

---

## Goal 5 — Built for LLM and harness use

The package exposes three surfaces, each serving a different cell of the experiment matrix.

### 5.1 — CLI (cells G, and any human or coding agent)

`python -m wumpus` runs the game in a terminal. Stdio shape matches Yob's exactly — line buffering, prompts on the same line as input, ALL CAPS output. This is what the G wild-baseline experiment (`wumpus_idea.md:97-103`) hands to Claude Code or Codex, and what a human plays for the human-baseline calibration.

Constraints:

- Line-buffered output (`sys.stdout` reconfigured to `line_buffering=True`, or explicit `flush=True` after every `print`). The `pexpect`/`wexpect` harnesses in the parent note depend on this.
- A `--seed` flag so identical seeds across runs produce identical layouts. Yob's source does not seed; this is a documented controlled deviation.
- A `--ledger <path>` flag so even CLI runs produce the same JSONL telemetry as programmatic runs.
- A `--surface <variant>` flag so the same CLI launches a Mystery run.

### 5.2 — Programmatic API (cells A, B, C, and the harness in E and F)

A `Game` class with a `step(action) -> Observation` shape, where `Observation` is a structured object containing the strings the player would see plus parsed fields. Cells A (scripted), B (random-legal), and C (heuristic) drive `Game` directly. The trusted-narrator harness for E and F drives it indirectly: the LLM produces a move in prose, the harness parses it, replays it through `Game`, and emits the resulting observation to the LLM as the next prompt.

Constraints:

- The API is **deterministic given a seed**. Two `Game(seed=k)` instances run through the same actions produce byte-identical ledgers.
- The API is **non-destructive on illegal input**. An off-graph move returns a `NOT POSSIBLE -` observation and leaves the world unchanged. The turn counter advances only on legal actions, matching Yob.
- The API is **inspectable**. A `Game.world_state()` method returns the full internal state as a structured object — for cells A, B, C that need ground truth, and for the divergence-events oracle in E and F.
- The API is **separate from telemetry**. The engine emits events to a ledger sink; the sink can be a file, an in-memory list, or `/dev/null`. Test runs use the in-memory sink.

### 5.3 — Host import (cell D)

Cell D — harebrain — wires an LLM into an MPL chart's decide-leaf via a host import (`wumpus_idea.md:147`). For this to work, the package must expose a function-call surface compatible with MPL's host-import contract: pure functions that take serializable inputs and return serializable outputs, with no hidden state.

The exact shape will be pinned by the MPL spike (step 1 of the parent note's build order). The constraint on this package is: nothing in the engine assumes a long-lived Python process owns the world. The `Game` state is serializable (the snapshot/restore API in §4); a host import can resurrect a `Game` from a snapshot, step it once, return a new snapshot, and exit. The engine must not break under that usage pattern.

### Cross-cutting constraints

- **No framework dependencies in the engine.** Not LangChain, not LangGraph, not MPL. The engine is plain Python. The harnesses live above it and import it.
- **Subprocess-safe.** A pexpect/wexpect wrapper around the CLI must not hang. This means no SDL window, no curses, no readline mode that confuses non-TTY stdin.
- **Reproducible.** Seed + variant + input transcript reconstruct the game exactly. The seed is the only entropy source; no `time.time()` calls, no untracked `os.urandom`.
- **Testable.** Every Yob message and every escalation rule has a regression test. The BASIC source is the spec; pinned transcripts from `wumpus.gwbasic.bas` are the test fixtures.

---

## Non-goals

A goals document earns its keep by saying what the package will not be.

- **Not a solver, planner, or agent.** Cells A through G live in the harness, not the engine. The engine plays no role of its own.
- **Not a graphical or web interface.** Yob's CLI is the interface. A future visualizer reads the ledger; it does not embed the engine.
- **Not a framework.** No plugin system, no event bus, no entity-component-system. Configuration + a small extension slot for escalation rules is the whole story.
- **Not a generalized roguelike engine.** Adjacent generalizations (other 1973-era text games, MUD primitives) are tempting and out of scope. The package is for Hunt the Wumpus and its declared variants.
- **Not a benchmark runner.** The runner lives in the harness. The engine produces ledgers; the runner consumes them.

---

## What earns "done"

The package is done for the parent note's purposes when:

1. A scripted control (cell A) plays Yob 1973 from a seed and produces a ledger byte-identical to a captured BASIC transcript from the same seed.
2. A configuration switch produces Mystery Wumpus on the same engine, same seed, with only surface strings changed.
3. The MPL spike (`wumpus_idea.md:147`) imports the engine and round-trips a turn through a host import.
4. The escalation ladder's L2 ("wumpus moves when startled," already required by Yob baseline) and L3 ("partial observability") drop in as configuration, not rewrites.
5. The analysis notebook consumes JSONL ledgers from cells A, B, C, D, E, F, and G — without special-casing any of them.

When those five hold, the engine has cleared its share of the experiment. Everything else is harness, model, and analysis.

---

## Where this sits in the series

| Source | Relation |
|---|---|
| [Hunt the Wumpus as the harebrain demo](./wumpus_idea.md) | The parent note. This document is the engine half of step 2 of its build order. |
| [Pure LLM trust — the cageless baseline](../experiments/pure_llm_trust.md) | Day-two analysis depends on this engine for retroactive divergence-event scoring. |
| [G wild baseline README](../experiments/g_wild_baseline/README.md) | The BASIC source this engine mirrors. When the two disagree, the BASIC source wins. |
| [LLM-Modulo benchmarks as supplements](../../docs/research/agents/llm-modulo-benchmarks-as-supplements-deep-dive.md) | Source of the Mystery Wumpus pattern this engine supports through the surface seam. |
