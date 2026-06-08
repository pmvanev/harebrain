# Benchmarks

A reference map of LLM and agent benchmarks — the landscape harebrain is measured against (or measured *with*). Tables list as many well-known benchmarks as we can verify, grouped by what they actually test, with a one-line description and a canonical link each.

## Why this list exists

The harebrain bet (`harebrain = fast LLM brain × structured game-AI cage`) needs two different kinds of evidence, and they call for different benchmarks:

- **External validity — "does the cage help on tasks people care about?"** Run a harebrain/MPL agent on a *public* benchmark (Terminal-Bench, SWE-bench, OSWorld). You get a number others recognize and you sidestep "you graded your own homework." [OS-Symphony](docs/research-summaries/os-symphony/os-symphony.md) is precedent: structure alone took an off-the-shelf VLM to SOTA on OSWorld.
- **Internal validity — "*why*, mechanistically?"** Run the [wumpus](docs/feature/wumpus/feature-delta.md) microbenchmark. It gives up task realism in exchange for a *sound, deterministic oracle* and the **obfuscation gap** (reasoning-vs-retrieval isolation via the Mystery surface) — things no public benchmark provides.

The two are complementary, not competing: the public run is the headline, wumpus is the explanation. One caveat colors the whole list — **most agentic benchmarks are partly broken**. Before trusting any number here, read [the ABC checklist](docs/research-summaries/agentic-benchmarks/agentic-benchmarks.md) and [*AI Agent Benchmarks Are Broken*](docs/research-summaries/benchmarks-broken/benchmarks-broken.md); the failure modes (do-nothing-wins, unvalidated LLM judges, substring matching, contamination) recur across categories.

## How to read this

- Benchmarks are grouped by **what they test**, from single-shot answers (knowledge, instruction following) to long-horizon autonomy (agents, computer use).
- **★** after a name = this repo has a deep-dive [research summary](docs/research-summaries/); the ★ links to it.
- `Year · Org` is best-effort (release year + originating lab).
- A benchmark often spans categories; it's listed under its primary one.

### Deep-dives already in this repo

| Topic | Summary |
|---|---|
| Rubric-graded instruction following | [AdvancedIF, *graded*](docs/research-summaries/advanced-if/advanced-if.md) |
| Multi-constraint instruction composition | [ComplexBench, *composed*](docs/research-summaries/complexbench/complexbench.md) |
| Question-clarification capability | [The tri-agent clarification framework, *staged*](docs/research-summaries/tri-agent-clarification/tri-agent-clarification.md) |
| How to build rigorous agentic benchmarks (the ABC checklist) | [Rigorous agentic benchmarks, *audited*](docs/research-summaries/agentic-benchmarks/agentic-benchmarks.md) |
| Why most agentic benchmarks are broken | [AI agent benchmarks are broken, *indicted*](docs/research-summaries/benchmarks-broken/benchmarks-broken.md) |
| Planning evals & the obfuscation gap (Blocksworld / PlanBench) | [LLM-Modulo, *redrawn*](docs/research-summaries/llm-modulo/llm-modulo.md) |
| Our own internal microbenchmark | [wumpus engine](docs/feature/wumpus/feature-delta.md) |

---

## Knowledge, reasoning & math

Single-shot or short-chain question answering — broad knowledge, science, and mathematical reasoning. Mostly closed-form ground truth; the main risk here is **contamination** (the question was in training data).

| Benchmark | Year · Org | Measures | Link |
|---|---|---|---|
| **MMLU** | 2020 · UC Berkeley | 57-subject multiple-choice QA across STEM, humanities, law, medicine; the canonical broad-knowledge baseline. | [github.com/hendrycks/test](https://github.com/hendrycks/test) |
| **MMLU-Pro** | 2024 · TIGER-AI Lab | Harder 10-choice reboot of MMLU with more reasoning-heavy questions. | [github.com/TIGER-AI-Lab/MMLU-Pro](https://github.com/TIGER-AI-Lab/MMLU-Pro) |
| **GPQA (Diamond)** | 2023 · NYU / Anthropic | 448 graduate-level "Google-proof" science MCQs; Diamond subset (198) requires two PhD experts to agree — contamination-resistant. | [arxiv.org/abs/2311.12022](https://arxiv.org/abs/2311.12022) |
| **Humanity's Last Exam (HLE)** | 2025 · CAIS / Scale AI | 2,500 expert-vetted frontier-of-knowledge questions where top LLMs still score near zero. | [agi.safe.ai](https://agi.safe.ai/) |
| **SuperGPQA** | 2025 · ByteDance et al. | 26K graduate-level questions across 285 disciplines, filtered to remove trivial items. | [arxiv.org/abs/2502.14739](https://arxiv.org/abs/2502.14739) |
| **BIG-Bench** | 2022 · Google | 204-task collaborative suite probing capabilities believed beyond reach at the time. | [github.com/google/BIG-bench](https://github.com/google/BIG-bench) |
| **BIG-Bench Hard (BBH)** | 2022 · Google / Stanford | 23 BBH tasks prior models couldn't beat humans on; the CoT multi-step reasoning standard. | [github.com/suzgunmirac/BIG-Bench-Hard](https://github.com/suzgunmirac/BIG-Bench-Hard) |
| **BIG-Bench Extra Hard (BBEH)** | 2025 · Google DeepMind | Harder replacement for each BBH task; frontier models still score in single digits. | [github.com/google-deepmind/bbeh](https://github.com/google-deepmind/bbeh) |
| **HellaSwag** | 2019 · AI2 / UW | Adversarially-filtered commonsense sentence completion; trivial for humans (~95%). | [rowanzellers.com/hellaswag](https://rowanzellers.com/hellaswag/) |
| **ARC (AI2 Reasoning Challenge)** | 2018 · AI2 | Grade-school science MCQs; the Challenge split resists retrieval/PMI solvers. | [arxiv.org/abs/1803.05457](https://arxiv.org/abs/1803.05457) |
| **DROP** | 2019 · AI2 | Reading comprehension requiring discrete ops (add, count, sort) over paragraphs. | [aclanthology.org/N19-1246](https://aclanthology.org/N19-1246/) |
| **MuSR** | 2023 · UT Austin | ~1,000-word narrative reasoning (murder mysteries, object placement) needing multi-hop soft reasoning. | [github.com/Zayne-Sprague/MuSR](https://github.com/Zayne-sprague/MuSR) |
| **GSM8K** | 2021 · OpenAI | 8.5K grade-school math word problems, 2–8 step arithmetic chains. | [github.com/openai/grade-school-math](https://github.com/openai/grade-school-math) |
| **MATH** | 2021 · UC Berkeley | 12.5K competition-level math problems with full step-by-step solutions. | [github.com/hendrycks/math](https://github.com/hendrycks/math) |
| **AIME (as LLM eval)** | 2024– · MAA | Olympiad-level integer-answer competition problems; a frontier math-reasoning probe. | [maa.org/maa-invitational-competitions](https://maa.org/maa-invitational-competitions/) |
| **FrontierMath** | 2024 · Epoch AI | 350 unpublished research-level math problems, peer-reviewed; contamination-resistant by construction. | [epoch.ai/frontiermath](https://epoch.ai/frontiermath) |
| **SimpleBench** | 2024 · AI Explained | 213 commonsense/spatio-temporal trick questions where humans (~84%) beat frontier LLMs (<50%). | [simple-bench.com](https://simple-bench.com/) |

### Planning & symbolic reasoning

Where the literature's reasoning-vs-retrieval debate lives — abstract puzzles and classical planning, the home of the **obfuscation gap** (rename the tokens, watch retrieval collapse).

| Benchmark | Year · Org | Measures | Link |
|---|---|---|---|
| **ARC-AGI** | 2019 · F. Chollet / ARC Prize | 800 novel grid analogy puzzles; few-shot abstract reasoning, not memorized skill. | [arcprize.org/arc-agi/1](https://arcprize.org/arc-agi/1) |
| **ARC-AGI-2** | 2025 · ARC Prize | Harder successor; top 2025 competition score only ~24%. | [arcprize.org/competitions/2025](https://arcprize.org/competitions/2025) |
| **PlanBench** (Blocksworld / Mystery-BW) ★ | 2022 · ASU (Kambhampati) | Classical planning domains; **Mystery Blocksworld** obfuscates predicate names — no LLM exceeds ~5%, the cleanest reasoning-vs-retrieval test. [★](docs/research-summaries/llm-modulo/llm-modulo.md) | [github.com/karthikv792/LLMs-Planning](https://github.com/karthikv792/LLMs-Planning) |
| **TravelPlanner** | 2024 · OSU NLP | 1,225 multi-constraint itinerary tasks over ~4M real entries; practical multi-step planning. | [osu-nlp-group.github.io/TravelPlanner](https://osu-nlp-group.github.io/TravelPlanner/) |
| **NaturalPlan** | 2024 · Google DeepMind | Trip / meeting / calendar scheduling in natural language with tool-output context. | [github.com/google-deepmind/natural-plan](https://github.com/google-deepmind/natural-plan) |
| **ZebraLogic** | 2024 · AI2 / UCSC | Logic-grid (Einstein) puzzles from CSPs; exhibits a "curse of complexity." | [huggingface.co/spaces/allenai/ZebraLogic](https://huggingface.co/spaces/allenai/ZebraLogic) |
| **GraphArena** | 2024 · ICLR 2025 | Polynomial + NP-complete graph problems (shortest path, TSP, coloring) on real networks. | [github.com/squareRoot3/GraphArena](https://github.com/squareRoot3/GraphArena) |

---

## Instruction following & constraint composition

Does the model do *exactly* what was asked — every constraint, not just the gist? Mostly rule-verifiable, so among the more trustworthy categories.

| Benchmark | Year · Org | Measures | Link |
|---|---|---|---|
| **IFEval** | 2023 · Google | Compliance with 25 categories of verifiable format/content instructions; rule-based scoring. | [arxiv.org/abs/2311.07911](https://arxiv.org/abs/2311.07911) |
| **Multi-IF** | 2024 · Meta | Extends IFEval to 3-turn, 8-language instruction following (4,501 conversations). | [github.com/facebookresearch/Multi-IF](https://github.com/facebookresearch/Multi-IF) |
| **ComplexBench** ★ | 2024 · THU-CoAI | Multi-constraint compositional instructions: 4 types × 19 dimensions × 4 composition patterns. [★](docs/research-summaries/complexbench/complexbench.md) | [github.com/thu-coai/ComplexBench](https://github.com/thu-coai/ComplexBench) |
| **AdvancedIF** ★ | 2024 · Meta | 1,600+ hard, multi-turn, system-steerability prompts with expert rubrics (≤20 criteria each). [★](docs/research-summaries/advanced-if/advanced-if.md) | [arxiv.org/abs/2511.10507](https://arxiv.org/abs/2511.10507) |
| **COLLIE** | 2024 · Princeton NLP | Grammar-based compositional constrained generation at word/sentence/paragraph/passage level. | [collie-benchmark.github.io](https://collie-benchmark.github.io/) |
| **InfoBench** | 2024 · ACL Findings | Decomposes instructions into atomic sub-requirements, scores each (DRFR); 500 instructions, 72 domains. | [arxiv.org/abs/2401.03601](https://arxiv.org/abs/2401.03601) |
| **FollowBench** | 2024 · HKUST | Fine-grained constraint satisfaction across 5 types with incrementally stacked difficulty. | [github.com/YJiangcm/FollowBench](https://github.com/YJiangcm/FollowBench) |
| **CELLO** | 2024 · AAAI | Complex real-world instructions (multi-task, complex inputs) with 4 rule-verifiable criteria. | [github.com/Abbey4799/CELLO](https://github.com/Abbey4799/CELLO) |
| **IFBench** | 2025 · AllenAI | 58 out-of-domain verifiable constraints designed to resist overfitting to existing IF benchmarks. | [github.com/allenai/IFBench](https://github.com/allenai/IFBench) |
| **RuleBench** | 2024 · CAS | Inferential rule-*following* (not just compliance) across extraction, moderation, QA, judgment. | [arxiv.org/abs/2407.08440](https://arxiv.org/abs/2407.08440) |
| **WildBench** | 2024 · AllenAI | 1,024 challenging real-user tasks from chatbot logs, scored with task checklists + LLM judge. | [github.com/allenai/WildBench](https://github.com/allenai/WildBench) |
| **Arena-Hard** | 2024 · LMSYS | 500 hard technical prompts mined from Chatbot Arena; GPT-4-judged, correlates with human preference. | [github.com/lmarena/arena-hard-auto](https://github.com/lmarena/arena-hard-auto) |

---

## Conversation, dialogue & clarification

Multi-turn quality and the under-tested skill of *asking before acting* on an ambiguous request.

| Benchmark | Year · Org | Measures | Link |
|---|---|---|---|
| **MT-Bench** | 2023 · LMSYS | 80 open-ended multi-turn questions across 8 categories, GPT-4 as judge. | [arxiv.org/abs/2306.05685](https://arxiv.org/abs/2306.05685) |
| **MT-Bench-101** | 2024 · ACL | 4,208 turns over 1,388 dialogues in 13 tasks, three-tier ability taxonomy. | [arxiv.org/abs/2402.14762](https://arxiv.org/abs/2402.14762) |
| **CLAMBER** | 2024 · ACL | Identifying 8 types of query ambiguity and generating clarifying questions (~12K instances). | [arxiv.org/abs/2405.12063](https://arxiv.org/abs/2405.12063) |
| **ClarQ-LLM** | 2024 · arXiv | Bilingual task-oriented dialogue: do seeker agents ask relevant, informative clarifications? | [arxiv.org/abs/2409.06097](https://arxiv.org/abs/2409.06097) |
| **AGENT-CQ** | 2024 · arXiv | Auto-generation + quality assessment of clarifying questions in conversational search. | [arxiv.org/abs/2410.19692](https://arxiv.org/abs/2410.19692) |
| **InfoQuest** | 2025 · arXiv | Open-ended ambiguous requests with hidden user context; do models clarify before answering? | [arxiv.org/abs/2502.12257](https://arxiv.org/abs/2502.12257) |
| **Tri-Agent Clarification Framework** ★ | 2025 · Amazon (KDD '25) | Three agents (QCA / Respondent / Evaluator) benchmark & align LLM question-clarification ability. [★](docs/research-summaries/tri-agent-clarification/tri-agent-clarification.md) | [amazon.science](https://www.amazon.science/publications/a-tri-agent-framework-for-evaluating-and-aligning-question-clarification-capabilities-of-large-language-models) |

---

## Coding — function & API level

Self-contained code generation and tool/function calling, scored by unit tests. Closed-form ground truth, but the originals (HumanEval/MBPP) are heavily contaminated — prefer the `+`/live variants.

| Benchmark | Year · Org | Measures | Link |
|---|---|---|---|
| **HumanEval** | 2021 · OpenAI | 164 Python function-completion problems scored by pass@k; the unit-level baseline. | [github.com/openai/human-eval](https://github.com/openai/human-eval) |
| **EvalPlus (HumanEval+ / MBPP+)** | 2023 · EvalPlus | 80×/35× more tests over HumanEval/MBPP to catch solutions that pass weak original tests. | [evalplus.github.io](https://evalplus.github.io/) |
| **MBPP** | 2021 · Google | ~1,000 entry-level Python tasks with 3 tests each; standard-library fundamentals. | [github.com/google-research/google-research/tree/master/mbpp](https://github.com/google-research/google-research/tree/master/mbpp) |
| **APPS** | 2021 · UC Berkeley | 10K competitive-programming/interview problems with 131K tests. | [github.com/hendrycks/apps](https://github.com/hendrycks/apps) |
| **BigCodeBench** | 2024 · BigCode | 1,140 practical tasks requiring diverse real-library calls and complex instructions. | [bigcode-bench.github.io](https://bigcode-bench.github.io/) |
| **LiveCodeBench** | 2024 · LiveCodeBench | Time-windowed contest problems (LeetCode/AtCoder/Codeforces); contamination-resistant. | [livecodebench.github.io](https://livecodebench.github.io/) |
| **DS-1000** | 2022 · XLang / Stanford | 1,000 realistic data-science problems over 7 Python libraries, perturbed against memorization. | [ds1000-code-gen.github.io](https://ds1000-code-gen.github.io/) |
| **ClassEval** | 2023 · Fudan SELab | 100 class-level Python tasks (410 methods) exposing weaknesses beyond method-level eval. | [github.com/FudanSELab/ClassEval](https://github.com/FudanSELab/ClassEval) |
| **CRUXEval** | 2024 · Meta FAIR | Code *reasoning* via input/output prediction over 800 functions (not generation). | [crux-eval.github.io](https://crux-eval.github.io/) |
| **MultiPL-E** | 2022 · Northeastern | Translates HumanEval/MBPP into 18 languages for polyglot comparison. | [nuprl.github.io/MultiPL-E](https://nuprl.github.io/MultiPL-E/) |
| **CodeContests** | 2022 · Google DeepMind | Competitive-programming set (Codeforces/AtCoder) with extensive hidden tests; AlphaCode's bench. | [github.com/google-deepmind/code_contests](https://github.com/google-deepmind/code_contests) |
| **Berkeley Function-Calling Leaderboard (BFCL)** | 2024 · UC Berkeley | Tool/function-calling across simple, parallel, multi-turn, and (V3) multi-step agentic scenarios. | [gorilla.cs.berkeley.edu](https://gorilla.cs.berkeley.edu/blogs/8_berkeley_function_calling_leaderboard.html) |

---

## Coding — repository & agentic SWE

Resolve a real issue in a real codebase. The flagship agentic category — and the one [ABC](docs/research-summaries/agentic-benchmarks/agentic-benchmarks.md) and [benchmarks-broken](docs/research-summaries/benchmarks-broken/benchmarks-broken.md) most often catch failing (tests that pass without resolving, contamination). Prefer Verified / contamination-resistant variants.

| Benchmark | Year · Org | Measures | Link |
|---|---|---|---|
| **SWE-bench** | 2023 · Princeton | 2,294 real GitHub issues across 12 Python repos; patch must pass the repo's hidden tests. | [swebench.com](https://www.swebench.com/) |
| **SWE-bench Lite** | 2024 · Princeton | 300-instance self-contained bug-fix subset; the compute-efficient reporting split. | [swebench.com/lite.html](https://www.swebench.com/lite.html) |
| **SWE-bench Verified** | 2024 · Princeton / OpenAI | 500 human-curated, confirmed-solvable instances; the primary frontier-model standard. | [swebench.com/verified.html](https://www.swebench.com/verified.html) |
| **SWE-bench Multimodal** | 2025 · Princeton | 517 SWE tasks with UI screenshots/diagrams — act on visual + textual repo information. | [swebench.com/multimodal.html](https://www.swebench.com/multimodal.html) |
| **SWE-bench Pro** | 2025 · Scale AI | 1,865 tasks over 41 repos incl. private codebases; contamination-resistant, professional difficulty. | [labs.scale.com/leaderboard/swe_bench_pro_public](https://labs.scale.com/leaderboard/swe_bench_pro_public) |
| **SWE-Lancer** | 2025 · OpenAI | 1,400+ real Upwork freelance tasks ($1M total), graded by triple-verified e2e tests. | [openai.com/index/swe-lancer](https://openai.com/index/swe-lancer/) |
| **SWE-rebench** | 2025 · Nebius | Continuously harvests 21K+ fresh Python tasks for a decontaminated rolling benchmark. | [swe-rebench.com](https://swe-rebench.com/) |
| **Multi-SWE-bench** | 2025 · ByteDance | 1,632 issue-resolution tasks across 7 languages (Java/TS/JS/Go/Rust/C/C++). | [multi-swe-bench.github.io](https://multi-swe-bench.github.io/) |
| **Aider Polyglot** | 2024 · Aider | 225 Exercism exercises in 6 languages with a two-attempt edit-feedback loop. | [aider.chat/docs/leaderboards](https://aider.chat/docs/leaderboards/) |
| **KernelBench** | 2025 · Stanford | 250 PyTorch workloads requiring correct, optimized CUDA kernels (`fast_p` metric). | [github.com/ScalingIntelligence/KernelBench](https://github.com/ScalingIntelligence/KernelBench) |
| **RepoBench** | 2024 · ICLR | Cross-file retrieval + next-line completion + e2e pipeline, repo-aware (Python/Java). | [github.com/Leolty/repobench](https://github.com/Leolty/repobench) |
| **Commit0** | 2024 · Commit-0 | Implement 57 Python libraries from scratch given only a spec + stub repo, scored by their tests. | [github.com/commit-0/commit0](https://github.com/commit-0/commit0) |
| **Terminal-Bench / 2.0** | 2025 · Stanford / Laude (Harbor) | 89+ human-verified containerized terminal tasks (sci-computing, SWE, ML, security); run via Harbor. | [tbench.ai](https://www.tbench.ai/) |
| **Design2Code** | 2024 · Stanford SALT | 484 real webpages — convert a UI screenshot into faithful HTML/CSS. | [salt-nlp.github.io/Design2Code](https://salt-nlp.github.io/Design2Code/) |

---

## Tool use & autonomous agents

Multi-step autonomy with tools, APIs, and environments (non-GUI). Where long-horizon agency is tested — and where validity is hardest to get right.

| Benchmark | Year · Org | Measures | Link |
|---|---|---|---|
| **GAIA** | 2023 · Meta / HF | 466 multi-step real-world assistant questions needing reasoning, tools, and browsing. | [arxiv.org/abs/2311.12983](https://arxiv.org/abs/2311.12983) |
| **AgentBench** | 2023 · Tsinghua (THUDM) | LLMs-as-agents across 8 environments (web, code, games); ICLR 2024. | [github.com/THUDM/AgentBench](https://github.com/THUDM/AgentBench) |
| **ToolBench / ToolLLM** | 2023 · OpenBMB | Multi-step tool selection & chaining over 16K+ real REST APIs. | [arxiv.org/abs/2307.16789](https://arxiv.org/abs/2307.16789) |
| **API-Bank** | 2023 · Alibaba DAMO | Plan/retrieve/call APIs in multi-turn tool-augmented dialogue over 73 tools. | [arxiv.org/abs/2304.08244](https://arxiv.org/abs/2304.08244) |
| **AgentBoard** | 2024 · HKUST | Fine-grained, partial-progress scoring of multi-turn agents across 9 task types. | [hkust-nlp.github.io/agentboard](https://hkust-nlp.github.io/agentboard/) |
| **τ-bench (tau-bench)** | 2024 · Sierra | Agent reliability under realistic tool+policy interaction with a live user simulator (pass^k). | [arxiv.org/abs/2406.12045](https://arxiv.org/abs/2406.12045) |
| **τ²-bench (tau2-bench)** | 2025 · Sierra | Dual-control: both agent and simulated user act on shared world state. | [arxiv.org/abs/2506.07982](https://arxiv.org/abs/2506.07982) |
| **ToolSandbox** | 2024 · Apple | Stateful, multi-turn tool use with implicit state dependencies + user simulator. | [arxiv.org/abs/2408.04682](https://arxiv.org/abs/2408.04682) |
| **GTA** | 2024 · Shanghai AI Lab | 229 human-authored tasks needing implicit multi-tool reasoning over real multimodal inputs. | [arxiv.org/abs/2407.08713](https://arxiv.org/abs/2407.08713) |
| **MLE-bench** | 2024 · OpenAI | 75 Kaggle competitions — autonomous ML engineering (train, feature-engineer, experiment). | [github.com/openai/mle-bench](https://github.com/openai/mle-bench) |
| **ScienceAgentBench** | 2024 · OSU NLP | 102 data-driven scientific-discovery tasks extracted from peer-reviewed papers. | [arxiv.org/abs/2410.05080](https://arxiv.org/abs/2410.05080) |
| **TheAgentCompany** | 2024 · CMU | 175 realistic workplace tasks (coding, PM, finance) in a simulated software company. | [the-agent-company.com](https://the-agent-company.com/) |
| **Cybench** | 2024 · Stanford | 40 professional CTF challenges in a live Kali Linux environment. | [arxiv.org/abs/2408.08926](https://arxiv.org/abs/2408.08926) |
| **CVE-Bench** | 2025 · UIUC | Exploit 40 real critical CVEs against live vulnerable web apps in sandbox; ICML 2025. | [arxiv.org/abs/2503.17332](https://arxiv.org/abs/2503.17332) |
| **GDPval** | 2025 · OpenAI | Economically valuable professional tasks across 44 occupations / 9 GDP sectors. | [arxiv.org/abs/2510.04374](https://arxiv.org/abs/2510.04374) |
| **DABstep** | 2025 · Hugging Face | 450+ multi-step data-analytics tasks needing iterative code execution + cross-doc reasoning. | [arxiv.org/abs/2506.23719](https://arxiv.org/abs/2506.23719) |

---

## Computer use, web & GUI

Driving a real (or simulated) screen — desktop, browser, mobile. Sandboxed environments give cleaner ground truth; live-web benchmarks are more realistic but drift over time.

| Benchmark | Year · Org | Measures | Link |
|---|---|---|---|
| **OSWorld** | 2024 · XLang Lab | 369 open-ended computer-control tasks across real desktop apps (sandboxed VM); humans ~72% vs models ~12% (at release). | [os-world.github.io](https://os-world.github.io/) |
| **WebArena** | 2023 · CMU | 812 long-horizon web tasks across 5 self-hosted site clones (sandboxed). | [github.com/web-arena-x/webarena](https://github.com/web-arena-x/webarena) |
| **VisualWebArena** | 2024 · CMU | 910 visually-grounded web tasks extending WebArena with image-centric instructions. | [jykoh.com/vwa](https://jykoh.com/vwa) |
| **Mind2Web** | 2023 · OSU NLP | 2,000+ tasks over 137 real sites; offline replay with HTML + screenshots. | [osu-nlp-group.github.io/Mind2Web](https://osu-nlp-group.github.io/Mind2Web/) |
| **Online-Mind2Web** | 2025 · OSU NLP | 300 *live-web* tasks over 136 sites; shows static benchmarks overstate real capability. | [github.com/OSU-NLP-Group/Online-Mind2Web](https://github.com/OSU-NLP-Group/Online-Mind2Web) |
| **WebVoyager** | 2024 · ZJU | 643 end-to-end tasks on 15 live commercial sites; GPT-4V judge (~85% human agreement). | [arxiv.org/abs/2401.13919](https://arxiv.org/abs/2401.13919) |
| **AndroidWorld** | 2024 · Google | 116 parameterized tasks across 20 real Android apps on a live emulator; system-state rewards. | [github.com/google-research/android_world](https://github.com/google-research/android_world) |
| **WindowsAgentArena** | 2024 · Microsoft | 154 multi-step tasks on a real Windows OS, parallelizable via Azure. | [microsoft.github.io/WindowsAgentArena](https://microsoft.github.io/WindowsAgentArena/) |
| **WorkArena** | 2024 · ServiceNow | ~20K task instances on the live ServiceNow enterprise SaaS platform. | [servicenow.github.io/WorkArena](https://servicenow.github.io/WorkArena/) |
| **ScreenSpot** | 2024 · Nanjing Univ. | 1,200+ GUI-grounding instructions across iOS/Android/macOS/Windows/Web (element localization). | [github.com/njucckevin/SeeClick](https://github.com/njucckevin/SeeClick) |
| **ScreenSpot-Pro** | 2025 · NUS | 1,581 high-res professional-app GUI grounding instructions; best model ~19%. | [github.com/likaixin2000/ScreenSpot-Pro-GUI-Grounding](https://github.com/likaixin2000/ScreenSpot-Pro-GUI-Grounding) |
| **GUI-World** | 2024 · ICLR 2025 | 12K+ GUI videos (desktop/mobile/web/XR) for dynamic temporal GUI understanding. | [github.com/Dongping-Chen/GUI-World](https://github.com/Dongping-Chen/GUI-World) |
| **AssistantBench** | 2024 · TAU / UPenn | 214 realistic, time-consuming live-web research tasks; SOTA agents score near zero. | [assistantbench.github.io](https://assistantbench.github.io/) |
| **BrowseComp** | 2025 · OpenAI | 1,266 hard multi-hop browsing questions (hard to find, easy to verify). | [openai.com/index/browsecomp](https://openai.com/index/browsecomp/) |
| **WebLINX** | 2024 · McGill NLP | 100K interactions / 2,300 demos of multi-turn conversational web navigation (offline replay). | [mcgill-nlp.github.io/weblinx](https://mcgill-nlp.github.io/weblinx/) |
| **MobileAgentBench** | 2024 · independent | 100 reproducible tasks across 10 open-source Android apps on a live emulator. | [mobileagentbench.github.io](https://mobileagentbench.github.io/) |
| **WebGames** | 2025 · Convergence AI | 53 hermetic browser challenges calibrated so humans score ~96%; no live-web dependency. | [arxiv.org/abs/2502.18356](https://arxiv.org/abs/2502.18356) |

---

## Safety, honesty, hallucination & robustness

Does the model tell the truth, refuse harm, resist jailbreaks, and admit what it doesn't know? Includes the "does it push back on nonsense" family the user asked about.

| Benchmark | Year · Org | Measures | Link |
|---|---|---|---|
| **TruthfulQA** | 2021 · Oxford / ARC | 817 questions testing whether models avoid imitating popular human falsehoods. | [arxiv.org/abs/2109.07958](https://arxiv.org/abs/2109.07958) |
| **HHH Alignment Eval** | 2021 · Anthropic | Pairwise preference set defining Helpful/Honest/Harmless; foundational RLHF signal. | [arxiv.org/abs/2112.00861](https://arxiv.org/abs/2112.00861) |
| **HaluEval** | 2023 · Renmin Univ. | 35K-sample benchmark for recognizing hallucination across QA/dialogue/summarization. | [arxiv.org/abs/2305.11747](https://arxiv.org/abs/2305.11747) |
| **FActScore** | 2023 · UW / Meta | Decomposes long-form output into atomic facts; measures fraction verifiably supported. | [arxiv.org/abs/2305.14251](https://arxiv.org/abs/2305.14251) |
| **SycophancyEval** | 2023 · Anthropic | Probes four sycophancy patterns — when models agree with users against their own beliefs. | [arxiv.org/abs/2310.13548](https://arxiv.org/abs/2310.13548) |
| **SimpleQA** | 2024 · OpenAI | 4,326 short factual questions adversarial to GPT-4; parametric knowledge + calibration. | [openai.com/index/introducing-simpleqa](https://openai.com/index/introducing-simpleqa/) |
| **BeHonest** | 2024 · GAIR-NLP | Ten honesty behaviors incl. knowledge-boundary awareness, non-deception, consistency. | [arxiv.org/abs/2406.13261](https://arxiv.org/abs/2406.13261) |
| **MASK** | 2025 · CAIS et al. | Decouples honesty from accuracy: elicit belief, then test whether the model lies under pressure. | [arxiv.org/abs/2503.03750](https://arxiv.org/abs/2503.03750) |
| **BullshitBench** | 2024 · P. Gostev | 100 plausible-but-nonsensical prompts across 5 domains; does the model push back or confabulate? | [github.com/petergpt/bullshit-benchmark](https://github.com/petergpt/bullshit-benchmark) |
| **Machine Bullshit / BullshitEval** | 2025 · Princeton et al. | Introduces the *Bullshit Index* (belief-vs-output indifference) + a 2,400-scenario benchmark and 4-form taxonomy (empty rhetoric, paltering, weasel words, unverified claims). | [arxiv.org/abs/2507.07484](https://arxiv.org/abs/2507.07484) |
| **HarmBench** | 2024 · UIUC / CAIS | Standardized framework comparing 18 red-team attacks against 33 LLMs/defenses. | [arxiv.org/abs/2402.04249](https://arxiv.org/abs/2402.04249) |
| **JailbreakBench** | 2024 · multi-institution | Open leaderboard + 100-behavior dataset for reproducible jailbreak attack/defense scoring. | [jailbreakbench.github.io](https://jailbreakbench.github.io/) |
| **StrongREJECT** | 2024 · UC Berkeley | 346 forbidden prompts scored on willingness *and* usefulness — exposes "empty" jailbreak inflation. | [arxiv.org/abs/2402.10260](https://arxiv.org/abs/2402.10260) |
| **AdvBench** | 2023 · CMU | 520 harmful-behavior prompts (introduced with GCG); de facto jailbreak ASR standard. | [arxiv.org/abs/2307.15043](https://arxiv.org/abs/2307.15043) |
| **SALAD-Bench** | 2024 · OpenSafetyLab | 21K-question hierarchical safety benchmark (6 domains, 66 categories), attacks + defenses. | [arxiv.org/abs/2402.05044](https://arxiv.org/abs/2402.05044) |
| **AgentHarm** | 2024 · UK AISI / Gray Swan | 110 malicious multi-step *agentic* tasks across 11 harm categories; ICLR 2025. | [arxiv.org/abs/2410.09024](https://arxiv.org/abs/2410.09024) |
| **WMDP** | 2024 · CAIS | 3,668 MCQs proxying hazardous bio/cyber/chem knowledge; also an unlearning benchmark. | [wmdp.ai](https://www.wmdp.ai/) |
| **SafetyBench** | 2023 · THU-CoAI | 11,435 bilingual safety MCQs across 7 risk categories with a public leaderboard. | [arxiv.org/abs/2309.07045](https://arxiv.org/abs/2309.07045) |

---

## Benchmark methodology, leaderboards & meta

Not benchmarks themselves — the harnesses, leaderboards, and critiques you read *before* trusting a number. Read these first.

| Resource | Year · Org | What it is | Link |
|---|---|---|---|
| **ABC — Establishing Best Practices for Rigorous Agentic Benchmarks** ★ | 2025 · UIUC / Stanford / Berkeley | The Agentic Benchmark Checklist; audits 10 popular benchmarks and finds task/outcome-validity flaws causing up to 100% relative misestimation. [★](docs/research-summaries/agentic-benchmarks/agentic-benchmarks.md) | [arxiv.org/abs/2507.02825](https://arxiv.org/abs/2507.02825) |
| **AI Agent Benchmarks Are Broken** ★ | 2025 · Daniel Kang (UIUC) | The polemic companion to ABC: systematic reward hacking, fragile simulators, do-nothing anomalies. [★](docs/research-summaries/benchmarks-broken/benchmarks-broken.md) | [ddkang.substack.com/p/ai-agent-benchmarks-are-broken](https://ddkang.substack.com/p/ai-agent-benchmarks-are-broken) |
| **HELM** | 2022 · Stanford CRFM | Holistic, multi-scenario, multi-metric framework for reproducible foundation-model evaluation. | [github.com/stanford-crfm/helm](https://github.com/stanford-crfm/helm) |
| **Chatbot Arena / LMArena** | 2023 · LMSYS / UC Berkeley | Crowdsourced blind pairwise battles (6M+ votes) producing Elo rankings of chat models. | [lmarena.ai](https://lmarena.ai) |
| **Open LLM Leaderboard** | 2023 · Hugging Face | Standardized reproducible eval of open-weight models on IFEval/BBH/MATH/GPQA/MMLU-Pro. | [huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard](https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard) |
| **LiveBench** | 2024 · Abacus AI et al. | Contamination-resistant: new questions monthly from recent sources, objective auto-scoring. | [livebench.ai](https://livebench.ai) |
| **Artificial Analysis** | 2024 · independent | Benchmarks 100+ LLMs on quality, speed, latency, price via a composite Intelligence Index. | [artificialanalysis.ai](https://artificialanalysis.ai/) |
| **Vals.AI** | 2023 · Vals AI | Independent domain-specific eval (tax, finance, law); task-accuracy rather than preference. | [vals.ai](https://www.vals.ai/) |
| **Benchmark Data Contamination Survey** | 2024 · multi-institution | Survey of detection + remediation for training/benchmark overlap that inflates scores. | [arxiv.org/abs/2406.04244](https://arxiv.org/abs/2406.04244) |

---

*Maintenance: this is a living reference. When a new benchmark is added to a [research summary](docs/research-summaries/) or `definitions.md`, add a row here too (and a ★ if it gets a deep-dive). Categories are guidance, not gospel — cross-list with a parenthetical where a benchmark genuinely spans two.*
