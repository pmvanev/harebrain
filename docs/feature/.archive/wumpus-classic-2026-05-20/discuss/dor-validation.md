# Definition of Ready Validation: wumpus-classic

All 9 DoR items checked for each of the 7 user stories. DoR is a hard gate per `nw-product-owner` Critical Rule 3.

## Story: US-01 — Engine boots with seeded cave and emits structured events

| DoR Item | Status | Evidence |
|---|---|---|
| 1. Problem statement clear, domain language | PASS | Story has Problem section in researcher language ("oracle", "ground truth", "divergence-event measurement"); no technical jargon hidden as user need. |
| 2. User/persona identified with specific characteristics | PASS | Harness Harriet, defined in `docs/product/jobs.yaml#personas/harness-harriet` with surface, success_feel, emotional arc. |
| 3. 3+ domain examples with real data | PASS | 3 examples: happy path with seed=42, edge case with seed=None and OS entropy, edge case with cave-gen re-roll on crossover. All use concrete code and seed values. |
| 4. UAT scenarios in Given/When/Then (3-7) | PASS | 5 scenarios covering: seeded instantiation, unseeded instantiation, two-instance equality, crossover elimination, late sink subscription. |
| 5. AC derived from UAT | PASS | 5 ACs (AC-01.1 through AC-01.5), each traceable to a UAT scenario. |
| 6. Right-sized (1-3 days, 3-7 scenarios) | PASS | 2 days, 5 scenarios. |
| 7. Technical notes: constraints/dependencies | PASS | Lists C-2, C-4; notes US-02 dependency. |
| 8. Dependencies resolved or tracked | PASS | No upstream; downstream tracked. |
| 9. Outcome KPIs defined with measurable targets | PASS | Who/Does what/By how much/Measured by all populated; target = 100% replay determinism on seeded instantiation. |
| Elevator Pitch (Dimension 0 BLOCKING) | PASS | Before/After/Decision-enabled present. After cites real entry point (`Game(seed=42)`). Concrete output (`GameStarted(seed=42, ...)`). Decision is real (choose sinks, enumerate scenarios). |

**DoR Status: PASSED**

## Story: US-02 — CLI loop runs end-to-end with movement-only gameplay

| DoR Item | Status | Evidence |
|---|---|---|
| 1. Problem statement clear, domain language | PASS | Pat-language Problem section ("verify that the Python port's prompt/parse cycle feels like Yob"). |
| 2. User/persona identified with specific characteristics | PASS | Player Pat, defined in jobs.yaml with success_feel, emotional arc (curious/tension/catharsis). |
| 3. 3+ domain examples with real data | PASS | 3 examples: 5-move session, invalid room input, S-in-skeleton-mode. All show real prompts and real responses. |
| 4. UAT scenarios in Given/When/Then (3-7) | PASS | 6 scenarios. |
| 5. AC derived from UAT | PASS | 8 ACs traceable to scenarios. |
| 6. Right-sized (1-3 days, 3-7 scenarios) | PASS | 2 days, 6 scenarios. |
| 7. Technical notes: constraints/dependencies | PASS | Lists C-1, C-3, C-5, C-7; US-01 dependency. |
| 8. Dependencies resolved or tracked | PASS | US-01. |
| 9. Outcome KPIs defined with measurable targets | PASS | 100% skeleton sessions complete; 100% transcript runs byte-identical to non-transcript. |
| Elevator Pitch (Dimension 0 BLOCKING) | PASS | Before/After/Decision-enabled present. After cites `wumpus` CLI command. Concrete output (CLI text shown). Decision: verify cave geometry before trusting combat rules. |

**DoR Status: PASSED**

## Story: US-03 — Hazards, senses, walking-into-hazards

| DoR Item | Status | Evidence |
|---|---|---|
| 1. Problem statement clear, domain language | PASS | Pat-language ("Yob's brutality is the design"). |
| 2. User/persona identified | PASS | Player Pat. |
| 3. 3+ domain examples with real data | PASS | 3 examples: 3-adjacent-hazard room, bat-into-pit chain, wumpus-bump-startle-survives. Real room numbers, real text. |
| 4. UAT scenarios in Given/When/Then (3-7) | PASS | 7 scenarios (sense order, pit, bat-safe, bat-pit, wumpus-bump-safe, wumpus-bump-eats, no-sense). |
| 5. AC derived from UAT | PASS | 7 ACs. |
| 6. Right-sized | PASS | 3 days, 7 scenarios — at upper limit but within. |
| 7. Technical notes | PASS | C-1, C-2, C-6 listed. |
| 8. Dependencies | PASS | US-01, US-02. |
| 9. Outcome KPIs | PASS | 100% senses match adjacency, 100% hazard branches match Yob, byte-identical loss messages. |
| Elevator Pitch | PASS | After shows real Pat-visible behavior (senses, bat snatch, pit fall messages). Decision: play hazard-only games. |

**DoR Status: PASSED**

## Story: US-04 — Shooting end-to-end

| DoR Item | Status | Evidence |
|---|---|---|
| 1. Problem statement | PASS | "shooting rules are also the most quirky and most often miscoded" — domain reasoning. |
| 2. Persona | PASS | Player Pat. |
| 3. 3+ examples | PASS | 4 examples: 2-room shoot win, crooked-path rejection, random-deflection, out-of-arrows. |
| 4. UAT (3-7) | PASS | 7 scenarios. |
| 5. AC from UAT | PASS | 9 ACs covering arrow walk, crooked, hit/miss/self-shot, startle, out-of-arrows, message text. |
| 6. Right-sized | PASS | 3 days, 7 scenarios. **Note**: this is the largest story; splitting was considered but rejected — half-shooting is no shooting (cannot be demoed end-to-end). See story-map.md Priority Rationale point 3. |
| 7. Technical notes | PASS | C-1, C-2, C-6; depends on US-01, 02, 03. |
| 8. Dependencies | PASS | Explicitly tracked. |
| 9. Outcome KPIs | PASS | 100% arrow rules match Yob; win/lose swap preserved byte-for-byte. |
| Elevator Pitch | PASS | After cites `S` command and shows Yob-faithful CLI text. Decision: complete a full Yob game. |

**DoR Status: PASSED**

## Story: US-05 — Seeded replay produces byte-identical event streams

| DoR Item | Status | Evidence |
|---|---|---|
| 1. Problem statement | PASS | "interesting case is now folklore" — concrete researcher pain. |
| 2. Persona | PASS | Harness Harriet. |
| 3. 3+ examples | PASS | 3 code examples: replay-matches, different-seed-diverges, sink-attachment-irrelevant. |
| 4. UAT (3-7) | PASS | 5 scenarios. |
| 5. AC from UAT | PASS | 5 ACs (single RNG, deterministic call order, byte-identical over 20 seeds, divergence visible on wrong seed, sink-independent). |
| 6. Right-sized | PASS | 2 days, 5 scenarios. |
| 7. Technical notes | PASS | C-2, C-3, C-4. |
| 8. Dependencies | PASS | US-01, US-03, US-04 (full game required for determinism over full ruleset). |
| 9. Outcome KPIs | PASS | 20/20 seeded scenarios byte-identical. |
| Elevator Pitch | PASS | After cites `Game(seed=42)` programmatic entry point. Concrete output (event-list equality). Decision: attach debuggers, share seeds. |

**DoR Status: PASSED**

## Story: US-06 — Concurrent CLI + JSONL sink — observer-effect absent

| DoR Item | Status | Evidence |
|---|---|---|
| 1. Problem statement | PASS | Cites Decision 4's user-named use case verbatim. |
| 2. Persona | PASS | Harness Harriet. |
| 3. 3+ examples | PASS | 3 examples: tee'd session, with/without --transcript byte-diff, broken sink isolation. |
| 4. UAT (3-7) | PASS | 5 scenarios. |
| 5. AC from UAT | PASS | 6 ACs (transcript format, byte-identical stdout, multi-sink, sink isolation, observer absence, header format). |
| 6. Right-sized | PASS | 2 days, 5 scenarios. |
| 7. Technical notes | PASS | C-3, C-4. |
| 8. Dependencies | PASS | US-01, US-02, US-05. |
| 9. Outcome KPIs | PASS | 100% dual-mode byte-identical stdout. |
| Elevator Pitch | PASS | After cites `wumpus --transcript` flag. Concrete output (both CLI text and JSONL file). Decision: instrument human studies. |

**DoR Status: PASSED**

## Story: US-07 — Oracle parity — engine matches PC-BASIC byte-for-byte

| DoR Item | Status | Evidence |
|---|---|---|
| 1. Problem statement | PASS | "fidelity claim is a self-assessment" — engineering pain. |
| 2. Persona | PASS | Engineering team (acting for Pat and Harriet). |
| 3. 3+ examples | PASS | 3 fixture examples (shoot-and-win, bat-into-pit-chain, sense-order-regression-caught). |
| 4. UAT (3-7) | PASS | 3 story-level scenarios + 10 fixture-level scenarios. |
| 5. AC from UAT | PASS | 5 ACs (fixture set, byte-equality runner, layout-matching strategy, rule-coverage gate, Windows-only platform constraint). |
| 6. Right-sized | PASS | 3 days, 3 + 10 scenarios. (Fixtures are data, not separate UATs.) |
| 7. Technical notes | PASS | C-1; depends on US-01 through US-04; depends on existing `g_wild_baseline/`. |
| 8. Dependencies | PASS | Explicit. |
| 9. Outcome KPIs | PASS | 10/10 fixtures pass; 100% rule coverage. |
| Elevator Pitch | PASS | After describes CI behavior with concrete diff-on-failure output. Decision: cite oracle-parity evidence externally; catch regressions. |

**DoR Status: PASSED**

## Slice-level Elevator Pitch check (Dimension 0 BLOCKING #5)

Each slice contains at least one user-visible story (no slice is 100% infrastructure):

| Slice | Stories | User-visible? |
|---|---|---|
| 1 (Walking Skeleton) | US-01, US-02 | YES — US-02 ships a runnable `wumpus` CLI |
| 2 (Hazards) | US-03 | YES — Pat plays hazard games |
| 3 (Shooting) | US-04 | YES — Pat wins or loses by shooting |
| 4 (Determinism/Instrumentation) | US-05, US-06 | YES — US-06 ships `--transcript` flag visible to Pat |
| 5 (Fidelity Audit) | US-07 | YES via secondary persona — Engineering team cites it; Pat/Harriet rely on it |

**Slice-level check: PASSED.**

## Aggregate DoR Status

**ALL 7 STORIES: PASSED**

No story is blocked. No story carries unresolved issues. Handoff to nw-product-owner-reviewer is unblocked.

## JTBD Traceability Check

| Story | job_id | In jobs.yaml? |
|---|---|---|
| US-01 | instrument-wumpus-play | YES |
| US-02 | play-classic-wumpus | YES |
| US-03 | play-classic-wumpus | YES |
| US-04 | play-classic-wumpus | YES |
| US-05 | replay-wumpus-deterministically | YES |
| US-06 | instrument-wumpus-play | YES |
| US-07 | play-classic-wumpus | YES |

No infrastructure-only stories. Every job_id resolves to an entry in `docs/product/jobs.yaml`.

**JTBD traceability: PASSED.**
