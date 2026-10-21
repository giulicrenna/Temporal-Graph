import pytest

from temporal_graph import Edge, TemporalGraph


@pytest.fixture
def graph():
    g = TemporalGraph(["a", "b", "c"])
    g.add_snapshot(0, [Edge("a", "b")])
    g.add_snapshot(1, [Edge("a", "b"), Edge("b", "c")])
    g.add_snapshot(2, [Edge("b", "c")])
    g.add_snapshot(3, [Edge("a", "b")])
    return g


def test_constructor_validation():
    with pytest.raises(ValueError):
        TemporalGraph([])
    with pytest.raises(TypeError):
        TemporalGraph(["a", 1])  # type: ignore[list-item]
    with pytest.raises(ValueError):
        TemporalGraph(["a", "a"])


def test_nodes_returns_copy():
    g = TemporalGraph(["a", "b"])
    g.nodes.append("z")
    assert g.nodes == ["a", "b"]


def test_snapshots_kept_sorted():
    g = TemporalGraph(["a", "b"])
    g.add_snapshot(5, [])
    g.add_snapshot(1, [])
    assert g.timesteps == [1, 5]


@pytest.mark.parametrize("t", ["1", 1.0, True, None])
def test_timestep_must_be_int(t):
    with pytest.raises(TypeError):
        TemporalGraph(["a", "b"]).add_snapshot(t, [])


def test_add_snapshot_rejects_bad_input():
    g = TemporalGraph(["a", "b"])
    with pytest.raises(TypeError):
        g.add_snapshot(0, [("a", "b")])  # type: ignore[list-item]
    with pytest.raises(ValueError):
        g.add_snapshot(0, [Edge("a", "z")])


def test_add_snapshot_replaces_existing():
    g = TemporalGraph(["a", "b", "c"])
    g.add_snapshot(0, [Edge("a", "b")])
    g.add_snapshot(0, [Edge("b", "c")])
    assert g.timesteps == [0]
    assert [e.key() for e in g.edges_at(0)] == [("b", "c")]


def test_duplicates_within_snapshot_are_deduplicated():
    g = TemporalGraph(["a", "b"])
    g.add_snapshot(0, [Edge("a", "b"), Edge("b", "a")])
    assert len(g.edges_at(0)) == 1


def test_edges_at_and_edge_at(graph):
    assert {e.key() for e in graph.edges_at(1)} == {("a", "b"), ("b", "c")}
    assert graph.edge_at(1, ("b", "c")).u == "b"
    with pytest.raises(KeyError):
        graph.edges_at(99)
    with pytest.raises(KeyError):
        graph.edge_at(99, ("a", "b"))
    with pytest.raises(KeyError):
        graph.edge_at(0, ("b", "c"))


def test_per_snapshot_properties_preserved():
    g = TemporalGraph(["a", "b"])
    g.add_snapshot(0, [Edge("a", "b", weight=1)])
    g.add_snapshot(1, [Edge("a", "b", weight=4, color="red")])
    assert g.edge_at(0, ("a", "b")).weight == 1
    assert g.edge_at(1, ("a", "b")).weight == 4


def test_snapshots_listing(graph):
    assert [t for t, _ in graph.snapshots()] == [0, 1, 2, 3]


def test_change_events(graph):
    assert graph.change_events() == [
        (1, "connect", ("b", "c")),
        (2, "disconnect", ("a", "b")),
        (3, "connect", ("a", "b")),
        (3, "disconnect", ("b", "c")),
    ]


def test_change_events_needs_two_snapshots():
    g = TemporalGraph(["a", "b"])
    g.add_snapshot(0, [Edge("a", "b")])
    assert g.change_events() == []


def test_edge_intervals(graph):
    assert graph.edge_intervals() == {
        ("a", "b"): [(0, 2), (3, 4)],
        ("b", "c"): [(1, 3)],
    }
