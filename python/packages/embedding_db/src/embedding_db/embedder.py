from __future__ import annotations

import numpy as np

MODEL_NAME = "all-MiniLM-L6-v2"

_model = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed(texts: list[str]) -> np.ndarray:
    """Encode texts as a (n_texts, embedding_dim) array of unit-normalized float32 vectors."""
    model = get_model()
    return model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
