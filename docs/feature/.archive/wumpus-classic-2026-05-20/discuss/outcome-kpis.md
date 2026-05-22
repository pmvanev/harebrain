# Outcome KPIs: wumpus-classic

## Feature: wumpus-classic

### Objective

A pip-installable Python package that plays Yob's 1973 Hunt the Wumpus with byte-recognizable fidelity and that doubles as the ground-truth oracle for the harebrain experiment matrix — shipped within one feature cycle.

### Outcome KPIs

| # | Who | Does What | By How Much | Baseline | Measured By | Type |
|---|---|---|---|---|---|---|
| 1 | A returning Wumpus player (Pat) | Recognizes the 1973 game on first session — including Yob's win/lose message swap and the bat-teleport disorientation pattern | 100% of byte-string assertions for prompts and outcome messages match the audited Yob source | None (greenfield) | Unit test: `MESSAGES` and `PROMPTS` exactly equal Yob source lines; oracle-parity test (KPI 4) corroborates | Leading |
| 2 | Researcher (Harriet) | Replays a recorded session by seed and receives byte-identical event streams | 100% of N=20 seeded runs at length 50 turns produce identical event sequences on replay | None | Replay determinism test: instantiate `Game(seed=s)`, run 50 turns of recorded commands, compare event lists for equality. Repeat for 20 seeds. | Leading |
| 3 | Researcher (Harriet) | Runs the engine programmatically at experiment-loop speed | At least 1000 programmatic turns complete in under 10 seconds of wall-clock time on a developer laptop (no CLI rendering, no JSONL sink) | None | Benchmark test: 1000 turns of a fixed seeded scenario, timed with `time.perf_counter` | Leading (secondary) |
| 4 | Researcher (Harriet) | Validates engine output against the BASIC reference | All 10 hand-curated scenarios produce engine event streams equivalent to `pcbasic wumpus.gwbasic.bas` output via `wexpect`-driven I/O capture (modulo seed mapping — see note) | None | Oracle-parity acceptance test: for each scenario, feed identical input sequence to both engine and PC-BASIC; compare engine's CLI-rendered output to PC-BASIC's captured stdout, byte-for-byte | Leading |
| 5 | Researcher (Harriet) | Captures the complete event stream while a human plays interactively (Decision 4 contract) | 100% of CLI sessions produce byte-identical stdout whether a JsonlSink is attached or not; 100% of attached JsonlSinks capture the complete event sequence for the session | None | Concurrent-monitoring test: run the same seeded CLI session twice (with and without JsonlSink), compare stdouts; assert JsonlSink output covers every event emitted | Leading |
| 6 | Engineering team | Achieves rule-fidelity coverage of the audited Yob source | 100% of rules enumerated in the Yob audit (`shared-artifacts-registry.md` constants + journey YAML invariants) have at least one acceptance scenario referencing them | None | Coverage gate test: parse rule list from audit doc, parse scenario titles from acceptance test files, fail build if any rule lacks coverage | Leading |
| 7 | Researcher (Harriet) | Identifies which divergence-event kind an LLM player exhibits (downstream payoff, dependency on this engine) | Engine emits event types covering all five divergence kinds catalogued in `wumpus_idea.md`: resurrected entity, inventory drift, position confusion, stale belief, phantom geography | None | Schema audit: cross-reference event types against catalogue; downstream tests in cells E/F validate kind detection | Leading (downstream-enabling) |

**Note on KPI 4 (oracle parity, "modulo seed mapping"):** The Python engine uses Python's `random.Random` PRNG; PC-BASIC uses GW-BASIC's RNG. There is no shared seed space — `Game(seed=42)` and `RANDOMIZE 42` produce different cave layouts. The oracle-parity test fixes this by *recording* a PC-BASIC scenario's layout (room positions of wumpus, pits, bats, player) and seeding the engine to a known seed whose generated layout matches. The comparison is then on event-by-event semantic equivalence, not on identical RNG output. Failing this test means a rule (sense order, hazard check order, message text) differs from Yob.

### Metric Hierarchy

- **North Star:** KPI 6 — rule-fidelity coverage. The whole point of this package is to be a faithful Yob implementation; if any rule is uncovered, the fidelity claim is undefended.
- **Leading indicators:**
  - KPI 1 — byte-string fidelity (the most visible Yob signal: the message swap)
  - KPI 2 — replay determinism (Harriet's gate to using this as an oracle)
  - KPI 5 — observer-effect absence (Decision 4 contract)
- **Guardrail metrics (must not degrade):**
  - KPI 3 — throughput stays at or above 1000 turns / 10s (an order of magnitude headroom for experiment loops)
  - KPI 4 — oracle parity stays at 10/10 scenarios passing

### Measurement Plan

| KPI | Data Source | Collection Method | Frequency | Owner |
|---|---|---|---|---|
| 1 | Source code: `MESSAGES`, `PROMPTS` constants | Unit test asserts byte-equality against `g_wild_baseline/wumpus.gwbasic.bas` lines | Every CI run | DEVELOP wave |
| 2 | Test suite: `tests/test_replay_determinism.py` | Pytest, 20 seeds x 50 turns, assert event-list equality | Every CI run | DEVELOP wave |
| 3 | Benchmark: `tests/bench_throughput.py` | `pytest-benchmark` or stdlib `time.perf_counter`, 1000-turn scenario | Every CI run | DEVELOP wave |
| 4 | Test suite: `tests/oracle_parity/` | 10 fixture scenarios; each runs `wexpect` against `pcbasic` and captures stdout; compares to engine CLI output | Every CI run on Windows runner (wexpect is Windows-only) | DEVELOP wave |
| 5 | Test suite: `tests/test_concurrent_sink.py` | Two engine runs with same seed, one with sink attached; diff stdouts | Every CI run | DEVELOP wave |
| 6 | Coverage gate: `tests/test_rule_coverage.py` | Parse rule-citation tags from acceptance test scenario titles (`@yob-3370`, etc.); parse rule list from `shared-artifacts-registry.md`; fail if any rule lacks ≥1 scenario | Every CI run | DEVELOP wave |
| 7 | Schema audit: `tests/test_divergence_kinds.py` | Static check: every divergence kind in `wumpus_idea.md` table maps to an event field | Every CI run | DEVELOP wave |

### Hypothesis

We believe that **a faithful, seedable, event-emitting Hunt the Wumpus engine** for **the harebrain experiment program (Harriet) and 1973-game enthusiasts (Pat)** will achieve **a byte-recognizable, oracle-grade implementation of Yob's game**.

We will know this is true when:
- KPI 1 = 100% byte-equality on all messages and prompts
- KPI 2 = 20/20 seeded runs replay byte-identical
- KPI 4 = 10/10 oracle-parity scenarios pass
- KPI 6 = 100% rule coverage

## Handoff to DEVOPS (platform-architect)

The platform-architect (DEVOPS wave) needs:

1. **Data collection requirements:**
   - Event stream is the primary instrumentation; no additional logging needed for KPIs 1-6.
   - For downstream divergence-event analysis (KPI 7), expose the engine's snapshot API alongside the event stream so harness consumers can diff at any turn.

2. **Dashboard/monitoring needs:**
   - None for this feature (it's a library + CLI, not a service).
   - Downstream (experiment harness): plot cumulative divergence events per turn (line chart), scratchpad accuracy per turn (line chart), per-kind divergence histogram (stacked bar).

3. **Alerting thresholds:**
   - CI gate: any KPI 1/2/4/5/6 test failure fails the build.
   - Soft alert: KPI 3 regression beyond 2x baseline triggers a warning (not a build fail — local-laptop variance is too noisy).

4. **Baseline measurement:**
   - No baselines to collect pre-release (greenfield package; no existing user behavior to baseline against).
   - Baselines for downstream experiment cells (E, F win-rate, divergence rate) will be collected in subsequent features once the engine ships.
