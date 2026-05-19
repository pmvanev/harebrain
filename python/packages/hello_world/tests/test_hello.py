from hello_world import hello


def test_hello_default():
    assert hello() == "hello, world"


def test_hello_named():
    assert hello("harebrain") == "hello, harebrain"
