# HANDOFF — read me first (WSL session)

**You are a fresh Claude started from a WSL clone of harebrain.** This note is the working memory
from the prior (Windows) session so you can continue without re-deriving everything. Read this, then
[`README.md`](README.md) and [`custom-agents.md`](custom-agents.md) in this folder.

_Last updated: 2026-06-11, end of the Windows session._

## The goal

Get **Terminal-Bench** running locally and then run it against **custom agents** — first a plain
Python agent, then an **MPL-chart-driven agent** (the harebrain cage). The bigger purpose: Terminal-
Bench is the benchmark/ruler that the harebrain research summaries keep pointing at
(`docs/research-summaries/terminal-bench/`, plus `meta-harness/` and `agent-harness-anatomy/`).
Running our own cage on it turns the harebrain hypothesis (`fast LLM brain × structured game-AI
cage`) into a measurable experiment: hold `--model` fixed, swap a thin scaffold vs. the MPL cage,
measure the delta; then hold the chart fixed and swap models to test transfer.

## Why we're in WSL (not native Windows)

`terminal-bench`'s orchestrator assumes a **POSIX host**. On native Windows it fails two ways
(documented with file:line in `README.md` § "Windows reality check"):
1. dataset cacher shells out to `rm -rf` and the `head` slug points at a branch with no `tasks/`;
2. `copy_to_container` builds the Linux container path with `\` → sends files to `\tmp` not `/tmp`
   → Docker 404.

Both vanish when the orchestrator runs as a **Linux process**. We chose **WSL2 + Ubuntu** over
Docker-in-Docker (DinD rejected: privileged/nested/no shared build cache). On Windows specifically,
WSL is low-friction because Docker Desktop's WSL integration transparently handles the one host-side
bind mount Terminal-Bench task containers use (`T_BENCH_TASK_LOGS_PATH` → task `/logs`); plain
Docker-out-of-Docker would force you to fight Docker Desktop bind-mount path translation.

## State as of this handoff

Done (committed in this repo — that's how you're seeing them):
- `docs/research-summaries/terminal-bench/` — house-style summary of the TB 2.0 paper (arXiv:2601.11868).
- `terminal-bench/README.md` — setup, run commands, the Windows findings, the WSL route, cost notes.
- `terminal-bench/custom-agents.md` — exact `BaseAgent` contract + full Python agent example + MPL
  agent adapter sketch. **This is the spec for the custom-agent work; trust it, it's read off the
  installed package source.**
- `terminal-bench/_probe_registry.py` — helper that prints a dataset's clone URL/branch/path.

Environment already set up (in the WSL2 *system*, survives the re-clone since it's global, but if you
run as a different Linux user than root you may need to re-install — see below):
- Ubuntu WSL2 installed and set as the **default** distro.
- As **root** in Ubuntu: `apt` curl/git, `uv`, and `terminal-bench 0.2.18` installed
  (`/root/.local/bin/tb`). uv auto-fetched CPython 3.13 for it.

**THE ONE REMAINING BLOCKER — a GUI step the prior Claude could not do:**
> Docker Desktop → **Settings → Resources → WSL Integration** → enable the **Ubuntu** toggle →
> **Apply & Restart**. Until this is on, `docker` inside Ubuntu prints
> *"The command 'docker' could not be found in this WSL 2 distro."* Verify with
> `docker version` inside WSL before doing anything else.

## Exact next steps (run these in the WSL clone)

```bash
# 0. PRE-REQ: confirm the Docker Desktop WSL-integration toggle for Ubuntu is ON
docker version --format '{{.Server.Version}}'        # must print a version, not the "not found" error

# 1. tb available? (if you're not root, or a fresh user, install it)
which tb || (curl -LsSf https://astral.sh/uv/install.sh | sh && uv tool install terminal-bench)
export PATH="$HOME/.local/bin:$PATH"

# 2. API key — env vars do NOT carry over from Windows. Only GEMINI_API_KEY was available before.
export GEMINI_API_KEY=...           # ask the user; or whichever provider key they have now

# 3. ZERO-COST harness smoke test. On Linux the registry auto-download works (use the pinned 0.1.1,
#    NOT ==head — head points at a branch with no tasks/). Oracle runs the reference solution.
tb run -d terminal-bench-core==0.1.1 -t hello-world --agent oracle --n-concurrent 1
#    EXPECT: hello-world resolves (accuracy 100%). That is the green baseline the Windows run
#    never reached (it died at the \tmp copy bug). If oracle resolves, the harness works.

# 4. First real agent run (spends a few API tokens on a cheap model)
tb run -d terminal-bench-core==0.1.1 -t hello-world --agent terminus-2 -m gemini/gemini-2.5-flash
```

If the registry auto-download misbehaves even on Linux, fall back to a local clone + `--dataset-path`
(see `README.md` § "Running it"); the dataset branch is `dataset/terminal-bench-core/v0.1.x`.

## Then: the actual work (custom agents)

Follow `custom-agents.md`. In short:
1. **Python agent** — subclass `BaseAgent`, implement `name()` + `perform_task(instruction, session,
   logging_dir)`; drive the task with `session.send_keys([...], block=True)` and read with
   `session.capture_pane()`. Constructor gets `model_name` from `--model`. Run via
   `--agent-import-path module:Class` (make it importable: run `tb` from a `uv` project venv that has
   both `terminal-bench` and your agent module, or set `PYTHONPATH`).
2. **MPL agent** — same `BaseAgent` shell, but `perform_task` boots the MPL runtime and registers
   host-imports `observe()` = `capture_pane`, `act(keys)` = `send_keys`, and a decide-leaf that calls
   the LLM. The MPL runtime's host-import registration API is **not yet pinned** in this repo
   (it's `blocked-on-mpl-spike` in `docs/feature/wumpus/feature-delta.md`, job
   `drive-engine-from-host-import`). Wire the three closures to it once it lands; the TB side of the
   adapter is exact.

## Gotchas carried over

- **API keys don't cross the Windows↔WSL boundary.** Re-export in the WSL shell.
- Use `terminal-bench-core==0.1.1`, never `==head` (head branch lacks `tasks/`).
- The 89-task **paper** set ("2.0") is a separate **Harbor** channel (`harbor run -d
  terminal-bench@2.0`), not in the `tb` registry. `terminal-bench-core` is the right local-iteration
  target.
- Keep task datasets + run outputs on the **WSL ext4 fs** (`~/...`), not `/mnt/c`, for Docker speed.
- `runs/` and `_datasets/` are gitignored. `tb` may crash printing its rich ✓/✗ tables only under the
  Windows console — not an issue in a Linux terminal, so `PYTHONUTF8` is no longer needed.
- Cost: paper reports $1–$100 per full run; iterate with `oracle`/`nop` (free) + single `-t` on a
  cheap model before any full sweep.

## If you (WSL Claude) get stuck

- Harness mechanics / agent contract: re-read `custom-agents.md` (sourced from the installed package).
- Whether a failure is POSIX-vs-Windows: you're on Linux now, so it's a real bug, not the path-sep
  issue — investigate normally.
- Confirm `docker version` works inside WSL first; ~90% of "nothing runs" is the integration toggle.
