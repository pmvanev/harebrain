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
| [A harness for every task](docs/research-summaries/dynamic-workflows/article.md) | Dynamic workflows in Claude Code ([summary](docs/research-summaries/dynamic-workflows/summary.md)). |

## Primary source

Harel, D., "Statecharts: A Visual Formalism for Complex Systems," *Science of Computer Programming* 8 (1987), pp. 231–274 — included here: [state-charts-harel.pdf](docs/research-summaries/harel/state-charts-harel.pdf).
