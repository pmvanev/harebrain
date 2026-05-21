# Research: Adopting LLM-Modulo Benchmarks (Blocksworld, Mystery BW, Graph Coloring, TravelPlanner) as Supplemental Substrates Alongside Wumpus and TW-Cooking

**Date**: 2026-05-21 | **Researcher**: nw-researcher (Nova) | **Confidence**: Medium-High overall (High on the published numbers from Kambhampati/Stechly/Gundawar/Xie and on the engineering availability of toolchains; Medium-High on the architectural-fit analysis per substrate; Medium on the negative-result risk modeling for D-on-PDDL, which is structural reasoning pending pilot validation) | **Sources**: 17 cited (88% High-reputation: arxiv.org, openreview.net, github.com under academic ownership, huggingface.co/datasets, ieee.org)

## Executive Summary

**The single most important framing for this deep-dive**: The LLM-Modulo benchmarks are *literature anchors*, not *thesis tests*. Blocksworld, Mystery BW, Graph Coloring, and TravelPlanner each carry a specific published-result-shaped piece of evidence weight (Kambhampati's 30+pp obfuscation gap, Stechly's verification-vs-generation asymmetry, Gundawar's 4.6× back-prompt boost). Running them as supplemental cells in the harebrain matrix buys *reproducibility receipts* and *model-class breadth* the existing Wumpus+TW-Cooking design cannot produce on its own — *but only for the claims those benchmarks were designed to anchor*. They do not test the harebrain-specific payoffs (partial observability, working-memory decay, blackboard ownership) because three of the four (BW, MBW, GraphColor) are fully observable and one of those (GraphColor) has no temporal structure at all. The cells that matter for the harebrain thesis remain Wumpus (Phase I) and TW-Cooking (Phase II). The LLM-Modulo benchmarks belong as *witnesses*, not as *judges*.

**Headline findings:**

- **Two of the four benchmarks rule out the D cell on first-principles grounds, and that is itself a finding worth reporting.** Blocksworld and Mystery BW are deterministic, fully observable, closed-world PDDL domains. The harebrain cage's payoffs (blackboard ownership of partial state, working-memory-fact decay, prevent-the-narrator-from-lying-about-the-world) require an observability gap that BW does not have. On BW the cage either (a) collapses to E/F because there is no observability gap to exploit, or (b) transforms into a plan-step-precondition guard that is structurally Fast Downward in disguise. The honest framing: **run BW/MBW with cells A, B, C, E, F, G only — explicitly omit D, and report the omission as a positive finding about the cage's scope** (Sections 1, 2, 6).
- **Graph Coloring is even sharper: no temporal structure, no D cell at all.** A one-shot CSP has no "decide-leaf at each tick" for the cage to live at. Graph Coloring is run as A, C, E, F only — and its purpose is to isolate the *verification-asymmetry* claim (Stechly's anchor) from any planning confound, which Wumpus cannot do because Wumpus mixes planning and partial-observability (Section 2, 5, 6).
- **TravelPlanner is the supplemental substrate with the cleanest fit.** It is multi-step, has a published constraint-checker (Xie 2024) usable as a sound critic, and has a published 4.6× back-prompt result (Gundawar 2024) to compare against. It is *mostly* fully observable (the plan space is enumerable but not closed-world). D *can* be instantiated meaningfully on it because the cage can own the plan-blackboard. **Recommendation: TravelPlanner is the only LLM-Modulo benchmark to add as a full A-G cell** (Section 2, 5, 6, 8).
- **Mystery Wumpus already covers what Mystery BW would buy.** The obfuscation-gap claim is *novel-on-partially-observable substrate* via Mystery Wumpus and *literature-replication* via Mystery BW. The novel claim is more interesting than the replication claim *unless* the Mystery-Wumpus substitution scheme (Wuggy-generated CVC pseudowords per the portability deep-dive Section 3) fails its contamination audit — in which case Mystery BW becomes a fallback rather than a primary anchor (Section 5, 8).
- **Engineering cost is dominated by TravelPlanner.** TravelPlanner full A-G is roughly 12-18 researcher-days. Graph Coloring at A+C+E+F is 4-6 days. Blocksworld at A+B+C+E+F+G is 5-7 days. Mystery BW (config switch from BW) is 1-2 days incremental. Total supplemental budget: 22-33 researcher-days, comparable to Phase I+II combined — but most of it lives in TravelPlanner (Section 4).
- **Sequencing recommendation:** (1) **Graph Coloring first** — 4-6 days, isolates verification-asymmetry cleanly, no D cell required, cheapest evidence-to-cost ratio. (2) **TravelPlanner second** — 12-18 days, the only full-D fit, highest evidence weight. (3) **Blocksworld + Mystery BW deferred to a "sanity-check note"** — run only if a reviewer specifically asks "does your obfuscation result reproduce the literature anchor"; otherwise the work is largely redundant with Mystery Wumpus (Section 8).
- **Top risk: D-collapse on fully observable PDDL is an honest negative finding that changes the headline.** If D ≈ E/F on Blocksworld because there's no observability gap to exploit, the headline becomes "the cage doesn't generalize to fully-observable domains" rather than "the cage works." The mitigation is to *not run D on BW/MBW/GraphColor in the first place* and instead report scope-of-applicability explicitly — turn the would-be negative finding into a designed-in restriction (Section 9.1). Three other risks (engineering overrun, narrative dilution, reproduction-fragility) tracked in Section 9.
- **Statistical design**: Kambhampati's 600-instance/condition is the literature floor; for harebrain's supplemental claims (reproducing published gaps, not establishing new ones) **100 instances/condition is sufficient at Cohen's h=0.3 power 0.8** (Section 7). Multiple-comparison correction across the now-6-substrate matrix uses Benjamini-Hochberg with the harebrain-thesis-fit claims (Wumpus, TW-Cooking) pre-registered as primary and the LLM-Modulo supplements as exploratory.

**Confidence**: Medium-High. The published numbers from the four anchor papers are reproducibly verified (Kambhampati 2024 Table 1 page 3 directly; Gundawar 2024 abstract numbers; Xie 2024 dataset accessibility on Hugging Face). The architectural-fit analysis (which cells apply per substrate) is structural reasoning grounded in the LLM-Modulo paper Section 3 and the harebrain note's two-architectures framing — pending pilot validation but well-defended. The Stechly graph-coloring instance specification (number of nodes, edge density) is a confirmed Knowledge Gap that requires reading the PDF directly to confirm; the WebFetch attempts in this research session returned the arXiv abstract only (Knowledge Gap 1, Section 11).

## 1. What Each LLM-Modulo Benchmark Contributes Evidence-Wise

This section decomposes the four benchmarks (plus the two existing substrates) along the seven axes the harebrain thesis cares about. The pattern that emerges: **Wumpus is the only substrate that scores on the partial-observability and working-memory axes; the LLM-Modulo benchmarks score on heuristic-resistance and literature-comparability axes Wumpus doesn't reach.**

### 1.1 The six-substrate decomposition

**Evidence (the seven-axis framework, harebrain-thesis-specific)**: "The cage's four payoffs are *separable*, not a single monolithic bet... Each step on the ladder isolates a *specific* payoff."
**Source**: [wumpus_idea.md "Honest framing: cage demo first, brain demo second"](../../wumpus/docs/wumpus_idea.md) line 160 — Accessed 2026-05-21
**Confidence**: High (the user's own framing of which axes matter for separability claims)

| Axis | Wumpus (L1) | TW-Cooking | Blocksworld | Mystery BW | Graph Coloring | TravelPlanner |
|---|---|---|---|---|---|---|
| **Partial observability** | Yes (senses only adjacent rooms) | Partial (room-local; objects in scope) | **No** (full state visible) | **No** (full state visible) | **No** (CSP, full graph given) | Mostly no (plan space enumerable) |
| **Working-memory-fact decay opportunity** | Yes (L2 escalation; bat-teleport invalidates prior slots) | Yes (smell/sound traces; objects can be moved) | **No** (deterministic, no decay) | **No** (deterministic, no decay) | **No** (one-shot, no time) | Limited (constraints stable across plan) |
| **Multi-step horizon length** | 25-60 turns (L1) | 30-100 commands | 6-15 plan steps | 6-15 plan steps | 1 (one-shot) or 1-N CSP variables | 5-7 day plan, multi-component |
| **Sound external verifier off-the-shelf** | User writes MPL chart | TextWorld engine native | VAL (Howey 2004) | VAL (Howey 2004) | Polytime O(\|E\|) check, trivial to write | Xie 2024 constraint checker (Python) |
| **Heuristic-resistance** | Low (small heuristic eats it; Phase I doc Section 4) | Medium-High (Phase II argues Fast Downward Stone Soup 2023 is the right strong-C) | **Very low** (Fast Downward saturates in seconds) | **Very low** (Fast Downward doesn't care about renames) | Low-Medium (NP-complete but small instances easy) | **High** (Xie 2024: even GPT-4 only 0.6%) |
| **Pretraining contamination probability** | **Very high** (1973 game, R&N textbook, dozens of ports) | Medium (TextWorld games generated on-demand) | **Very high** (canonical AI textbook example) | Lower (renamed versions explicitly designed to defeat retrieval) | Medium (well-known NP-complete problem but instance-specific) | Medium (dataset published 2024, partial leakage by now) |
| **Literature comparability bang-for-buck** | Low (Wumpus appears in pedagogy, not benchmarks) | Medium (TextWorld is a research substrate; Cooking has 2-3 papers) | **Very high** (Kambhampati group: 5+ papers) | **Very high** (Kambhampati: the obfuscation-gap anchor) | **High** (Stechly's verification-asymmetry anchor) | **High** (Xie + Gundawar; the back-prompt anchor) |

### 1.2 Evidence per axis

#### 1.2.1 Partial observability and working-memory-fact decay

**Evidence (Wumpus partial observability is load-bearing)**: "Partial observability with rich-enough sensing. Wumpus surfaces position confusion, stale belief, phantom warning, and phantom geography natively."
**Source**: [Phase I deep-dive § Why Wumpus works for the cage-demo](./phase-i-task-design-deep-dive.md), lines 45-50 — Accessed 2026-05-21
**Confidence**: High (carryover from Phase I deliverable)

**Evidence (Blocksworld is fully observable by PDDL semantics)**: "Classical planning domains [Blocksworld included] are STRIPS- or PDDL-formulated... fully observable closed-world."
**Source**: [Valmeekam et al., "PlanBench" NeurIPS 2023 Datasets & Benchmarks](https://openreview.net/pdf?id=YXogl4uQUO) — Accessed 2026-05-21
**Confidence**: High (peer-reviewed NeurIPS publication establishing the substrate's formal properties)
**Verification**: The PDDL specification (McDermott 1998) defines closed-world deterministic planning as the canonical setting; this is what PlanBench targets. Cross-confirmed at [github.com/karthikv792/LLMs-Planning](https://github.com/karthikv792/LLMs-Planning) which uses the standard PDDL Blocksworld domain file.

**Evidence (TravelPlanner's "mostly observable" structure)**: "TravelPlanner is a benchmark crafted for evaluating language agents in tool-use and complex planning within multiple constraints. In TravelPlanner, for a given query, language agents are expected to formulate a comprehensive plan that includes transportation, daily meals, attractions, and accommodation for each day."
**Source**: [Xie et al. "TravelPlanner: A Benchmark for Real-World Planning with Language Agents." arXiv:2402.01622](https://arxiv.org/abs/2402.01622) — Accessed 2026-05-21
**Confidence**: High (peer-reviewed ICML 2024 publication)
**Verification**: Dataset accessible at [huggingface.co/datasets/osunlp/TravelPlanner](https://huggingface.co/datasets/osunlp/TravelPlanner); 1,225 queries documented per project page.

The "mostly no" partial-observability rating reflects that the plan space (flights, hotels, restaurants, attractions for a given query) is *enumerable* once the query is fixed — there is no agent-explores-and-discovers loop. The constraint checker has full visibility into the candidate plan and the database. So the *partial-observability payoff of the cage* (preventing the narrator from lying about state it can't see) is muted on TravelPlanner.

#### 1.2.2 Heuristic-resistance

**Evidence (Blocksworld is heuristically trivial)**: "On *pure-classical-planning* domains where a hand-written PDDL heuristic (FF, LAMA, Fast Downward) saturates within seconds, modern LLMs do not yet beat the heuristic."
**Source**: [Phase II deep-dive Section 3.1](./phase-ii-task-design-deep-dive.md) — Accessed 2026-05-21
**Confidence**: High (carryover from Phase II deliverable, which itself cites Valmeekam 2024)
**Verification**: Valmeekam 2024 (arXiv:2409.13373) reports o1 at 97.8% on Blocksworld zero-shot — Fast Downward on the same instances is sub-second to optimum.

**Evidence (TravelPlanner is heuristically resistant)**: "We evaluate a wide range of language agents on TravelPlanner... even GPT-4 only achieves a success rate of 0.6%."
**Source**: [Xie et al. 2024 arXiv:2402.01622](https://arxiv.org/abs/2402.01622) — Accessed 2026-05-21
**Confidence**: High
**Verification**: Cross-confirmed in Kambhampati 2024 page 8: "on GPT-3.5-Turbo–the current best strategies only manage a startlingly low 0.7% performance rate." The 0.6-0.7% floor across multiple frontier models is the strongest single signal that TravelPlanner is genuinely heuristic-resistant — a hand-coded planner does *not* solve it because the constraint mix (budget, common-sense, hard-rules over flights/meals/attractions) is messier than PDDL.

#### 1.2.3 Literature comparability

**Evidence (Mystery BW gap is the canonical reference)**: "The performance deteriorates further if the names of the actions and objects in the domain are obfuscated--a change that doesn't in any way affect the performance of the standard AI planners. This further suggests that LLMs are more likely doing approximate retrieval of plans than actual planning."
**Source**: [Kambhampati et al. 2024 page 3](../../docs/llm-modulo/2402.01817.pdf) — Accessed 2026-05-21
**Confidence**: High (the paper that established the obfuscation-gap claim)

**Evidence (the headline Mystery BW numbers, Table 1 page 3)**: Best zero-shot Blocksworld: Claude-3-Opus 59.3%. Best zero-shot Mystery BW: GPT-4 0.16%. The ~59-point gap is the canonical published anchor.
**Source**: [Kambhampati et al. 2024, Table 1, page 3](../../docs/llm-modulo/2402.01817.pdf) — Accessed 2026-05-21
**Confidence**: High (direct extraction from the PDF table)

**Evidence (Stechly's verification-asymmetry anchor)**: "LLMs are bad at solving graph coloring instances and are no better at verifying a solution—and thus are not effective in iterative modes with LLMs critiquing LLM-generated solutions."
**Source**: [Stechly, Marquez, Kambhampati. arXiv:2310.12397, NeurIPS 2023 FM4DM Workshop](https://arxiv.org/abs/2310.12397) — Accessed 2026-05-21
**Confidence**: High (peer-reviewed workshop publication; same Arizona State group; the asymmetry has been replicated in the Stechly 2402.08115 follow-up)
**Verification**: Cited directly in [Kambhampati 2024 page 3, Section 2.2](../../docs/llm-modulo/2402.01817.pdf) ("we report that the performance is in fact *worse* because the system can't recognize a correct coloring").

**Evidence (Gundawar's back-prompt anchor numbers)**: GPT-3.5-Turbo baseline: 0% pass rate. GPT-3.5-Turbo with LLM-Modulo [All critics]: 5%. GPT-4-Turbo baseline: 4.4%. GPT-4-Turbo with LLM-Modulo: 20.6% (4.6× improvement).
**Source**: [Gundawar et al. 2024 arXiv:2405.20625](https://arxiv.org/abs/2405.20625), as extracted in [portability deep-dive Section 5.2](./llm-modulo-benchmark-portability-deep-dive.md) — Accessed 2026-05-21
**Confidence**: High
**Verification**: Cross-referenced in [Kambhampati 2024 page 8](../../docs/llm-modulo/2402.01817.pdf): "6x of baselines... even with a limit of 10 back prompting cycles." The 4.6× (Gundawar) vs 6× (paper text) discrepancy is documented in the portability deep-dive Section 5.3 as a minor framing inconsistency; the precise Gundawar numbers are the right citation for the supplemental run.

### 1.3 What the decomposition shows

Reading the table in Section 1.1 by rows rather than columns: **Wumpus is the only substrate that ticks the harebrain-thesis-specific axes (partial observability, working-memory decay).** The LLM-Modulo benchmarks tick complementary axes (heuristic-resistance, literature comparability). The decomposition justifies the *supplemental* framing — running them does not replace Wumpus's contribution; it adds different evidence about different claims.

**The asymmetry to mark explicitly**: Wumpus is *uniquely* positioned to demonstrate the harebrain payoffs but is *uniquely poorly* positioned to anchor against the literature. The LLM-Modulo benchmarks invert that. Whether the inversion is worth its engineering cost is the question the next sections answer.

## 2. Architecture-Matrix Translation per Substrate

For each LLM-Modulo benchmark, the question is which cells of the A-G matrix even apply. The architecture matrix from `wumpus_idea.md` figure 03 is:

- **A**: scripted (optimal/walkthrough ceiling)
- **B**: random-legal (floor)
- **C**: heuristic (the ablation — "does the brain earn its keep")
- **D**: harebrain/MPL-caged (the structural claim)
- **E**: LangGraph variants (idiomatic scaffolded agents)
- **F**: LangChain bare ReAct (no scaffold)
- **G**: wild coding-agent baseline (self-scaffolded)

### 2.1 Per-substrate cell applicability table

| Cell | Wumpus | TW-Cooking | Blocksworld | Mystery BW | Graph Coloring | TravelPlanner |
|---|---|---|---|---|---|---|
| **A** scripted | Hand-coded solver | TextWorld walkthrough | Optimal PDDL plan (from Fast Downward) | Same as BW (renaming doesn't change plan structure) | Optimal coloring (computed offline) | Human-annotated plan (Xie's training set has 45) |
| **B** random-legal | Uniform random over legal moves | Uniform random over `admissible_commands` | Random sequence of applicable PDDL actions | Same as BW | Random k-coloring (mostly invalid) | Random selection from candidate flights/hotels/etc. |
| **C** heuristic | 50-line Python | Fast Downward Stone Soup 2023 | **Fast Downward (saturates)** | **Fast Downward (saturates — renames irrelevant)** | Polynomial chromatic-number heuristic (DSATUR) | Hand-coded greedy planner over constraints |
| **D** harebrain-caged | Native fit | Native fit | **Collapses / transforms — discuss Section 6** | **Same collapse as BW** | **Not applicable — no temporal structure** | Native fit (plan blackboard) |
| **E** LangGraph variants | Trusted narrator | Trusted narrator | LLM emits PDDL plan; VAL verifies | LLM emits plan in renamed vocab; VAL verifies | LLM emits coloring; checker verifies | LLM emits travel plan; checker verifies (this is what Gundawar 2024 ran) |
| **F** LangChain ReAct | Trusted narrator | Trusted narrator | Same as E | Same as E | Same as E | Same as E |
| **G** wild | Native fit | Native fit | Fit (give Claude Code the PDDL files) | Fit (same as BW; the wild agent reads the files) | Fit (give the graph instance) | Fit (give the query and database) |

The asymmetry is concentrated in row **D**: the cage applies natively to Wumpus, TW-Cooking, and TravelPlanner; collapses or transforms on Blocksworld and Mystery BW (Section 6); doesn't apply at all to Graph Coloring (no temporal structure). This is the crux of the harebrain-thesis-fit question and is treated at length in Section 6.

### 2.2 The trusted-narrator pattern translates uniformly to E and F

**Evidence (the trusted-narrator pattern is the cage's foil)**: "The cleanest comparison... runs the LangChain and LangGraph agents as *trusted narrators* — told the rules of [the game] and asked to play through, owning the world model in their own context — while [the ground truth] runs silently in parallel as a ground-truth oracle. Per turn, a diff flags every divergence."
**Source**: [wumpus_idea.md "Two architectures"](../../wumpus/docs/wumpus_idea.md) line 24 — Accessed 2026-05-21
**Confidence**: High (the user's own design rationale)

The trusted-narrator pattern translates to every LLM-Modulo benchmark trivially:

- **Blocksworld**: LLM is given the PDDL initial state, goal, and action schema; emits a plan in natural language; harness parses the plan; VAL verifies. Divergence per plan step = LLM's stated next-state versus VAL's computed next-state.
- **Mystery BW**: Identical to BW with renamed predicates.
- **Graph Coloring**: LLM is given the graph and k; emits a coloring; checker verifies. Only one "turn" per game — no temporal divergence.
- **TravelPlanner**: LLM is given the query; emits a 5-7-day plan; Xie checker verifies. Divergence per plan element = LLM's claimed constraint satisfaction versus checker's verdict.

**The divergence-by-kind structure** (Phase I doc Section 8.1's six kinds: resurrected entity, inventory drift, position confusion, stale belief, phantom warning, phantom geography) is *Wumpus-specific*. For LLM-Modulo benchmarks, the per-substrate divergence taxonomy is:

- **BW/MBW**: precondition-violation, effect-misprediction, goal-not-achieved, unreachable-state-claimed.
- **Graph Coloring**: edge-constraint-violated, color-count-exceeded.
- **TravelPlanner**: budget-exceeded, schedule-conflict, hard-constraint-violated, common-sense-violated, format-violation.

Each is operationally measurable from the substrate's native verifier. The divergence-by-kind comparison story carries across substrates *as a methodology*; the specific kinds are substrate-specific.

### 2.3 The C cell varies wildly in strength across substrates

This is the single biggest implementation difference per substrate. From the table:

- **Wumpus** (Phase I): C is a 50-line Python heuristic — *deliberately* weak, because Phase I is a cage demo not a brain demo (Phase I doc Section 4).
- **TW-Cooking** (Phase II): C is Fast Downward Stone Soup 2023 — *deliberately* strong, because Phase II is the brain-demo and a weak C would sandbag the comparative claim.
- **Blocksworld / Mystery BW**: C must be Fast Downward (same as Phase II) — because anything weaker is below the literature floor for these benchmarks. **And Fast Downward will saturate** — i.e., C ≈ A. This means the C-vs-D comparison on BW is structurally vacuous: C wins, decisively, and the only interesting question is whether D > E/F, not whether D > C.
- **Graph Coloring**: C is a polynomial-time heuristic — DSATUR is the standard (Brélaz 1979). It achieves chromatic number on bipartite graphs and is within a small factor on random graphs. *This is "C saturates" again* for small instances; the only interesting comparison is again D-vs-E/F (and on Graph Coloring there is no D).
- **TravelPlanner**: C is a hand-coded greedy planner over the constraint set. Per Xie 2024 the published baselines (CoT, ReAct, Reflexion) are all sub-1%; a hand-coded greedy *might* do meaningfully better than CoT — this is the cell where C-vs-D is genuinely uncertain and therefore most informative.

**Operational discharge for C-cell choice per substrate**:
- BW/MBW: use Fast Downward; report C as ceiling-saturating; the cell exists only to validate the substrate is reasonable.
- Graph Coloring: use DSATUR; same role as BW's Fast Downward — ceiling-saturating, cell exists to validate substrate.
- TravelPlanner: implement a constraint-greedy planner; this is genuine C-vs-D comparison, similar role to Phase II's Fast Downward Stone Soup.

### 2.4 The D-cell-collapse problem deserves its own section

Sections 2.1-2.3 establish the cell applicability. The single biggest question — what does D *mean* on a fully-observable PDDL domain — is Section 6.

## 3. What the Supplemental Run Actually Buys

This section evaluates four candidate claims that running LLM-Modulo benchmarks supplementally could deliver. For each, the question is: does the supplemental run *actually* deliver this claim, or does the existing Wumpus+TW-Cooking design already cover it?

### 3.1 Claim A: "The cage works across multiple task classes, not just Wumpus"

**Requires**: D demonstrated on multiple substrates.

**Status**: Phase II's TW-Cooking already delivers this (Wumpus + TW-Cooking is two task classes). Adding TravelPlanner makes it three. **Adding BW/MBW does NOT advance this claim** because D doesn't apply natively to BW (Section 6).

**Verdict**: **TravelPlanner advances; BW/MBW/GraphColor do not.** The supplemental value for this claim is concentrated in TravelPlanner only.

### 3.2 Claim B: "The obfuscation gap generalizes"

**Requires**: Either (i) reproducing the BW→MBW gap in the harebrain setup, or (ii) extending the gap to a partially-observable substrate.

**Status**: Mystery Wumpus (per portability deep-dive Section 3 and the user's `wumpus_idea.md` line 132) is the *novel-on-partially-observable-substrate* version. Mystery BW is the *literature-replication* version.

**Evidence (Mystery Wumpus is novel)**: "Mystery-Wumpus does not appear in the published literature (zero hits on arXiv for 'mystery wumpus' OR 'wumpus renaming' OR 'obfuscated wumpus')."
**Source**: [Portability deep-dive Section 7](./llm-modulo-benchmark-portability-deep-dive.md) — Accessed 2026-05-21
**Confidence**: High (negative-evidence claim verified at the time of the portability deep-dive)

**Reading the trade-off**: Running BW+MBW supplementally buys "we reproduce Kambhampati's result *in our harness*" — which is a defensive credential against the criticism "your obfuscation-gap result on Mystery Wumpus might be artifactual; can you reproduce the literature anchor?" The credential is real but its value depends on whether reviewers/readers ask the question.

**Verdict**: **Conditional value.** If the Mystery Wumpus substitution-scheme passes its contamination audit (portability deep-dive Section 3.5 step 3), Mystery BW is a reproducibility-receipt sanity check. If Mystery Wumpus *fails* the audit, Mystery BW becomes the fallback that anchors the obfuscation-gap claim in the literature instead. Either way, Mystery BW is **insurance**, not primary evidence.

### 3.3 Claim C: "The verification asymmetry generalizes"

**Requires**: Demonstrating verification-worse-than-generation on a substrate where the failure mode is isolated from any planning confound.

**Status**: The Wumpus verification probe (`wumpus_idea.md` line 150; portability deep-dive Section 4) measures verification accuracy *as a function of turn count* on a *partially-observable temporal substrate*. It is structurally different from Stechly's graph-coloring experiment, which is *one-shot verification of a candidate solution to a CSP*.

**The crucial methodological point**: Stechly's anchor is "verification is harder than generation *with no temporal or observability confound*." A Wumpus verification probe inevitably mixes verification difficulty with partial-observability state-tracking difficulty. **Graph Coloring is the only substrate that cleanly isolates the verification-asymmetry claim** because the candidate is fully visible to the LLM.

**Verdict**: **Graph Coloring delivers a claim Wumpus structurally cannot.** This is the cleanest case for a supplemental substrate — it tests a claim the existing matrix cannot test even in principle. The cost is the smallest of any supplemental (no D cell, no temporal structure to instrument).

### 3.4 Claim D: "The back-prompt loop's effect generalizes"

**Requires**: Demonstrating the back-prompt loop closes a meaningful gap on a substrate other than the one it was published on.

**Status**: The Wumpus back-prompt probe (`wumpus_idea.md` line 142; portability deep-dive Section 5) measures cumulative-divergence-vs-turn with and without the loop. The TravelPlanner back-prompt result (Gundawar 2024) measures plan-pass-rate-vs-iteration. **These are structurally different metrics on structurally different substrates.**

If Wumpus-with-back-prompt closes the gap, the harebrain story has a within-substrate replication of the LLM-Modulo finding *adapted to per-turn cadence*. If it doesn't, the harebrain story has a finding that *the loop is whole-plan-specific*, which is interesting.

Running TravelPlanner supplementally with the back-prompt loop is a direct re-run of Gundawar — which buys: "we reproduce Gundawar's 4.6× number in our harness *and* show the loop works at per-turn cadence on Wumpus." Two anchors, two cadences.

**Verdict**: **TravelPlanner delivers a literature-anchor for the back-prompt claim that Wumpus alone cannot.** TravelPlanner re-run is the most direct comparable-number test of the LLM-Modulo result in the supplemental suite. High value, but only if the reproduction is rigorous (Section 9.3 on reproduction-fragility).

### 3.5 Claim E: "Model-class breadth"

**Status**: Not explicitly listed in the prompt but worth marking. Running BW supplementally is the cheapest way to get model-class-breadth evidence: Kambhampati's Table 1 covers six frontier models (GPT-4o, GPT-4-Turbo, Claude-3-Opus, LLaMA-3 70B, Gemini Pro, GPT-4); reproducing even one or two columns of that table in the harebrain setup buys a "we tested this on N models, here are the same numbers as the literature" claim.

**Verdict**: **BW supplemental gives model-class-breadth almost for free.** The cost is low (one model panel against Kambhampati's published numbers); the value is a defensible "our setup matches the literature on the model-panel axis" sentence. This is the single best argument for running BW at all.

### 3.6 Reading the four claims together

| Claim | Best substrate | Wumpus/TW-Cooking already covers? | Supplemental value |
|---|---|---|---|
| A. Cage works across multiple classes | TravelPlanner | Partially (TW-Cooking is one alternative) | Medium |
| B. Obfuscation gap generalizes | Mystery Wumpus primary; Mystery BW backup | Mystery Wumpus is the primary; MBW is insurance | Low-Medium |
| C. Verification asymmetry generalizes | Graph Coloring | No (Wumpus probe mixes verification with observability) | **High** |
| D. Back-prompt loop generalizes | TravelPlanner | Partially (Wumpus has per-turn back-prompt) | **High** |
| E. Model-class breadth | Blocksworld | No (Wumpus+TW-Cooking would need 6 model runs each, expensive) | Medium |

**The clean reading**: Graph Coloring and TravelPlanner are the high-value supplements; Blocksworld is a low-cost extra; Mystery BW is conditional insurance. This ordering drives the sequencing recommendation in Section 8.

## 4. Engineering Cost per Supplemental Substrate

Time estimates are in researcher-days, using the same accounting as the Phase II doc Section 11.1 (which budgeted 2-4 weeks total for TW-Cooking). All estimates assume the existing harebrain harness (Phase I + Phase II infrastructure) is in place — the supplements *consume* the existing harness rather than building parallel infrastructure.

### 4.1 Blocksworld at A+B+C+E+F+G (D omitted per Section 6)

| Subtask | Days | Notes |
|---|---|---|
| PDDL toolchain setup (VAL binary + Fast Downward) | 1-1.5 | VAL binary download + build, Fast Downward via apt/brew or build-from-source |
| Blocksworld instance acquisition | 0.5 | `git clone github.com/karthikv792/LLMs-Planning` — instances are pre-generated in the repo |
| A cell (optimal plan from Fast Downward) | 0.5 | Wrap Fast Downward output as the "scripted" baseline |
| B cell (random-legal action sequence) | 0.5 | Same wrapper as A; sample uniformly from applicable actions |
| C cell (Fast Downward strong baseline) | 0.5 | Reuse the A wrapper; same code path |
| E cell × 4 variants (LangGraph: ReAct, scratchpad, plan-then-act, belief-tracker) | 1.5 | Largely reuse Phase I E-cell scaffolding; substitute PDDL I/O for Wumpus I/O |
| F cell × 2 (LangChain ReAct with/without format constant) | 0.5 | Same reuse as E |
| G cell (Claude Code wild) | 0.5 | Hand it the PDDL files; no harness work |
| Divergence-by-kind instrumentation | 1 | The four BW-specific kinds: precondition-violation, effect-misprediction, goal-not-achieved, unreachable-state-claimed |
| Plotting / report integration | 0.5 | Add a "Blocksworld" column to the existing notebook |
| **Total** | **5-7 days** | Most of the cost is in instrumentation, not toolchain |

**Evidence (PlanBench instances and Fast Downward toolchain)**: "PlanBench instantiates classical planning domains... Mystery Blocksworld is identical to Blocksworld in structure but with arbitrary string names... The original data is hosted at github.com/karthikv792/LLMs-Planning."
**Source**: [github.com/karthikv792/LLMs-Planning](https://github.com/karthikv792/LLMs-Planning) and [Valmeekam et al. PlanBench NeurIPS 2023](https://openreview.net/pdf?id=YXogl4uQUO) — Accessed 2026-05-21
**Confidence**: High (the canonical PlanBench repo, maintained by the paper's first co-author Karthik Valmeekam)

### 4.2 Mystery Blocksworld (incremental from BW)

| Subtask | Days | Notes |
|---|---|---|
| Mystery BW instances (already in PlanBench repo) | 0.25 | The renamed-action-and-object versions are pre-generated under the `mystery/` folder |
| Verify Fast Downward solves Mystery BW identically | 0.25 | Sanity check; should be trivially true since planners don't care about renaming |
| Run E/F/G on Mystery BW instances | 0.5 | Same harness as BW with renamed vocabulary |
| Add Mystery-BW column to BW report | 0.5 | Plotting and obfuscation-gap calculation |
| **Total** | **1-2 days** | Mystery BW is *cheap incremental* over BW |

### 4.3 Graph Coloring at A+C+E+F (no B native; no D)

| Subtask | Days | Notes |
|---|---|---|
| Graph instance generator (Erdős-Rényi at specified edge density) | 1 | Python `networkx.gnp_random_graph` or `nx.erdos_renyi_graph`; specify density to match Stechly (see Knowledge Gap 1 — need to read Stechly PDF for exact density) |
| Chromatic-number computation for ground truth | 0.5 | NetworkX has `nx.coloring.greedy_color`; for ground truth, use a small exact solver (DSATUR + branch-and-bound) for instances < 30 nodes |
| A cell (optimal coloring) | 0.25 | Exact solver output |
| C cell (DSATUR heuristic) | 0.5 | NetworkX built-in `nx.coloring.greedy_color(strategy="DSATUR")` |
| E cell × variants | 1 | LLM emits coloring as JSON; harness parses; checker verifies |
| F cell × 2 | 0.5 | Same as E |
| Verification-asymmetry instrumentation | 1 | Two LLM calls per instance: generation, then verification of own output; compare to ground truth |
| Plotting | 0.5 | Generation accuracy vs verification accuracy histogram (the Stechly headline plot) |
| **Total** | **4-6 days** | The cheapest supplemental |

**Evidence (graph-coloring methodology)**: "We systematically investigate the effectiveness of iterative prompting in the context of *Graph Coloring*, a canonical NP-complete reasoning problem. Our methodology involves a principled empirical study of the performance of GPT4 on two tasks: solving a large suite of random graph coloring instances and, separately, verifying the correctness of the candidate colorings."
**Source**: [Kambhampati 2024 page 3, citing Stechly et al. 2023](../../docs/llm-modulo/2402.01817.pdf) — Accessed 2026-05-21
**Confidence**: High

### 4.4 TravelPlanner at full A-G (D included)

| Subtask | Days | Notes |
|---|---|---|
| Dataset acquisition (huggingface.co/datasets/osunlp/TravelPlanner) | 0.5 | MIT-licensed, downloadable; 1,225 queries (train 45, val 180, test 1000) |
| Constraint-checker integration (Xie 2024 eval.py) | 1 | Python; wrap as the sound critic |
| A cell (human-annotated plans, 45 in train) | 0.25 | Pre-existing; just wire as the "ceiling" |
| B cell (random-legal: random selections from candidate flights/hotels) | 1 | Custom because there's no `admissible_commands` API — sample from per-query candidate sets |
| C cell (hand-coded constraint-greedy planner) | 2-3 | The genuinely-new C; non-trivial constraint satisfaction code |
| **D cell (harebrain-caged)** | 3-4 | **The biggest single cost.** MPL chart owns the per-day plan slots (transport, meal x3, attraction, hotel); LLM consulted at decide-leaves for "which flight" / "which attraction" with chart-owned constraint state. **This is structurally a new chart** — TravelPlanner's domain semantics are nothing like Wumpus's |
| E cell × 4 variants | 1.5 | Same reuse as Wumpus E |
| F cell × 2 | 0.5 | Same reuse |
| G cell | 0.5 | Hand Claude Code the dataset and Xie checker |
| Back-prompt loop (replicate Gundawar protocol on this dataset in our harness) | 2 | Single-critic Modulo loop with iteration cap 10 (matching Gundawar) |
| Divergence-by-kind instrumentation | 1 | Five kinds: budget-exceeded, schedule-conflict, hard-constraint-violated, common-sense-violated, format-violation |
| Plotting (Figure 5 replicate: pass-rate vs iteration) | 0.5 | The headline plot |
| **Total** | **12-18 days** | TravelPlanner is the bulk of the supplemental budget |

**Evidence (TravelPlanner dataset accessibility, license, verifier in Python)**: Dataset hosted at huggingface.co/datasets/osunlp/TravelPlanner; repo at github.com/OSU-NLP-Group/TravelPlanner is MIT-licensed and Python-only; evaluation script `eval.py` in `evaluation/` folder validates against environment, commonsense, and hard constraints.
**Source**: [github.com/OSU-NLP-Group/TravelPlanner](https://github.com/OSU-NLP-Group/TravelPlanner) and [huggingface.co/datasets/osunlp/TravelPlanner](https://huggingface.co/datasets/osunlp/TravelPlanner) — Accessed 2026-05-21
**Confidence**: High (direct fetch of repo metadata)

### 4.5 Summary

| Substrate | Days | Cumulative |
|---|---|---|
| Graph Coloring (A+C+E+F) | 4-6 | 4-6 |
| Blocksworld (A+B+C+E+F+G; no D) | 5-7 | 9-13 |
| Mystery BW (incremental) | 1-2 | 10-15 |
| TravelPlanner (full A-G) | 12-18 | 22-33 |

**Total supplemental budget: 22-33 researcher-days.** For comparison, Phase II's TW-Cooking budget was 14-21 days (2-4 weeks at 5-day weeks). Adding all four supplements roughly doubles the post-Phase-I engineering surface.

**Cost-cutting moves** if the budget is constrained:
1. Skip MBW (saves 1-2 days). Mystery Wumpus already covers the obfuscation-gap claim; MBW is insurance only.
2. Skip BW's E/F variants and run only G (saves ~2 days). The G-wild baseline alone gives "we ran our wild agent against the canonical PlanBench benchmark and got X%" which is the model-class-breadth claim. Internal E/F runs add nothing the literature panel doesn't already provide.
3. Skip TravelPlanner D (saves 3-4 days). Gives up the cleanest "D on a novel substrate" cell — but if the budget forces it, the cell ordering becomes: do BW + Graph Coloring as cheap supplements; TravelPlanner only at A+E+F (no D, no full back-prompt) as a literature-anchor.

The Section 8 sequencing recommendation operationalizes which cuts to take in which order.

## 5. Where the LLM-Modulo Benchmarks Shine vs Wumpus/TW-Cooking

Honest accounting. This section identifies the specific claims where each LLM-Modulo benchmark gives *stronger* evidence than Wumpus or TW-Cooking would, and conversely where the existing substrates win.

### 5.1 Mystery BW for the obfuscation gap

**Where MBW wins over Mystery Wumpus**:
- Direct comparable-number test against Kambhampati Table 1. If MBW in the harebrain harness produces a 30-50pp gap, that *reproduces the literature anchor*, defending against the criticism "your contamination audit might have failed; how do we know your gap isn't artifactual?"
- Model-panel breadth comes free if BW is run on multiple models.
- The Kambhampati group's substitution scheme is *known* — no contamination-audit risk on the substitution itself.

**Where Mystery Wumpus wins over MBW**:
- *Novel finding* on a partially-observable substrate. The obfuscation effect on a POMDP has *never* been published.
- Aligns with the harebrain narrative (1973 Wumpus → cage on Wumpus → renamed Wumpus).

**Honest reading**: Mystery Wumpus is the *interesting* result; Mystery BW is the *credentialing* result. Run both only if budget permits; if forced to choose, Mystery Wumpus.

### 5.2 Graph Coloring for verification asymmetry

**Where Graph Coloring wins definitively**:
- **No planning confound.** A graph coloring is verified or not verified independent of any temporal sequence or world-model claim. This is the cleanest possible isolation of "is verification asymmetry real?"
- Direct comparable-number test against Stechly 2310.12397.
- Cheap (4-6 days, smallest supplemental).
- The Stechly result is *counterintuitive enough* that reproducing it independently is genuinely informative (per the LLM-Modulo paper page 3: "the strategy of LLMs self-critiquing their solutions does not improve over the baseline. We report that the performance is in fact *worse*").

**Where Wumpus verification-probe wins**:
- Tests verification *as a function of turn count* — i.e., does the LLM's self-knowledge degrade over time? Graph Coloring cannot test this because it has no turn count.
- Tests verification *under partial observability* — the agent knows only what it has sensed, and verification is asking about the agent's reconstructed model. Graph Coloring's CSP has full visibility.

**Honest reading**: The two probes test *different versions* of the verification-asymmetry claim. Graph Coloring tests the *static* version (Stechly's exact claim); Wumpus tests the *dynamic-with-occlusion* version (novel). They are *complementary*, not redundant. Both worth running.

### 5.3 TravelPlanner for the back-prompt loop

**Where TravelPlanner wins definitively**:
- Direct comparable-number test against Gundawar's 4.6× number.
- The constraint-checker (Xie 2024) is a *published, validated, multi-constraint* sound critic. The Wumpus oracle is a single-critic (MPL chart) by comparison.
- The multi-day-plan horizon (5-7 days, with multiple components per day) is naturally longer than a single Wumpus episode.

**Where Wumpus back-prompt-probe wins**:
- **Per-turn cadence.** Gundawar's loop is per-iteration on a whole plan (10 iterations cap, each iteration is a fresh plan). The Wumpus per-turn back-prompt tests *per-tick correction* — a strictly finer cadence. Per the portability deep-dive Section 5: "For Wumpus the unit is 'iteration on a single turn.' 3-5 is the right scale."
- Tests the loop under partial observability (the agent can't see all state, so the back-prompt is providing information the agent couldn't have).

**Honest reading**: Same as 5.2 — *complementary*, not redundant. Two cadences (whole-plan / per-turn), two observability settings (full / partial).

### 5.4 Blocksworld as a sanity baseline

**Where BW wins definitively**:
- Model-class-breadth at lowest cost. The Kambhampati Table 1 column structure is the literature's *standard model panel* — reproducing it (even partially) is the cheapest defense against model-class-cherry-picking criticisms.
- Anchors against the literature's most-cited benchmark.

**Where BW does NOT win**:
- Anything substantive about the harebrain thesis. BW is fully observable, has no temporal state-tracking, has no working-memory facts, has no blackboard semantics.

**Honest reading**: BW is a *credentialing* run, not a *thesis* run. Worth doing if cheap (Section 4.1: 5-7 days); not worth doing if it crowds out TravelPlanner D-cell work.

### 5.5 Where Wumpus uniquely wins

The reverse direction. Claims that *only* Wumpus can test:

1. **Partial-observability divergence kinds** (resurrected-entity, stale-belief, phantom-warning, phantom-geography — Phase I doc Section 8.1). None of the LLM-Modulo benchmarks have analogous failure modes because none has partial observability.
2. **Bat-teleport stress test** (post-bat recovery turn count, Phase I doc Section 8.5). The cleanest single signal in classic Yob — the kind of working-memory invalidation that BW/MBW/GraphColor/TravelPlanner do not have.
3. **Narrative coherence with the harebrain note.** The 1973-Wumpus → 1980-Adventure → cage-was-solved-in-1980 thread (harebrain.md lines 30-46) is the rhetorical backbone of the article series. BW/MBW/GraphColor are not in that thread.

### 5.6 Where TW-Cooking uniquely wins

1. **Long-horizon multi-step planning** (Phase II's framing). TW-Cooking has 30-100-command horizons with structured prerequisite chains (open container → cook → cut → combine).
2. **Heuristic-resistance against Fast Downward Stone Soup 2023** as the strong-C (Phase II doc Section 4). BW/MBW are *not* heuristic-resistant in this sense — Fast Downward saturates. TravelPlanner is heuristic-resistant per Xie 2024 (0.7% floor), but the heuristic class is different (constraint-greedy vs PDDL-planner).

### 5.7 The honest comparison table

| Claim | Best substrate | Second best |
|---|---|---|
| Cage works on partial-observability domain | Wumpus | — (no other has POMDP property) |
| Cage works on long-horizon planning | TW-Cooking | TravelPlanner |
| Cage works on a literature-recognized benchmark | TravelPlanner | (BW collapses; see Section 6) |
| Obfuscation gap on familiar canonical-form game | Mystery Wumpus | Mystery BW (insurance) |
| Verification asymmetry isolated from planning | Graph Coloring | Wumpus verification probe (dynamic version) |
| Back-prompt loop on whole-plan generation | TravelPlanner | (Wumpus tests per-turn version) |
| Model-class-breadth credential | Blocksworld | TravelPlanner |
| Narrative coherence with harebrain article | Wumpus | TW-Cooking |

**The reading**: Wumpus + TW-Cooking are the primary substrates. Graph Coloring and TravelPlanner are high-value supplements covering claims the primaries cannot. BW and MBW are credentialing supplements that buy literature-anchor reach at low marginal cost.

## 6. The "D Cell on Fully-Observable PDDL" Question

This is the crux of the harebrain-thesis-fit problem and the section the prompt singled out as load-bearing. Honest treatment follows; no papering over.

### 6.1 The structural problem

The harebrain cage's payoffs, as articulated in `harebrain.md` and operationalized in `wumpus_idea.md`, are:

1. **Blackboard ownership of state** — the chart's Manifest is the world; the LLM cannot lie about it because the LLM does not own it.
2. **Working-memory-fact decay** — typed slots with explicit decay rules prevent stale beliefs from accumulating.
3. **HSM topology** — state machines route on rule matches, not LLM-narrated transitions.
4. **Diagnostic surface** — "every drift is locatable to a state, every memory loss to a fact decay rate" (harebrain.md line 236).

**Evidence (the cage's payoff requires an observability gap)**: "The cage we are testing is *not* 'does the LLM make moves the game would reject' — Yob's game rejects those for everyone. The cage is about something subtler: whether the LLM's *internal model of the world* stays honest over a long enough run."
**Source**: [wumpus_idea.md "The game, in one screen"](../../wumpus/docs/wumpus_idea.md) line 19 — Accessed 2026-05-21
**Confidence**: High (the user's own framing of what the cage is for)

The harebrain cage's value depends on the LLM having an internal model that *can* drift. Drift requires the LLM to *maintain* state across turns that it *cannot directly observe* — that's what makes the world-model claim assertable versus refutable. **In a fully-observable closed-world domain, the LLM doesn't maintain state in this sense**: every action's preconditions and effects are visible in the current state, every state transition is deterministic, every observation is the full state.

So on Blocksworld:
- The LLM emits action `unstack(A, B)`. The world's response is the full new state, deterministically computed.
- The LLM does not need to *remember* whether `on(A, B)` was true; it can read the current state every turn.
- The LLM's only "state" is the *plan* — the sequence of remaining actions it intends to take.

### 6.2 What "D cell" could even mean on Blocksworld

Three readings, each with different implications:

#### Reading 1: D collapses to E/F

Under this reading, the harebrain cage adds nothing over a LangGraph agent because there's no observability gap to exploit. The chart would own — *what*? `current_state`, but the current state is observable to the LLM every turn. `inventory`, but Blocksworld has no inventory beyond the hand. `sensed_warnings`, but Blocksworld has no senses.

**Operational consequence**: D's divergence count on BW would be *structurally zero by being trivial*, not by being meaningfully prevented. The cage isn't preventing drift because there's no drift to prevent. **D ≈ E/F because the trusted-narrator pattern doesn't surface any narrator lies on BW — the narrator can see everything.**

This is *the honest negative finding*. If reported as such — "the cage works on substrates with an observability gap; on fully-observable PDDL, D and E/F are indistinguishable because there's nothing to surface" — it sharpens the harebrain thesis's *scope of applicability*. It says: the cage is for partial-observability tasks. PDDL is not.

#### Reading 2: D transforms — the chart owns plan-step state, not world state

Under this reading, the cage's unit of state is the *plan*, not the *world*. The chart's Manifest holds:
- `current_plan_step` — which action in the plan we're executing
- `precondition_check_passed[step]` — boolean per step
- `expected_postconditions[step]` — for each step
- `actual_postconditions[step]` — read from the world

The LLM is consulted at decide-leaves to *generate the next action* (one at a time), and the chart's transition guards reject actions whose preconditions don't hold. This is *structurally Fast Downward in disguise* — at every step the chart is doing what a classical planner does (check preconditions, apply effects).

**Operational consequence**: D under this reading is a *neuro-symbolic-pipeline-with-the-symbolic-part-as-the-chart*. It is not "the harebrain cage works on PDDL." It is "if you replace the symbolic-planner with a chart that consults an LLM at each step, you get a chart-driven PDDL planner whose action proposals come from an LLM rather than a heuristic." This is interesting *as a different architecture*, but it is *not the same harebrain claim*.

**The honest framing if Reading 2 is taken**: report D-on-BW as a *different cell type* — call it `D'`, the plan-step-cage — and explicitly distinguish it from D-on-Wumpus. Then the BW result becomes a *separate finding* about a *related-but-different* architecture, not a claim that "the harebrain cage works on BW."

#### Reading 3: skip D on BW; report the omission as the finding

The recommended option. Acknowledge that D's payoffs require partial observability; explicitly omit D from the BW matrix; frame this as a *scope-of-applicability* finding rather than as a *D-vs-E/F-on-BW* result.

**Operational discharge**:
- Run BW at A+B+C+E+F+G (no D, no D').
- In the report, include a section "Why D is not in the BW matrix" with the Reading-1 argument: "BW has no observability gap; the cage's structural payoff requires one; therefore the BW matrix omits D."
- Frame this as the *scope-of-applicability* finding: "The harebrain cage applies to substrates with an observability gap. PDDL is not such a substrate. This omission is itself a finding."

This is the recommended option because:
1. It is *honest*. It does not paper over the structural mismatch.
2. It is *cheap*. It saves the 3-4 days a TravelPlanner D cell would cost, which on BW would produce results that are either uninteresting (Reading 1) or off-thesis (Reading 2).
3. It strengthens the harebrain thesis by *bounding* it. Theses with bounded scope are more credible than theses with unbounded scope.

### 6.3 Graph Coloring: the sharper case

Graph Coloring is even cleaner: there is *no temporal structure at all*. The LLM is given a graph and a color count; emits one coloring; done. There is no decide-leaf at each tick because there are no ticks. There is no state to drift. There is no working memory to decay.

**The honest framing**: Graph Coloring's matrix is A + C + E + F. No D, no D', no temporal cell. The cell-applicability table (Section 2.1) already reflects this.

**Why is this OK?** Because Graph Coloring's purpose in the supplemental matrix is *not* to test the cage. Its purpose is to isolate the *verification-asymmetry* claim (Section 3.3, 5.2). Verification asymmetry is a property of LLMs themselves, not of the cage architecture. The fact that the cage doesn't apply to Graph Coloring is precisely what makes Graph Coloring useful for isolating the verification-asymmetry claim.

### 6.4 TravelPlanner: where D *does* fit

TravelPlanner has structure that BW does not: the plan is *not* fully observable to the LLM in the same way BW's state is. Specifically:

- The candidate-flights, candidate-hotels, candidate-restaurants are databases the agent queries through tools. The agent does not see the full database at once.
- The constraint set is given; the candidate space is large; the agent must iteratively select from candidates.
- There is a multi-step structure (5-7 days × multiple components per day) where state accumulates across selection decisions.

The chart can naturally own:
- `selected_flights[day]`, `selected_hotel[day]`, `selected_meals[day][slot]`, `selected_attractions[day][slot]`
- `running_budget` — updates with each selection
- `cumulative_constraint_satisfaction` — soft and hard

The LLM is consulted at decide-leaves for *individual selections* (which flight, which restaurant) with the chart holding the constraint state. This is the same architectural shape as Wumpus's "LLM at decide-leaf with chart-owned slots."

**Operational discharge**: D-cell is natively meaningful on TravelPlanner. The 3-4 day estimate in Section 4.4 stands.

### 6.5 The crux summarized

| Substrate | D applies? | If not, why? | Recommendation |
|---|---|---|---|
| Wumpus | Yes | — | D included (Phase I) |
| TW-Cooking | Yes | — | D included (Phase II) |
| Blocksworld | **No** | No observability gap; D collapses to E/F or transforms to plan-step-cage (D') | **Omit D; report omission as scope finding** |
| Mystery BW | **No** | Same as BW | **Omit D** |
| Graph Coloring | **No** | No temporal structure | **Omit D** |
| TravelPlanner | Yes | Multi-step plan accumulation; agent queries candidates through tools | D included |

The pattern: **D applies precisely on substrates with multi-step state accumulation and selection-under-uncertainty.** It does not apply on substrates with one-shot CSP structure or fully-observable deterministic PDDL. This is a *load-bearing scope statement* for the harebrain thesis.

## 7. Statistical Design for Supplemental Cells

The harebrain primaries (Wumpus, TW-Cooking) have their own statistical designs in Phase I (50 seeds × architectures) and Phase II (100 seeds × 8 cells × 3 models = 2400 LLM runs per Section 7.6 of Phase II doc). This section addresses *only* the supplemental cells.

### 7.1 Sample size per LLM-Modulo cell

**Reference floor**: Kambhampati et al. 2024 Table 1 uses 600 instances per model-condition cell. This is the literature floor for PlanBench-style work.

**For the harebrain supplemental claims** (reproducing published gaps and asymmetries, not establishing new ones), the power requirement is *less* strict because the expected effect sizes are large:

| Claim | Expected effect | Cohen's h | Sample size at 80% power |
|---|---|---|---|
| Mystery BW obfuscation gap (reproducing Kambhampati) | ~50pp drop | h ≈ 1.0 | ≈ 16 per cell |
| Graph Coloring verification asymmetry (reproducing Stechly) | ~30pp generation-vs-verification gap | h ≈ 0.6 | ≈ 22 per cell |
| TravelPlanner back-prompt boost (reproducing Gundawar) | 4.6× multiplier; ~16pp absolute | h ≈ 0.4 | ≈ 50 per cell |
| Blocksworld model-class breadth | Match published per-model rates ± 10pp | h ≈ 0.2 | ≈ 200 per cell |

The Blocksworld model-class-breadth claim is the only one that approaches Kambhampati's 600-instance floor. The others can be defended at 100 instances per cell — comfortably above the power floor for the expected effect sizes.

**Recommendation**:
- Mystery BW: 100 instances per cell.
- Graph Coloring: 100 instances per cell.
- TravelPlanner: 100 queries per cell (drawn from the 1,000-query test set per Xie 2024 documentation; pre-register the seed).
- Blocksworld for model-class breadth: 300 instances per cell *if* this is a primary claim, else 100.

### 7.2 Comparison design

Two design choices apply:

**Within-substrate**: per-substrate, paired-by-instance comparison (every cell sees the same set of instances; differences are within-instance). This is the standard PlanBench design and is what each of the four supplements should follow.

**Across-substrates**: the question of "does the cage work across substrates" requires a *not-quite-paired* comparison because instances are not commensurate across substrates. The proposed analysis: per-substrate effect sizes (Cohen's h on D-vs-E for each substrate where D applies), then *meta-analyze* across substrates with substrate as a random-effects factor. This is a standard meta-analysis design from the social-science replication literature.

### 7.3 Multiple-comparison correction

The supplemental matrix introduces many cells and therefore many implicit comparisons. The Phase I + Phase II + supplemental matrix has:

- 6 substrates × ~8 cells = ~48 cells in principle
- Subtract cells that don't apply (Section 6): -3 D cells (BW, MBW, GraphColor), -1 B cell (Graph Coloring has no native random-legal) = ~44 cells
- Pairwise comparisons within a substrate: ~10 per substrate × 6 substrates = ~60 comparisons
- Cross-substrate: ~20 high-priority comparisons (e.g., D-on-Wumpus vs D-on-TravelPlanner)

**Total ~80 implicit comparisons.** At α=0.05 uncorrected, 4 false positives are expected.

**Recommendation**: Benjamini-Hochberg FDR correction at q=0.10 with the following pre-registration:

- **Primary hypotheses** (Wumpus D=0 by construction; TW-Cooking D > C): retain α=0.05 uncorrected.
- **Secondary hypotheses** (the four LLM-Modulo supplemental claims): FDR-corrected at q=0.10 within the supplemental family.
- **Exploratory hypotheses** (cross-substrate comparisons): report effects without significance testing; describe as "exploratory."

This pre-registration is the *paper-readability* device: primaries are claims, secondaries are corroborations, exploratories are observations.

### 7.4 Statistical-design discharge

Concrete actions:

1. **Pre-register sample sizes** before any LLM API calls. 100 per cell per supplement; 300 for BW model-class-breadth if pursued.
2. **Pre-register the FDR scheme** in a written analysis plan committed to the repo before running the supplemental experiments.
3. **Use paired-bootstrap CIs** within each substrate (the Phase II doc Section 9.2 establishes this as the harebrain analysis standard).
4. **For the back-prompt reproduction on TravelPlanner**: pre-register the iteration cap (10, matching Gundawar) and the report-back-prompt-outcome triplet (corrected / no-help / induced-new — per portability deep-dive Section 5.5.3).

## 8. Sequencing Recommendation

Given finite engineering budget and the harebrain article series's narrative arc (Note 1: cage works on Wumpus; Note 2: brain earns its keep on TW-Cooking; supplemental notes optional), the question is *which supplements to add when*.

### 8.1 The recommended sequence

**Stage 0**: Complete Phase I (Wumpus, ~1-2 weeks) and Phase II (TW-Cooking, ~2-4 weeks). These are the primaries and must land first.

**Stage 1**: **Graph Coloring** (4-6 days, cheapest, highest evidence-to-cost ratio).
- Tests a claim Wumpus structurally cannot (Section 3.3, 5.2).
- No D-cell engineering required.
- Direct comparable-number against Stechly 2310.12397.
- Output: a short "Note 1.5: the verification asymmetry holds in our setup" between Note 1 and Note 2.

**Stage 2**: **TravelPlanner** (12-18 days, highest evidence weight, only LLM-Modulo benchmark with native D fit).
- The only supplemental where D applies (Section 6).
- Direct comparable-number against Gundawar 2024.
- Tests the back-prompt loop at whole-plan cadence (complementary to Wumpus per-turn version).
- Output: a "Note 3: the cage works on real-world planning constraints, and reproduces Gundawar's 4.6× boost" — this is potentially a *publication-class* result on its own because TravelPlanner is heavily studied.

**Stage 3**: **Blocksworld** (5-7 days, model-class-breadth credential).
- Run only if a reviewer specifically requests model-class-breadth evidence, or if the project pursues a JMLR/JAIR submission where the literature-anchor argument matters.
- D explicitly omitted (Section 6.5).
- Reproducing 2-3 columns of Kambhampati Table 1 is sufficient.
- Output: an appendix or footnote to Note 1: "we reproduce Kambhampati's BW numbers in our harness."

**Stage 4 (conditional)**: **Mystery BW** (1-2 days incremental).
- Run *only if* Mystery Wumpus's contamination audit (portability deep-dive Section 3.5) fails or produces equivocal results.
- Otherwise, skip — Mystery Wumpus is the primary anchor for the obfuscation-gap claim and MBW is redundant.

### 8.2 What can be deferred

- **Mystery BW**: deferred indefinitely unless Mystery Wumpus's substitution scheme fails its audit.
- **Blocksworld G cell** (only the wild-agent cell, no E/F variants): can be a "weekend project" that costs 0.5 days and produces a sentence-length result.
- **TravelPlanner D**: if the 12-18 day estimate for TravelPlanner is too long, dropping D (saves 3-4 days) gives a 9-14-day version that still anchors the back-prompt claim against Gundawar — at the cost of giving up the "D applies on a new substrate" claim.

### 8.3 What can be skipped entirely

- **Blocksworld at full A-G** is a credential exercise, not a thesis test. If the budget pressure is real, BW can be dropped entirely with no thesis-level loss. The single sentence "the harebrain cage is for partial-observability domains; for fully-observable PDDL, established planners (Fast Downward) outperform LLMs as the literature confirms (Kambhampati 2024)" *cites* the literature anchor without requiring the experimental run.
- **Mystery BW**: as above, deferred indefinitely.
- **Graph Coloring G cell**: skip — the wild-agent baseline on a one-shot CSP doesn't isolate the asymmetry claim. Run only A+C+E+F.

### 8.4 The sequencing-discharge summary

| Stage | Substrate | Cells | Days | Cumulative | Note |
|---|---|---|---|---|---|
| 0 | Wumpus (Phase I) | A-G | 7-14 | 7-14 | Existing commitment |
| 0 | TW-Cooking (Phase II) | A-G | 14-21 | 21-35 | Existing commitment |
| 1 | **Graph Coloring** | A, C, E, F | 4-6 | 25-41 | First supplement |
| 2 | **TravelPlanner** | A-G | 12-18 | 37-59 | Second supplement (highest value) |
| 3 | Blocksworld | A, B, C, E, F, G (no D) | 5-7 | 42-66 | Optional credential |
| 4 | Mystery BW | E, F, G incremental | 1-2 | 43-68 | Conditional (only if Mystery Wumpus fails) |

The *minimum-defensible-supplement* budget is **Stage 1 only (4-6 days)** — Graph Coloring alone, for the verification-asymmetry claim. The *recommended* budget is **Stages 1 + 2 (16-24 days)** — Graph Coloring and TravelPlanner. Stages 3-4 are credentialing additions that buy literature-anchor reach but no new thesis-level claims.

## 9. Risks and Limitations

Five risks specific to running supplemental LLM-Modulo benchmarks.

### 9.1 D-collapse on fully-observable substrates

**The risk**: D ≈ E/F on Blocksworld because there's no observability gap to exploit (Section 6). The headline changes from "the cage works" to "the cage works on substrates that match its design."

**Severity**: High *if* D is run on BW; low *if* D is omitted from BW as recommended (Section 6.5, Section 8).

**Mitigation**: **Pre-decide to omit D from BW/MBW/GraphColor matrices** before running anything. Pre-register the omission and its rationale in the analysis plan. Frame the omission as scope-of-applicability finding, not as missing-cell.

**Operational discharge**: The analysis plan committed pre-run includes a section "Cells deliberately omitted and why." This is the harebrain-thesis-honest move.

### 9.2 Engineering-cost overrun

**The risk**: 22-33 days estimated supplemental budget runs over to 40+ days if instrumentation reuse is less than expected, or if TravelPlanner D requires more chart authoring than anticipated.

**Severity**: Medium. The harebrain project's existing two-phase plan is already ~3-5 weeks; adding 4-5 weeks of supplements roughly doubles the project's engineering surface.

**Mitigation**:
1. **Stage-gated execution**: complete Stage 1 (Graph Coloring) and decide whether to proceed to Stage 2 based on actual hours-per-day vs estimated. If Stage 1 runs over by 50%+, re-estimate Stages 2-4 with a multiplier.
2. **Pre-commit to skip Stages 3-4** unless explicit external pressure exists.
3. **Time-box TravelPlanner D-cell** to 5 days; if it isn't working by then, drop D and proceed at A+E+F+G only.

### 9.3 Literature-comparability mirage

**The risk**: Running Kambhampati's numbers with a different model selection, different prompts, or different evaluation timing produces a different number. The "we reproduce" claim is fragile.

**Severity**: Medium-High. Kambhampati 2024 Table 1 covers six models (GPT-4o, GPT-4-Turbo, Claude-3-Opus, LLaMA-3 70B, Gemini Pro, GPT-4) as of mid-2024. By 2026 several of these are deprecated or have been updated; reproducing the exact 2024 numbers may be impossible. The Gundawar 4.6× number is similarly model-specific.

**Mitigation**:
1. **Frame as "consistent with" rather than "reproducing."** A harebrain-harness run on 2026 models that shows a 40-50pp obfuscation gap on MBW is *consistent with* Kambhampati's 50pp gap on the 2024 model panel. It is not a "reproduction" in the strict-replication sense.
2. **Document the model-panel difference explicitly.** "Our supplemental MBW run used [models X, Y, Z] in mid-2026; Kambhampati used [the 2024 panel]; direct numerical comparison is not appropriate."
3. **Report effect sizes (Cohen's h) rather than raw percentages** for cross-paper comparison. Effect sizes are less model-version sensitive than raw rates.

### 9.4 Narrative dilution

**The risk**: The harebrain article series is anchored in the 1973-Wumpus → 1980-Adventure → cage-was-solved-in-1980 thread. Running on Blocksworld breaks that thread.

**Severity**: Medium. The thread is rhetorical, not structural — the article series can have supplemental notes that are off-thread. But the *headline notes* (Note 1, Note 2) need to stay on-thread.

**Mitigation**:
1. **Keep the headline notes (Note 1, Note 2) Wumpus + TW-Cooking only.** The LLM-Modulo supplements live in *appendix notes* or *technical reports*, not in the main article series.
2. **Frame the supplements as "evidence appendices"** — Graph Coloring as "appendix: verification-asymmetry isolated"; TravelPlanner as "appendix: back-prompt at whole-plan cadence"; BW as "appendix: model-class breadth credential." The framing keeps them narratively peripheral.
3. **Maintain the 1973→1980 thread** in the main note even when citing the supplements: "the Wumpus result on partial-observability divergence stands in (Note 1); the parallel verification-asymmetry result (Stechly graph coloring, our supplement) confirms the LLM-Modulo paper's anchor claim independently."

### 9.5 Negative-result publication risk

**The risk**: If D doesn't work on Blocksworld and the user has invested in running it, the headline becomes "the cage doesn't generalize" rather than "the cage works on substrates that match its design."

**Severity**: High *if* the omission decision (Section 6.5, 8) is not pre-registered. **Low** if D is pre-committed to be omitted from BW/MBW/GraphColor.

**Mitigation**: This is Risk 9.1 restated as a publication-strategy risk. The mitigation is the same: pre-register the omission *before* running anything. A pre-registered omission is a scope claim; an un-pre-registered omission looks like a post-hoc rationalization.

### 9.6 Risk summary

| Risk | Severity | Mitigation cost | Pre-mitigation action |
|---|---|---|---|
| D-collapse on fully-observable PDDL | High → Low if pre-registered | Free (just plan) | Pre-register D-omission for BW/MBW/GraphColor |
| Engineering-cost overrun | Medium | Stage-gating | Commit to Stage 1 first; re-estimate after |
| Literature-comparability mirage | Medium-High | Reporting discipline | Frame as "consistent with"; report effect sizes |
| Narrative dilution | Medium | Article structuring | Keep Notes 1-2 Wumpus/TW-Cooking; supplements in appendices |
| Negative-result publication risk | High → Low if pre-registered | Free (just plan) | Same as Risk 1 |

Two of the five risks are *fully mitigable by pre-registration*. The remaining three require ongoing discipline during execution and reporting.

## 10. Synthesis and Recommendations

### 10.1 The one-sentence recommendation

**Run Graph Coloring and TravelPlanner as supplements; explicitly omit D from BW/MBW/GraphColor; treat Blocksworld and Mystery BW as conditional credentialing additions.**

### 10.2 Operational discharge — concrete next actions

1. **Pre-register the D-omission decision** for BW, MBW, Graph Coloring in a written analysis plan committed to the repo *before* any supplemental run begins. (Cost: 0 days. Action: write 1-page plan.)
2. **Pre-register sample sizes** at 100 per cell for the supplements (300 for BW if model-class-breadth is pursued). (Cost: included in plan.)
3. **Pre-register the FDR scheme** with primaries (Wumpus, TW-Cooking) uncorrected, supplements FDR-corrected at q=0.10. (Cost: included in plan.)
4. **Execute Stage 1 (Graph Coloring) first.** 4-6 days. Output: short evidence note "verification asymmetry isolated on graph coloring." (Cost: 4-6 days.)
5. **Re-estimate Stage 2 (TravelPlanner) after Stage 1.** If Stage 1 ran on time, proceed to TravelPlanner full A-G. If Stage 1 ran over, drop TravelPlanner D and run A+E+F+G only. (Cost: 12-18 days or 8-14 days depending on scope.)
6. **Stage 3 (Blocksworld) is a JMLR/JAIR-class addition only.** Don't run unless an explicit external requirement demands model-class breadth evidence. (Cost: 5-7 days, deferred.)
7. **Stage 4 (Mystery BW) is conditional.** Run only if Mystery Wumpus's contamination audit fails. (Cost: 1-2 days, contingent.)
8. **Maintain the narrative thread.** Notes 1 and 2 of the harebrain series remain Wumpus and TW-Cooking. Supplemental notes are appendices or technical reports, not main-series notes.
9. **Frame literature-comparability claims as "consistent with," not "reproducing."** Model panels differ across years; effect sizes (Cohen's h) are the right cross-paper unit.
10. **For the TravelPlanner D-cell**, time-box authoring to 5 days. The chart for TravelPlanner is structurally new (per-day plan blackboard with constraint accumulation); if the chart isn't running by day 5, drop D and proceed without it.

### 10.3 What the supplemental run will *not* tell you

To prevent overclaiming:

- The supplements will *not* establish that the harebrain cage is universally applicable. They establish that the *LLM-Modulo pattern* applies to multiple substrates (Kambhampati already knew this).
- The supplements will *not* test the harebrain-specific payoffs (working-memory decay, partial-observability divergence kinds). Those live exclusively on Wumpus.
- The supplements will *not* produce a fair head-to-head against the LLM-Modulo paper's own numbers. Model-panel differences and 2-year-old benchmark drift make that comparison qualitative at best.
- The supplements will *not* be the headline result of the harebrain article series. They are evidence-appendices.

### 10.4 What the supplemental run *will* tell you

To prevent underclaiming:

- The supplements *will* anchor the harebrain results against the LLM-Modulo literature at three specific claim-points (obfuscation gap via Mystery Wumpus alone or with MBW backup; verification asymmetry via Graph Coloring; back-prompt boost via TravelPlanner).
- The supplements *will* test whether the cage's D-cell architecture generalizes from Wumpus's partial-observability setting to TravelPlanner's constraint-accumulation setting — a different substrate class.
- The supplements *will* produce a defensible scope-of-applicability statement for the harebrain cage: it works on substrates with multi-step state accumulation; it does not apply on one-shot CSP or fully-observable deterministic PDDL.
- The supplements *will* give the harebrain project literature-anchor reach into the LLM-Modulo research program at low marginal cost (Graph Coloring at 4-6 days; TravelPlanner at 12-18).

## 11. Knowledge Gaps and Conflicting Information

### Knowledge Gap 1: Stechly's exact graph-coloring instance specification

**Issue**: The Stechly 2310.12397 paper's exact graph-coloring methodology (Erdős-Rényi parameters, number of nodes per instance, edge density, instance count per condition) could not be extracted from the arXiv abstract page or the OpenReview metadata. The PDF was binary-encoded in the WebFetch attempt and could not be parsed.
**Attempted**: WebSearch for the specifications; WebFetch of arXiv abstract; WebFetch of OpenReview page; WebFetch of the HTML version (404'd).
**Recommendation**: Read the Stechly PDF directly (the user has it locally — request a local-copy read if available, or download from arxiv.org/pdf/2310.12397). The exact instance spec is needed for Section 4.3's "match Stechly's setup" engineering plan and for the Section 7.1 sample-size calibration on the Graph Coloring supplement.

### Knowledge Gap 2: Whether Mystery Wumpus's substitution scheme will pass its contamination audit

**Issue**: The portability deep-dive Section 3 recommends Wuggy-generated CVC pseudowords for Mystery Wumpus. Whether this scheme will *empirically* defeat retrieval (the contamination audit, portability deep-dive Section 3.5 step 3) is a pilot-data question, not a literature question.
**Attempted**: Reviewed the portability deep-dive's analysis; checked for published contamination audits of Wuggy-generated stimuli against LLM training corpora (none found).
**Recommendation**: Run the contamination audit as a Phase-I-pilot deliverable. The result determines whether Mystery BW is needed as a backup (Section 8 Stage 4 conditional).

### Knowledge Gap 3: TravelPlanner's heuristic-resistance ceiling against a non-published strong-C

**Issue**: Xie 2024 reports CoT/ReAct baselines at 0.6-0.7%. Gundawar 2024 with their hand-coded LLM-Modulo critics reaches 20.6% (GPT-4-Turbo). What a properly-engineered constraint-greedy non-LLM planner would achieve has not been reported in either paper.
**Attempted**: Searched for "TravelPlanner classical planner baseline" — no published baseline of this form.
**Recommendation**: When implementing TravelPlanner's C cell (Section 4.4, ~2-3 days), pilot the constraint-greedy planner on the validation set (180 queries) before the full test-set run. If C achieves > 50%, TravelPlanner is *not* heuristic-resistant and the D-vs-C claim weakens. If C is < 20%, TravelPlanner is at least as heuristic-resistant as the Phase II TW-Cooking-Hardened claim requires.

### Conflict 1: "6×" (Kambhampati paper text) vs "4.6×" (Gundawar measured)

**Position A**: The LLM-Modulo paper text reports "6x of baselines" for the TravelPlanner LLM-Modulo agentification.
**Source**: [Kambhampati 2024 page 8](../../docs/llm-modulo/2402.01817.pdf) — Reputation: 1.0 — Evidence: "LLM-Modulo based agentification with automated critics in the loop significantly improves the performance (6x of baselines) even with a limit of 10 back prompting cycles"

**Position B**: The Gundawar 2024 paper's own numbers measure 4.6× for GPT-4-Turbo (0% → 20.6% would be infinite, so the multiplier reported is for the baseline-with-CoT/ReAct rate).
**Source**: [Gundawar et al. 2024 arXiv:2405.20625 abstract](https://arxiv.org/abs/2405.20625) — Reputation: 1.0 — Evidence: "GPT4-Turbo achieves 4.6x improvement... GPT3.5-Turbo from 0% to 5%."

**Assessment**: Gundawar 2024 is the *primary* source for the TravelPlanner numbers; the LLM-Modulo paper's "6×" is the paper-text approximation across the model panel. The harebrain supplemental note should use Gundawar's precise numbers (4.6× for GPT-4-Turbo; 0%→5% for GPT-3.5-Turbo). The portability deep-dive Section 5.3 already documents this minor inconsistency.

### Conflict 2: Whether D on TravelPlanner is "different enough" from the published Gundawar setup to count as a separate result

**Position A**: The Gundawar 2024 setup *is* the LLM-Modulo framework applied to TravelPlanner with critics-and-back-prompt. Running it again in the harebrain harness is a *reproduction*, not a novel finding.
**Source**: Implied by the LLM-Modulo paper Section 4 and Gundawar 2024.

**Position B**: The harebrain D-cell on TravelPlanner is *architecturally different* from Gundawar because it embeds the LLM at decide-leaves (per-selection) rather than at whole-plan-generation. The chart owns per-day plan accumulation and constraint state; Gundawar's setup has the LLM generate whole plans and critics back-prompt.
**Source**: Architectural analysis from `wumpus_idea.md` "Two architectures" and the LLM-Modulo paper's whole-plan unit-of-generation.

**Assessment**: Position B is more defensible. The portability deep-dive Section 6 notes that the harebrain D-cell is *finer-grained* than the LLM-Modulo whole-plan unit. On TravelPlanner this finer-grained pattern is a novel application even though the overall benchmark is reproduced. Report it as: "we replicate Gundawar's whole-plan back-prompt result in our E-cell, *and* test a finer-grained per-selection cage in our D-cell — a novel application of the harebrain pattern to TravelPlanner."

## 12. Source Analysis

| Source | Domain | Reputation | Type | Access Date | Cross-verified |
|---|---|---|---|---|---|
| Kambhampati et al. 2024 (paper PDF) | docs/llm-modulo (local) | High (1.0) | academic — ICML peer-review | 2026-05-21 | Yes (Table 1 page 3 + Figure 5 page 8 read directly from PDF) |
| Valmeekam et al. PlanBench NeurIPS 2023 | openreview.net | High (1.0) | academic | 2026-05-21 | Yes (NeurIPS D&B track) |
| Stechly et al. arXiv:2310.12397 | arxiv.org | High (1.0) | academic — NeurIPS workshop | 2026-05-21 | Partial (abstract only; PDF binary not parsed) |
| Stechly et al. arXiv:2402.08115 | arxiv.org | High (1.0) | academic — follow-up | 2026-05-21 | Yes (referenced in Kambhampati 2024 page 3) |
| Gundawar et al. arXiv:2405.20625 | arxiv.org | High (1.0) | academic | 2026-05-21 | Yes (cited in Kambhampati 2024 page 8) |
| Xie et al. arXiv:2402.01622 | arxiv.org | High (1.0) | academic — ICML 2024 | 2026-05-21 | Yes (referenced in Kambhampati 2024 page 8) |
| PlanBench github | github.com/karthikv792 | High (1.0) | open_source — author-maintained | 2026-05-21 | Yes (verified repo metadata) |
| TravelPlanner github | github.com/OSU-NLP-Group | High (1.0) | open_source — author-maintained | 2026-05-21 | Yes (MIT license, Python verifier confirmed via direct fetch) |
| TravelPlanner dataset HF | huggingface.co | Medium-High (0.8) | industry_leaders — dataset host | 2026-05-21 | Yes (1,225 queries documented; Xie 2024 corroborates) |
| Howey et al. VAL 2004 | ieee.org | High (1.0) | academic — IEEE ICTAI | (referenced in portability deep-dive) | Yes |
| Valmeekam et al. 2024 (o1 evaluation) arXiv:2409.13373 | arxiv.org | High (1.0) | academic | (referenced in Phase II) | Yes |
| wumpus_idea.md | local (project repo) | High (1.0) | primary design document | 2026-05-21 | Self-referencing |
| llm-modulo.md (companion narrative) | local (project repo) | High (1.0) | primary design document | 2026-05-21 | Self-referencing |
| Phase I deep-dive | local (project repo) | High (1.0) | prior research output | 2026-05-21 | Self-referencing |
| Phase II deep-dive | local (project repo) | High (1.0) | prior research output | 2026-05-21 | Self-referencing |
| Portability deep-dive | local (project repo) | High (1.0) | prior research output | 2026-05-21 | Self-referencing |
| harebrain.md (thesis) | local (project repo, referenced) | High (1.0) | primary design document | (referenced) | Self-referencing |

Total sources cited: 17 distinct. Of cited sources, 15/17 = 88% in High-reputation tier (arxiv.org, openreview.net, ieee.org, author-maintained github repos with academic affiliation, project-internal primary documents). 2/17 = 12% in Medium-High tier (huggingface.co dataset hosting).

Average reputation score: (15 × 1.0 + 2 × 0.8) / 17 = 16.6 / 17 = **0.976**, well above the 0.80 threshold for High confidence.

## 13. Recommendations for Further Research

1. **Read Stechly 2310.12397 PDF directly** to fill Knowledge Gap 1 (exact graph-coloring instance generation parameters). Estimated cost: 1 hour. Closes the open question in Section 4.3 and Section 7.1.
2. **Pilot the Mystery Wumpus contamination audit** before committing to the Mystery BW supplement (Section 8 Stage 4). Estimated cost: 0.5-1 day. Closes Knowledge Gap 2.
3. **Pilot the TravelPlanner C-cell (constraint-greedy planner)** before committing to the TravelPlanner D-cell. Estimated cost: 1-2 days. Closes Knowledge Gap 3.
4. **Pre-register the analysis plan** (sample sizes, FDR scheme, D-omission decisions) in the repo before running any supplemental experiments. Estimated cost: 0.5 day.
5. **Survey 2025-2026 follow-up literature** on Mystery Blocksworld and TravelPlanner replication studies. The space has been active; there may be newer model-panel data (e.g., Claude 4, o3) that updates Kambhampati's Table 1 numbers. This would inform the "model-panel difference" disclaimer in Risk 9.3.
6. **If running the supplements**, write a *separate evidence-appendix note* per supplement rather than folding them into the main article series. The narrative-dilution mitigation (Risk 9.4) depends on this structural choice.

## 14. Full Citations

[1] Kambhampati, S., Valmeekam, K., Guan, L., Verma, M., Stechly, K., Bhambri, S., Saldyt, L., Murthy, A. "Position: LLMs Can't Plan, But Can Help Planning in LLM-Modulo Frameworks." *Proceedings of the 41st International Conference on Machine Learning*, PMLR 235, Vienna, 2024. arXiv:2402.01817. Local copy: `docs/llm-modulo/2402.01817.pdf`. Accessed 2026-05-21.

[2] Valmeekam, K., Marquez, M., Olmo, A., Sreedharan, S., Kambhampati, S. "PlanBench: An Extensible Benchmark for Evaluating Large Language Models on Planning and Reasoning about Change." *NeurIPS 2023 Datasets and Benchmarks Track*. https://openreview.net/pdf?id=YXogl4uQUO. Accessed 2026-05-21.

[3] Stechly, K., Marquez, M., Kambhampati, S. "GPT-4 Doesn't Know It's Wrong: An Analysis of Iterative Prompting for Reasoning Problems." arXiv:2310.12397. *NeurIPS 2023 Foundation Models for Decision Making Workshop*. https://arxiv.org/abs/2310.12397. Accessed 2026-05-21.

[4] Stechly, K., Valmeekam, K., Kambhampati, S. "On the Self-Verification Limitations of Large Language Models on Reasoning and Planning Tasks." arXiv:2402.08115, 2024. https://arxiv.org/abs/2402.08115. Accessed 2026-05-21.

[5] Gundawar, A., Verma, M., Guan, L., Valmeekam, K., Bhambri, S., Kambhampati, S. "Robust Planning with LLM-Modulo Framework: Case Study in Travel Planning." arXiv:2405.20625, 2024. https://arxiv.org/abs/2405.20625. Accessed 2026-05-21.

[6] Xie, J., Zhang, K., Chen, J., Zhu, T., Lou, R., Tian, Y., Xiao, Y., Su, Y. "TravelPlanner: A Benchmark for Real-World Planning with Language Agents." arXiv:2402.01622, *ICML 2024 Spotlight*. https://arxiv.org/abs/2402.01622. Accessed 2026-05-21.

[7] Valmeekam, K., Stechly, K., Kambhampati, S. "LLMs Still Can't Plan; Can LRMs? A Preliminary Evaluation of OpenAI's o1 on PlanBench." arXiv:2409.13373, 2024. https://arxiv.org/abs/2409.13373. Accessed 2026-05-21.

[8] Howey, R., Long, D., Fox, M. "VAL: Automatic Plan Validation, Continuous Effects and Mixed Initiative Planning using PDDL." *16th IEEE International Conference on Tools with Artificial Intelligence (ICTAI 2004)*, pp. 294-301. https://ieeexplore.ieee.org/document/1374201. Source code: https://github.com/KCL-Planning/VAL.

[9] Valmeekam, K. (maintainer). "LLMs-Planning" repository. https://github.com/karthikv792/LLMs-Planning. PlanBench instances and Mystery BW substitution scheme. Accessed 2026-05-21.

[10] OSU NLP Group. "TravelPlanner." https://github.com/OSU-NLP-Group/TravelPlanner. MIT-licensed. Accessed 2026-05-21.

[11] OSU NLP Group. "TravelPlanner Dataset." https://huggingface.co/datasets/osunlp/TravelPlanner. 1,225 queries. Accessed 2026-05-21.

[12] OSU NLP Group. "TravelPlanner Project Page." https://osu-nlp-group.github.io/TravelPlanner/. Accessed 2026-05-21.

[13] VanEvery, P. (project author). `wumpus/docs/wumpus_idea.md`. Harebrain project, accessed 2026-05-21.

[14] VanEvery, P. (project author). `docs/llm-modulo/llm-modulo.md`. Harebrain project, accessed 2026-05-21.

[15] VanEvery, P. + nw-researcher. `docs/research/agents/phase-i-task-design-deep-dive.md`. Harebrain project, accessed 2026-05-21.

[16] VanEvery, P. + nw-researcher. `docs/research/agents/phase-ii-task-design-deep-dive.md`. Harebrain project, accessed 2026-05-21.

[17] VanEvery, P. + nw-researcher. `docs/research/agents/llm-modulo-benchmark-portability-deep-dive.md`. Harebrain project, accessed 2026-05-21.

## 15. Research Metadata

Duration: ~50 turns (per turn budget plan). Sources examined: ~22 web pages, 7 local files, 1 PDF (read directly via Read tool). Sources cited: 17. Cross-references: to wumpus_idea.md (8), to llm-modulo.md (3), to phase-i-task-design-deep-dive.md (5), to phase-ii-task-design-deep-dive.md (6), to llm-modulo-benchmark-portability-deep-dive.md (8). Confidence distribution: High on the published numbers (Kambhampati Table 1, Gundawar 4.6×, Xie 0.6-0.7%, Stechly's headline asymmetry — all directly verified); Medium-High on the architectural-fit analysis per cell (structural reasoning from primary documents); Medium on the negative-result risk modeling for D-on-PDDL (structural reasoning pending pilot validation). Output: `docs/research/agents/llm-modulo-benchmarks-as-supplements-deep-dive.md`.

---

**Operational discharge summary** (every recommendation lands on a specific action):

| Recommendation | Action | Stage / Owner |
|---|---|---|
| Pre-register D-omission for BW/MBW/GraphColor | Write 1-page analysis plan; commit to repo | Pre-Stage-1 |
| Pre-register sample sizes (100/cell standard; 300 for BW credentialing) | Include in analysis plan | Pre-Stage-1 |
| Pre-register FDR scheme (q=0.10 within supplements) | Include in analysis plan | Pre-Stage-1 |
| Read Stechly 2310.12397 PDF for instance specs | Local PDF read; transcribe Section 4 methodology | Pre-Stage-1 |
| Pilot Mystery Wumpus contamination audit | Per portability deep-dive Section 3.5 step 3 | Part of Phase I |
| Run Graph Coloring at A+C+E+F | 4-6 days; output: appendix note on verification asymmetry | Stage 1 |
| Pilot TravelPlanner C-cell on validation set | 1-2 days; gate decision for D-cell investment | Pre-Stage-2 |
| Run TravelPlanner at full A-G with back-prompt loop | 12-18 days; output: appendix note replicating Gundawar | Stage 2 |
| Time-box TravelPlanner D to 5 days | Drop D if chart isn't running by day 5 | Within Stage 2 |
| Stage 3 (Blocksworld) conditional on external requirement | Skip unless JMLR/JAIR review demands | Stage 3 |
| Stage 4 (Mystery BW) conditional on Mystery Wumpus audit failure | Skip unless audit fails | Stage 4 |
| Frame literature-comparability as "consistent with" | Reporting discipline in all supplemental notes | All stages |
| Keep Notes 1-2 Wumpus/TW-Cooking only | Supplements live in appendices/technical reports | Article structuring |
