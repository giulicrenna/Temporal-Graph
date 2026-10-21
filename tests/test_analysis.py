import pytest

from temporal_graph import Edge, TemporalGraph
from temporal_graph.analysis import (
    connected_components_at,
    degree_timeline,
    edge_persistence,
    is_temporally_acyclic,
)


@pytest.fixture
def graph():
    g = TemporalGraph(["a", "b", "c", "d"])
    g.add_snapshot(0, [Edge("a", "b"), Edge("b", "c")])
    g.add_snapshot(1, [Edge("a", "b")])
    g.add_snapshot(2, [Edge("c", "d", directed=True)])
    g.add_snapshot(3, [])
    return g


def test_degree_timeline(graph):
    assert degree_timeline(graph, "b") == {0: 2, 1: 1, 2: 0, 3: 0}
    assert degree_timeline(graph, "d") == {0: 0, 1: 0, 2: 1, 3: 0}


def test_degree_timeline_unknown_node(graph):
    with pytest.raises(ValueError):
        degree_timeline(graph, "z")


def test_connected_components(graph):
    assert connected_components_at(graph, 0) == [{"a", "b", "c"}, {"d"}]
    assert connected_components_at(graph, 2) == [{"a"}, {"b"}, {"c", "d"}]
    assert connected_components_at(graph, 3) == [{"a"}, {"b"}, {"c"}, {"d"}]


def test_connected_components_missing_timestep(graph):
    with pytest.raises(KeyError):
        connected_components_at(graph, 9)


def test_edge_persistence(graph):
    assert edge_persistence(graph) == {
        ("a", "b"): 0.5,
        ("b", "c"): 0.25,
        ("c", "d"): 0.25,
    }


def test_edge_persistence_empty():
    assert edge_persistence(TemporalGraph(["a"])) == {}


def test_acyclic_true(graph):
    assert is_temporally_acyclic(graph)


def test_acyclic_detects_cycle_in_one_snapshot():
    g = TemporalGraph(["a", "b", "c"])
    g.add_snapshot(0, [Edge("a", "b", directed=True)])
    g.add_snapshot(
        1,
        [
            Edge("a", "b", directed=True),
            Edge("b", "c", directed=True),
            Edge("c", "a", directed=True),
        ],
    )
    assert not is_temporally_acyclic(g)


def test_acyclic_ignores_undirected_triangle():
    g = TemporalGraph(["a", "b", "c"])
    g.add_snapshot(0, [Edge("a", "b"), Edge("b", "c"), Edge("c", "a")])
    assert is_temporally_acyclic(g)
