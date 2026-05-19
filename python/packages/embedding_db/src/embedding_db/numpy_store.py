from __future__ import annotations

import numpy as np


class NumpyStore:
    """Minimal hand-rolled vector store: parallel arrays of text + unit vectors, cosine-similarity search.

    Assumes input vectors are already unit-normalized so cosine similarity reduces to a dot product.
    """

    def __init__(self) -> None:
        self._texts: list[str] = []
        self._matrix: np.ndarray | None = None

    def __len__(self) -> int:
        return len(self._texts)

    def add(self, text: str, vector: np.ndarray) -> None:
        vec = np.asarray(vector, dtype=np.float32).reshape(1, -1)
        if self._matrix is None:
            self._matrix = vec
        else:
            self._matrix = np.vstack([self._matrix, vec])
        self._texts.append(text)

    def search(self, query: np.ndarray, k: int = 5) -> list[tuple[str, float]]:
        if self._matrix is None or not self._texts:
            return []
        q = np.asarray(query, dtype=np.float32).reshape(-1)
        scores = self._matrix @ q
        top_k = min(k, len(self._texts))
        idxs = np.argsort(-scores)[:top_k]
        return [(self._texts[i], float(scores[i])) for i in idxs]
