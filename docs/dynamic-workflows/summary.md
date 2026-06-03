# Summary — "A harness for every task: dynamic workflows in Claude Code"

**Author:** Thariq Shihipar & Sid Bidasaria (Anthropic, Claude Code) · **Published:** 2026-06-02 · **Source:** [X Article](https://x.com/trq212/status/2061907337154367865)

## The one-line claim

Claude Code can now write its own **harness on the fly** — a custom JavaScript orchestration script (a *dynamic workflow*) that spawns and coordinates multiple subagents, each with its own context window, tailored to the task at hand. Saveable, shareable, resumable.

## Why they exist — the failure modes

The default harness plans *and* executes in one context window. Over long, parallel, or adversarial tasks that breaks down into three failure modes a workflow is designed to structurally prevent:

- **Agentic laziness** — declaring a multi-part job done after partial progress (20 of 50 items).
- **Self-preferential bias** — Claude favoring its own outputs when asked to judge them.
- **Goal drift** — original constraints lost across turns, especially after lossy compaction.

Separate Claudes with isolated, focused goals fight all three.

## Core mechanics

- A workflow is a **JavaScript file** with special agent-spawning/coordination functions, plus standard JS (JSON, Math, Array) for data processing.
- Workflows choose **which model** each agent runs and whether agents run in **isolated worktrees** — picking intelligence level and isolation per step.
- Workflows are **resumable** after interruption.
- Trigger by asking Claude to "make a workflow" or with the keyword **"ultracode."**

## The reusable patterns

| Pattern | What it does |
|---|---|
| **Classify-and-act** | Classifier agent routes to different behavior by task type (or classifies the final output). |
| **Fan-out-and-synthesize** | Split into many steps, run an agent each, then a **barrier** merges structured outputs. Avoids cross-contamination. |
| **Adversarial verification** | A separate agent verifies each spawned agent's output against a rubric. |
| **Generate-and-filter** | Generate many ideas, filter/verify/dedupe, return only the best. |
| **Tournament** | N agents compete with different approaches; pairwise judging until a winner (comparative judgment beats absolute scoring). |
| **Loop until done** | Spawn agents until a stop condition (no new findings / no errors), not a fixed count. |

## Use cases highlighted

Large refactors/migrations (e.g. a Zig→Rust rewrite), research (the `/deep-research` skill), fact-checking every claim, sorting/ranking 1000+ items via tournament, rule-checking (one verifier per rule + skeptic to cut false positives), debugging (disjoint-evidence hypotheses + refuter panels), triage (with a **quarantine** pattern: untrusted-content readers can't take high-privilege actions), taste-based exploration, lightweight evals, and model routing. Explicitly **not just for code** — sales, data engineering, post-mortems.

## Practical guidance

- **Not for every task** — workflows use significantly more tokens. Ask "does this really need more compute?" Most coding tasks don't need a 5-reviewer panel.
- **Quick workflows** exist too (e.g. a fast adversarial review of one assumption).
- **Pair with `/loop`** (run repeatedly) and **`/goal`** (hard completion requirement).
- **Token budgets**: prompt "use 10k tokens" to cap spend.
- **Save** with "s" in the workflow menu → `~/.claude/workflows`, or **share via a skill** (reference the JS files in `SKILL.md`; treat them as templates, not verbatim scripts).

## Takeaway

Dynamic workflows turn Claude Code from a single-context coder into a programmable multi-agent orchestrator. Best applied where structure, parallelism, or adversarial checking beats raw single-context reasoning — used deliberately, because the token cost is real and best practices are still emerging.
