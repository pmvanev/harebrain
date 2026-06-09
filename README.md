# harebrain

Design-journal notes on game-AI primitives, statecharts, and LLM agency.

## The series

| Note | About |
|---|---|
| [Harebrain, *sketched*](docs/harebrain/harebrain.md) | Where game-AI primitives, statecharts, and LLM agency meet — and which intersections pay back. |
| [MPLv2, read against Harel's *Statecharts*](docs/mpl/mpl.md) | The cage made executable: Manifest, ticks, deterministic conflict resolution, declared signal interfaces. |
| [Traditional Game AI *Primitives*](docs/game-ai/game-ai.md) | The first-class building blocks of game-AI design, annotated for what ships in Unreal. |
| [Expectation-Driven Development](docs/edd/edd.md) | A validation framework for AI-agent code — the editor's tools, not the author's. |

## Research summaries

Distilled readings of external papers and articles, under [`docs/research-summaries/`](docs/research-summaries/). Each summary lives in its own directory following the same convention:

- a summary `*.md` written in the project's house style (a *distilled* / *redrawn* take, not a transcript);
- an `images/` folder of theme-adaptive SVG figures (and a `glyph.svg` masthead) that redraw the source's key diagrams;
- the source PDF alongside, where the original is a paper.

| Summary | Source |
|---|---|
| [Statecharts, *distilled*](docs/research-summaries/harel/harel.md) | Harel's 1987 statecharts paper — depth, orthogonality, broadcast (PDF included). |
| [LLM-Modulo, *redrawn*](docs/research-summaries/llm-modulo/llm-modulo.md) | LLMs Can't Plan, But Can Help Planning in LLM-Modulo Frameworks (PDF included). |
| [MEBN & PR-OWL, *distilled*](docs/research-summaries/mebn-prowl/mebn-prowl.md) | Multi-Entity Bayesian Networks: first-order probabilistic knowledge for a variable number of entities. |
| [AdvancedIF, *graded*](docs/research-summaries/advanced-if/advanced-if.md) | Rubric-based benchmarking and RL for advancing LLM instruction following (PDF included). |
| [Rigorous agentic benchmarks, *audited*](docs/research-summaries/agentic-benchmarks/agentic-benchmarks.md) | Best practices for building rigorous agentic benchmarks (PDF included). |
| [ComplexBench, *composed*](docs/research-summaries/complexbench/complexbench.md) | Benchmarking complex instruction following with multiple-constraint composition (PDF included). |
| [The tri-agent clarification framework, *staged*](docs/research-summaries/tri-agent-clarification/tri-agent-clarification.md) | Evaluating and aligning question-clarification capabilities of LLMs (PDF included). |
| [AgentSpec, *fenced*](docs/research-summaries/agentspec/agentspec.md) | A trigger–predicate–enforce DSL that intercepts the agent loop at runtime for safe, reliable LLM agents (PDF included). |
| [OS-Symphony, *conducted*](docs/research-summaries/os-symphony/os-symphony.md) | A computer-using-agent framework with milestone-driven long-term memory and trajectory-level self-correction — 65.84% on OSWorld (PDF included). |
| [Natural-Language Agent Harnesses, *interpreted*](docs/research-summaries/nlah/nlah.md) | Agent harnesses as editable natural-language documents interpreted by a runtime (IHR) (PDF included). |
| [Meta-Harness, *searched*](docs/research-summaries/meta-harness/meta-harness.md) | End-to-end search for the harness code that stores, retrieves, and presents context to the model (PDF included). |
| [AgentOS, *envisioning*](docs/research-summaries/agentos/agentos.md) | A natural-language-driven agent operating system: NUI portal, Skills-as-Modules, intent mining over a personal knowledge graph (PDF included). |
| [Harness Engineering, *practised*](docs/research-summaries/harness-engineering/harness-engineering.md) | Böckeler's practitioner taxonomy of the outer harness teams build around coding agents (martinfowler.com). |
| [The Anatomy of an Agent Harness, *dissected*](docs/research-summaries/agent-harness-anatomy/agent-harness-anatomy.md) | Decomposing `Agent = Model + Harness` into its component organs (LangChain blog). |
| [AI agent benchmarks are broken, *indicted*](docs/research-summaries/benchmarks-broken/benchmarks-broken.md) | Daniel Kang's polemic on broken task/outcome validity — the op-ed companion to the ABC paper (Medium). |
| [Benchmark Data Contamination, *quarantined*](docs/research-summaries/benchmark-contamination/benchmark-contamination.md) | The survey under harebrain's "obfuscation gap" — detection loses the arms race, so the wumpus engine generates its problems instead of shipping them (PDF included). |
| [Assessing LLM-as-a-Judge, *cross-examined*](docs/research-summaries/assessing-judges/assessing-judges.md) | Sage: validating the judge with no ground-truth key, via consistency axioms — the soft-critic validation harebrain's ABC pillar left open (PDF included). |
| [Evaluation Engineering, *instrumented*](docs/research-summaries/evaluation-engineering/evaluation-engineering.md) | The eval harness as a software product with its own failure modes — operational reliability, orthogonal to benchmark validity; the wumpus runner is a harness (PDF included). |
| [Autorubric, *calibrated*](docs/research-summaries/autorubric/autorubric.md) | The construction manual for the soft critic — analytic rubric decomposition, per-criterion explanation as optimization signal, and why reliability ≠ validity (PDF included). |
| [Multi-Agent Debate for LLM Judges, *deliberated*](docs/research-summaries/judge-debate/judge-debate.md) | Collaborative debate beats majority voting — but only with a correct seed; the productive counterweight to Sage's "debate hurts," resolved by protocol (PDF included). |
| [CollabEval, *convened*](docs/research-summaries/collabeval/collabeval.md) | The soft-critic panel as a guarded HSM: independent eval → consensus gate → bounded discussion → strong-judge fallback; orchestration, not averaging (PDF included). |
| [When "Better" Prompts Hurt, *iterated*](docs/research-summaries/eval-driven-iteration/eval-driven-iteration.md) | Define-Test-Diagnose-Fix + MVES; a generic "be helpful" prompt silently broke grounding — the empirical case for the cage (PDF included). |
| [A harness for every task](docs/research-summaries/dynamic-workflows/article.md) | Dynamic workflows in Claude Code ([summary](docs/research-summaries/dynamic-workflows/summary.md)). |

## Reference

- [Benchmarks](benchmarks.md) — a categorized map of LLM & agent benchmarks (knowledge, coding, agents, computer-use, safety, methodology), with links and the build-vs-borrow framing for evaluating harebrain.
- [Definitions](definitions.md) — glossary of harebrain, game-AI, and LLM-benchmark terms used across the repo.

## Primary source

Harel, D., "Statecharts: A Visual Formalism for Complex Systems," *Science of Computer Programming* 8 (1987), pp. 231–274 — included here: [state-charts-harel.pdf](docs/research-summaries/harel/state-charts-harel.pdf).
