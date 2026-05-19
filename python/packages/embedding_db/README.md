# embedding_db

A teach-yourself walk through embedding databases: build the pipeline twice, once by hand and once with a library, so the abstractions don't hide what they're doing.

## The pipeline

```
PDF  ->  text  ->  chunks  ->  vectors  ->  store  ->  similarity search
```

| Step | Module | What it does |
|---|---|---|
| Load | `pdf_loader.py` | Extract raw text from a PDF (pypdf). |
| Chunk | `chunking.py` | Split text into overlapping character windows. |
| Embed | `embedder.py` | Encode chunks as unit vectors with `sentence-transformers` (`all-MiniLM-L6-v2`, 384-dim). |
| Store | `numpy_store.py` | Hand-rolled: a list of (text, unit-vector) pairs; cosine similarity = dot product. |
| Store | `chroma_store.py` | Same interface, backed by Chroma. |

Both stores expose `add(text, vector)` and `search(query_vector, k) -> [(text, score), ...]`. Embedding is a separate step on purpose — a vector store doesn't know or care where vectors came from.

## Test data

`data/IA Employee Handbook 050826.pdf` — a real handbook, used end-to-end to verify the pipeline returns plausible chunks for natural-language queries.

## Run

From the workspace root (`python/`):

```bash
uv sync                                              # installs deps (heavy: torch + chromadb)
uv run --package embedding_db pytest -m "not slow"   # fast tests only
uv run --package embedding_db pytest                 # full suite; first run downloads ~90 MB model
```

## Suggested experiments

1. Change `chunk_size` / `overlap` in `chunking.py` and watch end-to-end results shift.
2. Drop `normalize_embeddings=True` in `embedder.py` and see how `NumpyStore.search` breaks (cosine != dot product anymore).
3. Swap `all-MiniLM-L6-v2` for a larger model (e.g. `all-mpnet-base-v2`, 768-dim) and compare retrieval quality.
4. Add a `persist_dir` to `ChromaStore` and inspect the SQLite files it leaves behind.
