# Feature Delta — `wumpus`

<!-- markdownlint-disable MD024 -->

> Engine the harebrain experiment matrix runs on. Faithful Yob 1973 at the core, extensible at the seams, observable by construction. Three first-class surfaces (CLI, programmatic `Game.step()`, MPL host-import). Source of record: `wumpus/docs/wumpus_python_goals.md`.

---

## Wave: DISCUSS / [REF] Phase Tracker

Workflow status (live during DISCUSS execution). Mark each phase as it completes.

| # | Phase | Status | Output |
|---|---|---|---|
| 1 | JTBD Analysis (Decision 4 = Yes) | **done** | `[REF] JTBD`, `[REF] Personas` sections below |
| 1.5 | Scope Assessment (Elephant Carpaccio gate) | **done** — user confirmed PASS (one feature) | `[REF] Scope Assessment` |
| 2 | Journey Design (mental model → emotional arc → shared artifacts → error paths → Gherkin) | **done** | `[REF] Journeys`, `[REF] Shared Artifacts Registry` |
| 2.5 | Story Mapping + Slice Carpaccio (≤1 day slices, learning hypotheses, taste tests) | **done** | `[REF] Story Map` (inline; harebrain single-file convention) |
| 3 | Requirements & Stories (LeanUX + Elevator Pitch + AC + DoR + outcome KPIs) | pending | `[REF] User Stories`, `[REF] Acceptance Criteria`, `[REF] Outcome KPIs`, `[REF] DoR Validation` |
| 4 | Optional per-wave review (only on trigger) | pending | invoked via `/nw-review nw-product-owner-reviewer` |
| 5 | Handoff (DESIGN + DEVOPS-KPI) + SSOT back-propagation | pending — **blocked: `docs/product/vision.md` deleted in working tree; Changes 1–3 target a missing file** | `[REF] Wave Decisions`, `[REF] Changed Assumptions`, `docs/product/` updates |

---

## Wave: DISCUSS / [REF] Inputs Consulted

Read before Phase 1 begins (prior-wave consultation gate):

- ✓ `wumpus/docs/wumpus_python_goals.md` — five-goal substrate; this wave's primary spec
- ✓ `wumpus/docs/wumpus_idea.md` — parent note; experiment-matrix consumer context (cells A–G, LLM-Modulo probes)
- ✓ `docs/product/vision.md` — wumpus-scoped; contains contradicted OUT-OF-SCOPE list (back-propagation required)
- ✓ `docs/product/jobs.yaml` — 3 existing jobs (Player Pat + Harness Harriet), inline personas
- ✓ `docs/product/journeys/play-classic-wumpus.yaml` — `$ref` pointer to archived feature path (broken; replaced this wave)
- ⊘ `docs/feature/wumpus/diverge/` — does not exist (no DIVERGE wave); validation flag for stories = `synthesized-from-goals-doc`
- ✓ `docs/feature/.archive/wumpus-classic-2026-05-20/discuss/*` — 7 archived stories; wording/AC mined for Yob-fidelity slice
- ✓ `docs/project-brief.md` / `docs/stakeholders.yaml` — not present in repo; skipped

**Contradictions to back-propagate at handoff (see `[REF] Changed Assumptions`):**
1. `vision.md` § Out of scope lists "WUMP2 cave variants", "escalation-ladder rules L2-L4", "MPL integration" — all three are IN-SCOPE per the new goals doc.
2. `vision.md` names the package `python/packages/wumpus_classic/` — the new goals doc names `python/packages/wumpus/`.
3. `journeys/play-classic-wumpus.yaml` is a `$ref` to an archived path — must be rewritten or split.

---

## Wave: DISCUSS / [REF] JTBD

Phase 1 output. Every user story in Phase 3 traces to a `job_id` here.

### Job inventory

Five jobs, three personas. Three jobs carry forward from `docs/product/jobs.yaml` with refined statements; two jobs are NEW for this wave (surface seam + host-import driving).

| job_id | Title | Primary persona | Validation |
|---|---|---|---|
| `play-classic-wumpus` | Play the 1973 Hunt the Wumpus game faithfully | player-pat | synthesized-from-goals-doc (refined from existing) |
| `instrument-wumpus-play` | Capture every game event from a live or programmatic session | harness-harriet | synthesized-from-goals-doc (refined) |
| `replay-wumpus-deterministically` | Reproduce a specific game from a recorded seed | harness-harriet | synthesized-from-goals-doc (refined) |
| `probe-llm-obfuscation-gap` | Run the same game under a relabeled surface to measure LLM pattern-completion vs reasoning | harness-harriet, llm-cell-consumer | NEW, synthesized-from-goals-doc |
| `drive-engine-from-host-import` | Drive a wumpus turn from a chart's decide-leaf via a host-import contract | mpl-cell-consumer | NEW, synthesized-from-goals-doc, **blocked-on-mpl-spike** for signature |

### Job stories

#### `play-classic-wumpus`

> When a person who knows or wants to learn Yob's 1973 Hunt the Wumpus opens a terminal,
> they want to play the game with byte-recognizable fidelity to the BASIC original
> (typos, message swap, startle rule, crooked-arrow-passes-through-player and all),
> so they can experience the game that lives in the historical record without an emulator detour.

**Dimensions:**

- *Functional* — get to a terminal prompt, type `S` or `M`, navigate a 20-room dodecahedron, kill the wumpus or die trying, observe the right strings at the right times.
- *Emotional* — feel disoriented in the way Yob's design intends. Bat-teleport erases your map; the 25% startle stay-put rule means "I shot, I missed" tells you nothing. The good outcome is the **experience** of disorientation, not its absence (per existing `player-pat.anti-confidence` note).
- *Social* — be able to say "I played the actual 1973 game" to other software-history people. The byte fidelity is what earns the claim.

**Four forces:**

- *Push* — Running PC-BASIC requires an isolated Python 3.12 tool environment and tolerating GW-BASIC dialect patches. Reading the BASIC source for atmosphere doesn't substitute for playing.
- *Pull* — A `pip install`-able (or `uv run`-able) Python game runnable anywhere Python runs, that **feels** like the original. ALL CAPS, double-space after `ROOM`, the works.
- *Anxiety* — A "modern reimplementation" that softens the original's quirks (the win/lose message swap, the startle rule, the `RAMDOM` typo) is not the game. If the package "fixes" Yob's bugs, it isn't faithful.
- *Habit* — Players reach for PC-BASIC or the kingsawyer mirror. To displace those, this needs to be at least as one-step as `pc-basic wumpus.gwbasic.bas`.

#### `instrument-wumpus-play`

> When a researcher runs an LLM agent or a human against Hunt the Wumpus and needs to diff
> what the agent claimed against what actually happened, they want a structured, append-only,
> schema-validated event stream from every game session, so they can compute divergence-event
> metrics post-hoc without re-running the game.

**Dimensions:**

- *Functional* — get a JSONL file per game with one event per turn including pre-state, senses-fired, raw stdin, effects, post-state, surface_variant, seed, RNG cursor, and timestamps.
- *Emotional* — confidence that the ledger is **the** truth. Notebooks read JSONL, not the live engine. If the ledger and the engine ever disagree, the ledger is what gets cited.
- *Social* — be able to point a collaborator at a JSONL file and have them reconstruct what happened without your in-memory context.

**Four forces:**

- *Push* — Without instrumentation, divergence metrics require re-running the game alongside the agent. That doubles compute and risks RNG drift between the run and the oracle.
- *Pull* — One JSONL stream, schema-validated on write, with every field the parent note's metric table (`wumpus_idea.md:104-122`) needs (divergence events, scaffolding leaks, obfuscation gap, back-prompt convergence, scratchpad accuracy, verification accuracy, post-bat recovery, arrow-shoot accuracy, tokens-per-turn).
- *Anxiety* — Instrumentation that mutates game behavior (observer effect) invalidates every measurement built on it. A background-thread logger that buffers across turn boundaries can lose the in-progress event on crash. Both are disqualifying.
- *Habit* — Researchers reach for print-statement archaeology or stdout regex parsing. The typed schema must be **easier** than either or it loses.

#### `replay-wumpus-deterministically`

> When a researcher finds an interesting divergence or scenario in a recorded transcript,
> they want to replay the exact game from a seed value, so they can investigate without
> searching for a needle in a stochastic haystack.

**Dimensions:**

- *Functional* — `Game(seed=k)` plus the input transcript reconstructs the game byte-for-byte. `replay(ledger_path)` reconstructs the world at any turn. Snapshot/restore captures full state and resumes later.
- *Emotional* — trust that "seed=42" means something stable across machines, across days, across CI runs. The whole oracle pattern collapses if seeded replay drifts.
- *Social* — be able to file a bug report as "seed=42, turn 17" and have anyone else reproduce it.

**Four forces:**

- *Push* — Non-seeded runs can't be replayed; bug reports become unreproducible folklore. Yob didn't seed; that's a documented controlled deviation.
- *Pull* — Seed value in the transcript header is sufficient. `Game(seed=42)` works like `random.Random(42)` — the obvious mental model.
- *Anxiety* — A seeded mode that differs from unseeded mode (e.g., picks layouts from a different distribution) silently invalidates cross-comparisons. Equally bad: a seed that's "stable" in one Python version and not the next.
- *Habit* — Researchers expect NumPy / `random.Random(42)` semantics. Anything else (string seeds, opaque tokens) loses.

#### `probe-llm-obfuscation-gap`

> When a researcher wants to measure how much an LLM's Hunt the Wumpus performance came from
> pattern-completing the 1973 game (on the public internet since '73) versus actually reasoning
> from observations, they want to run the same engine, same seed, same rules, but with every
> player-facing string relabeled to unfamiliar tokens, so the obfuscation gap (classic-minus-mystery
> win rate) is a clean measurement.

**Dimensions:**

- *Functional* — flip a `--surface mystery` flag (or pass a surface object to `Game`) and the same seed produces the same internal layout, the same RNG draws, the same rule outcomes — but every byte the LLM reads changes (room labels, sense strings, command verbs, hazard names in the instructions).
- *Emotional* — confidence that the seam is **structural**, not cosmetic. If a Mystery run accidentally takes one extra RNG draw, the obfuscation gap measurement is contaminated.
- *Social* — be able to say "this is the Mystery Blocksworld experiment applied to Wumpus" and have other LLM-Modulo readers immediately know what's being claimed (per `docs/research/agents/llm-modulo-benchmarks-as-supplements-deep-dive.md`).

**Four forces:**

- *Push* — Without a surface seam, you'd fork the engine for Mystery; now you maintain two copies that drift, and any measured gap is confounded by the fork.
- *Pull* — One config switch, identical internals, only the bytes the LLM reads change. Localization (French Wumpus) drops into the same hook for free.
- *Anxiety* — A surface seam that leaks (the engine references a room number by its surface form somewhere, or the surface object accidentally consumes an RNG draw) destroys the measurement. The seam must be provably structural.
- *Habit* — Researchers reach for "rename a few constants" — but constants embedded in `print()` calls are not a seam, they're a copy-paste fork waiting to happen.

#### `drive-engine-from-host-import`

> When the harebrain agent (cell D) plays Wumpus, the MPL chart owns the world state and the
> LLM consults at the decide-leaf via a host import. The host import sees an opaque snapshot,
> wants to step the game by one turn from that snapshot, and wants a new snapshot back —
> with no assumption that a long-lived Python process owns the world, so the chart can
> resurrect a Game on demand from a serialized state.

**Dimensions:**

- *Functional* — `Game.snapshot()` returns a serializable object; `Game.from_snapshot(snap).step(action)` returns a new snapshot + observation; the engine has no module-level mutable state that would prevent this round-trip.
- *Emotional* — confidence that the engine "fits" the MPL host-import contract without contortions, even before the exact contract is pinned by the MPL spike.
- *Social* — be able to say "MPL chart for Hunt the Wumpus calls the engine" without an asterisk explaining a process-lifetime workaround.

**Four forces:**

- *Push* — A `Game` that assumes a long-running Python process owning the world doesn't fit a chart that may serialize state across ticks. Globals, singletons, module-cached RNGs all break this.
- *Pull* — A `Game.snapshot()` / `Game.from_snapshot()` round-trip that preserves byte-identical determinism (snapshot, step, snapshot, restore, step, get same observation as if no round-trip).
- *Anxiety* — The MPL spike (`wumpus_idea.md:147`) hasn't been done yet. The exact function signature of the host-import surface is unknown today. Building too much around an imagined signature creates rework.
- *Habit* — Python game engines default to "long-lived process, mutable Game object, no serialization story." This is the failure mode to avoid.

### Opportunity scores (importance × satisfaction gap)

Five jobs is enough to score. Scale: importance and satisfaction both 1–10; opportunity = importance + max(0, importance − satisfaction). (Ulwick formula.)

| Job | Importance | Current satisfaction | Opportunity score | Ranking notes |
|---|---:|---:|---:|---|
| `play-classic-wumpus` | 10 | 3 (PC-BASIC exists but is painful, faithful Python reimpls are scarce) | 17 | The baseline; nothing else works without this |
| `instrument-wumpus-play` | 10 | 1 (no instrumented Wumpus exists; stdout-regex is the alternative) | 19 | **Highest** — gates every metric downstream |
| `replay-wumpus-deterministically` | 9 | 1 (Yob's source is unseeded; no replay anywhere) | 17 | Tied with #1; required for cross-cell comparison |
| `probe-llm-obfuscation-gap` | 8 | 0 (no Mystery Wumpus implementation exists) | 16 | Single-config probe; high research leverage |
| `drive-engine-from-host-import` | 7 (essential for cell D, irrelevant elsewhere) | 0 (MPL spike not yet done) | 14 | **Blocked-on-spike for signature**, but constraints knowable now |

### Job-to-story bridge

Phase 3 stories will trace to jobs per this map. Story IDs are placeholders; final IDs assigned in Phase 3.

| Job | Stories that will serve it (provisional) |
|---|---|
| `play-classic-wumpus` | US-01 engine-boot-with-seeded-cave, US-02 Yob-faithful-CLI-loop, US-03 hazards-and-senses, US-04 shooting-end-to-end, US-06 bug-for-bug-fidelity-pin |
| `instrument-wumpus-play` | US-07 versioned-JSONL-ledger-schema |
| `replay-wumpus-deterministically` | US-05 seeded-replay-byte-identical, US-08 programmatic-API-with-snapshot-restore |
| `probe-llm-obfuscation-gap` | US-09 surface-seam-for-mystery-variant |
| `drive-engine-from-host-import` | US-08 (shared — snapshot/restore round-trip), US-10 host-import-determinism-contract |
| (cross-cutting variant config) | US-11 variant-config-with-yob-defaults |

That's ~10–11 stories provisional. Phase 1.5 will assess whether this is right-sized as one feature.

---

## Wave: DISCUSS / [REF] Personas

Goals-doc + parent note implicate three personas. Two already exist inline in `jobs.yaml`; one is new. Per the output contract, each gets its own file under `docs/product/personas/` (created at handoff). Summaries below; the persona files are the SSOT.

### `player-pat` (existing, refined)

- **Role**: a person at a terminal who wants to play Yob's 1973 Hunt the Wumpus.
- **Sub-shapes**: (a) someone who already knows the game and recognizes the quirks ("HA HA HA - YOU LOSE!" on death is the tell); (b) someone learning the game for the first time who needs the on-disk INSTRUCTIONS prompt to do its job.
- **Surface**: CLI (line-buffered, all-caps prompts, no curses, no scrollback hijack).
- **Success feel**: "This is the 1973 game."
- **Emotional arc**: curious/off-balance → tension (smell + draft + bats-nearby triangulation) → catharsis (win or lose, the message text confirms it).
- **Anti-confidence note (preserved)**: Yob's game does not build player confidence as it progresses. Bat teleports erase mental maps; the wumpus's 25% stay-put startle rule means "I shot, I missed" doesn't tell the player where the wumpus is. Designing for player confidence would be designing against the game.

### `harness-harriet` (existing, refined)

- **Role**: a researcher or LLM agent driving the game programmatically. Runs thousands of games unattended, diffs transcripts across replays, tees event streams into JSONL ledgers.
- **Surface**: Python API (`Game(seed=k).step(command) -> Observation`) **and** the JSONL ledger. Both must serve.
- **Success feel**: "Deterministic, instrumented, oracular."
- **Emotional arc**: skepticism ("does this really agree with PC-BASIC?") → trust (seeded replays come back byte-identical; event stream covers every rule from the Yob audit) → conviction (the engine is now the ground-truth oracle; LLM divergences are measurable against it).
- **Concrete sub-roles** (same persona, different harness): scripted-baseline driver (cell A); random-legal driver (cell B); heuristic driver (cell C); LangChain/LangGraph trusted-narrator harness operator (cells E/F); wild-baseline observer wrapping the CLI with pexpect/wexpect (cell G).

### `mpl-cell-consumer` (NEW)

- **Role**: the MPL chart that owns Hunt the Wumpus world state for cell D (harebrain). The "user" is the chart author; the consumer of the engine API is the chart's host-import call. Wires a snapshot through the engine, gets a new snapshot back, has no Python process to assume.
- **Surface**: programmatic API restricted to serializable inputs/outputs (no Game object held across ticks).
- **Success feel**: "The engine fits the host-import contract without asterisks."
- **Emotional arc**: caution (the MPL spike hasn't pinned the exact signature) → relief (the engine's snapshot/restore round-trip already satisfies the underlying constraints) → confidence (when the spike lands, the engine doesn't need a refactor — just a thin adapter).
- **Why this is a persona, not just a job**: this consumer has *different* needs from `harness-harriet`. Harriet wants a long-lived `Game` object and an observation stream. The MPL chart wants stateless turn-stepping from opaque snapshots. The engine has to serve both without contortions.

### Note on cells A–G as personas vs. jobs

The parent note's six-cell matrix (`wumpus_idea.md:82-103`) names seven distinct actors (A scripted, B random-legal, C heuristic, D harebrain, E LangGraph, F LangChain, G wild-baseline). For this wave: **cells A–C and E–G are all instances of `harness-harriet`** with different harness code on top. **Cell D is the `mpl-cell-consumer`**. **A human player at the terminal is `player-pat`**. Three personas, not seven, because the engine's interface to each is the same surface (CLI for Pat and G; programmatic API for A/B/C/E/F; host-import for D).

---

## Wave: DISCUSS / [REF] Scope Assessment

**Verdict: PASS — 10–11 stories, 1 bounded context, projected ~18–25 days, absorbed by Phase 2.5 carpaccio slicing into ≤1 day verticals.** A feature-split alternative exists and is documented below; user can veto PASS before Phase 2.

### Signals (honest read)

| Signal | Threshold | Observed | Triggered? |
|---|---|---|---|
| User stories | >10 | 10–11 provisional | borderline (at the line) |
| Bounded contexts | >3 | **1** (the engine package) | no |
| WS integration points | >5 | 5–6 (seeded RNG, room graph, senses, CLI render, JSONL writer, transcript-fixture compare) | borderline (at the line) |
| Estimated effort | >2 weeks | ~18–25 days | **yes** |
| Independent user outcomes that could ship separately | "multiple" | engine + CLI as one; host-import as a defensible second | **mildly** (case exists; substrate is shared) |

That's **1 hard + 2 borderline + 1 mild trigger**. By the strict 2-of-N heuristic this lands in "propose a split" territory.

### Why I'm recommending PASS anyway

Three reasons:

1. **One bounded context.** The engine — Game state, room graph, RNG, rule loop, snapshot/restore, event emission — is one unified model. The three surfaces (CLI, programmatic API, host-import) are **inbound ports** on the same hexagon, not separate bounded contexts. Splitting them into separate features means publishing/freezing the shared types (`Game`, `Observation`, `Snapshot`, `Event`, `Surface`, `VariantConfig`) before all three surfaces have shaped them — Conway-violating its own substrate.

2. **The goals doc is explicit on this point.** `wumpus_python_goals.md` § "Where this sits" and `vision.md` (current, even before this wave's edits) both say it directly: *"The engine must serve all three from one source of truth. That is why this is a single feature, not three."* That's not decorative — it's the design wager. Splitting it down the middle and shipping engine + CLI first would land an API that has to be revised when the host-import constraint (no module-level state, snapshot/restore round-trip) gets added.

3. **The effort signal is a Phase 2.5 problem, not a Phase 1.5 problem.** ≤1 day elephant-carpaccio slices absorb ~20 days across ~20 slices, each one shipped independently with its own learning hypothesis. Phase 1.5's job is to detect *features that need to be split into multiple features*; Phase 2.5's job is to slice *the work inside the feature* into thin verticals. The effort number says "this is a lot of slices," not "this is multiple features."

### The split alternative (recorded for user veto)

If the user prefers to split anyway, the **clean seam is the host-import boundary**, not the surface boundary. Specifically:

- **Feature A — `wumpus` (engine + CLI + programmatic API + JSONL ledger + variant config + Mystery surface seam).** ~8 stories. ~14–18 days. Walking skeleton = cell A scripted plays Yob from seed → ledger byte-identical to BASIC transcript.
- **Feature B — `wumpus-host-import` (snapshot/restore round-trip + signature pinned by MPL spike + host-import determinism contract).** ~2–3 stories. ~4–7 days. Walking skeleton = snapshot → step → snapshot byte-identical round-trip.

Why this seam and not "engine vs CLI vs host-import as three features":
- Feature B has the spike blocker (R2). Splitting it out keeps Feature A from being held up by an unrelated unknown.
- Feature A's surfaces (CLI + programmatic API) genuinely share their substrate; the JSONL ledger and the `Game.step()` shape want to be designed together with cell-A-through-G all visible.
- Feature B's "users" (the MPL chart, cell D) don't exist yet — the chart and the harebrain agent ship in separate features anyway. Pushing Feature B later doesn't strand a real downstream user.

The cost of splitting: two DESIGN/DEVOPS/DISTILL/DELIVER cycles instead of one; Feature A has to publish a programmatic API that **anticipates** the host-import constraints (no module-level state, etc.) without being able to test against the host-import contract until Feature B; risk that Feature B reveals API churn requirements that ripple back into Feature A's already-shipped surface.

### Recommendation

**PASS as one feature.** The carpaccio slicing in Phase 2.5 will produce ≤1 day verticals; the effort number lives there, not here. The shared substrate argument from the goals doc and vision.md is the decisive one.

**Stop here if the user disagrees.** If you'd rather split into `wumpus` (engine + CLI + API) and `wumpus-host-import` (snapshot/restore + spike-blocked host-import contract), say so before I open Phase 2 — the work for Feature B's DESIGN would otherwise happen too early relative to its spike blocker.

---

## Wave: DISCUSS / [REF] Journeys

Phase 2 output. Four journeys, one per structurally-distinct surface-persona pair (per `[REF] Personas`):

| # | Journey ID | Primary persona | Surface | Job(s) served | Validation |
|---|---|---|---|---|---|
| J1 | `play-classic-wumpus` | player-pat | CLI (Yob default surface) | `play-classic-wumpus` | mined-from-archive + goals-doc |
| J2 | `run-mystery-wumpus-probe` | harness-harriet (orchestrator); LLM-cell-consumer (the player) | Programmatic API + CLI subprocess; mystery surface variant | `probe-llm-obfuscation-gap`, `play-classic-wumpus` (under mystery surface) | synthesized-from-goals-doc |
| J3 | `instrument-wumpus-session` | harness-harriet | Programmatic API + JSONL ledger | `instrument-wumpus-play`, `replay-wumpus-deterministically` | synthesized-from-goals-doc + mined-from-archive |
| J4 | `drive-wumpus-from-host-import` | mpl-cell-consumer | MPL host-import (snapshot-step-snapshot) | `drive-engine-from-host-import` | synthesized-from-goals-doc, **blocked-on-mpl-spike for signature** |

Conventions for each journey below:
- **Mental model** is how the consumer thinks they are using the engine — the words they would use, the contract they are imagining. The engine must not surprise them.
- **Emotional arc** is start → middle → end. Where a journey has two consumers in the same session (J2, J3), each arc is split.
- **Shared artifacts** lists the cross-journey artifacts consumed. Full ownership map lives in `[REF] Shared Artifacts Registry`.
- **Steps** are the minimum needed for the slice; the archived `journey-play-classic-wumpus.yaml` carries the byte-level Yob mockups and is the mining source. Re-inlining 1973-typo-level detail here would duplicate the archive without adding signal.
- **Error paths** are the failure modes the engine must handle correctly; full Yob branch detail lives in DISTILL.
- **Gherkin** captures the acceptance-test-shaped scenarios *unique* to the journey. Pan-engine fidelity scenarios (every Yob string, every adjacency) belong in DISTILL, not here.

---

### J1 — `play-classic-wumpus`

**Persona:** `player-pat` (sub-shapes a + b — knows-the-game and learning-the-game).
**Job:** `play-classic-wumpus`.
**Surface:** CLI — `python -m wumpus` or `wumpus` entry-point.
**Yob-fidelity claim:** byte-recognizable parity with `wumpus/experiments/g_wild_baseline/wumpus.gwbasic.bas`.

**Mental model.** Pat thinks: "this is the 1973 game; I type `S` or `M`, it talks back in ALL CAPS, when I lose it tells me HA HA HA — and when I win it tells me HEE HEE HEE, because Yob swapped them." Pat does **not** think about surface objects, variant configs, RNG seeds, JSONL ledgers, or snapshots. Those are present in the engine but never surface to Pat unless Pat passed a CLI flag.

**Emotional arc.**

| Phase | Pat's state | Trigger | Engine signal |
|---|---|---|---|
| Start | Curious / off-balance | sees `INSTRUCTIONS (Y-N)?` and the `HUNT THE WUMPUS` banner | exact Yob strings, including double-spaces |
| Orient | Ready to think | `YOU ARE IN ROOM <n>` + `TUNNELS LEAD TO  a  b  c` | sense lines fire if and only if a hazard is adjacent |
| Tension | Weighing options | `SHOOT OR MOVE (S-M)?` after sense triangulation | re-prompt on bad input without advancing turn |
| Commit | Committed (move or shoot) | typed `M` + room, or `S` + path | engine accepts, validates, advances world |
| Hazard or hit | Bracing or elated | `...OOPS! BUMPED A WUMPUS!`, `YYYIIIIEEEE . . . FELL IN PIT`, `ZAP--SUPER BAT SNATCH!`, `AHA! YOU GOT THE WUMPUS!`, `OUCH! ARROW GOT YOU!` | hazard order is wumpus → pit → bat; arrows decrement only on miss or self-shot |
| Terminal | Catharsis (the swap confirms) | `HA HA HA - YOU LOSE!` *or* `HEE HEE HEE - THE WUMPUS'LL GETCHA NEXT TIME!!` | swap preserved — this is the recognition signal |
| Replay | Re-entered, same disorientation | `SAME SET-UP (Y-N)?` Y → identical layout, fresh entropy | `Game._initial_layout` restored verbatim |

**Anti-confidence note (preserved from `[REF] Personas`):** the arc does NOT build confidence as it progresses. Bat teleports erase Pat's mental map; the 25% wumpus-stay-put startle rule means "I shot, I missed" tells Pat nothing about where the wumpus is now. Designing FOR confidence is designing against the game. The arc above is the *target* arc — the one Yob designed for. The engine's job is to deliver that arc faithfully, not to soften it.

**Steps (compressed; mockups in archived `journey-play-classic-wumpus.yaml` are mine-able verbatim):**

1. **Boot.** `wumpus` (or `wumpus --seed 42`); engine prompts `INSTRUCTIONS (Y-N)?`; on `Y` prints the verbatim instruction block including the `RAMDOM` typo (`goals.md` line 50); then banner `HUNT THE WUMPUS`.
2. **Orient.** On entry to a room, engine emits sense events in L-array order (wumpus, pit, pit, bat, bat — `[REF] Shared Artifacts Registry` → `sense_order`), then prints `YOU ARE IN ROOM  <n>` and `TUNNELS LEAD TO  <a>  <b>  <c>`.
3. **Choose action.** `SHOOT OR MOVE (S-M)?` — `S` or `M` only; anything else re-prompts.
4. **Resolve move.** `WHERE TO?` → adjacency-validated. Hazard resolution order wumpus → pit → bat (`HAZARD_ORDER` in registry). Bat teleport recurses into a fresh entry, sense lines fire again.
5. **Resolve shoot.** `NO. OF ROOMS(1-5)?` then `ROOM #?` per segment; crooked-path rejection re-prompts that slot only; arrow walks through dodecahedron taking random tunnel on missing connection; final-room match with player kills (preserves Yob's "crooked-arrow passing through player does not kill" — `goals.md` line 74).
6. **Terminal.** Yob's swapped messages (HA HA HA on lose, HEE HEE HEE on win). `SAME SET-UP (Y-N)?` Y restores the saved initial layout.

**Shared artifacts consumed:** `DODECAHEDRON`, `SENSE_ORDER`, `HAZARD_ORDER`, `PROMPTS`, `MESSAGES`, `arrow_count`, `wumpus_startle` (FNC distribution), `Surface` (defaulted to Yob), `VariantConfig` (defaulted to Yob).

**Error paths.**

- **Off-graph move** → `NOT POSSIBLE -` + re-prompt; turn counter does not advance.
- **Move to current room** → Yob permits (`bas` line 4090). Engine permits.
- **Invalid action input** (not `S`/`M`) → re-prompt; no `ActionChosen` event emitted.
- **Path length out of range** (`0` or `6+`) → re-prompt `NO. OF ROOMS(1-5)?`.
- **Crooked path** (`P(K) == P(K-2)`, K>2) → `ARROWS AREN'T THAT CROOKED - TRY ANOTHER ROOM` + re-prompt for that slot only; earlier slots preserved.
- **Arrow tunnel missing** → arrow takes `S(L, FNB(1))` random adjacent; remaining path is discarded; emits `ArrowPathStep(deflected=True)`.
- **Bat teleport into pit** → game ends (Yob's recursion through line 4130).
- **Wumpus startled onto player** (bumped *or* shot-miss) → `TSK TSK TSK- WUMPUS GOT YOU!` then `HA HA HA - YOU LOSE!`.
- **Out of arrows** → `HA HA HA - YOU LOSE!` (`GameEnded(outcome=out_of_arrows)`).
- **EOF on stdin** (e.g., pexpect/wexpect harness disconnects) → `SessionAborted` event, clean exit (does not hang).

**Gherkin (J1-specific; pan-engine fidelity scenarios live in DISTILL, mined from archived `journey-play-classic-wumpus.yaml`):**

```gherkin
Scenario: Pat sees Yob's swapped win message
  Given Pat is in room 8 with 5 arrows
  And the wumpus is in room 14 and rooms 8-7, 7-14 are connected
  When Pat shoots a 2-room path through rooms 7 then 14
  Then Pat sees "AHA! YOU GOT THE WUMPUS!"
  And Pat sees "HEE HEE HEE - THE WUMPUS'LL GETCHA NEXT TIME!!"
  # Yob swap: win prints HEE HEE HEE, not HA HA HA. The swap is the recognition signal.

Scenario: Pat sees Yob's typo preserved in instructions
  Given Pat answers "Y" to "INSTRUCTIONS (Y-N)?"
  Then the printed instruction block contains the exact string "RAMDOM"
  # Yob's typo (goals.md line 50); preservation is a fidelity claim, not a bug.

Scenario: Crooked arrow passing through Pat's room does not kill Pat mid-path
  Given Pat is in room 8 and shoots a 3-room path
  And the path walks rooms 7, then 8 (passing through Pat's room mid-path), then 9
  When the arrow walks the path
  Then Pat does not see "OUCH! ARROW GOT YOU!" when the arrow is in slot 2 (room 8)
  And the arrow continues to slot 3
  # goals.md line 74: arrow-self-shot detection fires only on FINAL room. Bug-for-bug fidelity.

Scenario: Bat teleport recurses into a chained hazard
  Given Pat moves into a bat room
  And the engine's next bat-teleport target is a pit room
  Then Pat sees "ZAP--SUPER BAT SNATCH! ELSEWHEREVILLE FOR YOU!"
  And Pat sees "YYYIIIIEEEE . . . FELL IN PIT"
  And Pat sees "HA HA HA - YOU LOSE!"

Scenario: SAME SET-UP=Y restores the initial layout exactly
  Given Pat just finished a game with wumpus in room 14, pits in rooms 4 and 17, bats in rooms 5 and 9, start room 8
  When Pat answers "Y" to "SAME SET-UP (Y-N)?"
  Then the new game has the same wumpus, pit, bat, and start placements
  And the engine emits GameStarted with the same layout_hash

Scenario: Subprocess wrapper (pexpect/wexpect) does not hang on prompt
  Given a pexpect/wexpect harness wraps `wumpus`
  When the harness reads up to "INSTRUCTIONS (Y-N)?"
  Then the prompt is observable WITHOUT requiring a trailing newline
  And the harness can write a response without deadlock
  # goals.md § 5.1: line-buffered stdout, no curses, no SDL, no readline.
```

---

### J2 — `run-mystery-wumpus-probe`

**Persona:** `harness-harriet` (orchestrator) **+** any LLM cell (D/E/F/G — the "player") **+** later, `player-pat` running a Mystery variant for calibration.
**Job:** `probe-llm-obfuscation-gap` (primary); incidentally also `play-classic-wumpus` under a non-default surface.
**Surface:** Mystery surface variant — same engine, same seed, same rules; **only** the bytes the LLM reads change.
**Structural claim being measured:** an LLM that reasons should be ~invariant under relabeling; one that pattern-completes from a 50-year-old training corpus is not.

**Mental model.** Harriet thinks: "I'll run the same seeded game twice — once with the Yob surface, once with the Mystery surface — and the **internal** trajectory must be byte-identical at the engine layer. The only diff is the strings the LLM read. If any non-surface byte differs between the two ledgers, the seam is leaking and the measurement is contaminated." The LLM player thinks (we hope): "I am in cadence Φ; I detect resonance ζ; I hear harmonics III; what should I do?" — and produces a move whose semantics are obvious to the engine via verb-token translation.

**Emotional arc (orchestrator, harness-harriet):**

| Phase | Harriet's state | Trigger |
|---|---|---|
| Start | Cautious — "this only works if the seam is structural" | constructs `Game(seed=k, surface=MysterySurface(), variant=YobVariant())` |
| Mid | Trust building — internal trajectory matches classic | `Game(seed=k).step(a).snapshot() == Game(seed=k, surface=Mystery()).step(a').snapshot()` where `a' = mystery.translate(a)` |
| End | Conviction — the obfuscation gap is a clean `GROUP BY surface_variant` | every event in the ledger carries `surface_variant`; analysis aggregates classic-minus-mystery win rate |

**Mental model (LLM player, secondary).** The LLM sees Mystery tokens, has no canonical-form retrieval to lean on, and must reason from observations. The engine offers no help — that's the experimental point.

**Steps:**

1. **Construct paired games.** `g_classic = Game(seed=k, surface=YobSurface())`; `g_mystery = Game(seed=k, surface=MysterySurface())`. Layout determined by `seed`, NOT by surface. Engine MUST consume zero RNG draws during surface translation (per `goals.md` § Goal 3 — "the surface object accidentally consumes an RNG draw" would contaminate the measurement).
2. **Drive a turn.** Harness reads classic prompt + LLM-A's response, drives `g_classic.step(action)`; reads mystery prompt + LLM-B's (or same-LLM-different-context) response, drives `g_mystery.step(mystery.translate_back(action))`. Engine's *internal* effect must be identical given identical `(seed, action)` pairs.
3. **Verify seam.** Engine emits an event per turn with `surface_variant: yob | mystery` and `internal_state_hash: <hash>`. Across the two ledgers, `internal_state_hash` MUST agree at every turn that received translation-equivalent actions.
4. **Aggregate.** Post-hoc notebook joins classic + mystery ledgers on `(seed, turn)`, computes win-rate-classic minus win-rate-mystery per LLM cell, per N-seeds.

**Shared artifacts consumed:** `Surface` (the seam — `YobSurface`, `MysterySurface`, future `FrenchSurface`); `seed`; `Event/Ledger record` (with `surface_variant` field); `VariantConfig` (the *non-surface* dimensions — wumpus count, room count, arrow count — frozen at Yob across both runs); `internal_state_hash` (engine emits per turn for seam verification).

**Error paths.**

- **Surface object holds engine state** → contamination; surface must be a pure translation layer with no mutable state of its own. Rejected at construction.
- **Surface consumes an RNG draw** (e.g., randomizing the symbol map per-game without seeding) → contamination. Mystery surface's symbol map must be either fixed or seeded by a *separate, declared* seed logged in the ledger header.
- **Engine references a room number by its surface form anywhere** (e.g., `print(surface.room(n))` inside the engine's move-validation path) → seam leak. The engine operates on internal IDs only; surface translates at the boundary.
- **`internal_state_hash` mismatch across paired runs** at the same turn → seam is leaking; the measurement is invalid; the experiment is paused.
- **Mystery surface assigns ambiguous verb tokens** (e.g., two distinct commands map to indistinguishable strings post-translation) → ill-defined player input. Surface validation rejects.
- **Localization third-variant test** (`FrenchSurface`) — a stretch goal of the seam — passes the same hash check as a smoke test that the seam is general, not just Mystery-shaped.

**Gherkin:**

```gherkin
Scenario: Paired classic and mystery runs produce identical internal trajectories
  Given Harriet constructs g_classic = Game(seed=42, surface=YobSurface())
  And Harriet constructs g_mystery = Game(seed=42, surface=MysterySurface())
  When Harriet steps both games with translation-equivalent actions for 20 turns
  Then for every turn t, g_classic.events[t].internal_state_hash == g_mystery.events[t].internal_state_hash

Scenario: Mystery surface does not consume engine RNG
  Given Harriet runs Game(seed=42, surface=YobSurface()) for 50 turns
  And Harriet runs Game(seed=42, surface=MysterySurface()) for 50 turns with identical translation-equivalent inputs
  Then the engine's internal RNG cursor (logged per turn) is identical between the two runs
  # goals.md § Goal 3: "if a Mystery run accidentally takes one extra RNG draw, the obfuscation gap measurement is contaminated."

Scenario: Every ledger event records the active surface variant
  Given Harriet runs Game(seed=42, surface=MysterySurface())
  When the ledger is read
  Then every event carries surface_variant = "mystery"
  And no event references a Yob string ("I SMELL A WUMPUS!", "HA HA HA - YOU LOSE!", etc.) under mystery surface

Scenario: Engine code paths reference no surface-form strings
  Given a static code audit of the engine package
  Then no print statement, no comparison, no error message inside the engine references a surface-layer string literal
  # goals.md § Goal 3 structural claim: surface is the only boundary; engine operates on internal IDs and enum tags.

Scenario: A second non-Mystery surface (FrenchSurface) drops in without engine changes
  Given Harriet implements FrenchSurface as a pure translation layer
  When Harriet runs Game(seed=42, surface=FrenchSurface())
  Then the engine's internal_state_hash sequence equals Game(seed=42, surface=YobSurface()) at every turn
  And the ledger emits surface_variant = "french"
  # The seam is general; Mystery is one instance.
```

---

### J3 — `instrument-wumpus-session`

**Persona:** `harness-harriet` (cells A, B, C, E, F, G in primary; D via host-import is J4's territory).
**Job:** `instrument-wumpus-play` (primary), `replay-wumpus-deterministically` (secondary — every instrumented session is also a replay seed).
**Surface:** programmatic Python API + JSONL ledger sink. Can also tee from CLI runs (`--ledger PATH`).
**The ledger is the source of truth for analysis** (`goals.md` § Goal 4) — notebooks read JSONL, not the live engine.

**Mental model.** Harriet thinks: "I subscribe a sink, I drive `Game.step(action)`, I get back an `Observation`. Every byte of behavior I care about for the parent note's metric table (`wumpus_idea.md:104-122`) shows up in the ledger as a typed event. If I close the sink and re-instantiate `Game(seed=k)` and re-feed the same actions, I get a byte-identical ledger." Harriet does NOT think about background threads, async event buses, or "logging strategy" — the ledger writes synchronously, ordered, on every event.

**Emotional arc:**

| Phase | Harriet's state | Trigger |
|---|---|---|
| Start | Skeptical — "does this really agree with PC-BASIC?" | first run against a captured BASIC transcript fixture |
| Mid | Trust — seeded replays come back byte-identical | `assert events1 == events2` passes across N seeds and command sequences |
| End | Conviction — the engine is the oracle | LLM divergence-event metrics can be computed post-hoc by joining ledger against the agent's narration |

**Steps:**

1. **Construct + subscribe.** `game = Game(seed=42)`; `sink = JsonlSink(path='session.jsonl')`; `game.events.subscribe(sink)`. Or `Game(seed=42, ledger='session.jsonl')` as sugar. The sink owns the file; the engine knows nothing about disks.
2. **Drive turns.** `obs = game.step(action)` returns an `Observation` (parsed fields + the strings Pat would see). On every effect, the engine emits a typed event to all attached sinks, synchronously, ordered, before `step()` returns.
3. **Observe.** Harriet can inspect `obs`, `game.world_state()` (ground truth — distinct from `Observation`), or read the ledger downstream. The engine never mutates state in `world_state()` (read-only inspection).
4. **Replay.** `Game(seed=42).replay(actions)` produces a byte-identical event sequence; `replay(ledger_path)` reconstructs the world at any turn.
5. **Snapshot/restore.** `snap = game.snapshot()`; `game2 = Game.from_snapshot(snap)`; `game2.step(action)` produces the next observation from the captured state (J4 also depends on this round-trip; the test fixtures live here).
6. **Schema versioning.** Every event carries `schema_version`; new fields are additive; existing fields never change meaning. Notebook code from N versions ago still reads N+k ledgers.

**Shared artifacts consumed:** `Snapshot`, `Observation`, `Event/Ledger record` (the full schema — `[REF] Shared Artifacts Registry`), `seed`, `layout_hash`, `surface_variant` (recorded per event for J2 joins), `RNG cursor` (recorded per event for seeded-replay verification), `VariantConfig` (recorded in ledger header).

**Error paths.**

- **Observer effect** — running with a sink attached changes the event sequence vs. running without. Disqualifying. Tested via paired runs: with sink, without sink, must produce identical event sequence (sink is downstream of emission).
- **Schema drift** — code emits a field not declared in the schema, or vice versa. Synchronous schema validation on write catches this at the first event; engine refuses to start a session that would silently corrupt analysis.
- **Background-thread logging** — engine SHALL NOT emit events from a background thread. Buffer crashes mid-turn lose the in-progress event. Forbidden.
- **Verbosity-up from off** — `goals.md` § Goal 4: harness can turn logging *down* from "log everything," never *up* from "off." Anything not logged is not measurable.
- **`time.time()` / `os.urandom` in engine code** — `goals.md` § Goal 5 cross-cutting: seed is the only entropy. A code-search audit at handoff to DESIGN catches violations.
- **Sink subscription order changes event emission order** — sinks are downstream; emission order is engine-internal and seed-determined. Attaching multiple sinks does not reorder.
- **Ledger missing header** — `Game(seed=k)` without a logged `seed` makes the ledger unreplayable. Ledger header is the first emitted event (`GameStarted` with full `VariantConfig`, `Surface` identifier, `schema_version`).

**Gherkin:**

```gherkin
Scenario: Seeded replay produces byte-identical events
  Given Harriet runs Game(seed=42) with command sequence C
  And Harriet captures the event sequence E1
  When Harriet creates a fresh Game(seed=42) and replays C
  Then the new event sequence equals E1 byte-for-byte

Scenario: Sink attachment does not alter event emission
  Given Harriet runs Game(seed=42) with command sequence C and no sinks
  And Harriet captures the in-memory event sequence E_none
  When Harriet runs Game(seed=42) with command sequence C and a JsonlSink + an in-memory sink attached
  Then the event sequence emitted matches E_none exactly
  # goals.md § Goal 4: logging is complete by default; sinks are downstream of emission.

Scenario: Snapshot round-trip preserves determinism
  Given Harriet runs Game(seed=42) for 10 turns
  And Harriet takes snap = game.snapshot() and continues to turn 20
  And Harriet captures the event sequence E_continuous from turns 11..20
  When Harriet reconstructs Game.from_snapshot(snap) and replays the same actions for turns 11..20
  Then the new event sequence equals E_continuous byte-for-byte

Scenario: Engine refuses to start with a schema-drift sink
  Given a sink declares an event schema older than the engine's emitted schema
  When Harriet attaches the sink and calls Game(...)
  Then construction raises a SchemaVersionMismatch with a clear message
  # goals.md § Goal 4: schema drift surfaces immediately, not three notebooks later.

Scenario: No background-thread logging
  Given a static audit of the engine package
  Then the engine source contains no Thread/asyncio.create_task/concurrent.futures use that emits events
  # Synchronous, ordered logging is a Goal 4 constraint.

Scenario: Ledger header carries everything needed to replay
  Given Harriet runs Game(seed=42, variant=YobVariant(), surface=YobSurface())
  When Harriet reads the first line of the ledger
  Then it parses as GameStarted with schema_version, seed=42, layout_hash, variant_config, surface_variant="yob", wumpus_engine_version
  And nothing in the rest of the ledger depends on engine state not captured in the header
```

---

### J4 — `drive-wumpus-from-host-import`

**Persona:** `mpl-cell-consumer` (the chart for cell D, harebrain).
**Job:** `drive-engine-from-host-import`.
**Surface:** MPL host-import — a pure function that takes a serializable snapshot + action and returns a new serializable snapshot + observation. **Signature blocked-on-mpl-spike** (R2); underlying constraints are knowable + testable today.
**Note.** The MPL chart and the harebrain agent (the LLM in cell D's decide-leaf) ship in *separate, downstream features* — they are not built by this feature. This feature ships the engine half: the constraints the chart will need are tested here, and a thin adapter (when the spike pins the signature) lands either as a tail-end story of this feature or as the first story of the chart feature.

**Mental model.** The MPL chart thinks: "I own world state in my Manifest. At a decide-leaf, I call a host import; it gets an opaque snapshot, calls the engine, gets a new snapshot back, and writes the result back into my Manifest. There is no Python process I control. Each call may start a fresh interpreter; the engine must not assume otherwise."

**Emotional arc (chart author + cell D operator):**

| Phase | Consumer state | Trigger |
|---|---|---|
| Start | Cautious — "the MPL spike hasn't pinned the signature" | first attempt to round-trip a snapshot through the host-import contract (mocked signature) |
| Mid | Relief — snapshot/restore is already byte-identical and engine has no module-level state | `from_snapshot(snap).step(a).snapshot()` round-trips equal a single-process `step(a).snapshot()` |
| End | Confidence — when the spike lands, no engine refactor is needed; only a thin adapter | the spike-shaped signature is implemented as an adapter over the engine's existing `from_snapshot`/`step`/`snapshot` |

**Steps:**

1. **Capture a snapshot.** `snap_t = game.snapshot()` — a JSON-serializable dataclass. No tuples-as-keys, no `random.Random` objects in the payload, no closures. The dataclass schema is versioned alongside the event schema.
2. **Persist.** The MPL chart writes `snap_t` into the Manifest (out of scope for this feature, but the *shape* must permit it — pure data).
3. **Resurrect.** `game_resurrected = Game.from_snapshot(snap_t)` — the engine reconstructs a fully usable `Game` instance. No global initialization side effects. No singleton RNG. The reconstructed `Game` has its `Random` instance restored from the snapshot's RNG cursor.
4. **Step once.** `obs, snap_t1 = game_resurrected.step(action)` (or some shape pinned by the spike) — exactly one turn, returning the new snapshot AND the observation, with byte-identical events emitted to whatever sink the host import wires up (typically an in-memory list returned to the chart).
5. **Return snapshot.** The chart receives `snap_t1` and writes it back to the Manifest. The Python interpreter for that decide-leaf may now exit; the chart has everything it needs.
6. **Verify equivalence.** Property: for any seed `s`, action sequence `A`, and split point `k`, `single_process_run(s, A)` produces a final snapshot byte-identical to `snapshot_split_run(s, A, k)` where the split run takes a snapshot at turn `k`, resurrects from it, and continues.

**Shared artifacts consumed:** `Snapshot` (the serializable dataclass — must be designed for this journey, with serialization round-trip tests as the primary acceptance criterion); `Observation`; `Event` (in-memory sink returned per call); `seed`; `RNG cursor` (must be in the snapshot, not held in an unsnapshotable `random.Random` object alone); `VariantConfig`, `Surface` identifier (both in snapshot — a host-import call must not need to be told them out of band).

**Error paths.**

- **Module-level mutable state in the engine** — any `module.SOME_LIST.append(...)` or singleton-cached RNG bypasses the snapshot. Audited at handoff.
- **`Game()` constructor has side effects on import-time globals** — e.g., it registers a logger, mutates a module-level cache. Forbidden.
- **Snapshot dataclass is not JSON-serializable** — e.g., it contains a `random.Random` instance, a frozenset of frozensets keyed by tuples that don't round-trip through JSON, a Python set in the field type, an `Enum` without a string serialization. Snapshot must declare an explicit serialization contract.
- **RNG state lost across snapshot/restore** — `random.Random(seed)` after N draws is *not* the same state as a freshly seeded Random; the cursor must be captured. Property test: `snap → restore → step` produces the same event as continuing the original would have.
- **MPL spike pins a signature that the engine can't satisfy without refactor** — the *known unknown* of this journey. Mitigation: the spike's expected output is a function-signature shape — if it requires async, the engine's synchronous step path is wrapped by the adapter; if it requires a specific naming, the adapter renames; if it requires multiple return values in a specific order, the adapter destructures. The engine's job is to expose the underlying capability; the adapter shapes it.
- **Long-lived `Game` assumption** — anything that requires `Game` to be held across ticks (e.g., a long-lived database connection, a TCP socket, an open file handle in `Game`) breaks the round-trip. The engine has no such resources.

**Gherkin:**

```gherkin
Scenario: Snapshot round-trip preserves the next event byte-identically
  Given a fresh Game(seed=42) is stepped through actions A1..A10
  And the snapshot is taken at turn 10: snap_10 = game.snapshot()
  When a new Game.from_snapshot(snap_10).step(A11) is performed
  And a different Game(seed=42) is stepped through A1..A11 in one process
  Then the event emitted by the snapshot-resurrected step is byte-identical to the event at turn 11 of the single-process run

Scenario: Snapshot is JSON-serializable
  Given a Game has been stepped through 20 turns
  When the snapshot is JSON-encoded and JSON-decoded back into a snapshot
  And a new Game.from_snapshot(decoded_snap).step(A) is performed
  Then the resulting observation and the next snapshot's internal_state_hash equal those from the in-memory snapshot path

Scenario: Engine has no module-level mutable state
  Given a static audit of the wumpus engine source
  Then no module-level statement creates a mutable container that engine code subsequently writes to
  # goals.md § 5.3: "nothing in the engine assumes a long-lived Python process owns the world."

Scenario: Two parallel game instances do not share state
  Given Game(seed=42) and Game(seed=99) are instantiated simultaneously
  When Game(seed=42).step(A) is performed
  Then Game(seed=99)'s snapshot is unchanged
  # Engine does not lean on any global RNG, global counter, or shared cache.

Scenario: RNG cursor advances across snapshot/restore
  Given Game(seed=42) has consumed N RNG draws (cave gen + some turn-driven draws)
  And game.snapshot() captures the RNG cursor at position N
  When Game.from_snapshot(snap) consumes one more RNG draw
  Then the value drawn equals the (N+1)th draw the original Random(42) would have produced

# BLOCKED-ON-MPL-SPIKE scenario (placeholder; lands when spike pins signature):
# Scenario: Host-import contract round-trip
#   Given the MPL spike has pinned the host-import contract as `f(snap, action) -> (snap', obs, events[])`
#   When the chart wires the wumpus engine into a decide-leaf via that contract
#   Then a Manifest with a captured snapshot can call f, write the returned snap back, and progress the game one turn
#   And the chart's process can exit between turns without affecting the next call
```

---

### Coherence check across journeys

A cross-journey scan to surface contradictions before Phase 3 stories are written.

| # | Coherence claim | Verified |
|---|---|---|
| C1 | Every persona has at least one journey | ✓ — pat (J1), harriet (J2, J3), mpl-cell-consumer (J4) |
| C2 | Every job has at least one journey | ✓ — `play-classic-wumpus` (J1), `instrument-wumpus-play` (J3), `replay-wumpus-deterministically` (J3), `probe-llm-obfuscation-gap` (J2), `drive-engine-from-host-import` (J4) |
| C3 | Every journey traces to at least one job and one persona | ✓ — table at top of section |
| C4 | Shared artifacts are consistent across journeys (no two journeys claim ownership of the same artifact under different shapes) | ✓ — registry below is the SSOT; per-journey lists are consumers, never owners |
| C5 | Surface seam (J2) does not contradict the JSONL ledger (J3) | ✓ — every event carries `surface_variant`; J2's seam-leak test is the same test J3's `surface_variant` field enables |
| C6 | Snapshot/restore (J3) is the same primitive as host-import round-trip (J4) | ✓ — J4 adds the *serialization* constraint on top; J3's in-memory snapshot test is the floor, J4's JSON round-trip test is the ceiling |
| C7 | CLI (J1) and programmatic API (J3) emit equivalent event streams | ✓ — CLI is `Game()` + a renderer subscribed as a sink; J3's "no observer effect" test covers this |
| C8 | The four journeys collectively cover Goals 1–5 of `wumpus_python_goals.md` | Goal 1 (faithful Yob): J1. Goal 2 (extensible without breaking): J1 default + variant-config exercised most directly in DISTILL parametric tests. Goal 3 (Mystery): J2. Goal 4 (observable): J3. Goal 5 (LLM/harness use): J1 (5.1 CLI) + J3 (5.2 API) + J4 (5.3 host-import). ✓ |

---

## Wave: DISCUSS / [REF] Shared Artifacts Registry

Every cross-journey shared piece of state has a single source of truth here. Untracked artifacts are the primary cause of horizontal integration failures and rule-fidelity drift. Engine constants (the parts already audited in the archived `shared-artifacts-registry.md` for `wumpus_classic`) are referenced; this section adds the *new* artifacts introduced by Mystery surface, host-import snapshot, and VariantConfig.

**Two tiers:**
- **Tier A — Cross-journey contract types** (Snapshot, Observation, Event, VariantConfig, Surface). These are new in this wave; they did not exist in the archived registry. Designed as a coherent set across J1–J4.
- **Tier B — Engine constants and runtime artifacts** (DODECAHEDRON, MESSAGES, PROMPTS, seed, RNG cursor, etc.). Mostly re-affirmed from the archived registry, renamed `wumpus_classic → wumpus` per D1, with surface-variant generalization.

---

### Tier A — Cross-journey contract types (NEW)

These types are public API surface — once they ship, changes are breaking (`schema_version` field on each).

#### A1 — `Snapshot`

**Owner:** `wumpus.types.Snapshot` (DESIGN locks the exact module; constructor lives on `Game`).
**Shape (placeholder; DESIGN refines):**

```
Snapshot = {
  schema_version: int,
  engine_version: str,
  seed: int,                    # the integer passed to Game(seed=...) — drawn from OS entropy if None at construction; logged
  rng_cursor: bytes | int,      # full state of the engine's random.Random — sufficient to resume mid-draw
  variant_config: VariantConfig,
  surface_id: str,              # "yob" | "mystery" | "french" | ... — name only, surface code is not in snapshot
  turn: int,
  world: {
    player_room: int,
    wumpus_rooms: list[int],    # length determined by variant_config.wumpus_count
    pit_rooms: list[int],
    bat_rooms: list[int],
    arrows: int,
    initial_layout: ...         # snapshotted at Game(seed=k) for SAME SET-UP=Y replay
  },
  pending_prompt: enum | None,  # if mid-turn awaiting input (e.g., between NO. OF ROOMS and ROOM #)
  pending_arrow_path: list[int] # partially-collected arrow path slots, if any
}
```

**Consumers:**
- J3 — `Game.snapshot()` / `Game.from_snapshot(snap)` for replay + mid-game state capture
- J4 — host-import round-trip; **MUST** be JSON-serializable end-to-end (no `random.Random` object as a field; cursor is bytes/int)
- DESIGN — locks the exact field types and serialization contract
- DISTILL — pins acceptance tests for snapshot round-trip (J3) and JSON round-trip (J4)

**Integration risks:**
- **HIGH** — Snapshot is the host-import contract's foundation (J4). Any non-serializable field added later forces a breaking version bump.
- **HIGH** — Missing `rng_cursor` makes seeded replay diverge after the first post-snapshot draw.
- **MEDIUM** — `pending_prompt` is easy to overlook; without it, a chart that snapshots mid-arrow-path cannot resume.

**Validation:**
- Property test (J3): `Game(seed=s).run(A).snapshot() == Game(seed=s).run(A[:k]).snapshot() ; Game.from_snapshot(that).run(A[k:]).snapshot()` — round-trip equality at the final snapshot.
- Round-trip test (J4): `Snapshot.from_json(snap.to_json()) == snap`.
- Negative test: any `random.Random` object stored as a field fails the JSON round-trip with a clear error, not a silent loss.

#### A2 — `Observation`

**Owner:** `wumpus.types.Observation`.
**Shape (placeholder):**

```
Observation = {
  schema_version: int,
  turn: int,
  surface_variant: str,
  player_room: int,
  adjacencies: list[int],
  senses: list[{kind: "smell"|"draft"|"bats"|<mystery-equivalents>, ...}],
  prompt: enum | None,              # what the engine is awaiting next, or None if turn complete
  rendered_lines: list[str],        # the strings Pat would see this turn (already surface-translated)
  outcome: enum | None,             # win / lose-eaten / lose-pit / lose-out-of-arrows / None
}
```

**Consumers:**
- J1 — CLI renderer reads `rendered_lines` and prints
- J2 — LLM agents receive `rendered_lines` as prompt input
- J3 — harness inspects parsed fields (`player_room`, `senses`) for ground-truth comparison
- J4 — host-import returns Observation alongside snapshot

**Integration risks:**
- **MEDIUM** — `Observation` overlaps with `Event` (Tier A4); the rule: `Observation` is what the *player* sees at the END of a step; `Event` is the *per-effect* engine trace WITHIN the step. Multiple events per observation.
- **MEDIUM** — `rendered_lines` is surface-translated; the parsed fields are surface-invariant. The seam claim in J2 depends on this split.

**Validation:**
- For paired classic/mystery runs (J2), parsed fields are identical; `rendered_lines` is different.

#### A3 — `VariantConfig`

**Owner:** `wumpus.types.VariantConfig`.
**Shape:** the table from `goals.md` § Goal 2 (room_count, topology, wumpus_count, pit_count, bat_count, arrow_count, arrow_max_range, wumpus_move_prob, escalation_rules slot).
**Yob default** is the no-args constructor.

**Consumers:**
- All four journeys — every `Game(...)` call carries a `VariantConfig`, even if defaulted.
- J1 — CLI exposes `--yob` (default) + individual override flags
- J2 — Mystery surface is *orthogonal* to variant config; you can run Mystery on Yob defaults OR Mystery on a non-Yob variant
- DISTILL — parametric tests sweep variant dimensions
- DESIGN — locks the `escalation_rules` slot shape (downstream features for L3/L4 plug in here)

**Integration risks:**
- **HIGH** — Variants must **not** change the internal state schema (`goals.md` § Goal 2 constraint: "two wumpuses means a list of length two, not a new field"). Snapshot (A1) is variant-config-independent in shape.
- **MEDIUM** — `escalation_rules` slot must be designed extensible (additive); L3 / L4 plug into it without rewriting the engine.

**Validation:**
- Yob default produces byte-identical output to BASIC transcript (the J1 fidelity claim).
- Non-Yob variant declares the invariants it relaxes; engine logs `active_variant_set` in `GameStarted`.

#### A4 — `Event` (and the Ledger Record schema)

**Owner:** `wumpus.events` module.
**Shape:** the event types pinned in the archived registry are still the right starter set (`GameStarted`, `PromptIssued`, `ActionChosen`, `MoveAttempted`, `MoveRejected`, `MoveResolved`, `SenseEmitted`, `LocationReported`, `HazardTriggered`, `WumpusStartled`, `PlayerTeleported`, `PlayerEaten`, `ArrowFired`, `ArrowPathStep`, `ArrowMissed`, `ArrowHitWumpus`, `ArrowHitPlayer`, `ArrowCountChanged`, `CrookedPathRejected`, `GameEnded`, `SessionAborted`).

**New required fields on every event (added in this wave; not in archived registry):**

| Field | Purpose | Journey requiring it |
|---|---|---|
| `surface_variant` | classic-vs-mystery `GROUP BY` | J2 |
| `internal_state_hash` | seam-leak detection | J2 |
| `rng_cursor` | per-event seeded-replay verification | J3, J4 |
| `schema_version` | additive evolution; notebooks survive engine upgrades | J3 |
| `actor_node` (optional) | scaffolding-leak tagging (LangGraph harness — `goals.md` § Goal 4 / `wumpus_idea.md:64-78`) | J3 (downstream consumer; engine accepts as optional input field, not engine-emitted) |
| `back_prompted` (optional) | back-prompt convergence metric | J3 (downstream consumer; engine accepts as optional input field) |
| `tokens_in` / `tokens_out` (optional) | tokens-per-turn metric | J3 (downstream consumer; engine reserves the field shape, harness fills it) |

**Consumers:**
- CLI renderer (J1) — translates events to Yob-faithful text under default surface
- JSONL sink (J3) — serializes events to disk, append-only, one line per event
- In-memory sink (J3, J4) — host-import returns events list inline
- Replay verifier (J3, J4) — compares event sequences for byte-identical determinism
- Analysis notebooks (`wumpus_idea.md:104-122` metric table) — every metric must be computable from this stream

**Integration risks:**
- **HIGH** — Event schema is published API; renames are breaking.
- **HIGH** — Adding `surface_variant` and `internal_state_hash` is non-negotiable for J2; the archived registry didn't have them.

**Validation:**
- `schema_version` on every event.
- Schema validation on write (synchronous, fail-fast — `goals.md` § Goal 4).
- DISTILL pins exact event sequences for seeded fixture scenarios.

#### A5 — `Surface`

**Owner:** `wumpus.surfaces` package (interface) — implementations `YobSurface`, `MysterySurface`, future `FrenchSurface`.
**Shape:**

```
Surface (interface) = {
  id: str,                                   # "yob" | "mystery" | ...
  room_label(room_id: int) -> str,           # 1 → "1" (Yob) | 1 → "α" (Mystery)
  sense_string(kind: SenseKind) -> str,      # SMELL → "I SMELL A WUMPUS!" | "YOU DETECT RESONANCE ζ"
  hazard_name(kind: HazardKind) -> str,
  command_token(verb: CommandVerb) -> str,   # SHOOT → "S" | "<mystery-token>"
  command_parse(token: str) -> CommandVerb,  # inverse — needed for input
  prompt_text(kind: PromptKind) -> str,
  instructions_block() -> str,
}
```

**Hard contract:**
1. Surfaces are pure translation layers. No internal mutable state, no engine references.
2. Surface methods are pure functions; constructors may seed internal *display* state (e.g., the symbol map for Mystery) from a separately-declared, logged seed.
3. Surface MUST NOT call into the engine's RNG.
4. Engine code MUST NOT compare or print surface-form strings directly — it operates on internal IDs (`int` for rooms, enums for senses/hazards/commands).

**Consumers:**
- J1 — Yob surface (default)
- J2 — Mystery surface (the obfuscation gap probe); French as a generality smoke-test
- J3 — `surface_variant` field on every event records which surface was active
- J4 — surface identifier in snapshot; chart receives translated strings only at the boundary

**Integration risks:**
- **CRITICAL** — Surface leak (engine references a surface-form string anywhere) destroys the J2 measurement. The structural argument in `goals.md` § Goal 3 rests on the absence of any such leak. Static-audit gate at DESIGN handoff.
- **HIGH** — A surface that consumes engine RNG contaminates J2 (`goals.md` § Goal 3 quote: "if a Mystery run accidentally takes one extra RNG draw...").
- **MEDIUM** — Mystery command-token ambiguity: two distinct verbs must produce distinguishable tokens under translation. Surface validation rejects ambiguous mappings.

**Validation:**
- `internal_state_hash` paired-run agreement test (J2 Gherkin).
- Static audit: no surface-form string literal inside `wumpus.engine` modules.
- Surface contract test: every Surface instance round-trips every CommandVerb (`command_parse(command_token(v)) == v`).

---

### Tier B — Engine constants and runtime artifacts (mostly re-affirmed)

These are mined from the archived `docs/feature/.archive/wumpus-classic-2026-05-20/discuss/shared-artifacts-registry.md`. Renamed `wumpus_classic → wumpus` per D1. Surface-form strings (PROMPTS, MESSAGES) now live behind the Surface interface (A5); the constants below are the Yob surface's *backing data*, but other surfaces have their own.

| Artifact | Source of truth (new path) | Origin | Owning journey | Status vs. archive |
|---|---|---|---|---|
| `DODECAHEDRON` adjacency | `wumpus.constants.DODECAHEDRON` (Yob default topology) | `bas` lines 0130-0160 | J1 (move + sense + arrow); J3 ground-truth | unchanged; now part of `VariantConfig.topology`'s Yob default |
| `SENSE_ORDER` | `wumpus.constants.SENSE_ORDER` | `bas` lines 2020-2120 | J1 | unchanged |
| `HAZARD_ORDER` | `wumpus.constants.HAZARD_ORDER` (wumpus → pit → bat) | `bas` lines 4140-4310 | J1 | unchanged |
| Yob `PROMPTS` | `wumpus.surfaces.yob.PROMPTS` | `bas` source | J1 via Surface (A5) | **moved behind Surface** — was a flat constant in archive |
| Yob `MESSAGES` (incl. win/lose swap) | `wumpus.surfaces.yob.MESSAGES` | `bas` source | J1 via Surface (A5); J3 byte-fidelity tests | **moved behind Surface** |
| `seed` (entropy source) | `Game.__init__(seed=...)` ctor arg, stored as `Game.seed`; written to ledger header | constructor | J1 (CLI `--seed`), J2 (paired runs), J3 (replay), J4 (snapshot field) | unchanged; surfaces in all four journeys |
| `RNG cursor` | `Game._random` state, snapshotted in `Snapshot.rng_cursor` | `random.Random(seed)` | J3 (replay), J4 (snapshot/restore) | **NEW (lifted from implicit) — explicit field for J4** |
| `layout_hash` | `Game._layout_hash` (blake2b over initial entity placement) | computed at construction | J3 (ledger header + replay verification) | unchanged |
| `arrow_count` | `Game._arrows` (init from `VariantConfig.arrow_count`, default 5) | `bas` line 0360 | J1 | unchanged; now variant-configurable |
| `wumpus_startle` distribution | `Game._move_wumpus_startle()` — `FNC(0) ∈ {1..4}`, parameterized by `VariantConfig.wumpus_move_prob` | `bas` lines 3370-3440 | J1 | unchanged at Yob default; now variant-configurable per `goals.md` § Goal 2 table |
| `initial_layout` | `Game._initial_layout` (saved at construction for `SAME SET-UP=Y`) | `bas` lines 0560-0610 | J1 | unchanged; included in `Snapshot.world` |

**Archived registry remains mine-able** for:
- The exact 20×3 dodecahedron adjacency table (lines 9–46 of archived file)
- The full Yob prompt/message strings (archived file lines 81–131)
- The "Validation checklist" at the bottom of the archived registry (still mostly applies; rewritten for J2 surface-leak audit + J4 snapshot-serializability audit)

---

### Cross-artifact integration claims (`must_match_across` from archive, refreshed)

| # | Claim | Across journeys | Failure surface |
|---|---|---|---|
| X1 | `DODECAHEDRON` is the ONLY adjacency table; every consumer (cave gen, sense check, move validation, arrow path) imports it | J1 | "Phantom geography" divergences (`wumpus_idea.md:55`) |
| X2 | `seed` value in ledger header equals `Game.seed` equals the integer the user passed (or the integer the engine drew, if `None`) | J1 (header), J3 (replay), J4 (snapshot) | Unreplayable bug reports |
| X3 | `rng_cursor` snapshot/restore round-trip is byte-exact across snapshot boundary | J3 (mid-game snapshot), J4 (host-import) | Cross-process replay drift |
| X4 | `internal_state_hash` for the same `(seed, action_sequence)` is identical across all surface variants | J2 (paired classic/mystery), J3 (per-event field), J4 (per-snapshot field) | Obfuscation-gap measurement contamination |
| X5 | Win/lose message swap from Yob preserved exactly under the default surface | J1 | Recognition-signal fidelity break |
| X6 | Event schema additive evolution: no field rename, no enum-value rename, no semantic change | J3 (notebooks must survive engine upgrades) | Three-notebooks-later schema drift |
| X7 | Snapshot is JSON-serializable end-to-end | J4 | Host-import contract violation; chart cannot persist state |
| X8 | Engine source contains no `time.time()`, `os.urandom`, module-level RNG access, or background-thread event emission | All four | Silent non-determinism; observer effect |

### Audit gates handed to DESIGN

These are not stories; they are *static audits* run at DESIGN handoff and re-run before any release:

- **Surface-leak audit (J2).** `grep` engine modules for any reference to a Yob-surface string literal. Expected: zero hits outside `wumpus.surfaces.yob`.
- **Determinism-source audit (X8).** `grep` for `time.time`, `time.monotonic`, `os.urandom`, `secrets`, top-level `random.` (without `random.Random` instance access). Expected: zero hits.
- **Snapshot-serializability audit (X7).** `Snapshot.from_json(snap.to_json()) == snap` for a fixture suite of snapshots covering: turn 0, mid-arrow-path, post-bat-teleport, post-startle, terminal-win, terminal-lose.
- **Module-level mutable state audit (J4).** `grep` for module-level mutable containers (lists, dicts, sets, dataclass instances with mutable fields) that engine code subsequently writes to. Expected: zero.

---

## Wave: DISCUSS / [REF] Story Map

Phase 2.5 output. Carpaccio-style: each slice is independently shippable and learnable, ≤1 day for one focused developer (or one Claude session). Per Phase 2 coherence check (C8), the four journeys collectively cover Goals 1–5 of `wumpus_python_goals.md`; the slices below decompose those journeys into the smallest verticals that each deliver a *demonstrable* increment.

### Backbone (big user activities, left to right)

Eight horizontal activities. Each release slices vertically through some subset of these.

| # | Activity | What it means | Journey it lights up |
|---|---|---|---|
| B1 | Construct an engine | `Game(seed=k, variant=V, surface=S)` returns a usable instance | J1, J2, J3, J4 |
| B2 | Receive a turn input | `step(action)` (programmatic) or stdin (CLI); validate; reject non-advancing inputs | J1, J3 |
| B3 | Resolve the world | hazards, startle, arrow walk; mutate snapshot | J1 |
| B4 | Render to the player | `Observation.rendered_lines` (Yob strings) — surface-translated | J1, J2 |
| B5 | Emit the event trace | events fire synchronously to all attached sinks | J1, J2, J3 |
| B6 | Persist + replay | JSONL ledger, schema validation, replay from seed | J3 |
| B7 | Snapshot / restore | `snapshot()` / `from_snapshot()` round-trip, JSON-serializable | J3, J4 |
| B8 | Run a variant or surface | non-Yob VariantConfig, MysterySurface, paired-run hash equality | J2 |

Reading left-to-right: a single turn flows B1 → B2 → B3 → B4 → B5. B6/B7/B8 are observability + portability layers on top.

### Walking Skeleton — R0 (1 day, 1 slice)

A toy-cave end-to-end run that proves the abstractions before any Yob fidelity layers on.

**R0** — *Toy-cave engine round-trips a deterministic step* — `Game(seed=k)` on a hard-coded 3-room linear cave with one wumpus; programmatic `step("move N")` advances player; events fire to an in-memory sink; running twice with the same seed + same actions produces identical event sequences. No CLI yet. No cave gen. No JSONL. No hazards beyond wumpus-bump. No Yob strings (placeholder strings).

The walking-skeleton's *purpose* is to force the architecture (Observation/Event split, Game-as-pure-function-of-state, deterministic-from-seed, in-memory event subscription) into existence on the cheapest possible substrate so the Yob-fidelity work in R1 has somewhere to land.

### Release slices

Conventions for each slice:
- **Pitch:** the elevator pitch in one or two sentences.
- **Demo:** the taste test — what we can show to declare the slice done.
- **Learning hypothesis:** what we expect to discover (the slice is a falsifiable bet).
- **AC sketch:** the acceptance criteria in Given-When-Then shape, abbreviated; full text lands in Phase 3.
- **Depends on:** prior slices that must be done first.
- **Risk:** the failure mode that would invalidate the slice; sometimes "none worth listing."

---

#### Release 0 — Walking Skeleton

**R0** — *Toy-cave engine, deterministic, event-emitting*

- **Pitch:** Build the smallest possible `Game` that round-trips a deterministic step. Programmatic only. 3 rooms in a line. One wumpus, no other hazards. Move-only (no shoot). Placeholder strings.
- **Demo:** `g1 = Game(seed=42); g1.step("move 2"); g1.step("move 3")` produces 4 events (GameStarted, MoveResolved×2, ...). `g2 = Game(seed=42)` with the same actions produces an equal event list.
- **Learning hypothesis:** the Observation/Event split is the right primary distinction; `Game` can be a pure state container with sinks attached for side-effect emission; `random.Random(seed)` as the only entropy source is workable.
- **AC sketch:** *Given* seed and actions, *When* step is called, *Then* event sequence is deterministic. *Given* same seed + actions across two instances, *Then* event sequences are equal.
- **Depends on:** nothing.
- **Risk:** abstractions chosen here propagate everywhere; if the Observation/Event split is wrong, every subsequent slice carries the wrong shape. Mitigation: keep R0 minimal so refactor cost stays low.

---

#### Release 1 — Yob fidelity (CLI playable)

Goal of release: a human at a terminal can run `wumpus` and play Yob's 1973 game with byte-recognizable fidelity. The goals-doc done-criterion #1 ("cell A scripted plays Yob from a seed → ledger byte-identical to BASIC transcript") lands at the *end* of R1, not as a single slice.

**R1-S01** — *Dodecahedron + cave gen from seed*

- **Pitch:** Replace R0's hardcoded 3-room cave with the real 20-room dodecahedron + seeded random entity placement per Yob's `FNB` rejection loop.
- **Demo:** `Game(seed=42).world_state()` shows a layout with 1 wumpus, 2 pits, 2 bats, 1 player, all in distinct rooms, on the audited 20×3 adjacency.
- **Learning hypothesis:** `random.Random(seed)` produces a stable layout across Python minor versions; the `FNB` rejection loop terminates quickly in practice.
- **AC sketch:** *Given* seed `k`, *When* `Game(seed=k)`, *Then* `_initial_layout` is deterministic and entity rooms are all distinct.
- **Depends on:** R0.
- **Risk:** Python random's stability across versions is *not* a Python guarantee. If it ever drifts, all replays drift. Mitigation: pin the Python version in `pyproject.toml` (`requires-python >= 3.11`) and add a regression test that `random.Random(42).randrange(20)` equals a known constant — catches drift at CI time.

**R1-S02** — *Sense emit on entry (Yob L-array order)*

- **Pitch:** On entering a room, emit `SenseEmitted` events for wumpus/pit/bat adjacency in Yob's L-array order. Multiple adjacent same-kind hazards emit the same event repeatedly.
- **Demo:** Forced-adjacency fixture: player enters a room adjacent to wumpus + pit → `SenseEmitted(WUMPUS_SMELL)` fires before `SenseEmitted(PIT_DRAFT)`.
- **Learning hypothesis:** the `SENSE_ORDER` table is sufficient; nothing about Yob's BASIC iteration leaks beyond the ordering.
- **AC sketch:** *Given* a room with N adjacent hazards of kinds K1..KN, *When* entered, *Then* N `SenseEmitted` events fire in `SENSE_ORDER` and precede the `LocationReported` event.
- **Depends on:** R1-S01.
- **Risk:** none worth listing.

**R1-S03** — *Move + wumpus bump + startle*

- **Pitch:** `step("M <room>")` validates adjacency, advances player; on entry to the wumpus's room emits `HazardTriggered(WUMPUS)` and runs the startle distribution (`FNC`: 75% move to adjacent, 25% stay). If startled wumpus lands on player → eaten → `GameEnded(eaten_after_bump)`.
- **Demo:** Forced fixture: player moves into wumpus's room, RNG forced to "stay" → game ends.
- **Learning hypothesis:** the `FNC` distribution implementation is the right approach; the recursive "wumpus lands on player" is detectable.
- **AC sketch:** *Given* wumpus in adjacent room and forced startle = stay, *When* player moves there, *Then* `GameEnded(eaten_after_bump)` fires.
- **Depends on:** R1-S01.
- **Risk:** none worth listing.

**R1-S04** — *Move + pit + bat teleport (recursive)*

- **Pitch:** Move into pit → `GameEnded(fell_in_pit)`. Move into bat room → `PlayerTeleported` to a random adjacent room → recursive re-entry (re-emits sense + location, may trigger another hazard).
- **Demo:** Forced fixture: bat target is a pit room → game ends with pit message.
- **Learning hypothesis:** the recursive bat-teleport pattern fits the engine's step model without a recursion-depth issue (cave-gen no-co-location invariant prevents pathological chains).
- **AC sketch:** *Given* bat-target rolls to a pit, *When* player moves into bat room, *Then* both BAT_SNATCH and FELL_IN_PIT events fire, in that order, before `GameEnded(fell_in_pit)`.
- **Depends on:** R1-S03.
- **Risk:** none worth listing.

**R1-S05** — *Shoot path collection + crooked-path rejection*

- **Pitch:** `step("S")` starts a shoot sub-state-machine: prompt `NO. OF ROOMS(1-5)?`, then per-slot `ROOM #?`. Reject path entries where `P(K) == P(K-2)` (Yob crooked-arrow rule). Emits `ArrowFired` when path collection completes.
- **Demo:** Shooter enters path `[7, 14, 7]` → engine emits `CrookedPathRejected(slot=3)` and re-prompts that slot only.
- **Learning hypothesis:** the engine's "pending_prompt + pending_arrow_path" state in Snapshot (Tier A1) is the right shape for mid-turn state capture — a snapshot mid-collection round-trips.
- **AC sketch:** *Given* path entries [7, 14], *When* the third entry is 7, *Then* `CrookedPathRejected` fires and re-prompt is for slot 3.
- **Depends on:** R1-S01.
- **Risk:** the mid-prompt snapshot shape might not be quite right here; this is the slice where we find out. R3-S04 cleans up if needed.

**R1-S06** — *Arrow walk + hit + miss + self-shot + out-of-arrows*

- **Pitch:** Walk the collected arrow path through the dodecahedron; on a non-connecting hop, take a random adjacent room (`FNB(1)`) and stop checking remaining path. If final-room match with player → self-shot (Yob's bug-for-bug rule, *not* mid-path). If lands on wumpus → kill. Otherwise → miss + wumpus startle + decrement arrow + check out-of-arrows.
- **Demo:** Forced crooked-arrow-through-player fixture passes WITHOUT killing the player mid-path. Separate forced-final-room-equals-player fixture DOES kill.
- **Learning hypothesis:** the bug-for-bug fidelity is genuinely implementable as a final-room check, not a per-step check.
- **AC sketch:** see J1 Gherkin "Crooked arrow passing through Pat's room does not kill Pat mid-path".
- **Depends on:** R1-S05.
- **Risk:** Yob's arrow walk has subtle branching (line 3170-3210); honest read of the BASIC source matters here. Mitigation: pair the slice with a re-read of `wumpus.gwbasic.bas` before implementation.

**R1-S07** — *Terminal state + Yob win/lose message swap + SAME SET-UP*

- **Pitch:** On any terminal state, emit `GameEnded(outcome, message_kind)`. The CLI renderer prints HA HA HA on lose, HEE HEE HEE on win (Yob's swap). `SAME SET-UP (Y-N)?` Y restores `Game._initial_layout` exactly.
- **Demo:** Forced-win fixture prints HEE HEE HEE. Forced-loss fixture prints HA HA HA. `SAME SET-UP=Y` → second game's layout_hash equals first.
- **Learning hypothesis:** the swap is robust against any "helpful corrector" in the engine code; the recognition-signal claim holds.
- **AC sketch:** see J1 Gherkin "Yob's swapped win message" and "SAME SET-UP=Y restores the initial layout exactly".
- **Depends on:** R1-S03, R1-S04, R1-S06.
- **Risk:** none worth listing.

**R1-S08** — *Instructions block (incl. RAMDOM typo)*

- **Pitch:** On `INSTRUCTIONS (Y-N)?` Y, print Yob's verbatim instruction block — including the typo `RAMDOM` in the arrow-deflection sentence.
- **Demo:** Byte-comparison: engine output for `Y` answer to instructions matches a captured Yob transcript byte-for-byte through the end of the instruction block.
- **Learning hypothesis:** the byte-for-byte fidelity story holds for the largest single fixed-text block in the game.
- **AC sketch:** *Given* user answers Y to INSTRUCTIONS, *Then* output contains the exact string "RAMDOM" once.
- **Depends on:** R0 (CLI shell needed by then).
- **Risk:** none.

**R1-S09** — *CLI subprocess-safe (line-buffered, no curses/SDL/readline)*

- **Pitch:** Wire the engine to a CLI that `pexpect`/`wexpect` can drive without deadlock. Line-buffered stdout (`flush=True` after every print or `sys.stdout.reconfigure(line_buffering=True)`). No SDL window, no curses, no readline mode that confuses non-TTY stdin.
- **Demo:** A pexpect (Linux/macOS) or wexpect (Windows) smoke test wraps `wumpus` and drives a fixed action sequence to a known terminal state without hanging.
- **Learning hypothesis:** Python's default stdio behavior under subprocess wrapping is what we expect, modulo explicit `flush=True`.
- **AC sketch:** see J1 Gherkin "Subprocess wrapper (pexpect/wexpect) does not hang on prompt".
- **Depends on:** R1-S07.
- **Risk:** Windows + wexpect is known-finicky. Mitigation: get this working on one platform first; document the other as a Phase 3 risk.

**R1-S10** — *Byte-identical BASIC transcript regression fixture suite*

- **Pitch:** Capture N (suggest: 10) PC-BASIC + GW-BASIC transcripts for `wumpus.gwbasic.bas` driven by deterministic input scripts and fixed seeds. Engine output for the same seed + input MUST match byte-for-byte. **This slice is the goals-doc done-criterion #1.**
- **Demo:** All N fixtures pass byte-comparison in CI.
- **Learning hypothesis:** every Yob mechanic R1-S01 through R1-S08 has been gotten right; if any failed, this slice surfaces it precisely.
- **AC sketch:** *Given* fixture `f_i` with seed `s_i` and inputs `I_i`, *When* engine runs with the same `(s_i, I_i)`, *Then* stdout equals `f_i.stdout` byte-for-byte.
- **Depends on:** R1-S01 through R1-S09.
- **Risk:** capturing BASIC transcripts deterministically requires a seeded `5 RANDOMIZE <seed>` patch line (per `wumpus/experiments/g_wild_baseline/README.md` caveat). This is a prerequisite, not a sub-slice — flag it in `[REF] Pre-requisites`.

---

#### Release 2 — Harness usable (ledger + replay)

Goal of release: any non-CLI consumer (cells A, B, C, E, F, G) can run the engine programmatically, get a typed event stream, persist it as JSONL, and replay it.

**R2-S01** — *Schema v1 event types + JSONL sink + schema validation on write*

- **Pitch:** Define all event dataclasses (per Tier A4) with `schema_version=1`. JSONL sink writes one event per line, synchronously. Schema validation rejects malformed events at emission time.
- **Demo:** Run R1-S10's fixture suite with `--ledger=session.jsonl` attached; resulting JSONL has one line per event, schema-validates clean.
- **Learning hypothesis:** synchronous schema validation is fast enough to leave on by default.
- **AC sketch:** see J3 Gherkin "Engine refuses to start with a schema-drift sink" and "No background-thread logging".
- **Depends on:** R1-S07.
- **Risk:** if the schema validator is too slow (>1ms per event), it'll show up in long property tests. Mitigation: benchmark in this slice; if slow, switch to dataclass-based validation rather than Pydantic.

**R2-S02** — *Ledger header (GameStarted with full context) + replay from ledger*

- **Pitch:** First event is `GameStarted` with `schema_version`, `engine_version`, `seed`, `layout_hash`, `variant_config`, `surface_id`. `replay(ledger_path)` reconstructs world at any turn by re-running from the header.
- **Demo:** Take a fixture run's ledger; `replay(ledger).advance_to(turn=15).world_state()` equals the original run's world at turn 15.
- **Learning hypothesis:** the header is sufficient to replay — nothing else is needed (no separate save file).
- **AC sketch:** see J3 Gherkin "Ledger header carries everything needed to replay".
- **Depends on:** R2-S01.
- **Risk:** none.

**R2-S03** — *Per-event rng_cursor + internal_state_hash + observer-effect property*

- **Pitch:** Every emitted event carries `rng_cursor` (state of `Game._random` after this event's draws) and `internal_state_hash` (hash of full world state). Add the property test that running with and without a JsonlSink produces identical in-memory event sequences.
- **Demo:** Property test passes: 100 seeded runs × paired sink/no-sink check all produce identical event sequences.
- **Learning hypothesis:** the observer-effect-absence claim is structurally true given the sink-is-downstream-of-emission design.
- **AC sketch:** see J3 Gherkin "Sink attachment does not alter event emission".
- **Depends on:** R2-S02.
- **Risk:** none.

---

#### Release 3 — Snapshot / host-import readiness

Goal of release: the J4 underlying constraints are testable (snapshot/restore byte-identical round-trip, JSON-serializable, no module-level state, parallel-instance isolation). The MPL-spike-pinned signature comes later as an adapter.

**R3-S01** — *Snapshot dataclass + in-memory round-trip*

- **Pitch:** `Game.snapshot()` returns a `Snapshot` dataclass (Tier A1 shape). `Game.from_snapshot(snap)` reconstructs. Property: at any turn `k`, `Game(seed=s).run(A[:k]).snapshot()` round-tripped through `from_snapshot().run(A[k:]).snapshot()` equals the single-process `Game(seed=s).run(A).snapshot()`.
- **Demo:** 1000-action property test passes at every split point.
- **Learning hypothesis:** the Snapshot shape covers everything; mid-prompt state (pending_arrow_path, etc.) is correctly captured.
- **AC sketch:** see J4 Gherkin "Snapshot round-trip preserves the next event byte-identically".
- **Depends on:** R2-S03 (needs the rng_cursor field).
- **Risk:** Snapshot may need extension for mid-prompt states surfaced in R1-S05/R1-S06. Mitigation: design R1-S05 with snapshot serialization in mind from the start.

**R3-S02** — *Snapshot JSON round-trip*

- **Pitch:** `Snapshot.to_json() / from_json()` preserves byte-identical state, including RNG cursor encoding. Fixture suite: turn 0, mid-arrow-path, post-bat-teleport, post-startle, terminal-win, terminal-lose.
- **Demo:** All fixtures round-trip through JSON file + read + restore + step and produce events identical to the in-memory path.
- **Learning hypothesis:** the snapshot shape really *is* JSON-serializable; nothing snuck in an unserializable field.
- **AC sketch:** see J4 Gherkin "Snapshot is JSON-serializable".
- **Depends on:** R3-S01.
- **Risk:** Python's `random.Random` state pickles but doesn't JSON-serialize natively. Mitigation: explicit encoding via `random.Random.getstate()` → tuple → base64-encoded bytes in the JSON. Documented as a serialization convention.

**R3-S03** — *Module-state audit + parallel-instance isolation property*

- **Pitch:** Static grep audit for module-level mutable state, `time.time`, `os.urandom`, top-level `random.`, background-thread event emission. Plus a property test: 100 parallel `Game(seed=k_i)` instances stepping concurrently never observe each other's state.
- **Demo:** Grep audit exits with zero hits in CI; parallel property test passes.
- **Learning hypothesis:** the engine genuinely has no shared mutable state. If audit finds anything, fix it in this slice.
- **AC sketch:** see J4 Gherkin "Engine has no module-level mutable state" and "Two parallel game instances do not share state".
- **Depends on:** R3-S02.
- **Risk:** the audit may surface things that need refactoring elsewhere. Time-boxed: if the audit finds >2 violations, split the cleanup into a follow-up slice; if 0–2, fix in-place.

---

#### Release 4 — Variant + surface seam

Goal of release: J2's obfuscation gap measurement is runnable. A MysterySurface paired against YobSurface produces equal `internal_state_hash` at every turn under translation-equivalent actions.

**R4-S01** — *VariantConfig type + Yob default + non-Yob smoke (arrow_count variant)*

- **Pitch:** `VariantConfig` dataclass holds the dimensions from `goals.md` § Goal 2 table. `VariantConfig()` is Yob defaults. `VariantConfig(arrow_count=3)` is a non-Yob variant. `GameStarted` event records the active VariantConfig.
- **Demo:** `Game(seed=42, variant=VariantConfig(arrow_count=3))` plays through to out-of-arrows in 3 misses; same seed with default plays through 5.
- **Learning hypothesis:** variants don't change internal schema (the constraint from `goals.md` § Goal 2); the engine's hazard/arrow/sense code is genuinely parameterized.
- **AC sketch:** *Given* non-Yob `arrow_count`, *When* engine runs, *Then* terminal state on out-of-arrows triggers at the configured count.
- **Depends on:** R1-S06, R3-S01 (snapshot carries variant_config).
- **Risk:** parameterization may surface hard-coded Yob assumptions (e.g., `arrows=5` in a constant). Catching these IS the slice's purpose.

**R4-S02** — *escalation_rules slot (extension point, empty)*

- **Pitch:** `VariantConfig.escalation_rules: list[EscalationRule]` is a public extension slot. `EscalationRule` is a Protocol/ABC; the engine consults it at specific decision points (TBD in DESIGN). For this slice: define the protocol + a no-op `IdentityRule()` and verify a Yob run with `escalation_rules=[IdentityRule()]` is byte-identical to a Yob run with `[]`.
- **Demo:** R1-S10 fixture suite re-run with `escalation_rules=[IdentityRule()]` — byte-identical.
- **Learning hypothesis:** the slot is non-intrusive at default; downstream L3/L4 features can plug in.
- **AC sketch:** *Given* `escalation_rules=[IdentityRule()]`, *Then* engine output matches the no-rules run byte-for-byte.
- **Depends on:** R4-S01.
- **Risk:** the slot's exact API is a DESIGN decision; this slice may need to defer the API and just punch the hole. Acceptable.

**R4-S03** — *Surface interface + YobSurface (strings moved out of engine constants)*

- **Pitch:** Define the `Surface` interface (Tier A5 shape). Implement `YobSurface` with all the Yob strings (lifted from R1's `wumpus.constants.PROMPTS` and `MESSAGES`). Engine code refactored to use `surface.prompt_text(...)`, `surface.sense_string(...)`, etc.
- **Demo:** R1-S10 fixture suite re-run after the refactor — byte-identical output.
- **Learning hypothesis:** the surface boundary is locatable; the refactor doesn't surface any "where do I print this from?" ambiguity.
- **AC sketch:** *Given* the refactor lands, *Then* R1-S10 fixtures all still pass.
- **Depends on:** R1-S10.
- **Risk:** the refactor may be wider than expected; some engine code may not have a natural "ask the surface" hook. Mitigation: time-box; if the refactor stalls, defer the un-refactored cases as known leak sites for R4-S04 to flag.

**R4-S04** — *Surface-leak audit*

- **Pitch:** Static `grep` of engine modules (`wumpus.engine.*`) for any reference to a Yob-surface string literal. Expected: zero hits outside `wumpus.surfaces.yob`. CI gate.
- **Demo:** Audit script runs in CI, fails the build on any hit.
- **Learning hypothesis:** the structural seam claim (J2's foundation) holds; nothing in the engine references a Yob string.
- **AC sketch:** see J2 Gherkin "Engine code paths reference no surface-form strings".
- **Depends on:** R4-S03.
- **Risk:** R4-S03's known-leak sites get flagged here; if any are genuinely necessary (e.g., a debug log inside the engine), it's a real architecture issue and the slice escalates.

**R4-S05** — *MysterySurface + paired-run internal_state_hash equality property*

- **Pitch:** Implement a `MysterySurface` with a fixed-but-arbitrary symbol map (no surface-level RNG). Paired property test: `Game(seed=k, surface=Yob())` and `Game(seed=k, surface=Mystery())` driven with translation-equivalent actions produce equal `internal_state_hash` at every turn.
- **Demo:** 100-seed × 50-turn paired property test passes.
- **Learning hypothesis:** the seam is structural, not cosmetic. J2's obfuscation gap measurement is sound.
- **AC sketch:** see J2 Gherkin "Paired classic and mystery runs produce identical internal trajectories" and "Mystery surface does not consume engine RNG".
- **Depends on:** R4-S04, R2-S03 (needs internal_state_hash field).
- **Risk:** the slice may surface that some Yob mechanic encoded a surface-form decision (e.g., command parsing was string-based at the wrong layer). If so, R4-S03 wasn't deep enough — fix in this slice.

**R4-S06** — *FrenchSurface smoke (surface generality)*

- **Pitch:** Implement a second non-Mystery surface (`FrenchSurface`) as a generality smoke test — Mystery isn't the only test. Paired Yob-vs-French run produces equal `internal_state_hash`.
- **Demo:** Paired property test passes with French surface; ledger emits `surface_variant="french"`.
- **Learning hypothesis:** the surface system is general, not Mystery-shaped.
- **AC sketch:** see J2 Gherkin "A second non-Mystery surface (FrenchSurface) drops in without engine changes".
- **Depends on:** R4-S05.
- **Risk:** none worth listing.

---

#### Release 5 — Tail (blocked + optional)

Goal of release: ship the items that depend on external work (the MPL spike) or that are nice-to-have polish. R5 is not required for the feature to be "done" per goals-doc done-criteria #1–4; it gates done-criterion #3.

**R5-S01** — *Host-import adapter (BLOCKED-ON-MPL-SPIKE)*

- **Pitch:** Once the MPL spike (`wumpus_idea.md:147`) lands and pins the host-import signature, implement a thin adapter `wumpus.host_import` that exposes the engine's `from_snapshot/step/snapshot` capability in the spike-pinned shape.
- **Demo:** A test chart in the harebrain package calls the adapter and round-trips a turn through the host-import contract.
- **Learning hypothesis:** the adapter really is thin — the engine's underlying capability is the right shape.
- **AC sketch:** see J4 Gherkin commented placeholder "Host-import contract round-trip".
- **Depends on:** the MPL spike (external), R3-S03 (parallel-instance isolation).
- **Risk:** **R2 from `[REF] Wave Decisions`** — the spike-pinned signature may surface a constraint the engine doesn't satisfy. Mitigation: R3-S01/S02/S03 cover the *known* constraints today; the adapter only fails if the spike adds a *new* constraint, which would be a real DESIGN issue.

**R5-S02** — *Variant parametric property tests (broader sweep)*

- **Pitch:** Property tests sweep `VariantConfig` dimensions beyond R4-S01's smoke (wumpus_count ∈ {1,2,3}, room_count ∈ {10,20,30}, etc.). Engine MUST not crash and snapshot round-trip MUST hold for all combinations.
- **Demo:** 500-config property test passes.
- **Learning hypothesis:** the variant parameterization is robust beyond Yob-default-plus-arrow-count.
- **AC sketch:** *For all* VariantConfig combinations in the swept space, *Then* engine runs to a terminal state without crash and snapshot round-trips byte-identically.
- **Depends on:** R3-S01, R4-S01.
- **Risk:** the sweep will surface bugs in non-Yob variants. Catching them IS the slice's purpose; they get logged as their own slices if found.

---

### Slice count + effort estimate

| Release | Slices | Days | Cumulative |
|---|---:|---:|---:|
| R0 walking skeleton | 1 | 1 | 1 |
| R1 Yob fidelity | 10 | 10 | 11 |
| R2 ledger | 3 | 3 | 14 |
| R3 snapshot | 3 | 3 | 17 |
| R4 variant + surface | 6 | 6 | 23 |
| R5 tail (blocked + optional) | 2 | 2 + spike-delay | 25 + spike |
| **Total** | **25** | **~25 days + MPL spike** | |

This matches the Phase 1.5 verdict's ~18–25 day estimate (the upper bound). Phase 1.5's claim that "the effort signal is a Phase 2.5 problem, not a Phase 1.5 problem" is now testable: if R0–R4 deliver in ~23 days, the verdict holds. If they stretch to 35+ days, Phase 1.5 should be revisited (and the split alternative reconsidered before R5).

### Priority Rationale

**R0 first** because the abstractions chosen there propagate everywhere. A wrong R0 means a costly refactor across every subsequent slice.

**R1 before R2/R3/R4** because Yob fidelity is the goals-doc's primary done-criterion (#1), the BASIC transcript regression test is the strongest *external* validation we can build, and every subsequent release builds on the substrate R1 produces. Mathematically: R2/R3/R4 each independently could come before R1, but each would face the same risk of being invalidated by a Yob-fidelity bug discovered later.

**R2 before R3** because the ledger schema is *referenced* by Snapshot (Tier A1 — Snapshot carries an `engine_version` that must match the ledger's `engine_version`; both come from the same constants). Building Snapshot first would force a guess about the schema; building the schema first means Snapshot just imports.

**R3 before R4** because R4-S01 (VariantConfig) is recorded in Snapshot (Tier A1), and R4-S03 (Surface interface) requires the engine to be already snapshot-friendly before the refactor lands (the refactor is wider if Snapshot is also being moved around).

**R5 last** because R5-S01 is genuinely blocked on the MPL spike (external dependency), and R5-S02 is non-blocking polish; neither is on a critical path.

**Within R1, the 10 slices follow Yob's own structural decomposition** (cave gen → sense → move → shoot → terminal → instructions → CLI → regression fixture), which matches the natural test-of-test layering: each slice's acceptance test depends on the prior slices' code being correct.

### Demo cadence

Every slice is independently demoable. Suggested cadence:
- R0 → ~1 day in: "the engine exists; here's a 3-room toy run."
- R1-S10 → ~11 days in: "byte-identical Yob — here are 10 captured BASIC transcripts the engine matches exactly."
- R2-S03 → ~14 days in: "every game emits a ledger; replay byte-identical from seed."
- R3-S03 → ~17 days in: "snapshot round-trips through JSON across processes; engine has no shared state."
- R4-S06 → ~23 days in: "Mystery surface produces equal internal-state-hash trajectories to Yob across 100 seeds — the obfuscation-gap measurement substrate is sound."
- R5 → spike-dependent.

The five demos line up with the goals-doc's five done-criteria.

### What's deferred to Phase 3 from this story map

- Full AC text per slice (the Given-When-Then expansions of the AC sketches above)
- DoR validation per story (9-item checklist)
- Story IDs (currently slice IDs; Phase 3 maps slice → story ID and writes the LeanUX statement)
- Outcome KPIs per slice (some are obvious — R1-S10's KPI is "10/10 BASIC fixtures pass" — others need quantification)
- The persona traceability matrix (each slice → which persona's job it serves)
- Cross-references to the elephant-carpaccio learning-hypothesis confirmations (this map's hypotheses become tracked claims in Phase 3)

---

## Wave: DISCUSS / [REF] User Stories

**Pending — Phase 3. Slice briefs land in `slices/slice-NN-*.md`; each story carries an Elevator Pitch + AC.**

---

## Wave: DISCUSS / [REF] Acceptance Criteria

**Pending — Phase 3. Embedded per story.**

---

## Wave: DISCUSS / [REF] Outcome KPIs

**Pending — Phase 3.**

---

## Wave: DISCUSS / [REF] DoR Validation

**Pending — Phase 3. 9-item gate per story.**

---

## Wave: DISCUSS / [REF] Wave Decisions

Locked decisions overriding the archived prior wave (`docs/feature/.archive/wumpus-classic-2026-05-20/`):

| D# | Decision | Rationale | Supersedes |
|---|---|---|---|
| D1 | Package location: `python/packages/wumpus/` | Matches the new goals doc; the archived `wumpus_classic/` name implied "there will be a non-classic" which is now false — variants are config on the same engine | Archived Decision 1 (`wumpus_classic/`) |
| D2 | Three first-class surfaces: CLI, programmatic `Game.step()` API, MPL host-import — none secondary | Goals doc § 5.1/5.2/5.3; cross-cutting feature type | New |
| D3 | Mystery surface seam IN-SCOPE; variant-config IN-SCOPE; `escalation_rules` slot IN-SCOPE (rules ship in downstream features) | Goals doc § 2, § 3; user answer Q2/Q4 | `vision.md` OUT-OF-SCOPE list contradicts — see `[REF] Changed Assumptions` |
| D4 | L2 ("wumpus moves when startled") is part of Yob baseline (`FNC` distribution); L3/L4 ship as downstream features in the `escalation_rules` slot | Goals doc § 1 design table + § 2 escalation slot; user answer Q4 | New |
| D5 | Cross-package engine ↔ experiments imports: **DEFERRED to DESIGN**. DISCUSS states constraint only: experiments import the engine without source mods, without hand-rolled `sys.path` injection | User answer Q1 — solution-architect picks the mechanism | New |
| D6 | Host-import surface IN-SCOPE WITH spike-blocker note. Story carries `validation: blocked-on-mpl-spike` for the exact function signature; underlying constraints (no module-level state, snapshot/restore round-trip, no singleton RNG) are knowable + testable now | User answer Q3; goals doc § 5.3 | New |
| D7 | Engine has no framework dependencies (no LangChain, LangGraph, MPL). Plain Python | Goals doc § 5 cross-cutting constraints | New (consistent with archived) |
| D8 | Determinism contract: seed + variant + input transcript reconstructs the game exactly. No `time.time()`, no untracked `os.urandom`, no `RANDOMIZE TIMER` equivalent | Goals doc § 5 cross-cutting constraints | New (consistent with archived) |
| D9 | Subprocess-safe CLI: no SDL, no curses, no readline mode that confuses non-TTY stdin. `sys.stdout` line-buffered or explicit `flush=True` per print | Goals doc § 5.1 | New (consistent with archived) |
| D10 | Synchronous, ordered, schema-validated JSONL logging. Background threads forbidden. Logging is **complete by default**; the harness turns verbosity down, never up from "off" | Goals doc § 4 constraints | New (consistent with archived) |
| D11 | Bug-for-bug fidelity. `RAMDOM` typo preserved; crooked-arrow-passes-through-player preserved; GW-BASIC RND semantic preserved. Each preserved mistake gets a one-line comment in source pointing at the BASIC line it mirrors | Goals doc § 1 "Mistakes — verbatim" | New (the archived feature was less explicit about this) |

**Risks surfaced (PO-level, handed to DESIGN):**

- **R1 — no DIVERGE wave was run.** All five jobs carry `synthesized-from-goals-doc` validation; refinements should happen when real ODI interviews exist. Mitigation: stories cite the goals-doc lines they refine; reviewer applies extra scrutiny to JTBD framing.
- **R2 — MPL spike not done.** US-10 (host-import determinism contract) has `validation: blocked-on-mpl-spike` for the function signature. Mitigation: split the story so the **underlying** constraints (snapshot/restore round-trip, no module-level state) are tested in DELIVER independently of the eventual signature.
- **R3 — back-propagation contradicts the existing `vision.md`.** See `[REF] Changed Assumptions`. Mitigation: vision.md edit lands as part of DISCUSS handoff; reviewer confirms before DESIGN proceeds.

---

## Wave: DISCUSS / [REF] Changed Assumptions

Per back-propagation contract. SSOT files are updated in-place at handoff; quotes preserved here.

### Change 1 — vision.md OUT-OF-SCOPE list

**Source**: `docs/product/vision.md` § "Out of scope for this feature"

**Original text (verbatim)**:

> - MPL integration (separate package, separate feature)
> - LLM player implementations (cells D, E, F — separate features)
> - Rule extensions: WUMP2 cave variants, WUMP3 hazard variants, escalation-ladder rules L2-L4

**Proposed new text** (to land in `vision.md` at handoff):

> - LLM player implementations (cells D, E, F — separate features)
> - WUMP3 hazard variants (separate feature; out of scope for `wumpus`)
> - Escalation-ladder rules L3 ("partial observability") and L4 ("non-dodec graph") — separate features that drop into the `escalation_rules` slot exposed by `wumpus`
> - GUI, web port, or graphical map rendering
>
> **In scope (contrast):** MPL host-import surface (the engine half — the chart and the LLM agent ship in separate features); variant-config including WUMP2-style room/hazard/arrow counts and wumpus-move probability; Mystery Wumpus surface seam; L2 ("wumpus moves when startled") is already part of Yob baseline.

**Rationale**: The new goals doc (`wumpus/docs/wumpus_python_goals.md`) explicitly lists all three excluded items as IN-SCOPE for the engine. § 5.3 puts the host-import surface in the engine; § 2 puts the variant config (WUMP2-shaped dimensions) in the engine with `escalation_rules` as a public extension slot; § 3 puts the Mystery surface seam in the engine. The vision.md list predates the goals doc and was written when "wumpus_classic" was scoped narrower.

### Change 2 — vision.md package name

**Source**: `docs/product/vision.md` § "This repository delivers, in dependency order:" → item 1

**Original text (verbatim)**:

> 1. **A faithful classic Hunt the Wumpus** (`python/packages/wumpus_classic/`) — Yob 1973 rules, byte-recognizable output, seedable for replay, instrumented for harnessing. The current feature.

**Proposed new text**:

> 1. **A faithful classic Hunt the Wumpus and its declared variants** (`python/packages/wumpus/`) — Yob 1973 rules at the default, byte-recognizable output, seedable for replay, instrumented for harnessing, with a surface seam for Mystery Wumpus and a variant-config slot for room/hazard/arrow counts and the `escalation_rules` extension point. The current feature.

**Rationale**: Package name change per Decision 1 (this wave) supersedes archived Decision 1 (`wumpus_classic/`). The "classic" framing was misleading once Mystery and variant-config landed on the same engine.

### Change 3 — vision.md role table

**Source**: `docs/product/vision.md` § "wumpus_classic plays three concurrent roles, by design:"

**Original text** uses `wumpus_classic` and lists three consumers (player at terminal | MPL chart downstream | experiment harness).

**Proposed new text**: rename to `wumpus`, add a fourth row for the **harebrain agent (cell D) via host import**, which is structurally distinct from "MPL chart (downstream) — rule reference" (the original meaning was "chart authors read the engine source to crib rules into MPL"; the new meaning is "chart at runtime imports the engine and round-trips a turn").

| Consumer | Role | What it needs |
|---|---|---|
| Player at a terminal | The game | A CLI that feels like 1973 |
| Experiment harness (cells A, B, C, E, F, G) | Ground-truth oracle | Deterministic seeded replay + structured event stream + programmatic `Game.step()` |
| MPL chart at design time | Rule reference | Auditable, line-traceable rules from `wumpus.gwbasic.bas` |
| MPL chart at runtime (cell D) | Host-import callee | Snapshot/restore round-trip + serializable inputs/outputs + no module-level state |

**Rationale**: The host-import surface is now first-class (Decision 2 this wave). The original three-role table conflated "chart authors crib rules" with "chart runtime calls engine."

### Change 4 — journeys/play-classic-wumpus.yaml

**Source**: `docs/product/journeys/play-classic-wumpus.yaml`

**Original text (verbatim)**:

```yaml
# SSOT mirror of docs/feature/wumpus-classic/discuss/journey-play-classic-wumpus.yaml
# Updated as the feature evolves. Do not edit one without the other (or use a sync check).

$ref: ../../feature/wumpus-classic/discuss/journey-play-classic-wumpus.yaml
```

**Proposed new text**: Phase 2 of this wave will produce 2–4 journey YAMLs under `docs/product/journeys/` (candidates: `play-classic-wumpus`, `play-mystery-wumpus`, `instrument-wumpus-session`, `drive-wumpus-from-host-import`). The dangling `$ref` is removed; each new journey is a real document.

**Rationale**: The archived feature path no longer exists; the `$ref` was broken on the day the archive moved. Splitting by journey (per persona/surface) is more honest than widening a single classic-only journey.

### Change 5 — jobs.yaml job statements

**Source**: `docs/product/jobs.yaml`

**Refinements** to all three existing jobs (statements + four-forces are sharpened with the goals-doc context; **the job IDs and their primary personas are unchanged**). Two new jobs (`probe-llm-obfuscation-gap`, `drive-engine-from-host-import`) are added.

**Rationale**: Refinements stay backward-compatible (no story breaks); additions are required because the goals doc adds surfaces (Mystery, host-import) that the original three jobs don't cover.

---

## Wave: DISCUSS / [REF] Out of Scope

Reaffirmed by this wave (handed to DESIGN; downstream features handle these):

- **LLM player implementations** — cells D, E, F ship in separate features. The engine exposes the host-import surface; the chart and the LLM agent that wire into it are elsewhere.
- **WUMP3 hazard variants** — additional hazard types beyond the Yob set (pit, bat, wumpus). The variant-config slot supports the counts; new hazard *kinds* are a separate feature.
- **Escalation rules L3 ("partial observability") and L4 ("non-dodec graph")** — these drop into the `escalation_rules` slot exposed by this feature. Surface the slot here; ship the rules elsewhere.
- **L2 ("wumpus moves when startled")** is **NOT** out of scope — it's part of Yob baseline (`FNC` distribution), so it's already in via the faithful-Yob slice.
- **GUI, web port, graphical map rendering** — Yob's CLI is the interface. A future visualizer reads the JSONL ledger; it does not embed the engine.
- **Benchmark runner** — the runner lives in the harness; the engine produces ledgers, the runner consumes them.
- **Solver, planner, agent code** — cells A–G live in the harness, not the engine.

---

## Wave: DISCUSS / [REF] Pre-requisites

- **Greenfield package** — `python/packages/wumpus/` does not yet exist. The walking skeleton creates it. No `pyproject.toml` to migrate.
- **BASIC reference present** — `wumpus/experiments/g_wild_baseline/wumpus.gwbasic.bas` exists and is byte-audited; it's the spec when this package disagrees with it. Test fixtures (captured BASIC transcripts) are a pre-requisite for the bug-for-bug fidelity AC; if they don't exist as pinned files yet, generating them is a Phase 2 slice precursor.
- **No DIVERGE wave** — every story carries `validation: synthesized-from-goals-doc`. The wave doesn't block on a missing DIVERGE; the validation flag is the trail to follow when interviews happen later.

---

## Wave: DISCUSS / [REF] WS Strategy

**Confirmed in Phase 2.5: Strategy A — straight-line walking skeleton.**

Slice R0 (see `[REF] Story Map`) is the walking skeleton: a programmatic-only, single-event-emitting, deterministic-from-seed `Game` that can be moved, observed, and terminated, on a *toy* 3-room cave with one hazard. It is intentionally *not* the goals-doc done-criterion #1 ("byte-identical BASIC transcript") — that's the target of Release 1 in aggregate, not a single slice. R0's purpose is to prove the architecture (Observation/Event split, deterministic Game(seed), in-memory ledger) before any Yob-fidelity work begins.

Strategies considered and rejected:

- **B (vertical-per-surface, three skeletons in parallel):** rejected. The three surfaces (CLI, programmatic API, host-import) share the same `Game` substrate; building three thin verticals first would force shared types (`Snapshot`, `Observation`, `Event`) to be locked before any single surface had shaped them. Conway-violates its own substrate.
- **C (Yob-fidelity-first single-thread):** rejected as a *strategy*; this is what Release 1 is. The R0 walking skeleton has to come first to validate the abstractions on cheap fixtures before Yob's full mechanics layer on top.
- **D (host-import-first):** rejected. Blocked-on-MPL-spike for the signature; building toward an unknown signature creates rework (per R2 risk).

The straight-line A strategy means: every release after R0 is sequential. Parallelism within a release is fine (R1 slices for move-hazards vs shoot-arrow can run side-by-side once R0 lands), but releases must serialize.

---

## Wave: DISCUSS / [REF] Driving Ports

Three inbound surfaces, one bounded context:

1. **CLI** — `python -m wumpus` (or `wumpus` console-script entry point), line-buffered stdio, `--seed`, `--ledger`, `--surface`, `--yob` (and individual variant flags).
2. **Programmatic Python API** — `from wumpus import Game` for cells A, B, C, E, F.
3. **MPL host-import** — snapshot-step-snapshot pure function. Signature pinned by the MPL spike (R2); constraints knowable now.

The ledger is observability, not a driving port. Files under `docs/product/journeys/` cover one journey per surface.
