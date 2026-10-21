import itertools
import random

import pytest

from temporal_graph import Edge, TemporalGraph
from temporal_graph.flows import (
    max_edge_disjoint_journeys,
    max_node_disjoint_journeys,
    max_out_disjoint_journeys,
    min_departure_separator,
    min_edge_separator,
)
from temporal_graph.journeys import enumerate_journeys

from .pdf_examples import example_4_3, figure_2


def blocks_every_journey(graph, source, target, departures):
    return all(
        any((a, t) in departures for a, _, t in journey.steps)
        for journey in enumerate_journeys(graph, source, target)
    )


def test_example_4_3():
    g = example_4_3()
    assert len(list(enumerate_journeys(g, "u1", "u4"))) == 9
    assert max_out_disjoint_journeys(g, "u1", "u4") == 3
    cut = min_departure_separator(g, "u1", "u4")
    assert len(cut) == 3 and blocks_every_journey(g, "u1", "u4", cut)


def test_figure_2_menger_variants():
    g = figure_2()
    assert len(max_node_disjoint_journeys(g, "u1", "u5")) == 1   # Section 4.2
    assert max_out_disjoint_journeys(g, "u1", "u5") == 2         # Exercise 4.1
    assert min_departure_separator(g, "u1", "u5") == {("u1", 1), ("u1", 5)}
    assert max_edge_disjoint_journeys(g, "u1", "u5") == 2        # Berman
    assert len(min_edge_separator(g, "u1", "u5")) == 2


def test_edge_version_requires_single_labels():
    with pytest.raises(ValueError, match="single labels"):
        max_edge_disjoint_journeys(example_4_3(), "u1", "u4")


def test_no_journeys_and_errors():
    g = TemporalGraph(["a", "b"])
    assert max_out_disjoint_journeys(g, "a", "b") == 0
    assert min_departure_separator(g, "a", "b") == set()
    assert max_edge_disjoint_journeys(g, "a", "b") == 0
    with pytest.raises(ValueError, match="differ"):
        max_out_disjoint_journeys(figure_2(), "u1", "u1")


def test_direct_edge_counts_once_for_node_disjointness():
    g = TemporalGraph.from_time_edges(["s", "z"], [("s", "z", 1), ("s", "z", 2)])
    assert len(max_node_disjoint_journeys(g, "s", "z")) == 1


def brute_force_out_disjoint(graph, source, target):
    journeys = list(enumerate_journeys(graph, source, target))
    departures = [frozenset((a, t) for a, _, t in j.steps) for j in journeys]
    for size in range(len(journeys), 0, -1):
        for combo in itertools.combinations(range(len(journeys)), size):
            if all(not departures[i] & departures[j] for i, j in itertools.combinations(combo, 2)):
                return size
    return 0


@pytest.mark.parametrize("seed", range(30))
def test_temporal_menger_max_equals_min_on_random_graphs(seed):
    rng = random.Random(seed)
    nodes = [str(i) for i in range(5)]
    g = TemporalGraph(nodes)
    for t in range(1, 6):
        g.add_snapshot(t, [Edge(*rng.sample(nodes, 2)) for _ in range(3)])
    flow = max_out_disjoint_journeys(g, "0", "4")
    cut = min_departure_separator(g, "0", "4")
    assert flow == len(cut) == brute_force_out_disjoint(g, "0", "4")
    assert blocks_every_journey(g, "0", "4", cut)
