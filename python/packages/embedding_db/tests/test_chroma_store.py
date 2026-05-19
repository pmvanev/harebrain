from embedding_db.chroma_store import ChromaStore


def test_empty_store_returns_no_results(make_unit):
    store = ChromaStore(collection_name="empty")
    assert store.search(make_unit([1, 0, 0]), k=5) == []


def test_add_and_search_returns_closest(make_unit):
    store = ChromaStore(collection_name="fruit")
    store.add("apple", make_unit([1, 0, 0]))
    store.add("banana", make_unit([0, 1, 0]))
    store.add("cherry", make_unit([0, 0, 1]))

    results = store.search(make_unit([0.9, 0.1, 0.0]), k=2)
    assert results[0][0] == "apple"
    assert len(results) == 2


def test_similarity_scores_are_bounded(make_unit):
    store = ChromaStore(collection_name="scores")
    store.add("a", make_unit([1, 0]))
    store.add("b", make_unit([0, 1]))

    results = store.search(make_unit([1, 0]), k=2)
    for _, score in results:
        assert -1.0001 <= score <= 1.0001


def test_persist_dir_round_trips(make_unit, tmp_path):
    persist = str(tmp_path / "chroma")
    store_a = ChromaStore(collection_name="persisted", persist_dir=persist)
    store_a.add("hello", make_unit([1, 0, 0]))

    store_b = ChromaStore(collection_name="persisted", persist_dir=persist)
    results = store_b.search(make_unit([1, 0, 0]), k=1)
    assert results[0][0] == "hello"
