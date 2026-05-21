# harebrain-wumpus

The Hunt the Wumpus working directory for the harebrain article series — Gregory Yob's 1973 BASIC source set up to run on Windows, plus the Python project that hosts the planned experiments around it.

See [`docs/wumpus_idea.md`](docs/wumpus_idea.md) for what this is *for* — the experiment matrix, the cage thesis, and why Wumpus is the first concrete test.

## Layout

```
wumpus/
├── pyproject.toml              uv project — experiment harness deps live here
├── experiments/
│   ├── g_wild_baseline/        the runnable Yob BASIC source (+ provenance)
│   └── pure_llm_trust.md       planned experiment notes
└── docs/                       the prose
```

## Prerequisites

- **Python 3.12** available to uv (uv will pull it if you don't have it).
- **[uv](https://docs.astral.sh/uv/)** on PATH.

## Install

Two installs — one global tool to run the BASIC interpreter, one project venv for the Python harness.

### 1. PC-BASIC (global uv tool)

PC-BASIC 2.0.7 imports `chunk` from the stdlib, which was removed in Python 3.13. Install it into an isolated 3.12 tool environment so it doesn't fight whatever your system Python is:

```powershell
uv tool install --python 3.12 pcbasic
```

This puts a `pcbasic` shim on PATH backed by a private 3.12 interpreter. Nothing else on your system changes.

### 2. Project venv (for the harness)

From inside `wumpus/`:

```powershell
uv sync
```

Creates `.venv/` with `anthropic`, `wexpect`, `python-dotenv`, `pytest`, and `setuptools<81` (wexpect 4.0.0 still imports `pkg_resources`).

## Play

From inside `wumpus/`:

```powershell
pcbasic --interface=text experiments/g_wild_baseline/wumpus.gwbasic.bas
```

`--interface=text` keeps it in your existing terminal — no SDL window. Ctrl-C quits.

Quick example session:

```
INSTRUCTIONS (Y-N)? N
HUNT THE WUMPUS

I SMELL A WUMPUS!
YOU ARE IN ROOM  8
TUNNELS LEAD TO  1  7  9

SHOOT OR MOVE (S-M)? M
WHERE TO? 7
```

See [`experiments/g_wild_baseline/README.md`](experiments/g_wild_baseline/README.md) for the source provenance, the GW-BASIC dialect patches, and the byte-level audit trail against Yob's original.

## Run experiments

Once an experiment has a Python entry point:

```powershell
uv run python experiments/<cell>/run.py
```

`uv run` auto-syncs the venv from `uv.lock`, so no manual `activate` step.
