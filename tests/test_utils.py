import pytest

from temporal_graph import Edge, TemporalGraph
from temporal_graph.utils import filter_edges, from_edge_list, snapshot_diff, subgraph


@pytest.fixture
def graph():
    g = TemporalGraph(["a", "b", "c"])
    g.add_snapshot(0, [Edge("a", "b"), Edge("b", "c", weight=5)])
    g.add_snapshot(1, [Edge("a", "b"), Edge("a", "c")])
    return g


def test_from_edge_list():
    g = from_edge_list(["a", "b", "c"], {1: [("b", "c")], 0: [("a", "b")]})
    assert g.timesteps == [0, 1]
    assert [e.key() for e in g.edges_at(1)] == [("b", "c")]


def test_from_edge_list_unknown_node():
    with pytest.raises(ValueError):
        from_edge_list(["a"], {0: [("a", "z")]})


def test_snapshot_diff(graph):
    added, removed = snapshot_diff(graph, 0, 1)
    assert [e.key() for e in added] == [("a", "c")]
    assert [e.key() for e in removed] == [("b", "c")]
    assert snapshot_diff(graph, 0, 0) == ([], [])


def test_snapshot_diff_missing_timestep(graph):
    with pytest.raises(KeyError):
        snapshot_diff(graph, 0, 9)


def test_filter_edges_keeps_structure(graph):
    result = filter_edges(graph, lambda e: e.weight > 1)
    assert result.nodes == graph.nodes
    assert result.timesteps == [0, 1]
    assert [e.key() for e in result.edges_at(0)] == [("b", "c")]
    assert result.edges_at(1) == []


def test_filter_edges_does_not_mutate_input(graph):
    filter_edges(graph, lambda e: False)
    assert len(graph.edges_at(0)) == 2


def test_subgraph(graph):
    result = subgraph(graph, ["c", "a"])
    assert result.nodes == ["a", "c"]
    assert result.edges_at(0) == []
    assert [e.key() for e in result.edges_at(1)] == [("a", "c")]


def test_subgraph_errors(graph):
    with pytest.raises(ValueError, match="not in graph"):
        subgraph(graph, ["a", "z"])
    with pytest.raises(ValueError):
        subgraph(graph, [])
