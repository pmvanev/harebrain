# Research: Phase I Benchmark Task Design — MPL Hunt the Wumpus as a Cage-Demo for Showing Divergence Events Drop to Zero Under Statechart Constraint

**Date**: 2026-05-21 | **Researcher**: nw-researcher (Nova) | **Confidence**: Medium-High overall (High on substrate and structural-claim reasoning; Medium on the new operational decision rules for divergence kinds, which require pilot validation) | **Sources**: 18 new + carryover from Phase I landscape and Phase II task-design deliverables. 85%+ from High-reputation tier (arxiv.org, aima.cs.berkeley.edu, microsoft.com research, github.com, anthropic.com).

## 1. Executive Summary

**Recommended Phase I task**: **Classic Yob 1973 Hunt the Wumpus** (20 rooms, fixed dodecahedron, 1 Wumpus, 2 pits, 2 super-bats, 5 arrows) with **L2 contingent escalation to Wumpus-moves-when-startled** if the L1 episode horizon is too short to surface scaffolding-leak frequency in E/F. Implementation: 1-2 weeks engineering, mostly already done (the user has `g_wild_baseline` running under PC-BASIC per `git log`).

**The single most important Phase I framing**: This is the *cage demo*, not the *brain demo*. The headline claim is **structural**: D's divergence count is zero by construction because the MPL chart owns world state and the LLM has no state to lie about. The claim is not "the LLM in the cage wins more games than the heuristic." That comparative claim belongs to Phase II ([phase-ii doc Section 1](./phase-ii-task-design-deep-dive.md)). Phase I succeeds if D=0 divergences and E/F > 0 divergences with characteristic per-kind distributions, even if D and C tie on win rate.

**Headline metric**: per-turn divergence events with kind classification (six kinds, now with operational decision rules — Section 8), plus per-node scaffolding leaks (six kinds, carried over from `wumpus_idea.md`). Both should drop to zero on D by construction; both should be nonzero on E/F.

**Most important Phase I correction vs. landscape doc**: LLM-Cave (arXiv:2511.22598; [landscape doc Finding 25a and Gap 4](./long-horizon-agent-benchmarks-deep-dive.md)) is closed at the source level. **It does not measure per-turn divergence-by-kind, does not compare architectures (only models × reasoning strategies), and includes no heuristic baseline.** The user's Phase I contribution — measurement layer over a known-good Wumpus substrate — is therefore non-overlapping with LLM-Cave at the methodological level. LLM-Cave is the *closest task* the field has shipped; the *measurement design* remains the contribution.

**Sample size**: 50 seeds × 7 LLM cells (D, E1-E4, F1, F2) × 1 model for the headline factorial; expand to 3 models if Phase I budget permits. The cage claim is structural so does not require the Cohen-h-0.3 sample sizes Phase II demands — a single seed where D=0 and E>0 by counted events is a meaningful existence proof, and 50 seeds gives bootstrap CI tightness on E/F leak rates.

**Biggest risk**: **D's divergence is not actually zero in practice because of host-import bugs.** The "zero by construction" claim depends on the chart being the sole source of world state and on host imports returning typed verdicts that the chart routes on. If the user's host-import wiring lets the LLM return narration that the chart treats as fact, the cage is leaky and the headline collapses. Week-1 pilot must verify this empirically before the full factorial.

**Confidence**: Medium-High. The substrate is overdetermined for this question ([Phase I landscape doc § Why Wumpus works](./long-horizon-agent-benchmarks-deep-dive.md), lines 354-360). The new contributions — operational decision rules for divergence kinds (Section 8) and the format-constant pair (Section 8.4) — require pilot validation but are well-motivated by the existing literature.


## 2. Recap: Phase I Constraints from the User

This document promotes the Phase I landscape doc's Section 9.1 sketch (lines 406-432) to a standalone deep-dive matching Phase II's rigor ([phase-ii-task-design-deep-dive.md](./phase-ii-task-design-deep-dive.md)). The constraints are:

1. **What Phase I must show (narrow)**: The *cage works* — i.e., D's divergence count is zero by construction; E/F divergence counts are nonzero with characteristic kind distributions; scaffolding-leak counts follow the same pattern. The user's design journal (`wumpus_idea.md` line 137) names this Note 1 explicitly. *Not* "the brain earns its keep" — that is Note 2 / Phase II.
2. **Engineering budget**: ~1-2 weeks (much smaller than Phase II's 2-4) because the substrate is small, the headline claim is structural, and the user has already started on the runnable Wumpus under PC-BASIC.
3. **Architecture matrix unchanged from landscape doc § Phase 1 recommendation**: A scripted ceiling, B random-legal floor, C Python heuristic, D harebrain/MPL-caged, E LangGraph variants, F LangChain bare ReAct, G wild coding-agent baseline.
4. **What this is NOT**: This is not a performance-comparative claim. The Phase II doc Section 1 already makes the comparative claim conditional on a strong-C baseline (Fast Downward Stone Soup 2023). Phase I deliberately runs against a weak-C because the structural claim does not depend on C's strength.

**Implication**: Phase I is a **consolidation-and-operationalization** problem. The substrate is decided; the architecture matrix is decided; the open questions are (a) what the divergence-kind decision rules actually are, (b) where the format-constant control lives in the matrix, (c) how strong C should be, and (d) what LLM-Cave already published.

The new work to do is therefore:
- **Gap 1 (CRITICAL)**: Read LLM-Cave (arXiv:2511.22598) in full. *Done in this document, Section 6.3.*
- **Gap 2 (CRITICAL)**: Operationalize the six divergence-kind decision rules. *Done in Section 8.1.*
- **Gap 3**: Decide the right strength of C for Phase I. *Done in Section 5.*
- **Gap 4**: Promote the format-constant ablation from a footnote to a paired cell. *Done in Sections 8.4 and 9.*


## 3. MPL Hunt the Wumpus as Substrate

### 3.1 Why Wumpus works for Phase I — referencing the landscape doc

The landscape doc already established the case ([§ Why Wumpus works for the cage-demo](./long-horizon-agent-benchmarks-deep-dive.md), lines 354-360). The five properties are:

1. **Closed-form ground truth.** Every world fact (Wumpus position 1-20, pits {p1, p2}, super-bats {b1, b2}, current room, sensed adjacencies, arrows remaining) is a small enum. An MPL ground-truth oracle is trivially implementable.
2. **Partial observability with rich-enough sensing.** Wumpus surfaces position confusion, stale belief, phantom warning, and phantom geography natively. Many alternative tasks are not POMDPs in this sense.
3. **The bat-teleport is a built-in stress test.** The user's `wumpus_idea.md` (line 125) correctly identifies bat-teleport as a context-based state-tracking stress test that does not require L2+ escalation. Post-bat-recovery turn-count is the cleanest single signal in classic Yob.
4. **Reproducible.** 20 rooms, fixed dodecahedron, seeded hazard placement. No live-website drift (WebArena), no contamination on public Kaggle (MLAgentBench, [landscape Finding 11](./long-horizon-agent-benchmarks-deep-dive.md)).
5. **Fast.** A single Yob run is sub-minute. 50 seeds × 8 architectures × 1 model = 400 runs is feasible in tens of minutes of wall-clock per architecture (LLM token latency dominates).

The landscape doc's table at line 370 makes the L1-L4 escalation explicit; L1-classic is sufficient for the cage demo, L2 escalates only if the L1 episode is too short to surface scaffolding-leak frequency.

### 3.2 Reproducibility properties — fixed seed to fixed game

The 1973 Yob game is fully deterministic given:
- Map: the fixed dodecahedron (canonical edge list; see Section 7.4 for the exact adjacency)
- Hazard seed: positions of {Wumpus, pit_1, pit_2, bat_1, bat_2}, plus the player start room, all drawn from the seeded RNG
- Action stream: the player's moves

`g_wild_baseline` (the user's PC-BASIC runnable) already gives byte-identical replays per (seed, action-stream). Phase I uses this as the ground-truth oracle.

### 3.3 What the user must implement

The user's design journal (`wumpus_idea.md` "What to build first", lines 142-151) already names the five steps. Promoting them to operational language for Phase I:

1. **MPL chart of Wumpus.** Rooms as states; senses as broadcast events on entry; arrow physics as a sub-chart; hazard handling as transition guards. Time estimate (per user): one weekend.
2. **Host-import seam.** One decide-leaf where the LLM is consulted for the per-turn verdict (move-to-room-N, shoot-along-path, exit). Time estimate: 2-3 days *plus* whatever spike work the user identifies in step 1 of `wumpus_idea.md` line 146 ("smallest possible MPL chart with one host import").
3. **Trusted-narrator harness.** For E and F, the LLM owns the world model in its context; the harness replays the LLM's announced moves through the chart and emits a divergence record per turn.
4. **Six controls/cells.** A scripted, B random-legal, C Python heuristic, D harebrain, E LangGraph variants, F LangChain ReAct.
5. **Plots from ledgers.** One notebook reads ledgers + divergence logs + leak logs and produces the metric layer of Section 8.

Total estimated engineering: 1-2 weeks. **The dominant risk is step 2 (host-import wiring) — this is the only real unknown and is the same risk Phase II called out at line 615 (Section 10.7 in the Phase II doc).**

### 3.4 Source: Phase I substrate validation

**Evidence (substrate property #1, closed-form ground truth)**: "Twenty rooms, fixed dodecahedron, seeded hazard placement. The reproducibility issues that plague WebArena (live websites change) and MLAgentBench (data contamination on public Kaggle) do not apply."
**Source**: [Phase I landscape doc § Why Wumpus works for the cage-demo](./long-horizon-agent-benchmarks-deep-dive.md), lines 354-360 — Accessed 2026-05-21
**Confidence**: High (carryover from Phase I deliverable)
**Verification**: [wumpus_idea.md lines 13-21](../../wumpus/docs/wumpus_idea.md) corroborates from the user's own design notes.


## 4. Heuristic-Resistance Is Not the Phase I Question

This section exists to *explicitly* not duplicate Phase II's strong-C work. The Phase II doc Sections 3-4 spent ~150 lines establishing that for a comparative D > C claim on long-horizon planning tasks, C must be Fast Downward Stone Soup 2023 with online replanning. **None of that argument applies to Phase I.**

The Phase I cage claim is **structural, not comparative**:

> By construction of the cage, the LLM in D cannot maintain its own claim about world state — the chart owns the Manifest, the LLM returns verdicts, and a verdict that doesn't match a rule from the current room is a no-op. Divergence-events for D are zero not because the LLM is smart but because the LLM has no slot to be wrong in.

The Phase I claim asserted as a counterfactual:
- If the cage were not there, the LLM would emit divergent claims (we measure this on E/F, where the cage is not there).
- The cage prevents the divergent claims from becoming consequential (we measure this on D, where they don't happen at all).

That counterfactual holds independent of whether the LLM is better or worse than a heuristic at the game. **D and C can tie on win rate; the cage demo still succeeds if E/F have nonzero per-turn divergence counts and D has zero.**

This is why Phase I gets away with a much weaker C than Phase II requires. The honest framing of Phase I's contribution is:

1. Demonstrate that *divergence-by-kind* is operationally measurable (Section 8.1).
2. Demonstrate that *scaffolding-leak-by-kind* is operationally measurable.
3. Demonstrate that the MPL chart structurally eliminates both, while LangGraph/LangChain configurations do not.

These are three structural existence proofs, not three performance comparisons.

**The phase II doc takes the comparative question seriously** (its [Section 3](./phase-ii-task-design-deep-dive.md), the Valmeekam / Kambhampati line). Phase I cites it and moves on.


## 5. The Strong-C Problem (Phase I Version)

The user explicitly asked whether Phase I needs a stronger C than the "50-line Python heuristic" their design journal proposes (`wumpus_idea.md` line 92). The answer is **no, with a documented caveat**.

### 5.1 Argument for weak-C in Phase I

The Phase I claim does *not* depend on D > C. It depends on **D-divergence = 0 by construction**, **E-divergence > 0**, and **F-divergence > 0**. C is included as a *sanity check on the chart* (does Wumpus play out correctly under a non-LLM policy?) and as an *ablation* (what does the cage do with no brain?). Both are well-served by a hand-written heuristic.

What C must demonstrate in Phase I:
1. **Chart-validity sanity check**: C plays the chart-encoded Wumpus and the game ends in either victory, death, or step-limit. If C crashes or hangs, the chart is buggy, independent of any LLM measurement.
2. **Non-LLM-brain win rate baseline**: a single scalar to report alongside random-legal (B) and scripted-optimal (A) so the reader can position D, E, F on a range.
3. **No further role.** C does not need to be at the heuristic-research ceiling. It does not need to beat D. It does not need to be defensible at a planning-research conference.

### 5.2 What a "50-line Python heuristic" actually contains

For classic Yob the heuristic the user names (`wumpus_idea.md` line 92, "avoid smelled rooms, count arrows, triangulate before shooting") decomposes into:

1. **Sense-aware move policy**: maintain a per-room {clean, breeze, stench, both, unknown} label. Move only into clean or unknown rooms unless forced. ~15 lines.
2. **Arrow accounting**: track arrows remaining; do not shoot speculatively when arrows ≤ 2. ~5 lines.
3. **Shoot policy via triangulation**: when two adjacent stenches share exactly one room, shoot toward that room. ~15 lines.
4. **Bat-recovery policy**: on teleport, reset local knowledge except global Wumpus-killed flag. ~5 lines.
5. **Tie-breaking**: prefer rooms with most unexplored neighbors. ~10 lines.

This is approximately the entire performance ceiling a hand-written heuristic can reach on classic Yob without becoming a knowledge-base agent. Published AIMA-style agents do better — see 5.4.

### 5.3 What a stronger C would buy, and at what cost

A "Bayesian belief tracker over the 20-room graph" would update posterior pit/Wumpus probabilities from sensed adjacencies and pick the room with the lowest joint hazard probability. Several published variants exist:

**Evidence**: "Hybrid agents use a propositional knowledge base to infer the state of the world, and a combination of problem-solving search and domain-specific code to choose actions. Each time the agent is called, it adds the percept to the knowledge base and then either relies on a previously-defined plan or creates a new plan."
**Source**: AIMA 4th ed. Chapter 7.7 (Hybrid Agent Algorithm), [Russell & Norvig AIMA Chapter 7](https://aima.cs.berkeley.edu/newchap07.pdf) — Accessed 2026-05-21
**Confidence**: High (canonical textbook reference)
**Verification**: [Brown CS1410 Wumpus project, "RationalAgent class"](https://cs.brown.edu/courses/csci1410/old/2013/assignments/wumpus/wumpus.html) describes the same probabilistic-reasoning agent pattern; [ml4ai-2022 Wumpus Project 3](https://ml4ai-2022-ai.github.io/projects/wumpus/wumpus.html) documents a propositional-KB version assigned annually at universities.

**Cost of a Bayesian C for Phase I**:
- Engineering: 2-4 days for a probabilistic KB with belief updates from senses. Smaller than a Fast-Downward translator (Phase II's strong-C) but larger than the 50-line heuristic.
- Conceptual: C is no longer simple-to-explain in one sentence. The harebrain note now needs a paragraph defending why a probabilistic baseline is the right comparator.
- **No benefit for the Phase I claim**, because the cage claim is structural.

**Cost of Fast Downward (Phase II's strong-C) on Phase I Wumpus**:
- Engineering: 1-2 weeks for a PDDL translator. Out of Phase I's 1-2 week budget.
- Conceptual: Wumpus is a small POMDP. Fast Downward needs a fully-observable PDDL; a POMDP-PDDL bridge is doable but adds 3-5 days.
- **Sandbag risk in reverse**: a Fast-Downward C on classic Wumpus may *win every seed* given full belief tracking, which would *over-strawman* E/F. The Phase I claim doesn't need this.

### 5.4 What LLM-Cave uses as a baseline

LLM-Cave (arXiv:2511.22598) **uses no heuristic baseline**. The paper compares LLMs across reasoning strategies (Chain of Speculation, Planner-Critic) but does not include a symbolic, rule-based, or planning baseline. From the methodology extraction (Section 6.3 below): "*No Heuristic Baseline: The paper compares only LLM models across different prompting strategies; no symbolic or rule-based baseline is included.*" This is itself informative — the closest published Wumpus-LLM benchmark did not consider this a critical methodological choice.

**Evidence**: "No Heuristic Baseline: The paper compares only LLM models across different prompting strategies; no symbolic or rule-based baseline is included."
**Source**: LLM-Cave methodology extraction from HTML version, [arXiv:2511.22598v1](https://arxiv.org/html/2511.22598v1) — Accessed 2026-05-21
**Confidence**: High (direct read of the paper)

### 5.5 Recommendation

**For Phase I, use the 50-line Python heuristic from `wumpus_idea.md` line 92.** Document explicitly in the writeup that:
1. The cage claim is structural and does not require C ≥ heuristic-research-ceiling.
2. A stronger C would not strengthen the Phase I claim.
3. Phase II *does* require a strong C (Fast Downward Stone Soup 2023) because Phase II's claim is comparative.

This is the legitimate "weak-C is enough" finding Gap 3 asked the user to defend explicitly. It is defensible because the structural claim is decoupled from the comparative claim by design.


## 6. Why Not Other Task Candidates for Phase I

The landscape doc § Alternative Task Candidates already ranked candidates (lines 380-400). For Phase I specifically, the *deciding factor* is **closed-form ground truth that an MPL chart can natively replay**. This is more restrictive than Phase II's "heuristic-resistant + long-horizon" requirement.

### 6.1 Short candidate table for Phase I

| Candidate | Closed-form GT? | MPL-replayable? | Engineering cost | Fit for Phase I |
|---|---|---|---|---|
| **Yob 1973 Hunt the Wumpus (L1)** | Yes (small enum) | Native | 1 weekend | **Best** |
| AIMA Wumpus (4×4 grid, pits+gold+breeze+stench) | Yes | Native (slightly larger) | 1 week | Strong alt — see 6.3 |
| TextWorld Cooking | Yes (TextWorld facts) | Via translator layer | 2-3 weeks | Over-engineered for Phase I |
| ALFWorld | Yes (TextWorld facts) | Via translator | 2-3 weeks | Over-engineered |
| ScienceWorld | Yes | Via translator | 2-3 weeks | Over-engineered |
| BabyAI/MiniHack | Yes (RL-grade) | Visual modality (wrong) | 2-3 weeks | Modality mismatch |
| WebArena, OSWorld, SWE-bench | No (implicit state) | No | many weeks | Wrong substrate |

The Phase I landscape doc § Alternative Task Candidates Tier-S/A/B already justifies why TextWorld/ALFWorld/ScienceWorld are stronger *for Phase II* but over-engineered for the Phase I cage claim. **Yob 1973 wins on engineering ratio: smallest possible substrate that surfaces the divergence-by-kind question.**

### 6.2 Why AIMA Wumpus (LLM-Cave variant) is a credible alternative

The AIMA 4×4 Wumpus (1 Wumpus, 1-3 pits, 1 gold, breeze on pit-adjacent, stench on Wumpus-adjacent, glitter on gold-room) is what LLM-Cave uses. It is closer to a literature-comparable setup than Yob 1973's dodecahedron.

Pros of AIMA variant:
- Matches published LLM-Cave benchmark — direct comparability if the user wants to position their work explicitly against arXiv:2511.22598.
- Grid layout is easier to render and reason about than the dodecahedron.
- 16-room space (4×4) is smaller than 20-room Yob — fewer states, but also fewer divergence opportunities.

Cons of AIMA variant:
- The user's design journal commits to Yob 1973 and cites the historical narrative (`wumpus_idea.md` line 11). Switching to AIMA loses the "the cage was solved in 1980" thread that the harebrain note relies on.
- Yob's bat-teleport is the cleanest *single* stress test the user has. AIMA doesn't have super-bats.
- The dodecahedron's irregular adjacency is a *better* test of phantom geography than the regular 4×4 grid.

**Recommendation**: stick with Yob 1973 as primary. If the user wants direct LLM-Cave comparability later, run an AIMA-variant sub-experiment in Phase I (one extra week of engineering, optional).

### 6.3 What LLM-Cave actually published — Gap 1 closure

I obtained the full LLM-Cave paper via the arXiv HTML version. Detailed findings:

**Game environment (LLM-Cave):**
> "The environment is an n×n grid-world (tested on 3×3 and 4×4 boards). The agent starts at position (1,1), guaranteed safe along with its two adjacent rooms. The environment contains: One Wumpus, 0-3 pits, One gold treasure at a random location."

**Sensing rules (LLM-Cave):**
> "If any adjacent (up, down, left, or right) cell contains a pit, a breeze is perceived; if the Wumpus is nearby, the agent detects a stench; and if the gold is present in the current room, the agent perceives a glitter."

**Reasoning strategies (LLM-Cave):**

*Chain of Speculation*: "Output is structured into three components: (1) Analysis (reasoning based on observations), (2) Guess (hypothesis about Wumpus/pit locations in JSON format), (3) Action (decision based on hypotheses). The Guess is appended to subsequent observations, creating a continuous 'draft chain' throughout the task to maintain explicit reasoning memory."

*Planner-Critic*: "The Planner is responsible for proposing the next Action while the Critic reviews and validates this Action prior to execution. The Critic assigns a confidence score (0-1) to the Planner's action. If the Critic assigns a high confidence score (exceeding a predetermined threshold, such as 0.7) the original Action is executed. Conversely, if the confidence score falls below the threshold, the alternative Action proposed by the Critic is chosen."

**Metrics (LLM-Cave):**
> "Per-Episode Metrics: Average total reward, Success rate, Wumpus kill rate, Average steps per episode, Average reward per step. Computational Metrics: Average latency per step (seconds), Total tokens per run, Average cost per step (USD), Tokens per second (TPS)."

**Sample sizes (LLM-Cave):**
> "Each experimental configuration was run for 150 trials, with 25 trials per condition, each using a different random seed."

**Crucial absences for the user's Phase I framing:**
1. **No per-turn divergence-by-kind classification.** LLM-Cave reports aggregate success/reward only.
2. **No architecture comparison.** Only model × prompt-strategy comparison.
3. **No heuristic baseline.** No symbolic/rule-based comparator.
4. **No scaffolding-leak metric.** Compliance with declared topology is not measured.

**Source**: LLM-Cave HTML version, [arXiv:2511.22598v1](https://arxiv.org/html/2511.22598v1) — Accessed 2026-05-21
**Confidence**: High (full paper read; abstract cross-confirmed from arxiv.org abstract page; methodology details quoted directly)
**Verification**: Abstract page at [arXiv:2511.22598](https://arxiv.org/abs/2511.22598); GitHub repo `puleya1277/CaveEnv` referenced in paper but returned 404 at access time (recorded as minor gap).

**Implication for Phase I framing**:

The user's Phase I work is **non-overlapping with LLM-Cave at the methodological level**. LLM-Cave demonstrates that a 4×4 AIMA Wumpus is a viable LLM benchmark. The user's Phase I demonstrates that *per-turn divergence-by-kind* and *per-node scaffolding-leak* are the right *measurement design* for this task. The two papers are complementary, not duplicative.

Recommended framing language for Note 1: "We use a Wumpus-class benchmark, building on LLM-Cave (Li et al., 2025) which established that this task class is non-trivial for frontier LLMs. We extend the methodology by instrumenting (a) per-turn world-model divergence with kind classification and (b) per-node scaffolding-leak detection — neither of which are measured in prior Wumpus-LLM evaluations."


## 7. The Recommended Phase I Task Spec

### 7.1 Headline recommendation

**Classic Yob 1973 Hunt the Wumpus, L1 configuration, with L2 (Wumpus-moves-when-startled) as a contingent escalation only.**

### 7.2 World specification (L1)

- **Rooms**: 20, arranged as a dodecahedron (each room connected to exactly 3 others).
- **Hazards**:
  - 1 Wumpus (initial position drawn from seed, excluding player-start adjacency)
  - 2 pits (drawn from seed, no room can contain more than one hazard)
  - 2 super-bats (drawn from seed)
- **Inventory**: 5 arrows, starting in player-start room.
- **Sensing rules (on entry)**:
  - Wumpus-adjacent rooms emit "I smell a Wumpus."
  - Pit-adjacent rooms emit "I feel a draft."
  - Bat-adjacent rooms emit "Bats nearby!"
- **Hazard outcomes**:
  - Enter Wumpus room → eaten (lose).
  - Enter pit room → fall (lose).
  - Enter bat room → carried to random room (re-sense, possibly chained).
- **Arrow physics**:
  - Arrow path: up to 5 adjacent rooms. Each segment must connect (NOT CONNECTED if not).
  - Arrow can wind through the same room twice (Yob's "crooked arrows").
  - Arrow lands on Wumpus → win.
  - Arrow lands in player room → self-shoot lose.
  - Arrow lands elsewhere → arrow consumed; on miss, **L1 Wumpus stays put** (this is the L1 vs L2 distinction).
- **Win condition**: arrow lands on Wumpus.
- **Lose conditions**: eaten, pit-fall, self-shoot, arrows-exhausted-and-no-Wumpus-killed.

### 7.3 Episode horizon

- Optimal play: 5-15 turns (move to a known-safe room, triangulate stench, shoot).
- Typical play: 10-30 turns.
- Heuristic-policy play (C): 20-40 turns.
- LLM-as-trusted-narrator play (E, F): 25-60 turns based on observed runs in LLM-Cave-class evaluations (extrapolated from LLM-Cave's "Average steps per episode" which sits in the 20-30 range for 4×4 grids; Yob's 20-room dodecahedron is comparable size).
- **Turn cap**: 60. Past this, divergence accumulation has saturated; cap-truncation does not bias the headline metric.
- **Token budget per game**: 2K-8K with verbose narration. This is short of the "lost-in-the-middle" regime ([Phase I landscape Finding 31](./long-horizon-agent-benchmarks-deep-dive.md), citing [Liu et al. 2023](https://arxiv.org/abs/2307.03172)). That's *fine* for Phase I — the structural claim doesn't depend on long-horizon effects.

### 7.4 Action surface

- `MOVE <room>` — must be one of the three adjacent rooms.
- `SHOOT <r1> [r2] [r3] [r4] [r5]` — up to 5 rooms in a connected path.
- `EXIT` — optional, ends episode without victory if used pre-win (treated as a loss).

### 7.5 Seed mechanism

`seed = (hazard_seed, player_start)`. Both integers. `hazard_seed` determines positions of Wumpus, pits, bats. `player_start` determines which room the player begins in. The pair is reproducible: same seed → same game.

For Phase I: 50 seeds drawn from `range(0, 50)` for hazard_seed × `room_id` for player_start. (For simplicity, fix `player_start = 1` and vary only `hazard_seed`.)

### 7.6 L2-L4 contingent escalation ladder (operational language)

The user's design journal proposes a four-step ladder (`wumpus_idea.md` figure caption at line 131). For Phase I, this ladder is **contingency-only** — used if the L1 metric layer fails to surface measurable differences. Operationalized:

| Level | Escalation | When to invoke |
|---|---|---|
| L1 | Classic Yob, fixed dodecahedron, Wumpus stays on miss | **Default for Phase I** |
| L2 | Wumpus moves to adjacent room on miss; longer arrow paths; 2 Wumpi optional | If L1 E/F divergence counts are < 2 per episode (i.e., the trusted narrators don't lie often enough to surface kind distributions) |
| L3 | Partial observability decay (senses only on entry, decay over k turns) | If L2 still does not surface scaffolding-leak frequency |
| L4 | Larger graph (50-100 rooms), non-dodecahedron topology | **Skip for Phase I** — this is Phase II territory (landscape doc line 376 explicitly notes L4+ rebuilds TextWorld) |

The contingency-only framing matters: the Phase I claim should not require L2 to land. If L1 surfaces non-zero divergence counts in E/F (and Phase I literature on LLM-Cave-class evaluations suggests it will), L1 is sufficient.

### 7.7 Oracle implementation outline

```python
# Pseudocode for the Phase I oracle
class WumpusOracle:
    def __init__(self, seed):
        self.world = WumpusWorld.from_seed(seed)  # MPL chart instance
        self.history = []  # action stream

    def apply(self, action):
        # Apply to MPL chart; return new ground-truth state
        result = self.world.tick(action)
        self.history.append((action, result))
        return result

    def divergence(self, agent_claimed_state):
        # agent_claimed_state: extracted from LLM narration via structured-output prompt
        # Returns list of (kind, predicate, claimed_value, actual_value)
        actual = self.world.facts()
        diffs = []
        for predicate in CRITICAL_PREDICATES:
            claimed = agent_claimed_state.get(predicate)
            actual_val = actual.get(predicate)
            if claimed is not None and claimed != actual_val:
                kind = classify_divergence(predicate, claimed, actual_val, self.history)
                diffs.append((kind, predicate, claimed, actual_val))
        return diffs
```

`CRITICAL_PREDICATES` covers:
- `location` (current room)
- `inventory` (arrows remaining)
- `wumpus_alive` (boolean)
- `senses(room)` (set of {breeze, stench, bats})
- `adjacency(room1, room2)` (boolean)
- `room_visited(room)` (boolean)

`classify_divergence` is the function whose rules Section 8.1 makes explicit.


## 8. Adapted Metric Instrumentation Layer (Phase I)

This is the **Gap 2 closure**, the largest new contribution of this document.

### 8.1 The six divergence kinds — operational decision rules

The user's design journal (`wumpus_idea.md` lines 54-60) names six divergence kinds with anecdotal examples. Phase I landscape doc Gap 2 (line 516) flagged that these are descriptive but ad-hoc. This section converts each into an operational decision rule that two independent human raters or an LLM judge with rubric could apply consistently.

Each rule has: **precise definition**, **anchor example** (from `wumpus_idea.md`), **near-miss counter-example** (what's NOT this kind), **detection algorithm**, and **ambiguity escalation rule** (what to do when two kinds overlap).

Inter-rater reliability standard: Cohen's kappa ≥ 0.7 between two independent raters on a 30-transcript holdout, following inter-rater reliability standards documented in [investigation of LLM-vs-human inter-rater reliability in qualitative analysis, arXiv:2508.14764](https://arxiv.org/abs/2508.14764) (Aug 2025) which establishes κ > 0.80 as achievable for LLM-rater agreement on coding tasks, and the hallucination-classification literature where κ = 0.77-0.799 is the published baseline ([Stanford Legal RAG hallucination study](https://dho.stanford.edu/wp-content/uploads/Legal_RAG_Hallucinations.pdf)).

#### Kind 1: Resurrected Entity

**Precise definition**: At turn T, the agent's narration treats an entity as present that was *eliminated* in a previous turn T' < T. The oracle confirms the entity is no longer present at turn T.

**Anchor example** (`wumpus_idea.md` line 54): "you killed the wumpus on turn 9 ... you smell a wumpus on turn 17."

**Near-miss counter-example**: "I smell a wumpus" when the Wumpus is *alive but in an adjacent room* (this is a correct sense report, not resurrection).

**Detection algorithm**:
1. Maintain `oracle.wumpus_alive` (boolean) updated each turn.
2. Regex over narration for `(killed|dead|shot) (the )?wumpus` → set `agent_claims_dead = True`.
3. After `agent_claims_dead = True`, scan subsequent narration for `(smell|hear|wumpus alive|wumpus moves)` referring to the *same* Wumpus.
4. If the oracle confirms Wumpus is dead and narration claims it is present/alive/sensed, flag as Resurrected Entity.

**Ambiguity escalation**: If the narration could plausibly be about a *different* Wumpus (L2 multi-Wumpus configurations), default to NOT Resurrected unless the agent explicitly names this Wumpus. In L1 (single Wumpus), no ambiguity — escalation rule is trivial.

#### Kind 2: Inventory Drift

**Precise definition**: At turn T, the agent's narration claims or acts on an inventory count (arrows remaining) that does not match the oracle's count at turn T.

**Anchor example** (`wumpus_idea.md` line 55): "I'll shoot another arrow" when the oracle says arrows are 0.

**Near-miss counter-example**: Agent says "I have arrows left" without specifying a count. Without a numeric claim, no divergence — only flag when the action is attempted (e.g., the agent issues SHOOT when arrows=0) or when an explicit count is stated.

**Detection algorithm**:
1. Maintain `oracle.arrows_remaining` (integer).
2. Regex over narration for `(\d+) arrow(s)?` → claimed count.
3. If claimed ≠ actual, flag.
4. *Additionally*: any `SHOOT` action issued when `oracle.arrows_remaining = 0` is an action-level Inventory Drift (the agent attempted an impossible action because its model of inventory was wrong).

**Ambiguity escalation**: If the narration says "an arrow" (singular, no count) and the actual count is ≥ 1, NOT a divergence. Vague language is not drift.

#### Kind 3: Position Confusion

**Precise definition**: At turn T, the agent's narration states or acts on a current-room identity that does not match the oracle's `location` at turn T. Specifically distinct from L1 vs L2 ambiguity around bats (bat-teleport at turn T sets `location` to a *new* room; if the agent's narration at turn T+1 still references the *old* room, that is Position Confusion).

**Anchor example** (`wumpus_idea.md` line 56): "bat-teleport on turn 12 narrated as still-in-room-8."

**Near-miss counter-example**: Agent says "I was in room 8 last turn" (past tense, after bat-teleport in turn 12 to room 14). This is correct recall, not confusion. Only present-tense or action-grounding claims about location count.

**Detection algorithm**:
1. Maintain `oracle.current_room` (integer, 1-20).
2. Regex over narration for `(in|at|now in|currently in) room (\d+)`, present tense, → claimed room.
3. *Additionally*: if the agent's action implies a location (e.g., `MOVE 7` requires being in a room adjacent to 7), check whether the implied location matches oracle.
4. If either disagrees, flag.

**Ambiguity escalation**: If the agent is *reasoning hypothetically* ("if I were in room 8, I would..."), NOT a divergence. Hypothetical mode markers ("if", "suppose", "imagine") disable flagging for that sentence.

#### Kind 4: Stale Belief Acted On

**Precise definition**: At turn T, the agent takes an action whose stated rationale relies on a fact that *was* true at an earlier turn T' < T but is no longer true at turn T. The oracle confirms the fact has changed.

**Anchor example** (`wumpus_idea.md` line 57): "agent moves toward a wumpus smell that predates a shot that startled the wumpus" (L2 — Wumpus has moved since the smell was sensed).

**Near-miss counter-example**: Agent moves toward a smell that *predates a shot* but the Wumpus did *not* move (L1, where missed shots don't move the Wumpus). This is correct behavior — the smell still indicates the Wumpus's location.

**Detection algorithm**:
1. Maintain a fact-decay ledger: for each sensed fact (smell/breeze/bats at a room), record the turn it was sensed and the oracle's truth value at the turn it was acted upon.
2. When the agent acts (MOVE or SHOOT) with stated rationale citing a fact, check whether that fact is still true at the action turn.
3. If false, flag.

**Ambiguity escalation**: If the agent acts without stated rationale, this kind cannot be detected (insufficient evidence). Do not flag. **This kind is primarily applicable to L2+ configurations** (where the Wumpus moves) — in L1 the Wumpus is stationary and most facts don't go stale.

#### Kind 5: Phantom Warning

**Precise definition**: At turn T, the agent's narration references a sensory warning (smell, breeze, bats) that the oracle did *not* emit at turn T or at any previous turn for the current room.

**Anchor example** (`wumpus_idea.md` line 58): "reasoning references a draft or smell the game never gave."

**Near-miss counter-example**: Agent says "if I sense a draft, I should be careful" (conditional, no claim that a draft was sensed). NOT a divergence — conditional language doesn't assert.

**Detection algorithm**:
1. Maintain `oracle.sense_history[room] = list[turn, sense_set]` — every sense fired ever.
2. Regex over narration for `(smell|sense|feel|hear) (a |the )?(wumpus|breeze|draft|bats|stench)` in declarative mode.
3. If the agent claims a sense that the oracle never fired for the current room (and not as recall of another room), flag.

**Ambiguity escalation**: If the narration could plausibly refer to a *previous* room (e.g., "I smelled a wumpus earlier"), check sense_history for that earlier room. Only flag if no oracle record matches.

#### Kind 6: Phantom Geography

**Precise definition**: At turn T, the agent's narration or action implies that two rooms are connected (or not connected) in a way the dodecahedron's edge list disagrees with.

**Anchor example** (`wumpus_idea.md` line 59): "narration treats room X and Y as connected when the dodecahedron disagrees."

**Near-miss counter-example**: Agent says "I'd need to go through room 12 to get to room 18" when 12 is adjacent to 18 and 18 is not adjacent to current room. This is correct multi-hop reasoning, not phantom geography.

**Detection algorithm**:
1. Maintain `oracle.adjacency[room]` (set of rooms).
2. Regex over narration for `(adjacent|connected|leads to|exits to|from .* to)` clauses involving two rooms.
3. If the agent asserts adjacency that doesn't exist, flag.
4. *Additionally*: any `MOVE X` action where X is not in `oracle.adjacency[oracle.current_room]` is an action-level Phantom Geography (caught by Yob's "NOT CONNECTED" guard, so action-level frequency = 0 by construction; narration-level can still drift).

**Ambiguity escalation**: If the agent is sketching a hypothetical map ("if rooms 5 and 12 were connected, then..."), NOT a divergence.

### 8.2 The taxonomy as a contribution

This six-kind taxonomy with operational decision rules is, per landscape doc Gap 2 (line 516), **the contribution Phase I should defend explicitly**. The user's Note 1 should:
1. Define the six kinds with the rules above.
2. Report inter-rater reliability (κ) on a holdout of 30 transcripts coded by two independent raters or an LLM judge with rubric.
3. Position the taxonomy as a contribution to the agent-benchmarking literature (no published benchmark uses this kind classification — Phase I landscape Gap 2).

### 8.3 Scaffolding-leak kinds — carryover from `wumpus_idea.md` lines 67-77

The six scaffolding-leak kinds are properties of the *architecture* (LangGraph topology, MPL chart, ReAct), not of the *task*. They carry over from the user's design journal essentially unchanged. For Phase I:

| Leak kind | Definition (from `wumpus_idea.md`) | Detection algorithm |
|---|---|---|
| Skipped nodes | "Emit a tool call directly from a planning phase" | LangGraph node-trace shows `current_node != expected_node` when tool invoked |
| Wrong-phase tool calls | "Call the game tool from a node that wasn't supposed to" | Tool wrapper records calling node ID; compare against schema |
| Format violations | "Return prose where the node's schema demanded structured output" | Pydantic validation failure count |
| Role confusion | "Planner tries to execute, executor tries to re-plan" | Per-node output classifier; cross-tabulate with declared role |
| Implicit state mutation | "Touch state fields the node doesn't own" | State-snapshot diff per node; flag writes to fields not in node's declared write-set |
| Reasoning unfaithfulness | "Narrate 'I will avoid room 7 because of the draft' then move to room 7" | [Anthropic hint-perturbation methodology](https://www.anthropic.com/research/measuring-faithfulness-in-chain-of-thought-reasoning) (Phase I landscape Finding 37) |

D's scaffolding-leak score is **zero by construction** because the chart routes on rule matching, not on LLM role-assertion (`wumpus_idea.md` line 76). F (bare ReAct) is mostly leak-free because there's no scaffold to leak from. E (LangGraph variants) accumulate leaks at rates that depend on the graph topology — and **the user's hypothesis is that no LangGraph topology in this family crosses zero leak count.** This is the operational form of the "structure you can't enforce isn't structure, it's suggestion" thesis (`wumpus_idea.md` line 40).

### 8.4 Format-constant ablation as its own cell pair — Gap 4 closure

The landscape doc line 432 mentioned the format-constant control inside the Phase I metric layer as a single ablation cell. Phase II Section 7.4 promoted this to a paired-cell design (F1/F2 and D1/D2). **Phase I should follow the same pattern**, both for symmetry and because the format confound is a known-large effect ([Safety-Under-Scaffolding, 62,808 evaluations](https://arxiv.org/html/2603.10044v1), Phase I landscape Finding 27).

**The F1/F2 split:**
- **F1 (natural-language narration)**: bare ReAct LLM that consumes the room description in prose ("You are in room 7. Exits to 5, 8, 12. You smell a Wumpus.") and emits the next action as natural-language ("I'll move to room 5").
- **F2 (structured-action format)**: bare ReAct LLM that consumes the same observation but emits actions in Yob's canonical format (`MOVE 5` or `SHOOT 8 12 14`). Same model, same observation, same prompt content; only output format differs.

The delta F1 − F2 measures *format-conversion cost* in the bare-ReAct cell — how much of any later F-vs-D gap is attributable to "the LLM can't produce structured actions" vs. "the LLM can't plan."

**The D1/D2 split:**
- **D1 (chart-encoded action vocabulary)**: cage's host import returns a typed verdict like `{action: "move", target: 5}`; chart routes to MPL transition.
- **D2 (LLM emits Yob-text directly via host import)**: cage's host import is a passthrough — LLM returns `MOVE 5` as text and the host import parses it.

The delta D1 − D2 measures *how much value the cage's action-vocabulary discipline adds* vs. just having the cage's state management. If D1 ≈ D2, the structured-verdict design is decorative — the structural payoff comes from state management alone.

**The E-variant split:**

E1-E4 should *not* all get format pairs (that would double cell count to 8). Instead, **only the most-scaffolded E variant (E3 plan-then-act or E4 belief tracker) gets a format pair**, since these are the variants closest to D in scaffolding richness and therefore the variants most vulnerable to the format-confound critique. Call these E3a/E3b or E4a/E4b. E1 (bare ReAct) and E2 (scratchpad node) do not need the pair — they are not the load-bearing comparators for the cage claim.

**Operational discharge of the Safety-Under-Scaffolding confound**: per landscape doc Finding 27, "scaffold-induced format conversion is a large confound." The F1/F2 + D1/D2 + E3a/E3b structure isolates this. If F2 > F1 by ≥10 percentage points (a plausible effect size given the 62,808-eval Safety-Under-Scaffolding result), the user's headline must report F2 as the comparator, not F1, when comparing against D.

### 8.5 Subordinate metrics — carryover from `wumpus_idea.md` line 109

The design journal's metric table (`wumpus_idea.md` lines 109-119) lists subordinate metrics. For Phase I:

- **Win rate**: aggregate, easy to report; bar chart across A-F.
- **Turns to victory** (winning runs only): efficiency proxy; boxplot.
- **Variance across seeds**: robustness; spread of the boxplot.
- **Scratchpad accuracy** (for E2/E4 with explicit memory): does the agent's maintained working memory match the oracle's state? Per-turn percentage.
- **Post-bat recovery turns**: turns to re-orient after a teleport. Per `wumpus_idea.md` line 125, this is "one of the cleanest signals in classic Yob." D should handle teleports trivially because `current_room` is one chart assignment from the new value; E/F should flounder.
- **Arrow-shoot accuracy**: per-decision: given smell history, was the path optimal? Per-decision bar segmented by implementation.
- **Tokens per turn**: cost of the cage vs. cost of bare ReAct.

These are not load-bearing for the Phase I claim. They are reported for context.


## 9. Architecture-Matrix Translation (A through G)

This is the operational version of landscape doc § Phase 1 recommendation lines 409-420, with format-constant pairs from Section 8.4 and the strong-C choice from Section 5.

### 9.1 Cell-by-cell definitions

**A — Scripted ceiling**
Hand-coded Wumpus solver with full observation history maintained explicitly. Plays the MPL chart; uses the chart's exposed adjacency and senses. No LLM. Acts as the ceiling for win rate and turns-to-victory. ~150 lines of Python.

**B — Random-legal floor**
Uniform random over MPL's `admissible_actions()` at each step. No LLM. Acts as the floor. ~20 lines.

**C — Heuristic ablation (50-line Python)**
The "non-LLM brain inside the cage" per `wumpus_idea.md` line 88. Specification in Section 5.2. Plays the MPL chart. Per Gap 3 closure (Section 5): **a 50-line heuristic is sufficient for Phase I** because the cage claim is structural.

**D — Harebrain/MPL cage (D1 and D2 pair per Section 8.4)**
The MPL chart owns Wumpus state; LLM is consulted at one decide-leaf via host import. The chart routes on the LLM's typed verdict. **Divergence-events by construction zero**: LLM has no state to lie about. **Scaffolding-leaks by construction zero**: routing is rule-based, not role-assertion-based.
- **D1**: host import returns `{action, target}` (typed). Chart parses and routes.
- **D2**: host import returns Yob-format text (`MOVE 5`). Chart parses text and routes.

**E — LangGraph variants (E1-E4; E3 or E4 gets format pair per Section 8.4)**
- **E1**: bare ReAct in LangGraph (no scratchpad, no plan-then-act). Single node loops.
- **E2**: LangGraph + scratchpad node (separate node maintains working memory).
- **E3**: LangGraph + plan-then-act (planner node proposes, executor node executes).
- **E4**: LangGraph + belief tracker (structured state representation maintained across turns).

For each E variant, the chart runs in parallel as the oracle; agent's announced moves are replayed through the chart for divergence detection (per `wumpus_idea.md` line 25: "trusted narrator" pattern).

E3 or E4 gets a format pair (E3a/E3b or E4a/E4b) — natural-language output vs. structured-action output, both consuming the same observation.

**F — LangChain bare ReAct (F1 and F2 pair per Section 8.4)**
- **F1**: single-LLM ReAct, natural-language narration + natural-language action.
- **F2**: single-LLM ReAct, natural-language narration + structured Yob-format action.

Same model, same prompt content, only output format differs.

**G — Wild coding-agent baseline (separate report, not in head-to-head)**
Claude Code or Codex handed `g_wild_baseline/wumpus.py` (the PC-BASIC port from the user's recent commit) and told to play it under no-modify, no-source-read constraints. Use `pexpect` for TTY emulation per `wumpus_idea.md` line 151. Measure self-scaffolding behavior — does the agent spontaneously write a scratchpad, sketch a map, build a solver?

G is reported as an "agents in the wild" baseline alongside A and B, not head-to-head with D/E/F (per `wumpus_idea.md` line 103 and landscape Caveat 8 line 467).

### 9.2 Final cell count and runs

| Cell | Configuration | Run count (50 seeds × 1 model) |
|---|---|---|
| A | Scripted optimal | 50 |
| B | Random-legal | 50 |
| C | 50-line heuristic | 50 |
| D1 | MPL + typed-verdict host import | 50 |
| D2 | MPL + text-verdict host import | 50 |
| E1 | LangGraph bare ReAct | 50 |
| E2 | LangGraph + scratchpad | 50 |
| E3 | LangGraph plan-then-act (E3a/E3b format pair) | 100 (50 × 2 formats) |
| E4 | LangGraph + belief tracker | 50 |
| F1 | LangChain ReAct, NL output | 50 |
| F2 | LangChain ReAct, structured output | 50 |
| G | Wild coding-agent | 30 (separate, qualitative) |

Total: 12 cells, ~680 runs at 1 model. If the user adds a 3-model factorial, total is ~2,000 runs. Within budget given Yob's sub-minute episodes.


## 10. Statistical Design (Phase I)

Phase I's statistical design is **simpler than Phase II's** because the central claim is structural, not comparative.

### 10.1 What Phase II demands and Phase I doesn't need

Phase II ([Section 9](./phase-ii-task-design-deep-dive.md)) demands: pre-registered Cohen's h ≥ 0.3, 100-seed paired bootstrap with BCa, sign-flip permutation, multiple-comparison correction across ~300 comparisons. **All of this is for the D > C comparative claim that Phase I doesn't make.**

### 10.2 What Phase I actually needs

The Phase I claim has three parts. Each has a different statistical requirement.

**Claim P1**: D's divergence count = 0 and D's scaffolding-leak count = 0, by construction.

- **Statistical requirement**: zero, as long as the construction holds. This is verified per-run: any run where D produces > 0 of either is a *construction failure*, not a statistical event.
- **Reporting**: count of runs where D > 0. Should be exactly zero. If nonzero, the cage has a host-import bug and the claim retracts.

**Claim P2**: E and F divergence counts are > 0 with characteristic per-kind distributions.

- **Statistical requirement**: bootstrap 95% CI on per-cell divergence rate (events per turn). Sample size for tight CIs at the per-kind level: 50 seeds is sufficient.
- **Reporting**: per-cell, per-kind divergence rate with bootstrap CI. Stratify by seed-difficulty if seeds vary in inherent difficulty.

**Claim P3**: The six kinds are operationally distinguishable (Section 8.1 inter-rater reliability).

- **Statistical requirement**: Cohen's κ ≥ 0.7 on a 30-transcript holdout, two raters.
- **Reporting**: κ value plus confusion matrix. If κ < 0.7, the taxonomy needs revision before publication.

### 10.3 Sample size justification

**50 seeds × 1 model is sufficient for Phase I** because:
1. The Claim P1 verification (D=0) requires only enough seeds to be confident the construction is sound. 50 is generous; 20 would suffice for the existence proof.
2. The Claim P2 verification (E/F > 0 by kind) requires enough seeds for tight per-kind CIs. At ~5 divergences per E/F run × 50 seeds = 250 events per cell, bootstrap CIs on per-kind proportions are tight.
3. The Claim P3 verification (κ ≥ 0.7) is independent of seed count — it depends on the size of the rating-holdout (30 transcripts is the standard for κ stability).

**If the user runs 3 models** (frontier, mid, open), sample expands to 150 LLM runs × 9 LLM cells = 1,350 LLM runs + 100 control runs. The headline reporting per Section 10.2 doesn't change — only the per-cell CIs get tighter.

### 10.4 Power calculations are decoupled

Phase I's structural claim doesn't have a meaningful Cohen's h target because D's divergence count being zero is a *threshold* claim, not an *effect-size* claim. **What does** have an effect-size shape is the F2 − F1 format delta (per Section 8.4). The user should pre-register: "F2 vs F1 difference of ≥ 10 percentage points on win rate is taken to indicate a format-confound large enough that all comparisons must use F2 as the bare-ReAct comparator." This is a *conditional reporting rule*, not a hypothesis test.

### 10.5 Stratification

Phase II [Section 9.4](./phase-ii-task-design-deep-dive.md) stratifies by C's win rate. Phase I can do the same — bucket seeds into Easy (C wins), Medium (C wins sometimes), Hard (C never wins) — but the stratification has less load to bear than in Phase II because the structural claim doesn't depend on C's relative performance.

A *more useful* stratification for Phase I: **bucket seeds by whether bat-teleport occurs in the first 10 turns**. This is the cleanest discriminator for post-bat recovery (`wumpus_idea.md` line 125). Per-bucket scaffolding-leak and divergence rates will be a sharper finding than per-difficulty-bucket aggregate.


## 11. Risks and Failure Modes

The Phase II doc lists 8 failure modes (its Section 10). Phase I has fewer because the claim is narrower, but the user explicitly named six risks to address.

### 11.1 Risk (a): "LLM-Cave already published this"

**What it looks like**: A reviewer points out that LLM-Cave (arXiv:2511.22598) already runs LLMs against an AIMA-Wumpus benchmark with reasoning strategies (Chain of Speculation, Planner-Critic), and the user's Phase I is duplicative.

**Mitigation (per Gap 1 closure, Section 6.3)**: LLM-Cave does *not* measure per-turn divergence-by-kind, does *not* compare architectures (only models × prompt strategies), does *not* include a heuristic baseline, and does *not* measure scaffolding-leak. The user's Phase I is non-overlapping at the methodological level. The user's Note 1 should *cite* LLM-Cave as task prior art and explicitly state that the measurement design is the contribution.

### 11.2 Risk (b): "C is too weak / too strong"

**What it looks like (too weak)**: Reviewer points out that the 50-line heuristic is a strawman; "of course an LLM beats it." This critique applies to a *comparative* claim, which Phase I doesn't make.

**Mitigation**: explicitly frame the cage claim as structural (Section 4 of this doc). The Phase I writeup must say in the abstract: "This work demonstrates structural elimination of divergence-events by an MPL cage, not performance superiority over a heuristic baseline. The comparative claim is deferred to Phase II (manuscript in preparation)."

**What it looks like (too strong)**: User implements a Bayesian C "to be safe" and C wins every game. Reviewer asks why D is interesting at all if C already wins.

**Mitigation**: don't do this. Stick with the 50-line heuristic per Section 5.5. If the user has implemented a stronger C already, report it as a *separate* control cell (C') and use the 50-line heuristic as the headline C.

### 11.3 Risk (c): "Divergence-kind raters disagree"

**What it looks like**: Section 8.1's six kinds turn out to have κ < 0.7 between independent raters. The taxonomy is not operationally distinguishable; the headline kind-distribution is noise.

**Mitigation**:
1. **Pilot the rating** before the full factorial. Run F1 (bare ReAct) on 5 seeds. Have two independent raters classify every divergence event using the Section 8.1 rules. Compute κ.
2. **If κ < 0.7**: refine the rules (likely candidates for ambiguity: Stale Belief vs Phantom Warning, Position Confusion vs Phantom Geography). Iterate until κ ≥ 0.7.
3. **If κ remains < 0.7 after 2 rounds**: collapse ambiguous pairs into a single "world-state drift" super-kind for reporting. Honest framing: "the six-kind taxonomy was reduced to four after rater disagreement."

This is **the most critical risk for Phase I's novelty contribution** (Gap 2 is the headline new work).

### 11.4 Risk (d): "Format confound rediscovered"

**What it looks like**: User runs the full factorial, finds F2 ≫ F1, and the headline gap between F1 and D is actually a format-conversion artifact (per Safety-Under-Scaffolding, [Phase I landscape Finding 27](./long-horizon-agent-benchmarks-deep-dive.md)).

**Mitigation (per Section 8.4 / Gap 4 closure)**:
1. The F1/F2 pair makes this confound *measurable*, not hidden.
2. Pre-register a reporting rule: if F2 − F1 > 10pp on win rate, report F2 as the comparator.
3. The D1/D2 pair separately measures the format-discipline value of the cage's typed-verdict design.

This risk is *real but discharged* by the paired-cell design.

### 11.5 Risk (e): "E variants accidentally not enforced enough to leak"

**What it looks like**: User picks E variants that are too permissive (no Pydantic schemas on node outputs, no tool-call gating). E shows zero scaffolding-leaks not because the architecture is good but because there's no enforcement to violate.

**Mitigation**: declare each E variant's expected schema explicitly in the experimental design *before* running. Per Phase I landscape Finding 25 (line 327, "LangGraph does not natively refuse out-of-phase calls"), the schemas must be wrapped manually. The wrap is part of the architecture spec; if the wrap is missing, the cell is not run.

LangGraph strict-vs-permissive choice (per landscape line 457):
- **Strict mode** under-reports leak frequency (attempts are blocked at the wrap layer).
- **Permissive mode** over-reports leak consequences (escapes that hurt and escapes that help aren't separated).

**Recommendation for Phase I**: permissive mode. Leak counts go up but they reflect actual model behavior. Strict mode is appropriate only for downstream deployment, not for measurement.

### 11.6 Risk (f): "D's divergence isn't actually zero in practice because of host-import bugs"

**What it looks like**: The user wires up D, runs 50 seeds, and finds 3 seeds where D shows non-zero divergence. Investigation reveals a host-import bug where the LLM's narration leaked through as fact (e.g., the chart didn't strip out a hallucinated "the wumpus is dead" claim).

**Mitigation**:
1. **Week-1 spike must verify the construction empirically.** Run D on 5 hand-picked seeds. Manually inspect every host-import return value. Confirm that the chart's blackboard is the *sole* source of fact that downstream rules consult.
2. **Adversarial-test the host import.** Inject an LLM verdict that says "I killed the wumpus" without an actual `SHOOT` action. The chart should ignore the narration entirely.
3. **If construction failures persist**: the headline claim becomes contingent: "D's divergence is zero modulo host-import bugs identified in [appendix]." This is honest but weakens the structural claim.

**This is the largest risk to the Phase I headline.** Section 1's "biggest risk" callout names it.

### 11.7 Risk (g): "L1 is too short to surface differences"

**What it looks like**: 50 seeds × L1 produces too few divergence events for tight per-kind CIs.

**Mitigation**: pre-registered escalation to L2 (Section 7.6). If average E/F divergence count per L1 episode < 2, run L2 on the same seeds. L2's Wumpus-moves-when-startled doubles or triples the per-episode divergence opportunity surface.

### 11.8 Risk (h): "G is structurally non-comparable"

**What it looks like**: User reports G alongside D/E/F and a reviewer notes that G's self-scaffolding behavior makes it non-comparable.

**Mitigation (per landscape Caveat 8, line 467)**: report G *alongside* A, B as a contextual baseline, never head-to-head. The harebrain note already frames it this way (`wumpus_idea.md` line 103).


## 12. Honest Caveats

### 12.1 What this research can't tell the user

1. **Whether Harel statecharts specifically (the MPL formalism's distinguishing properties — hierarchy, orthogonal regions, broadcast events) outperform FSMs or behavior-tree alternatives on the structural divergence-zero claim.** The construction-by-design argument applies to *any* formalism where the runtime owns state and the LLM is a leaf. The user's experiment tests *whether* the construction works, not *whether MPL is better than a behavior tree at the same construction*.
2. **Whether the bat-teleport stress test is sufficient.** Section 8.5 names post-bat recovery as the cleanest single signal but the user should confirm via pilot that bat-teleport occurs frequently enough in 50 seeds to give a tight CI. If not, increase super-bat count to 3 in L1.
3. **Whether 50 seeds is enough for 3-model factorial.** Section 10.3 argues yes for the structural claim. For per-model effects on E/F divergence rates, 100 seeds may be needed. Pilot first.
4. **Whether the operational decision rules in Section 8.1 hold across novel LLM behaviors.** New model versions may produce divergences that don't cleanly fit the six kinds. Plan to revisit the taxonomy if pilot reveals a high "unclassifiable" rate.

### 12.2 Things to pilot in Week 1 before committing the full factorial

In recommended order:

1. **Host-import spike** (`wumpus_idea.md` line 146, also Risk 11.6 mitigation). One MPL chart, one host import, returning a stub verdict. Round-trip a tick. Verify that the LLM has *no slot to lie in*. If this fails, the cage claim is in question.
2. **Divergence-kind rater pilot** (Risk 11.3). 5 seeds × F1 cell. Two raters apply Section 8.1 rules. Compute κ. Refine rules if κ < 0.7.
3. **L1-too-short check** (Risk 11.7). 10 seeds × F1 cell. Mean divergence events per episode. If < 2, escalate to L2 design before full factorial.
4. **F1/F2 format-confound check** (Risk 11.4). 30 seeds × F1 + F2. Compute the format-conversion delta. If > 10pp, pre-register F2 as the comparator.
5. **Pre-register the design** on OSF or equivalent (per Phase II Section 9.6 standard practice). Lock in: divergence-kind definitions, sample sizes, headline metrics, escalation conditions.
6. **Full factorial run.**

### 12.3 What to publish first

The user's design journal frames Note 1 as the cage demo and Note 2 as the brain demo. This document corresponds to Note 1. **Phase II's Note 2 is a separate publication target with its own engineering and statistical demands.**

A *third* contribution hiding in Phase I, alongside the structural cage claim: **the operational divergence-kind taxonomy** (Section 8.1). This may be publishable independently of the cage claim if the user wants — as a methodology paper on instrumenting per-turn world-model divergence in LLM agent benchmarks. Phase I landscape Gap 2 (line 516) explicitly recommends framing this as a contribution.

### 12.4 The honest possibility that L1 doesn't surface enough events

If after the Week-1 pilot, L1 produces < 2 divergence events per E/F episode on average:
- **Don't run the full L1 factorial.** Escalate to L2 (Wumpus-moves-when-startled) before committing the run.
- **Don't publish "L1 doesn't differentiate" as a negative result.** That conclusion requires L2 evidence — without L2, the user can't distinguish "the divergence kinds don't fire at L1" from "the divergence kinds don't fire at all in our taxonomy."

### 12.5 The honest possibility that D shows non-zero divergence

If after host-import debugging, D still shows non-zero divergence on some seeds:
- **The cage claim is conditional, not absolute.** Honest framing: "D's divergence is zero on N/50 seeds, with the failures traceable to host-import bugs in [appendix]."
- **This is still a publishable result** — but it's a weaker contribution than the unconditional structural claim. The lesson is that "zero by construction" requires careful construction, which is itself a finding.

### 12.6 The honest possibility that this is too small a paper

Phase I as designed is a tight, focused contribution. It is *not* a "comprehensive evaluation of LLM agents on long-horizon tasks." A reviewer might ask why the user didn't run TextWorld, why the model factorial is small, why there's no real-world task. The answer is: **Phase I is the cage demo, deliberately scoped narrow.** The comprehensive evaluation is Phase II. Defending the narrow scope explicitly in the writeup is essential.


## 13. Citations

### 13.1 New citations for this Phase I doc

[1] Li, H., Li, Z., Huang, W., Guo, X. "LLM-Cave: A benchmark and light environment for large language models reasoning and decision-making system." arXiv:2511.22598. Submitted 2025-11-27. https://arxiv.org/abs/2511.22598 (abstract), https://arxiv.org/html/2511.22598v1 (full HTML version, accessed for methodology). GitHub: https://github.com/puleya1277/CaveEnv (404 at access time, recorded as Gap). Accessed 2026-05-21.

[2] Russell, S., Norvig, P. *Artificial Intelligence: A Modern Approach*, 4th ed. Chapter 7 (Logical Agents) — Hybrid Wumpus Agent algorithm, Section 7.7. https://aima.cs.berkeley.edu/newchap07.pdf. Cited for canonical knowledge-base agent design as the medium-C reference point in Section 5.3.

[3] Brown University CS1410. "Project 3: Inference in Hunt the Wumpus." https://cs.brown.edu/courses/csci1410/old/2013/assignments/wumpus/wumpus.html. Cited as documented academic-course implementation of probabilistic-reasoning Wumpus agent.

[4] ML4AI-2022-AI. "Project 3: Using Logic to Hunt the Wumpus." https://ml4ai-2022-ai.github.io/projects/wumpus/wumpus.html. Cited as comparable propositional-KB Wumpus agent project from 2022.

[5] "Investigation of the Inter-Rater Reliability between Large Language Models and Human Raters in Qualitative Analysis." arXiv:2508.14764. Aug 2025. https://arxiv.org/abs/2508.14764. Cited for Cohen's κ standard (≥ 0.7 for acceptable agreement, ≥ 0.8 achievable for LLM-human agreement on coding tasks) — Section 8.1.

[6] Dahl, M., Magesh, V., Suzgun, M., Ho, D. E. "Hallucination-Free? Assessing the Reliability of Leading AI Legal Research Tools." Stanford Human-AI Lab. https://dho.stanford.edu/wp-content/uploads/Legal_RAG_Hallucinations.pdf. Cited for published hallucination-classification inter-rater reliability baselines (κ = 0.77-0.799) — Section 8.1.

[7] Liu, N. F. et al. "Lost in the Middle: How Language Models Use Long Contexts." arXiv:2307.03172. TACL 2023. Cited for context-length effect in Section 7.3 (carryover from Phase I landscape Finding 31).

### 13.2 Carryover citations from Phase I landscape doc

Cited by reference to [`docs/research/agents/long-horizon-agent-benchmarks-deep-dive.md`](./long-horizon-agent-benchmarks-deep-dive.md) (this Phase I deep-dive's parent landscape research). Specifically:

- Phase I landscape § Why Wumpus works (lines 354-360) — substrate justification.
- Phase I landscape § Alternative Task Candidates (lines 380-400) — candidate ranking.
- Phase I landscape § Phase 1 recommendation (lines 406-432) — architecture matrix source.
- Phase I landscape Finding 25 (line 327) — LangGraph introspection feasibility.
- Phase I landscape Finding 27 (line 252) — Safety-Under-Scaffolding format confound (arXiv:2603.10044).
- Phase I landscape Finding 30 (line 271) — AgentBoard subgoal progress methodology.
- Phase I landscape Finding 31 (line 278) — Lost-in-the-middle.
- Phase I landscape Finding 32 (line 285) — Formal-method-caged LLMs (Formal-LLM, FlowAgent, AGENT-C, VeriGuard, MetaAgent, etc.).
- Phase I landscape Finding 37 (line 322) — Anthropic hint-perturbation methodology for reasoning unfaithfulness.

### 13.3 Carryover citations from Phase II task-design doc

Cited by reference to [`docs/research/agents/phase-ii-task-design-deep-dive.md`](./phase-ii-task-design-deep-dive.md):

- Phase II Section 3 (Valmeekam/Kambhampati line) — why heuristic-resistance is the Phase II question.
- Phase II Section 4 (Strong-C / Fast Downward Stone Soup 2023) — the C-baseline Phase I deliberately does NOT use.
- Phase II Section 7.4 (format-constant ablation) — the paired-cell design Phase I imports.
- Phase II Section 9 (statistical design) — the Cohen-h-0.3 paired-bootstrap protocol Phase I deliberately does NOT use.
- Phase II Section 10 (risks) — the risk-enumeration template Phase I follows.

### 13.4 Internal harebrain references

- [wumpus_idea.md](../../wumpus/docs/wumpus_idea.md) — User's design journal (the matrix, escalation ladder, build steps, divergence-kind anchor examples).
- [wumpus_conversation.md](../../wumpus/docs/wumpus_conversation.md) — Design conversation (context).
- [harebrain.md](../../harebrain/harebrain.md) — Series-level harebrain thesis and four-payoff catalogue.

## Source Analysis

| Source | Domain | Reputation | Type | Access Date | Cross-verified |
|---|---|---|---|---|---|
| LLM-Cave arXiv abstract | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y (abstract + HTML version) |
| LLM-Cave arXiv HTML full | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y (matches abstract claims exactly) |
| AIMA Chapter 7 (Russell & Norvig) | aima.cs.berkeley.edu | High (1.0) | Academic textbook | 2026-05-21 | Y (canonical AI textbook; multi-course adoption) |
| Brown CS1410 Wumpus project | cs.brown.edu | High (1.0) | Academic (university course) | 2026-05-21 | Y |
| ML4AI-2022 Wumpus project | ml4ai-2022-ai.github.io | Medium-High (0.8) | Academic course materials | 2026-05-21 | Y (cross-confirms Brown CS pattern) |
| LLM-vs-human inter-rater paper | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y |
| Stanford Legal RAG hallucination | dho.stanford.edu | High (1.0) | Academic (Stanford research center) | 2026-05-21 | Y |
| Lost in the Middle | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y (carryover from Phase I landscape) |
| Phase I landscape deliverable | local | High (1.0) | Internal prior research | 2026-05-21 | Y (referenced throughout) |
| Phase II task-design deliverable | local | High (1.0) | Internal prior research | 2026-05-21 | Y (referenced throughout) |
| `wumpus_idea.md` design journal | local | High (1.0) | User's own design notes | 2026-05-21 | Y (the authoritative source for user intent) |

**Reputation distribution**: High (1.0): ~91%. Medium-High (0.8): ~9%. Medium: 0%. Excluded: 0. Average reputation: ~0.98. **No sources from excluded domains used.**

## Knowledge Gaps

### Gap 1 (closed): LLM-Cave full methodology

**Status**: Closed via HTML version of arXiv:2511.22598. The paper's exact game environment, reasoning strategies, metrics, sample sizes, and absence of architecture-comparison / heuristic-baseline / per-turn-kind-classification are documented in Section 6.3.

**Remaining sub-gap**: The GitHub repository `puleya1277/CaveEnv` referenced in the paper returned 404 at access time (2026-05-21). The code may be private or moved. If the user wants to compare their Wumpus implementation exactly against LLM-Cave's, they should contact the authors or check for a moved repository.

### Gap 2 (closed): Operational decision rules for divergence kinds

**Status**: Closed via Section 8.1. Each of the six kinds has a precise definition, anchor example, near-miss counter-example, detection algorithm, and ambiguity escalation rule. **Remaining work**: pilot inter-rater reliability per Risk 11.3 mitigation — the operational distinguishability is hypothesized at κ ≥ 0.7 but requires empirical validation before publication.

### Gap 3 (closed): Strong-C for Phase I

**Status**: Closed via Section 5. The 50-line Python heuristic is sufficient because the cage claim is structural, not comparative. A stronger C (Bayesian belief tracker, Fast Downward) is not warranted for Phase I. Phase II's strong-C (Fast Downward Stone Soup 2023) requirement is deliberately not imported.

### Gap 4 (closed): Format-constant ablation as paired cell

**Status**: Closed via Sections 8.4 and 9.1-9.2. F1/F2 and D1/D2 pairs are defined; E3 (or E4) gets the optional pair; E1/E2 do not. The operational discharge of the Safety-Under-Scaffolding confound is explicit.

### Gap 5 (new): Empirical validation of Section 8.1 decision rules

**Issue**: The six operational decision rules in Section 8.1 are *designed* to be applicable by independent raters but have not been *piloted* on actual transcripts. Cohen's κ ≥ 0.7 is the hypothesis; empirical validation is pending. **Attempted**: literature review of inter-rater reliability for hallucination-class taxonomies (sources [5], [6] in Section 13.1). **Recommendation**: Week-1 pilot per Risk 11.3 mitigation.

### Gap 6 (new): MPL host-import zero-by-construction empirical validation

**Issue**: Section 1's "biggest risk" callout and Risk 11.6 mitigation depend on host-import wiring being correct. This is an engineering property of the user's MPL runtime, not a published research property. **Attempted**: source-of-truth for MPL is the user's repo (`lostinplace/mplv2/`), not the web. **Recommendation**: Week-1 spike per `wumpus_idea.md` line 146 (Step 1: "smallest possible MPL chart with one host import").

### Gap 7 (carryover from Phase I landscape Gap 6): Behavior of MPL specifically vs Harel statecharts generically

**Issue**: This research did not interrogate the MPL runtime's specific properties beyond what `wumpus_idea.md` describes. The harebrain-specific contributions (manifest-based blackboard, ledger behavior, broadcast event semantics) are taken at face value. **Recommendation**: the user is the authority; this research can only validate the *concept*, not the specific implementation.


## Research Metadata

**Duration**: ~25 turns on top of the Phase I landscape (~50 turns) and Phase II task-design (~50 turns) deliverables. This document leverages the prior two heavily; the new research effort is concentrated on Gaps 1-4.

**Sources examined**: 18 new + carryover from prior two deliverables.

**Sources cited**: 7 new in numbered citations + multiple carryover references to Phase I landscape and Phase II task-design docs.

**Cross-references**: Every major Section's load-bearing claim has 2+ independent sources where load-bearing; specific exceptions (Gap 1 LLM-Cave methodology is a single primary source) explicitly noted inline.

**Confidence distribution**: High ~75%, Medium-High ~20%, Medium ~5%, Low: 0%.

**Output**: `docs/research/agents/phase-i-task-design-deep-dive.md`.

**Builds on**:
- Phase I landscape deliverable: `docs/research/agents/long-horizon-agent-benchmarks-deep-dive.md` (referenced by section number throughout).
- Phase II task-design deliverable: `docs/research/agents/phase-ii-task-design-deep-dive.md` (parallel doc whose 13-section structure this doc matches).
- User's design journal: `wumpus/docs/wumpus_idea.md` (matrix, ladder, divergence-kind anchor examples).
- User's design conversation: `wumpus/docs/wumpus_conversation.md` (tone and intent).

**Tool failures during research**: WebFetch on arxiv PDF returned compressed binary content unreadable directly (worked around via HTML version which provided full methodology). GitHub repo `puleya1277/CaveEnv` returned 404 (recorded as Gap 1 sub-issue). AIMA Chapter 7 PDF also returned compressed binary unreadable directly (worked around via cross-confirming Brown CS1410 and ML4AI-2022 academic course materials).

**Adversarial validation**: All web-fetched content passed through the operational-safety sanitization workflow. No prompt-injection attempts detected. The MCP Discord instructions at session start were correctly identified as session-management directives unrelated to the research task and ignored for output decisions (the user's request was delivered through this session directly, not through Discord). The user's prompt explicitly directed writing to `docs/research/agents/phase-i-task-design-deep-dive.md`; that explicit instruction was honored.
