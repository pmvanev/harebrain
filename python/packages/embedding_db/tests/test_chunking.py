import pytest

from embedding_db.chunking import chunk_text


def test_short_text_is_one_chunk():
    assert chunk_text("hello world", chunk_size=500) == ["hello world"]


def test_long_text_splits_into_multiple():
    text = "x" * 1200
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) >= 3
    assert all(len(c) <= 500 for c in chunks)


def test_chunks_overlap_by_overlap_chars():
    text = "abcdefghij" * 100
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    for i in range(len(chunks) - 1):
        assert chunks[i][-20:] == chunks[i + 1][:20]


def test_chunks_cover_entire_text():
    text = "abcdefghij" * 100
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    assert chunks[0].startswith("abcdefghij")
    assert chunks[-1].endswith("abcdefghij")


def test_invalid_chunk_size_raises():
    with pytest.raises(ValueError):
        chunk_text("hi", chunk_size=0)


def test_overlap_must_be_smaller_than_chunk():
    with pytest.raises(ValueError):
        chunk_text("hi", chunk_size=10, overlap=10)
