# Definitions

A glossary of harebrain and LLM-benchmark terms used across this repo.

## Instruction-following benchmarks

| Term | Definition |
|---|---|
| **ComplexBench** | A benchmark for how well LLMs follow **complex, composite instructions** — prompts chaining multiple constraints (and / chain / selection / nesting). Scores whether *every* constraint is met, not just the gist. |
| **AdvancedIF** | An **advanced instruction-following** benchmark using expert-written, hard, multi-constraint prompts with rubric-based grading — probing how reliably models honor demanding, real-world instructions. |
| **Tri-Agent Framework / Tri-Agent Evaluation** | Zhao 2025 (KDD '25) — evaluates an LLM's **question-clarification** ability (do you ask before acting on an ambiguous query?) via three LLM agents: **QCA** (Question Clarifying Agent — the system under test, spots ambiguity and asks), **RA** (Respondent Agent — simulates a user, can inject irrelevant or ambiguous replies to stress-test), and **EA** (Evaluator Agent — LLM-as-a-judge scoring ambiguity handling, question relevance/timing, dialogue coherence, and final-intent alignment; validated against human judgments). The EA is a *soft critic* in LLM-Modulo terms. |

## Agentic & coding benchmarks

| Term | Definition |
|---|---|
| **SWE-Bench** | The canonical "can an agent fix a real bug" benchmark ([github.com/swe-bench/SWE-bench](https://github.com/swe-bench/SWE-bench)): given a repo and a GitHub issue, the agent must produce a patch that passes hidden `FAIL_TO_PASS` + `PASS_TO_PASS` tests. 2,294 task instances mined from 12 Python repos; **SWE-bench Verified** is the human-curated 500-task gold subset ([OpenAI](https://openai.com/index/introducing-swe-bench-verified/); 68.3% of raw tasks dropped for invalid harnesses or vague specs). The hidden test suite is a *sound* **hard critic** (LLM-Modulo terms) — which is exactly why SWE-Bench results are trusted where oracle-less benchmarks aren't (cf. **AI agent benchmarks are broken**). *(The `todo.md` entry "Sweep Bench" = SWE-Bench.)* |
| **Terminal-Bench / Terminal-Bench 2.0** | The command-line analogue to SWE-Bench ([tbench.ai](https://www.tbench.ai/)): each task is a unique terminal environment with a human-written solution and verification tests — assemble proteins for synthesis, debug async code, resolve a CVE. **2.0** is a curated hard set of 89 tasks run through **Harbor**, the official harness (`harbor run -d terminal-bench@2.0`; [github.com/harbor-framework/terminal-bench-2](https://github.com/harbor-framework/terminal-bench-2)); frontier agents score < 65%. Per-task real environments + hidden tests make it an **ABC**-grade benchmark — sound critics, not vibes. |

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
| **Harness engineering** | The discipline of building the *non-weight* scaffolding that turns a raw LLM into a reliable system — tool access, context/memory construction, control flow, verification/critics, recovery — as opposed to **prompt engineering** (wording one input) or training (changing weights). The whole harebrain bet is a harness-engineering claim: **the cage** is a harness pushed to its rigorous extreme (typed, statechart, sound guarantees). *Dynamic workflows* (Claude writing its own JS orchestration harness per task — see `docs/research-summaries/dynamic-workflows/`) are the soft, runtime-authored end of the same spectrum. |

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

## LangChain ecosystem

| Term | Definition |
|---|---|
| **LangChain** | The **Agent layer** of the four-layer stack (*capability*). A framework of composable abstractions for LLM apps — model wrappers, prompt templates, tools, memory, and the tool-calling / ReAct agent loop. Owns *what the model can do*: hands it tools and a reason-act loop. The framework behind experiment **cell F** (trusted-narrator agent). |
| **LangGraph** | The **Orchestration layer** (*structure*), from the LangChain team and built atop it. Models an agent as a directed graph: nodes (steps) and edges (transitions) over a shared state object, with conditional routing functions and a `recursion_limit` loop cap. The runtime enforces topology but delegates routing *decisions* to LLM-driven functions — see **Scaffolding leak / graph leak / chart leak**. The framework behind **cell E**. |
| **LangSmith** | Observability and evaluation platform for LangChain/LangGraph apps — run tracing, logging, dataset-based evals, prompt management. *Ecosystem term, not currently used in this repo*: its role here is filled by the **Ledger (JSONL)** (the repo's own append-only telemetry source of truth) plus judge validation. Listed for completeness. |
| **Langflow** | A visual, low-code node editor for building LangChain-style flows (drag-and-drop pipelines exported as runnable graphs). *Ecosystem term, not used in this repo* — no role in the cage or experiment matrix. Listed for completeness. |

## Third-party agent & automation platforms

| Term | Definition |
|---|---|
| **Otera** | An enterprise platform ([otera.ai](https://www.otera.ai/), tagline *"beyond augmentation, into autonomy"*) for turning regulated, document-heavy processes (insurance claims/underwriting, banking KYC/loans, shared-services AP/O2C) into end-to-end **autonomous** operations. A *multi-agent reasoning* architecture (80%+ straight-through processing) wrapped in governance: field-level confidence scoring, full audit trails, vision/OCR for messy docs, private-cloud deployment. *Ecosystem term, not used in this repo* — but a real-world echo of the harebrain bet: autonomy made safe by a cage (confidence scoring ≈ **working-memory facts**, audit trail ≈ the **Ledger (JSONL)**). The autonomous/high-stakes end of the platform spectrum, opposite static **Zapier**/**n8n**. |
| **Zapier** | A hosted no-code automation / iPaaS that connects SaaS apps via trigger→action "Zaps" across thousands of integrations (with bolted-on AI actions). Mostly *linear, human-authored* trigger-action flows — orchestration with little or no LLM judgment driving control flow. *Ecosystem term, not used in this repo*; the static, slow-clock end of the **harness engineering** spectrum (contrast Claude *dynamic workflows*). Listed for comparison. |
| **n8n** | An open-source, self-hostable workflow-automation tool — node-based visual editor (fair-code licensed), more developer-oriented than **Zapier** (code nodes, branching, self-host), with LangChain-backed AI/agent nodes. Same static, human-authored orchestration category. *Ecosystem term, not used in this repo*; listed for comparison as another point on the **harness engineering** spectrum. |
| **SwarmForge** | Robert C. Martin's ("Uncle Bob") agent-orchestration platform ([unclebob/swarm-forge](https://github.com/unclebob/swarm-forge), 100% Shell) — *"a disciplined tmux-based agent orchestration platform that turns swarms of AI agents into reliable, professional software engineers."* Coordinates multiple coding agents working in parallel on one project: config-driven swarm topology, an isolated **git worktree + tmux session per agent role**, role prompts layered over "constitution" files, multi-backend (Claude/Codex/Copilot/Grok), one terminal per agent (observable), agent-to-agent comms, project-local state in `.swarmforge/`. *Ecosystem term, not used in this repo*; the self-hosted, vendor-neutral cousin of **Claude (dynamic) workflows** (multi-agent + worktree isolation), where the "constitution" files play the role-defining part of the cage. |

## Agent-harness research

Each term below is distilled in `docs/research-summaries/` — see the [README series table](README.md).

| Term | Definition |
|---|---|
| **NLAH (Natural-Language Agent Harnesses)** | Pan et al. 2026 (arXiv:2603.25723). The agent harness written as an editable **natural-language document** interpreted at runtime by an **IHR** (Intelligent Harness Runtime), rather than baked into code or a fixed prompt — comparable task outcomes with far shorter, legible policies. The **MPL** bet reached from the agent-scaffold side: a declarative cage + an interpreting runtime, the model confined to leaves. The medium is the trade — NLAH's prose is cheap to author but offers no determinism or static analysis, where MPL's formal **Manifest** is provably bounded but harder to write. Summary: `docs/research-summaries/nlah/`. See **Harness engineering**. |
| **OS-Symphony** | Yang et al. 2026 (arXiv:2601.07779). A computer-using-agent framework that makes an off-the-shelf VLM state-of-the-art on **OSWorld** (65.84%) purely through structure: an orchestrator + tool agents plus a **Reflection-Memory Agent** whose milestone-driven long-term memory enables trajectory-level self-correction. The harebrain **cage** instantiated for the desktop; the binary milestone marker is a *retain-gate decay policy* over expensive facts (screenshots) — i.e. **working-memory facts** for a CUA. Every critic is soft (LLM judgment), so it's the director-without-a-sound-checker shape. Summary: `docs/research-summaries/os-symphony/`. |

## Agent dev tooling (CLIs & MCP)

| Term | Definition |
|---|---|
| **Amazon Bedrock AgentCore** | AWS's services for deploying and operating agents at scale — Runtime, Memory, Gateway, Identity, Code Interpreter, Observability. The **AgentCore CLI** (`@aws/agentcore`, [github.com/aws/agentcore-cli](https://github.com/aws/agentcore-cli)) scaffolds an agent project, deploys it to AgentCore Runtime, and invokes it; you write the loop in a framework you already use (Strands, LangChain/LangGraph, Google ADK, OpenAI Agents) and AWS hosts it. The older Python [`bedrock-agentcore-starter-toolkit`](https://github.com/aws/bedrock-agentcore-starter-toolkit) CLI is now legacy. *Ecosystem term, not used in this repo* — the cloud deployment plane for a cage authored elsewhere; AWS's answer to **Claude Managed Agents**. |
| **Google ADK / `adk` CLI** | Google's **Agent Development Kit** ([google.github.io/adk-docs](https://google.github.io/adk-docs/)) — a model-agnostic, deployment-independent agent framework, optimized for Gemini/Vertex AI. The `adk` CLI covers the full loop: `adk create` (scaffold), `adk run` (interactive), `adk web` (dev chat UI), `adk eval`, and `adk deploy` (one command to Vertex AI **Agent Engine**). The Google-stack peer of **LangChain** / Bedrock AgentCore / the **Claude Agent SDK**. *Ecosystem term, not used in this repo.* |
| **Playwright MCP** | Microsoft's official MCP server ([github.com/microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp), `npx @playwright/mcp`) giving an LLM browser automation via Playwright. Operates on the page's **accessibility tree** — structured text, ~200–400 tokens per snapshot — not pixels/screenshots, so no vision model is needed and control is deterministic; 40+ tools (navigate, forms, network mocking, storage, tracing). A concrete **seam** for web tasks: typed browser actions an agent/chart calls and routes on — the deterministic alternative to pixel-based computer use. *Ecosystem term, not used in this repo.* |

## Anthropic agent products

| Term | Definition |
|---|---|
| **Claude Code** | Anthropic's agentic coding tool — a terminal CLI (also desktop, web, and IDE extensions) where Claude reads/edits files, runs commands, and drives multi-step software tasks. The "default harness" the dynamic-workflows article builds on; the host environment for this repo's tooling. |
| **Claude (dynamic) workflows** | The Claude Code feature where Claude writes its *own* JavaScript orchestration harness per task — spawning and coordinating subagents (`agent()` / `parallel()` / `pipeline()`) with deterministic control flow and schema-validated returns. The soft, runtime-authored end of the **harness engineering** spectrum; near chart-strength orchestration (subagents can't touch control flow — see **Scaffolding leak / graph leak / chart leak**). Walkthrough archived at `docs/research-summaries/dynamic-workflows/`. |
| **Claude Managed Agents** | Anthropic's *hosted* agent runtime (beta; `managed-agents-2026-04-01` header) — a fully managed harness + infrastructure for running Claude autonomously: built-in tools (file, shell, web, code execution), stateful long-running resumable sessions with server-side history/sandbox, plus built-in prompt caching and compaction. You supply the goal; Anthropic runs the loop and plumbing. The managed counterpart to the self-hosted **Claude Agent SDK**. |
| **Claude Cowork** | Anthropic's agentic system for *non-developer* knowledge work — a desktop app that connects to local files and apps and completes multi-step tasks end-to-end (research synthesis, document prep, file management). Pitched as "Claude Code power for knowledge work"; GA on paid plans. |
| **Claude Agent SDK** | Anthropic's SDK for building custom agents on the *same harness that powers Claude Code* — the agent loop, tool use (file/bash/web), MCP, subagents, hooks, and context management, exposed as a library you embed in your own app. Available for **TypeScript** (`@anthropic-ai/claude-agent-sdk`) and **Python** (`claude-agent-sdk`); renamed from the *Claude Code SDK* in 2025 to signal it's for general agents, not just coding ([docs](https://platform.claude.com/docs/en/api/agent-sdk)). The self-hosted, build-your-own counterpart to **Claude Managed Agents** (Anthropic runs the loop): with the SDK *you* run the loop and own the environment. The vendor peer of **Google ADK** and **Amazon Bedrock AgentCore**. |

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
| **Scaffolding leak / graph leak / chart leak** | The brain doing something the structure didn't sanction. The naïve picture — agent "escapes" the graph/chart into undefined behavior — rarely holds literally: most runtimes hard-guard topology (you can't route to an undefined node or fall out; LangGraph also caps loops via `recursion_limit`). So a real leak is usually a **legal-but-wrong transition** (the LLM picks a permitted-but-incorrect branch; the structure faithfully executes a bad-but-allowed step) **or unconstrained leaf behavior** (a node/leaf is itself a free agent the scaffold doesn't bound *within*), **not** a true containment escape. **Strength differs by layer** — i.e. how much *judgment* is delegated at the seam, and how bounded each leaf is: *chart leak* (MPLv2, cell D) impossible by construction — the chart owns *where*, the LLM only returns a typed seam verdict, so a genuine one is an embedding bug not an agent choice; *Claude dynamic workflow* near chart-strength — deterministic JS owns control flow, agents can't touch it and return schema-validated values (residual surface: intra-agent behavior, or a branch authored on *unvalidated* free-text output); *graph leak* (LangGraph, cells E/F, *trusted-narrator*) — runtime enforces topology but routing functions **delegate the decision** to the LLM, so the leak is the legal-but-wrong choice plus free node internals; bare agent (cell G) — no cage, total surface. True *escape* only occurs in a hand-rolled scaffold that routes on raw LLM text with no validation. Leak surface grows with **Tier 1–5** latitude. Detected via the LangGraph harness's per-turn `actor_node` tagging. *Compare* **Divergence event**: a leak is an illegal/wrong *action*; divergence is a *claimed* state that doesn't match the ledger — either can happen without the other. |
| **Agentic Benchmark Checklist (ABC)** | The checklist introduced in "Establishing Best Practices for Building Rigorous Agentic Benchmarks" (Zhu et al. 2025) — the quality bar the benchmark-runner must meet: per-seed solvability, oracle solver, statistical significance, baseline reporting, judge validation. Applied to CVE-Bench, ABC cut performance overestimation by 33%. |

## Learning & cognition (cross-cutting concepts)

| Term | Definition |
|---|---|
| **Hebbian learning** | "Neurons that fire together, wire together" (Hebb, 1949). A *local*, correlational rule: a synapse strengthens when its pre- and post-synaptic neurons activate together — no global error signal, no labels. The unsupervised counterpoint to backprop, and the reason the **credit assignment problem** is hard: local rules can't easily attribute a distant outcome to an early weight. |
| **Clever Hans** | The horse that "did arithmetic" by reading unconscious cues from its handler rather than computing. In ML: a model that gets the right answer *for the wrong reason* — exploiting spurious correlations or dataset artifacts instead of the intended capability. The **obfuscation gap** is a Clever Hans detector: rename the tokens, and retrieval-not-reasoning collapses. |
| **Homunculus fallacy** | "Explaining" a capability by positing a little intelligent agent *inside* that already has that capability — an infinite regress that explains nothing, just relocates the mystery. The trap when crediting **the brain** with "understanding" or "planning": the word does work the mechanism hasn't earned. LLM-Modulo's insistence on *sound external verifiers* is partly a refusal of this fallacy. |
| **Credit assignment problem** | Deciding which decisions deserve credit (or blame) for an eventual outcome — *temporal* (which earlier action mattered, under delayed/sparse reward) and *structural* (which component or weight). The core difficulty of long-horizon agency, and a thing **the cage** attacks structurally: hierarchical decomposition and per-state guards localize blame to a state rather than smearing it across a 50-turn transcript. |
