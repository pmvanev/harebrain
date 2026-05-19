from __future__ import annotations

import numpy as np


class ChromaStore:
    """Same interface as NumpyStore, backed by Chroma. Configured for cosine distance."""

    def __init__(self, collection_name: str = "default", persist_dir: str | None = None) -> None:
        import chromadb

        if persist_dir:
            self._client = chromadb.PersistentClient(path=persist_dir)
        else:
            self._client = chromadb.EphemeralClient()
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._next_id = 0

    def __len__(self) -> int:
        return self._collection.count()

    def add(self, text: str, vector: np.ndarray) -> None:
        self._collection.add(
            ids=[str(self._next_id)],
            embeddings=[np.asarray(vector, dtype=np.float32).tolist()],
            documents=[text],
        )
        self._next_id += 1

    def search(self, query: np.ndarray, k: int = 5) -> list[tuple[str, float]]:
        if self._collection.count() == 0:
            return []
        result = self._collection.query(
            query_embeddings=[np.asarray(query, dtype=np.float32).tolist()],
            n_results=k,
        )
        texts = result["documents"][0]
        distances = result["distances"][0]
        # Chroma returns cosine *distance* (1 - cosine similarity); convert back to similarity.
        return [(t, 1.0 - float(d)) for t, d in zip(texts, distances)]
