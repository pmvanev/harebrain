# Running Terminal-Bench locally

Working notes for running [Terminal-Bench](https://www.tbench.ai) on this machine, plus
the mechanics of pointing it at a **custom agent** (see [`custom-agents.md`](custom-agents.md)).

Terminal-Bench is the benchmark distilled in
[`docs/research-summaries/terminal-bench/`](../docs/research-summaries/terminal-bench/terminal-bench.md).
This directory is the *operational* counterpart to that summary: how to actually run the thing.

> **TL;DR for this machine:** the `tb` CLI installs and runs fine on Windows, but the harness
> assumes a **POSIX host** and breaks when it copies files into the Linux task container
> (it builds container paths with `\` instead of `/`). Run it **inside a WSL2 Linux distro**
> instead. Details in [§ Windows reality check](#windows-reality-check).

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
`terminal-bench-core` is the right target — it's smaller, free to clone, and uses the same
task format and harness.

## Prerequisites

- **Docker** — every task runs in its own Linux container. (`docker version` → 29.4 here.)
- **uv** — for installing the CLI and for any project venv that holds a custom agent.
- **git** — the dataset cacher clones task repos.
- An **API key** for whatever model your agent drives, exported as an env var. On this machine
  only `GEMINI_API_KEY` is set, so examples below use `gemini/gemini-2.5-flash`
  (litellm provider prefix `gemini/` reads `GEMINI_API_KEY`).

## Install

```powershell
uv tool install terminal-bench        # provides `tb` and `terminal-bench`
tb --help
```

Installed here: **terminal-bench 0.2.18** (uv resolved it onto CPython 3.13 in its own tool venv —
note it does *not* use the system's Python 3.14).

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

- **`oracle`** — runs the task's reference solution. Use it to smoke-test that Docker + the harness
  work end-to-end; it should always resolve.
- **`nop`** — does nothing; should always *fail*. Useful to confirm a task isn't trivially passable.

## Running it (the canonical commands)

Force UTF-8 first — the `tb` rich-table output crashes under the Windows console's cp1252 codec
when it prints the ✓/✗ glyphs:

```powershell
$env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"
```

Because the registry auto-download is broken on Windows (see below), we point `tb` at a
**locally-cloned** task directory with `--dataset-path`:

```powershell
# one-time: clone the core task set (the dedicated dataset branch, not main)
git clone --depth 1 --branch dataset/terminal-bench-core/v0.1.x `
  https://github.com/laude-institute/terminal-bench `
  terminal-bench\_datasets\terminal-bench-core-0.1.x

$tasks = "$PWD\terminal-bench\_datasets\terminal-bench-core-0.1.x\tasks"

# zero-cost harness smoke test (reference solution; should resolve)
tb run --dataset-path $tasks -t hello-world --agent oracle --n-concurrent 1 --output-path terminal-bench\runs

# real agent run (spends API tokens)
tb run --dataset-path $tasks -t hello-world --agent terminus-2 -m gemini/gemini-2.5-flash --output-path terminal-bench\runs
```

Useful flags: `-t/--task-id` (glob, repeatable), `--n-tasks N`, `-e/--exclude-task-id`,
`--n-concurrent` (default 4), `--n-attempts` (default 1, for pass@k), `--livestream`,
`--no-rebuild` (skip Docker rebuild on re-runs), `--output-path` (default `runs/`).

Results land in `runs/<timestamp>/results.json` (`is_resolved`, `failure_mode`, token counts,
recording path per trial).

## Running the paper's 89-task 2.0 set (Harbor)

Per the paper, the hard set is distributed via Harbor:

```
harbor run -d terminal-bench@2.0
```

Harbor is the laude-institute harness/runner the `tb` tasks are also built on; configs from the
paper's experiments are at
[github.com/laude-institute/terminal-bench-experiments](https://github.com/laude-institute/terminal-bench-experiments).
Same POSIX-host caveat applies — run it from WSL2/Linux.

---

## Windows reality check

The CLI installs and the dataset clones, but **the harness does not run a trial to completion on
native Windows.** Two confirmed root causes, both "the code assumes it's on Linux":

1. **Dataset auto-download is POSIX-only.**
   `terminal_bench/registry/client.py` (`download_dataset`) `git clone`s the dataset, then runs
   `subprocess.run(["rm", "-rf", ".git"], check=True)` — `rm` isn't a Windows command — and copies
   from `temp/<dataset_path>`. Separately, the `terminal-bench-core==head` entry points at the repo's
   `main` branch with `dataset_path=./tasks`, but the tasks live on the dedicated
   `dataset/terminal-bench-core/v0.1.x` branch, so the copy source doesn't exist.
   → **Workaround:** clone the dataset branch yourself and use `--dataset-path` (above).

2. **Container file-copy uses the host path separator.**
   `terminal_bench/terminal/docker_compose_manager.py::copy_to_container` calls
   `container.put_archive(container_dir, …)` where `container_dir` ends up as `\tmp` on Windows
   instead of `/tmp`. Docker (the container is Linux) returns
   `404 … Could not find the file \tmp in container`. There is no flag-level workaround, and
   patching site-packages is fragile — and this is almost certainly not the only POSIX assumption
   downstream (tmux session wiring, asciinema recording paths, etc.).

### The fix: run inside WSL2

Docker Desktop here is already WSL2-backed, but only the minimal **`docker-desktop`** utility distro
exists (no login shell), so there's no Linux userland to run `tb` in. Install a real distro and run
the harness as a Linux process — then container paths are `/`-based and the POSIX assumptions hold.

```powershell
wsl --install -d Ubuntu        # one-time; may prompt to reboot and create a UNIX user
```

Then in **Docker Desktop → Settings → Resources → WSL Integration**, enable integration for the
Ubuntu distro. Inside Ubuntu:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh      # uv
uv tool install terminal-bench
export GEMINI_API_KEY=...                             # your key(s)
# clone tasks (or let the registry auto-download — it works on Linux)
tb run --agent oracle -t hello-world -d terminal-bench-core==0.1.1
```

Keep the repo on the Windows filesystem if you like (`/mnt/c/Users/PhilVanEvery/Git/…`), but for
speed prefer cloning task datasets inside the WSL filesystem (`~/…`); cross-`/mnt` Docker bind
performance is poor.

> **Why not just patch the package?** We could monkey-patch the two functions above, but every
> upgrade would reintroduce the bugs, and the harness drives tmux/asciinema with more POSIX
> assumptions we haven't hit yet. WSL2 is the supported environment and the lower-maintenance path.

## Status on this machine (initial setup, 2026-06-11)

| Step | State |
|---|---|
| Docker / uv / git present | ✓ |
| `tb` CLI installed (0.2.18) | ✓ |
| Core task set cloned locally (86 tasks) | ✓ in `_datasets/terminal-bench-core-0.1.x/` |
| Harness builds task container + starts trial | ✓ |
| `oracle` resolves `hello-world` | ✗ — `failure_mode: unknown_agent_error` (the `\tmp` copy bug) |
| Custom Python / MPL agent run | ⏳ blocked on a working harness (WSL2) |

Next step is gated on installing a WSL2 distro (a heavyweight, reboot-capable system change) — left
for explicit go-ahead rather than done implicitly.

## Cost note

The paper reports **$1–$100 per full run** depending on model, with some single tasks making
hundreds of API calls / ~100M tokens. Always iterate with `oracle`/`nop` (free) and a single
`-t <task>` on a cheap model before any full-set sweep.

## Files here

- `README.md` — this file.
- `custom-agents.md` — how to run Terminal-Bench against a custom Python agent and a custom MPL agent.
- `_probe_registry.py` — tiny helper that prints a dataset's clone URL/branch/path from the `tb`
  registry (how the local-clone workaround was derived). Run with the tool venv's Python.
- `_datasets/`, `runs/` — gitignored (cloned tasks, run outputs).
