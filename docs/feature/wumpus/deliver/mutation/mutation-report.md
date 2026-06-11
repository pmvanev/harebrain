# Wumpus — Mutation testing baseline (2026-05-28)

First-ever real mutation run for the wumpus feature. The CI `mutation.yml` gate
that had previously been the documented quality gate had been **silently
no-op'ing on every push** (uv couldn't find `mutmut` from the workspace root +
the workflow's `|| true` swallowed the spawn failure + `TOTAL=0` was treated
as PASS), so this report is the first time the project actually measured the
test suite's kill rate. The CI workflow has since been retired (commit
`c837315`); mutation testing is now a local developer practice (see
`CLAUDE.md` § Mutation Testing Strategy).

## Run

- **Tool:** [cosmic-ray](https://github.com/sixty-north/cosmic-ray) 8.4.6 (Windows-native; replaces mutmut, which has no native Windows support in 3.x and whose config schema had been rewritten incompatibly with this project's previous `[tool.mutmut]`).
- **Scope (focused first run):** `python/packages/wumpus/src/wumpus/surfaces/mystery.py` only — the smallest new-this-session file (≈ 120 lines), chosen to validate the pipeline end-to-end before scaling up.
- **Test command:** `uv run pytest tests -x --ignore=tests/subprocess -q` (excludes the wexpect smoke that hangs on Windows; matches the project's "NNN non-subprocess tests green" convention).
- **Wall-clock:** ~4 min for 71 mutants (`baseline` 6s + `exec` ~4 min).
- **Config + session DB:** `cosmic-ray.toml` and `session.sqlite` are siblings of this report; `session.sqlite` is gitignored.

## Results

| | count |
|---|---:|
| Total mutants | 71 |
| Killed | 43 |
| **Survived** | **22** |
| Incompetent (cosmic-ray rejected — equivalent / un-compilable) | 6 |
| **Raw kill rate** (`killed / (killed + survived)`) | **66.2 %** |

Raw 66.2 % is below the 80 % target. But the survivors cluster into two distinct buckets, and one of them is genuinely *equivalent* mutants the cosmic-ray default operator set generates against type annotations:

### Survivor analysis

**(A) ~11 survivors are equivalent mutants on type annotations** — the `BitOr_*` replacements (`|` → `+`, `-`, `*`, `/`, `//`, `%`, `**`, `>>`, `<<`, `&`, `^`) all target the `int | None` *return-type annotation* at line 198:

```python
def room_id(self, label: str) -> int | None:
```

Python doesn't enforce type annotations at runtime, so these mutations have no observable behavior — no test could ever kill them. This is a known cosmic-ray default-operator quirk, not a test-suite gap.

**Action:** add these to `MUTATION_EXEMPTIONS.md`, or (better) tune the cosmic-ray operator set to skip annotation mutations on the next run.

**(B) ~11 survivors are a genuine, actionable test gap** in `MysterySurface.terminal_lines` (lines 310–311):

```python
tag = _WIN_TAG if message_kind == "win" else _LOSE_TAG
if reason:
    return (reason, tag)
return (tag,)
```

The 8 comparison mutants on `message_kind == "win"` and the related `AddNot` / `OrWithAnd` survivors all indicate the **Mystery surface's win/lose terminal branch is never exercised by the test suite**. The paired obfuscation property runs short action sequences that don't reach a `GameEnded` event under the Mystery surface, so this whole code path goes untested.

**Action:** add a Mystery-surface acceptance scenario (or extend the paired property) that drives the engine to *both* a win and a loss under `MysterySurface()` and asserts the rendered terminal lines.

### Effective kill rate

Discounting the type-annotation equivalents:

- 43 killed / (43 killed + ~11 real survivors) = **~79.6 %** — one or two killing tests away from the 80 % threshold.

## Recommended follow-ups (own slice or fold into next surface work)

1. **Add Mystery terminal-rendering scenarios** to `R4_surface.feature` (or a sibling property) — drive a forced-win + forced-loss under `MysterySurface()`, assert `terminal_lines` content. Will kill the ~11 `terminal_lines` survivors and push the effective rate well above 80 %.
2. **Tune cosmic-ray operators** — `cosmic-ray operators` lists the available mutators; disable the `BitOr_*` replacements (or any operator that targets annotation syntax) in `cosmic-ray.toml`. Re-run; expect the equivalent-mutant count to drop to ~0.
3. **Expand scope** — re-run with `module-path` widened to the engine + the other surfaces + the new audit (`engine/game.py`, `surfaces/yob.py`, `surfaces/french.py`, `audits/surface_leak.py`). The other modules likely have their own gaps to surface.

## Re-running this report

From `python/packages/wumpus/`:

```bash
CONF=../../../docs/feature/wumpus/deliver/mutation/cosmic-ray.toml
SESS=../../../docs/feature/wumpus/deliver/mutation/session.sqlite
rm -f "$SESS"
uv tool run --from cosmic-ray cosmic-ray init "$CONF" "$SESS"
uv tool run --from cosmic-ray cosmic-ray baseline "$CONF"          # sanity check
uv tool run --from cosmic-ray cosmic-ray --verbosity INFO exec "$CONF" "$SESS"
uv tool run --from cosmic-ray cosmic-ray dump "$SESS"              # raw results
```

Source files are not modified in place — cosmic-ray applies + reverts each mutation around its test run, so an interrupted run leaves the working tree clean. (Verified post-run: `git status` was clean.)

---

# R5-S01 host_import.py (2026-06-10)

Feature-scoped mutation run on the just-shipped **R5-S01 host-import seam**
(`src/wumpus/host_import.py`, 94 lines — `step_from_snapshot`, `StepResult`,
`iter_steps`). This is the local QUALITY_GATE for the slice; no production logic
was changed (the gate either adds a killing test or documents an equivalent-mutant
exemption).

## Run

- **Tool:** cosmic-ray 8.4.6 (Windows-native).
- **Scope:** `src/wumpus/host_import.py` only.
- **Config / session:** `cosmic-ray-host-import.toml` + `session-host-import.sqlite` (gitignored), siblings of this report.
- **Test command (scoped):** `uv run pytest tests/acceptance/step_definitions/test_R5_host_import.py -x -q --ignore=tests/subprocess` — the R5-S01 acceptance scenarios are the only tests that exercise this file; `--ignore=tests/subprocess` avoids the wexpect hang (CLAUDE.md session gotcha).
- **Baseline:** green before mutating (`cosmic-ray baseline` clean; scoped pytest = 3 passed in ~0.5s after the new scenario was added).

### Windows decode gotcha (tooling, not a finding)

cosmic-ray 8.4.6 on Windows mislabels a **caught** mutant as `INCOMPETENT` when the
failing pytest output contains a non-UTF-8 byte: `cosmic_ray/testing.py:51` does
`err.output.decode("utf-8")` on cp1252-captured output (byte `0x97`, the `—` em-dash
in assertion messages) and crashes before recording `KILLED`. **Fix:** run
init+exec with `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` in the environment so the test
subprocess emits UTF-8. After that, all caught mutants report cleanly as `KILLED`.

## Results

| | count |
|---|---:|
| Total mutants | 3 |
| Killed | 2 |
| **Survived** | **1** |
| Equivalent / exempted (excluded from denominator) | 1 |
| **Final kill rate** (`killed / (total − exempted)` = 2 / (3 − 1)) | **100 %** |

**Gate verdict: PASS** (≥ 80 %).

`host_import.py` is almost pure dataflow (resurrect → subscribe → step → serialize),
so cosmic-ray's default operator set finds only 3 mutable points — hence the small
mutant population.

## Per-survivor / per-mutant disposition

| Location | Operator | Outcome | Disposition |
|----------|----------|---------|-------------|
| `host_import.py:32` (`@dataclass`) | `core/RemoveDecorator` | **KILLED** | Removing `@dataclass` breaks `StepResult` construction; existing scenarios 1-2 fail. (Reported KILLED only after the UTF-8 env fix above.) |
| `host_import.py:91` (`iter_steps` loop) | `core/ZeroIterationForLoop` (`for action in []:`) | **KILLED by new test** | **Real gap** — scenarios 1-2 never called `iter_steps`. Added acceptance **Scenario 3** (`iter_steps drives a sequence of turns threading each snapshot forward`) in `R5_host_import.feature` + step defs `_r5s03_run_iter_steps` / `_r5s03_one_per_action` / `_r5s03_equals_manual_chain`. Asserts N actions → N `StepResult`s, room sequence 5→1→2, and threaded output == manual `step_from_snapshot` chaining. A no-op loop yields zero results → both assertions fail → mutant dies. |
| `host_import.py:32` (`frozen=True`) | `core/ReplaceTrueWithFalse` (`frozen=False`) | **SURVIVED → exempted** | **Equivalent mutant.** `frozen=` only governs post-construction attribute reassignment; `StepResult` is constructed once and never mutated, so the flag has no observable effect at the port boundary. Killing it would assert a Python dataclass language guarantee (`FrozenInstanceError`), a banned anti-pattern (`nw-test-optimization` §1.2 / §2.3). Documented in `python/packages/wumpus/MUTATION_EXEMPTIONS.md`; excluded from the denominator. |

## Reproduce

From `python/packages/wumpus/`:

```bash
CONF=../../../docs/feature/wumpus/deliver/mutation/cosmic-ray-host-import.toml
SESS=../../../docs/feature/wumpus/deliver/mutation/session-host-import.sqlite
rm -f "$SESS"
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 uv tool run --from cosmic-ray cosmic-ray init "$CONF" "$SESS"
uv tool run --from cosmic-ray cosmic-ray baseline "$CONF"
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 uv tool run --from cosmic-ray cosmic-ray exec "$CONF" "$SESS"
uv tool run --from cosmic-ray cr-report "$SESS"
```

---

# Core engine — partial spot-check (2026-06-10), campaign DEFERRED

Broadening the mutation posture from the per-file pilots to the **core engine
package** (`src/wumpus/engine/`). The full campaign was **deliberately stopped
after a 75-mutant sample** (user decision, 2026-06-10) rather than run to
completion — this section documents the indicative result and the reason, and
hands the full run off as a follow-up.

## Run

- **Tool:** cosmic-ray 8.4.6, `PYTHONUTF8=1` (the Windows decode fix above).
- **Scope (intended):** `src/wumpus/engine/` — **1,117 mutants** across all engine modules (`__init__` excluded). Config: `cosmic-ray-engine.toml` (sibling of this report).
- **Test command:** `uv run pytest tests -x --ignore=tests/subprocess -q` (full local kill signal; ~12 s green).
- **Completed:** **75 / 1,117 jobs (6.7 %)** before the run stopped — see "Why it stopped".

## Why it stopped (infrastructure finding)

Background commands in this environment are terminated at **~16 min wall-clock**, which is **~75 mutants** at ~12 s/mutant serial (cosmic-ray's `local` distributor is single-process). The `exec` was cut mid-job with a clean log (no error/traceback); cosmic-ray sessions are **resumable** (re-running `exec` on `session-engine.sqlite` continues the pending jobs), so no work is lost. A full serial run is ~3.7 h ≈ ~14 of these cycles. Given that cost, the campaign was stopped at the sample by decision.

## Result on the 75-mutant sample

| | count |
|---|---:|
| Completed (of 1,117) | 75 |
| Killed | 60 |
| **Survived** | **15** |
| **Kill rate on the sample** (`killed / completed`) | **80.0 %** |

The sampled mutants skew toward the modules cosmic-ray enumerated first (`game.py` 42, `hash.py` 10, `arrow_walk.py` 8, plus a few in `startle`/`sense`/`transitions`/`hazard_resolve`/`_r0_toy_cave`), so this is **indicative, not a per-module verdict.** 80 % on a partial, untriaged sample is encouraging but not a gate result.

## The 15 survivors (untriaged — candidates for the full run)

| Module | Operator | Occ. |
|---|---|---:|
| `game.py` | `ReplaceBinaryOperator_Mul_Div` | 4 |
| `game.py` | `ReplaceBinaryOperator_BitOr_Mul` | 7 |
| `game.py` | `ReplaceBinaryOperator_BitOr_FloorDiv` | 0 |
| `game.py` | `ReplaceBinaryOperator_BitOr_Pow` | 0, 2 |
| `game.py` | `ReplaceBinaryOperator_BitOr_BitAnd` | 5 |
| `game.py` | `ReplaceBinaryOperator_BitOr_BitXor` | 0, 9 |
| `game.py` | `ReplaceComparisonOperator_NotEq_Lt` | 2 |
| `game.py` | `AddNot` | 23 |
| `game.py` | `ReplaceAndWithOr` | 0 |
| `hash.py` | `ReplaceBinaryOperator_BitOr_Mul` | 0 |
| `hash.py` | `ReplaceBinaryOperator_BitOr_FloorDiv` | 1 |
| `sense.py` | `ReplaceComparisonOperator_Eq_Is` | 0 |
| `hazard_resolve.py` | `ReplaceBreakWithContinue` | 2 |

Cautious read (NOT verified — triage is part of the deferred run):

- The cluster of **`BitOr_*` replacements** echoes the mystery.py pilot, where every `BitOr_*` survivor was an **equivalent mutant on an `int | None` type annotation** (no runtime effect). Several of these engine instances are likely the same annotation quirk; `hash.py`'s, however, *may* be genuine bit-mixing in the hashing path — these need individual triage (annotation ⇒ exempt; real bitwise/set op ⇒ likely a real gap).
- The **boolean/branch mutants** (`AddNot`, `ReplaceAndWithOr`, `ReplaceComparisonOperator_*`, `ReplaceBreakWithContinue`) are the higher-value candidates for genuine test gaps and should be triaged first when the full run lands.

## ⚠ Latent engine bug surfaced by the campaign (snapshot loses VariantConfig on restart)

Running the suite ~75× under mutation made Hypothesis explore a degenerate-variant
example the prior green runs never hit, and it **saved the counterexample** to its
(gitignored) `.hypothesis/` DB. It **reproduces on clean `HEAD`** —
`tests/property/test_variant_sweep.py::test_variant_snapshot_round_trip_holds`
now fails for `VariantConfig(room_count=20, pit_count=0, bat_count=0,
arrow_count=1, arrow_max_range=1, wumpus_move_prob=0.0)`, `seed=0`,
`actions=('Y','S','1','1','Y')`, `k=0`.

**Root cause (pinpointed).** The two event sequences match in *structure* (16 events,
identical types); the first *field* divergence is at the `GameStarted` emitted by the
`Y` / `SAME SET-UP` **restart**. Its `variant_config` is the custom variant in the
single-process baseline but reverts to **Yob defaults** (`pit_count=2, bat_count=2,
arrow_count=5`) in the snapshot-restored game. So **`Game.from_snapshot` does not
preserve the `VariantConfig` used to regenerate the cave on a SAME-SETUP restart** —
a restored non-Yob game silently reverts to Yob defaults when restarted.

**Impact: real, not a test-strictness artifact.** The cell-D host-import path (R5-S01)
drives the engine *via snapshots*; a snapshot-restored Mystery/variant game that hits
a restart would silently switch to Yob defaults, corrupting an obfuscation-gap (J2)
run. This is exactly the latent defect property + mutation testing exist to find.

**Disposition.** Out of scope for this "document the sample" pass; recommended path is
a dedicated bug-fix (RCA → regression test → fix via TDD; `/nw-bugfix`). The failing
Hypothesis example is **retained** in `.hypothesis/` (NOT cleared) because it marks a
real defect — clearing it would hide the bug. The mutation report and this finding are
independent of the eventual fix.

## Deferred-campaign handoff

To complete the engine campaign later (own slice or a maintenance pass):

1. **Reorder the suite fast-tests-first** in `cosmic-ray-engine.toml`'s `test-command` — e.g. `uv run pytest tests/acceptance tests/regression tests/property -x --ignore=tests/subprocess -q`. With `-x`, the ~80 % of mutants that die do so against the fast acceptance tests in ~3 s; only survivors pay the full property-sweep cost. Same kill signal, ~2-3× fewer cycles (~6 instead of ~14).
2. **Or run per-module** (`module-path` per file) so each module fits inside one ~16-min background cycle and yields its own kill-rate row.
3. **Or run on a host without the ~16-min background cap** (a longer-lived shell / CI runner), where the full serial run completes in one pass.
4. Then **triage survivors** (annotation-equivalents → `MUTATION_EXEMPTIONS.md`; real gaps → killing tests), and tune the cosmic-ray operator set to drop annotation-targeting `BitOr_*` mutations (recommended in the 2026-05-28 report, still open).

`cosmic-ray-engine.toml` and the partial `session-engine.sqlite` (gitignored) are retained as siblings of this report so the run can be resumed rather than restarted.
