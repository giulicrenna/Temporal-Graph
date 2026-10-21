import math
import random

import pytest

from temporal_graph import Edge, TemporalGraph
from temporal_graph.connectivity import (
    connectivity_time,
    future_set_sizes,
    is_continuously_connected,
    is_f_connected,
    is_interval_connected,
    lifetime,
    outgoing_influence_time,
    temporal_diameter,
    vertex_connectivity_at,
)
from temporal_graph.generators import alternating_matchings, moving_star, soifer_graph


@pytest.mark.parametrize(
    "generator, ct, oit, d",
    [(moving_star, 1, 1, 7), (alternating_matchings, 2, 1, 4), (soifer_graph, 2, 1, 4)],
)
def test_table_4(generator, ct, oit, d):
    g = generator(8, 40)
    assert connectivity_time(g) == ct
    assert outgoing_influence_time(g) == oit
    assert temporal_diameter(g) == d


@pytest.mark.parametrize("n, d", [(5, 4), (6, 5), (8, 7), (10, 9)])
def test_moving_star_diameter_is_n_minus_1(n, d):
    assert temporal_diameter(moving_star(n, 6 * n)) == d


@pytest.mark.parametrize("n", [6, 8, 10])
def test_alternating_matchings_diameter_is_half_n(n):
    assert temporal_diameter(alternating_matchings(n, 6 * n)) == n // 2


def test_snapshot_properties():
    star, matchings = moving_star(6, 10), alternating_matchings(6, 10)
    assert is_continuously_connected(star)
    assert not is_continuously_connected(matchings)
    assert is_interval_connected(star, 1) and not is_interval_connected(star, 2)
    assert vertex_connectivity_at(star, 1) == 1
    assert vertex_connectivity_at(matchings, 1) == 0
    assert is_f_connected(star, 1) and not is_f_connected(star, 2)
    with pytest.raises(ValueError):
        is_interval_connected(star, 0)


def test_clique_snapshots_are_n_minus_1_connected_and_diameter_1():
    nodes = [str(i) for i in range(5)]
    clique = [Edge(u, v) for i, u in enumerate(nodes) for v in nodes[i + 1:]]
    g = TemporalGraph(nodes)
    for t in range(1, 6):
        g.add_snapshot(t, clique)
    assert vertex_connectivity_at(g, 1) == 4
    assert is_f_connected(g, 4)
    assert temporal_diameter(g) == 1  # Exercise 6.3


def test_future_set_grows_by_one_per_instant_on_the_star():
    sizes = future_set_sizes(moving_star(8, 30), "u7", 0)
    assert [size for _, size in sizes[:9]] == [1, 2, 3, 4, 5, 6, 7, 8, 8]


def test_unrecorded_instants_have_no_edges():
    g = TemporalGraph(["a", "b"])
    g.add_snapshot(1, [Edge("a", "b")])
    g.add_snapshot(3, [Edge("a", "b")])
    assert lifetime(g) == (1, 3)
    assert not is_continuously_connected(g)
    assert connectivity_time(g) == 2


def test_degenerate_graphs():
    single = TemporalGraph(["a"])
    assert temporal_diameter(single) == 0
    assert connectivity_time(single) == 1
    assert outgoing_influence_time(single) == 1
    two = TemporalGraph(["a", "b"])
    assert temporal_diameter(two) is None
    assert connectivity_time(two) is None
    assert outgoing_influence_time(two) is None
    assert lifetime(two) is None
    disconnected = TemporalGraph.from_time_edges(list("abc"), [("a", "b", 1)])
    assert connectivity_time(disconnected) is None
    assert temporal_diameter(disconnected) is None


@pytest.mark.parametrize("seed", range(25))
def test_inequalities_oit_ct_d(seed):
    rng = random.Random(seed)
    nodes = [str(i) for i in range(5)]
    g = TemporalGraph(nodes)
    for t in range(1, 25):
        g.add_snapshot(t, [Edge(*rng.sample(nodes, 2)) for _ in range(3)])
    ct, oit, d = connectivity_time(g), outgoing_influence_time(g), temporal_diameter(g)
    if None not in (ct, oit, d):
        assert oit <= ct <= d <= (len(nodes) - 1) * ct


def test_proposition_6_2_bound_on_f_connected_snapshots():
    g = soifer_graph(8, 30)
    n = len(g.nodes)
    for f in range(1, 3):
        if is_f_connected(g, f):
            assert temporal_diameter(g) <= math.ceil((n - 1) / f)
