import pytest

from embedding_db.chunking import chunk_text
from embedding_db.chroma_store import ChromaStore
from embedding_db.embedder import embed
from embedding_db.numpy_store import NumpyStore
from embedding_db.pdf_loader import load_pdf


@pytest.mark.slow
def test_numpy_pipeline_on_handbook(pdf_path):
    text = load_pdf(pdf_path)
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    vectors = embed(chunks)

    store = NumpyStore()
    for chunk, vec in zip(chunks, vectors):
        store.add(chunk, vec)

    query_vec = embed(["paid time off and vacation"])[0]
    results = store.search(query_vec, k=3)

    assert len(results) == 3
    assert all(-1.0001 <= r[1] <= 1.0001 for r in results)


@pytest.mark.slow
def test_chroma_pipeline_on_handbook(pdf_path):
    text = load_pdf(pdf_path)
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    vectors = embed(chunks)

    store = ChromaStore(collection_name="handbook_e2e")
    for chunk, vec in zip(chunks, vectors):
        store.add(chunk, vec)

    query_vec = embed(["paid time off and vacation"])[0]
    results = store.search(query_vec, k=3)

    assert len(results) == 3
