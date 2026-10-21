import pytest

from temporal_graph import Edge
from temporal_graph.graph import DEFAULT_COLOR


def test_defaults():
    e = Edge("a", "b")
    assert (e.directed, e.weight, e.color) == (False, 1.0, None)


@pytest.mark.parametrize(
    "kwargs, exc",
    [
        ({"u": 1, "v": "b"}, TypeError),
        ({"u": "a", "v": None}, TypeError),
        ({"u": "a", "v": "a"}, ValueError),
        ({"u": "a", "v": "b", "directed": 1}, TypeError),
        ({"u": "a", "v": "b", "weight": "2"}, TypeError),
        ({"u": "a", "v": "b", "weight": -1}, ValueError),
        ({"u": "a", "v": "b", "color": 5}, TypeError),
    ],
)
def test_validation(kwargs, exc):
    with pytest.raises(exc):
        Edge(**kwargs)


def test_zero_weight_allowed():
    assert Edge("a", "b", weight=0).weight == 0


def test_undirected_identity_ignores_order_weight_color():
    assert Edge("a", "b") == Edge("b", "a", weight=3, color="red")
    assert hash(Edge("a", "b")) == hash(Edge("b", "a"))
    assert Edge("a", "b").key() == ("a", "b") == Edge("b", "a").key()


def test_eq_with_other_type():
    assert Edge("a", "b") != ("a", "b")


def test_other():
    e = Edge("a", "b")
    assert e.other("a") == "b"
    assert e.other("b") == "a"
    with pytest.raises(ValueError):
        e.other("c")


def test_endpoints_in_order():
    assert Edge("b", "a", directed=True).endpoints_in_order() == ("b", "a")
    assert Edge("b", "a").endpoints_in_order() == ("a", "b")


def test_effective_color():
    assert Edge("a", "b").effective_color() == DEFAULT_COLOR
    assert Edge("a", "b", color="#f00").effective_color() == "#f00"


def test_frozen():
    with pytest.raises(AttributeError):
        Edge("a", "b").weight = 2  # type: ignore[misc]
