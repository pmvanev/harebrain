from embedding_db.numpy_store import NumpyStore


def test_empty_store_returns_no_results(make_unit):
    store = NumpyStore()
    assert store.search(make_unit([1, 0, 0]), k=5) == []


def test_add_and_search_returns_closest(make_unit):
    store = NumpyStore()
    store.add("apple", make_unit([1, 0, 0]))
    store.add("banana", make_unit([0, 1, 0]))
    store.add("cherry", make_unit([0, 0, 1]))

    results = store.search(make_unit([0.9, 0.1, 0.0]), k=2)
    assert [r[0] for r in results] == ["apple", "banana"]


def test_search_returns_scores_in_descending_order(make_unit):
    store = NumpyStore()
    store.add("a", make_unit([1, 0]))
    store.add("b", make_unit([0.7, 0.7]))
    store.add("c", make_unit([0, 1]))

    results = store.search(make_unit([1, 0.1]), k=3)
    scores = [r[1] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_k_larger_than_size_returns_everything(make_unit):
    store = NumpyStore()
    store.add("only", make_unit([1, 0]))
    results = store.search(make_unit([1, 0]), k=10)
    assert len(results) == 1


def test_len_tracks_adds(make_unit):
    store = NumpyStore()
    assert len(store) == 0
    store.add("a", make_unit([1, 0]))
    store.add("b", make_unit([0, 1]))
    assert len(store) == 2
