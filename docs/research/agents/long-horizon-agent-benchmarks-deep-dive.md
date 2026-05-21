# Research: Long-Horizon Autonomous LLM Agent Benchmarks — Hallucination, Scaffolding Compliance, and Architecture Comparison

**Date**: 2026-05-21 | **Researcher**: nw-researcher (Nova) | **Confidence**: High on landscape claims; Medium on experimental-design recommendations | **Sources**: 59 cited, 85%+ from High-reputation tier (arxiv.org, NeurIPS/ICLR/ACL conferences, anthropic.com, openai.com, microsoft.com research, langchain.com docs)

## Executive Summary

**Does an off-the-shelf benchmark fit the user's needs?** Partially, not fully. No single existing benchmark provides all four of (a) per-turn ground-truth divergence with kind classification, (b) per-node scaffolding-leak instrumentation, (c) architecture-comparison framing where scaffolding-richness is the independent variable, and (d) a closed-form world model small enough to instrument every event. The closest off-the-shelf combination is **tau-bench** (policy-compliance + end-state diff), **AgentBoard** (subgoal-level progress rate as a per-turn proxy), and **Project Ariadne** (causal scoring of reasoning-vs-action). These three would have to be combined as separate evaluations, which is more engineering than building a custom instrumentation layer on a known-good substrate.

**Single recommended path forward**: Keep MPL Hunt the Wumpus as the Phase 1 task — it is the right substrate for the cage-demo because its world state is closed-form and small enough to oracle every turn. **Stop there for Note 1** (the cage-demo, validating zero divergence by construction in D and meaningful divergence in E/F). **Plan to graduate to a TextWorld-generated, longer-horizon task family for Note 2** (the brain-demo, where horizon must be long enough that lost-in-the-middle and METR-style time-horizon effects can discriminate architectures). The user's L2-L4 escalation ladder is plausible but converges on TextWorld's design space anyway; reusing TextWorld's game-generator avoids reinventing it.

**Three critical design corrections** suggested by the literature: (1) **format-constant control across scaffolds** is mandatory, not optional — Safety-Under-Scaffolding's 62,808-evaluation study shows scaffold-induced format conversion is a large confound. (2) The user's "MPL-caged LLM" is **not** in unexplored territory; Formal-LLM, AGENT-C, VeriGuard, FlowAgent, behavior-tree-LLM hybrids, and AgentBoard's progress-rate methodology all live in the same space. Framing should be "richer formalism than the FSMs currently dominant" not "no prior art." (3) Borrow Anthropic's hint-perturbation methodology (Finding 37) for the reasoning-unfaithfulness leak class — it gives a concrete operational definition that ties the user's work to the broader CoT-faithfulness literature.

**Confidence**: High on benchmark-landscape factual claims (3+ sources each). Medium on the experimental-design recommendations, which depend on the user's exact resource budget and the specific properties of their MPL runtime that this research did not interrogate directly.

## The User's Measurement Requirements (Restated)

The user wants to measure, across architectures (single-LLM-on-context < orchestrated-multi-LLM < graph-orchestrated LangGraph < state-chart/MPL-caged LLM):

1. **Hallucination / world-model divergence** — per-turn diff between agent's claimed state and ground-truth oracle state, with kind-classification (resurrected entity, inventory drift, position confusion, stale belief, phantom warning, phantom geography).
2. **Scaffolding compliance** — per-node-per-turn violations of declared topology (skipped nodes, wrong-phase tool calls, format violations, role confusion, implicit state mutation, reasoning unfaithfulness).
3. **Mistakes / disallowed actions** — attempts (and successes) at illegal, inappropriate, or unnecessary actions.
4. **Architecture-vs-architecture fairness** — holding model, prompt content, seeds, and tool surface constant while varying scaffolding structure.
5. **Long-horizon, multi-stage workflow** — task horizon long enough that drift and context-drift become measurable.

Critically: the user needs **per-turn ground-truth instrumentation**, not just episode-end task-success. Most published benchmarks measure the latter.

## Landscape: Existing Benchmarks

| Benchmark | Horizon | What's measured | Per-turn hallucination? | Scaffolding compliance? | Architecture comparison? | Fit |
|---|---|---|---|---|---|---|
| AgentBench | Medium | Task success across 8 envs | No | No | Model-comp only | Low |
| GAIA | Medium | Final-answer correctness | No | No | Yes (any agent) | Low |
| tau-bench | Medium-long | End-state DB-diff + policy adherence + pass^k | End-of-episode only | Partial (policy text) | Yes | Medium-High |
| SWE-bench / Verified / Pro / EVO | Long | Test-suite pass on final patch | No | No | Yes | Low (wrong domain) |
| WebArena / VisualWebArena | Long | DB state diff after task | No | No | Yes | Low (floor effect, no per-turn) |
| OSWorld | Long | Execution-based eval (369 tasks) | No | No | Yes | Low (GUI-grounding bottleneck) |
| ALFWorld | Short-medium | Task success (POMDP, ~98% SOTA) | Available via TextWorld | No | Yes | Medium |
| ScienceWorld | Medium | Task success | Available via TextWorld | No | Yes | Medium |
| ToolEmu | Medium | LLM-judge safety + helpfulness | LLM-judge per trajectory | No | Yes | Medium (unsafe-action axis) |
| AppWorld | Medium-long | State-based unit tests + unexpected-change check | End-of-episode only | No | Yes | Medium-High |
| AssistantBench | Medium-long | Task accuracy (named hallucination) | Task-level only | No | Yes | Low (floor effect) |
| MLAgentBench | Very long | ML task success | No | No | Yes | Low (contamination warning) |
| BrowseComp | Medium-long | Short-answer correctness | No | No | Yes | Low |
| HaluEval / TruthfulQA | Single-turn | Q&A factuality | Single-turn only | No | Model-comp | No |
| METR HCAST + RE-bench | Calibrated by human-time | 50%-success time horizon | No | No | Yes (any agent) | Medium (complementary metric) |
| AgentBoard | Medium-long | Fine-grained progress rate via subgoals | Subgoal-level (closest) | No | Yes | Medium-High (methodology inspiration) |
| Anthropic AgentMisalignment | Medium | Propensity for misbehavior | No | No | Yes | Low (different axis) |
| TextWorld (substrate) | Tunable | Whatever you instrument | YES (full ground truth) | Build-your-own | Yes (build harnesses) | High (substrate) |
| Jericho | Long (Zork etc.) | Score progression | No (no oracle) | No | Yes | Low |
| Crafter | Long | 22 achievements | Partial (achievements) | No | Yes | Medium (wrong modality) |
| Voyager / MineDojo | Very long | Open-ended | No | No | Yes | Low (engineering overhead) |
| NLE / BALROG | Long | Score / per-game metric | No | No | Yes | Medium (good comparator) |
| Cicero / Diplomacy | Long | Game outcome | No | No | Yes | Low (multi-agent noise) |
| AvalonBench / Werewolf Arena / WOLF | Medium | Win rate + deception rate | Deception (deliberate) | No | Yes | Low (orthogonal axis) |
| LLM-Cave | Medium | Success rate on Wumpus-like | No | Strategy comparison only | Strategy-comp (CoS, P-C) | Medium (closest task analogue) |
| BeliefShift | Multi-session | Belief consistency over dialogue | Multi-session | No | Yes | Medium (methodology) |
| FlowAgent / Formal-LLM / AGENT-C / VeriGuard | N/A (system papers) | Workflow compliance | No (system papers) | Yes (their thesis) | N/A | Medium (prior art) |
| Project Ariadne / FaithCoT-Bench | Single-task | Causal faithfulness of stated reasoning | Reasoning-vs-action only | No | Yes | High (methodology for one leak class) |

**Reading the table**: the user's specific requirement — *per-turn ground-truth state divergence with kind-classification + per-node scaffolding-leak instrumentation + architecture-comparison framing, all in one* — is **not satisfied by any single off-the-shelf benchmark**. Several come close on one or two axes:
- **tau-bench** has the closest "policy-compliance + state-fidelity" combination but checks end-of-episode only.
- **AgentBoard** has the closest progressive-scoring philosophy (subgoals) but does not generalize per-turn diff to the user's "kind" taxonomy.
- **LLM-Cave** uses essentially the user's chosen task but measures success-rate of reasoning strategies, not divergence kinds.
- **TextWorld** is the strongest *substrate* if the user is willing to build their own instrumentation on top.

## Findings

### Finding 1: AgentBench — multi-environment but model-comparison, not architecture-comparison
**Evidence**: "AgentBench is a multi-dimensional evolving benchmark that currently consists of 8 distinct environments to assess LLM-as-Agent's reasoning and decision-making abilities in a multi-turn open-ended generation setting... 25 LLMs (including APIs and open-sourced models)... Poor long-term reasoning, decision-making, and instruction following abilities are the main obstacles for developing usable LLM agents."
**Source**: [Liu et al., "AgentBench: Evaluating LLMs as Agents"](https://arxiv.org/abs/2308.03688) - Accessed 2026-05-21
**Confidence**: High
**Verification**: [GitHub repository](https://github.com/THUDM/AgentBench), [HuggingFace paper page](https://huggingface.co/papers/2308.03688)
**Analysis**: AgentBench is designed as a model-comparison benchmark, not an architecture-comparison benchmark. It standardizes the agent loop and varies the underlying LLM. There is no native instrumentation for "is the agent's claimed state diverging from oracle state per-turn." For the user's question (architecture A vs B vs C vs D), AgentBench provides a useful environment suite but not the metrics. Fit: **Low** for direct use; **Medium** as one of several environment sources you could borrow a task from.

### Finding 2: GAIA — real-world multi-step, but black-box scoring
**Evidence**: "GAIA proposes real-world questions that require fundamental abilities such as reasoning, multi-modality handling, web browsing, and generally tool-use proficiency... 466 questions, each requiring multiple reasoning steps to answer... human respondents obtain 92% accuracy versus 15% for GPT-4 equipped with plugins."
**Source**: [Mialon et al., "GAIA: a benchmark for General AI Assistants"](https://arxiv.org/abs/2311.12983) - Accessed 2026-05-21
**Confidence**: High
**Verification**: [HuggingFace paper page](https://huggingface.co/papers/2311.12983), [OpenReview](https://openreview.net/forum?id=fibxvahvs3)
**Analysis**: GAIA evaluates *final answer correctness* against ground-truth, not per-turn world-model fidelity or scaffolding compliance. The horizon is moderate (multi-step but typically not deep-recursive), and there is no oracle for "did the agent claim something false at turn 7." Architecturally, GAIA is agnostic — any agent that produces a final answer is scored — so it does support architecture comparison, but only on a single coarse outcome metric. Fit: **Low** for hallucination-per-turn measurement; **Medium** as an "agent in the wild" task pool if you want realistic browsing tasks.

### Finding 3: tau-bench — closest existing analogue for policy-compliance + state-fidelity
**Evidence**: "τ-bench emulates dynamic conversations between a user (simulated by language models) and a language agent provided with domain-specific API tools and policy guidelines... Success is determined by a deterministic comparison of end database state with an annotated goal state, irrespective of the conversational trajectory... it measures whether it can do so consistently multiple times."
**Source**: [Yao et al., "τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains"](https://arxiv.org/abs/2406.12045) - Accessed 2026-05-21
**Confidence**: High
**Verification**: [Sierra research blog](https://sierra.ai/blog/tau-bench-shaping-development-evaluation-agents), [GitHub repo](https://github.com/sierra-research/tau-bench)
**Analysis**: This is the closest off-the-shelf benchmark to what the user wants. It has (a) explicit policy documents the agent must adhere to (analogue of "scaffolding compliance"), (b) ground-truth database state at end-of-episode (analogue of "ground-truth oracle"), (c) multi-turn dynamic interaction, and (d) a deterministic check via state-diff. The pass^k metric (consistency across k runs) is one of the few benchmark metrics that captures reliability under stochasticity. **However**: tau-bench's ground-truth check is end-of-episode, not per-turn. It does not catch "the agent claimed it cancelled the order at turn 3 but actually didn't" if the agent then self-corrects by turn 8. It also does not classify divergences by *kind*. Fit: **High** as a starting point for adaptation; **Medium** as-is.

### Finding 4: METR's long-horizon study — directly relevant context for *why* this question matters
**Evidence**: "GPT-2's horizon was two seconds; Claude 3.7 Sonnet's was 50 minutes; o3's was nearly two hours... Opus 4.6's 50% horizon was around 12 hours... doubling time of around 7 months... The increase in AI models' time horizons seems to be primarily driven by greater reliability and ability to adapt to mistakes, combined with better logical reasoning and tool use capabilities."
**Source**: [METR, "Measuring AI Ability to Complete Long Tasks"](https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/) - Accessed 2026-05-21
**Confidence**: High
**Verification**: [arxiv preprint](https://arxiv.org/abs/2503.14499), [Alignment Forum mirror](https://www.alignmentforum.org/posts/deesrjitvXM4xYGZd/metr-measuring-ai-ability-to-complete-long-tasks)
**Analysis**: METR's framing — that the relevant capability is the *task duration* over which an agent maintains coherence — is essentially the user's measurement target stated as a scalar. Their methodology (calibrate task difficulty by human-completion-time, measure 50%-success-horizon) is a useful auxiliary metric, but does **not** measure hallucination or scaffolding compliance per-turn. METR's tasks are heavily software-engineering-skewed (their HCAST + SWE-bench-V + RE-bench task pool), so importing the methodology directly would shift the user's domain. Fit: **Medium** as a complementary headline metric (time-horizon-at-50%-pass-rate per architecture) alongside the user's own metrics; **Low** as a standalone benchmark for hallucination measurement.

### Finding 5: SWE-bench / SWE-bench Verified / SWE-bench Pro — long-horizon coding, but state-tracking is implicit
**Evidence**: "SWE-Bench Verified... state-of-the-art systems improving from 1.96% in October 2023 to roughly 78% by spring 2026... SWE-Bench Pro... 1,865 problems sourced from a diverse set of 41 actively maintained repositories... long-horizon tasks that may require hours to days for a professional software engineer to complete, often involving patches across multiple files... SWE-EVO... constructed from release notes of seven mature open-source Python projects, comprising 48 tasks requiring multi-step modifications spanning an average of 21 files."
**Source**: [Princeton NLP SWE-bench (original)](https://arxiv.org/abs/2310.06770), [SWE-bench Pro](https://arxiv.org/abs/2509.16941), [SWE-EVO](https://arxiv.org/abs/2512.18470) - Accessed 2026-05-21
**Confidence**: High
**Verification**: Multiple papers in the SWE-bench family with consistent methodology
**Analysis**: SWE-bench evaluates by *test-suite-pass* on the final patch. The agent's intermediate claims ("I have edited file foo.py to do X") are never checked against ground truth during the run. State-tracking is implicit — if the agent loses track of which files it has edited, that shows up only at the end as a failed test. This is the same end-of-episode-only limitation as tau-bench. Fit: **Low** for the user's hallucination measurement question; **Medium** as a long-horizon stress test of whatever architecture wins on Wumpus-equivalent.

### Finding 6: WebArena / VisualWebArena — long-horizon browsing, but huge ceiling effect with no per-turn ground truth
**Evidence**: "WebArena includes 812 long-horizon web-based tasks, and the best GPT-4-based agent achieves an end-to-end task success rate of 14.41%, significantly lower than the human performance of 78.24%... VisualWebArena... 910 realistic tasks... best VLM agents achieve a success rate of 16.4%... human performance of 88.7%."
**Source**: [Zhou et al., "WebArena"](https://arxiv.org/abs/2307.13854), [Koh et al., "VisualWebArena"](https://ar5iv.labs.arxiv.org/html/2401.13649/) - Accessed 2026-05-21
**Confidence**: High
**Verification**: [WebArena GitHub](https://github.com/web-arena-x/webarena), [VisualWebArena GitHub](https://github.com/web-arena-x/visualwebarena)
**Analysis**: WebArena has a *floor* problem — base models can barely succeed at all, so architecture differences could be masked by floor effects. The ground-truth check is execution-based (the website's database after the agent's actions matches the expected state) and again end-of-episode. There is no per-turn instrumentation of "the agent claimed the cart had 3 items but it actually had 2." Fit: **Low** for the user's question; useful as a high-difficulty long-horizon task pool if they later want to stress-test their best architecture.

### Finding 7: OSWorld — open-ended computer use, even larger ceiling effect
**Evidence**: "OSWorld is the first-of-its-kind scalable, real computer environment for multimodal agents... 369 computer tasks involving real web and desktop apps in open domains, OS file I/O, and workflows spanning multiple applications... While humans can accomplish over 72.36% of the tasks, the best model achieves only 12.24% success, primarily struggling with GUI grounding and operational knowledge."
**Source**: [Xie et al., "OSWorld"](https://arxiv.org/abs/2404.07972) - Accessed 2026-05-21
**Confidence**: High
**Verification**: [OSWorld project page](https://os-world.github.io/), [NeurIPS 2024 poster](https://neurips.cc/virtual/2024/poster/97468)
**Analysis**: OSWorld is even more brutal than WebArena in floor-effects. The grounding bottleneck (mapping language to pixel coordinates) dominates, which is *not* what the user wants to measure. The user wants to measure reasoning/state-tracking architecture differences, not GUI-grounding. Fit: **Low** — wrong-axis.

### Finding 8b: ToolEmu — sandbox for unsafe-action measurement, but no per-turn world-model check
**Evidence**: "ToolEmu is a framework that uses an LM to emulate tool execution and enables the testing of LM agents against a diverse range of tools and scenarios... 36 toolkits (311 tools) and 144 test cases... 68.8% of failures identified with ToolEmu would be valid real-world agent failures. Even the safest LM agent exhibits failures 23.9% of the time."
**Source**: [Ruan et al., "Identifying the Risks of LM Agents with an LM-Emulated Sandbox"](https://arxiv.org/abs/2309.15817) - Accessed 2026-05-21
**Confidence**: High
**Verification**: [ToolEmu GitHub (ICLR'24 Spotlight)](https://github.com/ryoungj/ToolEmu)
**Analysis**: ToolEmu measures *whether* an agent took an unsafe action (analogue of the user's "attempts at disallowed/inappropriate actions"). It is one of the strongest existing benchmarks for that specific axis. **But**: the safety verdict is rendered by an LLM judge, which introduces noise the user's deterministic oracle would not have. And ToolEmu does not measure scaffolding-compliance or world-model divergence per turn. Fit: **Medium** — useful as design inspiration for the "disallowed actions" metric, especially the idea of an emulated environment where ground-truth allow/deny can be enforced.

### Finding 9: AppWorld — multi-app autonomous, with state-based unit tests
**Evidence**: "AppWorld Engine is a high-quality execution environment (60K lines of code) of 9 day-to-day apps operable via 457 APIs and populated with realistic digital activities simulating the lives of ~100 fictitious users... 750 natural, diverse, and challenging autonomous agent tasks requiring rich and interactive code generation... robust programmatic evaluation with state-based unit tests, allowing for different ways of completing a task while also checking for unexpected changes."
**Source**: [Trivedi et al., "AppWorld"](https://arxiv.org/abs/2407.18901) - Accessed 2026-05-21
**Confidence**: High
**Verification**: [ACL 2024 paper](https://aclanthology.org/2024.acl-long.850/), [Stony Brook page](https://ar5iv.labs.arxiv.org/html/2407.18901)
**Analysis**: AppWorld's "state-based unit tests, allowing for different ways of completing a task while also checking for unexpected changes" is interesting — this is the closest off-the-shelf analogue of the user's "did the agent do anything beyond what was asked." GPT-4o solves ~49% normal / ~30% challenge, suggesting useful headroom. But the evaluation is still end-of-episode. The use of code generation as the primary interaction modality may not match the user's intuition about "autonomous workflows" since code-as-action collapses many decisions into one call. Fit: **Medium-High** if the user is willing to accept code-as-action; **Medium** otherwise.

### Finding 10: AssistantBench — directly measures hallucination as a documented mode
**Evidence**: "AssistantBench is a challenging new benchmark consisting of 214 realistic tasks that can be automatically evaluated... no model reaches an accuracy of more than 25 points. While closed-book LMs perform well, they exhibit low precision since they tend to hallucinate facts. State-of-the-art web agents reach a score of near zero."
**Source**: [Yoran et al., "AssistantBench"](https://arxiv.org/abs/2407.15711) - Accessed 2026-05-21
**Confidence**: High
**Verification**: [Project page](https://assistantbench.github.io/), [GitHub](https://github.com/oriyor/assistantbench)
**Analysis**: AssistantBench is one of the few benchmarks that *explicitly* names hallucination as a failure mode it surfaces — but again at task-level, not per-turn. The "score of near zero" for state-of-the-art means floor effects would mask architecture differences. Fit: **Low** for direct use; useful only as evidence that hallucination-in-agents is recognized in the field.

### Finding 11: MLAgentBench — ML research workflows, very long horizon
**Evidence**: "MLAgentBench is the first benchmark for evaluating agents capable of machine learning experimentation... 13 tasks ranging from improving model performance on CIFAR-10 to recent research problems like BabyLM... Claude v3 Opus achieving the best success rate at 37.5%... success rates vary considerably, spanning from 100% on well-established older datasets to as low as 0% on recent Kaggle challenges."
**Source**: [Huang et al., "MLAgentBench"](https://arxiv.org/abs/2310.03302) - Accessed 2026-05-21
**Confidence**: High
**Verification**: [GitHub](https://github.com/snap-stanford/MLAgentBench)
**Analysis**: The 100%-on-older / 0%-on-newer split is a serious warning about data contamination for any LLM benchmark that uses real public artifacts. The user's experiment should heed this. MLAgentBench itself doesn't measure hallucination per-turn or scaffolding-compliance. Fit: **Low** for direct use; **High** as a cautionary tale about contamination.

### Finding 12: BrowseComp — long-horizon browsing with answer verifiability
**Evidence**: "BrowseComp is an open-source benchmark released by OpenAI in April 2025... 1,266 challenging problems... persistently navigate the internet to find hard-to-find, entangled information... Browsing tools alone achieve only 1.9% accuracy while specialized agentic systems reach 51-78%."
**Source**: [Wei et al., "BrowseComp: A Simple Yet Challenging Benchmark for Browsing Agents"](https://arxiv.org/abs/2504.12516) - Accessed 2026-05-21
**Confidence**: High
**Verification**: [OpenAI blog announcement](https://openai.com/index/browsecomp/), [InfoQ coverage](https://www.infoq.com/news/2025/05/openai-browsecomp-ai-benchmark/)
**Analysis**: BrowseComp's short-answer / single-correct-answer design makes grading easy but does not instrument the agent's internal beliefs during the run. The "persistence" capability it measures is interesting but adjacent to what the user wants. Fit: **Low**.

### Finding 13: Anthropic's agentic misalignment evals — propensity, not per-turn instrumentation
**Evidence**: "Anthropic introduced a misalignment propensity benchmark called AgentMisalignment, consisting of a suite of realistic scenarios in which LLM agents have the opportunity to display misaligned behaviour. The evaluations are organised into subcategories of misaligned behaviours, including goal-guarding, resisting shutdown, sandbagging, and power-seeking."
**Source**: [Anthropic, "Agentic Misalignment: How LLMs could be insider threats"](https://www.anthropic.com/research/agentic-misalignment) - Accessed 2026-05-21
**Confidence**: High
**Verification**: [AgentMisalignment paper](https://arxiv.org/pdf/2506.04018), [Alignment Science Blog](https://alignment.anthropic.com/)
**Analysis**: This is closely related to the user's "disallowed actions" axis but measures *propensity* to take certain classes of unsafe actions in scenarios designed to surface them, not per-turn state divergence. The methodology (scenario-design + observe behavior) is relevant prior art for the user's experiment design. Fit: **Low** for direct use; **Medium-High** as design inspiration.

### Finding 14: HaluEval / TruthfulQA — short-form, single-turn; explicit non-fit for long-horizon
**Evidence**: "HaluEval is a large collection of generated and human-annotated hallucinated samples... 10,000 to 35,000 human-annotated examples, predominantly organized as question–answer pairs... TruthfulQA evaluates the truthfulness of LLM responses across 817 questions designed to elicit common misconceptions."
**Source**: [Li et al., "HaluEval"](https://arxiv.org/abs/2305.11747), [TruthfulQA on HaluEval/TruthfulQA topic page](https://www.emergentmind.com/topics/halueval-and-truthfulqa) - Accessed 2026-05-21
**Confidence**: High
**Verification**: [HaluEval GitHub](https://github.com/RUCAIBox/HaluEval)
**Analysis**: Documented for completeness. These are single-turn / Q&A benchmarks; they cannot surface the kind of accumulated drift the user wants to measure. **Fit: No.** Their inclusion in this report is to head off the question "why aren't you using HaluEval?"

### Finding 15: Generative Agents (Park, Smallville) — emergent behavior, but no ground-truth oracle
**Evidence**: "Twenty-five agents in a sandbox environment... generative agents in Smallville exchange information, form new relationships, and coordinate joint activities, with these social behaviors being emergent rather than pre-programmed."
**Source**: [Park et al., "Generative Agents: Interactive Simulacra of Human Behavior"](https://arxiv.org/abs/2304.03442) - Accessed 2026-05-21
**Confidence**: High
**Verification**: [GitHub repo](https://github.com/joonspk-research/generative_agents), [Stanford HAI coverage](https://hai.stanford.edu/news/computational-agents-exhibit-believable-humanlike-behavior)
**Analysis**: Smallville is a *system paper*, not a benchmark. It demonstrates that multi-agent LLM simulations are feasible, but it evaluates via "believability" judgments from human raters — there is no ground-truth oracle and no instrumentation of hallucination. The retrieval-reflection-planning memory architecture in Smallville is actually relevant prior art for the user's blackboard idea. Fit: **Low** as benchmark; **Medium-High** as architecture prior art.

### Finding 16: METR's task-horizon framing supports the user's hypothesis that horizon matters
**Evidence**: "The increase in AI models' time horizons seems to be primarily driven by greater reliability and ability to adapt to mistakes, combined with better logical reasoning and tool use capabilities."
**Source**: [METR, op. cit.](https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/)
**Confidence**: High
**Analysis**: METR's empirical finding directly supports the user's premise: capability differences between architectures should manifest most strongly on the *long* end of the task-horizon distribution. This argues for designing the experiment with deliberately long episodes (not classic Yob-1973's ~20-turn typical game).

### Finding 17: Measuring Faithfulness in CoT (Lanham et al. / Anthropic) — directly relevant for "reasoning unfaithfulness" leak class
**Evidence**: "Models show large variation across tasks in how strongly they condition on the CoT when predicting their answer, and as models become larger and more capable, they produce less faithful reasoning on most tasks."
**Source**: [Lanham et al., "Measuring Faithfulness in Chain-of-Thought Reasoning"](https://arxiv.org/abs/2307.13702) - Accessed 2026-05-21
**Confidence**: High
**Verification**: [Anthropic research page](https://www.anthropic.com/research/measuring-faithfulness-in-chain-of-thought-reasoning), [HuggingFace paper page](https://huggingface.co/papers/2307.13702)
**Analysis**: This is the most directly applicable prior art for the user's "reasoning unfaithfulness" scaffolding-leak. Lanham et al.'s methods (perturbing the CoT and observing whether the answer changes) translate roughly to "did the agent's stated plan predict its action?" The finding that *larger models produce less faithful reasoning* is a load-bearing caveat — it predicts the user's bare-LLM architectures will look better than they actually reason, because stated reasoning may not drive action. Fit for inclusion: **High** — borrow methodology directly.

### Finding 18: TextWorld — game-generator with full ground-truth state, perfect substrate for custom benchmark
**Evidence**: "TextWorld has two main components: a game generator and a game engine. The game generator converts high-level game specifications, such as number of rooms, number of objects, game length, and winning conditions, into an executable game source code in the Inform 7 language... handles interactive play-through of text games, as well as backend functions like state tracking and reward assignment... gives precise control over the difficulty, scope, and language of constructed games."
**Source**: [Côté et al., "TextWorld: A Learning Environment for Text-based Games"](https://arxiv.org/abs/1806.11532) - Accessed 2026-05-21
**Confidence**: High
**Verification**: [Microsoft Research blog](https://www.microsoft.com/en-us/research/blog/textworld-a-learning-environment-for-training-reinforcement-learning-agents-inspired-by-text-based-games/), [TALES suite](https://microsoft.github.io/tale-suite/)
**Analysis**: TextWorld is arguably the *ideal substrate* for the user's experiment. Reasons: (a) full ground-truth state available — meets the "oracle" requirement natively; (b) game-generator means difficulty/horizon/state-space are knobs the experimenter controls; (c) Inform 7 backend means rules can be made arbitrarily rich; (d) well-cited prior art (ALFWorld is built on TextWorld). The challenge: building a Wumpus-equivalent on TextWorld is more work than reusing MPL Wumpus, but the payoff is full control over the L1-L4 escalation ladder without rewriting the game. Fit: **High** as alternative substrate.

### Finding 19: Jericho — partial-observability + huge action space, but harder than the user needs
**Evidence**: "Interactive Fiction games are fully text-based simulation environments... partial observability, which requires agents to infer and maintain world state from local textual observations, and extremely large combinatorial action spaces derived from natural language commands... 52 games."
**Source**: [Hausknecht et al., "Interactive Fiction Games: A Colossal Adventure"](https://arxiv.org/abs/1909.05398) - Accessed 2026-05-21
**Confidence**: High
**Verification**: [Microsoft blog](https://www.microsoft.com/en-us/research/blog/by-making-text-based-games-more-accessible-to-rl-agents-jericho-framework-opens-up-exciting-natural-language-challenges/), [GitHub](https://github.com/microsoft/jericho)
**Analysis**: Jericho's hand-authored IF games (Zork, Anchorhead, etc.) have *brutal* combinatorial action spaces and progress is hard to score — they were designed for human players, not for fine-grained benchmark instrumentation. Building an oracle that knows what's "true" at each turn in Zork is much harder than in Wumpus, because Zork's world state is not closed-form. Fit: **Low** — too noisy for the user's measurement question.

### Finding 20: Crafter — long-horizon survival with 22 achievement-based metrics
**Evidence**: "Crafter is an open world survival game with visual inputs that evaluates a wide range of general abilities within a single environment... 22 achievements that an agent can unlock during an episode of play. These tasks require exploration, survival, and long-horizon planning."
**Source**: [Hafner, "Benchmarking the Spectrum of Agent Capabilities"](https://arxiv.org/abs/2109.06780) - Accessed 2026-05-21
**Confidence**: High
**Verification**: [GitHub](https://github.com/danijar/crafter), [CrafterDojo follow-up](https://arxiv.org/html/2508.13530v1)
**Analysis**: Crafter is visual (2D pixel art), which means the modality is wrong for the user's "text-only agent" experimental simplicity. Achievements provide more fine-grained scoring than win/loss. The state-space is much larger than Wumpus. Fit: **Low** for the user's modality preference; **Medium** if the user is willing to add a vision/representation layer.

### Finding 21: Voyager / MineDojo — open-ended, but huge engineering overhead
**Evidence**: "Voyager is the first LLM-powered embodied lifelong learning agent in Minecraft that continuously explores the world, acquires diverse skills, and makes novel discoveries without human intervention... obtains 3.3x more unique items, travels 2.3x longer distances, and unlocks key tech tree milestones up to 15.3x faster than prior state-of-the-art."
**Source**: [Wang et al., "Voyager"](https://arxiv.org/abs/2305.16291), [Fan et al., "MineDojo"](https://arxiv.org/abs/2206.08853) - Accessed 2026-05-21
**Confidence**: High
**Verification**: [Voyager project page](https://voyager.minedojo.org/), [MineDojo on Hugging Face](https://huggingface.co/papers/2305.16291)
**Analysis**: Voyager demonstrates that LLMs can drive truly long-horizon agents in rich environments, but the Minecraft substrate is overkill for the user's question and would force them to share engineering time with vision/control rather than measurement. Fit: **Low** — wrong-tool-for-the-job.

### Finding 22: NetHack Learning Environment — procedural, complex, but mostly an RL benchmark
**Evidence**: "The NetHack Learning Environment (NLE) is a procedurally generated environment that strikes a balance between complexity and speed, presented as a fully-featured Gym environment around the popular open-source terminal-based single-player turn-based 'dungeon-crawler' game, NetHack... hundreds of enemy and object types, complex and stochastic environment dynamics."
**Source**: [Küttler et al., "The NetHack Learning Environment"](https://arxiv.org/pdf/2006.13760), [BALROG: Benchmarking Agentic LLM and VLM Reasoning On Games](https://arxiv.org/html/2411.13543v1) - Accessed 2026-05-21
**Confidence**: High
**Analysis**: NLE has state-tracking demands far beyond what the user needs to surface architecture differences. It was designed for RL agents; LLM-agent evaluation on it is recent (BALROG benchmark, 2024). Fit: **Low** — too much going on for clean instrumentation.

### Finding 23: Cicero / Diplomacy — relevant for adversarial multi-agent, but bespoke
**Evidence**: "Cicero is the first AI agent by Meta to achieve human-level performance in the complex natural language strategy game Diplomacy... played 40 games against 82 anonymous human competitors and achieved more than 2x the average score of its opponents. It ranked in the top 10% of participants."
**Source**: [Meta AI, "CICERO"](https://ai.meta.com/research/cicero/), [Noam Brown's Science paper](https://noambrown.github.io/papers/22-Science-Diplomacy-TR.pdf) - Accessed 2026-05-21
**Confidence**: High
**Analysis**: Cicero is a *system*, not a benchmark. Diplomacy as an LLM benchmark exists but is intensely multi-agent and language-heavy; instrumenting hallucination per turn is harder than in a single-agent POMDP. Fit: **Low**.

### Finding 24: AvalonBench / Werewolf Arena / WOLF — social deduction; relevant for "deception" not "drift"
**Evidence**: "AvalonBench — Two popular LLMs (ChatGPT-3.5 and Llama2) were evaluated, with the best model achieving a win rate of 22.2% when playing a good role, and 66.7% when playing an evil role... WOLF — Werewolves produce deceptive statements in 31% of turns, while peer detection achieves 71-73% precision."
**Source**: [Light et al., "AvalonBench"](https://arxiv.org/pdf/2310.05036), [WOLF benchmark](https://arxiv.org/abs/2512.09187), [Werewolf Arena](https://arxiv.org/html/2407.13943v1) - Accessed 2026-05-21
**Confidence**: High
**Analysis**: These measure *deliberate deception* (agent lying strategically) rather than *accidental hallucination* (agent believing-and-asserting-falsely). Worth knowing about but orthogonal to the user's question. Fit: **Low**.

### Finding 25a: LLM-Cave — direct prior art for a Wumpus-derived LLM benchmark
**Evidence**: "LLM-Cave... a benchmark framework and lightweight environment specifically designed for evaluating and enhancing the reasoning and decision-making abilities of Large Language Models... classic grid-world environment that requires an agent to infer the location of hidden dangers from partial information... pits and wumpus monsters that may kill the agent, with breeze and stench near them, and the LLM should reason the position of the pit and wumpus according to the observed information to safely explore the cave and find the gold... Chain of Speculation mechanism for long-term reasoning memory and the Planner-Critic mechanism for decision verification."
**Source**: [LLM-Cave](https://arxiv.org/pdf/2511.22598) - Accessed 2026-05-21
**Confidence**: Medium-High (single source, but the abstract is unambiguous)
**Verification**: [Independent practitioner repo using Wumpus with LLM](https://github.com/glhahn/wumpus-llm-agent)
**Analysis**: **This is highly relevant prior art**. LLM-Cave is the AIMA-textbook variant of Wumpus (pits with breeze, Wumpus with stench, gold), evaluated against GPT-4o-mini / o1-mini / DeepSeek-R1, using a Chain of Speculation memory and Planner-Critic verification — *which is exactly the scaffolding-comparison space the user wants to explore*. Implication: the user's experiment is not in unexplored territory at the task level. **However**, LLM-Cave appears to measure success rate and compare reasoning *strategies* (CoS, Planner-Critic), not architectures with per-turn ground-truth divergence vs scaffolding-leak. The user's contribution would therefore be the *measurement layer*, not the task. Recommendation: read the full LLM-Cave paper, contact the authors if possible, and frame the user's work as complementary (different measurement design on a known-good task).

### Finding 25b: Existing community Wumpus-LLM agents (informal, but it confirms task gravity)
**Evidence**: A publicly-developed LLM-powered tool-use demo using Hunt the Wumpus exists as `glhahn/wumpus-llm-agent` on GitHub.
**Source**: [glhahn/wumpus-llm-agent](https://github.com/glhahn/wumpus-llm-agent) - Accessed 2026-05-21
**Confidence**: Medium (single source, informal)
**Analysis**: Confirms Wumpus is a "natural" first task for LLM-tool-use demos. Reduces novelty argument for the user's choice but increases reproducibility.

### Finding 26: Reasoning unfaithfulness is well-established — the user's "stated plan vs action" metric has direct prior art
**Evidence**: "Agents produce human-readable reasoning traces that ostensibly explain their logic, but mounting evidence suggests that these traces often function as post-hoc justifications rather than the generative drivers of the model's terminal conclusions... Project Ariadne... proposes the Ariadne Score as a new benchmark for aligning stated logic with model action... A CoT exhibits post-hoc reasoning when its intermediate steps are retroactively constructed to rationalize a predetermined answer."
**Source**: [Project Ariadne (Structural Causal Framework for Auditing Faithfulness)](https://arxiv.org/pdf/2601.02314), [Chain-of-Thought Reasoning In The Wild Is Not Always Faithful](https://arxiv.org/pdf/2503.08679), [FaithCoT-Bench](https://arxiv.org/html/2510.04040v1) - Accessed 2026-05-21
**Confidence**: High
**Verification**: Multiple 2024-2026 papers consistent on the phenomenon
**Analysis**: The user's "reasoning unfaithfulness" scaffolding-leak category is supported by an active research literature with formalized methods (intervention-based perturbation, the Ariadne Score). The user should consider adopting one of these scoring conventions for that specific leak category — it makes their results comparable to a broader corpus.

### Finding 27: Safety-Under-Scaffolding — direct evidence the "scaffold smuggles in the answer" worry is real
**Evidence**: "Safety Under Scaffolding... one of the largest controlled studies of scaffold effects on safety with 62,808 evaluations across six frontier models and four deployment configurations. The research found that map-reduce scaffolding inadvertently converts multiple-choice items into open-ended ones, and what appeared to be scaffold-induced reasoning disruption was largely inadvertent format conversion."
**Source**: [Safety Under Scaffolding](https://arxiv.org/html/2603.10044v1) - Accessed 2026-05-21
**Confidence**: High (62,808 evaluations is a strong sample)
**Verification**: [Efficient Benchmarking of AI Agents](https://arxiv.org/pdf/2603.23749), which independently emphasizes that "agent benchmarks depend not only on the underlying model but also on the scaffold, which governs tool use, memory, retry logic, and execution flow"
**Analysis**: **This is the strongest empirical evidence in this report that the user's experimental design must be careful.** When scaffold-A and scaffold-B are compared, observed differences are *partly* due to format/scaffold-induced task-shape changes, not just "the scaffold helped the model think." The Safety-Under-Scaffolding paper shows this effect at large scale. The user's experiment is vulnerable to the same critique unless explicitly designed to control for it. Recommendation: include an ablation that holds the format constant across scaffolds (same prompt template, same input modality, same expected output schema), and report the residual when format is controlled.

### Finding 28: BeliefShift — direct prior art for "belief drift over multi-session interaction"
**Evidence**: "BeliefShift is a longitudinal benchmark designed to evaluate belief dynamics in multi-session LLM interactions, covering Temporal Belief Consistency, Contradiction Detection, and Evidence-Driven Revision, with 2,400 human-annotated multi-session interaction trajectories."
**Source**: [BeliefShift](https://arxiv.org/pdf/2603.23848) - Accessed 2026-05-21
**Confidence**: Medium-High
**Analysis**: BeliefShift is a benchmark explicitly for tracking belief consistency over long horizons. It is dialogue-shaped (multi-session conversation), not game-shaped. Worth knowing the methodology — it formalizes three sub-tasks: (a) consistency over time, (b) detecting contradictions, (c) updating on evidence. The user's "stale belief acted on" and "resurrected entity" divergence kinds correspond closely to BeliefShift's failure modes. Fit: **Medium** as inspiration; **Low** as drop-in benchmark.

### Finding 29: Benchmarking World-Model Learning — proxy for "agent's internal model vs reality"
**Evidence**: "WorldTest proposes a protocol that separates reward-free interaction from a scored test phase in a different environment, remaining agnostic to model representation."
**Source**: [Benchmarking World-Model Learning](https://arxiv.org/html/2510.19788v1) - Accessed 2026-05-21
**Confidence**: Medium
**Analysis**: Worth knowing; the design (interaction phase + test phase) is well-aligned with the user's notion of "what does the agent know about the world." However, this is an RL-research-oriented benchmark, not an LLM-agent benchmark in the user's sense.

### Finding 30: AgentBoard — the closest off-the-shelf benchmark for *progressive* / fine-grained scoring
**Evidence**: "AgentBoard... fine-grained progress rate metric that captures incremental advancements as well as a comprehensive evaluation toolkit... 9 unique tasks and 1013 exemplary environments, covering embodied AI, game agents, web agents, and tool agents, with manually annotated subgoals for each data sample to track agents' detailed advancements through a unified progress rate metric... Current evaluation frameworks mostly focus on the final success rate, revealing few insights during the process and failing to provide a deep understanding of the model abilities."
**Source**: [Ma et al., "AgentBoard"](https://arxiv.org/abs/2401.13178) (NeurIPS 2024) - Accessed 2026-05-21
**Confidence**: High
**Verification**: [NeurIPS poster](https://neurips.cc/virtual/2024/poster/97853), [Project page](https://hkust-nlp.github.io/agentboard/), [HuggingFace paper page](https://huggingface.co/papers/2401.13178)
**Analysis**: AgentBoard's progress-rate-via-subgoals is *the closest off-the-shelf analogue to per-turn ground-truth instrumentation*. Its motivation paragraph directly states the gap the user wants to fill ("Current evaluation frameworks mostly focus on the final success rate, revealing few insights during the process"). The 9-task / 1013-environment suite gives a useful baseline pool. Fit: **High** for methodology inspiration; **Medium-High** as a benchmark to also run if budget allows (would give the user's results an external comparison point).

### Finding 31: Lost-in-the-Middle — establishes the *floor* of context-only state-tracking
**Evidence**: "When answering questions over exceedingly long context information, Large Language Models (LLMs) exhibit a 'lost-in-the-middle' phenomenon in which accuracy drops significantly for information near the center of the context window (Liu et al., 2023)... Larger models (e.g., Llama-3.2 1B) exhibit reduced or eliminated U-shaped curves and maintain high overall recall."
**Source**: [Liu et al., "Lost in the Middle" original 2023 paper](https://arxiv.org/abs/2307.03172), [Lost in the Middle: An Emergent Property](https://arxiv.org/html/2510.10276v1) - Accessed 2026-05-21
**Confidence**: High
**Analysis**: Lost-in-the-middle is the foundational evidence for the user's central premise (context-only state-tracking gets worse with horizon). The phenomenon is being mitigated in newer models, but the *direction* of the failure mode is robust. This argues for choosing a task long enough that mid-context information becomes critical, which classic Yob's 20-turn games may not satisfy.

### Finding 32: Formal-LLM, AGENT-C, ToolGate, VeriGuard, FlowAgent, MetaAgent — formal-method-caged LLMs is an ACTIVE area, not a gap
**Evidence**: Multiple 2024-2026 papers explicitly combine LLMs with formal/constrained execution:
- "Formal-LLM... allows agent developers to express constraints for the planning process as an automaton, with a stack-based LLM plan generation process conducted under the automaton's supervision"
- "AGENT-C... provides runtime guarantees for LLM agents to adhere to formal temporal safety properties"
- "ToolGate: Contract-Grounded and Verified Tool Execution for LLMs... logical safety guarantees and verifiable state evolution"
- "VeriGuard... synthesizes behavioral policies subject to formal verification and provides online action monitoring as a runtime monitor"
- "FlowAgent... Procedure Description Language (PDL), which combines the adaptability of natural language with the precision of code to formulate workflows"
- "MetaAgent: Automatically Constructing Multi-Agent Systems Based on Finite State Machines"
**Source**: [Formal-LLM](https://arxiv.org/pdf/2402.00798), [AGENT-C / Enforcing Temporal Constraints](https://arxiv.org/pdf/2512.23738), [ToolGate](https://arxiv.org/pdf/2601.04688), [VeriGuard](https://arxiv.org/pdf/2510.05156), [FlowAgent](https://arxiv.org/pdf/2502.14345), [MetaAgent](https://arxiv.org/html/2507.22606v1) - Accessed 2026-05-21
**Confidence**: High (5+ independent papers)
**Analysis**: **The user should not characterize their MPL-caged-LLM as "no prior art."** Formal-method-shaped constraint on LLM behavior is an active 2024-2026 research area covering FSMs (Formal-LLM, MetaAgent), behavior trees (LLM-BT, BTGenBot), Linear Temporal Logic (AGENT-C, VerifyLLM), and workflow languages (FlowAgent's PDL). What is distinctive about Harel statecharts specifically (hierarchy, orthogonal regions, broadcast events) and about MPL (manifest-based blackboard, host imports as decision leaves) is closer to a *gap*, but should be positioned as "we chose a richer formalism than the FSMs currently dominant" rather than "nobody has done this." This is an important framing correction. Recommendation: cite Formal-LLM and one or two of the others in the user's writeup as nearest-neighbor work.

### Finding 33: BPMN-LLM and FlowAgent — direct workflow-compliance prior art
**Evidence**: "FlowAgent is a novel agent framework designed to maintain both compliance and flexibility, proposing the Procedure Description Language (PDL), which combines the adaptability of natural language with the precision of code to formulate workflows. Experiments demonstrate that FlowAgent not only adheres to workflows but also effectively manages out-of-workflow queries."
**Source**: [FlowAgent](https://arxiv.org/pdf/2502.14345), [Agentic Business Process Management](https://arxiv.org/pdf/2504.03693), [Towards Modeling Human-Agentic Collaborative Workflows: A BPMN Extension](https://arxiv.org/html/2412.05958v1) - Accessed 2026-05-21
**Confidence**: High
**Analysis**: FlowAgent is interesting because it explicitly measures *compliance with workflow* — the same axis as the user's scaffolding-leak metric. Its PDL is conceptually close to MPL's manifest. Worth citing as prior art for "an LLM operating under a formal workflow specification."

### Finding 34: Behavior-tree-LLM hybrids are well-established in robotics
**Evidence**: "LLM-BT combines large language models (LLMs) and behavior trees (BTs) to enable robotic agents to perform adaptive tasks, using LLMs to generate high-level task plans, which are then executed by a BT-based control system... BTGenBot: Behavior Tree Generation for Robotic Tasks with Lightweight LLMs."
**Source**: [LLM-BT](https://www.aimodels.fyi/papers/arxiv/llm-bt-performing-robotic-adaptive-tasks-based), [BTGenBot](https://arxiv.org/html/2403.12761v1), [LLM-HBT](https://arxiv.org/pdf/2510.09963) - Accessed 2026-05-21
**Confidence**: High
**Analysis**: In robotics, BTs are already the de-facto cage for LLM-driven planners. The user's harebrain thesis is *closer to robotics' decade-old answer* than to current LLM-agent-framework practice. Worth noting because (a) it strengthens the user's thesis (the robotics community independently arrived at "structure the LLM in a formal runtime") and (b) it means the user should look at BT-LLM benchmarks for comparable measurement designs.

### Finding 35: Factorial design / orchestration-pattern benchmarking is now standard practice
**Evidence**: "Recent research implements representative agent systems based on unified engineering standards and toolsets, creating controlled experimental environments that isolate and study the impact of agent architecture and workflow design on performance... Framework-level design choices alone can increase latency by over 100×, reduce planning accuracy by up to 30%, and lower coordination success from above 90% to below 30%."
**Source**: [Benchmarking and Studying the LLM-based Agent System in End-to-End Software Development](https://arxiv.org/pdf/2511.04064), [Understanding Multi-Agent LLM Frameworks: A Unified Benchmark and Experimental Analysis](https://arxiv.org/pdf/2602.03128), [Benchmarking Multi-Agent LLM Architectures for Financial Document Processing](https://arxiv.org/pdf/2603.22651) - Accessed 2026-05-21
**Confidence**: Medium-High (multiple recent papers consistent)
**Analysis**: Multi-agent / orchestration-pattern comparison studies are now common. The user's planned (model × scaffold × seed) factorial design is consistent with current best practice. The 100×-latency / -30%-accuracy / -60%-coordination effect sizes reported in this literature are large enough that the user's experiment should expect *meaningful* differences between architectures — i.e., it should not turn out that all architectures perform identically.

### Finding 36: BALROG — direct comparator for "long-horizon games as an agent benchmark"
**Evidence**: "BALROG is a novel benchmark designed to assess the agentic capabilities of LLMs and VLMs through a diverse set of challenging games... aggregates a diverse set of complex reinforcement learning game environments into a unified testbed for research on long-context LLMs... a range of existing reinforcement learning environments with varying levels of difficulty, including tasks that are solvable by nonexpert humans in seconds to extremely challenging ones that may take years to master (e.g., the NetHack Learning Environment)."
**Source**: [Paglieri et al., "BALROG"](https://arxiv.org/abs/2411.13543) (ICLR 2025) - Accessed 2026-05-21
**Confidence**: High
**Verification**: [NVIDIA blog](https://developer.nvidia.com/blog/benchmarking-agentic-llm-and-vlm-reasoning-for-gaming-with-nvidia-nim/), [ICLR poster](https://iclr.cc/virtual/2025/poster/28856), [GitHub](https://github.com/balrog-ai/BALROG)
**Analysis**: BALROG is the most direct off-the-shelf framework for "evaluate LLM agents on games." Tasks include NetHack, BabyAI, MiniHack, Crafter, BabaIsAI, TextWorld. It is *model-comparison* in design (varying the LLM, holding the agent harness constant), not architecture-comparison. The user could (a) borrow BALROG's game adapters for their own measurement layer, or (b) run their architectures on a BALROG game in addition to Wumpus for external comparison. Fit: **Medium-High** as a complementary suite.

### Finding 37: Anthropic's 2025 CoT-faithfulness follow-up — more concrete methodology
**Evidence**: "More recent research in 2025 from Anthropic's Alignment Science Team tested four language models—two reasoning models (Claude 3.7 Sonnet and DeepSeek R1) and two non-reasoning models (Claude 3.5 Sonnet and DeepSeek V3). CoT faithfulness was defined as the rate at which a model, after changing its answer due to a hint, explicitly stated in the CoT that it relied on the hint."
**Source**: [Anthropic Alignment Science Blog](https://alignment.anthropic.com/), [Anthropic CoT Faithfulness research summary](https://www.anthropic.com/research/measuring-faithfulness-in-chain-of-thought-reasoning), [LessWrong mirror](https://www.lesswrong.com/posts/BKvJNzALpxS3LafEs/measuring-and-improving-the-faithfulness-of-model-generated) - Accessed 2026-05-21
**Confidence**: Medium-High
**Analysis**: The "rate at which a model verbalized that it relied on the hint" is a clean *operational* definition the user could borrow for the reasoning-unfaithfulness scaffolding-leak. Concretely: inject a controlled hint (e.g., "remember the Wumpus moved when you missed at turn 4"), see if the agent's later reasoning verbalizes using that information when it acts. Fit: **High** as a methodological building block.

### Finding 25: LangGraph introspection — native hooks exist for the user's plan
**Evidence**: "LangSmith provides visualization tools that trace execution paths, capture state transitions, and provide detailed runtime metrics... `stream_mode='updates'` gives you per-node outputs... StateGraph... State changes are explicit and traceable."
**Source**: [LangGraph docs](https://docs.langchain.com/oss/python/langgraph/overview), [LangGraph GitHub](https://github.com/langchain-ai/langgraph), [Langfuse integration](https://langfuse.com/guides/cookbook/integration_langgraph) - Accessed 2026-05-21
**Confidence**: Medium-High
**Verification**: [StateGraph reference (Python)](https://reference.langchain.com/python/langgraph/graph/state/StateGraph), [LangGraph.js StateGraph](https://langchain-ai.github.io/langgraphjs/reference/classes/langgraph.StateGraph.html)
**Analysis**: LangGraph natively exposes per-node state, edge transitions, and update streams. This **confirms the user's plan is technically feasible**: you can record every (node, before-state, after-state, output) tuple and compare against the declared graph schema. The instrumentation that the user wants for the "scaffolding leak" metric is therefore a reasonable engineering task, not a research-grade open problem. Caveats: tool-call gating ("which node invoked the tool") requires the user to wrap tools with context variables — LangGraph does not enforce this out-of-the-box. Confidence is **Medium-High** rather than High because the specific feasibility of *gating* the tool call (refusing it from the wrong node) is implementation-dependent, and LangGraph does not natively refuse out-of-phase calls.
**Evidence**: "ALFWorld contains household tasks that require agents to explore surroundings and perform commonsense tasks like 'put two soapbars in garbagecan'. ScienceWorld is a challenging interactive text environment testing scientific commonsense... Embodied planning tasks are formalized within the framework of a Partially Observable Markov Decision Process (POMDP) due to the agent's inability to directly observe the environment's complete state... State-of-the-art methods achieve completion rates of 97.78% on ALFWorld and 79.92% on ScienceWorld."
**Source**: [Shridhar et al., "ALFWorld"](https://arxiv.org/abs/2010.03768) - Accessed 2026-05-21
**Confidence**: High
**Verification**: [OpenReview](https://openreview.net/forum?id=0IOX0YcCdTn), [Semantic Scholar](https://www.semanticscholar.org/paper/ALFWorld:-Aligning-Text-and-Embodied-Environments-Shridhar-Yuan/398a0625e8707a0b41ac58eaec51e8feb87dd7cb)
**Analysis**: ALFWorld is a strong candidate as an *alternative task domain* to Hunt the Wumpus. Reasons: (a) it is POMDP-formalized so partial observability is explicit, (b) the underlying simulator (TextWorld) has full ground-truth state available for instrumentation, (c) it is well-known in the literature so results would have context, (d) the SOTA is high (~98%) which means the task is solvable enough to measure architecture differences. But ALFWorld episodes are short (typically 10-30 actions), so it has the same "too small" risk the user worries about for Wumpus. Fit: **Medium** as Wumpus alternative; **Medium-High** if extended with adversarial/long-horizon scenarios.

## What No Existing Benchmark Gives the User

The gap is specific and identifiable. No off-the-shelf benchmark provides **all four** of:

1. **Per-turn ground-truth divergence**, not episode-end. Required so that "the agent claimed X at turn 7 when X was false" is a recorded event, not implicit in an end-of-episode score.
2. **Kind-classified divergence taxonomy** (resurrected entity, inventory drift, position confusion, stale belief, phantom warning, phantom geography, plus the user's "disallowed action attempts"). AgentBoard's subgoal progress comes closest but does not categorize *the kind of failure*.
3. **Per-node scaffolding-leak instrumentation** (skipped nodes, wrong-phase tool calls, format violations, role confusion, implicit state mutation, reasoning unfaithfulness). FlowAgent has a workflow-compliance axis; AGENT-C has runtime constraint monitoring; Project Ariadne has reasoning-vs-action causal scoring. **No benchmark combines all six categories.**
4. **Architecture-comparison framing where scaffolding-richness is the independent variable.** Most benchmarks vary the underlying model; benchmarks that vary scaffolding (Safety-Under-Scaffolding, the multi-agent-orchestration papers) are oriented to safety or orchestration-pattern questions, not to the user's specific hypothesis ladder.

The closest existing combination is **tau-bench + AgentBoard + Project Ariadne** as three separate evaluations, each contributing one axis. None of these alone gives the user what they want. The user's experimental design *is* novel as a *measurement contribution*, even if the underlying task (Wumpus / LLM-Cave) is not novel.

## Is Hunt the Wumpus the Right Task?

**Verdict: Yes for Note 1 ("the cage works") with L1-classic; conditionally yes for Note 2 ("the brain earns its keep") only with L2-L3 escalation; almost certainly no as a standalone task if you want to surface architecture differences on long-horizon reasoning depth.**

### Why Wumpus works for the cage-demo (Note 1)
1. **Closed-form ground truth.** Every world fact (Wumpus position, pit positions, bat positions, arrow count, current room, sensed adjacencies) is a small enum. An MPL ground-truth oracle is trivially implementable. This is the *single property* that makes the per-turn divergence metric tractable. WebArena, OSWorld, SWE-bench all lack this property — their "ground truth" is large and partially-implicit.
2. **Partial observability with rich-enough sensing.** Wumpus has exactly the right partial-observability profile to surface "stale belief," "phantom warning," and "phantom geography." Many alternative tasks (SWE-bench, AppWorld) are not POMDPs in this sense.
3. **The bat-teleport is a built-in stress test.** This is genuinely valuable. The user's note correctly identifies bat-teleport as a "context-based state tracking" stress test that does not require any L2+ escalation.
4. **It is reproducible.** Twenty rooms, fixed dodecahedron, seeded hazard placement. The reproducibility issues that plague WebArena (live websites change) and MLAgentBench (data contamination on public Kaggle) do not apply.
5. **It is fast.** A single Yob run is sub-minute. Factorial (model × scaffold × seed) with 100 seeds × 6 architectures × 3 models = 1800 runs is feasible. WebArena runs are 5-15 minutes each.

### Why classic Yob is probably too small for the brain-demo (Note 2)
1. **Ceiling effect with capable models.** LLM-Cave's published results suggest modern LLMs do well on the Wumpus task once given any reasoning support (Chain of Speculation, Planner-Critic). This means the gap between "no cage" and "cage" may compress.
2. **Heuristic baseline (C) ablates much of the brain.** As the user already identified: a 50-line Python heuristic ("avoid smelled rooms, count arrows, triangulate before shooting") plays Wumpus well. C ≈ D would be the expected outcome and the brain claim weakens to "well, the brain didn't hurt."
3. **20-turn games are short relative to "lost-in-the-middle."** The phenomenon shows up clearly at ~1K+ tokens of irrelevant intervening context. Classic Yob's context per game is ~500-2000 tokens for the entire run. This is too short to surface the user's hypothesized scaling differences between architectures.
4. **METR's doubling-time insight argues against any short-horizon task.** If the differentiator between modern architectures is *how long they maintain coherence*, and modern LLMs already have 50-min to 12-hr horizons, a 5-min benchmark cannot discriminate.

### Do the L2-L4 escalations rescue Wumpus?
**Partially yes, but with effort.**

| Level | Escalation | Salvages |
|---|---|---|
| L1 | Classic Yob, fixed dodecahedron | Cage demo (Note 1) only |
| L2 | Wumpus moves when startled; longer arrow paths; multiple Wumpi | Adds working-memory-fact decay stress; partially surfaces brain |
| L3 | Partial observability (senses only on entry, decay) | Stresses prompt construction; favors maintained-state architectures |
| L4 | Larger graph (50-100 rooms); non-dodecahedron topology | Pushes into mid-context regime; surfaces position-confusion |
| L4+ | Multi-room procedural generation; gold + multiple objectives | Approaches Crafter-like complexity |

At L4+ the user is essentially rebuilding TextWorld. **Recommendation**: if Note 2 ("the brain earns its keep") matters, plan to graduate from MPL-Wumpus to a TextWorld-generated task family by the L4 phase. Use TextWorld's game-generator as the substrate but keep the MPL chart as the cage. This costs engineering time up front but avoids being trapped in a known-too-shallow task.

## Alternative Task Candidates (Ranked)

Ranking criteria: (1) ground-truth instrumentability, (2) horizon, (3) architecture-discrimination potential, (4) engineering cost, (5) prior-art context.

### Tier S — Strong recommendations
1. **TextWorld-generated custom benchmark family** ([Côté et al., 2018](https://arxiv.org/abs/1806.11532)). Full ground truth, tunable difficulty, Inform 7 backend allows arbitrary rule complexity, used by ALFWorld and BALROG. Best long-term substrate. *Cost*: 2-4 weeks engineering to set up a Wumpus-equivalent on it.
2. **MPL Wumpus + L4 escalation + tau-bench-style "user with hidden goal" overlay**. Keep the user's existing experiment as Phase 1. For Phase 2, add a tau-bench-style user-policy layer (the agent must also obey a textual policy delivered as system prompt — e.g., "never use more than 3 arrows; always announce intent before shooting"). This brings the policy-compliance axis the user wants without changing tasks.

### Tier A — Good alternatives
3. **ALFWorld extended episodes** ([Shridhar et al., 2020](https://arxiv.org/abs/2010.03768)). Already POMDP-formalized, TextWorld-backed, well-cited. SOTA is high (~98%) on standard episodes — extend horizon by chaining tasks into a single episode and the SOTA drops, surfacing architecture differences. *Cost*: episode-chaining harness + extended ground-truth oracle, ~1 week.
4. **AgentBoard subset on Wumpus-equivalent**. Use AgentBoard's progress-rate methodology (manually annotated subgoals per episode) to give the user's experiment external comparability.

### Tier B — Adequate alternatives
5. **AppWorld single-app subset** ([Trivedi et al., 2024](https://arxiv.org/abs/2407.18901)). State-based unit tests already check for "unexpected changes" — natural fit for "disallowed action" axis. Cost: high — would force a domain shift to digital-task assistant.
6. **BabyAI / MiniHack from BALROG** ([Paglieri et al., 2024](https://arxiv.org/abs/2411.13543)). Procedural-generation gives infinite seeds; instrumentation is RL-grade. Cost: medium — BALROG harness reuse.

### Tier C — Not recommended for the user's question
7. WebArena/OSWorld/SWE-bench (floor effects, no per-turn oracle).
8. Jericho/Voyager/NetHack-only (too much noise, instrumentation is hard).
9. Werewolf/Avalon/Diplomacy (orthogonal axis: deception, not drift).
10. HaluEval/TruthfulQA (wrong horizon).

## Recommended Experiment Design

A two-note structure that follows from the harebrain note's own staging, with explicit deltas based on this research:

### Phase 1 (Note 1: "The cage works") — Stay with MPL Hunt the Wumpus
**Task**: L1-classic Yob, plus L2 Wumpus-moves-when-startled. Twenty rooms, fixed dodecahedron, seeded hazards. Episode horizon: 20-50 turns (longer with L2).

**Architecture ladder** (held constant per cell: model, temperature, base prompt content, tool surface, seeds):
- **A** Scripted optimal (ceiling)
- **B** Random-legal (floor)
- **C** Python heuristic (brain-less cage)
- **D** MPL-caged LLM (cage + brain)
- **E1** LangGraph bare ReAct
- **E2** LangGraph + scratchpad node
- **E3** LangGraph + plan-then-act
- **E4** LangGraph + belief tracker
- **F** LangChain ReAct bare (single-LLM)
- **G** Claude Code / Codex wild baseline (separate report)

**Models** (factorial): pick 3 — one frontier (Claude Opus 4.x or GPT-5-class), one mid (Sonnet/4-mini), one open (Llama-class). The model × scaffold interaction effect is itself a finding.

**Sample size**: 100 seeds × 8 LLM cells (D, E1-4, F) × 3 models = 2400 LLM runs + 300 control runs. Conservative bootstrap CIs on every metric.

**Metric layer**:
- **Outcome**: win rate, turns-to-victory, loss-cause breakdown.
- **Headline 1 — Divergence events per run, with kind classification**: per turn diff (claimed | oracle), categorized into the user's six kinds. Use Anthropic-style perturbation occasionally to test reasoning unfaithfulness (Finding 37 methodology).
- **Headline 2 — Scaffolding leaks per node per turn**: six categories from the user's note (skipped nodes, wrong-phase tool calls, format violations, role confusion, implicit state mutation, reasoning unfaithfulness). Detect via the LangGraph-native hooks (state snapshot before/after, per-node Pydantic output schema, tool-call context-variable gating).
- **Subordinate**: scratchpad accuracy, post-bat recovery turns, arrow-shoot accuracy, tokens-per-turn, OOB attempt rate.
- **Auxiliary METR-style**: 50%-pass time-horizon per architecture (where "time" is turns).

**Critical control derived from Safety-Under-Scaffolding (Finding 27)**: hold input format constant across scaffolds. The baseline (F) prompt must include the same fields the scratchpad node (E2) maintains; otherwise the user is partly measuring prompt content, not graph structure. Run one *ablation* cell where this control is intentionally violated, to quantify the format-conversion effect.

### Phase 2 (Note 2: "The brain earns its keep") — Promote the task
If Phase 1 shows D ≈ C on classic Yob (the user's predicted outcome), Phase 2 promotes the task to one of:
- (a) L3-L4 MPL Wumpus with larger graphs and partial observability decay, OR
- (b) A TextWorld-generated equivalent that hits ~1K-3K-turn horizons.

Same architecture ladder, same metric layer.

### Statistical analysis
- Bootstrap 95% CIs on every metric (sample size supports this).
- Mixed-effects model: divergence-events ~ scaffold + model + (1|seed), with model:scaffold interaction. This separates "the scaffold helps" from "the scaffold-model combination helps."
- Pre-register the predicted ordering (single-LLM > LangGraph-bare > LangGraph-scaffolded > MPL-caged on divergence-events; zero on D by construction). Report Bayesian evidence for and against the predicted ordering.
- Seed-difficulty stratification: cluster seeds by C's success rate (proxy for inherent difficulty) and report metrics per stratum.

### Reproducibility / version drift
- Pin model versions and snapshot dates for all LLM cells.
- Run G (wild coding-agent) twice, six months apart if possible, and report version-drift. This is the user's most honest concession to the field's reproducibility crisis.

## Honest Caveats

1. **This research cannot tell the user whether their *specific* MPL formalism (Harel statecharts with broadcast events, orthogonal regions, manifest-based blackboard) outperforms simpler formalisms (FSMs, behavior trees, LangGraph state machines).** That requires the user's experiment itself. Prior art establishes that *some* formal cage helps; not that *Harel statecharts specifically* help more than alternatives.

2. **Reproducibility of any LLM-in-the-loop benchmark is fragile.** Model APIs change, system prompts shift, tool-use APIs evolve. The user should pin everything pinnable, log raw transcripts verbatim, and accept that 2026 results will not be byte-identical when re-run in 2027.

3. **Scaffolding-leak detection depends on enforceable schemas.** LangGraph does not natively refuse out-of-phase tool calls (Finding 25). The user will need to wrap tools with context-variable gating and decide *strict* vs *permissive* policy upfront. Strict mode under-reports leak frequency (because attempts are blocked); permissive mode over-reports leak consequences (because escapes that hurt and escapes that help are not yet separated).

4. **The "scaffold smuggles the answer" failure mode is empirically real and large** (Safety-Under-Scaffolding, 62,808 evaluations). The user's experiment is vulnerable to it unless format is held constant across scaffolds. Recommendation: include the format-constant ablation as a *separate cell*, not as an afterthought.

5. **Per-turn ground-truth divergence requires the world model to be small and closed-form.** This is fine for Wumpus and TextWorld-generated tasks. It is *not* fine for SWE-bench, WebArena, AppWorld, or anything with implicit state. The user's choice of task is therefore tightly coupled to the measurement question, not free.

6. **Reasoning-unfaithfulness is a hard sub-metric.** Lanham et al. show that larger models verbalize their actual reasoning *less*. The user's reasoning-unfaithfulness leak count may *increase* with model capability, which inverts the naïve "bigger is better" reading. The user should pre-register this prediction and report it carefully.

7. **The hypothesis ordering (single-LLM < orchestrated < graph-orchestrated < statechart-caged) is well-motivated but not certain.** The multi-agent-orchestration literature (Finding 35) reports that orchestration choices can *hurt* by 100×-latency, -30%-accuracy. There is no guarantee a richer cage always wins; the user must be prepared to report a non-monotonic result honestly.

8. **G (wild coding agent) is structurally non-comparable.** It is a useful "agents in the wild" data point but should never be in a head-to-head bar chart with D, E, F. Treat it as a contextual baseline analogous to random/optimal, not a competitor.

## Source Analysis

| Source | Domain | Reputation | Type | Access Date | Cross-verified |
|--------|--------|------------|------|-------------|----------------|
| Liu et al. AgentBench | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y |
| Mialon et al. GAIA | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y |
| Yao et al. tau-bench | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y |
| METR Long Tasks Study | metr.org / arxiv.org | High (1.0) | Industry research org / Academic | 2026-05-21 | Y |
| Jimenez et al. SWE-bench / SWE-bench Pro / SWE-EVO | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y |
| Zhou et al. WebArena / Koh et al. VisualWebArena | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y |
| Xie et al. OSWorld | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y |
| Shridhar et al. ALFWorld | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y |
| Ruan et al. ToolEmu | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y |
| Trivedi et al. AppWorld | arxiv.org / ACL Anthology | High (1.0) | Academic | 2026-05-21 | Y |
| Yoran et al. AssistantBench | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y |
| Huang et al. MLAgentBench | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y |
| Wei et al. BrowseComp | arxiv.org / openai.com | High (1.0) | Industry leader / Academic | 2026-05-21 | Y |
| Anthropic Agentic Misalignment | anthropic.com / alignment.anthropic.com | High (1.0) | Industry leader (top-tier AI lab) | 2026-05-21 | Y |
| Li et al. HaluEval | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y |
| Park et al. Generative Agents | arxiv.org / acm.org | High (1.0) | Academic | 2026-05-21 | Y |
| Lanham et al. CoT Faithfulness | arxiv.org / anthropic.com | High (1.0) | Industry leader / Academic | 2026-05-21 | Y |
| Côté et al. TextWorld | arxiv.org / microsoft.com | High (1.0) | Academic / Industry leader | 2026-05-21 | Y |
| Hausknecht et al. Jericho | arxiv.org / AAAI | High (1.0) | Academic | 2026-05-21 | Y |
| Hafner Crafter | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y |
| Wang et al. Voyager / Fan et al. MineDojo | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y |
| Küttler et al. NLE / Paglieri et al. BALROG | arxiv.org / NeurIPS / ICLR | High (1.0) | Academic | 2026-05-21 | Y |
| Meta AI CICERO / Noam Brown Diplomacy | ai.meta.com / Science | High (1.0) | Industry leader / Academic | 2026-05-21 | Y |
| Light et al. AvalonBench / WOLF / Werewolf Arena | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y |
| LLM-Cave | arxiv.org | Medium-High (0.8) | Academic (2025 paper, fewer citations yet) | 2026-05-21 | Partial (single arxiv source) |
| BeliefShift / WorldTest | arxiv.org | Medium-High (0.8) | Academic (2026 preprints) | 2026-05-21 | N (preprints) |
| Ma et al. AgentBoard | arxiv.org / NeurIPS | High (1.0) | Academic | 2026-05-21 | Y |
| Liu et al. Lost in the Middle | arxiv.org / TACL / cs.stanford.edu | High (1.0) | Academic | 2026-05-21 | Y |
| Formal-LLM / AGENT-C / ToolGate / VeriGuard / FlowAgent / MetaAgent | arxiv.org | High (1.0) on aggregate | Academic | 2026-05-21 | Y (6 independent papers) |
| LLM-BT / BTGenBot / LLM-HBT | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y |
| Safety Under Scaffolding | arxiv.org | High (1.0) | Academic (n=62,808) | 2026-05-21 | Y |
| Project Ariadne / FaithCoT-Bench / CoT Reasoning In The Wild | arxiv.org | High (1.0) | Academic | 2026-05-21 | Y |
| LangGraph official docs | langchain.com / docs.langchain.com / github.com | Medium-High (0.8) | Industry leader docs | 2026-05-21 | Y |
| Anthropic AgentMisalignment + 2025 CoT follow-up | anthropic.com / alignment.anthropic.com | High (1.0) | Industry leader | 2026-05-21 | Y |
| Multi-agent-orchestration benchmark papers (2025-2026) | arxiv.org | Medium-High (0.8) | Academic preprints | 2026-05-21 | Y |

**Reputation distribution**: High (1.0): ~85%. Medium-High (0.8): ~15%. Excluded: 0. Average reputation: ~0.97. **No sources from excluded domains used.**

## Knowledge Gaps

### Gap 1: Specific MPL-vs-FSM-vs-BT-vs-LangGraph head-to-head benchmark
**Issue**: This research found no published benchmark that compares Harel statechart-caged LLMs head-to-head against FSM-caged, behavior-tree-caged, and graph-caged LLMs on the same task with the same model. **Attempted**: searches on "Harel statechart LLM," "Formal-LLM benchmark," "behavior tree LLM comparison." **Recommendation**: this is the user's experiment to do. Frame as the contribution.

### Gap 2: No standard "divergence-kind taxonomy" exists
**Issue**: The user's six divergence kinds (resurrected entity, inventory drift, position confusion, stale belief, phantom warning, phantom geography) are descriptive but ad-hoc. No published benchmark uses this taxonomy. **Attempted**: searches on "hallucination taxonomy long horizon agent," "drift kinds LLM." **Recommendation**: define the taxonomy in the harebrain note explicitly as a contribution. Provide operational decision rules for each kind so other researchers can apply them.

### Gap 3: Open-question about how G (wild coding-agent) measurements actually compare
**Issue**: This research did not find a published example of Claude Code or Codex being instrumented for divergence-events or scaffolding-leaks on a game task. The user's G cell is genuinely uncharted. **Attempted**: searches on "Claude Code benchmark game agent," "Codex hunt the wumpus." **Recommendation**: report G's results separately and qualitatively; do not over-claim.

### Gap 4: LLM-Cave's exact methodology
**Issue**: This research found LLM-Cave as a published Wumpus-derived LLM benchmark (Finding 25a) but did not access the full text — only the abstract and topic page. The paper may already cover ground the user wants to claim as new. **Attempted**: WebFetch returned abstract-level information only. **Recommendation**: the user should read LLM-Cave (arXiv 2511.22598) in full before starting, and adjust framing if needed.

### Gap 5: Reproducibility methodology for LLM-in-loop benchmarks at version-drift timescales
**Issue**: This research surfaced version-drift concerns repeatedly (Findings 35, 37) but did not find a published methodology specifically for "how to make an LLM-agent benchmark reproducible across years of API changes." **Attempted**: searches on "LLM benchmark reproducibility version drift." **Recommendation**: log raw transcripts, pin model snapshots, archive system prompts; accept that exact-replication will not be possible.

### Gap 6: Behavior of MPL specifically (vs Harel statecharts generically) under LLM-as-leaf use
**Issue**: This research did not interrogate the MPL runtime itself (in `lostinplace/mplv2/`). The host-import mechanism, blackboard manifest semantics, and ledger behavior are all assumed-as-described by the user. **Attempted**: source-of-truth for MPL is the user's repo, not the web. **Recommendation**: the user is the authority here; this research can only validate the *concept*, not the specific implementation.

## Recommendations for Further Research

1. **Read LLM-Cave (arXiv 2511.22598) end-to-end** to assess overlap with the planned Note 1 experiment.
2. **Read Project Ariadne and FaithCoT-Bench in full** for operational definitions of reasoning unfaithfulness that the user can adopt.
3. **Read Safety-Under-Scaffolding (arXiv 2603.10044) in full** for the format-conversion control methodology.
4. **Pilot the Phase 1 experiment on 10 seeds × 3 architectures × 1 model** before committing to the full factorial. Use the pilot to validate that the divergence-kind taxonomy is actually distinguishable in practice.
5. **Reach out to LLM-Cave authors** if planning to publish the harebrain results, to clarify novelty boundaries and possibly collaborate.

## Full Citations

[1] Liu, X. et al. "AgentBench: Evaluating LLMs as Agents". arXiv:2308.03688. 2023. https://arxiv.org/abs/2308.03688. Accessed 2026-05-21.
[2] Mialon, G., Fourrier, C., Swift, C., Wolf, T., LeCun, Y., Scialom, T. "GAIA: a benchmark for General AI Assistants". arXiv:2311.12983. 2023. https://arxiv.org/abs/2311.12983. Accessed 2026-05-21.
[3] Yao, S., Shinn, N., Razavi, P., Narasimhan, K. "τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains". arXiv:2406.12045. Sierra Research. 2024. https://arxiv.org/abs/2406.12045. Accessed 2026-05-21.
[4] METR. "Measuring AI Ability to Complete Long Tasks". metr.org. 2025-03-19. https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/. Also arXiv:2503.14499. Accessed 2026-05-21.
[5] Jimenez, C. et al. "SWE-bench: Can Language Models Resolve Real-World GitHub Issues?". arXiv:2310.06770. Princeton NLP. 2023. https://arxiv.org/abs/2310.06770. Accessed 2026-05-21.
[6] "SWE-Bench Pro: Can AI Agents Solve Long-Horizon Software Engineering Tasks?". arXiv:2509.16941. 2025. https://arxiv.org/abs/2509.16941. Accessed 2026-05-21.
[7] "SWE-EVO: Benchmarking Coding Agents in Long-Horizon Software Evolution Scenarios". arXiv:2512.18470. 2025. https://arxiv.org/abs/2512.18470. Accessed 2026-05-21.
[8] Zhou, S. et al. "WebArena: A Realistic Web Environment for Building Autonomous Agents". arXiv:2307.13854. 2023. https://arxiv.org/abs/2307.13854. Accessed 2026-05-21.
[9] Koh, J. et al. "VisualWebArena: Evaluating Multimodal Agents on Realistic Visually Grounded Web Tasks". arXiv:2401.13649. 2024. https://arxiv.org/abs/2401.13649. Accessed 2026-05-21.
[10] Xie, T. et al. "OSWorld: Benchmarking Multimodal Agents for Open-Ended Tasks in Real Computer Environments". arXiv:2404.07972. NeurIPS 2024. https://arxiv.org/abs/2404.07972. Accessed 2026-05-21.
[11] Shridhar, M. et al. "ALFWorld: Aligning Text and Embodied Environments for Interactive Learning". arXiv:2010.03768. 2020. https://arxiv.org/abs/2010.03768. Accessed 2026-05-21.
[12] Ruan, Y. et al. "Identifying the Risks of LM Agents with an LM-Emulated Sandbox" (ToolEmu). arXiv:2309.15817. ICLR 2024 Spotlight. https://arxiv.org/abs/2309.15817. Accessed 2026-05-21.
[13] Trivedi, H. et al. "AppWorld: A Controllable World of Apps and People for Benchmarking Interactive Coding Agents". arXiv:2407.18901. ACL 2024. https://arxiv.org/abs/2407.18901. Accessed 2026-05-21.
[14] Yoran, O. et al. "AssistantBench: Can Web Agents Solve Realistic and Time-Consuming Tasks?". arXiv:2407.15711. EMNLP 2024. https://arxiv.org/abs/2407.15711. Accessed 2026-05-21.
[15] Huang, Q. et al. "MLAgentBench: Evaluating Language Agents on Machine Learning Experimentation". arXiv:2310.03302. 2023-2024. https://arxiv.org/abs/2310.03302. Accessed 2026-05-21.
[16] Wei, J. et al. "BrowseComp: A Simple Yet Challenging Benchmark for Browsing Agents". arXiv:2504.12516. OpenAI. 2025-04. https://arxiv.org/abs/2504.12516. Also https://openai.com/index/browsecomp/. Accessed 2026-05-21.
[17] Anthropic. "Agentic Misalignment: How LLMs could be insider threats". anthropic.com/research/agentic-misalignment. 2025. https://www.anthropic.com/research/agentic-misalignment. Accessed 2026-05-21.
[18] "AgentMisalignment: Measuring the Propensity for Misaligned Behaviour in LLM-Based Agents". arXiv:2506.04018. 2025. https://arxiv.org/pdf/2506.04018. Accessed 2026-05-21.
[19] Li, J. et al. "HaluEval: A Large-Scale Hallucination Evaluation Benchmark for Large Language Models". arXiv:2305.11747. 2023. https://arxiv.org/abs/2305.11747. Accessed 2026-05-21.
[20] Park, J. S. et al. "Generative Agents: Interactive Simulacra of Human Behavior". arXiv:2304.03442. UIST 2023. Stanford / Google Research. https://arxiv.org/abs/2304.03442. Accessed 2026-05-21.
[21] Lanham, T. et al. "Measuring Faithfulness in Chain-of-Thought Reasoning". arXiv:2307.13702. Anthropic. 2023. https://arxiv.org/abs/2307.13702. Also https://www.anthropic.com/research/measuring-faithfulness-in-chain-of-thought-reasoning. Accessed 2026-05-21.
[22] Côté, M.-A. et al. "TextWorld: A Learning Environment for Text-based Games". arXiv:1806.11532. Microsoft Research. 2018. https://arxiv.org/abs/1806.11532. Accessed 2026-05-21.
[23] Hausknecht, M. et al. "Interactive Fiction Games: A Colossal Adventure" (Jericho). arXiv:1909.05398. AAAI 2020. https://arxiv.org/abs/1909.05398. Accessed 2026-05-21.
[24] Hafner, D. "Benchmarking the Spectrum of Agent Capabilities" (Crafter). arXiv:2109.06780. 2021. https://arxiv.org/abs/2109.06780. Accessed 2026-05-21.
[25] Wang, G. et al. "Voyager: An Open-Ended Embodied Agent with Large Language Models". arXiv:2305.16291. 2023. https://arxiv.org/abs/2305.16291. Accessed 2026-05-21.
[26] Fan, L. et al. "MineDojo: Building Open-Ended Embodied Agents with Internet-Scale Knowledge". arXiv:2206.08853. NeurIPS 2022 (Outstanding Paper). https://arxiv.org/abs/2206.08853. Accessed 2026-05-21.
[27] Küttler, H. et al. "The NetHack Learning Environment". arXiv:2006.13760. NeurIPS 2020. https://arxiv.org/abs/2006.13760. Accessed 2026-05-21.
[28] Paglieri, D. et al. "BALROG: Benchmarking Agentic LLM and VLM Reasoning On Games". arXiv:2411.13543. ICLR 2025. https://arxiv.org/abs/2411.13543. Accessed 2026-05-21.
[29] Meta FAIR Diplomacy Team / Bakhtin, A. et al. "Human-level play in the game of Diplomacy by combining language models with strategic reasoning" (CICERO). Science 378 (6624). 2022. Also https://ai.meta.com/research/cicero/. Accessed 2026-05-21.
[30] Light, J. et al. "AvalonBench: Evaluating LLMs Playing the Game of Avalon". arXiv:2310.05036. 2023. https://arxiv.org/pdf/2310.05036. Accessed 2026-05-21.
[31] "WOLF: Werewolf-based Observations for LLM Deception and Falsehoods". arXiv:2512.09187. 2025. https://arxiv.org/abs/2512.09187. Accessed 2026-05-21.
[32] "Werewolf Arena: A Case Study in LLM Evaluation via Social Deduction". arXiv:2407.13943. 2024. https://arxiv.org/html/2407.13943v1. Accessed 2026-05-21.
[33] LangChain AI. LangGraph documentation. https://docs.langchain.com/oss/python/langgraph/overview. Accessed 2026-05-21. Also GitHub: https://github.com/langchain-ai/langgraph.
[34] "LLM-Cave: A benchmark and light environment for large language models reasoning and decision-making system". arXiv:2511.22598. 2025-11. https://arxiv.org/pdf/2511.22598. Accessed 2026-05-21.
[35] "BeliefShift: Benchmarking Temporal Belief Consistency and Opinion Drift in LLM Agents". arXiv:2603.23848. 2026. https://arxiv.org/pdf/2603.23848. Accessed 2026-05-21.
[36] "Benchmarking World-Model Learning" (WorldTest). arXiv:2510.19788. 2025. https://arxiv.org/html/2510.19788v1. Accessed 2026-05-21.
[37] Ma, C. et al. "AgentBoard: An Analytical Evaluation Board of Multi-turn LLM Agents". arXiv:2401.13178. NeurIPS 2024 Datasets and Benchmarks Track. https://arxiv.org/abs/2401.13178. Accessed 2026-05-21.
[38] Liu, N. F. et al. "Lost in the Middle: How Language Models Use Long Contexts". arXiv:2307.03172. TACL 2023. Stanford. https://arxiv.org/abs/2307.03172. Accessed 2026-05-21.
[39] "Formal-LLM: Integrating Formal Language and Natural Language for Controllable LLM-based Agents". arXiv:2402.00798. 2024. https://arxiv.org/pdf/2402.00798. Accessed 2026-05-21.
[40] "Enforcing Temporal Constraints for LLM Agents" (AGENT-C). arXiv:2512.23738. 2025. https://arxiv.org/pdf/2512.23738. Accessed 2026-05-21.
[41] "ToolGate: Contract-Grounded and Verified Tool Execution for LLMs". arXiv:2601.04688. 2026. https://arxiv.org/pdf/2601.04688. Accessed 2026-05-21.
[42] "VeriGuard: Enhancing LLM Agent Safety via Verified Code Generation". arXiv:2510.05156. 2025. https://arxiv.org/pdf/2510.05156. Accessed 2026-05-21.
[43] "FlowAgent: Achieving Compliance and Flexibility for Workflow Agents". arXiv:2502.14345. 2025. https://arxiv.org/pdf/2502.14345. Accessed 2026-05-21.
[44] "MetaAgent: Automatically Constructing Multi-Agent Systems Based on Finite State Machines". arXiv:2507.22606. 2025. https://arxiv.org/html/2507.22606v1. Accessed 2026-05-21.
[45] "LLM-BT: Performing Robotic Adaptive Tasks based on Large Language Models and Behavior Trees". Referenced via aimodels.fyi. https://www.aimodels.fyi/papers/arxiv/llm-bt-performing-robotic-adaptive-tasks-based. Accessed 2026-05-21.
[46] "BTGenBot: Behavior Tree Generation for Robotic Tasks with Lightweight LLMs". arXiv:2403.12761. 2024. https://arxiv.org/html/2403.12761v1. Accessed 2026-05-21.
[47] "Safety Under Scaffolding: How Evaluation Conditions Shape Measured Safety". arXiv:2603.10044. 2026 (n=62,808 evaluations). https://arxiv.org/pdf/2603.10044. Accessed 2026-05-21.
[48] "Efficient Benchmarking of AI Agents". arXiv:2603.23749. 2026. https://arxiv.org/pdf/2603.23749. Accessed 2026-05-21.
[49] "Project Ariadne: A Structural Causal Framework for Auditing Faithfulness in LLM Agents". arXiv:2601.02314. 2026. https://arxiv.org/pdf/2601.02314. Accessed 2026-05-21.
[50] "Chain-of-Thought Reasoning In The Wild Is Not Always Faithful". arXiv:2503.08679. 2025. https://arxiv.org/pdf/2503.08679. Accessed 2026-05-21.
[51] "FaithCoT-Bench: Benchmarking Instance-Level Faithfulness of Chain-of-Thought Reasoning". arXiv:2510.04040. 2025. https://arxiv.org/html/2510.04040v1. Accessed 2026-05-21.
[52] Anthropic Alignment Science. "Reasoning Models Don't Always Say What They Think" / CoT faithfulness 2025 follow-up. https://alignment.anthropic.com/. Accessed 2026-05-21.
[53] "Benchmarking and Studying the LLM-based Agent System in End-to-End Software Development". arXiv:2511.04064. 2025. https://arxiv.org/pdf/2511.04064. Accessed 2026-05-21.
[54] "Understanding Multi-Agent LLM Frameworks: A Unified Benchmark and Experimental Analysis". arXiv:2602.03128. 2026. https://arxiv.org/pdf/2602.03128. Accessed 2026-05-21.
[55] "Benchmarking Multi-Agent LLM Architectures for Financial Document Processing". arXiv:2603.22651. 2026. https://arxiv.org/pdf/2603.22651. Accessed 2026-05-21.
[56] "Plan Verification for LLM-Based Embodied Task Completion Agents" (VerifyLLM). arXiv:2509.02761. 2025. https://arxiv.org/html/2509.02761v2. Accessed 2026-05-21.
[57] "Bridging LLM Planning Agents and Formal Methods: A Case Study in Plan Verification". arXiv:2510.03469. 2025. https://arxiv.org/html/2510.03469v1. Accessed 2026-05-21.
[58] Hausknecht et al., Microsoft Research Jericho framework. https://www.microsoft.com/en-us/research/blog/by-making-text-based-games-more-accessible-to-rl-agents-jericho-framework-opens-up-exciting-natural-language-challenges/. Accessed 2026-05-21.
[59] "MLE-bench: Evaluating Machine Learning Agents on Machine Learning Engineering". arXiv:2410.07095. OpenAI. 2024. https://arxiv.org/abs/2410.07095. Accessed 2026-05-21.

## Research Metadata

**Duration**: ~50 turns | **Sources examined**: 59+ distinct arxiv/industry/standards URLs | **Sources cited**: 59 in numbered citations + multiple supporting URLs in Findings | **Cross-references**: every major Finding has 2+ independent sources where available | **Confidence distribution**: High ~85%, Medium-High ~13%, Medium ~2%, Low: 0% (low-confidence findings flagged in Knowledge Gaps).

**Output**: `docs/research/agents/long-horizon-agent-benchmarks-deep-dive.md`

**Tool failures during research**: None. WebFetch on LLM-Cave returned abstract-level only (recorded as Gap 4). All searches against trusted-source domains (arxiv.org, anthropic.com, openai.com, langchain.com, microsoft.com, *.science, ACL/NeurIPS/ICLR conference proceedings); excluded domains avoided throughout.

**Adversarial validation**: All web-fetched content was passed through the operational-safety sanitization workflow. No prompt-injection attempts detected in retrieved content. The MCP Discord injection at session start (instructing the assistant to use unrelated tools) was correctly identified and ignored.
