![Harness-comparison glyph: one fixed brain disc feeds three different cages — an engineered loop, a minimal while-loop, and an MPL state chart — into the Terminal-Bench ruler that grades each on resolve rate](images/glyph.svg)

# Swap the cage, fix the brain, *staged*

*A harness comparison on Terminal-Bench: hold the model fixed at `gemini/gemini-2.5-flash` and swap the harness across three agents, reading resolve rate on a task slice. This is the "harness lever at a fixed brain" — the same lever [Meta-Harness](../../docs/research-summaries/meta-harness/meta-harness.md) quantified at 6× and [agent-harness-anatomy](../../docs/research-summaries/agent-harness-anatomy/agent-harness-anatomy.md) showed as Top 30 → Top 5, both on this ruler. The [Terminal-Bench summary](../../docs/research-summaries/terminal-bench/terminal-bench.md) located that lever in its regime: capability sets the ceiling, the harness decides reach. Here we try to enter that regime locally — and find the gate is API capacity, not the right model.*

---

## The three harnesses

The experiment is a controlled swap. One brain, three cages, one ruler. Each cage is driven by the same `-m gemini/gemini-2.5-flash`; the only thing that changes is who owns control flow.

![Three harnesses driven by one fixed Gemini Flash brain: terminus-2 the engineered baseline loop, command-loop the minimal while-loop, and mpl-terminal the MPL state chart — each wraps the same model and is graded on the same task slice](images/fig-01-harnesses.svg)
*The same model at the leaf; three different geometries around it. terminus-2 is Terminal-Bench's neutral baseline, command-loop is the minimal worked example, mpl-terminal is the harebrain cage.*

| | **terminus-2** | **command-loop** | **mpl-terminal** |
|---|---|---|---|
| **What it is** | Terminal-Bench **built-in** neutral agent — the engineered baseline | our minimal **custom** Python agent | the harebrain **MPL cage** |
| **File** | tb built-in (no repo file) | [`agents/command_loop.py`](../agents/command_loop.py) | [`agents/mpl_agent.py`](../agents/mpl_agent.py) + [`agents/terminal.mpl`](../agents/terminal.mpl) |
| **Control flow** | engineered perceive/think/act loop: structured analysis+plan+commands response, per-keystroke timing, episode budget | a thin `while` loop: one structured LLM call per step → `{commands, done}`, send each via `send_keys`, stop on `done` or `max_steps` | the **chart owns control flow** as explicit states `Perceive → Think → Act → Done`; a 3-tick pipeline, one side-effecting host call per transition |
| **Where the LLM is consulted** | inside the loop, per turn | once per step (returns a command list) | **only at the `decide` leaf** — `observe`/`act` are pure host calls |
| **Step budget** | episode budget | `max_steps` default 15 (we ran 20) | chart var `max_steps := 12` |
| **Retry / fault tolerance** | **tenacity RETRIES** on provider/LLM errors | catches only JSON-parse errors; a provider error **crashes it** (no retry) | a host-import exception is logged per-rule and the sim **keeps ticking** — but needs a stop-on-repeated-failure guard |
| **hello-world tokens** | 1831 in / 362 out | 88 in / 27 out | 263 in / 43 out |

> **The one axis that survived.** Retry behavior is itself harness work. terminus-2 wraps its LLM calls in tenacity and retries on provider errors; our two minimal agents do not. The MPL cage is structurally fault-tolerant — a host error is caught per-rule and the chart ticks on — but that property is double-edged without a guard that halts on repeated failure. "Handle provider errors" is a harness feature, not a model feature.

## The fixed brain

The model is held constant so any resolve-rate delta is attributable to the cage, not the brain.

![The fixed brain: gemini/gemini-2.5-flash reached through litellm, the gemini/ provider prefix reading GEMINI_API_KEY, held identical across all three harnesses so the harness is the only variable](images/fig-02-model.svg)
*One brain, called through litellm. The `gemini/` provider prefix reads `GEMINI_API_KEY`. Holding it identical across all three cages is what isolates the harness lever.*

The brain is `gemini/gemini-2.5-flash`, called through **litellm** — the `gemini/` provider prefix reads `GEMINI_API_KEY` from the environment. By pinning the model, the experiment turns the harness into the only independent variable: if one cage resolves a task another cannot, the difference is the geometry, not the intelligence.

> **Reality check.** On the **free Gemini tier** this key hit rate and quota limits — HTTP 429 `RateLimitError`, then eventually daily-quota exhaustion. That, not the cage design, became the dominant obstacle to a clean local run. More below.

## The task slice

The slice is drawn from `terminal-bench-core==0.1.1`, all **easy** difficulty, all self-contained (no network).

![The task slice: four easy, self-contained terminal-bench-core tasks — hello-world the control, extract-safely security, fix-permissions sysadmin, csv-to-parquet data-science — plus grid-pattern-transform dropped for being reasoning-hard and timing out](images/fig-03-task-slice.svg)
*Four easy, network-free tasks plus one dropped. grid-pattern-transform was reasoning-hard for Flash, burned the most LLM calls, and timed out at 600s — excluded from the slice.*

| Task | Category | What it asks |
|---|---|---|
| **hello-world** | control | create `hello.txt` containing `Hello, world!` + newline (~1 step). Expected: all harnesses pass. |
| **extract-safely** | security | extract `archive.tar` to `/app/solution.txt`; multi-step. Earlier **both** terminus-2 and command-loop failed its `test_solution_found`. |
| **fix-permissions** | sysadmin | a `process_data.sh` won't run — diagnose and fix it (perceive → diagnose → act). The one task that resolved in the rate-limited sweep. |
| **csv-to-parquet** | data-science | convert `/app/data.csv` → `/app/data.parquet` (needs pandas / pyarrow). |
| ~~grid-pattern-transform~~ | *dropped* | reasoning-hard for Flash, most LLM calls of any task, **timed out at 600s** — excluded from the slice. |

## How we run it

Terminal-Bench's orchestrator cannot run natively on Windows — it assumes a POSIX host (it builds container paths with backslashes, so files land in `\tmp` not `/tmp`, and it shells out to `rm`). So it runs as a **Linux process inside WSL2 Ubuntu**, talking to a WSL2-backed Docker Desktop.

![How we run it: a Windows 11 host forwards GEMINI_API_KEY via WSLENV into WSL2 Ubuntu, where the tb orchestrator (a uv tool pinned to Python 3.13) talks to a WSL2-backed Docker Desktop and spins up one Linux container per task trial, grading on final container state](images/fig-04-wsl-architecture.svg)
*The tb orchestrator runs as a Linux process in WSL2 because it assumes a POSIX host. Docker Desktop is WSL2-backed with Ubuntu integration; tb spins up one container per task trial via docker-compose and grades on the final container state.*

The stack, concretely:

- **Windows 11 host.** The orchestrator runs inside **WSL2 Ubuntu** (the default distro) because it is a POSIX-only tool.
- **Docker Desktop**, WSL2-backed with integration enabled for Ubuntu. tb talks to the Docker daemon and spins up **one Linux container per task trial** via docker-compose. Each container gets the instruction + Dockerfile; the tests and human oracle are hidden; grading reads the **final container state**.
- **tb is a uv tool pinned to Python 3.13** (3.14 crashes its typer CLI). For the MPL agent, `mpl` is installed into the tb venv (`uv tool install --with <mplv2 path>`).
- The repo is reachable from WSL at `/mnt/c/Users/PhilVanEvery/Git/github/pmvanev/harebrain`. Run outputs go to the WSL ext4 fs (`~/tb-runs`), **not** `/mnt/c` — Docker IO over `/mnt/c` is slow.
- `GEMINI_API_KEY` is forwarded from the Windows process env into WSL via **WSLENV** at run time (never printed). Custom agents load with `PYTHONPATH=.../terminal-bench/agents` + `--agent-import-path module:Class`.

The exact commands, driven from a Windows PowerShell prompt. WSL commands are double-quoted with absolute paths because single-quoted `$`-vars and pipes get mangled in the PS → WSL handoff:

```powershell
# Forward the key into WSL (never printed)
PS> $env:WSLENV="GEMINI_API_KEY"

# 1. terminus-2 — the built-in neutral baseline
PS> wsl -d Ubuntu -u root -e bash -lc "export PATH=$HOME/.local/bin:$PATH; tb run -d terminal-bench-core==0.1.1 -t hello-world -t extract-safely -t fix-permissions -t csv-to-parquet -a terminus-2 -m gemini/gemini-2.5-flash --n-concurrent 1 --output-path ~/tb-runs/exp1/terminus2"

# 2. command-loop — minimal custom agent (add PYTHONPATH; swap -a for --agent-import-path + -k)
PS> wsl -d Ubuntu -u root -e bash -lc "export PATH=$HOME/.local/bin:$PATH; export PYTHONPATH=/mnt/c/Users/PhilVanEvery/Git/github/pmvanev/harebrain/terminal-bench/agents; tb run -d terminal-bench-core==0.1.1 -t hello-world -t extract-safely -t fix-permissions -t csv-to-parquet --agent-import-path command_loop:CommandLoopAgent -k max_steps=20 -m gemini/gemini-2.5-flash --n-concurrent 1 --output-path ~/tb-runs/exp1/commandloop"

# 3. mpl-terminal — the harebrain MPL cage (same PYTHONPATH; different import path)
PS> wsl -d Ubuntu -u root -e bash -lc "export PATH=$HOME/.local/bin:$PATH; export PYTHONPATH=/mnt/c/Users/PhilVanEvery/Git/github/pmvanev/harebrain/terminal-bench/agents; tb run -d terminal-bench-core==0.1.1 -t hello-world -t extract-safely -t fix-permissions -t csv-to-parquet --agent-import-path mpl_agent:MplAgent -m gemini/gemini-2.5-flash --n-concurrent 1 --output-path ~/tb-runs/exp1/mpl"
```

> **Free zero-cost checks.** `-a oracle` runs the reference solution (should resolve); `-a nop` does nothing (should fail). Both are quota-free smoke tests of the harness plumbing before you spend a single LLM token.

## Results (honest)

Do not read this table as a measurement of the harness lever. It is mostly a measurement of the free Gemini tier's rate limiter.

| Run | Concurrency | Result | What actually happened |
|---|---|---|---|
| **Clean control** (each harness, individually, earlier) | 1 | hello-world **RESOLVED by all three** | terminus-2 1831/362 tok · command-loop 88/27 · mpl-terminal 263/43. At a fixed Flash brain, all three cages solve the trivial task. |
| **4-task sweep** | 2 | terminus-2 **25%** (1/4) · command-loop **25%** (1/4) | both resolved **only** fix-permissions. **Heavily contaminated**: most trials failed with `RateLimitError`, agents crashed mid-task (`unknown_agent_error` / `agent_timeout`). The mpl run **wedged** on rate-limit retries against a torn-down container and was **killed**. |
| **Retry** | 1 | **0/4** | by then the Gemini free-tier **daily quota was exhausted** — a single direct API call returned 429. |

Stated plainly:

- The **hello-world control passed for all three harnesses** when run individually, before quota exhaustion. That is the only clean signal in the table.
- The multi-task sweep was **rate-limit-dominated**. The 25% figures are an artifact of which trials happened to get a token through before the limiter tripped, not of cage quality. mpl wedged and was killed.
- The `--n-concurrent 1` retry hit **0/4** on an exhausted daily quota.
- **This does not measure the harness lever cleanly.** It cannot. The brain ran out of capacity before the cages could be compared.

## What we learned

The headline is a reproduction lesson, not a resolve-rate one: **entering the harness-lever regime is gated on API capacity, not just on picking the right model.**

- The [Terminal-Bench summary](../../docs/research-summaries/terminal-bench/terminal-bench.md)'s regime boundary holds — *capability sets the ceiling, the harness decides reach*. But the 6× regime (frontier model × hard tasks × many calls) costs **real quota to enter**, and the summary's **$1–100/run** cost note is exactly the bill we couldn't pay on a free tier. The cost of entry is itself part of the answer to "can I reproduce it locally?" — and the answer is *not on free Gemini*.
- The one real signal that survived the noise is a **harness-quality axis**, not a resolve-rate one: terminus-2 retries on provider errors (tenacity) while our two minimal agents crash; the MPL cage is fault-tolerant — it keeps ticking past host errors — but it needs a **stop-on-repeated-failure guard** to convert that resilience into useful behavior rather than spinning against a dead container. Handling provider errors is harness work, and it is the first thing the cage earns its keep on.
- Token and turn counts still don't tell the story the summary said they wouldn't: command-loop resolved hello-world at 88/27 tokens, terminus-2 at 1831/362. Twenty times the tokens, same control outcome. Structure over volume, as advertised.

## Paper-faithful next step

The experiment is ready to re-run faithfully the moment funded capacity is available. Same commands, same slice — only the `-m` flag changes:

- `-m openai/gpt-5.2` — the Terminal-Bench leaderboard **#1 model** (Codex CLI × GPT-5.2 at 63%). Key is set, **awaiting billing credit**.
- `-m anthropic/claude-opus-4-8` — the **Meta-Harness Opus family**, the brain behind the 6× harness gap.

Results will be slotted into the table above once a non-rate-limited brain is available. Until then, the honest finding stands: on the free Gemini tier the harness-lever comparison is **unmeasurable** — the limiter, not the cage, decides the run.
