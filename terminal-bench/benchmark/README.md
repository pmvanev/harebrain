# Toward an optimized MPL harness for Terminal-Bench 2.0

*This folder is where we design and harden a real MPL-cage harness aimed at the **89-task Terminal-Bench 2.0** set — graduating the teaching-demo cage in [`../agents/`](../agents/) into something that can actually compete, and (when submissions reopen) land on the [leaderboard](https://www.tbench.ai/leaderboard/terminal-bench/2.0).*

---

## The hope

Build **the ultimate MPL harness**: an MPL chart (the harebrain cage) engineered well enough to score on the **hard** TB-2 tasks — not just pass easy ones — then run it on `terminal-bench@2.0` via **Harbor** at submission spec and put a real number on the board.

This is the manual, hand-authored counterpart to what [Meta-Harness](../../docs/research-summaries/meta-harness/meta-harness.md) *automates*: we're pulling the harness lever by hand, deliberately, on the same ruler the paper used.

## Where we're starting — and why the demo isn't enough

[`../agents/mpl_agent.py`](../agents/mpl_agent.py) + [`../agents/terminal.mpl`](../agents/terminal.mpl) is a minimal `Perceive → Think → Act → Done` cage. It proved the harebrain hypothesis *runs on the ruler* ([`../simple-experiment/`](../simple-experiment/README.md)) — but it's a teaching demo: one command per step, a single `decide` leaf, no planning, no verification, no recovery. On the easy 4-task slice it swung 50–75–100% across cages and carried a one-line `done`-detection bug (now fixed). On the **hard** 89-task set it would land near the floor.

The bar is high and honest:

| | |
|---|---|
| TB-2 leaderboard top (mid-2026) | **~84–85%** (e.g. NexAU-AHE / LemonHarness / Capy / Codex CLI on GPT-5.5) |
| Frontier baseline on TB-2 | **< 65%** — the set is built to *not* be saturated |
| Our demo cage | would sit near the bottom — getting **listed ≠ ranking** |

So "ultimate" is the project, not a given. A thin cage will not compete; an engineered one might.

## What "optimized MPL harness" should mean (design charter)

The cage's job is to add the structure the model can't give itself. Each direction below becomes a **chart region/state or host-import**, and each is aimed at a specific TB-2 failure class (the paper's taxonomy: Execution / Coherence / Verification):

- **Plan → execute.** A `Planning` state that drafts a task plan onto the blackboard *before* acting, and is revisited on failure. (Attacks Coherence: task derailment, context loss.)
- **Verify before done.** A `Verify` state that checks progress against the instruction — run the task's own checks where present, inspect final state — before declaring complete. (Attacks Verification: premature/weak termination — the failure class that bit our demo.)
- **Recovery / bounded retry.** Turn MPL's structural fault-tolerance (it keeps ticking past a host error) into *real* behavior: bounded retries with backoff on provider/command errors, plus a **stop-on-repeated-failure** guard so it never spins against a dead container. (Attacks Execution + the rate-error class.)
- **Blackboard, not transcript.** Keep a compact working memory (plan, files touched, last error) instead of re-sending the whole screen each tick — the "diagnostic surface, uncompressed" idea, made cheap.
- **Tool grounding.** A guard that checks/installs a tool before use — the single largest TB-2 *command* failure is "command not found / not in PATH" (~24%).
- **Long-horizon shape.** Explicit states make multi-phase tasks legible and resumable, which is where the hard tasks live.

These map cleanly onto the harebrain primitives — chart topology, blackboard, guards, the sound critic — so the design is "draw the cage region that kills failure class X," not "tune a prompt."

## Two ways to get the chart

1. **Hand-author it** (what we do here): iterate the `.mpl` chart against a small set of *hard* tasks, RPP-style — add a region, re-run, measure, keep or cut.
2. **Search for it** (the horizon, out of scope for now): a Meta-Harness-style loop where a coding-agent proposer *evolves* the chart against a search set. The cage's deterministic-given-seed replay is a *cleaner* search target than arbitrary Python harnesses — noted for later, after we know what a good hand-authored chart looks like.

## The honest constraints

- **Cost.** A full submission run is **89 tasks × 5 trials = 445 trials** of a frontier reasoning model — hours and **tens-to-hundreds of dollars**. We iterate on a small hard-task subset with `-k 5` first; we do not run the full 445 until the harness earns it.
- **Variance.** N is small per task; the simple-experiment already showed a 75% → 50% swing on re-draw. Use `-k 5` (pass@k) and report error bars (the board does: ±~2%).
- **Submissions are CLOSED** until ~end of June 2026 (a new process is pending; PRs go to `harborframework/terminal-bench-2-leaderboard` with `metadata.yaml` + per-trial `result.json`, `timeout_multiplier = 1.0`, no overrides, no web access). We **design + dry-run now, submit later**.
- **Determinism.** TB-2 allows internet, so the *benchmark* isn't replayable; pin sampling at the `decide` leaf so the *cage* is.

## Status

- [ ] **Design the optimized chart** (here) — the regions above, as a new `terminal_v2.mpl` + a thin `mpl_agent_v2.py` host.
- [ ] **Dry-run on a hard TB-2 subset** via Harbor (`harbor run -d terminal-bench@2.0`, a handful of hard tasks, `-k 5`) — validate the score *and* that we produce valid submission artifacts.
- [ ] **Scale to 89 × 5** only once the harness is worth the spend.
- [ ] **Submit** when the leaderboard reopens.

## Planned layout

```
benchmark/
  README.md            # this charter
  terminal_v2.mpl      # the optimized cage (TODO)
  mpl_agent_v2.py      # thin host wiring the v2 chart's host-imports (TODO)
  tasks-hard.txt       # the hard-task dry-run subset (TODO)
  harbor/              # run configs for terminal-bench@2.0 (TODO)
  runs/                # gitignored
```

**See also:** [`../simple-experiment/`](../simple-experiment/README.md) (the lever, measured), [`../custom-agents.md`](../custom-agents.md) (the agent contract + the v1 cage), and the [Terminal-Bench](../../docs/research-summaries/terminal-bench/terminal-bench.md) / [Meta-Harness](../../docs/research-summaries/meta-harness/meta-harness.md) summaries (the ruler and the search the cage is graded against).
