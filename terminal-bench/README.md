# Running Terminal-Bench locally

Working notes for running [Terminal-Bench](https://www.tbench.ai) on this machine, plus
the mechanics of pointing it at a **custom agent** (see [`custom-agents.md`](custom-agents.md)).

Terminal-Bench is the benchmark distilled in
[`docs/research-summaries/terminal-bench/`](../docs/research-summaries/terminal-bench/terminal-bench.md).
This directory is the *operational* counterpart to that summary: how to actually run the thing.

> **TL;DR.** The `tb` orchestrator assumes a **POSIX host**, so native Windows can't run a trial to
> completion (it builds Linux-container paths with `\`). The working setup is **WSL2 + Ubuntu**, with
> Docker Desktop's WSL integration on. That's verified here: `oracle` resolves `hello-world` at 100%.
> The "why" is in [§ Why WSL (the native-Windows wall)](#why-wsl-the-native-windows-wall).

---

## What you get, and from where

There are two related distributions, and they are *not* the same task set:

| Channel | Tool | Dataset slug | Contents |
|---|---|---|---|
| `tb` registry | `terminal-bench` (pip/uv) | `terminal-bench-core==0.1.1` / `==head` | the original ~80–90 launch tasks + many *adapter* datasets (SWE-bench, AppWorld, MLEBench, …) |
| **Harbor** registry | `harbor` | `terminal-bench@2.0` | the **89 hard tasks from the paper** (the "2.0" set) |

The `tb` CLI's default registry serves `terminal-bench-core` and adapters; it does **not**
serve the paper's 89-task `terminal-bench@2.0` set. That comes through Harbor
(`harbor run -d terminal-bench@2.0`). For day-to-day local iteration on a custom agent,
`terminal-bench-core` is the right target — smaller, free, same task format and harness.
Use `==0.1.1` (pinned), **not** `==head` (its branch has no `tasks/`).

## Prerequisites

- **Docker Desktop**, WSL2-backed, with **WSL integration enabled for your Linux distro**
  (Settings → Resources → WSL Integration). Verify with `docker version` *inside* the distro.
- **A real WSL2 distro** (e.g. Ubuntu) — the minimal `docker-desktop` utility distro is not enough
  (no login shell). `wsl --install -d Ubuntu`.
- **uv** + **git** inside the distro.
- An **API key** for whatever model your agent drives, exported in the WSL shell. On this machine
  only `GEMINI_API_KEY` exists, so examples use `gemini/gemini-2.5-flash` (litellm prefix `gemini/`
  reads `GEMINI_API_KEY`). **Env vars do not cross the Windows↔WSL boundary — re-export in WSL.**

## Setup (WSL2 Ubuntu)

```bash
# one-time distro (from Windows): wsl --install -d Ubuntu
# then, inside Ubuntu:
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv tool install --python 3.13 terminal-bench       # PIN 3.13 — see gotcha
tb --help
```

> **Gotcha — pin Python 3.13.** uv otherwise defaults `terminal-bench` onto **Python 3.14**, where it
> crashes at startup: `TypeError: 'function' object is not subscriptable` evaluating `list[str] | None`
> parameter annotations (a 3.14 annotation-machinery incompatibility in the typer-based CLI). Pin with
> `--python 3.13` (uv fetches it); to repair an existing install,
> `uv tool install --python 3.13 --force terminal-bench`.

**You don't have to re-clone the repo into WSL.** The Windows checkout is visible at
`/mnt/c/Users/PhilVanEvery/Git/github/pmvanev/harebrain` and `tb` runs fine against it as a Linux
process. Re-cloning to ext4 (`~/…`) is a *speed* optimization only. Either way, write **run outputs**
(`--output-path`) and **task datasets** to the WSL fs (`~/…`), not `/mnt/c` — Docker IO over `/mnt/c`
is slow, and the one host-side bind mount tasks use (`T_BENCH_TASK_LOGS_PATH` → task `/logs`) is
happier on ext4. Reading task *definitions* over `/mnt/c` is fine (they're copied into containers via
the Docker API, not bind-mounted).

You can drive all of this from a Windows PowerShell prompt without opening a WSL shell:
`wsl -d Ubuntu -e bash -lc '<command>'` (add `-u root` to run as root).

## The model + agent matrix

`tb run` selects an agent and a model independently:

- `--agent` (built-ins): `oracle`, `naive`, `terminus`/`terminus-1`, `terminus-2`, `mcp-terminus`,
  `claude-code`, `aider`, `codex`, `goose`, `goose-mcp`, `gemini-cli`, `grok-cli`, `openhands`,
  `mini-swe-agent`, `opencode`, `qwen-coder`, `cursor-cli`, `nop`.
- `--agent-import-path module:Class` — a **custom** agent (overrides `--agent`). See
  [`custom-agents.md`](custom-agents.md).
- `--model provider/model_name` — litellm-style (`anthropic/…`, `openai/…`, `gemini/…`,
  `together_ai/…`).
- `--agent-kwarg k=v` (repeatable) — extra constructor kwargs for the agent.

Two built-ins are special and cost **no API tokens**:

- **`oracle`** — runs the task's reference solution. Smoke-tests that Docker + the harness work
  end-to-end; should always resolve.
- **`nop`** — does nothing; should always *fail*. Confirms a task isn't trivially passable.

## Running it (the canonical commands)

On Linux the registry auto-download works, so no manual clone is needed:

```bash
# zero-cost harness smoke test (reference solution; resolves at 100%)
tb run -d terminal-bench-core==0.1.1 -t hello-world --agent oracle --n-concurrent 1 --output-path ~/tb-runs

# real agent run (spends API tokens; needs the model's key exported)
export GEMINI_API_KEY=...
tb run -d terminal-bench-core==0.1.1 -t hello-world --agent terminus-2 -m gemini/gemini-2.5-flash --output-path ~/tb-runs
```

Useful flags: `-t/--task-id` (glob, repeatable), `--n-tasks N`, `-e/--exclude-task-id`,
`--n-concurrent` (default 4), `--n-attempts` (default 1, for pass@k), `--livestream`,
`--no-rebuild` (skip Docker rebuild on re-runs), `--output-path` (default `runs/`).

Results land in `<output-path>/<timestamp>/results.json` (`is_resolved`, `failure_mode`, token
counts, recording path per trial).

## Running the paper's 89-task 2.0 set (Harbor)

Per the paper, the hard set is distributed via Harbor:

```
harbor run -d terminal-bench@2.0
```

Harbor is the laude-institute harness/runner the `tb` tasks are also built on; configs from the
paper's experiments are at
[github.com/laude-institute/terminal-bench-experiments](https://github.com/laude-institute/terminal-bench-experiments).
Same POSIX-host caveat — run it from WSL2/Linux.

---

## Why WSL (the native-Windows wall)

The CLI installs and the dataset clones on Windows, but **the harness can't finish a trial there.**
Two confirmed root causes, both "the code assumes it's on Linux":

1. **Dataset auto-download is POSIX-only.**
   `terminal_bench/registry/client.py::download_dataset` `git clone`s the dataset, then runs
   `subprocess.run(["rm", "-rf", ".git"], check=True)` (`rm` isn't a Windows command), and copies from
   `temp/<dataset_path>`. Separately, `terminal-bench-core==head` points at the repo's `main` branch
   with `dataset_path=./tasks`, but the tasks live on the `dataset/terminal-bench-core/v0.1.x` branch,
   so the copy source doesn't exist.
   *(If you must poke at it on Windows, clone that branch yourself and use `--dataset-path`; on Linux
   the auto-download just works.)*

2. **Container file-copy uses the host path separator.**
   `terminal_bench/terminal/docker_compose_manager.py::copy_to_container` calls
   `container.put_archive(container_dir, …)` where `container_dir` becomes `\tmp` on Windows instead
   of `/tmp`; Docker (the container is Linux) returns `404 … Could not find the file \tmp in container`.
   No flag-level workaround, and this is unlikely to be the only POSIX assumption (tmux/asciinema
   paths, etc.).

Both vanish when the orchestrator runs as a **Linux process** — i.e. in WSL2. We chose WSL over
Docker-in-Docker (DinD: privileged, nested, no shared build cache) because on Windows, Docker
Desktop's WSL integration transparently resolves the task containers' host-side log bind mount;
plain Docker-out-of-Docker would force you to fight Desktop bind-mount path translation.

> **Why not just patch the package?** Monkey-patching the two functions would be reintroduced on every
> upgrade, and there are likely more POSIX assumptions downstream. WSL2 is the supported, lower-
> maintenance path.

Also note: `tb`'s rich ✓/✗ table output crashes under the Windows console's cp1252 codec — harmless
in a Linux terminal, so `PYTHONUTF8` is unnecessary in WSL (on Windows you'd set
`$env:PYTHONUTF8="1"`).

## Status on this machine

| Step | State |
|---|---|
| Docker / uv / git present | ✓ |
| WSL2 Ubuntu installed + set default; Docker Desktop integration on | ✓ (`docker version` → server 29.4.0 in Ubuntu) |
| `tb` installed in Ubuntu (0.2.18, **pinned Python 3.13**) | ✓ |
| `oracle` resolves `hello-world` — **WSL2 Ubuntu** | ✓ **100% accuracy** (2026-06-11) |
| `oracle` resolves `hello-world` — native Windows | ✗ — `\tmp` copy bug (POSIX assumption) |
| Real built-in agent run | ✓ `terminus-2` × `gemini/gemini-2.5-flash` resolved `hello-world` (2026-06-11), 1831 in / 362 out tokens |
| Custom **Python** agent (`command-loop`, `agents/command_loop.py`) | ✓ resolved `hello-world` via `--agent-import-path` + `PYTHONPATH` (2026-06-11), Gemini Flash, 88 / 27 tokens |
| Custom **MPL** agent (`mpl-terminal`, `agents/terminal.mpl` + `agents/mpl_agent.py`) | ✓ resolved `hello-world` (2026-06-12), Gemini Flash, 263 / 43 tokens — MPL chart owns the perceive→think→act loop, LLM only at the `decide` leaf |

## Cost note

The paper reports **$1–$100 per full run** depending on model, with some single tasks making hundreds
of API calls / ~100M tokens. Always iterate with `oracle`/`nop` (free) and a single `-t <task>` on a
cheap model before any full-set sweep.

## Files here

- `README.md` — this file.
- `custom-agents.md` — running Terminal-Bench against a custom Python agent and a custom MPL agent.
- `agents/command_loop.py` — the worked custom **Python** agent from `custom-agents.md`; verified
  resolving `hello-world`. Run with `PYTHONPATH=…/terminal-bench/agents tb run
  --agent-import-path command_loop:CommandLoopAgent …`.
- `agents/mpl_agent.py` + `agents/terminal.mpl` — the custom **MPL cage** agent (chart owns the loop;
  LLM at the `decide` leaf); verified resolving `hello-world`. Needs `mpl` in tb's venv (see
  `custom-agents.md` § Environment).
- `agents/_chart_dryrun.py` — runs `terminal.mpl` with stub host fns (no Docker/LLM) to validate
  chart edits fast.
- `_probe_registry.py` — tiny helper that prints a dataset's clone URL/branch/path from the `tb`
  registry (how the Windows local-clone workaround was derived). Run with the tool venv's Python.
- `_datasets/`, `runs/` — gitignored (cloned tasks, run outputs).
