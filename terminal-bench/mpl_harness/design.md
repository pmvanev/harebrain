# Harness design proposal — the MPL cage for TB-2

*A concrete proposal for an MPL-chart harness aimed at the top of the [Terminal-Bench 2.0 leaderboard](https://www.tbench.ai/leaderboard/terminal-bench/2.0). Priorities, in order: **accuracy → token use → time.** Every choice below is tied to a verified finding in the [research notes](README.md) (§ refs point there). This is a **design**, not yet runnable code — the MPL syntax in the sketch must be validated against the live `mplv2` package before it executes (see [Risks](#risks--what-to-validate-first)).*

> **The bet, in one line.** The leaders win by *engineering the failure classes* (Execution / Coherence / Verification), not by prompt-tuning. So the cage makes the two highest-accuracy guarantees **structural** — *premature "done" is unreachable* and *retry fires only on a sound signal* — pays for them in tokens/time deliberately (accuracy is priority #1), and claws the cost back everywhere else (blackboard, truncation, milestone memory, a hard anti-spin budget).

---

## 1. Design principles, in priority order

**Accuracy first (we will spend tokens and time to get it):**

- **A sound verification gate, made structural.** The finalize edge is reachable *only* through a passing deterministic check — so "the agent self-certified and the grader disagreed" (the Verification failure class, the bug that bit our v1) is unreachable *by geometry*, not discouraged by a prompt (notes §1, §3 verify-before-done; soundness rule §2).
- **Retry only on a sound failure signal, bounded.** Intrinsic self-retry *decreases* accuracy (GSM8K 95.5→89.0); retry grounded in an external signal *raises* it (Reflexion→91%). And LLMs are bad at *finding* errors (GPT-4 52.9%) but good at *fixing given the location* — so the cage retries only when `check()` fails and hands the **error location** to the fix step (notes §3 bounded-retry).
- **Plan before acting.** Drafting ordered sub-goals fixes missing-step / derailment (Plan-and-Solve; notes §3 plan→execute).
- **Tool grounding pre-flight.** A `command -v`-style probe before invoke attacks the **24.1%** command-not-found bucket — the single largest Execution failure — at ~zero token cost (notes §1, §3 tool-grounding).

**Token use second (claw it back without touching accuracy):**

- **Blackboard, not transcript.** The rich working state (plan, last error, files touched, milestone memory) lives **host-side**; the cage re-reads a compact digest each loop instead of re-sending the screen (notes §3 blackboard; the policy/mechanism split, §4 two-clock).
- **Head/tail output truncation** (first+last KB of long output — the two high-signal regions) and **milestone-curated memory** (curation helped +; naive last-K *hurt*) (notes §2, §3).

**Time third (never traded against accuracy or tokens):**

- **A hard anti-spin budget.** The expensive failure we actually measured was *time*: the v1/baseline cages spun **7–10 minutes** then timed out on `csv-to-parquet`. A `max_steps` cap + **stop-on-repeated-failure** + a top-priority `Abort` edge kill doom-spirals — which simultaneously saves time, tokens, *and* avoids the wasted-budget accuracy hit.
- **Parallel read-only scouting is deferred.** It helps time but costs tokens and leaks at the hand-off seam (parent/child recall 0.32 vs 1.00); since tokens outrank time, it's an *optional later region*, not in the core loop (notes §3 parallel; §5).

## 2. Architecture — the control loop

The cage is the **control plane** (a legible MPL chart); all data and side effects live in the **host** (Python), reached only through typed host-imports. This is the two-clock split: author the chart slowly under review; run it fast and many times.

```
            ┌───────────────────── @priority(100) Abort ◄── budget / loop / verify-exhausted
            │                         (wins every tick — the HALT-reachability lesson)
  ENTER → Boot → Plan ──► Observe ──► Decide ──► Ground ──┬─(empty cmd)──────────► Verify ─► Checked ─(pass)─► Done ✓
                            ▲           (LLM leaf)         ├─(cmd, tool ok)─► Act ──┘                │
                            │                              └─(cmd, tool missing)─► Decide            ├─(fail, <N)─► Decide  (retry on SOUND signal,
                            └──────────────── Act ─────────────────────────────────┘                │              error location handed back)
                                                                                                     └─(fail, ≥N)─► Abort
```

- **Boot** — snapshot the terminal; hand the instruction to the host blackboard.
- **Plan** — `plan(instruction)` once; host stores ordered sub-goals (Coherence).
- **Observe → Decide** — perceive (truncated screen) then the **single LLM leaf**; the prompt is assembled host-side from compact slots, not the transcript (tokens).
- **Ground** — tool-grounding pre-flight + done-detection: empty command routes to **Verify** (you don't get to skip the gate); a missing tool routes back to **Decide** to repair instead of running a doomed command (Execution).
- **Act** — the **one** mutating shell; returns a truncated screen; loops.
- **Verify → Checked** — `check()` is a **sound** deterministic check (re-run the task's *own visible* checks / assert observable end-state), called **once** and branched on next tick (avoids the double-call hazard). Pass → **Done**; fail → bounded retry → **Decide**; exhausted → **Abort**.
- **Done** — terminal; reachable **only** through a passing `check()`.
- **Abort** — terminal; budget exhausted, loop detected, or verification exhausted — never a silent give-up.

## 3. The chart (design sketch — validate syntax before running)

```mpl
// Scalar-only host seam (notes §3 gap-a): rich state is host-side; MPL routes on
// strings/bools. The host builds every prompt from its blackboard (plan + milestone
// memory + truncated screen); the cage only sequences and gates.
host import {
    observe() -> string,                  // head/tail-truncated screen
    plan(instruction:string) -> bool,     // host drafts + stores an ordered plan
    decide(screen:string) -> string,      // LLM leaf: next shell command, or "" when it believes the goal is met
    tool_ok(command:string) -> bool,      // pure pre-flight: executable present / command well-formed?
    act(command:string) -> string,        // the single mutating shell; returns truncated screen
    check() -> bool,                       // SOUND verify: re-run the task's visible checks / assert end-state
    note(kind:string, value:string) -> bool,  // curated milestone-memory write (errors, locations)
} from agent;

default machine Agent {
    vars {
        instruction:string := "";
        screen:string := "";
        cmd:string := "";
        verified:bool := false;
        steps:int := 0;   max_steps:int := 40;
        fails:int := 0;   max_fails:int := 3;
        finished:bool := false;
    }

    state Boot; state Plan; state Observe; state Decide; state Ground;
    state Act;  state Verify; state Checked; state Done; state Abort;
    ENTER => Boot;

    // HALT reachability: budget guard outranks every working transition this tick (notes §5).
    @priority(100) Boot|Plan|Observe|Decide|Ground|Act|Verify|Checked
        when steps > max_steps => Abort then { note("abort","budget"); finished := true; };

    Boot    => Plan    then { screen := observe(); };
    Plan    => Observe then { plan(instruction); };          // plan once, into host memory
    Observe => Decide  then { screen := observe(); };        // compact re-perceive
    Decide  => Ground  then { cmd := decide(screen); steps += 1; };   // the one LLM leaf

    // Tool grounding + done-detection. `cmd == ""` is the model's "I'm done" — it still must pass the gate.
    Ground when cmd == ""                       => Verify;
    Ground when cmd != "" && tool_ok(cmd)        => Act    then { screen := act(cmd); };
    Ground when cmd != "" && !tool_ok(cmd)       => Decide then { note("error","missing tool: " + cmd); };

    Act => Observe;

    // Sound gate. check() called ONCE; branch next tick on the committed `verified` (no double test run).
    Verify  => Checked then { verified := check(); };
    Checked when verified                        => Done   then { finished := true; };
    Checked when !verified && fails <  max_fails => Decide then { fails += 1; note("error","verify failed; retry with location"); };
    Checked when !verified && fails >= max_fails => Abort  then { note("abort","verify exhausted"); finished := true; };

    // Done is terminal and ONLY reachable through a passing check() — premature "done" is unreachable.
}
```

The host (`mpl_agent_v2.py`, a `BaseAgent`) registers the seven imports over the live `session` + an LLM built from `--model`, pins the decide-leaf sampling, holds the blackboard, and ticks until `Agent/finished`. It is the v1 host grown a plan/verify/grounding/memory surface — same contract, more leaves.

## 4. How the priority order resolves each trade-off

| Lever | Accuracy | Tokens | Time | Decision (priority: acc → tok → time) |
|---|:--:|:--:|:--:|---|
| Sound verify gate | **++** | + (a real check run) | + | **Keep** — accuracy is #1; the gate is the core guarantee |
| Bounded sound-signal retry | **++** | + | + | **Keep**, capped at `max_fails` so token/time burn is bounded |
| Tool-grounding pre-flight | **+** | ~0 | **−** | **Keep** — a free accuracy win that also saves time |
| Plan → execute | **+** | + (one round) | + | **Keep** — coherence on long-horizon tasks |
| Host-side blackboard (vs transcript) | ~ | **−−** | − | **Keep** — big token win, accuracy-neutral |
| Head/tail truncation + milestone memory | + | **−−** | − | **Keep** — curation *helped* accuracy; last-K hurt |
| Anti-spin budget + stop-on-fail | + | **−−** | **−−** | **Keep** — fixes the measured 7–10 min timeout-spins |
| Parallel read-only scouts | + | **++** | **−−** | **Defer** — tokens outrank time, and the seam leaks |

The through-line: **we spend** on verification, retry, planning, and grounding (priority #1), and **we save** with the blackboard, truncation, memory curation, and the anti-spin budget — so the cage buys accuracy with tokens it recovers elsewhere, and the budget guard keeps time bounded as a side effect.

## 5. Determinism & cost

- **Determinism.** `SIM/seed` pins MPL's tie-breaks and arbitration (notes §3 action-selection); the decide leaf pins temperature/seed where the provider allows. The residual nondeterminism is the model call itself — so the *cage* replays deterministically and we log the decide outputs to make a full trace replayable (notes §1 auditability; §3 gap-b: `TICK/seed` is not injected — confirm the replay guarantee before claiming it).
- **Cost ceiling.** `max_steps` + a host-side token/$ budget both feed the `@priority(100)` Abort. Milestone-curated memory keeps each decide prompt small, which is the dominant token cost over a 40-step task.

## 6. Self-improvement — a seeded stochastic transition policy

> ⚠ **SPIKE CORRECTION (2026-06-15 — see [`spike-findings.md`](spike-findings.md)).** The probe **refuted** the mechanism this section originally assumed: `choose(1){@weight}` with constant weights and only `SIM/seed` is **deterministic, weight-insensitive, and seed-independent** (1:3 *and* 1:99 both gave an exact 50/50 split; seed 7 ≡ seed 42). MPL has **no chart-level seeded RNG** — `arena.mpl`'s randomness is a **host import** (`randint`). **So the entropy source below moves from `@weight` to a host-seeded RNG** (`rand01()->float`, backed by `random.Random(trial_seed)` in `mpl_agent_v2.py`), feeding a guard like `Decide when rand01() < p_scout => Scout` or `@priority(host_score(...))`. The *strategy* in (a) and (b) is unchanged — pass@k via per-trial seed, sound-signal-only learning, host-persisted probabilities — only the draw's plumbing changes, and the harness (not the chart) owns the seed. This is *more* aligned with harebrain's determinism-via-host model, not less.

MPL's choice points are a **stochastic policy**: the transition probabilities are `P(Tᵢ) = wᵢ / Σw`, and the weights are *expressions over `vars`*, so the distribution can both be *sampled from* and *updated at runtime*. (Per the correction above, the *sampling* is done by a host-seeded RNG import, not by `@weight` itself.) Two distinct uses fall out — and they sit very differently against our priorities and the determinism rule in §5.

**(a) A *fixed* seeded stochastic policy — a near-term pass@k win, no learning.** TB-2 scores **≥5 trials per task** (pass@k). A deterministic argmax cage takes 5 near-identical shots at the same failure; a seeded stochastic policy (a fresh `SIM/seed` per trial) takes 5 that **explore different paths** — and diverse attempts beat identical ones at pass@k. Because each draw is **seeded**, every trial still replays exactly from its logged seed (§5). So making the *leaf* selection stochastic buys cell-level accuracy with **full reproducibility and zero online learning** — the cheapest accuracy lever the policy framing unlocks, and it belongs in the first build. *(Restraint, priority #2: keep exploration narrow — sampling a clearly-worse branch is a wasted, possibly task-failing action that costs tokens. Explore only among near-tied candidates — a `choose(1)` over a 2–3-way `@weight` set — not a flat distribution over everything.)*

**(b) *Learning* the probabilities — a contextual bandit, and a slow-clock job.** Updating the distribution from outcomes (`P(branch) ↑` when it led to a passed `check()`) is the genuinely adaptive version, under three hard constraints:

- **Sound signal only.** Update from `check()` / exit-code outcomes, *never* from the model's own judgment — intrinsic self-tuning erodes accuracy the same way intrinsic self-correction does (§1; notes §2).
- **Sample + isolation reality.** One task (~tens of steps) has almost no signal, and each TB-2 trial is a *fresh container/process* — so a learned distribution must persist **host-side across trials**, making this a *cross-trial* contextual bandit (context = task features), not within-task learning.
- **Determinism is the line.** Probabilities *drifting live, unlogged* break the cage's replay guarantee — the very thing the cage exists to provide (§5; the two-clock rule, notes §4). The optimizer trades determinism for a fraction of a point unless that's an explicit constraint (notes §4, meta-harness).

> **The stance: structure deterministic, leaf stochastic, learning on the slow clock.** Keep the chart's *structure* (states, guards, the verify gate) fixed and legible. Let only the *leaf action-selection* be a seeded stochastic policy. **Learn its probabilities offline** — run the bandit over the dry-run trials (§8), freeze the tuned distribution, ship a deterministic-given-seed chart. Transition probabilities are the **narrowest, most auditable search space** there is (a handful of scalars, not a code rewrite), which makes them the ideal first step toward the Meta-Harness *search* horizon (notes §4, hand-author-now/search-later) — without collapsing the two clocks. Online learning is permissible *only* if the update is a deterministic function of logged sound outcomes + the seed, and the learned state is **reset/versioned per submission** so the run still replays.

Net for priorities: seeded-stochastic selection (a) is accuracy-positive (pass@k) and replayable → **build it in**; probability *learning* (b) is a slow-clock optimization that must stay sound + logged → **defer, and never let it drift live in a scored run.**

## 7. What it would actually take to beat the record

Honest framing — the [notes](README.md) earn it:

- **The harness lever is largest at the frontier**, where the model cluster is packed and the scaffold decides order. So this cage must run on a **top model** (GPT-5.5 / Opus-class — what the 84–85% leaders use), not a cheap one. The harness is necessary, not sufficient.
- **"Beat records" is an empirical claim, not a design claim.** This design targets exactly the failure classes the leaders engineer *plus* two structural guarantees they implement only as middleware (unreachable-premature-done, sound-only retry). That's a credible top-tier *candidate* — but whether it beats ~84–85% is answered only by the `-k 5` dry-run → full run, with CIs. We do **not** put a number on it before measuring.
- **Token/time "records" aren't leaderboard-ranked** (the board ranks accuracy ± CI). They're our efficiency goals — and the simple-experiment already showed the cage can finish *fast* when it converges; the anti-spin budget is what protects that.

## 8. Validation plan (eval-driven — notes §4)

> ✅ **Smoke test passed (2026-06-15).** `mpl_agent_v2.py` + `terminal_v2.mpl` resolved `hello-world` **1/1 (100%)** on `gemini/gemini-2.5-flash` (`terminal-bench-core==0.1.1`). The verify gate **fired** (`checks=3`); the separate verifier authored a textbook-sound predicate — `test -f hello.txt && printf "Hello, world!\n" | diff -q hello.txt - && test "$(find . -maxdepth 1 -mindepth 1 ! -name hello.txt | wc -l)" -eq 0` — re-deriving *all three* observable requirements (exists / exact content+newline / **no other files**) from the public instruction, no oracle touched. Cost: solver 332/43, verifier 243/64 tokens. The hidden `bash /tests/run-tests.sh` ran only *after* the session ended, confirming the soundness analysis live. *Finding:* Gemini's free tier threw transient `ServiceUnavailable`/`RateLimit` on some `Think`/`check` calls — the bounded-retry cage absorbed them and still resolved, but **the 89×5 sweep should use a paid/reliable endpoint** (OpenAI, or a higher Gemini tier) to avoid contaminating accuracy with infra flakiness (the same trap that bit the earlier multi-task sweep).

> 📊 **Metering pilot (2026-06-15, `gpt-5.2`, 3 tasks).** `fix-permissions` ✅, `openssl-selfsigned-cert` ✅, `csv-to-parquet` ❌ → **2/3**. Real per-task tokens (total in / out): fix-permissions **1.7K / 156**, openssl **4.7K / 788**, csv **6.4K / 579** — i.e. **~5× lower than the earlier 25K-input extrapolation**. Retightened projection: full **89×5 ≈ $7–21** on gpt-5.2 (output at $14/M roughly matches input at $1.75/M despite far fewer tokens, so terse commands matter); the pilot itself cost **~$0.04**. Three findings, in order of importance:
> 1. **The verify gate didn't fire on 2/3 tasks (`checks=0`).** On multi-step tasks the solver spent the whole 16-step budget and hit the `@priority` Abort path *before* ever claiming done — so the gate was bypassed and resolution rode on the base loop alone. **The gate's accuracy thesis is currently untested at scale.** Lever: raise `max_steps` (chart, currently 16; try ~30–40) so the solver can finish and claim done, *then* the gate engages. This is the #1 thing to fix before a sweep meant to measure the gate.
> 2. **Container-death error flood — FIXED.** When commands hit the 180s tmux timeout and tb killed the container, the sim kept ticking ~120× against a dead container (~7 min wasted/​task, would explode at 89×5). `mpl_agent_v2.py` now stops after 3 consecutive failed host calls (`host_dead`).
> 3. **180s per-command timeout** bit `csv-to-parquet` (heavy install/convert). Some tasks need a longer command timeout or a different task selection.

> ✅ **Re-pilot (2026-06-15, `max_steps`=30 + the termination fix, same 3 tasks).** Both findings resolved: **3/3 resolved**, the gate **fires on every task** now (`checks` = 1 / 2 / 3), **zero dead-container errors**, ~11.5 min (was ~18). On the multi-step tasks the gate did real work — `openssl` `checks=2` and `csv-to-parquet` `checks=3` (which flipped ❌→✅) mean the verifier caught incomplete state and drove verify→retry cycles, not a rubber-stamp. Real per-task tokens *with the gate active* (total in / out): fix-permissions **1.7K / 178**, openssl **18.3K / 2.6K**, csv **18.9K / 1.3K** — higher than the gate-bypassed run because we're now paying for the verifier calls + extra solver steps (the accuracy mechanism). **Retightened cost: full 89×5 ≈ $15–30 on gpt-5.2** (central ~$19; the gate roughly doubles the gate-bypassed estimate); this 3-task re-pilot cost **~$0.13**.

> 🧪 **Attribution eval (2026-06-15, gpt-5.2, gate-ON vs gate-OFF ablation, 5 tasks × k=5 = 50 trials).** The honest, decisive result: **the verify gate produced ZERO accuracy change.** Identical per task — fix-permissions 5/5=5/5, openssl 4/5=4/5, csv-to-parquet 4/5=4/5, heterogeneous-dates 0/5=0/5, organization-json-generator 0/5=0/5; **both conditions 52% (13/25)**, not even a per-task swap. And it wasn't free: gate-ON cost **+48.8K input / +10K output tokens** (16 verifier calls) over the ablation, for no gain. **Root cause (from logs):** the gate's target failure mode — premature / false done-claims — *did not occur*. Resolving tasks resolve because gpt-5.2 actually completes them and claims done correctly (the gate just rubber-stamps). The 0/5 tasks fail with `checks=0` on **every** trial — the solver never claims done; it gets **stuck** (organization-json-generator looped on `ls`/`cat` re-exploration and emitted a Unicode-corrupted command `ls -ლა`), exhausts the budget, and hits Abort, so the gate never engages.
>
> **Keep/cut (§8 discipline):** on a *capable* model the sound verify gate is **inert** — it guards a failure class gpt-5.2 doesn't exhibit. It is sound and cheap to leave dormant, but it is **not the accuracy lever here.** The real lever this eval points at is **progress / stuck-detection** (catch repeated-failed or no-progress commands and intervene) — a *different* region than the gate. **Next experiments:** (a) re-attribute the gate on a *weaker* model (Haiku / Gemini-flash) where premature-done is common (the Stanford transfer result predicts harness value varies by model); and/or (b) build a stuck-detector region and attribute *that*. Do not scale the gate to 89×5 expecting accuracy — this data says it would just add cost.

1. **Baseline = terminus-2**, not our v1 demo. Measure where each region adds over a real harness.
2. **Add one region at a time** (gate → grounding → plan → memory), `-k 5` on a **hard subset**, keep/cut by CI. (System-prompt-only *regressed* −2.3pp — single-change attribution is the only honest way.)
3. **Report CIs, never a point estimate.**
4. **Do-nothing sanity check** through the cage — any resolve credit is a signal leak.
5. Only then scale to **89 × 5** and submit when the board reopens.

## Risks — what to validate first

- **MPL syntax/feature gaps** (notes §3 gaps) — ✅ **partly resolved by the SPIKE ([`spike-findings.md`](spike-findings.md), 2026-06-15):** `@priority` winning the tick (incl. the `S1|S2 when … =>` priority-Abort form) **WORKS**; the `check()`-once-then-branch (write-in-`then`/read-next-tick) **WORKS**; `choose(n)/@weight` weighted-*stochastic* selection **DOES NOT** — it's deterministic and seed-independent, so §6's entropy moves to a host-seeded RNG (corrected in §6). *Still unconfirmed:* scalar-only host types at the v2 surface, and `check()` soundness (below). The `§` pointers in the notes were approximate.
- **Can `check()` be sound without leaking the hidden oracle?** — ✅ **DESIGNED ([`check-soundness.md`](check-soundness.md), 2026-06-15):** confirmed the hidden grader is injected into `$TEST_DIR` and run only *after* the session ends (the `Dockerfile` doesn't `COPY tests/`), so the oracle is both unreachable and off-limits during the run. Sound `check()` = a deterministic predicate over the *real* end-state, re-derived from the *public instruction* by a **separate verifier pass**, verdict = exit code. A FAIL is a real observable deficiency; a PASS is necessary-not-sufficient (coverage varies by task). The skeleton's unbounded verify-fail loop was itself a failure mode (a wrong predicate traps a correct solution) → chart now does **bounded retries then SUBMIT**, deferring to the sound external grader.
- **Replay guarantee** at the decide leaf (`TICK/seed` not injected) — pin what we can, log the rest, and state the honest claim.

## Next step

✅ **Built + smoke-passed** (in this folder): `terminal_v2.mpl` (chart, dry-run-green via `_chart_dryrun_v2.py`) + `mpl_agent_v2.py` (four host-imports — `observe`/`decide`/`act`/`check` — over the live session, `check()` = the separate sound verifier). `hello-world` resolved 1/1 (§8). **Next:** run the §8 validation loop on a **hard subset** (`-k 5`, one region at a time, vs the terminus-2 baseline) on a reliable endpoint, then scale to 89×5.
