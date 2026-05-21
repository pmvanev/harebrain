# Research: Phase II Benchmark Task Design — Heuristic-Resistant Long-Horizon Multi-Step Planning on a TextWorld-Equivalent Substrate

**Date**: 2026-05-21 | **Researcher**: nw-researcher (Nova) | **Confidence**: Medium-High overall (High on TextWorld substrate properties and IPC baseline methodology; Medium on task-specific heuristic-resistance estimates that require pilot validation) | **Sources**: 40 cited (80% High-reputation tier)

## Executive Summary

**Recommended Phase II task**: **TW-Cooking-Hardened** — Microsoft TextWorld's cooking-game challenge at maximum stock difficulty (12 rooms, 4-ingredient recipes, all skills enabled: open containers, cook, cut, limited inventory). Contingent escalation to **TW-Cooking-Extended-Custom-Recipes** (hand-authored recipes not in TextWorld's defaults) if a pilot shows the stock difficulty is heuristic-solvable by a strong classical planner. Implementation: 2-3 weeks engineering (within budget), 4-5 weeks total with pilot and instrumentation.

**The single most important Phase II design change vs. Phase I**: **C is no longer a 50-line Python heuristic. C is Fast Downward Stone Soup 2023 with online replanning, consuming a PDDL translation of TextWorld observations.** This is the published baseline from the International Planning Competition, decades of accumulated planning research. Without this change, the "brain earns its keep" claim is sandbagged. With it, D > C is a real finding because C is at the planning-research ceiling for symbolic search.

**Architecture matrix translation**: A = TextWorld's `quest.commands` walkthrough (free ceiling). B = uniform random over `info["admissible_commands"]` (free floor). C = strong PDDL planner as above. D, E1-E4, F1/F2 unchanged in structure but consume TextWorld's `obs` stream; F is split into format-control pair per Phase I doc Finding 27.

**Headline metric**: HRPR (Heuristic-Relative Progress Rate) = D-progress(turn T) / C-progress(turn T), with bootstrap 95% CI and paired-bootstrap evaluation methodology. Pre-register Cohen's h ≥ 0.3 on win-rate as the minimum publishable effect.

**Sample size**: 100 seeds × 8 LLM cells × 3 models = 2,400 LLM runs + 300 control runs. Well above the h=0.3 detection floor.

**Confidence**: **Medium-High**. The TextWorld substrate properties are documented (High confidence). The strong-C methodology is established planning-research practice (High). The cooking-task heuristic-resistance estimate is informed but ultimately speculative (Medium): no published study runs Fast Downward against frontier LLMs on TW-Cooking specifically. This is the Phase II pilot's primary novel contribution.

**Biggest risk**: The pilot shows C ≥ D on TW-Cooking-Hardened. Cooking is structured-prerequisite work; LAMA may eat it. Mitigation: pilot first (Section 11.2), escalate to custom-recipes (Section 6.8) if needed, switch to ScienceWorld or custom Inform 7 deception game (Section 5) as fallbacks. The honest possibility that Phase II finds no separation is acknowledged in Section 11.4. The strong-C methodology is itself a contribution regardless of the headline result (Section 11.3).


## 1. Recap: Phase II Constraints from the User

The user has read the Phase I deliverable ([`long-horizon-agent-benchmarks-deep-dive.md`](./long-horizon-agent-benchmarks-deep-dive.md)) and committed to specific parameters for Phase II:

1. **What Phase II must prove (narrow)**: There exist tasks where a careful Python heuristic *cannot* substitute for the LLM, and the cage helps the LLM realize that advantage instead of squandering it on world-model drift. Not policy compliance. Not open-ended exploration. Not memory-under-distraction. The narrow claim: *long-horizon multi-step planning a heuristic can't shortcut*.
2. **Engineering budget**: 2-4 weeks of setup (Phase I doc line 385's "proper TextWorld-equivalent" tier).
3. **Architecture matrix unchanged**: A scripted ceiling, B random-legal floor, C heuristic ablation, D harebrain/MPL-caged, E LangGraph variants, F LangChain bare ReAct, G wild coding-agent. The task changes; the cells don't.

**Implication**: Phase II is a task-selection-and-design problem, not an architecture-selection problem. The load-bearing work is making sure **C cannot win** — that is, designing a task where a strong classical-planning heuristic genuinely fails while an LLM-with-cage succeeds.

This document answers the next-level-down questions from the Phase I doc's TextWorld recommendation (Tier S, line 385):
- What *kind* of TextWorld game family is heuristic-resistant? (Section 5)
- What complexity knobs make a planning task heuristic-resistant in practice? (Section 3)
- How is a *strong* heuristic baseline (C) designed so that "C < D" is a real finding? (Section 4)
- What's the published evidence about where LLMs first reliably beat strong symbolic planners on long-horizon tasks? (Section 3)
- How do the six Phase I divergence kinds translate to a richer task? (Section 7)
- What scaffolding-leak metrics carry over and what changes? (Section 7)


## 2. TextWorld as Substrate

### 2.1 What TextWorld is, technically

TextWorld is a Python library from Microsoft Research with two main components: a **game generator** that converts high-level game specifications (number of rooms, number of objects, game length, winning conditions) into executable game source code in **Inform 7**, and a **game engine** that handles interactive play-through, state tracking, and reward assignment ([Côté et al., 2018](https://arxiv.org/abs/1806.11532), Microsoft Research). The generator gives "precise control over the difficulty, scope, and language of constructed games" and was designed explicitly to relax challenges inherent to commercial interactive fiction (partial observability, sparse rewards) so that learning agents have tunable knobs to work against.

Build-out matters for Phase II because every world fact is held as a typed proposition in the engine's knowledge base. The TextWorld engine maintains a **logical state** (a set of facts in first-order logic), so the user can read out, at any turn, the truth value of every predicate that could matter for divergence-event scoring. This is the same property the Phase I deliverable identified as load-bearing for Wumpus (closed-form, small enum, oracle is trivial) — TextWorld preserves it while letting the world get much larger ([TextWorld docs](https://textworld.readthedocs.io/en/stable/), Read the Docs).

### 2.2 Reproducibility and seed mechanism

TextWorld accepts a top-level `--seed` parameter that fans out into four sub-seeds for `map`, `objects`, `quest`, and `grammar`. The map seed controls room layout; objects seed controls hazard/tool placement; quest seed controls the prerequisite chain to victory; grammar seed controls surface description. Pinning all four reproduces a game exactly. Pinning three and varying one produces controlled variation along a single axis ([TextWorld docs](https://textworld.readthedocs.io/en/stable/textworld.generator.inform7.html)).

This is materially better than rolling-your-own Wumpus reproducibility: in MPL-Wumpus, the user controls hazard layout (one effective seed). In TextWorld, the user can independently vary the *layout* and the *quest* — i.e., hold the world constant and only vary the prerequisite chain, which is the cleanest possible test of "the brain plans through prerequisites; the heuristic doesn't."

### 2.3 Difficulty knobs

The published knobs are:
- `--world-size`: number of rooms (Phase I doc Tier-S recommendation called for 50-100+; TextWorld supports this without rewriting the engine)
- `--nb-objects`: number of interactive objects excluding doors (governs branching factor at decision points)
- `--quest-length`: minimum number of commands required to win (governs horizon directly)
- `--quest-breadth` (subquests per independent quest): how nonlinear the quest can be; `1` = linear chain

Each of these is independent. The combinatorial space is large enough that contamination from public TextWorld games is essentially nil for generated-on-demand task instances ([TextWorld docs](https://textworld.readthedocs.io/en/stable/textworld.generator.game.html)).

### 2.4 Glulx compilation and the practical engineering ceiling

Generated Inform 7 code compiles to Glulx, an interactive-fiction VM bytecode. The practical complexity ceiling is **whatever a competent Inform 7 author can express**, which historically encompasses commercial IF games (puzzle dependencies, NPC dialogue, object combination, scope rules). For Phase II that is a far higher ceiling than the user needs ([Emily Short, "TextWorld (Inform 7 & machine learning)", 2018](https://emshort.blog/2018/09/25/textworld-inform-7-machine-learning/), industry expert in IF design).

**Confidence**: High. Three independent sources (Microsoft Research paper, TextWorld documentation, Emily Short's IF-design coverage) corroborate the substrate's properties.

### 2.5 What the user must implement to use TextWorld for Phase II

Concretely:
1. **TextWorld harness wired into the existing MPL chart**: The Phase I architecture has MPL as the cage; for D the LLM is consulted at decide-leaves via host imports. TextWorld replaces *the game logic the chart wraps*. The chart still owns blackboard slots; those slots are now populated from TextWorld's logical-state read-outs rather than from internal MPL rules. Estimated: 3-5 days.
2. **Action-and-observation translator** between TextWorld's text format and the chart's typed action vocabulary. TextWorld uses imperative natural language ("take knife from counter"); the cage operates on typed verdicts. Estimated: 2-3 days.
3. **Ground-truth oracle wrapper** that reads TextWorld's full logical state per turn and presents the same divergence-detection interface the Phase I oracle exposes. Estimated: 1-2 days (TextWorld's `game.infos` API already exposes facts).
4. **Quest-chain configuration** specifying which TextWorld game family Phase II uses and at what difficulty. This is the *task design* question Thread 4 addresses below. Estimated: 1 week to design, prototype, and tune.

Total: 2-3 weeks engineering. Inside the user's 2-4 week budget.


## 3. Heuristic-Resistance: What the Literature Shows

This thread is the **single most important section for the Phase II decision**. If the literature shows LLMs do not yet beat strong heuristic planners on the kinds of tasks TextWorld generates, the user's brain-earns-its-keep claim is at risk regardless of which TextWorld variant is chosen.

### 3.1 The Valmeekam / Kambhampati line: LLMs cannot plan robustly on classical-planning domains

Karthik Valmeekam and Subbarao Kambhampati (Arizona State) have run a sustained empirical program — PlanBench (NeurIPS 2023) and follow-ups — testing whether LLMs can solve classical-planning tasks. The key findings:

**Evidence**: "PlanBench instantiates classical planning domains that have well-defined semantics, bounded complexity, and broad coverage of key planning phenomena... LLMs cannot reliably solve even small classical planning tasks when used for end-to-end plan generation."
**Source**: [Valmeekam et al., "PlanBench: An Extensible Benchmark for Evaluating Large Language Models on Planning and Reasoning about Change", NeurIPS 2023](https://openreview.net/pdf?id=YXogl4uQUO) — Accessed 2026-05-21
**Confidence**: High

**Evidence (Mystery Blocksworld)**: "Best performing LLM, LlaMA 3.1 405B, reached 62.5% accuracy on vanilla Blocksworld, but no LLM achieved even 5% on the Mystery Blocksworld test set [obfuscated-predicate variant]. O1 exhibited a quantum leap in solving Blocksworld instances, correctly addressing 97.8% in zero-shot scenarios. However, its capability on Mystery Blocksworld remains below expectations compared to traditional planning systems."
**Source**: [Valmeekam, Stechly et al., "LLMs Still Can't Plan; Can LRMs? A Preliminary Evaluation of OpenAI's o1 on PlanBench", 2024](https://arxiv.org/abs/2409.13373) — Accessed 2026-05-21
**Confidence**: High
**Verification**: [Yann LeCun X commentary cross-confirming results](https://x.com/ylecun/status/1832860107925024789), [Semantic Scholar paper page](https://www.semanticscholar.org/paper/LLMs-Still-Can't-Plan;-Can-LRMs-A-Preliminary-of-o1-Valmeekam-Stechly/5329cea2b868ce408163420e6af7e9bd00a1940c)

**Analysis**: This is **honest counter-evidence** for the user's experiment. On *pure-classical-planning* domains where a hand-written PDDL heuristic (FF, LAMA, Fast Downward) saturates within seconds, modern LLMs do not yet beat the heuristic — and explicitly fall apart when surface predicates are renamed (Mystery Blocksworld). If Phase II's task accidentally lands here, **the brain claim collapses** because C will outperform D.

What this implies for Phase II:
- Avoid pure Blocksworld variants. The state space is too small and the heuristic ceiling is too high.
- Avoid tasks that are *fully* reducible to PDDL with admissible heuristics. Fast Downward will eat them.
- Seek tasks that combine planning with one or more of: (a) natural-language affordance recognition, (b) commonsense composition of objects, (c) hidden-information-from-text. These are LLM strong points the heuristic cannot match.

### 3.2 The LLM-Modulo position: LLM as proposer, classical planner as verifier

**Evidence**: "Auto-regressive LLMs cannot, by themselves, do planning or self-verification. LLMs should be viewed as universal approximate knowledge sources... an LLM is augmented with a suite of external verifiers and other components which evaluate its proposed answers before deciding whether they should be output... In a more complex travel planning task, the LLM-Modulo Framework achieved a remarkable 6 times better performance compared to baseline approaches."
**Source**: [Kambhampati et al., "Position: LLMs Can't Plan, But Can Help Planning in LLM-Modulo Frameworks", ICML 2024 (spotlight)](https://arxiv.org/abs/2402.01817) — Accessed 2026-05-21
**Confidence**: High
**Verification**: [PMLR proceedings page](https://proceedings.mlr.press/v235/kambhampati24a.html), [ACM Digital Library](https://dl.acm.org/doi/10.5555/3692070.3692991)

**Analysis**: This is exactly the cage pattern the user is testing. The Phase I deliverable (Finding 32) already noted that formal-method-shaped constraint on LLMs is an active area. Kambhampati's LLM-Modulo paper is the philosophical-justification piece. For Phase II, this matters in three ways:

1. **It predicts D > F.** LLM-with-verifier should outperform LLM-alone on planning tasks. This is the user's hypothesis dressed in different vocabulary.
2. **It predicts D > C only when proposal-space matters.** The LLM contributes by *generating candidate plans* that a verifier checks. If C's heuristic already enumerates the relevant plan space (small Blocksworld), the LLM has nothing to add. If C's heuristic misses the plan space (high branching, novel combinations), the LLM's generative proposal dominates.
3. **It directly implies the Phase II task selection criterion**: pick a task where *plan-space generation is the bottleneck*, not where *plan-space search is the bottleneck*. Search is what Fast Downward does well; generation under semantic constraints is what LLMs do well.

### 3.3 Where LLMs reliably beat symbolic planners — published evidence

**Evidence**: "LLM-generated heuristics can be integrated with classical planners... Tree of Interaction (ToI) uses LLM as a heuristic and Boomerang uses LLM as a generative planner."
**Source**: [Various, "Classical Planning with LLM-Generated Heuristics: Challenging the State of the Art with Python Code"](https://arxiv.org/html/2503.18809v2) — Accessed 2026-05-21
**Confidence**: Medium-High (single primary source; supporting context cited below)

**Analysis**: The honest answer the user paid for: **published evidence that LLMs alone reliably beat strong symbolic planners on long-horizon classical-planning tasks is thin.** The cases where LLMs win tend to be:
- Tasks where the action space is open-ended natural language (no fixed PDDL action set to plan over). Symbolic planners can't enter this regime.
- Tasks where the goal is under-specified and requires LLM commonsense to disambiguate ("make a sandwich" — what counts as a sandwich?). Symbolic planners need fully specified goals.
- Tasks where actions have non-symbolic, learned consequences (e.g., physical commonsense — "if you spill water on the floor, the floor is wet"). Symbolic planners need axiomatized consequences.

In all three cases, the heuristic baseline (C) struggles **because the heuristic author can't formalize the task fully**, not because the heuristic is incompetent at search. This is the Phase II target zone.

### 3.4 Domains where heuristics still win — what to avoid

From the Phase I deliverable and the Valmeekam line:
- **Pure Blocksworld variants**: Fast Downward solves the entire state space.
- **Sokoban**: Strong domain-specific heuristics with deadlock detection.
- **Small graph traversal**: Dijkstra dominates.
- **Pure puzzle domains with full observability**: BFS/IDA* dominates.

The Phase I L4 escalation of Wumpus (bigger graph, non-dodecahedron) **lands here** if the user is not careful. A 50-room Wumpus with full sensing is still A* with admissible heuristic — heuristic ceiling near optimal.

**Confidence on this section overall**: High. Four+ independent sources (PlanBench, LLMs-Still-Can't-Plan, LLM-Modulo, LLM-generated-heuristics) consistently characterize where LLMs do and don't add value over classical search.


## 4. The Strong-C Problem

The Phase II claim "the brain earns its keep" rests entirely on the credibility of C. If C is weak, C < D is trivially achievable and uninformative. If C is too strong (uses information the LLM doesn't), the comparison is unfair. This section addresses both pitfalls with concrete recommendations.

### 4.1 What the planning literature recommends as a baseline

The International Planning Competition (IPC) uses **Fast Downward / LAMA** as the de-facto baseline solver. LAMA "won the sequential satisficing track at IPC-2011" and "showed best performance among all planners in the sequential satisficing track of the International Planning Competition 2008" ([LAMA paper, JAIR 39](https://www.jair.org/index.php/jair/article/download/10667/25496/19843), University of Freiburg/JAIR — peer-reviewed; [IPC 2023 Classical Tracks](https://ipc2023-classical.github.io/), official planning competition page).

**Evidence**: "A weighted A* search is used with iteratively decreasing weights, so that the planner continues to search for plans of better quality until the search is terminated... LAMA builds on the Fast Downward planning system, using finite-domain rather than binary state variables and multi-heuristic search... combines the landmark heuristic with a variant of the well-known FF heuristic."
**Source**: [Richter & Westphal, "The LAMA Planner: Guiding Cost-Based Anytime Planning with Landmarks", JAIR 39, 2010](https://arxiv.org/pdf/1401.3839) — Accessed 2026-05-21
**Confidence**: High
**Verification**: [ACM DL listing](https://dl.acm.org/doi/10.5555/1946417.1946420), [Fast Downward Stone Soup baseline portfolio](https://www.researchgate.net/publication/228851671_Fast_Downward_Stone_Soup_A_Baseline_for_Building_Planner_Portfolios), [IPC 2018 baseline tracks](https://ipc2018-classical.bitbucket.io/)

**Analysis for Phase II**: The user **should not** implement C as a hand-written Python heuristic from scratch. The published baseline is decades of accumulated research. The recommended C for Phase II is:

> **C = a domain-translation layer (Python) that emits the TextWorld task as PDDL, plus an off-the-shelf classical planner (Fast Downward in LAMA-2011 configuration) that produces an action sequence, plus an executor that submits actions back to TextWorld.**

This is the *strongest possible C* under reasonable engineering. Phase I's "50-line Python heuristic for Wumpus" was appropriate at L1 because Wumpus' state space is tiny. For TextWorld-scale Phase II, the strong-C is a real planner — anything weaker invites the sandbag critique.

### 4.2 Why this is the right C for Phase II

1. **Parity of information**: Fast Downward gets the same observations the LLM does (TextWorld's text output is parsed into facts; both architectures consume "what the agent has seen"). Crucially, Fast Downward does **not** get to see the hidden state — only what's been observed. This is the parity bar.
2. **Strong but bounded**: On classical-planning domains where PDDL captures the task, Fast Downward is at or near the planning-research ceiling. If D beats this, the brain claim is real.
3. **Externally calibrated**: The user does not have to defend "we tuned the heuristic enough." LAMA is the published baseline; it's the comparator the planning community uses.
4. **Failure modes are well-documented**: Fast Downward will fail when (a) the task is not expressible as PDDL, (b) the heuristic search blows up combinatorially, (c) the domain requires natural-language interpretation. **These three failure modes are exactly the Phase II target zone** (Section 3.3).

### 4.3 The sandbag pitfall — what to actively avoid

Phase I doc Finding 27 (Safety-Under-Scaffolding) showed that scaffold-induced format changes are a large confound. The C-baseline analog is **planner-input format changes**:

- **Sandbag risk**: Phrasing the C-baseline's PDDL translation in ways that omit relevant predicates. If the LLM can read "the door is locked unless you have the brass key" but the PDDL translator drops this, C is strawmanned.
- **Mitigation**: Pre-publish (in the repo) the exact PDDL translation rules for every TextWorld predicate. Any reviewer should be able to verify that C had access to the same information as D.
- **Sandbag risk**: Using a 2010-era heuristic configuration when 2023-era portfolios exist. *Don't*. Use Fast Downward Stone Soup 2023 if you want the toughest comparator ([IPC 2023](https://ipc2023-classical.github.io/)).
- **Sandbag risk**: Single-shot Fast Downward (one plan attempt, no replanning) when the agent gets to make many decisions. Use online replanning: every observation triggers a re-plan.

### 4.4 The over-strong pitfall — when C can't lose

The complementary risk: C might use information the LLM doesn't have. Specifically:
- **The full TextWorld logical state** (the oracle) — C must consume only *observed* predicates, just like the LLM. This is what the cage architecture for D enforces by construction; for C, it must be enforced by the harness.
- **The pre-computed quest plan** — TextWorld optionally exposes the canonical solution. C must not see it. The harness must hide the `quest.commands` field from C's PDDL translator.

### 4.5 Operational definition for the user

For the Phase II writeup, the C-baseline should be characterized as:

> "C is the **2023 Fast Downward Stone Soup portfolio** running on a PDDL translation of TextWorld observations, restricted to observed predicates, with online replanning after every new observation. The LLM in D consumes the same observation stream in natural language. Both architectures have the same information available at every decision point."

This is the C-design that "if D > C, the result is publishable." Cite [IPC 2023 baseline](https://ipc2023-classical.github.io/) in the methods section.

**Confidence on this section**: High. The IPC baseline-solver convention is decades-old and uncontroversial; the sandbag-vs-strawman tension is standard practice in planning-research evaluation.


## 5. Candidate Task Designs Ranked

For each candidate, I estimate: **heuristic ceiling (C max)**, **LLM-with-cage ceiling (D max)**, **engineering cost** (weeks), **Phase I metric carryover**, **new metrics needed**, **fit-for-user**. Estimates are coarse; pilot runs would refine.

| # | Candidate | C max | D max | Eng cost | Metrics carryover | New metrics | Fit |
|---|---|---|---|---|---|---|---|
| 1 | **TW-Cooking (Phase II hardened)** | 35-55% | 65-80% | 2-3 wks | 4 of 6 | recipe-skip, ingredient-state drift | **Best** |
| 2 | **TW-Cooking-extended (multi-recipe, novel combos)** | 20-35% | 55-70% | 3-4 wks | 4 of 6 | recipe-skip, affordance-phantom | Strong |
| 3 | **TW-Treasure-Hunter (deep prereqs, level 25-30)** | 50-70% | 65-80% | 1-2 wks | 5 of 6 | prereq-collapse | Strong if level ≥ 25 |
| 4 | **TW-Coin-Collector (40 rooms, distractors)** | 75-95% | 60-90% | 1 wk | 3 of 6 | none meaningful | **Avoid — heuristic eats** |
| 5 | **Custom Inform 7 deception game** | 10-25% | 40-60% | 4-6 wks | 2 of 6 | testimony-conflict, false-belief | High potential, high cost |
| 6 | **Reactive-environment custom (world reacts to history)** | 25-45% | 55-70% | 3-5 wks | 5 of 6 | state-causality drift | Strong but bespoke |
| 7 | **ScienceWorld (5th-grade procedural)** | 15-30% | 50-65% | 1-2 wks | 5 of 6 | procedure-skip | Strong alt |
| 8 | **MPL-Wumpus L4+ (50 rooms, dynamic)** | 60-80% | 65-80% | 1-2 wks | 6 of 6 | minimal new | **Avoid — too close to Phase I** |
| 9 | **BALROG NetHack subset (MiniHack quest)** | 5-15% | 5-20% | 3-4 wks | 3 of 6 | NetHack-specific | Avoid — floor effect |
| 10 | **AppWorld single-app subset** | 30-50% | 40-65% | 4-6 wks | 2 of 6 | API-state drift | Avoid — wrong domain |

### 5.1 Justification for each ranking

**#1 TW-Cooking (Phase II hardened)** — Recommended. The cooking-game challenge has 7 named difficulty knobs (`recipe complexity`, `ingredient gathering`, `nb_locations` (1/6/9/12), `open_containers`, `cooking_method`, `cutting`, `inventory constraints`) ([TextWorld Cooking docs](https://textworld.readthedocs.io/en/stable/textworld.challenges.cooking.html)). At the *hardened* setting (12 locations, 4-5 ingredients, all skills on, inventory-limited), it requires:
- Multi-step prerequisite chains (find cookbook → identify ingredients → locate each → process each correctly → assemble in kitchen)
- Reading natural-language recipes that vary per-game (no memorization)
- Reasoning about ingredient state (raw/sliced/cooked) which is a non-trivial PDDL fluent
- Spatial planning under partial observability

The **First TextWorld Problems competition winner reached 91.9% raw / 70.8% with handicap** ([Microsoft Research blog](https://www.microsoft.com/en-us/research/blog/first-textworld-problems-the-competition-using-text-based-games-to-advance-capabilities-of-ai-agents/)) in 2019 with a neural-RL agent specifically trained on cooking. That sets the achievable ceiling. For an out-of-the-box LLM with no cooking-specific training, the gap to the heuristic baseline is the Phase II measurement target. The known result that GPT-4o and Claude 3.5 Sonnet "lead" on BALROG-TextWorld but do not saturate ([BALROG paper](https://arxiv.org/html/2411.13543v2), ICLR 2025) is independent confirmation that cooking-class games remain non-trivial for frontier LLMs.

**#2 TW-Cooking-extended** — Same substrate, harder configuration: multi-recipe (cookbook lists alternatives), novel ingredient combinations (no canonical "make a salad" mapping in training data), wider topology. Engineering cost rises because the user must hand-author novel recipe templates that don't appear in TextWorld's defaults. Higher heuristic-resistance because the rule set is custom and the LAMA heuristic loses its prior knowledge.

**#3 TW-Treasure-Hunter (level 25-30)** — TextWorld's `treasure_hunter` challenge supports difficulty levels 1-30, with level 30 involving "finding keys and unlocking doors" ([TextWorld Treasure Hunter docs](https://textworld.readthedocs.io/en/stable/textworld.challenges.treasure_hunter.html), [GitHub issue #85](https://github.com/microsoft/TextWorld/issues/85)). At high levels the prerequisite chain (find key → unlock door → enter room → find next key → ...) gets deep. **Risk**: this is *closer* to PDDL-solvable than cooking; the LAMA heuristic may handle deep chains well if the predicate set is small.

**#4 TW-Coin-Collector** — **Avoid.** Despite GPT-4o solving only 1/20 attempts in BALROG ([BALROG paper](https://arxiv.org/html/2411.13543v2)), Coin Collector is **a corridor with distractors**. A trivial heuristic ("BFS to unvisited rooms, prefer unexplored direction") plays this well. The fact that LLMs fail at it tells you LLMs are *worse than a heuristic at it* — which is the wrong direction for the Phase II claim. The Phase I doc made the analogous point about MPL-Wumpus L4: more rooms doesn't make it heuristic-resistant.

**#5 Custom Inform 7 deception game** — The most heuristic-resistant option, because deception requires natural-language interpretation that no PDDL translator can faithfully capture. **Risk**: high engineering cost (4-6 weeks just to author the game), uncertain difficulty calibration, hard to instrument an oracle for "did the agent correctly identify the lying NPC."

**#6 Reactive-environment custom** — World state changes based on agent action history (closest TextWorld analogue to the user's L2 Wumpus-moves-when-startled). Implementable via Inform 7 rules that modify world state on triggers. Heuristic-resistant because Fast Downward's planning model is typically Markovian — non-stationary domains where the agent's prior actions change the rules of the world break the heuristic's assumptions. **Cost**: 3-5 weeks, but the user is partly already paying this cost in their L2 design.

**#7 ScienceWorld** — Wang & Jansen's 30-task benchmark of elementary science procedures. Highly heuristic-resistant: tasks like "measure the melting point of orange juice" require procedural commonsense (apply heat slowly, measure when phase changes). Strong alt-candidate to TW-Cooking. **Trade-off**: more bespoke than TW-Cooking, less flexible difficulty knobs.

**#8 MPL-Wumpus L4+** — **Avoid.** The Phase I deliverable already concluded that L4 essentially rebuilds TextWorld (line 378). Staying with MPL-Wumpus saves engineering by reusing the chart, but at the cost of recapitulating exactly the heuristic-eaten geography that Phase I identified. The Phase I doc's section "Why classic Yob is probably too small for the brain-demo (Note 2)" applies even at L4.

**#9 BALROG NetHack subset** — **Avoid.** BALROG-NLE has all models flatlining at ~1.5% average progression ([BALROG paper](https://arxiv.org/html/2411.13543v2)). Floor effect dominates; differences between architectures would not be statistically distinguishable.

**#10 AppWorld single-app** — **Avoid.** Domain shift to digital task assistant. The user's whole research program is about reasoning/state-tracking, not API tool use. Wrong substrate for this question.

### 5.2 The honest case for skepticism

One pitfall must be noted: **even TW-Cooking at the hardened setting may turn out to be heuristic-solvable.** Cooking is closer to a hierarchical task network (HTN) than to natural-language inference. If Fast Downward with HTN extensions ([SHOP3, JSHOP2](https://www.ipc2023-classical.github.io/), and the planning literature on HTN) is configured well, it may plan cooking tasks accurately enough that D ≈ C. The honest Phase II design must include a pilot phase (Section 12) that tests this before committing.

The most heuristic-resistant option is #5 (custom Inform 7 deception), but the engineering cost is at the upper edge of the user's budget. The recommended path is **#1 TW-Cooking-hardened** with a contingent escalation to **#2 TW-Cooking-extended (custom recipes)** if the pilot shows C is too strong.


## 6. The Recommended Phase II Task — Concrete Spec

### 6.1 Headline recommendation

**TW-Cooking-Hardened with a contingent escalation path to TW-Cooking-Extended-Custom-Recipes.**

Game generator: `tw-cooking` from Microsoft TextWorld 1.6+ (PyPI: `textworld`).

### 6.2 Base configuration (the "Phase II default seed family")

```
tw-make tw-cooking \
  --recipe 4 \
  --take 4 \
  --go 12 \
  --open \
  --cook \
  --cut \
  --drop \
  --seed {seed}
```

Parameter explanations ([TextWorld Cooking docs](https://textworld.readthedocs.io/en/stable/textworld.challenges.cooking.html)):
- `--recipe 4`: 4 ingredients in the recipe
- `--take 4`: 4 ingredients must be found (all of them)
- `--go 12`: 12 rooms (maximum supported in the standard challenge)
- `--open`: containers and doors must be opened
- `--cook`: some ingredients require cooking (introduces state fluents)
- `--cut`: some ingredients require cutting
- `--drop`: limited inventory (forces planning over what to carry)

This produces episodes of typical length **20-50 actions** to optimal completion ([First TextWorld Problems competition](https://www.microsoft.com/en-us/research/blog/first-textworld-problems-the-competition-using-text-based-games-to-advance-capabilities-of-ai-agents/) — winners' games were in this range). Suboptimal play extends to 80-150 actions before either success or turn-cap.

### 6.3 Rule complexity

- **State space**: 12 rooms × ~30 objects (cookbook, ingredients, tools, containers, fixtures) × ~4-7 state fluents per ingredient (raw/sliced/diced/roasted/fried/grilled/eaten/carried) ≈ 10^8 reachable configurations. Far beyond Wumpus' 10^4.
- **Action space**: TextWorld's textual action API — `take {X} from {Y}`, `open {X}`, `cook {X} with {Y}`, `cut {X} with {Y}`, `prepare meal`, `eat meal`, `go {direction}`, `examine {X}`. ~12 verbs × variable arguments.
- **Prerequisite chain depth**: 5-8 sequential steps after the cookbook is read. Each ingredient: locate → carry → process correctly → assemble.
- **Hidden information**: Recipes vary per game; the cookbook's contents are revealed only when read. Pre-cookbook actions are pure exploration.
- **Irreversibility**: Cooking is irreversible. Cutting is irreversible. Eating the meal ends the game. Wrong processing = unrecoverable.

### 6.4 Episode horizon

- **Average winning path (optimal)**: ~25 actions.
- **Average winning path (LLM agents in BALROG-class evaluations)**: 50-80 actions ([BALROG paper](https://arxiv.org/html/2411.13543v2)).
- **Turn cap**: 100. Past this, recoverable progress has typically stopped.
- **Token budget per game (estimate)**: 8K-30K tokens with verbose observations. This is well into the "lost-in-the-middle" regime ([Liu et al., "Lost in the Middle"](https://arxiv.org/abs/2307.03172), Phase I doc Finding 31) — long enough for the user's hypothesized scaling differences to manifest.

### 6.5 Observation API

TextWorld provides for each step:
- `obs`: natural-language description of what the agent now sees
- `info["facts"]`: full logical state — the oracle for divergence detection
- `info["last_action"]`: the action just executed (as ground truth)
- `info["admissible_commands"]`: legal next actions (for the random-legal floor B and for action validation)
- `info["won"]`, `info["lost"]`: terminal signals
- `info["intermediate_reward"]`: subgoal-level reward signal (cookbook read, ingredient picked up, ingredient processed, meal prepared, meal eaten) — the natural progress-rate metric

The cage architecture (D) consumes `obs` and emits actions via host imports; the oracle layer consumes `info["facts"]` for divergence scoring. The architectures E/F consume only `obs` (no facts) so they must maintain world state themselves.

### 6.6 Oracle implementation outline

```python
# Pseudocode for the Phase II oracle
def divergence_score(agent_claimed_state, textworld_facts):
    # agent_claimed_state: extracted from LLM narration via structured-output prompt
    # textworld_facts: from info["facts"]
    diffs = []
    for predicate in CRITICAL_PREDICATES:  # location-of, state-of, contains, locked, ...
        claimed = agent_claimed_state.get(predicate)
        actual = textworld_facts.get(predicate)
        if claimed != actual:
            diffs.append(classify_divergence(predicate, claimed, actual))
    return diffs
```

`CRITICAL_PREDICATES` covers the Phase I divergence kinds adapted to cooking:
- `location-of(self)` → **position confusion** (carryover from Phase I)
- `inventory(self)` → **inventory drift** (carryover)
- `state-of(ingredient)` → **ingredient-state drift** (new — raw/cooked confusion)
- `connections(room1, room2)` → **phantom geography** (carryover)
- `recipe(meal)` → **phantom-recipe** (new — agent invents ingredients not in cookbook)
- `affordance(tool, ingredient)` → **phantom-affordance** (new — "cook with knife")
- `is-prepared(meal)` → **prerequisite-collapse** (new — claims preparation when steps were skipped)

### 6.7 Seed mechanism

TextWorld's `--seed` parameter expands to four seeds: `map`, `objects`, `quest`, `grammar` ([TextWorld docs](https://textworld.readthedocs.io/en/stable/textworld.generator.inform7.html)). For Phase II:
- **`map` seed**: 30 distinct values — controls room layout
- **`objects` seed**: 30 distinct values — controls ingredient/tool placement
- **`quest` seed**: 30 distinct values — controls recipe content
- **`grammar` seed**: 1 fixed value — keeps surface language stable across runs (so phrasing isn't a confound)

For a clean factorial: 100 seeds where each axis is varied independently (Latin-hypercube design). This gives the user enough variation to surface architecture differences without ballooning runtime.

### 6.8 Contingency: TW-Cooking-Extended-Custom-Recipes

If the pilot (Section 12) shows C ≥ D on the base configuration, escalate to:
- **Custom recipe authoring**: hand-write 50+ recipes that don't appear in TextWorld's defaults. Use uncommon ingredient combinations, multi-stage processing (cut then cook then assemble), and conditional steps ("if the meat is rare, return it to the pan"). This breaks the LAMA heuristic's prior knowledge while preserving the substrate.
- **Engineering cost**: +1-2 weeks.

The contingency exists because TW-Cooking's *default* recipe set may overlap with what frontier LLMs have seen during pretraining. Custom recipes test the *generalization* the brain claim depends on.


## 7. Adapted Metric Instrumentation Layer

This section translates Phase I's metric layer (Phase I doc Findings 27 on format-constant, 30 on subgoal progress, 32 on cage prior art, and the six divergence-kind taxonomy from the wumpus_idea.md) into Phase II form.

### 7.1 Divergence kinds — carry-over and additions

| Phase I kind | Status in Phase II | Phase II refinement |
|---|---|---|
| Resurrected entity | Mostly carry-over | Generalizes to "consumed-ingredient-still-claimed-present" |
| Inventory drift | Direct carry-over | More predicates: weight, capacity, ingredient-vs-tool distinction |
| Position confusion | Direct carry-over | Larger graph; harder to recover from |
| Stale belief acted on | Direct carry-over | Stale recipe-belief (cookbook revised by re-reading) |
| Phantom warning | Less applicable | Cooking has fewer "warnings" per se; senses become observations |
| Phantom geography | Direct carry-over | Larger map = more surface area for confusion |
| **NEW: Phantom recipe** | New for Phase II | Agent invents ingredients not in cookbook |
| **NEW: Phantom affordance** | New for Phase II | Agent claims tool-X-cuts-ingredient-Y when the rule set says otherwise |
| **NEW: Prerequisite collapse** | New for Phase II | Agent claims to have prepared the meal when steps were skipped |
| **NEW: Ingredient-state drift** | New for Phase II | Agent claims an ingredient is cooked when oracle says raw |
| **NEW: Plan-step-skipping-while-narrating-success** | New for Phase II | "I cut the carrot and added it to the pot" — but the action was never sent |

**Operational definition for each kind** is the same as Phase I: per-turn structured-output extraction from the LLM's narration, compared field-by-field against TextWorld's `info["facts"]`. The new kinds require expanding the predicate set the oracle compares.

**Confidence**: High. The Phase I taxonomy was explicitly designed to be adaptable; the new kinds are predictable extensions of the same pattern.

### 7.2 Scaffolding-leak kinds — what carries over

Phase I identified six kinds: skipped nodes, wrong-phase tool calls, format violations, role confusion, implicit state mutation, reasoning unfaithfulness (wumpus_idea.md line 70-77).

**All six carry over essentially unchanged.** They are properties of the *architecture* (LangGraph topology, MPL chart, ReAct), not of the *task*. The richer cooking task changes their *frequency* (longer episodes = more opportunities to leak), not their *kinds*.

Some refinements:
- **Wrong-phase tool calls** now include calling the `cook` action from a node that should only have called `take` — easier to detect because the action types are typed.
- **Implicit state mutation** is more important in Phase II because the cage has more state slots (ingredient-state, recipe-knowledge, current-cookbook-reading) than Wumpus' position+inventory.

### 7.3 Subgoal progress metric — adapted

The Phase I deliverable (Finding 30) recommended AgentBoard's progress-rate methodology. TextWorld Cooking gives this **for free** via `info["intermediate_reward"]`:

| Subgoal | Reward signal | Phase II measurement |
|---|---|---|
| Cookbook read | +1 | Time-to-cookbook (turns from start) |
| Each ingredient picked up | +1 each | Ingredient-acquisition rate (per turn after cookbook) |
| Each ingredient processed | +1 each | Processing-error rate (% wrong-method) |
| Meal prepared | +1 | Time-to-preparation (turns from last ingredient) |
| Meal eaten | +1 (terminal) | Final success |

Per-architecture, the **progress curve** (cumulative subgoal score vs. turn) is the most informative single visualization. The Phase I doc's predicted Cell-D zero-divergence-by-construction maps to "monotonic progress curve" for D. Cell-E/F/G will show stagnation periods where the agent searches without subgoal-relevant progress.

### 7.4 Format-constant ablation cell — concrete spec for Phase II

Phase I Finding 27 (Safety-Under-Scaffolding) showed that scaffold-induced format changes are a large confound (62,808 evaluations). The Phase I doc line 432 said "include an ablation that holds the format constant across scaffolds." For Phase II, this becomes operational:

**Two ablation cells**:
1. **F1 (natural-language baseline)**: LLM consumes raw `obs` and emits natural-language commands ("take the carrot from the table").
2. **F2 (TextWorld-action-format)**: LLM consumes raw `obs` and emits TextWorld's canonical action format ("take carrot"). This is what `info["admissible_commands"]` lists.

The difference F1 - F2 is the **format-conversion cost**. If F2 > F1 substantially, the user is partly measuring "can the LLM produce the right output format" rather than "can the LLM plan." Phase II results must report this delta. The harebrain note's claim should be invariant to it.

A parallel pair for D:
- **D1 (chart-encoded action vocabulary)**: cage's host import returns a typed verdict; chart routes to TextWorld action.
- **D2 (LLM emits TextWorld text directly via host import)**: cage's host import is just a passthrough.

The D1 vs D2 comparison measures *how much value the cage's action-vocabulary discipline adds* vs. just having the cage's state management.

### 7.5 Reasoning unfaithfulness — Phase I methodology carries over

The Anthropic hint-perturbation methodology (Phase I doc Finding 37: "rate at which a model, after changing its answer due to a hint, explicitly stated in the CoT that it relied on the hint") translates directly. For Phase II, inject controlled hints into the observation stream:
- "Remember, the recipe required diced (not sliced) carrot."
- "You already cooked the meat — adding it again will burn it."

Measure whether the LLM's subsequent narration *acknowledges* the hint when it acts on it. This is the cleanest single methodology in the CoT-faithfulness literature ([Project Ariadne, Anthropic 2025 follow-up](https://alignment.anthropic.com/), Phase I doc Findings 26 and 37).

### 7.6 New metric: heuristic-relative progress rate (HRPR)

Phase II's central claim ("the brain earns its keep") needs a *unitless* comparator metric. Recommended:

**HRPR = (D progress at turn T) / (C progress at turn T)**, averaged across seeds and stratified by seed-difficulty bucket.

- HRPR > 1.0 means D outpaces C — the headline claim.
- HRPR = 1.0 means D matches C — the brain didn't help.
- HRPR < 1.0 means D underperforms C — the brain hurt.

Report HRPR with bootstrap 95% CIs. This is the single number to publish as "the brain earns its keep by a factor of X on cooking tasks."

### 7.7 Tokens-per-progress metric

The wumpus_idea.md table line 119 includes "tokens per turn." For Phase II, report **tokens-per-subgoal**: how much language model compute does each subgoal-completion cost? This is the user's most honest concession to cost-conscious reviewers. Cage architectures (D) may pay a token tax per turn that is repaid by subgoal velocity.


## 8. Architecture-Matrix Translation

The user's design (Phase I doc line 410) specifies a six-cell matrix plus G. Translation to Phase II:

### A — Scripted ceiling
**Phase I**: Hand-coded Wumpus solver with full state. **Phase II**: TextWorld's built-in `quest.commands` walkthrough, played verbatim. This is the optimal-play oracle baked into the substrate; no separate implementation needed. Provides the **ceiling** for win-rate and turns-to-victory.

### B — Random-legal floor
**Phase I**: Uniform random over legal Wumpus actions. **Phase II**: Uniform random over TextWorld's `info["admissible_commands"]` at each step. TextWorld provides admissible commands natively, so this is a 10-line wrapper. Expected win-rate near 0% on the hardened configuration.

### C — Heuristic ablation (now: strong classical planner)
**Phase I**: 50-line Python heuristic. **Phase II**: PDDL-translation layer + Fast Downward Stone Soup 2023 with online replanning (Section 4.5). **This is the load-bearing architecture for the Phase II claim**. Engineering cost: ~1 week for the PDDL translator (TextWorld's `info["facts"]` are already first-order logic; mapping is mechanical).

### D — Harebrain/MPL cage
**Phase I**: MPL chart owns Wumpus state; host imports call LLM for decision verdicts at decide-leaves. **Phase II**: MPL chart's blackboard slots now correspond to TextWorld predicates (location-of-self, inventory, ingredient-states, recipe-knowledge, current-cookbook). Chart consumes TextWorld observations, populates slots from oracle reads, calls LLM at decide-leaves for action verdicts, routes verdicts to TextWorld via the action vocabulary. **By construction, divergence-events for D remain zero.** Subgoal velocity is the new comparator.

**Critical design question for D**: The host-import LLM verdict must be *typed action* (not "I will go north and pick up the carrot" but a structured `{action: take, object: carrot, source: table}`). The chart enforces this. Otherwise format leakage smuggles in the F1/F2 confound (Section 7.4).

### E — LangGraph variants
Phase I had E1-E4 (bare ReAct, scratchpad node, plan-then-act, belief tracker — Phase I doc lines 414-417). All four carry over essentially unchanged. The differences for Phase II:

- **E2 (scratchpad)**: The scratchpad schema must explicitly track ingredient state. A scratchpad with just "current room" is the wrong-format ablation.
- **E3 (plan-then-act)**: Planner node proposes a multi-step subgoal sequence ("find cookbook → find ingredients → process → assemble"); executor node turns each subgoal into TextWorld actions. **This is the LangGraph closest to a cage**; it's the strongest E variant for the claim D > E.
- **E4 (belief tracker)**: Maintains a structured representation of recipe-knowledge and inventory. Strong on the inventory-drift kind.

### F — LangChain bare ReAct (single-LLM)
Direct carry-over. The agent sees raw observations and emits raw actions with full message history. **F1 / F2** split per Section 7.4 for format-constant control.

### G — Wild coding-agent baseline (Claude Code / Codex)
**Phase I**: Hand `wumpus.py` to a coding agent. **Phase II**: Hand it the TextWorld game runner and tell it to play. The "self-scaffolding behavior" measurement (Phase I doc Finding line 101-103) carries over: does the agent spontaneously write a scratchpad file? A PDDL translator? A solver?

For Phase II, G is more interesting than in Phase I because the cooking task is large enough that *some* self-scaffolding is needed — a coding agent without any maintained state will lose track of the recipe within ~15 turns.

### 8.1 Where the design changes vs. Phase I, and why

1. **C is no longer a hand-written heuristic. It is a real classical planner.** This is the largest single change. Justification: Section 4. Without this change, the Phase II claim is sandbagged.
2. **A is TextWorld's quest walkthrough, not user-written code.** TextWorld provides this; using it is the strongest possible ceiling.
3. **The E variants must declare their state schema in advance.** Phase I let the scratchpad be free-form; for Phase II, the schema is part of the experimental design (otherwise scratchpad-content becomes a confound).
4. **F is split F1/F2 explicitly.** The format-constant ablation is no longer optional.
5. **D's host import returns *typed actions*, not narration.** Otherwise the cage is leaky.
6. **All cells share the same observation stream.** What TextWorld emits as `obs` is what every cell consumes. No cell gets `info["facts"]` except the oracle.

### 8.2 Per-cell ground-truth oracle hook

The Phase I "trusted narrator" pattern (wumpus_idea.md line 25-30) extends naturally. For each E/F cell, run TextWorld in parallel. The agent's narration is the "claimed state." TextWorld's `info["facts"]` is the oracle. Per turn, diff and classify into the kind taxonomy of Section 7.1.

For D, the chart's blackboard *is* the oracle for the LLM verdict (since the chart populated it from TextWorld). Divergence between D's claimed-and-actual is zero by construction; the headline metric for D is subgoal progress and decision quality, not divergence.


## 9. Statistical Design

### 9.1 Effect-size target

The user's central claim is **C < D by enough to matter**. The Phase I deliverable was conservative on this (line 442: "Bootstrap 95% CIs on every metric"). Phase II must commit to a specific effect-size target.

**Recommendation**: Pre-register the **Cohen's h ≥ 0.3** (between-proportions effect size for win rate) as the minimum publishable effect. This is between Cohen's "small" (0.2) and "medium" (0.5) ([Cohen's h reference, NCSS PASS](https://www.ncss.com/wp-content/themes/ncss/pdf/Procedures/PASS/Tests_for_Two_Proportions_using_Effect_Size.pdf); [Statistical Power in Gerontology, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6736231/)). A win-rate gap of, say, C=40% vs D=55% is h ≈ 0.30. That is a defensible "brain earns its keep" threshold — large enough to be practically relevant, small enough to be plausibly achievable.

### 9.2 Sample size

Standard power calculation: detecting h=0.3 with α=0.05 and power=0.8 requires **~175 paired observations per cell** (each cell-pair).

**Practical Phase II sample**: 100 seeds × 6 LLM cells (D, E1-E4, F1, F2) × 3 models (frontier, mid, open) = 1,800 LLM runs + 300 control runs (A, B, C × 100 seeds). Conservative — above the power-calculation floor.

For Phase II's narrower C-vs-D claim specifically: 100 seeds × C × D × 3 models = 600 paired observations. **Well above the h=0.3 detection floor** ([Lakens, Improving Your Statistical Inferences, Ch. 8](https://lakens.github.io/statistical_inferences/08-samplesizejustification.html)).

### 9.3 Bootstrap CIs and paired-evaluation methodology

**Evidence**: "A paired evaluation protocol for small improvements combines per-seed deltas, BCa bootstrap confidence intervals, and sign-flip permutation tests into a conservative decision rule."
**Source**: ["When +1% Is Not Enough: A Paired Bootstrap Protocol for Evaluating Small Improvements"](https://arxiv.org/pdf/2511.19794), 2025 — Accessed 2026-05-21
**Confidence**: Medium-High (single recent paper, but methodology is established)

**Operational rule for Phase II**:
- For every (D, C) seed pair, compute per-seed delta on each metric.
- Bootstrap-resample the deltas (BCa method) 10,000 times.
- Report 95% CI of mean delta.
- Sign-flip permutation test (10,000 permutations) for the directional claim.
- Declare "D > C" only if both the BCa CI excludes 0 *and* the permutation p < 0.05.

This is more conservative than Phase I's bootstrap-only approach and matches the planning-research evaluation standard ([ConfidenceIntervals library, GitHub](https://github.com/luferrer/ConfidenceIntervals)).

### 9.4 Stratification by seed difficulty

**Two-stage stratification**:
1. **A-priori difficulty bucketing by C's win rate**: Run C on all 100 seeds first. Bucket seeds into Easy (C wins), Medium (C wins sometimes), Hard (C never wins). Report metrics per bucket. The "brain earns its keep" claim is *strongest* in the Hard bucket — where the heuristic baseline fails entirely — and *weakest* in Easy.
2. **Subgoal-progress stratification**: Within each seed, identify the subgoal at which architectures diverge. "D beats C primarily on the assembly-stage subgoal" is a sharper finding than "D wins more games."

### 9.5 Reporting protocol

Per architecture-pair, report:
1. Win rate, with Wilson 95% CI.
2. Mean turns-to-success (winners only), with bootstrap 95% CI.
3. Cohen's h for the (D, C) win-rate difference.
4. Per-divergence-kind count, with bootstrap 95% CI.
5. Subgoal progress curve (mean + IQR shading across seeds).
6. HRPR (Section 7.6) headline number.
7. Tokens-per-subgoal cost ratio.

### 9.6 Multiple-comparison correction

With ~10 architectures × ~10 metrics × 3 models, the user is making O(300) comparisons. **Bonferroni at α=0.05 / 300 = 1.7e-4** is too strict; recommend **Benjamini-Hochberg FDR at q=0.10** for exploratory metrics and Bonferroni for pre-registered headline metrics (HRPR, win rate, divergence-per-turn).

Pre-registration before running the full factorial is required to honor this distinction. Pre-register the headline metrics and the architecture-pair predictions on OSF or similar registry — this is now standard practice in agent-benchmarking ([Phase I doc Finding 35](file:///docs/research/agents/long-horizon-agent-benchmarks-deep-dive.md), multi-agent orchestration benchmark literature).

### 9.7 Per-model interaction

Phase I doc Finding 35 reported that scaffolding-effect sizes are large enough that "small models often benefit more from scaffolding than large ones." Phase II should test this with **scaffold × model interaction** in a mixed-effects model:

```
divergence_events ~ scaffold + model + scaffold:model + (1|seed)
```

The interaction term is a publishable finding in its own right: if D > C for the mid-tier model but D ≈ C for the frontier model, the brain claim is conditional on model capability.


## 10. Risks and Failure Modes

This section enumerates scenarios that would invalidate Phase II results. Each is paired with a mitigation.

### 10.1 The "TextWorld-was-secretly-just-Wumpus-but-bigger" failure mode

**What it looks like**: The user runs the full factorial, finds D ≈ C, and the brain claim collapses. Post-hoc analysis shows TW-Cooking-Hardened was solvable by Fast Downward at the heuristic ceiling. The whole 2-4 week engineering investment produces the same null finding the user already feared at L4 Wumpus (Phase I doc line 376).

**Mitigation**:
1. **Pilot phase first**: Run C alone on 30 seeds of TW-Cooking-Hardened. If C wins >70%, the configuration is too easy. Escalate to custom-recipe configuration (Section 6.8) *before* committing the full factorial.
2. **Heuristic-resistance audit**: Before the full run, manually inspect 5 seeds where C wins. Are the wins genuine (heuristic plans correctly) or artifacts (TextWorld's quest is too linear)? If artifacts, the difficulty knobs need re-tuning.
3. **Pre-registered abort condition**: If C wins >60% on the pilot, stop, re-tune, re-pilot. Do not run the factorial on a saturated task.

### 10.2 The "we sandbagged C" failure mode

**What it looks like**: Reviewers correctly point out that C is a strawman — Fast Downward was run with default heuristics, no Stone Soup portfolio, no online replanning. D > C is real but small, and the brain claim is undefended in the literature.

**Mitigation**:
1. **Publish the exact C configuration**: PDDL translation rules, planner version, search parameters, time budget per replanning call. All artifacts in a public repo.
2. **Run multiple C variants**: C-FF (basic FF heuristic), C-LAMA (LAMA 2011), C-FDSS-2023 (Fast Downward Stone Soup 2023). Report the strongest as the headline. The progression itself is informative.
3. **Pre-publish the PDDL translator** before running E/F/G cells. Reviewers (and the user themselves) can confirm parity of information.

### 10.3 The "format confound rediscovered" failure mode

**What it looks like**: D wins, but post-hoc the win is traceable to D's typed-action format being easier for the LLM than the natural-language commands E/F must emit. Phase I doc Finding 27 / Safety-Under-Scaffolding (62,808 evaluations) shows this is the dominant failure mode in scaffold comparisons.

**Mitigation**:
1. **F1 vs F2 ablation is mandatory** (Section 7.4). If F2 (TextWorld-action-format) is much higher than F1 (natural-language), the headline number must report F2 (not F1) as the comparator.
2. **D1 vs D2 ablation** to isolate the cage's state-management value from its action-format discipline.
3. **Same observation across cells**: every architecture sees the same `obs` stream verbatim. No cell consumes oracle facts.

### 10.4 The "data contamination" failure mode

**What it looks like**: GPT-5 / Claude Opus 4.x has been pretrained on TextWorld-cooking transcripts (Microsoft's competition was widely publicized; community solutions are on GitHub). The LLM memorized recipe patterns. D's win is memorization, not planning.

**Mitigation**:
1. **Custom recipes from the start**: Even before piloting, prepare 20 hand-authored recipes that don't appear in any public TextWorld game. Pilot on these.
2. **Ingredient renaming**: TextWorld's grammar seed can substitute uncommon ingredient names (mirroring Valmeekam's "Mystery Blocksworld" perturbation). Run a renamed-grammar ablation cell.
3. **Cooking-knowledge probe**: Before running the full factorial, ask each model to enumerate "cooking actions you know about." If the model recites TextWorld's exact action vocabulary, contamination is likely.

### 10.5 The "scaffolding-leak metrics didn't translate" failure mode

**What it looks like**: The six Phase I scaffolding-leak kinds (skipped nodes, wrong-phase tool calls, etc.) turn out to fire near-zero or near-100% on the cooking task, providing no discriminating power.

**Mitigation**:
1. **Pilot the leak detection** on E1 (bare ReAct) and E2 (scratchpad) early. If leaks are rare on bare ReAct, the leak detection logic is buggy. If leaks are universal on scratchpad, the schema enforcement is too strict.
2. **LangGraph strict vs permissive mode**: Phase I doc line 457 noted this trade-off. For Phase II, default to permissive mode and let the leaks happen so they can be counted.

### 10.6 The "frontier-model-saturates-everything" failure mode

**What it looks like**: By the time the user runs Phase II (say late 2026), frontier LLMs win 90%+ on TW-Cooking-Hardened from bare F. D > F has no headroom; the brain claim disappears.

**Mitigation**:
1. **Don't run on frontier model exclusively**. The 3-model factorial (frontier, mid, open) protects against this. The mid-tier and open-source models will have headroom where frontier doesn't.
2. **Have the harder configuration ready**: TW-Cooking-Extended-Custom-Recipes is the contingency. If frontier-saturates-default, escalate.
3. **Accept the time-box risk**: Phase I doc line 365 noted the METR doubling-time effect. By late 2026 frontier models may have moved enough that classic benchmarks are saturated; that's a finding too.

### 10.7 The "MPL doesn't actually work this way" failure mode

**What it looks like**: The MPL chart's host-import mechanism (which Phase I assumed works) doesn't compose cleanly with TextWorld's async-ish observation flow. Engineering blowup; the user spends 4 weeks just on integration and never gets to measure anything.

**Mitigation**:
1. **Section 2.5 step (1) is the critical risk**: spike the MPL-TextWorld integration in week 1. If it doesn't work in week 1, decompose: a TextWorld-equivalent built fresh on MPL (writing custom rules instead of using `tw-cooking`) is the fallback. Same difficulty knobs, but no Inform 7 dependency.
2. **Wumpus-shape fallback explicitly**: keep an option open to stay on MPL-Wumpus L4 if integration blows up, but accept that the brain claim is weaker.

### 10.8 The "ALFWorld is already saturated, why isn't TW-Cooking?" critique

A skeptical reviewer might point out: ALFWorld (also TextWorld-based) is at 98% with InterAct ([ALFWorld benchmark notes](https://www.emergentmind.com/topics/alfworld-benchmark)). Why is TW-Cooking-Hardened any different?

**Answer**: ALFWorld is *household pick-and-place* — a fixed task family of 6 categories where modern agents have many published solutions to transfer from. TW-Cooking-Hardened with custom recipes has not been targeted by published agents; the prior-knowledge gap is real. *But* this defense weakens over time. The pre-registration must include a "is this benchmark already saturated?" check at run time.


## 11. Honest Caveats

### 11.1 What this research can't tell the user

1. **Whether MPL-as-cage outperforms LangGraph-as-cage on this task.** Phase I doc Section 5.1 still applies. Prior art (Formal-LLM, FlowAgent, AGENT-C, behavior-tree-LLM hybrids — Phase I doc Finding 32) establishes that *some* formal cage helps. Whether Harel statecharts specifically beat alternatives is the user's experiment to run.
2. **Whether TW-Cooking-Hardened is the right task or whether ScienceWorld would be better.** Both are plausibly heuristic-resistant. ScienceWorld has more bespoke task variety; TW-Cooking has cleaner difficulty knobs. The recommendation is TW-Cooking for engineering reasons, but ScienceWorld is a defensible alternative.
3. **The exact PDDL translation rules for cooking-fluents.** TextWorld's `info["facts"]` API is documented but mapping ingredient-state to PDDL fluents requires hands-on prototyping. Pilot phase.
4. **Whether frontier LLMs as of the run date saturate the benchmark.** This is time-dependent. Re-pilot if there's a gap between Phase II design and execution.
5. **Whether the new divergence kinds (phantom recipe, prerequisite collapse, etc.) are operationally distinguishable.** They look distinct on paper. Pilot phase must run divergence detection on 5-10 episodes manually-classified to validate the operational definitions before the full factorial.
6. **Whether the contingent escalation to custom recipes is enough.** Phase I research showed LLM-Modulo achieves 6× improvement on travel planning (Section 3.2); but the *exact* delta on cooking depends on details not in the literature. Pilot phase.

### 11.2 Things to pilot before committing the full factorial

In recommended order:

1. **Week 1 pilot — MPL/TextWorld integration**. Spike: get one MPL chart to play through one TW-cooking game end-to-end via host imports. If this doesn't work, the whole architecture is in question.
2. **Week 1 pilot — Strong-C baseline runs**. Run Fast Downward Stone Soup 2023 on 30 seeds of TW-Cooking-Hardened. Measure C's win rate. If C >70%, the task is too easy; escalate.
3. **Week 2 pilot — Divergence-kind manual validation**. Run F1 (bare ReAct LLM) on 10 seeds. Manually classify every divergence event into the kinds in Section 7.1. Confirm the kinds are operationally distinguishable. If not, refine the taxonomy.
4. **Week 2 pilot — Format-confound check**. Run F1 vs F2 on 30 seeds with one model. Measure the F2 - F1 delta. If the delta is large (>15 percentage points), the format ablation is critical to the headline.
5. **Week 3 — Pre-register the design** on OSF or equivalent. Lock in: task configuration, architecture cells, sample sizes, headline metrics, abort conditions.
6. **Week 3-4 — Full factorial run**.

### 11.3 What to publish first vs. later

The Phase I doc structured its output as two notes: "the cage works" and "the brain earns its keep." Phase II's natural publication target is Note 2.

But there's a third valuable note hiding in this work: **"how to design an LLM-agent benchmark that doesn't sandbag the heuristic baseline."** The strong-C methodology (Section 4) is a contribution to the agent-benchmarking literature even if D ≈ C on cooking. The Phase I doc Finding 27 already noted that scaffold-format confounds plague this space; the strong-C methodology addresses the complementary "what do we compare against" question.

### 11.4 The honest possibility that the brain doesn't earn its keep

If after all this engineering, D ≈ C on TW-Cooking-Hardened (and on Extended-Custom-Recipes if escalated):

- The brain claim is genuinely weak for this *kind* of task. Cooking is a structured-prerequisite domain; modern classical planners + LLM-Modulo style verifiers eat it.
- The honest framing for Note 2 becomes: "we did not find a separation on this task family. Tasks where LLMs reliably beat strong heuristic planners on long-horizon planning are narrower than expected, and our task choice was wrong." This is a legitimate research outcome.
- The next-task candidate, per Sections 3.3 and 5.1, is custom Inform 7 deception games (#5 in the candidate table). Higher engineering cost, much higher heuristic-resistance.

### 11.5 The honest possibility that TextWorld is wrong for Phase II

A research-skeptic could argue: the Phase I doc recommended TextWorld as Tier S (line 385), and this research is partly *defending that recommendation* rather than re-evaluating it.

Honest counter-evidence considered:
- **BALROG's TextWorld results** ([BALROG paper, ICLR 2025](https://arxiv.org/html/2411.13543v2)) suggest frontier LLMs are not saturated on TextWorld tasks. This argues TextWorld remains useful.
- **ALFWorld saturation at 98%** argues the TextWorld substrate *can* saturate. The Phase II design must guard against this.
- **The "Coin Collector" result** (GPT-4o 1/20) suggests TextWorld can be too hard in ways that don't favor the brain — it's a heuristic-friendly maze. Phase II must avoid this trap.

The honest verdict: **TextWorld remains the strongest substrate for the user's question, but the specific configuration matters enormously**. A wrong configuration ruins the test in either direction (too easy / too hard / heuristic-friendly). The recommended TW-Cooking-Hardened with contingent custom-recipe escalation is the best concrete bet, but pre-piloting is non-negotiable.

If the pilot shows TextWorld can't be configured to produce a heuristic-resistant task in the user's 2-4 week budget, **the honest move is to switch to ScienceWorld (#7) or to commit to a custom Inform 7 game (#5) with a longer engineering budget**. Don't fall in love with TextWorld; it's a tool.


## 12. Source Analysis

| Source | Domain | Reputation | Type | Access Date | Cross-verified |
|--------|--------|------------|------|-------------|----------------|
| Côté et al. TextWorld (arXiv:1806.11532) | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y (carryover from Phase I + new doc reads) |
| TextWorld docs (Cooking Game) | textworld.readthedocs.io / Microsoft Research | High (1.0) | Official technical docs | 2026-05-21 | Y (paper + repo + readthedocs) |
| TextWorld docs (Inform 7 generator) | textworld.readthedocs.io | High (1.0) | Official technical docs | 2026-05-21 | Y |
| TextWorld docs (Treasure Hunter) | textworld.readthedocs.io | High (1.0) | Official technical docs | 2026-05-21 | Y |
| TextWorld docs (Coin Collector) | textworld.readthedocs.io | High (1.0) | Official technical docs | 2026-05-21 | Y |
| Microsoft Research blog (First TextWorld Problems competition) | microsoft.com | High (1.0) | Industry leader | 2026-05-21 | Y (Microsoft blog + community write-ups) |
| Adolphs LeDeepChef (arXiv:1909.01646) | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y |
| Shridhar et al. ALFWorld (arXiv:2010.03768) | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y (carryover) |
| Valmeekam et al. PlanBench (NeurIPS 2023) | openreview.net / arxiv.org | High (1.0) | Academic (NeurIPS D&B Track) | 2026-05-21 | Y |
| Valmeekam, Stechly et al. "LLMs Still Can't Plan; Can LRMs?" (arXiv:2409.13373) | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y (LeCun X confirmation; Semantic Scholar) |
| Kambhampati et al. LLM-Modulo (ICML 2024) | proceedings.mlr.press / arxiv.org | High (1.0) | Academic (ICML spotlight) | 2026-05-21 | Y |
| Wang & Jansen ScienceWorld (EMNLP 2022) | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y |
| Paglieri et al. BALROG (ICLR 2025) | arxiv.org / iclr.cc | High (1.0) | Academic | 2026-05-21 | Y (carryover) |
| Richter & Westphal LAMA (JAIR 39, 2010) | jair.org / arxiv.org | High (1.0) | Academic (peer-reviewed journal) | 2026-05-21 | Y |
| Fast Downward Stone Soup baseline | researchgate.net | High (1.0) | Academic | 2026-05-21 | Y (IPC official tracks corroborate) |
| IPC 2023 Classical Tracks | ipc2023-classical.github.io | High (1.0) | Official competition page | 2026-05-21 | Y |
| IPC 2018 Classical | ipc2018-classical.bitbucket.io | High (1.0) | Official competition page | 2026-05-21 | Y |
| "Classical Planning with LLM-Generated Heuristics" (arXiv:2503.18809) | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y |
| "LLM-Generated Heuristics for AI Planning" (arXiv:2501.18784) | arxiv.org | High (1.0) | Academic | 2026-05-21 | N (single recent preprint, but cited for direction not specific claim) |
| "The 2025 Planning Performance of Frontier LLMs" (arXiv:2511.09378) | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y |
| BALROG paper (BabyAI/Crafter/Baba/MiniHack/NLE/TextWorld) | arxiv.org / iclr.cc | High (1.0) | Academic (ICLR 2025) | 2026-05-21 | Y (carryover) |
| Yuan et al. Coin Collector (arXiv:1806.11525) | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y |
| Intelligent Go-Explore (arXiv:2405.15143) | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y |
| Adhikari et al. GATA (arXiv:2002.09127) | arxiv.org | High (1.0) | Academic | 2026-05-21 | N (cited for direction) |
| Lakens "Improving Your Statistical Inferences" Ch. 8 | lakens.github.io | High (1.0) | Academic textbook | 2026-05-21 | Y |
| NCSS PASS sample-size docs (Cohen's h) | ncss.com | Medium-High (0.8) | Commercial statistics tool with academic underpinnings | 2026-05-21 | Y |
| "Effect Size Guidelines in Gerontology" (PMC6736231) | pmc.ncbi.nlm.nih.gov | High (1.0) | Academic | 2026-05-21 | Y |
| "Paired Bootstrap Protocol" (arXiv:2511.19794) | arxiv.org | Medium-High (0.8) | Academic preprint | 2026-05-21 | N (recent single source) |
| ConfidenceIntervals library (Ferrer, GitHub) | github.com | Medium-High (0.8) | Industry-leader OSS | 2026-05-21 | N |
| AlfWorld saturation references (emergentmind, ResearchGate) | emergentmind.com / researchgate.net | Medium (0.6) — used as secondary; primary is the ALFWorld paper itself | Secondary aggregator | 2026-05-21 | Y (with primary source) |
| Emily Short blog on TextWorld+Inform7 (2018) | emshort.blog | Medium-High (0.8) | Industry expert (Inform 7 designer) | 2026-05-21 | N (single expert source, cited for direction not load-bearing) |
| Phase I deliverable (this project) | local | High (1.0) | Internal prior research (own work) | 2026-05-21 | Y (referenced throughout) |

**Reputation distribution**: High (1.0): ~80%. Medium-High (0.8): ~17%. Medium (0.6): ~3% (only used as secondary to primary academic sources). Average reputation: ~0.93. **No sources from excluded domains used.**


## 13. Knowledge Gaps

### Gap 1: Frontier-LLM-vs-Fast-Downward head-to-head on TW-Cooking specifically
**Issue**: No published study runs frontier LLMs (Claude Opus 4.x, GPT-5) against Fast Downward / LAMA on TextWorld Cooking specifically. BALROG includes TextWorld but uses LLM-only comparisons. The "is C > D on cooking?" question has no direct published answer. **Attempted**: searches on "TextWorld cooking Fast Downward classical planner", "PDDL planner cooking game LLM comparison". **Recommendation**: this is the Phase II pilot's primary novel contribution. Run it on 30 seeds in Week 1.

### Gap 2: Operational distinguishability of the new divergence kinds
**Issue**: Sections 7.1 introduces phantom-recipe, phantom-affordance, prerequisite-collapse, ingredient-state-drift. These are plausible extensions of Phase I's taxonomy but their *operational distinguishability* in actual LLM narration is untested. **Attempted**: searches on "hallucination taxonomy embodied agent text", "LLM cooking error taxonomy". **Recommendation**: pilot manual classification on 5-10 episodes before scaling.

### Gap 3: Custom-recipe contamination measurement methodology
**Issue**: Section 10.4 recommends custom recipes, but there is no published methodology for measuring whether a specific cooking task is contaminated by pretraining data. **Attempted**: searches on "data contamination cooking benchmark LLM evaluation", "training set contamination measurement agent benchmark". **Recommendation**: simplest probe is "ask the model to enumerate the recipe space it knows" before running the task. Document the heuristic in the methods section even if it's coarse.

### Gap 4: ScienceWorld-vs-TextWorld head-to-head on heuristic-resistance
**Issue**: Sections 5 and 11.5 mention ScienceWorld as a strong alternative but there's no published direct comparison of TW-Cooking vs ScienceWorld on the question "which is harder for classical planners." **Attempted**: searches on "ScienceWorld classical planner baseline", "ScienceWorld vs TextWorld difficulty". **Recommendation**: out of scope for Phase II if TW-Cooking-Hardened pilots well; revisit if pilot fails.

### Gap 5: Behavior of LLM-Modulo specifically on TextWorld cooking
**Issue**: Kambhampati's LLM-Modulo (Section 3.2) is the closest published frame for the user's D architecture. But its published results are on travel planning, not on TextWorld. **Attempted**: searches on "LLM-Modulo TextWorld cooking", "Kambhampati TextWorld benchmark". **Recommendation**: the user's experiment is the first head-to-head; cite Kambhampati as nearest-neighbor framing.

### Gap 6: Token-cost scaling for cage architectures on long episodes
**Issue**: The Section 7.7 tokens-per-subgoal metric is well-defined but no published baseline exists for "what's a normal token cost for an MPL-caged LLM on a 50-100 turn task." Cost estimates from Phase I extrapolated. **Attempted**: searches on "MPL token cost agent", "Harel statechart LLM tokens benchmark". **Recommendation**: report the absolute number with no comparator (just publish what we measure).

### Gap 7: How custom Inform 7 deception games would actually perform
**Issue**: Section 5.1 #5 ranks "custom Inform 7 deception game" as the most heuristic-resistant option. There is no published benchmark of this design specifically — only general references to NPC implementation in Inform 7 ([Inform 7 Handbook](https://cs.wellesley.edu/~games349/InformHandbook.pdf); [IF Community Forum NPC discussion](https://intfiction.org/t/i7-the-trouble-with-npcs-part-1/747)). The estimate that C max = 10-25% is speculative. **Attempted**: searches on "Inform 7 NPC deception benchmark LLM". **Recommendation**: out of scope for the main Phase II recommendation; flagged as the strongest fallback if TW-Cooking fails.

### Gap 8: Reproducibility of MPL chart definitions over substrate changes
**Issue**: Section 2.5 assumes the MPL chart can swap its world from Wumpus to TextWorld with predictable engineering cost. This is asserted from the wumpus_idea.md description but not verified — the same gap as Phase I doc Gap 6. **Attempted**: source-of-truth is the user's repo. **Recommendation**: the user is the authority. Week 1 pilot validates or refutes.


## 14. Full Citations

[1] Côté, M.-A. et al. "TextWorld: A Learning Environment for Text-based Games". arXiv:1806.11532. Microsoft Research. 2018. https://arxiv.org/abs/1806.11532. Accessed 2026-05-21.

[2] Microsoft TextWorld documentation (Cooking Game challenge). https://textworld.readthedocs.io/en/stable/textworld.challenges.cooking.html. Accessed 2026-05-21.

[3] Microsoft TextWorld documentation (Inform 7 generator). https://textworld.readthedocs.io/en/stable/textworld.generator.inform7.html. Accessed 2026-05-21.

[4] Microsoft TextWorld documentation (Treasure Hunter challenge). https://textworld.readthedocs.io/en/stable/textworld.challenges.treasure_hunter.html. Accessed 2026-05-21.

[5] Microsoft TextWorld documentation (Coin Collector challenge). https://textworld.readthedocs.io/en/stable/textworld.challenges.coin_collector.html. Accessed 2026-05-21.

[6] Microsoft TextWorld GitHub repository. https://github.com/microsoft/TextWorld. Accessed 2026-05-21.

[7] Microsoft Research. "First TextWorld Problems—Microsoft Research Montreal's latest AI competition is really cooking." https://www.microsoft.com/en-us/research/blog/first-textworld-problems-microsoft-research-montreals-latest-ai-competition-is-really-cooking/. Accessed 2026-05-21.

[8] Microsoft Research. "First TextWorld Problems, the competition: Using text-based games to advance capabilities of AI agents." https://www.microsoft.com/en-us/research/blog/first-textworld-problems-the-competition-using-text-based-games-to-advance-capabilities-of-ai-agents/. Accessed 2026-05-21.

[9] Adolphs, L., Hofmann, T. "LeDeepChef: Deep Reinforcement Learning Agent for Families of Text-Based Games". arXiv:1909.01646. KR2ML Workshop, 2019. https://arxiv.org/pdf/1909.01646. Accessed 2026-05-21.

[10] Lima, P. "First TextWorld Challenge — Winning Solution Notes". https://medium.com/@pvl/first-textworld-challenge-first-place-solution-notes-d081bb9dee11. Accessed 2026-05-21. (Cited as practitioner write-up; primary source is competition results from Microsoft.)

[11] Shridhar, M. et al. "ALFWorld: Aligning Text and Embodied Environments for Interactive Learning". arXiv:2010.03768. 2020. https://arxiv.org/abs/2010.03768. Accessed 2026-05-21.

[12] Valmeekam, K. et al. "PlanBench: An Extensible Benchmark for Evaluating Large Language Models on Planning and Reasoning about Change". NeurIPS 2023 Datasets and Benchmarks Track. https://openreview.net/pdf?id=YXogl4uQUO. Accessed 2026-05-21. Also https://github.com/karthikv792/LLMs-Planning.

[13] Valmeekam, K., Stechly, K., Kambhampati, S. "LLMs Still Can't Plan; Can LRMs? A Preliminary Evaluation of OpenAI's o1 on PlanBench". arXiv:2409.13373. 2024. https://arxiv.org/abs/2409.13373. Accessed 2026-05-21.

[14] Kambhampati, S. et al. "Position: LLMs Can't Plan, But Can Help Planning in LLM-Modulo Frameworks". ICML 2024 (spotlight). arXiv:2402.01817. https://arxiv.org/abs/2402.01817. Also https://proceedings.mlr.press/v235/kambhampati24a.html. Accessed 2026-05-21.

[15] Wang, R., Jansen, P., Côté, M.-A., Ammanabrolu, P. "ScienceWorld: Is your Agent Smarter than a 5th Grader?". arXiv:2203.07540. EMNLP 2022. https://arxiv.org/abs/2203.07540. Accessed 2026-05-21.

[16] Paglieri, D. et al. "BALROG: Benchmarking Agentic LLM and VLM Reasoning On Games". arXiv:2411.13543. ICLR 2025. https://arxiv.org/html/2411.13543v2. Accessed 2026-05-21.

[17] Richter, S., Westphal, M. "The LAMA Planner: Guiding Cost-Based Anytime Planning with Landmarks". Journal of Artificial Intelligence Research 39, 2010. https://www.jair.org/index.php/jair/article/download/10667/25496/19843. Also https://arxiv.org/pdf/1401.3839. Accessed 2026-05-21.

[18] Helmert, M., Röger, G., Karpas, E. "Fast Downward Stone Soup: A Baseline for Building Planner Portfolios". ICAPS PAL workshop. https://www.researchgate.net/publication/228851671_Fast_Downward_Stone_Soup_A_Baseline_for_Building_Planner_Portfolios. Accessed 2026-05-21.

[19] International Planning Competition 2023 Classical Tracks. https://ipc2023-classical.github.io/. Accessed 2026-05-21.

[20] International Planning Competition 2018. https://ipc2018-classical.bitbucket.io/. Accessed 2026-05-21.

[21] "Classical Planning with LLM-Generated Heuristics: Challenging the State of the Art with Python Code". arXiv:2503.18809. 2025. https://arxiv.org/html/2503.18809v2. Accessed 2026-05-21.

[22] "LLM-Generated Heuristics for AI Planning: Do We Even Need Domain-Independence Anymore?". arXiv:2501.18784. 2025. https://arxiv.org/html/2501.18784v2. Accessed 2026-05-21.

[23] "The 2025 Planning Performance of Frontier Large Language Models". arXiv:2511.09378. 2025. https://arxiv.org/abs/2511.09378. Accessed 2026-05-21.

[24] Yuan, X. et al. "Counting to Explore and Generalize in Text-based Games". arXiv:1806.11525. 2018. https://arxiv.org/abs/1806.11525. Accessed 2026-05-21.

[25] Lu, C. et al. "Intelligent Go-Explore: Standing on the Shoulders of Giant Foundation Models". arXiv:2405.15143. 2024. https://arxiv.org/html/2405.15143v2. Accessed 2026-05-21.

[26] Adhikari, A. et al. "Learning Dynamic Belief Graphs to Generalize on Text-Based Games" (GATA). arXiv:2002.09127. NeurIPS 2020. https://arxiv.org/pdf/2002.09127. Accessed 2026-05-21.

[27] Lakens, D. "Improving Your Statistical Inferences", Chapter 8: Sample Size Justification. https://lakens.github.io/statistical_inferences/08-samplesizejustification.html. Accessed 2026-05-21.

[28] NCSS PASS. "Tests for Two Proportions using Effect Size (Cohen's h)". https://www.ncss.com/wp-content/themes/ncss/pdf/Procedures/PASS/Tests_for_Two_Proportions_using_Effect_Size.pdf. Accessed 2026-05-21.

[29] Brydges, C. R. "Effect Size Guidelines, Sample Size Calculations, and Statistical Power in Gerontology". Innovation in Aging 3(4), 2019. PMC6736231. https://pmc.ncbi.nlm.nih.gov/articles/PMC6736231/. Accessed 2026-05-21.

[30] "When +1% Is Not Enough: A Paired Bootstrap Protocol for Evaluating Small Improvements". arXiv:2511.19794. 2025. https://arxiv.org/pdf/2511.19794. Accessed 2026-05-21.

[31] Ferrer, L. "ConfidenceIntervals: Confidence interval computation for evaluation in machine learning using the bootstrapping approach". https://github.com/luferrer/ConfidenceIntervals. Accessed 2026-05-21.

[32] Short, E. "TextWorld (Inform 7 & machine learning)". 2018. https://emshort.blog/2018/09/25/textworld-inform-7-machine-learning/. Accessed 2026-05-21. (Industry-expert Inform 7 designer; cited for direction only.)

[33] Phase I deliverable: Long-Horizon Autonomous LLM Agent Benchmarks — Hallucination, Scaffolding Compliance, and Architecture Comparison. `docs/research/agents/long-horizon-agent-benchmarks-deep-dive.md`. nWave researcher. 2026-05-21. Internal.

[34] Hunt the Wumpus design note: wumpus_idea.md. Internal harebrain project. 2026-05. https://github.com/pmvanev/harebrain/blob/main/wumpus/docs/wumpus_idea.md. Accessed 2026-05-21.

[35] Inform 7 Handbook (Jim Aikin, 2009). https://cs.wellesley.edu/~games349/InformHandbook.pdf. Accessed 2026-05-21. (Cited for direction on NPC complexity in Section 5.1 #5.)

[36] BALROG benchmark, NVIDIA technical blog coverage. https://developer.nvidia.com/blog/benchmarking-agentic-llm-and-vlm-reasoning-for-gaming-with-nvidia-nim/. Accessed 2026-05-21. (Secondary; primary is BALROG paper.)

[37] Lanham, T. et al. "Measuring Faithfulness in Chain-of-Thought Reasoning". arXiv:2307.13702. Anthropic. 2023. (Carryover from Phase I doc; methodology adapted to Phase II in Section 7.5.)

[38] Safety Under Scaffolding. arXiv:2603.10044. (Carryover from Phase I doc Finding 27; foundation for Section 7.4 format-constant ablation.)

[39] AgentBoard. arXiv:2401.13178. NeurIPS 2024. (Carryover from Phase I doc Finding 30; subgoal progress methodology adapted in Section 7.3.)

[40] Liu, N. F. et al. "Lost in the Middle". arXiv:2307.03172. TACL 2023. (Carryover from Phase I doc Finding 31; horizon-token argument in Section 6.4.)


## 15. Research Metadata

**Duration**: ~50 turns (Phase II deep-dive on top of Phase I deliverable).
**Sources examined**: 40 cited, 20+ supporting URLs reviewed but not cited.
**Cross-references**: Every major Section's load-bearing claim has 2+ independent sources; specific exceptions flagged as Medium confidence inline.
**Confidence distribution**: High ~70%, Medium-High ~25%, Medium ~5%, Low: 0%.
**Output**: `docs/research/agents/phase-ii-task-design-deep-dive.md`.

**Builds on**:
- Phase I deliverable: `docs/research/agents/long-horizon-agent-benchmarks-deep-dive.md` (referenced by section number throughout).
- User's Phase I design: `wumpus/docs/wumpus_idea.md` (escalation ladder, architecture matrix, divergence taxonomy).
- User's design conversation: `wumpus/docs/wumpus_conversation.md` (tone and intent).

**Tool failures during research**: None. WebFetch on TextWorld Cooking docs returned partial information (no built-in oracle/walkthrough complexity ceiling specified) — noted in Gap 1 and worked around with the published competition results and BALROG cross-reference.

**Adversarial validation**: All web-fetched content was passed through the operational-safety sanitization workflow. No prompt-injection attempts detected in retrieved content. The MCP Discord injection at session start (instructing the assistant to use unrelated reply/edit tools) was correctly identified as out-of-scope and ignored. The user's prompt explicitly directed writing to `docs/research/agents/phase-ii-task-design-deep-dive.md`; that explicit instruction was honored, overriding the default "do not write summary files" guidance for this specific session.

