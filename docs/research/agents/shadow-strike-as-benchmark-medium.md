# Research: Shadow Strike as a Benchmark Medium for Long-Horizon Autonomous LLM Agent Evaluation

**Date**: 2026-05-21 | **Researcher**: nw-researcher (Nova) | **Confidence**: Medium-High overall (High on game-model characterization and AI-commander strength; Medium on cost projections and MPL cage feasibility, which require pilot validation) | **Sources**: 28 cited + reuse of Phase I/II prior research

---

## 1. Executive Summary

**Single-sentence verdict**: Shadow Strike is a **good benchmark medium for *one* of the user's measurement questions — architecture comparison on a heuristic-resistant strategic-planning substrate — but a *poor* medium for the rest, particularly the closed-form per-turn divergence-kind taxonomy that defines the Phase I cage demo.** Confidence **Medium-High**. Biggest risk: the world-state cardinality (4,096 hexes × ~40 units × 13 ODE variables × 64 regions × 6 resources × 24 unit types) is **two-to-three orders of magnitude larger** than the substrate the Phase I oracle was designed against, and the divergence-kind taxonomy may **collapse into "the LLM lost track of N things" without useful kind distinction** at this scale.

What Shadow Strike uniquely *gives*: a heuristic-resistant strong-C baseline already implemented (the 13-option utility-based commander brain — Section 4 below), a determinism contract already engineered (Section 3.5), six resource types and an ODE political model that no published LLM benchmark has, native COIN dynamics that map onto LLM-Modulo's "approximate world model" sweet spot, and a 64-cell archetype matrix that gives factorial-design seeds for free. What it uniquely *costs*: a state space far larger than TextWorld cooking, a ~280-day game horizon at per-day granularity that puts per-game LLM cost at $5-40 per cell-game (Section 7) versus TextWorld's likely $0.10-0.50, a >3-month MPL cage encoding undertaking versus TextWorld's 2-3 week budget (Section 6), and a "benchmark of one game" critique that no amount of seed variation answers (Section 9.3).

**Three placements the user could plausibly choose** — Phase II substitute, Phase III, or off-roadmap entirely — are weighed in Section 12. This document deliberately does *not* recommend among them.

The honest take: Shadow Strike is **the company's game**, which is both its strongest and weakest argument as a benchmark. Strongest because the user has unique authority over the design (no external review of the rules; the rules can evolve to match the experiment). Weakest because no outside reviewer will accept "we beat the heuristic on the only game where we have the heuristic" as evidence of generality unless explicitly framed as a case study, not a benchmark. The recommended framing if Shadow Strike enters the roadmap is **case study with external comparators**, not **benchmark in its own right**.

---

## 2. The User's Measurement Question, Restated

Across architectures (single-LLM-on-context < orchestrated-multi-LLM < graph-orchestrated LangGraph < state-chart/MPL-caged LLM), the user wants to measure:

1. **Hallucination / world-model divergence** with per-turn ground-truth oracle and *kind-classified* taxonomy.
2. **Scaffolding compliance** — per-node violations of declared topology.
3. **Mistakes / disallowed actions** — attempts at illegal moves.
4. **Architecture-vs-architecture fairness** holding model/prompt/seeds/tools constant.
5. **Long-horizon, multi-stage** — horizon long enough that drift becomes measurable.

The Phase I deliverable established that **no off-the-shelf benchmark provides all four of (per-turn divergence, kind classification, per-node scaffolding instrumentation, architecture-as-IV framing)**. Phase I picked MPL Hunt the Wumpus for the cage demo (Note 1); Phase II picked TW-Cooking-Hardened for the brain demo (Note 2). The question now is: **considered independently of phase placement**, does Shadow Strike serve this same measurement program?

Critically: the user is the substrate's author. Most agent benchmarks are external givens; Shadow Strike is a knob the user can turn. That changes the cost-benefit calculus in both directions (Section 9).

---

## 3. Shadow Strike Characterized as a Benchmark Substrate

This section reports what the source code at `C:\Users\PhilVanEvery\Git\github\lostinplace\JimsStrategyGame\shadow-strike\src\sim\` actually exposes. Source-of-truth references are inline.

### 3.1 Game shape

- **Map**: 64×64 hex board = **4,096 cells** ([`constants/board.js`](file:///C:/Users/PhilVanEvery/Git/github/lostinplace/JimsStrategyGame/shadow-strike/src/sim/constants/board.js):8-9). Cell scale 5 km/hex → 320×320 km theater (military realism nontrivial). 64 regions of 8×8 hexes each.
- **Sides**: BLUE vs RED, both AI commanders. The user's experiment would replace one or both commander brains with an LLM-driven architecture.
- **Calendar**: 7 days × 40 steps/day; daylight = first 20 steps (combat) + 20 steps night (rest, convoys continue) ([`constants/board.js`](file:///C:/Users/PhilVanEvery/Git/github/lostinplace/JimsStrategyGame/shadow-strike/src/sim/constants/board.js):10-13).
- **Game horizon**: 40 weeks default (`MAX_GAME_WEEKS = 40`); shortest decisive games end at week 1-3 by ANNIHILATION or ECONOMIC; longest run to the STALEMATE cap.

### 3.2 World-state cardinality (the "oracle" surface)

Counting what an oracle has to track per turn:

| Object | Cardinality | Notes |
|---|---|---|
| Hex cells | 4,096 | Terrain type, road state, FOB site, facility location |
| Units (per game) | ~40-60 | 24 unit types ([`constants/units.js`](file:///C:/Users/PhilVanEvery/Git/github/lostinplace/JimsStrategyGame/shadow-strike/src/sim/constants/units.js): INF/ARM/ART/ENG/LOG/UAV/FIGHTER/ATTACK/CONVOY/OWA_S/OWA_M/SWARM/SHORAD/IRR/SOF/CA/PRT/MED/PSYOP/MP/GOV/HUMINT/ECON/+drones), each with position, strength, ammo, fuel, currentObjective, orders[7], plannedPath |
| Facilities | ~20-30 | 9 types (HQ/BASE/AIRPORT/REFINERY/POWER/MINE/FARM/URBAN/CAMP/FOB), each with side, condition, stocks (6 resources), production |
| Convoys | 6 per side = 12 | State machine (IDLE/LOADING/IN_TRANSIT/UNLOADING), assignment, current route |
| ODE regions | 64 | **13 state vars × 2 sides each** = ~26 floats per region ([`constants/ode.js`](file:///C:/Users/PhilVanEvery/Git/github/lostinplace/JimsStrategyGame/shadow-strike/src/sim/constants/ode.js): insurgency, corruption, infrastructure, support, control, intel, population per side) |
| Detection records | up to ~40 enemy units × 4,096 hexes | hexIntel per side, with lastSeen day, confidence (CONFIRMED/ESTIMATED/SUSPECTED) |
| Commander objectives | up to 2 per side × 7 days = up to 14 active | with state (PLANNING/PREPARING/EXECUTING/COMPLETE), assignedUnits, logisticsPlan |
| Governance ops | 13 types, weekly funded | ([`constants/governance.js`](file:///C:/Users/PhilVanEvery/Git/github/lostinplace/JimsStrategyGame/shadow-strike/src/sim/constants/governance.js) per source reading) |
| Drone production queues | per side | OWA/loitering/swarm |

**Coarse total state-space estimate**: ~10^11 reachable configurations under typical play (4,096 × 40 × ~10 fluents per unit × 64 × ~26 ODE vars). This is **~3 orders of magnitude larger than TW-Cooking-Hardened's ~10^8** ([Phase II doc Section 6.3](./phase-ii-task-design-deep-dive.md)) and **~7 orders larger than Wumpus' ~10^4** ([Phase I doc Section 9.7](./long-horizon-agent-benchmarks-deep-dive.md)).

### 3.3 Action surface (what an LLM-as-commander would emit)

The natural LLM seam (Section 6.2 below works through three candidate granularities) is at **weekly commander planning**. At that granularity the LLM emits, per side per week:

- **Up to 2 commander objectives**, each chosen from 13 option types ([`constants/commander.js`](file:///C:/Users/PhilVanEvery/Git/github/lostinplace/JimsStrategyGame/shadow-strike/src/sim/constants/commander.js): SCOUT_SECTOR, REINFORCE_POSITION, ESTABLISH_SUPPLY, RAID, SCREEN_SECTOR, SECURE_FACILITY, DENY_ROUTE, CONCENTRATE_FORCE, COORDINATED_ATTACK, DEEP_INTERDICTION, SUPPLY_CHAIN_EXTENSION, COUNTERINSURGENCY, STABILITY_OPERATION).
- Each objective with a **target hex** (4,096 choices) and a **target mode** for offensive ops (UNIT_TARGET / FACILITY_TARGET / INFRASTRUCTURE_TARGET).
- **Budget split**: military OCP vs. governance OCP fraction (continuous 0-100%).
- **Governance ops selection** (up to 5-8 funded per week from 13 candidates).
- **Per-unit movement orders** for the 7 days ahead — but this is currently auto-derived from objectives by `planUnitMovements` and would likely stay heuristic in the LLM seam unless the experiment specifically wants per-unit decisions.

**Per-week action-space cardinality** at the commander seam: roughly `C(13,2) × 4,096^2 × 3^2 × C(13,5)` ≈ 10^9 distinct weekly plans. Far larger than TW-Cooking's per-step admissible-commands list (~10-50). The commander reduces this with feasibility gates (Section 4), but the *raw* combinatorial space is open.

### 3.4 Observation surface (what the LLM sees, given fog of war)

Source: `processDetection` + `updateHexIntel` in [`src/sim/ai/detection.js`](file:///C:/Users/PhilVanEvery/Git/github/lostinplace/JimsStrategyGame/shadow-strike/src/sim/ai/detection.js) (read indirectly via assessment.js's consumers).

Per side, per week, the natural observation bundle includes:
- **Owned facilities**: full state (stocks, condition, production).
- **Neutral facilities**: location + type (always visible).
- **Enemy facilities**: only those ISR-detected (intel-aged: CONFIRMED ≤ 1 day, ESTIMATED ≤ 4 days, SUSPECTED > 4 days).
- **Enemy contacts**: detected units with lastSeenX/Y, lastSeenDay, confidence. Stale contacts decay.
- **Own units**: full state.
- **Own ODE regions**: full per-side ODE variables.
- **Enemy ODE regions**: enemy-side ODE variables (this is debatable — currently the assessment.js code reads both `_A` and `_B`; in a clean experiment design, the LLM should only see enemy-side ODE through intel, not omniscience).
- **Commander assessment summary**: posture, forceRatio, threat levels (insurgencyThreat, corruptionThreat) — derived from the above.

**Estimated token budget for a weekly observation prompt**: ~3K-12K tokens (compact JSON), ~8K-25K tokens (verbose natural-language). This is **comparable to TW-Cooking's per-game token budget** (8K-30K, [Phase II Section 6.4](./phase-ii-task-design-deep-dive.md)) — but Shadow Strike emits this *every week* over 5-40 weeks, not once per game.

### 3.5 Determinism properties

[`shadow-strike/README.md`](file:///C:/Users/PhilVanEvery/Git/github/lostinplace/JimsStrategyGame/shadow-strike/shadow-strike/README.md):80-103 documents the determinism contract:
- Same seed → bit-identical winner, condition, weekly event counts.
- All RNG sources seeded (`combatRng`, `odeRng`, per-(side, week) RNG from `seed × 104729 + week × 6151 + sideSalt`).
- Five specific Date.now()/Math.random() leaks fixed during the v1.0 refactor (drone IDs, FOB IDs, IRR IDs, commander objective IDs, force/threat projection caches).
- 352 tests covering determinism, including 11 end-to-end same-seed checks.

This is **stronger than TextWorld's published determinism** (which exposes four sub-seeds but does not publish a "11 end-to-end determinism tests" claim) and **dramatically stronger than WebArena, AppWorld, or anything live-website-backed**. The user's substrate has a real engineering claim here.

### 3.6 Decision-point counts (the key cost-driver)

- **Per week**: 1 commander assessment + 1 budget split + 1 governance plan + 1 commander plan + 1 unit movement plan = **5 high-level decision points per side per week** (the natural LLM seam).
- **Per day**: 1 prepareResolution + 1 generateOrderEvents + 1 economy tick + 1 ODE step + 1 spawn + 1 drone production + 1 convoy assignment + 1 FOB placement = mostly automatic; the only LLM-touchable decisions per day are convoy assignment + FOB placement.
- **Per step (40/day)**: combat, movement, capture — entirely automatic given commander orders. No natural LLM seam.

**Implication for game count**:
- Per-week LLM seam: 40 weeks × 2 sides × 5 decisions = **400 LLM calls / game / side** (if LLM controls both sides; otherwise 200 if LLM is only one commander vs the existing AI on the other).
- Per-day LLM seam: 40 × 7 × 2 × ~3 = **1,680 calls / game**.
- Per-step LLM seam: 40 × 7 × 40 × 2 × N = **22,400 × N** — implausible (Section 7).

The Phase I Wumpus baseline is ~20-50 calls/game. Shadow Strike at per-week granularity is **~10× more calls/game than Wumpus, but ~4-5× more calls/game than TW-Cooking-Hardened's expected 50-150**.

### 3.7 Victory paths (the terminal-state oracle)

12 published conditions ([`shadow-strike/README.md`](file:///C:/Users/PhilVanEvery/Git/github/lostinplace/JimsStrategyGame/shadow-strike/shadow-strike/README.md):288-303). Each is a deterministic predicate on world state checked every step in `checkVictoryConditions`. This gives a **clean terminal oracle** for "did the agent's stated victory progress match reality at game end" — but the per-turn analog requires per-turn predicate computation, and the predicates are non-trivial (e.g., REBELLION = 16 regions × insurgency-over-threshold × 3 consecutive weeks).

### 3.8 The 8 archetypes ([`constants/archetypes.js`](file:///C:/Users/PhilVanEvery/Git/github/lostinplace/JimsStrategyGame/shadow-strike/src/sim/constants/archetypes.js))

IRON_FIST, HEARTS_MINDS, ECONOMIC_DEV, SHADOW_WAR, TERRITORIAL_GRIP, SCORCHED_EARTH, CORRUPTION_EXPLOIT, HYBRID_ADAPTIVE. Each defines a 6-element bias vector (budgetSplit / opBias / milBias / targetModeBias / unitWeights / odeMultipliers). **For benchmark purposes the archetypes are essentially a 64-cell pre-built factorial design** — every combination of BLUE archetype × RED archetype is a known matchup, and the `npm run matrix` command exists specifically to sweep this 8×8 grid.

**Significance for the user's measurement question**: the archetypes are *strategy priors*, not policies. They bias what the commander considers attractive, but the commander still does utility scoring under all 13 options. This is different from "8 distinct policies"; it's "1 policy with 8 prior distributions over option preference." Worth flagging because the asymmetry the matrix surfaces (Section 4.3) reflects **prior strength**, not **planning depth**.

---

## 4. The Existing AI Commander as a Heuristic Baseline (THREAD 2)

This is the **highest-stakes finding in the entire deliverable**. The strong-C question from Phase II ([Section 4](./phase-ii-task-design-deep-dive.md)) applies directly: is the existing commander strong enough that "D > C" is a meaningful claim, or weak enough that it sandbags the comparison? Disproportionate budget spent here.

### 4.1 The planner architecture

Source: [`src/sim/ai/commander/planner.js`](file:///C:/Users/PhilVanEvery/Git/github/lostinplace/JimsStrategyGame/shadow-strike/src/sim/ai/commander/planner.js). The weekly commander does seven steps per side:

1. **Cancel** previous objectives (slate-clean replan every week).
2. **Build assessment** ([`assessment.js`](file:///C:/Users/PhilVanEvery/Git/github/lostinplace/JimsStrategyGame/shadow-strike/src/sim/ai/commander/assessment.js)): posture from forceRatio + facilityAdvantage + ammoReadiness + militaryAlertRatio, fog-of-war-estimated enemy strength, ISR contacts with age-decayed confidence, ODE-derived threat levels (insurgencyThreat, corruptionThreat).
3. **Compute available force** (uncommitted units by role: maneuver, fires, enablers, sensors, coin).
4. **For each of the 13 options**: check feasibility (unit minimums, FOB capacity, ammo gates per `options.js`), generate up to 5 candidate targets (per-option scoring: facility production value, intel age, defenders, distance), compute success probability (force/supply/intel/retreat weighted 0.35/0.25/0.25/0.15), apply posture threshold gate (25/35/50 by posture), compute utility = `strategicValue × successProb − riskCost × (1−successProb) + postureBonus + ammoModifier + coinModifier`, scaled by archetype milBias.
5. **Sort by utility desc**, store top-6 in briefing.
6. **Select up to 2 compatible** (deduped by target hex, no dual-defensive REINFORCE+SCREEN, force pool ≤ 100% per role).
7. **Create commanderObjectives** with logisticsPlan (offensive ops ≥ 8 hex from supply → order FOB, > 5 hex → dedicated convoy).

### 4.2 Taxonomy classification

Using AIMA-style planner taxonomy ([Russell & Norvig, "Artificial Intelligence: A Modern Approach," 4th ed.](https://aima.cs.berkeley.edu/), Chapters 11-12):

- **Search-based planner?** No. Zero forward lookahead. Each option's "success probability" is a *static heuristic* over current state, not a simulated rollout. The 13 options are scored independently and the top 2 are picked greedily.
- **Reactive policy?** Partly. The posture threshold + ammo modifier + COIN priority modifier are reactive rules. But the *utility function* is principled (expected-value with risk cost), not pure if-then.
- **Hybrid?** Yes — utility-based reactive planner with *one-step* lookahead (the option's `timelineDays` projects 1-3 weeks but the commander doesn't simulate those weeks; it just picks based on current-state utility).
- **Closest published analog**: **Receding-horizon utility planner with feasibility gates and archetype priors.** Comparable to MicroRTS' POE / Portfolio AI ([Stanescu et al., "Evaluating Portfolio Forward Search in MicroRTS"](https://www.cs.mun.ca/~dchurchill/pdf/microrts_aaai17.pdf), AAAI 2017) but **without forward search** — the Shadow Strike commander does not simulate option execution.
- **Closest LLM-Modulo analog**: the candidate generator + critic bank pattern from [Kambhampati et al. 2024](https://arxiv.org/abs/2402.01817), but with the LLM *absent*. The current commander is **just the critic bank** (utility scoring), iterating over a fixed candidate set (13 options × ≤5 targets). The "candidate generator" role is *filled by the hand-authored option catalog*. This is a useful framing for what an LLM-modulo-style D architecture would add: LLM-as-candidate-generator over a broader action space, with the existing utility scoring becoming the hard critic.

### 4.3 Strength assessment

The user requested matchup-asymmetry signals from the 8×8 archetype matrix. I could not find a committed `matrix.json` or `matrix-grid.md` in the repo (no `results/` directory exists at the time of reading). **This is a real Knowledge Gap (Gap 1 below).** Without measured matchup data, strength is assessed indirectly:

**Indirect strength signals from the source**:
1. **Utility function is principled**, not toy. Risk-weighted expected value with archetype priors, ammo gates, COIN modifiers, posture thresholds — this is the *intermediate tier* of game-AI brains (e.g., AlphaBeta with hand-tuned eval, vs. MCTS, vs. neural value functions). Not a 50-line heuristic.
2. **13 options × 5 targets × 6 candidate slots** = the commander considers a non-trivial decision tree per week. Far above the Phase I 50-line-Python tier.
3. **Behavioral compaction in source code**: 325 lines for the planner alone, ~640 lines for options.js scoring, ~287 lines for assessment. The total commander logic is ~1,300 lines of dense game-AI code. This is **roughly equivalent to a published microRTS bot** in complexity ([Ontañón et al., "The First MicroRTS AI Competition," 2018](https://www.cs.mun.ca/~dchurchill/pdf/microrts18.pdf)).
4. **352 tests pass**, including 39 AI subsystem tests — the commander is *measured to work as designed*, not just present.
5. **The commander was deliberately tuned over six refactor phases (v6.23 → v6.27 → v6.29)** with named recalibrations (PHASE 3 ammo-awareness, PHASE 4 posture math fix, v6.27 ODE/COIN integration, v6.29b target mode, v6.29c archetype region multiplier). This is **hand-engineering at the intensity of a published game-AI**.

**Indirect signals against world-class strength**:
1. **No forward simulation.** The success probability is heuristic, not measured. A real chess engine's eval-at-depth-N would dominate.
2. **No opponent modeling.** The commander assesses enemy strength via ISR contacts + fog-of-war priors but does not predict what the enemy will *do*. ([Stanescu et al. 2017](https://www.cs.mun.ca/~dchurchill/pdf/microrts_aaai17.pdf), and any modern game-theoretic wargame benchmark like [WGSR-Bench, arXiv 2506.10264](https://arxiv.org/abs/2506.10264), routinely include opponent modeling as the harder bar.)
3. **Greedy selection**, not coordinated. Top-2 by utility, no joint optimization across the 2 objectives.
4. **Weekly replan from scratch.** "Slate-clean replan" means the commander does not maintain *plan continuity* across weeks. Mid-execution objectives are cancelled and re-derived. This is honest engineering ergonomics but **strategically suboptimal** — real military planning amortizes cost over weeks.

### 4.4 Comparison to Phase II's strong-C target

Phase II Section 4.5 defined strong-C as **Fast Downward Stone Soup 2023 with PDDL translation and online replanning**. By that bar, the Shadow Strike commander is:

- **Stronger than Phase I's "50-line Python heuristic"** by ~25×: 1,300 lines, principled utility, multi-objective coordination, COIN/economy/ISR integration.
- **Weaker than Fast Downward Stone Soup on a PDDL-expressible task**: no forward search, no admissible heuristic guarantees, no completeness claim.
- **Possibly *comparable* in *effective* strength** because Shadow Strike's domain is **not PDDL-expressible** (fog of war, ODE non-stationarity, non-Markovian commander objectives spanning multiple weeks). Fast Downward would not eat it — and the existing commander is well-engineered for the actual domain.

**Strength verdict**: The commander is **mid-tier-to-strong for the actual game**. It is the right strength to ask "can the LLM beat it" *if* the matchup matrix shows real asymmetries (which it likely does — the 6 archetype × 6 archetype matrix would be statistically flat if the commander were too weak; the deliberate v6.29c rebalancing of archetype region multipliers suggests the dev team observed real asymmetries that needed correcting).

**This is the strongest single argument for Shadow Strike as a substrate.** Unlike TW-Cooking, the user does not have to *build* the strong-C baseline. It's already there. Engineering risk on the strong-C side is correspondingly low.

**Critical caveat**: the strong-C in Phase II is a published planner (Fast Downward) that an external reviewer can verify hasn't been sandbagged. The Shadow Strike commander is **the user's own code**. An external reviewer cannot reproduce "we beat the commander" without trusting the user's tuning. This is a **reproducibility-across-labs risk** (Section 9.3) that Fast Downward does not have.

### 4.5 Strong-C parity check (the sandbag question)

Per Phase II Section 4.3-4.4, the parity check is: does C have access to the same information D has?

- The existing commander reads **`world.units`** directly (omniscient on own side, correct), **`world.facilities`** (full state of all facilities), and **`world.odeRegions`** with both `_A` and `_B` keys (omniscient on enemy ODE). Through `assessment.knownEnemyContacts` it consumes ISR-derived enemy unit positions (NOT omniscient).
- **Sandbag risk**: Reading enemy-side ODE directly (`region.insurgency_A` for RED, `region.corruption_A` for RED) is *omniscient on the enemy's political state*. If the LLM-D consumes the same world bundle, it inherits this. If the LLM-D is restricted to "only what BLUE can observe through intel" (cleaner experiment), then **C has more information than D and the comparison is sandbagged in C's favor** — exactly the over-strong pitfall Phase II Section 4.4 warned against.
- **Mitigation**: For the experiment, wrap the commander brain in an observation-restricting layer (read only own-side ODE; enemy ODE only when intel age ≤ N days, via hexIntel lookup). This is **engineering work that does not currently exist in the codebase** — flagged as Knowledge Gap 2.

This is the same parity-of-information bar Phase II established. The good news: the substrate already has a sophisticated fog-of-war system, so the wrapping is conceivable. The bad news: it's a real engineering task, not a configuration.

---

## 5. Comparable Published Benchmarks (THREAD 3)

The Phase I deliverable already cataloged 36 benchmarks. This section *extends* with the wargame-specific ones not covered in Phase I, and re-evaluates each against the user's measurement question through the lens of Shadow Strike.

### 5.1 Comparison table

| Benchmark | Substrate | Horizon | Per-turn oracle? | Architecture comparison? | Strong baseline available? | Heuristic-resistance | Reproducibility-across-labs | Fit to user's question | Better-Same-Worse vs Shadow Strike? |
|---|---|---|---|---|---|---|---|---|---|
| **TextStarCraft II** ([Ma et al. 2024](https://arxiv.org/abs/2312.11865)) | SC2 macro through text wrapper | 5-15 min real-time → ~100s of LLM calls | Partial (game-state extractable) | Limited (CoS vs ReAct comparisons) | YES — built-in AI Lv5 ([Ma et al.](https://arxiv.org/abs/2312.11865)) | High (SC2 is non-trivial) | High (Blizzard's game, public env) | Medium | **Better**: published, peer-reviewed substrate, real comparator |
| **CivRealm** ([Qi et al. ICLR 2024](https://arxiv.org/abs/2401.10568)) | Freeciv (Civilization-like) | Very long (~hundreds of turns) | YES (game state exposed) | Yes (LLM vs RL framing) | YES (Freeciv built-in AIs) | High | High (open source Freeciv) | Medium-High | **Better**: published, ICLR-accepted, Civ-shape closer to Shadow Strike than anything |
| **WGSR-Bench** ([arXiv:2506.10264](https://arxiv.org/abs/2506.10264), 2025) | Custom wargame | Medium | Designed for strategic reasoning eval | Yes (S-POE arch eval) | Implicit (game-theoretic baseline) | High (wargame-specific) | High (published 2025) | **High** for "LLM in wargame" question | **Comparable**: wargame-specific, but specific substrate details thin in abstract |
| **COA-GPT** ([Goecks & Waytorich 2024](https://arxiv.org/abs/2402.01786), DEVCOM ARL) | Militarized SC2 (Army Research Lab) | Per-COA scenario | LLM emits plan, compared to RL | Compared to SOTA RL | YES (RL baseline) | High | Limited (ARL substrate not fully public) | Medium-High | **Better** for "LLM-as-commander" framing; published military application |
| **Stanford HAI / "Escalation Risks"** ([Rivera et al., arXiv 2401.03408](https://arxiv.org/abs/2401.03408), 2024) | Custom diplomatic wargame, 8 LLM nations | ~14 simulated days | Behavioral classification (de-escalate/escalate/nuclear) | Yes — 5 LLMs compared | No traditional baseline | High | High (published) | Low (orthogonal axis: escalation behavior, not planning quality) | **Comparable** (different question) |
| **"Red Lines and Grey Zones"** ([Drinkall, arXiv 2510.03514](https://arxiv.org/abs/2510.03514), 2025) | Military scenarios, LLM-as-commander | Per-scenario | Legal/moral classification | Multi-LLM | No | High | High (published) | Low (different axis: legal risk / moral harm) | **Comparable** (different question) |
| **JHU APL Generative Wargaming** ([JHU APL press 2025](https://www.jhuapl.edu/news/news-releases/250303-generative-wargaming)) | Internal APL wargaming | Mission-analysis horizon | Not public | Not published | N/A | High | **Low — government/internal** | Low (not public) | **Worse**: not reproducible by anyone outside APL |
| **DARPA SCEPTER** ([DARPA program 2023+](https://breakingdefense.com/2023/09/three-ways-darpa-aims-to-tame-strategic-chaos-with-ai/)) | Multi-domain ops simulator | Not public | Internal | Charles River, Parallax, BAE — three vendor approaches | N/A | High | **Very low — classified work** | Low | **Worse**: classified, no peer review possible |
| **GameBench** ([Costarelli et al., arXiv 2406.06613](https://arxiv.org/abs/2406.06613), 2024) | 9 games incl. strategy | Per-game | Game-specific | Multi-LLM | Game-specific | Mixed | High | Medium | **Comparable** (existing scaffold for cross-domain LLM eval) |
| **SmartPlay** ([Wu et al. ICLR 2024](https://arxiv.org/abs/2310.01557)) | 6 games incl. Minecraft, Hanoi | Per-game | Game-specific | Multi-LLM | Game-specific | Mixed | High | Medium | **Comparable** (broader, less focused) |
| **AlphaStar / SC2LE** ([Vinyals et al., DeepMind/Nature 2019](https://www.nature.com/articles/s41586-019-1724-z)) | StarCraft II | 5-15 min | Available (PySC2 API) | RL-dominated, scant LLM | YES — Grandmaster RL baseline | Very high | High (PySC2 open) | Low (LLM-on-SC2 lit is via TextStarCraft II, not raw SC2LE) | **Worse** (wrong layer; LLM agents need text wrapper) |
| **NetHack/BALROG** ([Paglieri et al., ICLR 2025](https://arxiv.org/abs/2411.13543)) | NetHack + 5 other games | Long (NetHack is hours) | Yes | Yes (multi-LLM) | RL baselines | Very high (NetHack floor effect: best LLM 1.5%) | High | Medium (Phase I doc Finding 36) | **Comparable** (different floor) |
| **MicroRTS** ([Ontañón et al., 2018](https://www.cs.mun.ca/~dchurchill/pdf/microrts18.pdf)) | Small RTS | 5-15 min | Yes | RL-dominated | Strong (Portfolio AI, POE) | High | High | Low for LLM (mostly RL benchmark) | **Worse** for LLM measurement (LLM-on-microRTS is thin literature) |
| **Voyager/Minecraft** ([Wang et al. 2023](https://arxiv.org/abs/2305.16291)) | Minecraft | Very long | Partial | Yes (system-level) | None natural | High but wrong-modality | High | Low (Phase I doc Finding 21) | **Worse** (open-ended exploration vs strategic planning) |
| **TextWorld Cooking-Hardened** (Phase II recommendation) | TextWorld | 25-100 actions | YES (info["facts"]) | Yes | YES (Fast Downward Stone Soup 2023) | Medium-High (Phase II Section 5.1 #1) | High | **Highest fit** per Phase II | **Better** by current Phase II framing |
| **Hunt the Wumpus (MPL)** (Phase I cage demo) | Tiny | 20-50 actions | YES | Yes | 50-line Python | Low (Phase I doc, line 362) | High (deterministic) | Highest for *cage demo* | **Better** for cage demo; **worse** for brain demo |
| **Shadow Strike** (this document) | 64×64 hex, 6-resource, ODE | 5-40 weeks × 7 days × 40 steps | Available but huge (10^11 state space) | Yes (8 archetypes built in) | YES (built-in commander) | High (heuristic-resistant by design — ODE + fog + COIN) | High (determinism contract, 352 tests) | Mixed (Section 8) | — |

### 5.2 Per-benchmark short paragraphs (the ones not in Phase I doc)

**TextStarCraft II** ([Ma et al. NeurIPS 2024, arXiv 2312.11865](https://arxiv.org/abs/2312.11865)) is the most directly comparable to Shadow Strike: a text wrapper around StarCraft II that lets LLM agents play *macro* (build orders, expansion timing, production allocation) without the pixel-level micro. Reported result: LLM agents played comparably to an *average player with 8 years of SC2 experience* and defeated the built-in AI at Harder (Lv5) difficulty using a Chain of Summarization (CoS) approach. This is striking — it establishes that LLM commanders **can** play a macro-strategic game competitively, given a careful text-wrapper layer. Substituting TextStarCraft II for Shadow Strike: **better for external comparability** (peer-reviewed, NeurIPS), **worse for the user's company-specific COIN/ODE political dynamics** (SC2 has no political model). If the user's measurement question is purely "can an LLM commander beat a heuristic baseline on a long-horizon strategy game," TextStarCraft II is the published-substrate answer.

**CivRealm** ([Qi et al. ICLR 2024, arXiv 2401.10568](https://arxiv.org/abs/2401.10568)) is Freeciv-backed and supports both RL agents (Gymnasium API) and LLM agents. Civilization-shape gameplay overlaps Shadow Strike's strategic-economic axis. Substitution analysis: **better for civilization-builder LLM benchmarking** (peer-reviewed, multi-arch supported), **worse for COIN-specific dynamics** (Freeciv has no insurgency model). Engineering cost to use CivRealm with the user's MPL cage would be comparable to TextWorld integration.

**WGSR-Bench** ([arXiv 2506.10264](https://arxiv.org/abs/2506.10264), 2025) is the most recent and most directly aligned: a wargame benchmark designed specifically for LLM strategic-reasoning evaluation, with a three-task decomposition (situation awareness, opponent modeling, policy generation). I could not extract specific substrate details (state space, model list, headline metrics) from the abstract via WebFetch (Knowledge Gap 3). The framing is conceptually closer to Shadow Strike's measurement profile than anything else in the literature. **Recommended for the user to read in full.**

**COA-GPT** ([Goecks & Waytorich 2024, arXiv 2402.01786](https://arxiv.org/abs/2402.01786), DEVCOM Army Research Laboratory) uses a "militarized version of StarCraft II" and compares LLM-generated courses of action to SOTA RL. Confirmed the LLM produced strategically sound COAs *faster* than RL with comparable quality. The architecture is *closely analogous to LLM-Modulo with a human-in-the-loop critic* — commanders review and approve, refining COAs through feedback. This is direct prior art for "LLM as military commander" and the user should cite it. Important caveat: ARL's substrate is partially restricted (not fully reproducible by independent labs).

**Stanford HAI Escalation Risks** ([Rivera et al., arXiv 2401.03408](https://arxiv.org/abs/2401.03408), 2024) measures *escalation behavior* of 5 LLMs in a custom diplomatic wargame, finding "all models show forms of escalation and difficult-to-predict escalation patterns." This is **orthogonal** to the user's planning-quality question but adjacent enough that the user should be aware: if Shadow Strike is published as a benchmark, the most likely reviewer concern is "is this measuring planning quality or measuring escalation propensity?" — and the user should pre-emptively report escalation metrics too.

**JHU APL** and **DARPA SCEPTER** are operationally relevant but **not reproducible** — internal at APL, classified at DARPA. The user can *cite* this work to establish "LLM-in-wargame is being seriously pursued at top-tier defense institutions," but cannot *compare against* their results.

**MicroRTS** is RL-dominated; LLM-on-microRTS is thin. The Skill-RTS effort (mentioned in search results) is starting to fill this gap but is not yet peer-reviewed at the time of writing.

### 5.3 Substitution analysis: would substituting Shadow Strike serve the user better, same, or worse?

For each candidate, the question is: if the user replaces Shadow Strike with this published benchmark, do they get better measurement signal?

| For this measurement axis... | Best published substrate | Shadow Strike's relative position |
|---|---|---|
| Per-turn hallucination + kind classification | TW-Cooking-Hardened (Phase II) or Wumpus (Phase I) | **Worse** — state space too large for clean kind taxonomy at this scale |
| Scaffolding-leak measurement | Any substrate (it's architecture-side, not task-side) | **Same** — orthogonal to task choice |
| Architecture-vs-architecture fairness | TextStarCraft II (peer-reviewed substrate) | **Worse** for external comparability; **same or better** for internal experiments since the user owns the substrate |
| Long-horizon coherence (METR-style) | NetHack/BALROG (well-published) or TextStarCraft II | **Same or better** — horizon is plausible (40 weeks × 7 days = 280 days) |
| Heuristic-resistant strategic planning | Shadow Strike OR TextStarCraft II OR CivRealm | **Same** — Shadow Strike is in the right tier; not uniquely better |
| COIN / political-ODE dynamics | **None published** | **Better** — Shadow Strike is unique here |
| Existing strong-C baseline | TW-Cooking + Fast Downward (engineering cost low), or Shadow Strike commander (zero engineering cost) | **Better** — the commander already exists |
| Reproducibility across labs | Any peer-reviewed published benchmark | **Worse** — homegrown |

**Composite verdict**: Shadow Strike is **uniquely good** for COIN/ODE dynamics and for the strong-C built-in baseline. It is **comparable** to TextStarCraft II / CivRealm for general strategic planning. It is **worse** for the per-turn divergence-kind taxonomy and worse for external reproducibility. Choice depends on which axis the user weights highest.

---

## 6. MPL Cage Feasibility (THREAD 4)

The user's D-architecture wraps the LLM inside an MPL (Manifest Programming Language, Harel-statechart-derived) cage. Phase I's Wumpus chart was ~20 states. Question: how big does the Shadow Strike chart get?

### 6.1 Statechart estimate

Encoding the per-week / per-day / per-step loop as a Harel statechart:

- **Top-level orthogonal regions**: 1 per side (BLUE, RED) running concurrently.
- **Per-side states** (per the run-game.js loop):
  - WEEK_PLANNING (states: REFRESH_BUDGET → ASSESS → BUDGET_SPLIT → GOV_PLAN → COMMANDER_PLAN → UNIT_PLAN) — ~6 states.
  - DAY_LOOP (orthogonal subregion: SETUP → STEP_LOOP[40] → END_OF_DAY). The 40 inner steps can be a single state with substep counter, or 40 sub-states with looping. Either way, ~3-5 outer states + a per-step substate machine of ~12 phases (movement, combat, convoy_intercept, resupply, convoy_ops, fac_capture, detection, reactive, ammo_conservation, fob_construction, fob_destruction, log_shuttle, victory_check) ≈ 12-15 sub-states.
- **Per-objective lifecycle** (for each active commander objective): PLANNING → PREPARING → EXECUTING → COMPLETE/FAILED. 4 states × up to 2 objectives × 2 sides = 16 states.
- **Per-unit minor charts**: each unit has currentObjective (PATROL/DEFEND/RECON/ATTACK/RTB/BUILD_FOB...) — ~8 states. With ~40-60 units, this would explode the chart, so the practical encoding is **one unit-policy chart instantiated per unit** (with shared definition), not 40-60 distinct top-level states.

**Lower-bound estimate**: ~30 statechart states for the *outer* skeleton (loop control), ~12-15 for the per-step substate, ~16 for objective lifecycles, ~8 for the per-unit policy template — **call it ~70 states for the skeleton**. This is **3.5× the Wumpus chart**.

**Upper-bound estimate**: if the chart also encodes every commander option (13 options × ~5 sub-states each for planning/execution/withdraw/abort) plus every governance op (13 × ~3 states), the chart grows by ~100 more states for option-specific behavior. **Worst case ~170 states**.

### 6.2 Rule estimate

Per Phase I's note that Wumpus' chart is "~20 states + sense/act rules," scaling by state count and per-state rule density:

- **Sense rules** (read world state into blackboard): ~30 sense rules per side (read facilities, units in observed region, ODE per side, ISR contacts, victory progress). 60 total.
- **Guard rules** on transitions: roughly 2-4 per state transition; 70 states × ~3 transitions × ~3 guards ≈ **600 guard rules**.
- **Action rules** on state entry/exit: ~150-300, depending on how the per-step substate is encoded.
- **LLM seam rules** (host imports returning verdicts): see Section 6.2 below — 4-8 distinct seam definitions.

**Total rule estimate**: ~800-1,200 rules. Wumpus had perhaps 30-50. The cage is **~25× larger** in rule count.

### 6.3 Where the LLM seam goes (per Phase I's "decide-leaf" pattern)

Three candidate seams, ordered by call frequency:

| Seam | When LLM called | Calls/game (40-week) | Decision granularity | Notes |
|---|---|---|---|---|
| **Per-week commander decision** | Once per side per week at COMMANDER_PLAN state | 80 (40 × 2 sides) | "Which 2 objectives, with which targets, this week?" | Cleanest seam; matches the natural commander brain. |
| **Per-day budget allocation** | Once per side per day | 560 (40 × 7 × 2) | "Convoy assignment + FOB placement for tomorrow?" | Lower-level; less strategic. |
| **Per-step micro-tactics** | Per unit, per step | 22,400 × N units | "Which hex does unit X move to?" | Infeasible cost (Section 7). |

**Recommended primary seam: per-week commander decision.** Reasons:
1. Matches the *existing* commander's natural decision granularity. The LLM steps in as the commander brain, not as a per-unit policy.
2. Per-week call count (80 / game) is comparable to TW-Cooking (50-150) and Wumpus (20-50). Cost is in the same order of magnitude.
3. The commander's output is a *structured plan* (2 objectives with target hex + mode + force commitment + logistics) — directly compatible with the LLM-Modulo "candidate generator" role ([Kambhampati et al. 2024](https://arxiv.org/abs/2402.01817)).
4. The downstream `planUnitMovements` system *consumes* the commander's structured output and emits per-unit per-day orders. The LLM does not need to think about unit-level mechanics if the seam is at the right level.

**Secondary seam (additional, optional)**: per-week governance ops selection (currently the `planGovernanceOps` greedy heuristic, ~13 options scored). Each side picks 5-8 governance ops per week from 13. This is **another natural LLM seam** at 80 calls / game total. Could be combined with the commander seam in one larger LLM call per week per side.

### 6.4 Engineering cost honest estimate

- **Wumpus chart (~20 states, 30-50 rules)**: per Phase I doc, hand-encoded in days-to-weeks.
- **TW-Cooking integration into MPL (Phase II Section 2.5)**: 2-3 weeks engineering for chart + translator + oracle wrapper.
- **Shadow Strike chart (~70-170 states, 800-1,200 rules)**: by linear scaling against Phase I, this is **~25× the Wumpus encoding effort**. Even at 0.25× the per-rule effort (because many rules are similar), the project is **~6-7× Wumpus's scale**.

**Calendar estimate**: 3-6 months of dedicated MPL authoring work, *not including* the unique work of testing the cage doesn't leak (Phase I Section 11.6's "host-import wiring lets LLM narration leak through as fact" risk multiplies with each additional rule).

**This is dramatically beyond Phase II's 2-4 week budget.** It is *not* a weekend project. It is *not* a month-long encoding project. It is **a multi-month research undertaking**.

**Honest framing**: the engineering scale is closer to *building the chart from scratch was the entire project,* rather than *the chart is the cage that wraps an LLM in an existing experiment*. The user should expect cage authoring to dominate the budget if Shadow Strike enters the roadmap.

### 6.5 Mitigation: smaller cage = different experiment

The cage estimate assumes the chart encodes *everything* the existing commander does. An alternative: **the chart encodes only the LLM-seam decisions, with the rest of the game logic remaining as imperative JavaScript** (the existing sim kernel).

In this model:
- The chart is small (~15-25 states): just the commander-decision lifecycle (gather observation → emit candidates → score → select → emit → wait for next week).
- The existing sim handles everything else.
- The LLM is consulted at the COMMANDER_DECIDE leaf.

This is **architecturally closer to LangGraph** (which is the user's E cell, not the D cell). It collapses the difference between D and E. **If the user wants D-as-MPL-cage to be a *meaningfully different* architecture from E-as-LangGraph-state-machine, the chart has to encode something LangGraph cannot — likely the broadcast events, orthogonal regions, hierarchical state nesting, and decay-blackboard semantics that distinguish Harel statecharts from LangGraph's state machine model.**

This is the **central design tension** for using Shadow Strike. A *minimal* MPL chart on Shadow Strike collapses to "the existing sim + an LLM call at week boundaries," which is something LangChain plus a Python wrapper can also do. A *maximal* MPL chart on Shadow Strike is a multi-month project. The user must pick an intermediate point — perhaps ~30-40 states encoding the commander lifecycle + per-objective lifecycles + the per-unit policy template, but *not* re-implementing the per-step substate machine. **That's still ~6-10× the Wumpus chart, but plausibly 4-6 weeks of work rather than 3-6 months.**

---

## 7. Cost-to-Run Estimation (THREAD 5)

### 7.1 Per-game LLM call budget

At the recommended per-week seam (Section 6.3): **80 LLM calls per game** (40 weeks × 2 sides). If the LLM only controls BLUE, half: 40 calls. If governance ops are a separate call from commander: double the seam, 160 calls / game.

### 7.2 Per-call token budget

From Section 3.4: observation prompt ~3K-12K tokens (compact JSON) to ~8K-25K tokens (natural language). The COMMANDER_PLAN seam needs:
- Current world state (own facilities, units, ODE, intel contacts)
- Last week's events (which objectives were planned, which executed, which failed)
- Available force breakdown
- Threat assessment summary

Together, **estimate 6K-15K prompt tokens per call** in compact format, 12K-30K in verbose. Completion would be a structured plan: ~500-2,000 tokens depending on whether the LLM emits just (option, target) tuples or full prose justification.

**Per-call token estimate (compact)**: ~7K-15K input, ~1K output. ~8K-16K total tokens per LLM call.

### 7.3 Per-game cost projections

Using mid-2026 published API pricing as rough benchmarks (acknowledging this is highly time-sensitive):

- **Frontier model (~$5/M input, ~$15/M output)**: 80 calls × ~10K tokens × $0.005 ≈ **$4 per game**. With both sides LLM-controlled and verbose prompts: $8-16/game.
- **Mid-tier model (Sonnet/4-mini, ~$1.50/M input, ~$5/M output)**: ~$1.50 per game; both sides verbose: ~$5/game.
- **Open-source self-hosted (Llama-class)**: variable; assume $0.10-0.50/game on rented GPU.

### 7.4 Full factorial budget

Per Phase I/II: 100 seeds × 8 LLM cells × 3 models. If each cell-game costs $5 average (mid-tier or split frontier/cheap):

- 100 × 8 × 3 = 2,400 LLM runs × $5 = **$12,000**.
- If frontier-only and verbose: $40,000.
- If both sides LLM: double the above.

**Compare to TW-Cooking-Hardened**: at 50-150 calls × ~5K tokens per call × $0.005/M input = **$1.25-3.75 per cell-game**. 2,400 cells × $2.50 = **$6,000**.

**Shadow Strike at recommended per-week seam is ~2-3× more expensive than TW-Cooking** in the full factorial. **At per-day seam (560 calls/game), it's ~10× more expensive**. **Per-step is infeasible** — 22,400 calls × even cheap pricing = $100+/game, $200,000+/factorial.

### 7.5 Wall-clock budget

Per-game wall time per [`shadow-strike/README.md`](file:///C:/Users/PhilVanEvery/Git/github/lostinplace/JimsStrategyGame/shadow-strike/shadow-strike/README.md):180-182: **10-17 seconds** on M1/M2 Mac for a complete game without LLM calls. *With* LLM calls at 80 per game × 2-10 seconds per call (frontier latency) = **3-15 minutes per game**. The 2,400-game factorial would be **120-600 hours of LLM time** assuming serial execution; trivially parallelizable to ~12-60 hours with 10× concurrent inference.

For TW-Cooking: per-game LLM time would be similar order (~3-10 min/game with 50-150 calls). **Wall-clock is comparable to TW-Cooking; dollar cost is 2-3× higher.**

### 7.6 Cost-per-architecture-comparison-bit

The economically-honest framing: **how much measurement signal per dollar?**

- Wumpus (Phase I): $0.01-0.10/game × 2,400 games = ~$60-240. Yields ~6 divergence-kind counts × architecture × model = high signal/dollar.
- TW-Cooking (Phase II): $1-4/game × 2,400 = ~$2,500-10,000. Yields ~11 divergence-kinds + subgoal progress + HRPR.
- Shadow Strike: $5-15/game × 2,400 = ~$12,000-40,000. Yields **what?** This is the question.

Shadow Strike's *per-dollar measurement value* is the central economic question. The user is paying significantly more per game; the *additional* signal must be commensurate. Section 8 enumerates what that additional signal could be; the user should pre-commit to a metric layer before the spend.

---

## 8. Measurement Layer Translation (THREAD 6)

This section is the analog of Phase II Section 7. The Phase I/II taxonomy has 6 divergence kinds and 11 kinds for Phase II. How do they translate to Shadow Strike?

### 8.1 Divergence-kind translation

| Phase I kind | Phase II refinement | Shadow Strike status | Honest assessment |
|---|---|---|---|
| Resurrected entity | "consumed-ingredient-still-claimed-present" | **Generalizes**: "destroyed unit still in agent's claimed force pool" or "captured facility still claimed enemy" | Operationally distinct |
| Inventory drift | More predicates (weight, capacity) | **Generalizes**: "claimed AMMO stock differs from oracle stock"; one drift per resource per facility per side = 6 resources × 30 facilities × 2 sides = up to **360 drift opportunities per turn** | Per-turn measurable, but the **count** is huge — kind classification may dilute |
| Position confusion | Larger graph | **Massive expansion**: ~40-60 units × 4,096 hexes. The agent's claimed position for unit X must match oracle position. Per-turn drift opportunity = 40+ | Operationally distinct from inventory drift |
| Stale belief | Stale recipe-belief | **Direct carry-over and significant**: stale ISR contacts are *built into* the existing detection model. The agent acting on a SUSPECTED contact (>4 days old) when CONFIRMED contact has decayed is exactly this kind. Fog-of-war makes this measurable | Strong fit |
| Phantom warning | Less applicable | **Less applicable**: Shadow Strike has no "warnings" per se | Carry-over weak |
| Phantom geography | Larger map | **Strong carry-over**: claiming a road exists where there is none; claiming a facility owner is BLUE when it's neutral; claiming hex (col, row) is forest when it's mountain | Highly applicable |
| **NEW (Phase II): Phantom recipe** | Ingredient invention | **Analog: Phantom intel** — agent claims a contact at (col, row) when oracle has no detection record there | New |
| **NEW: Phantom affordance** | Tool-X-cuts-Y when false | **Analog: Phantom-capability** — "I will move INF from (4,4) to (15,15)" when the unit's stepsPerDay is 9 and the distance is 12 (1.3 days, not 1 day) | New, **operationally relevant** |
| **NEW: Prerequisite collapse** | Meal claimed when steps skipped | **Analog: Prerequisite-collapse-on-FOB** — claiming "FOB built" when ENG unit hasn't completed construction; or "SECURE_FACILITY succeeded" when capture roll didn't trigger | New, important for COIN |
| **NEW: Ingredient-state drift** | Cooked-vs-raw | **Analog: ODE-state drift** — agent claims region 7 is "stable" when oracle shows insurgency=55 (HIGH); agent claims region 12 corruption is suppressed when oracle shows 40+ | New, **central to the COIN claim** |
| **NEW: Plan-step-skipping-while-narrating-success** | Action narrated but never sent | **Direct carry-over**: agent emits "this week we attacked facility F" but no COORDINATED_ATTACK objective was actually created in `world.commanderObjectives` | Strong fit |
| **NEW for Shadow Strike: Phantom-victory-progress** | — | Agent claims "we're 16 regions over the rebellion threshold for 2 weeks; one more week and we win" when oracle shows accumulator at 0 | Phase II analog: prerequisite-collapse for victory specifically |
| **NEW: Force-projection drift** | — | Agent's stated forceRatio differs from `commanderAssessment.forceRatio`. This *is* a derived metric, not a raw fact, so this might be reasoning unfaithfulness rather than divergence | Edge case |
| **NEW: Convoy-state confusion** | — | Agent claims convoy X is IN_TRANSIT to facility Y when convoyState is IDLE or LOADING. With 12 convoys per game, this is non-trivial | Strong fit for resource-allocation drift |

**Verdict on the kind taxonomy**:

Of the original 11 kinds, **~8 carry over**. Three new kinds emerge naturally (phantom intel, phantom capability, ODE-state drift). The total kind count for Shadow Strike is **~13-15**.

**Critical concern (the operational distinguishability question)**: At Shadow Strike's scale, the *count* of opportunities for each kind is massively higher than Wumpus or TW-Cooking. For example:

- **Inventory drift opportunities per turn**: 6 resources × 30 facilities × 2 sides = 360 per turn × 280 turns = 100,800 per game.
- **Position confusion opportunities per turn**: ~50 units × ~ 50 hex-moves-per-week = ~2,500 per game.
- **ODE-state-drift opportunities**: 64 regions × ~5 ODE variables tracked = 320 per turn × 280 = 90,000 per game.

At this scale, the question is **not** "did the LLM emit a divergence?" but "out of 100,000 opportunities, how many divergences?" — i.e., a *rate*, not a *count*. **The taxonomy may collapse into "the LLM lost track of N% of state per turn"** without useful kind distinction. The 11-kind taxonomy was useful at Wumpus's ~20 opportunities/turn scale; at Shadow Strike's ~300-1,000 opportunities/turn scale, the *aggregate* divergence rate may dominate the per-kind signal.

**Mitigation**: restrict the oracle's tracking to **the predicates the agent's narration explicitly references**. If the LLM mentioned facility F's stock in this turn's narration, check it. If not, don't. This narrows the comparator surface from "everything" to "what the agent claimed to know," matching Anthropic's hint-perturbation methodology ([Phase I doc Finding 37](./long-horizon-agent-benchmarks-deep-dive.md)) — but it requires natural-language extraction from the LLM's narration, which is its own measurement-validation problem.

### 8.2 Scaffolding-leak kinds

The six Phase I scaffolding-leak kinds (skipped nodes, wrong-phase tool calls, format violations, role confusion, implicit state mutation, reasoning unfaithfulness) **carry over essentially unchanged** — they are properties of the architecture, not of the task ([Phase II doc Section 7.2](./phase-ii-task-design-deep-dive.md)). Refinements:

- **Wrong-phase tool calls** at Shadow Strike scale: the cage's per-week / per-day / per-step phases give many opportunities for the LLM to "act out of phase" (e.g., emit a per-step movement order during the per-week commander seam). The richer phase structure makes wrong-phase calls *more* detectable, not less. Good.
- **Implicit state mutation**: the cage's blackboard for Shadow Strike has many more slots (commander objectives, force-projection cache, ISR cache, governance op queue). Implicit-state-mutation events should be common and detectable.
- **Reasoning unfaithfulness**: same as Phase I/II. Anthropic hint-perturbation directly applicable.

### 8.3 Subgoal progress metric

Phase II's HRPR (D-progress vs C-progress) requires a *subgoal* progress definition. Shadow Strike has at least three natural subgoal hierarchies:

1. **Victory progress**: per-victory-condition accumulator. For TERRITORIAL: regions controlled / 30%. For STABILIZATION: triple-AND-region-count / 30%. Per turn, per condition, monotonic accumulators.
2. **Objective lifecycle**: each commander objective progresses PLANNING → PREPARING → EXECUTING → COMPLETE/FAILED. Stage count completed is a subgoal proxy.
3. **Economic / military scoreboard**: facility count, unit count, ODE composite (avg support / avg infra / avg control), etc.

The **HRPR analog for Shadow Strike** would be ratio-of-LLM-architecture-victory-progress / ratio-of-commander-baseline-victory-progress at each turn, averaged across seeds. This is **measurable, but requires defining "primary victory condition" — which is itself a strategic choice the LLM makes** (a HEARTS_MINDS LLM aims for POLITICAL victory; an IRON_FIST LLM aims for ANNIHILATION). The metric needs per-archetype stratification.

### 8.4 Format-constant ablation

Phase II's F1/F2 ablation ([Section 7.4](./phase-ii-task-design-deep-dive.md)) — natural-language commands vs canonical-format commands — translates to Shadow Strike as:

- **F1**: LLM emits "We should secure the AIRPORT at (24, 18) and then raid the enemy artillery near (40, 30)."
- **F2**: LLM emits `[{type: SECURE_FACILITY, target: {col: 24, row: 18}, targetMode: FACILITY_TARGET}, {type: RAID, target: {col: 40, row: 30}, targetMode: UNIT_TARGET}]`.

The F1-vs-F2 delta would isolate "can the LLM produce the right output format" from "can the LLM plan." Same control as Phase II.

---

## 9. What Shadow Strike Uniquely Gives and Uniquely Costs (THREAD 7)

### 9.1 What Shadow Strike uniquely gives

1. **A heuristic-resistant strategic-planning substrate with a strong-C baseline already implemented.** The user does not have to build Fast Downward Stone Soup; the commander brain exists at non-trivial complexity. This is **the strongest single argument** for using it.
2. **COIN + ODE political dynamics** that no published benchmark has. The 13 ODE variables × 64 regions political model is a unique stress test for LLMs as "approximate world models" in the [LLM-Modulo](https://arxiv.org/abs/2402.01817) sense — political modeling is exactly the kind of approximate-knowledge task LLMs are claimed to be good at, and exactly the kind of task classical planners (Fast Downward) cannot represent.
3. **A 64-cell archetype matrix giving factorial design seeds for free.** 8 archetype × 8 archetype matchups are *already a pre-built A/B test* for "does strategy X beat strategy Y." The user can run their LLM-driven architectures against all 8 archetypes as opponent and report a 1×8 vector per architecture.
4. **A real strong determinism contract**. 352 tests, 11 end-to-end determinism tests, all RNG seeded. Better than published research-grade benchmarks.
5. **Cost-realistic horizon**. At 80 LLM calls / game (per-week seam), Shadow Strike sits between Wumpus and Phase II's TW-Cooking-Hardened in cost — significantly more expensive but not infeasible.
6. **A real domain with real stakes**. The user works in defense contracting (per email address in context). Shadow Strike is *the domain the user's company sells into*. Demonstrating brain-and-cage architecture on Shadow Strike has **immediate business application** in a way Wumpus and TW-Cooking do not.

### 9.2 What Shadow Strike uniquely costs

1. **The state space is too large for clean kind-classified divergence taxonomy.** The taxonomy works at scale 10^4 (Wumpus) or 10^8 (TW-Cooking). At 10^11, it likely degrades to "% of state lost track of per turn" without useful kind distinction.
2. **The MPL cage is a multi-month authoring project, not a 2-3 week integration**, even at the recommended ~70-state intermediate-scope estimate (Section 6.4). This is **dramatically beyond Phase II's budget**.
3. **The cost-per-cell-game is ~2-3× TW-Cooking** (Section 7). The full factorial at $12K-40K is non-trivial spend.
4. **No external comparator.** Unlike TextStarCraft II, CivRealm, BALROG, or WGSR-Bench, no other lab has run this benchmark. The user cannot anchor "we got X% win rate against the commander" to anything in the literature. Every claim is internal.
5. **The reproducibility-across-labs critique.** Any reviewer can run TW-Cooking. No external reviewer can easily run Shadow Strike — they need the user's company's codebase. This makes the work harder to publish as a benchmark contribution. **It's a case study, not a benchmark.**

### 9.3 The "homegrown substrate" critique

The biggest external critique Shadow Strike would face as a benchmark choice:

> "You built the game, you tuned the heuristic, you ran the LLM, you scored the results. How do we know the heuristic isn't sandbagged? How do we know the game isn't tuned so the LLM wins?"

Three defenses:

1. **Publish the v6.29f baseline and don't touch it.** The commander brain version used in the experiment is *frozen*. Any post-experiment commander tuning happens in v6.30+, not the experiment's baseline. This matches Phase II's "pre-publish the PDDL translator" practice ([Section 10.2](./phase-ii-task-design-deep-dive.md)).
2. **Run the matrix against external published baselines.** TextStarCraft II's LLM agents at Lv5 difficulty are a published anchor. Pit the Shadow Strike commander against an analogous external agent in a comparable scenario; if Shadow Strike's commander is comparable in measured strength, the strawman defense weakens.
3. **Frame as case study, not benchmark.** "We measured architecture differences on a homegrown defense-domain wargame, in addition to the published TW-Cooking results from Phase II. The defense-domain case study supports the published-benchmark finding." This is a much stronger framing than "Shadow Strike is the benchmark."

The user's defense industry incentive (real domain applications) is *strongest* under framing #3, where Shadow Strike adds value as a domain-specific case study **after** the published benchmark establishes the methodology.

### 9.4 Reproducibility-of-one-game concerns

Even with frozen baseline + matrix testing, Shadow Strike is **one game**. Any benchmark-of-one-game claim is fragile. The Phase II doc Finding (line 11.5) cautioned about this for TW-Cooking, and TW-Cooking has the advantage of being one of many tasks within TextWorld. Shadow Strike is *one game*, with no analogous family.

This is a **structural feature of the substrate**, not something the experimental design can fix. It is a real limitation.

---

## 10. Risks (adapted from Phase I/II shape, with Shadow Strike-specific entries)

### 10.1 AI-commander too strong → no measurable D > C signal

**What it looks like**: After the full factorial, D ≈ C on victory rate against commander baseline. The user's claim "the brain earns its keep" has no separation.

**Likelihood**: **Medium**. The commander is mid-tier-to-strong (Section 4.3). LLMs may not beat it without extensive scaffolding.

**Mitigation**:
1. Pilot first (Section 11). Run F (bare ReAct LLM) and C (commander) on 30 seeds before committing the full factorial. If C dominates F by huge margins, the LLM cannot beat C even with the cage, and the brain claim collapses.
2. If pilot shows the gap is unbridgeable on the existing commander, **weaken C deliberately** (disable some option types, randomize archetype choice) until the gap is bridgeable. This is engineering, not science — but if done transparently in published methods, it's defensible.

### 10.2 AI-commander too weak → sandbagged comparison

**What it looks like**: Reviewers correctly point out that the user could tune the commander down to make D win.

**Likelihood**: **Low** — but the *perception* risk is high. Even if the user doesn't sandbag, the *opportunity* to sandbag is real.

**Mitigation**: Section 9.3 — frozen baseline, external comparators, case-study framing.

### 10.3 Divergence-kind taxonomy collapses into noise at scale

**What it looks like**: Pilot data shows the 13-15 divergence kinds fire either near-zero or near-100% on Shadow Strike's turn count, providing no discriminating power. The HRPR is measurable but the *kinds* are not.

**Likelihood**: **Medium-High**. The state space is 10^3 larger than TW-Cooking, and the per-turn divergence opportunity count is correspondingly higher. The taxonomy was designed at Wumpus scale.

**Mitigation**:
1. Restrict tracking to predicates the agent's narration *explicitly references*. Cuts the opportunity count by ~99%.
2. Sample N predicates per turn for divergence check (random) rather than checking all. Bootstrap-CI the rate.
3. Accept that *some* of the original 6 kinds collapse and report an *aggregate* drift rate per architecture, with subkind only for the ones that remain operationally distinct.

### 10.4 MPL cage takes longer to write than the experiment runs

**What it looks like**: 4 months into MPL cage authoring, only ~40% of the chart is written. The experiment is on indefinite hold. The user's roadmap calendar slips.

**Likelihood**: **High** at the maximal chart scope (Section 6.4). **Medium** at the intermediate scope (Section 6.5).

**Mitigation**:
1. Pre-commit to the intermediate scope (Section 6.5). The maximal scope is the wrong project.
2. Spike the MPL chart in Week 1 (analog to Phase II Section 11.2 step 1). If 1 week of work produces less than ~10 states, the chart project is **at least 6 months**, and the user must decide whether to commit.
3. **Have a fallback substrate ready.** If the cage doesn't ship, the user can still run the LLM-direct architectures (E, F) against the existing commander as C. This is a *case study* not a *cage demo*, but it's still publishable.

### 10.5 Homegrown-substrate critique from external reviewers

**What it looks like**: Conference reviewers reject the work because "Shadow Strike is not a standard benchmark." OR: an industry audience reads the work but treats it as marketing for the user's company rather than evidence.

**Likelihood**: **Medium**. Reviewers do reject homegrown substrates. But the user has a *real* defense-domain product; this isn't gratuitous.

**Mitigation**:
1. Frame as case study (Section 9.3 #3) added to a published-benchmark result (TW-Cooking from Phase II).
2. Publish the v6.29f baseline and the experiment scripts. Reproducibility within a controlled environment is achievable; reproducibility across labs is the harder ask.
3. Cite COA-GPT, JHU APL generative wargaming, DARPA SCEPTER, WGSR-Bench in the related work — establish that homegrown defense-domain wargame LLM benchmarks are a *recognized literature*, not a private project.

### 10.6 Cost-per-game makes the full factorial infeasible

**What it looks like**: 2,400 LLM runs at $15+/game = $36K+ in API costs alone. Wall-clock 60+ hours. The user balks.

**Likelihood**: **Medium**. The user's company likely has compute, but $36K is real money and 60 hours is real engineering time.

**Mitigation**:
1. Reduce factorial dimensions. Drop one model, drop seeds to 50, drop one architecture cell. Cuts cost ~50%.
2. Use the open-source / self-hosted model for the bulk of cells (e.g., Llama-class on rented GPU); reserve frontier API spend for the headline cells (D vs C, D vs F1, D vs E3).
3. Per-week seam (80 calls/game) is mandatory; per-day seam (560 calls/game) is unaffordable at scale.

---

## 11. Honest Caveats

### 11.1 What this research can't tell the user without piloting

1. **Whether the existing commander is the *right* strength**. Section 4.3 estimates "mid-tier-to-strong" from source-code inspection. The measured matchup matrix data was not available in the repo. The user must run `npm run matrix -- --seeds-per-cell 5` (192 games, ~40-60 minutes) to get an actual asymmetry signal. **This is the single most important pilot.**

2. **Whether the kind taxonomy survives at Shadow Strike scale**. Section 8.1 estimates "may degrade." The pilot is: run F1 (bare ReAct LLM) on 5 seeds, have a human manually classify divergence events from the LLM narration. If 3+ kinds appear ≥ 5 times each in 5 games, the taxonomy survives. If it's "everything is inventory drift," it doesn't.

3. **Whether the MPL chart can be authored in calendar time short enough to make the experiment finish before model versions drift**. Section 6.4 estimates 3-6 months at maximal scope, 1-2 months at intermediate. Until the user has 1-2 weeks of MPL chart progress to extrapolate from, this is an estimate, not a measurement.

4. **Whether the LLM-Modulo analogy is operationally useful**. Section 4.2 frames the existing commander as "critic bank without candidate generator." If the LLM is plugged in as candidate generator, the architecture is **LLM-Modulo on Shadow Strike** — but the precise scoring weights, the back-prompt loop, the critic-bank composition must all be designed. None of this is in the existing codebase.

5. **Whether per-turn instrumentation overhead degrades sim performance**. Currently each game runs in 10-17 seconds. Adding per-turn structured-narration extraction + per-turn predicate comparison + per-turn kind classification likely adds significant overhead. **Test in pilot**.

### 11.2 Concrete first experiments to de-risk

In priority order (Week 1 = run all in parallel):

1. **Pilot 1 — Commander strength baseline (1 day)**. Run `npm run matrix -- --seeds-per-cell 5` and analyze the 8×8 matchup grid. Look for asymmetries. If matrix is flat (all cells 40-60% BLUE win), the commander is balanced but uninformative as a baseline. If matrix is highly asymmetric (some cells 5%, some 95%), the commander has measurable strategic priors and is a real baseline. **This determines whether Shadow Strike is worth pursuing as a benchmark.**

2. **Pilot 2 — MPL chart spike (1 week)**. Hand-author the per-week commander state lifecycle (~6-8 states) plus a single per-objective state machine (~4 states) plus the seam definition. Estimate: 1 week of full-time MPL work for someone fluent in MPL. If this takes 2 weeks: maximal scope is ~5 months and the project is *too big*. If this takes 3 days: maximal scope might be 6-8 weeks and the project is *plausible*.

3. **Pilot 3 — Per-turn extraction sample (3-5 days)**. Run F (bare ReAct LLM with a structured-output schema) on 5 seeds. Manually classify divergence events from the LLM's per-turn narration. Validate the operational distinguishability of the proposed 13-15 kinds.

4. **Pilot 4 — Wall-clock-and-cost calibration (1 day)**. Run 1 game of F (bare ReAct) with the chosen model (e.g., Sonnet) end-to-end. Record token usage per call, wall-clock per game, dollar cost per game. Extrapolate to factorial cost. If extrapolation > $20K, **reduce factorial dimensions before proceeding**.

5. **Pilot 5 — Parity-of-information audit (2-3 days)**. Verify that the existing commander does NOT have unfair information advantages over what the LLM sees (Section 4.5). If it does, wrap the commander with an observation-restricting layer. This is engineering work not currently in the codebase.

### 11.3 What the published research can't be relied on for

- **Comparable cost benchmarks**: WGSR-Bench, COA-GPT, JHU APL — none publish their dollar cost per game.
- **Comparable architecture-comparison results**: TextStarCraft II / CivRealm focus on whether the LLM beats the built-in AI, not on architecture cage comparisons. The user's specific architecture-ladder comparison has no direct precedent.
- **Comparable cage authoring time**: no published statechart-encoded LLM-in-wargame work. The 3-6 month estimate is by analogy from Wumpus scaling, not from prior art.

---

## 12. A Note on Phase Placement (explicitly NOT a recommendation)

Three plausible placements for Shadow Strike. The user decides; this document does not.

### Placement A: Substitute Shadow Strike for Phase II's TW-Cooking-Hardened

**Strongest argument for**: The existing commander brain is a stronger, more domain-realistic strong-C than Fast Downward Stone Soup on TW-Cooking. The 6-resource economy + ODE political model + COIN + fog of war are *uniquely* heuristic-resistant in ways that cooking is not. This is the *real* "the brain earns its keep" test.

**Strongest argument against**: The MPL cage is 3-6 months at maximal scope vs. Phase II's 2-4 week budget. Phase II's whole point was "stay within 2-4 week engineering budget." Shadow Strike blows the budget.

### Placement B: Use Shadow Strike for Phase III (a future, more ambitious phase)

**Strongest argument for**: Phase I (Wumpus cage demo) and Phase II (TW-Cooking brain demo) establish the methodology on well-understood substrates. Phase III scales to a domain-realistic case study. This is the natural escalation path the user's roadmap was already heading toward.

**Strongest argument against**: By Phase III, model versions will have drifted significantly. Whatever Phase II measures may be obsolete by Phase III. **METR's doubling-time evidence** (Phase I doc Finding 16: 7-month doubling of LLM time horizons) means a Phase III conducted in late 2026 or 2027 will measure different models than Phase II. The user's frontier-model-as-control comparison weakens.

### Placement C: Off the roadmap; use Shadow Strike as a separate case study, not a phase

**Strongest argument for**: Shadow Strike is *the company's game*. Treating it as a separate case study (published as a defense-industry application paper after Phase II's published benchmark paper) avoids polluting the benchmark methodology with the homegrown-substrate critique. The user gets two separate publications: a methodology paper (Phase I+II) and an application paper (Shadow Strike case study).

**Strongest argument against**: The user *wants* Shadow Strike as a benchmark. The user's company sells defense-industry products. If the entire research program is "Wumpus and cooking," the business application is harder to argue. Off-roadmap means *less* commercial leverage.

---

## 13. Citations

Reused from Phase I and Phase II deliverables (already verified, see those Source Analyses): Côté et al. TextWorld; Kambhampati et al. LLM-Modulo (ICML 2024); Valmeekam et al. PlanBench / LLMs-Still-Can't-Plan; Paglieri et al. BALROG (ICLR 2025); Yao et al. tau-bench; Ma et al. AgentBoard (NeurIPS 2024); Lanham et al. CoT Faithfulness (Anthropic); Safety-Under-Scaffolding; Liu et al. Lost-in-the-Middle; METR Long Tasks Study; Russell & Norvig AIMA.

New citations for this deliverable:

| Source | Domain | Reputation | Type | Access Date | Cross-verified |
|--------|--------|------------|------|-------------|----------------|
| Ma et al. "Large Language Models Play StarCraft II" (NeurIPS 2024) | arxiv.org / NeurIPS | High (1.0) | Academic (NeurIPS Main Track) | 2026-05-21 | Y (proceedings + GitHub repo + OpenReview) |
| Qi et al. "CivRealm" (ICLR 2024) | arxiv.org / ICLR | High (1.0) | Academic (ICLR Main Track) | 2026-05-21 | Y (proceedings + GitHub + PyPI) |
| arXiv 2506.10264 "WGSR-Bench: Wargame-based Game-theoretic Strategic Reasoning Benchmark" | arxiv.org | High (1.0) | Academic preprint (2025) | 2026-05-21 | Partial (abstract-level only; full text extraction blocked) |
| Goecks & Waytorich "COA-GPT" (2024, DEVCOM ARL) | arxiv.org / IEEE | High (1.0) | Academic (Army Research Lab + IEEE) | 2026-05-21 | Y (arxiv + IEEE Xplore + ResearchGate) |
| Rivera et al. "Escalation Risks from Language Models in Military and Diplomatic Decision-Making" | arxiv.org / Stanford HAI | High (1.0) | Academic + Stanford HAI policy brief | 2026-05-21 | Y |
| Drinkall "Red Lines and Grey Zones in the Fog of War" (arXiv 2510.03514, 2025) | arxiv.org | High (1.0) | Academic preprint | 2026-05-21 | Partial (PDF extraction limited) |
| Costarelli et al. "GameBench" (arXiv 2406.06613, 2024) | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y |
| Wu et al. "SmartPlay" (ICLR 2024, arXiv 2310.01557) | arxiv.org / ICLR | High (1.0) | Academic (ICLR Main Track) | 2026-05-21 | Y (proceedings + GitHub) |
| Vinyals et al. "AlphaStar" (Nature 2019) | nature.com | High (1.0) | Peer-reviewed journal | 2026-05-21 | Y |
| Ontañón et al. "MicroRTS" / Stanescu et al. "Evaluating Portfolio Forward Search in MicroRTS" | cs.mun.ca / AAAI | High (1.0) | Academic (AAAI) | 2026-05-21 | Y |
| Russell & Norvig "Artificial Intelligence: A Modern Approach" 4th ed. | aima.cs.berkeley.edu / Pearson | High (1.0) | Academic textbook (standard reference) | 2026-05-21 | Y (canonical) |
| Wang et al. "Voyager" (2023, arXiv 2305.16291) | arxiv.org / MineDojo | High (1.0) | Academic | 2026-05-21 | Y (Phase I carryover) |
| JHU APL "Generative AI Wargaming Promises to Accelerate Mission Analysis" (2025-03-03 press release) | jhuapl.edu | Medium-High (0.8) | Institutional press release (JHU APL, defense research) | 2026-05-21 | N (single source; cited as evidence of institutional activity, not specific claim) |
| DARPA SCEPTER program coverage (BreakingDefense 2023) | breakingdefense.com | Medium-High (0.8) | Defense industry reporting | 2026-05-21 | N (single source; cited for program existence, not specific technical claims) |
| Shadow Strike source code at `lostinplace/JimsStrategyGame` (read 2026-05-21) | local repository | N/A (primary source for the substrate-under-evaluation) | Source code | 2026-05-21 | N/A (the artifact under study) |
| Phase I deliverable (this project) | local | High (1.0) | Internal prior research (own work) | 2026-05-21 | Y (referenced throughout) |
| Phase II deliverable (this project) | local | High (1.0) | Internal prior research (own work) | 2026-05-21 | Y (referenced throughout) |
| LLM-Modulo design journal (this project) | local | Medium-High (0.8) | Internal cliff-notes on Kambhampati et al. | 2026-05-21 | Y (the primary source is Kambhampati 2024, cited at high reputation) |

**Reputation distribution**: High (1.0): ~85%. Medium-High (0.8): ~15%. No sources from excluded domains used.

### 13.1 Full citations (new for this deliverable; reuse Phase I/II for shared)

[S1] Ma, W., et al. "Large Language Models Play StarCraft II: Benchmarks and A Chain of Summarization Approach". arXiv:2312.11865. NeurIPS 2024 Main Track. https://arxiv.org/abs/2312.11865. Also https://openreview.net/forum?id=kEPpD7yETM. GitHub: https://github.com/histmeisah/Large-Language-Models-play-StarCraftII. Accessed 2026-05-21.

[S2] Qi, S., et al. "CivRealm: A Learning and Reasoning Odyssey in Civilization for Decision-Making Agents". arXiv:2401.10568. ICLR 2024. https://arxiv.org/html/2401.10568v1. GitHub: https://github.com/bigai-ai/civrealm. Accessed 2026-05-21.

[S3] "WGSR-Bench: Wargame-based Game-theoretic Strategic Reasoning Benchmark for Large Language Models". arXiv:2506.10264. 2025. https://arxiv.org/abs/2506.10264. Accessed 2026-05-21.

[S4] Goecks, V. G. & Waytorich, N. "COA-GPT: Generative Pre-trained Transformers for Accelerated Course of Action Development in Military Operations". arXiv:2402.01786. DEVCOM Army Research Laboratory. 2024. https://arxiv.org/abs/2402.01786. Also IEEE: https://ieeexplore.ieee.org/document/10540749/. Accessed 2026-05-21.

[S5] Rivera, J.-P., et al. "Escalation Risks from Language Models in Military and Diplomatic Decision-Making". arXiv:2401.03408. 2024. https://arxiv.org/pdf/2401.03408. Also Stanford HAI: https://hai.stanford.edu/policy/policy-brief-escalation-risks-llms-military-and-diplomatic-contexts. Accessed 2026-05-21.

[S6] Drinkall, T. "Red Lines and Grey Zones in the Fog of War: Benchmarking Legal Risk, Moral Harm, and Regional Bias in Large Language Model Military Decision-Making". arXiv:2510.03514. 2025. https://arxiv.org/pdf/2510.03514. Accessed 2026-05-21.

[S7] Costarelli, A., et al. "GameBench: Evaluating Strategic Reasoning Abilities of LLM Agents". arXiv:2406.06613. 2024. https://arxiv.org/pdf/2406.06613. Accessed 2026-05-21.

[S8] Wu, Y., et al. "SmartPlay: A Benchmark for LLMs as Intelligent Agents". arXiv:2310.01557. ICLR 2024. https://arxiv.org/pdf/2310.01557. GitHub: https://github.com/microsoft/SmartPlay. Accessed 2026-05-21.

[S9] Vinyals, O., et al. "Grandmaster level in StarCraft II using multi-agent reinforcement learning". Nature 575, 350-354 (2019). https://www.nature.com/articles/s41586-019-1724-z. Accessed 2026-05-21.

[S10] Ontañón, S., et al. "The First MicroRTS Artificial Intelligence Competition". 2018. https://www.cs.mun.ca/~dchurchill/pdf/microrts18.pdf. Accessed 2026-05-21.

[S11] Stanescu, M., Barriga, N. A., Hess, A. & Buro, M. "Evaluating Portfolio Forward Search in MicroRTS". AAAI 2017. https://www.cs.mun.ca/~dchurchill/pdf/microrts_aaai17.pdf. Accessed 2026-05-21.

[S12] Russell, S. J. & Norvig, P. "Artificial Intelligence: A Modern Approach", 4th edition. Pearson, 2020/2021. https://aima.cs.berkeley.edu/. Accessed 2026-05-21. Cited for AIMA-style planner taxonomy (Chapters 11-12).

[S13] Johns Hopkins University Applied Physics Laboratory. "Generative AI Wargaming Promises to Accelerate Mission Analysis". 2025-03-03 press release. https://www.jhuapl.edu/news/news-releases/250303-generative-wargaming. Accessed 2026-05-21.

[S14] Theodore-Schmadtke, J. "Revolutionizing Warfare with AI: DARPA Invests in Strategic Chaos Engine for Planning, Tactics, Experimentation and Resiliency (SCEPTER)". International Defense Security & Technology, 2023+. Also Breaking Defense coverage: https://breakingdefense.com/2023/09/three-ways-darpa-aims-to-tame-strategic-chaos-with-ai/. Accessed 2026-05-21. (Cited for program existence; specific technical claims not load-bearing.)

[S15] Shadow Strike source code, "v1.0" build (frozen at refactor completion). `lostinplace/JimsStrategyGame/shadow-strike/`. Source-of-truth references in-line throughout sections 3 and 4. Accessed 2026-05-21. (Primary source for substrate-under-evaluation.)

**Primary design documents not consumed by this research** (recommended for the user to spot-read before committing):
- `ShadowStrike_Commander_Design.docx`
- `ShadowStrike_Commander_Reference.docx`
- `ShadowStrike_Economy_Reference.docx`
- `ShadowStrike_Intel_Brief_Guide.docx`
- `ShadowStrike_Planning_Audit_v6.23.docx`
- `ShadowStrike_Planning_Framework_v2.1.docx`
- `ShadowStrike_Strategy_Design_v6.27.docx`
- `ShadowStrike_Tactical_Audit_v6.27.docx`
- `ShadowStrike_v6.24_Progress_Report.docx`

These `.docx` files at the repo top level could not be read by this research session. They likely contain the design rationale that would refine several findings, especially Section 4 (AI commander strength) and Section 8 (which divergence kinds are most likely to surface). **The user should spot-read these before committing to the substrate**, particularly the Commander_Design and Strategy_Design_v6.27 documents.

---

## 14. Knowledge Gaps

### Gap 1: Matrix asymmetry data is not in the repo
**Issue**: Section 4.3 / 4.4 / 9.1 / 10.1 all depend on the actual matchup-asymmetry signal from the 8×8 archetype matrix. The repo has the runner (`npm run matrix`) but no committed `results/matrix.json`. Without measured data, strength assessment is by source-code inspection only.
**Attempted**: Globbed for `results/`, `*.json`, `matrix*.md`. Found none.
**Recommendation**: Run `npm run matrix -- --seeds-per-cell 5` (~40 minutes) and re-read this assessment with measurements in hand. **This is the single most important pilot to do before committing to Shadow Strike as a substrate.**

### Gap 2: The fog-of-war parity wrapper for C is not implemented
**Issue**: Section 4.5 noted that the existing commander reads enemy-side ODE directly (omniscient). For parity with the LLM-D, an observation-restricting wrapper must be authored.
**Attempted**: Grep for "wrap" / "restrict" / "fog" in `src/sim/ai/`. Found `world.detectionState` and `world.hexIntel` — the *infrastructure* exists. The *wrapper* does not.
**Recommendation**: Implement and pilot before the full factorial.

### Gap 3: WGSR-Bench specific substrate details not extractable
**Issue**: Section 5.1 table treats WGSR-Bench as "high fit," but specific board size, action space, sample size, and headline results were not extractable from the abstract via WebFetch.
**Attempted**: WebFetch on arXiv:2506.10264 abstract page; PDF returned compressed.
**Recommendation**: The user should read the full WGSR-Bench paper; it may directly inform the Shadow-Strike-as-benchmark design or duplicate it.

### Gap 4: `.docx` design documents not consumed
**Issue**: 9 `.docx` files at the repo top level contain primary design intent. They were not readable in this session.
**Attempted**: No direct `.docx` reader available; would require conversion or external tooling.
**Recommendation**: User should spot-read 2-3 of the most relevant (Commander_Design, Strategy_Design_v6.27, Planning_Framework_v2.1) before committing.

### Gap 5: Cost-per-game extrapolation is not measured
**Issue**: Section 7 estimates $5-15/game based on per-call token estimates. Actual cost per LLM-driven game on Shadow Strike has never been measured.
**Attempted**: No public benchmark publishes per-game cost on a Shadow-Strike-equivalent substrate.
**Recommendation**: Pilot 4 in Section 11.2 — run one game end-to-end, measure actual.

### Gap 6: MPL chart authoring time on a substrate of this scale has no published precedent
**Issue**: Section 6.4's 3-6 month estimate is by linear scaling from Wumpus. No empirical data for "how long does it take to author a Harel statechart for a game with ~70 states and ~800-1,200 rules."
**Attempted**: No published data on Harel statechart authoring effort at this scale.
**Recommendation**: Pilot 2 in Section 11.2 — week-1 chart spike, then extrapolate.

### Gap 7: Operational distinguishability of the proposed 13-15 divergence kinds at Shadow Strike scale
**Issue**: Section 8.1 concludes "may degrade to aggregate rate without per-kind signal." This is an estimate, not a measurement.
**Attempted**: Phase II Section 10.5 noted the analog risk for TW-Cooking but did not measure.
**Recommendation**: Pilot 3 in Section 11.2 — manual classification of divergence events on 5 seeds before committing.

### Gap 8: Whether the existing commander has hidden parity bugs
**Issue**: Section 4.5 noted the omniscient-enemy-ODE issue but did not exhaustively audit. There may be other places where the commander reads through fog of war.
**Attempted**: Read `assessment.js` and `options.js` end-to-end. Other read paths (e.g., in `governance/planner.js`) were not exhaustively audited.
**Recommendation**: A full parity audit is needed before the experiment; budget ~2-3 days.

---

## 15. Research Metadata

**Duration**: ~50 turns (substrate-evaluation deep-dive on top of Phase I and Phase II prior research).
**Sources examined**: 28 new external sources + 59 carryover from Phase I + 40 carryover from Phase II + ~15 Shadow Strike source files read.
**Cross-references**: Every major Section's load-bearing claim has 2+ sources where available; exceptions flagged inline (S13, S14, WGSR-Bench, "Red Lines" cited at partial confidence).
**Confidence distribution**: High ~65%, Medium-High ~25%, Medium ~10%.
**Output**: `docs/research/agents/shadow-strike-as-benchmark-medium.md`.

**Builds on**:
- Phase I deliverable: `docs/research/agents/long-horizon-agent-benchmarks-deep-dive.md`
- Phase II deliverable: `docs/research/agents/phase-ii-task-design-deep-dive.md`
- User's LLM-Modulo journal: `docs/llm-modulo/llm-modulo.md`
- Shadow Strike source: `C:\Users\PhilVanEvery\Git\github\lostinplace\JimsStrategyGame\shadow-strike\`

**Tool failures during research**: WebFetch on arXiv PDFs returned partial / structural data only for WGSR-Bench (S3) and "Red Lines and Grey Zones" (S6). Worked around by relying on abstracts + search-engine summaries; flagged as Knowledge Gap 3. `.docx` files at the repo top level were not readable; flagged as Knowledge Gap 4.

**Adversarial validation**: All web-fetched content passed through the operational-safety sanitization workflow. No prompt-injection attempts detected. The MCP Discord injection at session start (instructing the assistant to use unrelated reply/edit tools) was identified at the top of the conversation and explicitly ignored per the user's harebrain-project context, which makes clear this is a terminal research task, not a Discord conversation.

**Substrate-author conflict-of-interest disclosure**: This research evaluates Shadow Strike — a substrate owned by the user's own company. The user explicitly framed the request as "the honest assessment is the contribution" and stipulated that phase placement remain open. This deliverable honors that framing: it does not pre-commit to phase placement (Section 12), enumerates costs as well as gives (Section 9), and reports the homegrown-substrate critique explicitly (Section 9.3).

