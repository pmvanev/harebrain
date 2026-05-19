# python

Python playground for exploring RAG, LangChain, LangGraph, and related ideas alongside the design-journal notes in this repo.

## Layout

A [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/) — one root, many member packages. Each package pins its own dependencies but shares a single lockfile and `.venv`.

```
python/
├── pyproject.toml          # workspace root (no code, just members + shared dev deps)
├── uv.lock                 # shared lockfile
├── .venv/                  # shared virtual env (created by `uv sync`)
└── packages/
    ├── hello_world/        # smoke test — proves the workspace + test runner work
    ├── rag/                # (planned) retrieval-augmented generation experiments
    ├── langchain/          # (planned) bare LangChain experiments
    └── langgraph/          # (planned) LangGraph state-machine experiments
```

Each member package follows a `src/` layout:

```
packages/<name>/
├── pyproject.toml
├── src/<name>/             # importable as `import <name>`
│   └── __init__.py
└── tests/
    └── test_*.py
```

## Why a workspace (vs. one flat package)

- Each experiment can pin a different `langchain` / `langgraph` version without fighting the others.
- Shared utilities (later) can live in their own member package and be imported by the rest without path hacks.
- One `uv sync` resolves and installs everything; one `uv run pytest` runs all tests.

## Common commands

Run from the `python/` directory:

```bash
uv sync                                # install all workspace members + dev deps
uv run pytest                          # run all tests across all packages
uv run --package hello_world pytest    # run tests for one package
uv add --package hello_world <dep>     # add a dep to a specific package
```

## Packages

| Package | Status | About |
|---|---|---|
| [hello_world](packages/hello_world/) | ✅ | Smoke test for the workspace setup. |
| [embedding_db](packages/embedding_db/) | ✅ | PDF → chunks → embeddings → vector store → search. Hand-rolled NumPy store alongside a Chroma-backed one. |
| rag | planned | Retrieval-augmented generation: chunking, embeddings, vector stores, retrieval strategies. |
| langchain | planned | Direct LangChain primitives — chains, prompts, output parsers, tools. |
| langgraph | planned | LangGraph state graphs for agentic flows. |
