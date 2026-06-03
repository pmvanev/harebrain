# Definitions

A glossary of harebrain and LLM-benchmark terms used across this repo.

## Instruction-following benchmarks

| Term | Definition |
|---|---|
| **ComplexBench** | A benchmark for how well LLMs follow **complex, composite instructions** — prompts chaining multiple constraints (and / chain / selection / nesting). Scores whether *every* constraint is met, not just the gist. |
| **AdvancedIF** | An **advanced instruction-following** benchmark using expert-written, hard, multi-constraint prompts with rubric-based grading — probing how reliably models honor demanding, real-world instructions. |

## The harebrain thesis

| Term | Definition |
|---|---|
| **harebrain** | The core bet of the doc series: `harebrain = fast LLM brain × structured game-AI cage`. Neither half does the long-horizon agent job alone; the combination might. |
| **The cage** | The structured half: bounded state, hierarchical decomposition, typed shared memory, utility-scored choice, and a meta-loop watching the inner loop. Owns *where* the agent is and what's next. |
| **The brain** | The LLM half: rich, judgment-heavy work done inside the leaves of the cage. Owns *what* to do, not *where*. |
| **The seam** | The single boundary where brain meets cage: one typed value crossing in one direction. The chart asks, the LLM answers a verdict, the chart decides whether to act. |
| **Tier 1–5 (structural latitude)** | A gradient of how much freedom the LLM has: 1 oracle (returns a verdict) → 2 instantiator → 3 per-instance editor → 4 author (writes new chart source) → 5 bare Python (no cage). Higher tiers = less the cage can guarantee. |
| **Two clocks** | Slow clock = compile-time, human-reviewed chart authoring; fast clock = runtime, autonomous selection among declared options. Keeps Tier-1 guarantees while letting the system evolve. |
| **The four-layer stack** | **Policy** (MPLv2 — invariants) wraps **Orchestration** (LangGraph — structure) wraps **Agent** (LangChain — capability) wraps **Model** (the LLM — judgment). Each layer's clock is ~1–2 orders of magnitude slower than the one below. |

## Game-AI primitives (the cage's parts)

| Term | Definition |
|---|---|
| **Blackboard** | Typed, keyed, persistent shared memory (the `UBlackboardData` pattern). The agent prompt is built from named slots, not a rolling transcript. |
| **Working-memory facts** | Blackboard facts with timestamps and decaying confidence (F.E.A.R. pattern). Stale facts decay to "low confidence" rather than persisting as if fresh; pinned facts ignore age. |
| **HSM / hierarchical statechart** | The topology owner (Harel; UE State Trees). Enforces "you are *in* this state"; transitions out require a satisfied guard — preventing premature conclusion. |
| **Utility AI** | A scoring layer that picks tools/sub-agents by normalized response curves over signals (cost, success rate, freshness) — making choice inspectable, tunable, replayable. |
| **AI Director** | An outer loop (from *Left 4 Dead*) watching the inner loop: modulates verbosity, escalates scrutiny, injects "are you stuck?" interrupts, restarts on detected loops. |
| **EDD** | **Expectation-Driven Development** — a supervision protocol whose adversarial-review step becomes the director's job; expectations attach to states as transition guards. |

## MPL / statechart terms

| Term | Definition |
|---|---|
| **MPLv2 / MPL** | The execution model that makes the statechart cage executable. Ticks, deterministic conflict resolution, declared signal interfaces. The Policy layer of the stack. |
| **Manifest** | MPLv2's immutable per-tick snapshot of the *whole* system (active regions, signals, variables, regionmaps), recomputed atomically each tick. A blackboard's rigorous, global, transactional sibling. |
| **Host import** | The seam mechanism: the chart declares a typed contract (`host import { decide(scene) -> string }`), the embedder registers a Python function satisfying it, and a rule routes on the return value. |
| **Conflict resolution** | MPLv2's deterministic tiebreak for competing proposals: `@priority` → `@weight` → seeded RNG. Same inputs + same seed → same trace. |

## LLM-Modulo (Kambhampati et al., ICML 2024)

| Term | Definition |
|---|---|
| **LLM-Modulo** | A Generate-Test-Critique framework where the LLM produces candidates and external **sound verifiers** judge them. Argues LLMs can't plan or self-verify alone, but help inside the loop. |
| **Generate-Test-Critique loop** | LLM generates a candidate → critic bank tests it → on disagreement a meta-controller pools critiques into one back-prompt → LLM regenerates → on agreement, return the solution. |
| **Hard critic** | A model-based, *sound* verifier (VAL for PDDL, a simulator, unit tests). Soundness of the whole framework is inherited from the hard critics. |
| **Soft critic** | A style/preference/explicability verdict, often itself LLM-based. Needs a meta-controller and back-prompt loop; carries no soundness guarantee. |
| **Obfuscation gap** | The accuracy drop when a problem's tokens are renamed but its structure is unchanged (Blocksworld ~50% → Mystery-BW ~1%). Measures how much "performance" was retrieval, not reasoning. |
| **Back-prompt** | A single consolidated critique fed back to the LLM as its next prompt. Pass rates climb across back-prompt rounds when a sound critic is present. |

## The wumpus engine & experiment matrix

| Term | Definition |
|---|---|
| **wumpus engine** | The Python package (`python/packages/wumpus/`) every experiment cell plays. Faithful Yob 1973 at the core, extensible at the seams, observable by construction. |
| **Yob 1973 / faithful** | Bug-for-bug fidelity to Robert Yob's original *Hunt the Wumpus* — verbatim messages (including the `RAMDOM` typo), dodecahedron topology, exact rules. The BASIC source wins all disputes. |
| **Surface (seam)** | A single object holding every player-facing string and symbol. Swapping it relabels the game without touching topology or rules — the engine works on internal IDs and translates at the boundary. |
| **Mystery Wumpus** | A relabeled surface (rooms → `α β …`, senses → unfamiliar vocabulary) over a byte-identical engine and seed. The variant that produces the obfuscation gap. |
| **Ledger (JSONL)** | The append-only, schema-validated, one-event-per-turn telemetry file. The source of truth for analysis — notebooks read JSONL, never the live engine. |
| **Experiment matrix (cells A–G)** | The runs over seeded scenarios: **A** scripted, **B** random-legal, **C** heuristic (controls, no LLM); **D** harebrain (LLM at MPL leaf via host import); **E** LangGraph, **F** LangChain (trusted-narrator agents); **G** wild baseline (a coding agent handed the game, no constraints on its scaffolding). |
| **Ablation (cell C)** | A non-LLM brain inside the cage. If C wins at nearly D's rate, the cage did the work and the brain didn't pull weight — itself a real finding. |
| **Escalation ladder (L2/L3/L4)** | Additive variant rules over the base engine: L2 wumpus-moves-when-startled, L3 partial observability, L4 bigger/non-dodecahedron graph. Each drops in as config, not a rewrite. |
| **Divergence event** | A diff between an LLM's claimed state (its narration) and the ledger's actual post-state — e.g. agent says room 5, oracle says room 12. |
| **Scaffolding leak** | Per-node-per-turn tagging (via the LangGraph harness's optional `actor_node` field) revealing which part of the agent graph produced an action. |
| **ABC framework** | "Best Practices for Building Rigorous Agentic Benchmarks" (Zhu et al. 2025) — the quality bar the benchmark-runner must meet: per-seed solvability, oracle solver, statistical significance, baseline reporting, judge validation. |

## Learning & cognition (cross-cutting concepts)

| Term | Definition |
|---|---|
| **Hebbian learning** | "Neurons that fire together, wire together" (Hebb, 1949). A *local*, correlational rule: a synapse strengthens when its pre- and post-synaptic neurons activate together — no global error signal, no labels. The unsupervised counterpoint to backprop, and the reason the **credit assignment problem** is hard: local rules can't easily attribute a distant outcome to an early weight. |
| **Clever Hans** | The horse that "did arithmetic" by reading unconscious cues from its handler rather than computing. In ML: a model that gets the right answer *for the wrong reason* — exploiting spurious correlations or dataset artifacts instead of the intended capability. The **obfuscation gap** is a Clever Hans detector: rename the tokens, and retrieval-not-reasoning collapses. |
| **Homunculus fallacy** | "Explaining" a capability by positing a little intelligent agent *inside* that already has that capability — an infinite regress that explains nothing, just relocates the mystery. The trap when crediting **the brain** with "understanding" or "planning": the word does work the mechanism hasn't earned. LLM-Modulo's insistence on *sound external verifiers* is partly a refusal of this fallacy. |
| **Credit assignment problem** | Deciding which decisions deserve credit (or blame) for an eventual outcome — *temporal* (which earlier action mattered, under delayed/sparse reward) and *structural* (which component or weight). The core difficulty of long-horizon agency, and a thing **the cage** attacks structurally: hierarchical decomposition and per-state guards localize blame to a state rather than smearing it across a 50-turn transcript. |
