![Agentic Harness Engineering glyph: a coding agent emits a raw trace, an agent-debugger distils it to layered evidence, an evolve agent commits a file-level harness edit carrying a predicted-impact manifest, and the next round's outcome verifies or reverts it — a closed loop](images/glyph.svg)

# Agentic Harness Engineering, *evolved*

*Cliff notes on Lin, Liu, Pan et al. (Fudan, Peking, Shanghai Qiji Zhifeng), "Agentic Harness Engineering: Observability-Driven Automatic Evolution of Coding-Agent Harnesses" (arXiv:2604.25850, April 2026) — the paper that takes [Meta-Harness](../meta-harness/meta-harness.md)'s "search the cage" and bolts on the governance layer that summary said was missing: every edit a falsifiable contract, every rejected edit reverted, the verifier locked out of reach. And then it measures the one thing harebrain most needed measured — whether a self-editing cage can see what it's about to break.*

---

## What this paper is, relative to its siblings

This is the third harness paper in the bibliography, and the family resemblance is the point. [Meta-Harness](../meta-harness/meta-harness.md) made the harness a *search target* and proved it was the 6× lever. [Harness Engineering](../harness-engineering/harness-engineering.md) (Böckeler) named the harness as a *craft* — feedforward guides, feedback sensors, a cybernetic governor. AHE takes the search idea and asks the question both siblings left open: **if a machine is going to evolve the cage unattended, what stops it from cheating, and can it tell when it has made things worse?**

The answer is an architecture organised entirely around one word — *observability* — split into three matched pillars. The thesis, taken verbatim:

> **The pivot.** "Jointly evolving multiple components end-to-end faces two structural obstacles: long, unstructured trajectories yield little actionable signal, and tightly coupled harness frameworks make edits beyond the prompt error-prone." The central insight is that autonomous harness evolution "is bottlenecked by *observability*, not by agent capability: once the evolution agent receives structured context over a clear action space, it can reliably converge on better harness designs."

That is a different diagnosis from Meta-Harness, which said the bottleneck was *feedback compression* (scalar scores destroy the diagnostic signal). AHE agrees on the symptom and goes one layer deeper on the cure: it is not enough to hand the evolver raw traces — the *action space* (what is editable), the *evidence* (what failed and why), and the *decision* (what each edit predicted) all have to be made into legible, file-level, revertible artifacts. Three pillars, one for each.

## The three observability pillars

![The AHE closed loop, Algorithm 1: a minimal bash-only seed harness on the NexAU substrate exposes seven component types as files; the Code Agent runs k rollouts per task into raw traces; the Agent Debugger distils ten million trajectory tokens into a layered, drill-down evidence corpus; the Evolve Agent reads the evidence and commits file-level harness edits, each carrying a manifest entry that predicts the fixes and at-risk regressions; the next round's task-level deltas verify each prediction, and ineffective edits are rolled back at file granularity before the loop repeats.](images/fig-01-ahe-loop.svg)
*One iteration, three observable surfaces. Components are files (so the action space is explicit and revertible), trajectories are distilled (so the signal survives), and every edit ships a prediction that the next round grades (so a rationale becomes a contract). Ten iterations of this lift Terminal-Bench 2 from 69.7% to 77.0%.*

**Pillar ❶ — Component observability** is realised by **NexAU**, a decoupled substrate that exposes *seven orthogonal component types as explicit files* at fixed mount points in one workspace: system prompt, tool description, tool implementation, middleware, skill, sub-agent config, and long-term memory. The component types are loosely coupled — adding a middleware does not require editing the system prompt; adding a skill does not touch any tool. The payoff: "each failure pattern maps cleanly to a single component class," and "each logical edit becomes one commit on the workspace's git history, which yields file-level diffs and rollback granularity for free." The seed harness `H₀` is *deliberately minimal* — a single shell-execution tool, no middleware, no skills, no sub-agents — precisely so that "a seed already fitted to the target benchmark would contaminate every subsequent edit's attribution." The minimal seed forces every component AHE adds to earn its place against measured rollouts.

**Pillar ❷ — Experience observability** is the **Agent Debugger**: `k` traces per task produce *millions of tokens of raw messages*, and a debugging agent navigates them as a file-based environment (each trajectory message is its own file, reached through generic shell tools), analysing the root cause of each failure or success into a *per-task analysis report*, then aggregating a *benchmark-level overview* as the entry point for each iteration. The corpus is layered for **progressive disclosure** — the evolver reads a ~10K-token overview and drills down into the ~10M-token raw traces only where it needs to, with the original traces kept available so claims in the reports can be verified rather than trusted.

**Pillar ❸ — Decision observability** is the part the siblings don't have, and it is the reason to read this paper. The **Evolve Agent** closes the loop under two constraints that together turn every edit into a *falsifiable contract*:

- **Controllability.** The Evolve Agent "writes only inside the harness workspace, while the runs directory, tracer, verifier, and LLM configuration are read-only, and the seed system prompt is marked non-deletable." These restrictions "block the shortcuts an unconstrained self-modifier would take, such as disabling the verifier, swapping the model, or raising the reasoning budget."
- **Evidence-driven edits.** "Every change ships with a recorded prediction." Each edit attaches a manifest entry naming the failure evidence, the inferred root cause, the targeted fix, and a *predicted impact comprising both expected fixes and at-risk regressions*. The next round intersects the predicted-fix and predicted-regression sets with the observed task-level deltas to produce a *per-edit verdict*. "Each edit thereby becomes falsifiable by the next evaluation, which replaces rationale-driven self-justification with a measurable contract between rounds."

> **Why this is the missing layer.** The [Meta-Harness](../meta-harness/meta-harness.md) summary ended on a warning: `arg max_H` "has no term for auditability, determinism, or reachability invariants — keep the human review and the invariant-checking evaluator, or the search will trade them away for a fraction of a point." AHE is that warning, answered in code. Git-commit-per-edit is the audit trail. The read-only verifier/model/reasoning-budget is a lockbox the optimiser cannot route around. The predicted-impact manifest plus file-granular rollback is the invariant-checking evaluator, run every round. AHE is Meta-Harness with the governance the first paper deferred to "future work."

The outer loop (their Algorithm 1) composes the three: **rollout** (`k ≥ 2` per task, so each task carries a pass-rate signal that stabilises pass@1) → **clean** (normalise traces) → **attribute** the prior round's manifest and *roll back rejected edits* → **distill** (Agent Debugger) → **evolve** (workspace edits + new manifest) → **commit** (tag the iteration in git). Attribution runs *before* distillation, so its verdict lands inside the evidence corpus as a contract rather than a rationale. All three role agents — Code Agent, Agent Debugger, Evolve Agent — share one base model (GPT-5.4 at high reasoning), which isolates the gain to the harness edits rather than to a stronger analyser or editor.

## The evidence

Three research questions: where AHE sits versus alternatives, whether the product transfers off its optimisation target, and what inside the loop drives the gain.

**RQ1 — main result.** Ten AHE iterations on the bash-only seed lift pass@1 on Terminal-Bench 2 from **69.7% → 77.0%** in roughly 32 hours, beating every baseline on the panel:

| Harness | Terminal-Bench 2 pass@1 (All / Easy / Med / Hard) | Kind |
|---|---|---|
| OpenCode | 47.2 / 75.0 / 52.7 / 33.3 | human-designed |
| Terminus-2 | 62.9 / 75.0 / 74.5 / 40.0 | human-designed |
| Codex | 71.9 / 75.0 / 80.0 / **56.7** | human-designed |
| NexAU₀ (seed) | 69.7 / 87.5 / 78.2 / 51.7 | minimal seed |
| ACE | 68.9 / 91.7 / 78.2 / 48.9 | self-evolve (prompt) |
| TF-GRPO | 72.3 / 100.0 / 79.4 / 55.6 | self-evolve (traj. feedback) |
| **AHE** | **77.0 / 100.0 / 88.2 / 53.3** | self-evolve (full harness) |

The two self-evolve baselines (ACE, TF-GRPO) start from the *same* seed and lose. The reason is a *layer mismatch*: "ACE distills natural-language playbooks the agent reads in-context, and TF-GRPO is a trajectory-feedback variant of GRPO that reinforces successful tool sequences; neither method opens the surrounding scaffolding to edits." AHE jointly evolves system prompt, tools, middleware, and long-term memory — and the ablation (below) shows the gain lives in exactly the three components prompt-only methods leave untouched. The lone exception is the Hard tier, where AHE marginally trails Codex (53.3 vs 56.7); the paper traces this to *component interference* on long-horizon tasks, not a missing capability — swapping AHE's long-term memory alone into the seed already surpasses Codex on Hard.

**RQ2 — transfer.** The frozen harness, with *no further evolution*, is evaluated on SWE-bench-verified (500 tasks, 7 repos) and three alternate model families:

- **Cross-benchmark.** AHE achieves the **highest aggregate success (75.6%) while spending 12% fewer tokens than the seed** (461 vs 526 ktok). ACE and TF-GRPO both *regress below the seed* in aggregate while spending 11–29% *more* tokens — their distilled playbook and reinforced trajectory ride the prompt at every model call, so a different task surface adds cost without reshaping the underlying run. AHE instead "encodes behavior in tools, middleware, and memory," which "avoids the per-call re-derivation cost prompt-only baselines incur." Token cut: **−32% vs ACE, −21% vs TF-GRPO, −12% vs seed.**
- **Cross-model.** Re-evaluated on five alternate bases, the frozen harness yields **+5.1 to +10.1 pp** gains across three alternate families: deepseek-v4-flash +10.1 (51.7→61.8), qwen-3.6-plus +6.3 (56.2→62.5), gemini-3.1-flash-lite +5.1 (36.5→41.6) — all *above* the within-family GPT-5.4 numbers. "Cross-family gains dominate within-family ones," because bases further from saturation "lean more on the coordination patterns AHE has fixed inside tools, middleware, and long-term memory, while a stronger base re-derives the same coordination from its prompt at low marginal cost."

> **The transfer reading.** A harness that ports across task surfaces *and* model families while *cutting* tokens is encoding a strategy, not a benchmark-specific trick — the same bar Meta-Harness's math harness had to clear, met here on two axes at once. The structure beats prose precisely because structure is re-used for free where prose is re-derived per call.

**RQ3a — where the value lives.** Isolating one evolved layer into the seed at a time:

| Variant | All (89) | Hard (30) |
|---|---|---|
| NexAU₀ seed | 69.7 | 51.7 |
| + memory only | 75.3 | **63.3** |
| + tools only | 73.0 | 46.7 |
| + middleware only | 71.9 | 50.0 |
| + system_prompt only | **67.4** *(regresses)* | 46.7 |
| **AHE full** | **77.0** | 53.3 |

Two findings fall out. First, **structure transfers, prose does not**: tools, middleware, and memory each carry the improvement on their own, while the system prompt alone *regresses 2.3 pp below the seed*. The system prompt encodes "79 lines of universal discipline whose executability depends on the other three"; inserted by itself it has nothing to act on. Second, **the components interact non-additively**: the three positive single-component gains sum to +11.1 pp against full AHE's +7.3 pp. Stacking effective edits does not stack their effects — memory, middleware, and the prompt "all push toward the same closure-style verification, so stacking them spends turns on redundant re-checks within the long-horizon budget." The cage has a coordination budget, and the evolver spends part of the Hard-tier memory effect to buy a Medium-tier-dominated aggregate.

**RQ3b — can the loop see what it's doing?** This is the finding harebrain most needed, and it is an *asymmetry*. Each round the Evolve Agent predicts which tasks an edit will *fix* and which it puts *at risk of regression*; the paper scores round-`N−1` predictions against round-`N` ground truth.

![Two panels contrasting the evolve agent's self-prediction accuracy. Left, fix targeting: cross-iteration fix-precision 33.7% and fix-recall 51.4%, each roughly five times its random-prediction baseline (6.5% and 10.6%) — the editor lands on real, anticipated targets. Right, regression foresight: regression-precision 11.8% and regression-recall 11.1%, only about twice their random baselines (5.6% and 5.4%) — most regressions an edit causes are unforeseen. The agent can justify why an edit should help but cannot reliably name what it is about to break.](images/fig-02-attribution.svg)
*The load-bearing asymmetry. Fix-targeting is evidence-driven (≈5× random); regression-foresight is near-blind (≈2× random). "The agent can justify why an edit should help, but it cannot reliably name the tasks the same edit is about to break" — which is what produces the non-monotone dips in the evolution curve.*

The fix panel says the loop is real: 5× over chance means each harness edit "lands on a real, agent-anticipated target rather than on an arbitrary subset of the panel." The regression panel says the loop is *dangerous if trusted to certify its own safety*: at barely 2× chance, "most upcoming regressions go unforeseen." The paper is unusually direct that this is *the* open problem — "closing this gap is the clearest direction for future self-evolution loops" — and lists it in Limitations under "self-modification governance": AHE "bounds edits, attributes them, and rolls back ineffective edits at file granularity, but it does not provide a complete guardrail stack ... AHE should be viewed as a controlled research prototype rather than a fully mature autonomous self-improvement system."

## Where this sits in the harebrain hypothesis

The harebrain thesis is `harebrain = fast LLM brain × structured game-AI cage`. AHE evolves the cage — same object as [Meta-Harness](../meta-harness/meta-harness.md), but with the governance machinery harebrain's [latitude-tier table](../../harebrain/harebrain.md) demanded of any self-editing cage. So this is the paper that moves the "can the cage edit itself safely?" question from argument to measurement.

![Two-column mapping: Agentic Harness Engineering constructs on the left in oxblood, harebrain primitives on the right in blueprint, dashed arrows between matched pairs. NexAU seven-component substrate maps to the cage; component observability (file-per-component, git-commit-per-edit) to the diagnostic surface plus reviewable MPL diff; experience observability (layered evidence corpus) to the deterministic trace where every drift is locatable to a state; decision observability (predicted-impact manifest) to a chart amendment carrying a predicted impact verified next tick; the Evolve Agent to the AI director on the slow clock; the controllability lockbox (read-only verifier and model) to the invariants a Tier-4 self-edit cannot route around; falsifiable contract plus file-granular rollback to a reviewable diff with auto-revert; and pass@1 on Terminal-Bench 2 to the score, which has no term for the regressions the editor cannot foresee.](images/fig-03-mapping.svg)
*Same cage as Meta-Harness, now with a governor. The new rows are the bottom three — the lockbox, the falsifiable contract, and the score's blind spot — which are exactly the auditability/invariant terms the Meta-Harness summary said `arg max_H` was missing.*

| Agentic Harness Engineering | harebrain |
|---|---|
| NexAU 7-component substrate (files at fixed mounts) | The cage — chart + blackboard + guards + typed seam |
| Component observability (file-per-component, git commit/edit) | The diagnostic surface + the reviewable `.mpl` diff / audit trail |
| Experience observability (layered evidence, Agent Debugger) | The deterministic trace — every drift locatable to a state |
| Decision observability (predicted-fix + at-risk-regression manifest) | Every chart amendment carries a predicted impact, verified next tick |
| Evolve Agent (offline, never ships) | AI director on the slow clock — chart authoring |
| Controllability lockbox (verifier/model/budget read-only) | Invariants a Tier-4 self-edit cannot route around |
| Falsifiable contract + file-granular rollback | Reviewable diff + auto-revert; soundness inherited from an external check |
| `pass@1` objective (regression-blind) | The score — no term for what the edit is about to break |

### What the paper gives harebrain

Four things, each load-bearing — and each is an *advance on Meta-Harness*, not a restatement.

- **The governance layer, in code.** Meta-Harness proved the cage is searchable and warned that the search has no term for auditability, determinism, or invariants. AHE supplies three concrete mechanisms for exactly those gaps: a git commit per edit (the audit trail harebrain wanted for every chart version that went live), a read-only verifier/model/reasoning-budget lockbox (the "self-edit cannot disable its own checker" invariant), and a predicted-impact manifest with file-granular rollback (an invariant-checking evaluator that runs every round and reverts edits that don't pay). This is harebrain's Tier-4 amendment process — "a reviewable MPL diff and an audit trail of which chart version was live" — built and measured.
- **The empirical proof that the editor cannot certify its own safety.** The regression-blindness number — 11% recall, barely 2× chance — is the strongest evidence in the bibliography that you cannot let the cage's *author* sign off on the cage's *safety*. The editor is sharp about what it's fixing (5× chance) and blind to what it's breaking. This is [LLM-Modulo](../llm-modulo/llm-modulo.md)'s "soundness is inherited from a sound checker, never from the generator" restated with a measurement: the regression check must be *external* to the editor and *run every candidate*, because the editor's own forecast of breakage is near-worthless. Harebrain's invariant-checking evaluator is not optional polish — AHE shows what happens without it.
- **Structure beats prose, with an ablation.** The system-prompt-only variant *regressing below the seed* while tools/middleware/memory each *gain* is harebrain's "topology bounds, prose steers" thesis, measured. Prose discipline (the 79-line system prompt) is inert without structural components to act on; the durable gains live in the executable scaffolding. A harebrain chart's guarantees should likewise live in its topology and guards, not in the prompt text at its leaves.
- **The non-additive coordination budget.** +11.1 pp of single-component gains collapsing to +7.3 pp combined is a caution harebrain should internalise: guards and edits don't sum. Adding a sound check that overlaps an existing one spends tick-budget on redundant verification for no marginal coverage. A cage has a coordination ceiling, and past it more controls subtract.

### What harebrain pushes that the paper doesn't

Two extensions, both harebrain bets rather than AHE claims.

- **Reachability invariants, not just a meta-lockbox.** AHE's controllability is a fixed *allowlist* at the meta level — don't touch the verifier, the model, the budget. It protects the *evaluation*, which is exactly right, but it has no notion of a *per-transition reachability invariant*: "this state must be unreachable by geometry." Its objective is `pass@1`, and — by its own RQ3b result — a score-driven editor is blind to the regressions that would violate such an invariant. Harebrain's strongest claim is topological: the unwanted state is unreachable, not discouraged. AHE neither offers that nor rewards it, and its regression-blindness finding is the proof that it *can't* be left to the optimiser to discover. Harebrain would compile the invariant into the chart's geometry and verify it externally on every candidate, not hope the manifest predicts the breakage.
- **The seam, formalised.** AHE's NexAU splits "tool description" from "tool implementation" — gesturing at the boundary between what the model is told a tool does and what the tool actually does — but the boundary stays an informal pair of files. Harebrain's typed seam (host-import return values with a declared contract) is the formal version of exactly that split. AHE shows the split *matters* (tools-only is a top gainer); harebrain's bet is that *typing* it is what makes the contract checkable rather than merely separated.

> **The trap to mark, in the paper's own words.** Do not read "evolved harness + predicted-impact manifest + automatic rollback" as "safe autonomous self-improvement." AHE itself refuses that reading: it is "a controlled research prototype rather than a fully mature autonomous self-improvement system," and the 11% regression-recall is the number behind the hedge. The manifest makes every edit *falsifiable*, which is a real and valuable property — but falsifiable-next-round is not safe-this-round. The cage can tell you, after the fact, that an edit broke three tasks; it cannot tell you, before shipping, which three. For harebrain's workflows that is the whole ballgame: the governance AHE built is the right shape, and the external sound check it still lacks is the part that has to be there before a self-editing cage runs unattended.

### Two clocks, with a contract on the slow one

Harebrain's slow/fast split says an LLM authors the chart slowly (with review) and executes it quickly (autonomously). AHE refines the *slow* clock specifically: it is not just "author then review," it is **author → predict → commit → verify → revert**. Every slow-clock amendment carries a falsifiable prediction that the next batch of fast-clock runs grades, and ineffective amendments are reverted at file granularity. That is a strictly better slow clock than "human reads the diff once" — the diff is reviewable *and* the edit is contractually accountable to the next round's outcomes. The piece AHE proves harebrain still needs to add: because regression-foresight is near-blind, the verify step must include an *external invariant check the editor did not write*, not only the editor's own predicted-regression set.

## What's worth taking away

- AHE is [Meta-Harness](../meta-harness/meta-harness.md) plus the governance layer that summary said was missing: git-commit-per-edit (audit), a read-only verifier/model lockbox (the self-edit can't disable its checker), and a predicted-impact manifest with auto-rollback (an invariant evaluator every round). The cage-search question now has a governed answer.
- The headline number is **69.7% → 77.0%** on Terminal-Bench 2 from harness evolution alone, beating human-designed Codex and prompt-only self-evolution — and the frozen harness *transfers* across a second benchmark and three model families while cutting tokens 12%. A real cage encodes strategy, not a trick.
- **Structure beats prose, measured**: tools/middleware/memory each gain; the system-prompt-only variant regresses below the seed. Harebrain's "topology bounds, prose steers," with an ablation under it.
- **The regression-blindness result is the one to carry.** The editor is 5× chance at naming what it fixes and barely 2× chance at naming what it breaks. You cannot let the cage's author certify the cage's safety — the invariant check must be external and run every candidate. This is LLM-Modulo's soundness lesson with a number on it.
- Components **interact non-additively** (+11.1 pp of parts → +7.3 pp combined). A cage has a coordination budget; past it, more controls subtract. Don't stack overlapping guards.
- AHE governs the *meta* level (lockbox + falsifiable contract) but has no *reachability invariant* and no *typed seam*. Those are harebrain's two pushes: compile the invariant into geometry and verify it externally; type the tool-description/implementation split AHE leaves informal.

---

**Sources.** Lin, J., Liu, S., Pan, C., Lin, L., Dou, S., Xi, Z., Huang, X., Yan, H., Han, Z., Gui, T., & Jiang, Y.-G. "Agentic Harness Engineering: Observability-Driven Automatic Evolution of Coding-Agent Harnesses." [arXiv:2604.25850v4](https://arxiv.org/abs/2604.25850) [cs.CL], submitted 28 April 2026 (v4, 18 May 2026) ([raw PDF in this folder](Agentic-Harness-Engineering-Observability-Driven-Automatic-Evolution-2604.25850.pdf)). Affiliations: Fudan University (Lin, Liu, Dou, Xi, Huang, Han, Gui, Jiang), Peking University (Pan), Shanghai Qiji Zhifeng Co., Ltd (Lin, Han). Corresponding authors: Zhenhua Han, Tao Gui. Code: <https://github.com/china-qijizhifeng/agentic-harness-engineering>. Constructs referenced: the three observability pillars (component / experience / decision), the NexAU substrate, the Agent Debugger, the Evolve Agent's controllability and evidence-driven constraints, the predicted-impact manifest as falsifiable contract, and the fix-targeting / regression-blindness asymmetry. Benchmarks: Terminal-Bench 2 and SWE-bench-verified. Companion summaries in this series: [Meta-Harness, *searched*](../meta-harness/meta-harness.md) (the harness as a search target — AHE adds the governance it deferred), [Harness Engineering, *practised*](../harness-engineering/harness-engineering.md) (the harness as a craft, feedforward/feedback), [Terminal-Bench, *graded*](../terminal-bench/terminal-bench.md) (the ruler AHE evolves against), and [LLM-Modulo, *redrawn*](../llm-modulo/llm-modulo.md) (soundness inherited from an external checker — the lesson the regression-blindness result confirms with a number); the [harebrain hypothesis](../../harebrain/harebrain.md) for the cage / two-clocks / latitude-tier vocabulary. All diagrams above are original SVGs drawn for this page.
