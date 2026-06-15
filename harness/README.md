# Harness research — building effective LLM agent harnesses

*Findings on how to build effective LLM agent harnesses — particularly for **Terminal-Bench 2.0** — distilled from this repo's [research summaries](../docs/research-summaries/), deep web research, and the MPL v2 feature surface (the `mplv2` repo). The operational charter — the MPL-cage we're hand-authoring toward a TB-2 submission — lives in [`terminal-bench/benchmark/`](../terminal-bench/benchmark/README.md); this folder is the research that feeds it.*

*These are **approach notes**, not a design: a methodology and a technique menu to iterate against. We are deliberately **not** drawing the chart here.*

---

## How to approach the best-possible TB-2 harness

### 1. What a TB-2 harness must actually do well

TB-2 grades **final container state only** — blind to commands, narration, or the model's claim of "done" (repo: `terminal-bench`). So the harness is judged on three failure classes (the paper's taxonomy):

| Failure class (what goes wrong) | Maps to | Where it bites |
|---|---|---|
| **Execution** | wrong/failed commands | `command not found`/PATH is **24.1%** of all failures; "running executables" next at 9.6% (repo: `terminal-bench`, web: arxiv.org/html/2601.11868v1, high) |
| **Coherence** | context loss, derailment, reasoning↔action mismatch | ~25% of trajectory failures; tasks are hour-to-10-day long-horizon (repo: `terminal-bench`; web: www.warp.dev/blog/terminal-bench, high) |
| **Verification** | premature/weak/no "done" | the class that bit our v1 demo; the agent self-certifies and the grader disagrees (repo: `terminal-bench`, `harness-engineering`) |

…against three engineering axes we are not allowed to trade away silently:

> **Cost** (89×5 = 445 frontier-reasoning trials per submission), **determinism** (TB-2 allows internet, so the *benchmark* isn't replayable — but the *cage* must be, pinned at the `decide` leaf), and **auditability** (a "we gained X points" claim is only honest with a replayable trace + CIs).

> **The lever is the harness, not the model.** With weights fixed, harness-only edits move resolve rate by up to **6×** (repo: `meta-harness`) or **25 leaderboard places** (repo: `agent-harness-anatomy`); LangChain moved one agent **52.8%→66.5% (+13.7pts)** on the same GPT-5.2-Codex weights purely via middleware (web: explainx.ai/blog/agent-harness-engineering-terminal-bench-langchain-2026, medium). The frontier model cluster is packed (63/58/57%), so the scaffold decides order (repo: `terminal-bench`). Every point we want comes from here.

### 2. What the leaders + the literature actually do

The recurring techniques, attributed:

- **One headless-terminal tool over a real tmux pane**, model emits `{keystrokes, duration}` and re-polls instead of blocking (Terminus-2 — verified locally in the installed `terminal-bench` package, `terminal_bench/agents/terminus_2/terminus_2.py`). Model-agnostic, no provider-specific schema — the neutral testbed.
- **Head+tail output truncation** at a fixed byte budget (first 5KB + last 5KB of >10KB output) — the two highest-signal regions (Terminus-2, high; mirrored by Anthropic context-engineering, web: anthropic.com/engineering/effective-context-engineering-for-ai-agents, high).
- **A completion gate**: Terminus-2's two-step "are you sure?" re-inspect-and-reaffirm (high); LangChain's spec-driven `PreCompletionChecklistMiddleware` (medium). Both are enforced self-verification before the irreversible grade.
- **Loop / no-progress detection** to halt doom-spirals — turns and tokens do **not** correlate with success (repo: `terminal-bench`; web: explainx.ai, medium).
- **Filesystem-as-durable-state + continuation loop** (the Ralph Loop: a hook that re-injects the prompt in a clean context). Progress lives in git + `progress.txt`, not the window (repo: `agent-harness-anatomy`; web: anthropic.com/engineering/effective-harnesses-for-long-running-agents, high; ghuntley.com/ralph/, high).
- **Proactive summarize-then-handoff** before context overflow, reactive unwind as fallback (Terminus-2, high).
- **Tool-grounding pre-flight** (`command -v` before invoke) attacking the 24.1% bucket at ~zero token cost (repo: `terminal-bench`, high).
- **Structure beats prose, measured**: tools +3.3pp, middleware +2.2pp, long-term memory +5.6pp — but a system-prompt-only variant **regressed −2.3pp** (repo: `agentic-harness-engineering`; web: arxiv.org/html/2604.25850v3, medium).
- **Model-harness fit**: present the edit-format/verbs the target model was post-trained on (Codex `apply_patch` vs Claude `old_string`); multi-point swings attributed purely to fit (web: nicolasbustamante.com/blog/model-harness-fit, medium — single-source, treat as directional).

> **The soundness rule that governs all of it (repo: `harness-engineering`, `llm-modulo`):** a deterministic check is **sound** (it has *proven* something); an LLM-judge verdict is **advisory** only. Never read "a green from a model-written check" as "verified." TB-2's container oracle is the only sound critic — the harness's notion of done must terminate there, not in an LLM's "looks good." Self-critique without an external signal can *decrease* accuracy (GPT-4 GSM8K 95.5→89.0 over two intrinsic rounds; web: openreview.net/pdf?id=IkmD3fKBPQ, high).

### 3. Technique menu (capability → evidence → cost → failure class → MPL expression)

Each row is a *candidate*, not a commitment. "MPL expression" maps to the v2 feature surface in the bundle and **flags gaps honestly**.

| Capability | What it is | Evidence it helps | Trade-off / cost | TB-2 class | How MPL could express it (+ gaps) |
|---|---|---|---|---|---|
| **Plan → execute** | Emit ordered sub-goals onto a blackboard before touching the shell | Plan-and-Solve fixes "missing-step" errors, beats Zero-shot-CoT (web: arxiv.org/abs/2305.04091, high); Warp's editable todo was *preferred over* extended thinking (web: www.warp.dev/blog/terminal-bench, high) | One extra LLM round-trip; plan can ossify | Coherence | A `Planning` **State** (`Overview §3.3`), plan written to typed **vars** blackboard (`§4.1`); ENTER on `Plan` fires the host `decide` call (`§6.1`) |
| **Verify-before-done** | Re-derive a container-side check (re-run, diff, assert exit code) before "done"; gate the finalize edge | Outcome self-checks raise resolve rate (repo: `terminal-bench`); CRITIC tool-grounded +7.7 F1, self-critique-only lower (web: arxiv.org/pdf/2305.11738, high); LLM-Modulo Blocksworld 35%→82% via sound VAL filter (repo: `llm-modulo`) | Costs a real test run each gate | Verification | `Verify when checks_failed => Retry` **guard** (`§7.2`); the finalize transition is `=>` gated so "accepted under-specified result" is **unreachable** not penalized (`§7.3`). **MPL has no native test-runner** — verification is a `host import { run_checks(...)->string }` (`§3.6`); the soundness lives in the Python host, MPL only routes on it |
| **Bounded retry / recovery** | Retry on *external* failure signal with a stop-on-repeated-failure cap; hand the error **location** to the fix step, don't ask the model to self-diagnose | Only retry on oracle signal — intrinsic retry hurts (web: openreview.net, high); LLMs bad at *finding* errors (GPT-4 52.9%) but good at *fixing* given location (web: arxiv.org/html/2311.08516v3, high); Reflexion lifts HumanEval to 91% **when grounded in execution reward** (web: arxiv.org/html/2303.11366, high) | Each retry is more tokens; unbounded = budget burn | Execution + rate-error | Retry counter in **vars**; cooldown idiom (`Cooling -> {cooldown-=1}; when cooldown<=0 => Ready`, see `examples/starship.mpl` / `squad_tactics.mpl`); a Verifier **emits** `FAIL`, the retry region `receives { FAIL }` (`§6.1`). Reflexion buffer = bounded **vars** slots |
| **Blackboard / context mgmt** | Hold task spec + constraints + last error in explicit slots re-read each step; head/tail-truncate + offload bulk to files; milestone-curated long-term memory | Naive Last-K reflection *hurt* (56.1 vs 60.2); milestone curation helped (61.86) and saved ~3.3 steps (repo: `os-symphony`); structured note-taking (web: anthropic.com context-engineering, high); don't compress diagnostic signal to a scalar (repo: `meta-harness`) | Curation policy is itself code to maintain | Coherence + cost | Typed **vars** = blackboard, persist across ticks (`§4.1`); **regionmaps** as a work-item/sub-agent registry (`§5`). **Caveat:** spec/invariants must live in vars (which persist), **not** activation values (which reset next tick, `§11.2`) — a documented footgun. OpenClaw deleted 200+ emails when compaction summarized away a pinned rule (repo: `openclaw-emails`) |
| **Tool grounding** | Probe executable exists before invoke; reject syntactically-bad edits before they land | 24.1% command-not-found bucket (repo: `terminal-bench`, high); SWE-agent's *whole interface* (incl. linter-reject guardrails) lifted pass@1 3.8%→12.5% (web: emergentmind.com/topics/swe-agent-frameworks, high); AgentSpec guard blocks >90% risky exec at ~3ms (repo: `agentspec`) | Pre-checks add turns; over-guarding blocks valid work | Execution | A **guard** state before the act leaf (`Doing when tool_present => Run`), or a compiled host pre-check. AgentSpec's `before_action`/`on_finish` typed boundary ≈ MPL guarded transitions + `@priority` safety override (`§8.6.1`) |
| **Parallel / sub-agent actions** | Fan out read-only exploration to isolated-context sub-agents; serialize anything that mutates | Sub-agent isolation returns ~1-2k-token summaries (web: anthropic.com context-engineering, high); Ralph: many parallel for search, **exactly 1** for build/tests (web: ghuntley.com, high); TDFlow decomposition beats monolithic ReAct (web: arxiv.org/pdf/2510.23761, high) | **The handoff seam leaks**: parent/child recall collapses to ~0.32 vs 1.00 single-context (repo: `nlah`) | Coherence (the seam) | `spread { => CallA; => CallB }` fan-out (`§9.2`); **machine** parallel containers (`§2.1`); `@conflict(resource_id)` mutex so only one sub-agent grabs the shell (`§9.4`). **Prefer a global immutable per-tick snapshot every region reads** over private task-packets (repo: `nlah`). **Gaps:** runtime `new` has **no `destroy`** (manifest grows monotonically — a leak for long loops, `§3.4 partial`); rule-spawned regions are **not** restored by snapshot (`§17.8`) |
| **Action selection** | Pick one (or top-N) candidate action at the decide leaf; utility/weighted or hard-priority override | Utility `@priority(expr)` selection is a proven game-AI pattern (`§ examples/town.mpl`); `choose(1)`/`choose(2)` bounded selection (`§9.1`) | Stochastic = need seed for replay | Coherence/Execution | `Deciding choose(1) { @priority(urgency) ...; @weight(score) ... }` (`§9.1`, `§8.6.2`); deterministic Priority→Weight→seeded-Random pipeline (`§12`) makes arbitration reproducible |

> **Cross-cutting MPL gaps to carry honestly (from the feature bundle):** (a) **host-import types are scalar-only** — bool/int/float/string/vector<N>, *no dict/list* — so LLM messages and JSON tool args cross the seam **as strings** parsed host-side (`§17.12 partial`, `host.py:39-83`); (b) **seed determinism is partial** — `SIM/seed` is injected and real, but per-tick `TICK/seed`/`TICK/hash` are *proposed, not injected* (AUDIT T3.4), and the **LLM call's own nondeterminism is outside the seed entirely**; (c) **SDK surface has conflicting docs** — Feature Status (2026-04-30) says Phase 1–4 implemented+tested (714 tests), AUDIT (2026-04-22) says `__init__.py` empty — trust the newer status but **re-verify against the live package** before building; (d) `regionmap clear()` and `SourceAnd` in iteration have conflicting/absent support — verify before relying.

### 4. Recommended PROCESS, not a product

Eval-driven iteration, RPP-style — the same discipline the literature insists on (validate every change against a held-out suite, not vibes; repo: `eval-driven-iteration`, `agentic-harness-engineering`):

1. **Baseline first.** Start from **terminus-2** as the reference harness, not our v1 demo. It already has the truncation, summarization, completion-gate, and retry plumbing — measure where the *cage* adds over it, not over a strawman.
2. **Add exactly one region, then measure.** Draw one capability from the menu, dry-run on a **hard subset with `-k 5`**, keep or cut. Non-monotonic regressions are real (a "be more thorough" prompt silently degraded grounded behavior; system-prompt-only **regressed −2.3pp**) — one change at a time is the only way to attribute a delta.
3. **Report CIs, never a point estimate.** TB-2 runs ≥5 per cell *because* single runs are noisy (32,155 trials total; ABC checklist demands CIs — repo: `agentic-benchmarks`). A one-shot number can't tell improvement from variance.
4. **Sanity-check the harness itself.** Run a **do-nothing / scripted baseline** through the cage; any resolve credit it earns is a signal leak (tau-bench's do-nothing agent passed 38%; TB-2's own dummy-agent gauntlet — repos: `benchmarks-broken`, `terminal-bench`).
5. **Hand-author now, search later.** We pull the lever **by hand** against hard tasks. Meta-Harness-style *search* is the horizon — and the cage's deterministic-given-seed replay is a *cleaner* search target than arbitrary Python — but only **after** we know what a good hand-authored chart looks like. Auditability is a property of the *authoring process*: a searched harness no human vetted is not the same trust object, and the optimizer will trade determinism away for a fraction of a point unless it's an explicit constraint (repo: `meta-harness`).

> **Two-clock rhythm (repo: `llm-modulo`).** Author the chart slowly, once, under review (the slow clock — orchestration, guards, rubrics). Execute it fast and many times autonomously (the fast clock — per-step host calls + deterministic checks). MPL's policy/mechanism split fits this: policy is the readable `.mpl` you ablate; mechanism (running tests, parsing, grading) stays sound Python reached via host imports (repo: `nlah`).

### 5. Open questions / risks to resolve *before* designing

- **Can `verify` run the hidden tests?** TB-2 grades on hidden final-state checks the agent must not see (Integrity: future git commits are stripped — repo: `terminal-bench`). Our `Verify` region can re-run the task's *own* visible checks, but it **cannot** read the grader. Open: how close can a sound self-check get to the hidden oracle without leaking it (which would inflate resolve rate *and* fail the integrity bar)?
- **Determinism at the `decide` leaf.** We can pin MPL's internal randomness via `SIM/seed`, but the LLM host call is nondeterministic and `TICK/seed` is *not injected* (AUDIT T3.4). What's the actual replay guarantee we can claim?
- **Cost ceiling.** 445 trials of a frontier reasoning model is tens-to-hundreds of dollars. What's the per-task token/$ cap that triggers `Abort` (`when TICK/count > max_steps`, `§13.1`), and does milestone-curated memory actually keep us under it?
- **MPL feature gaps that could block a region.** No `destroy` (sub-agent leak on long loops); scalar-only host types (rich tool I/O as strings); snapshot doesn't restore runtime-spawned regions or `on()` callbacks; SDK doc conflict unresolved. Each must be confirmed against the **live package** before a region depends on it.
- **Where does verification fire?** Before generation (bound what can be claimed) vs on the transition exit (verify-then-commit, three-valued proceed/gather-more/retract — repo: `rag-attribution-survey`)? The exit-gate is the strongest point but costs a check every finalize attempt.
- **HALT reachability.** A stop signal (budget exhaustion, loop-detector) must win over the in-flight action — OpenClaw's remote stop *lost* the priority contest and only a power-off ended the run (repo: `openclaw-emails`). Confirm `@priority(100)` on an Abort edge actually beats every normal transition in the same tick (`§8.6.1`).

### 6. Provenance & verification status

*Synthesized by a fan-out research workflow, then **verified by a second fetch-and-confirm pass** (2026-06-12).*

- **Web + paper citations: verified.** All 15 load-bearing sources were fetched and confirmed — including the LangChain **+13.7pt (52.8→66.5)** figure (verbatim on `explainx.ai`), the TB-2 **24.1%** command-not-found figure, and the Reflexion / CRITIC / self-correction / Plan-and-Solve / agentic-harness-ablation numbers (all matched their cited figures). Two were **corrected for over-claiming**: Warp's planning todo was *preferred over* (not "beat") extended thinking, and the SWE-agent 3.8→12.5% lift is attributable to its *whole interface* (incl. linter-reject guardrails), not linter-reject alone.
- **Repo claims (`repo: <slug>`)** come from this repo's research summaries; the Terminus-2 technique was verified against the **installed** `terminal-bench` package (`terminal_bench/agents/terminus_2/terminus_2.py` — in the WSL venv, not the repo tree, so re-checking needs that venv).
- **MPL `§` section numbers remain approximate** — they come from an agent's reading of the external `mplv2` repo (not in this tree), so the citation pass did **not** re-verify them. Treat them as pointers and **verify against the live package/docs** before a region depends on a feature (the SDK doc conflict in §3(c) is why).

> Net: the external evidence is now confirmed. The only references not verifiable from this repo are the MPL `§` pointers (external source) — confirm those against the live `mplv2` package when building.

## See also

- [`terminal-bench/benchmark/`](../terminal-bench/benchmark/README.md) — the operational charter that draws on these notes (the MPL-cage for TB-2).
- [`terminal-bench/simple-experiment/`](../terminal-bench/simple-experiment/README.md) — the harness lever, measured (fix the brain, swap the cage).
- The [Terminal-Bench](../docs/research-summaries/terminal-bench/terminal-bench.md), [Meta-Harness](../docs/research-summaries/meta-harness/meta-harness.md), and [agent-harness-anatomy](../docs/research-summaries/agent-harness-anatomy/agent-harness-anatomy.md) summaries (the ruler, the search, and the practitioner anatomy this synthesis leans on).
