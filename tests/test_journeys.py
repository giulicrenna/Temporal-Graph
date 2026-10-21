import random
from collections import deque

import pytest

from temporal_graph import Edge, TemporalGraph
from temporal_graph.expansion import static_expansion
from temporal_graph.journeys import (
    Journey,
    earliest_arrival,
    enumerate_journeys,
    fastest_journey,
    foremost_journey,
    is_temporally_connected,
    latest_departure,
    reachability,
    reachable,
    shortest_journey,
    temporal_distance,
)

from .pdf_examples import example_2_2, example_2_6, figure_2

# -- time-edge model ---------------------------------------------------------

def test_time_edges_labels_age_and_count():
    g = figure_2()
    assert g.age == 7 and g.label_count == 7
    assert g.labels("u2", "u1") == [5]
    assert g.time_edges()[0] == ("u1", "u3", 1, False, 1.0)
    empty = TemporalGraph(["a"])
    assert empty.age == 0 and empty.label_count == 0 and empty.time_edges() == []


def test_time_edges_follow_direction_and_cache_is_invalidated():
    g = TemporalGraph(["a", "b"])
    g.add_snapshot(1, [Edge("b", "a", directed=True)])
    assert [(e.u, e.v) for e in g.time_edges()] == [("b", "a")]
    g.add_snapshot(0, [Edge("a", "b")])
    assert [e.t for e in g.time_edges()] == [0, 1]
    g.add_snapshot(1, [])
    assert [e.t for e in g.time_edges()] == [0]


def test_from_time_edges_groups_by_instant():
    g = TemporalGraph.from_time_edges(
        ["a", "b", "c"], [("a", "b", 3), ("b", "c", 3), ("a", "c", 1)]
    )
    assert g.timesteps == [1, 3]
    assert {e.key() for e in g.edges_at(3)} == {("a", "b"), ("b", "c")}


def test_static_expansion_sizes_match_proposition_2_4():
    expansion = static_expansion(example_2_6())  # Example 2.6
    assert (len(expansion.time_nodes), len(expansion.arcs)) == (16, 20)
    assert len(expansion.vertical_arcs) == 12
    expansion = static_expansion(figure_2())  # Exercise 2.1
    assert (len(expansion.time_nodes), len(expansion.arcs)) == (40, 49)
    assert static_expansion(figure_2(), waiting=False).vertical_arcs == []


# -- foremost / reachability -------------------------------------------------

def test_foremost_example_3_5_and_exercises_3_1_3_2():
    g = figure_2()
    assert earliest_arrival(g, "u1", 0) == {"u1": 0, "u3": 1, "u2": 2, "u5": 3, "u4": 4}
    assert str(foremost_journey(g, "u1", "u5", 0)) == "u1 -1-> u3 -2-> u2 -3-> u5"
    assert earliest_arrival(g, "u5", 0) == {"u5": 0, "u2": 3, "u1": 5, "u4": 6}
    assert earliest_arrival(g, "u1", 2) == {"u1": 2, "u2": 5, "u4": 6, "u5": 7}


def test_reachability_is_neither_symmetric_nor_transitive():
    matrix = reachability(example_2_2(), 0)  # Example 3.3
    assert "B" in matrix["A"] and "C" in matrix["B"] and "C" not in matrix["A"]
    assert "A" in matrix["C"]
    assert reachable(example_2_6(), "d", 0) == {"c", "d"}  # Example 2.6
    assert not is_temporally_connected(example_2_2())


def test_non_strict_journeys_chain_within_an_instant():
    g = TemporalGraph.from_time_edges(list("ABC"), [("A", "B", 1), ("B", "C", 1)])
    assert "C" not in earliest_arrival(g, "A", 0)
    assert earliest_arrival(g, "A", 0, strict=False) == {"A": 0, "B": 1, "C": 1}


def test_non_strict_latest_departure_shortest_and_fastest():
    g = TemporalGraph.from_time_edges(list("ABCD"), [("A", "B", 2), ("B", "C", 2), ("C", "D", 3)])
    assert latest_departure(g, "D", strict=False) == {"D": 3, "C": 3, "B": 2, "A": 2}
    # strictly, A cannot chain A-B and B-C at the same instant 2
    assert latest_departure(g, "D") == {"D": 3, "C": 3, "B": 2}
    assert shortest_journey(g, "A", "D", strict=False).labels == [2, 2, 3]
    assert fastest_journey(g, "A", "C", strict=False).duration == 1
    assert shortest_journey(g, "A", "D") is None


def test_directed_edges_are_one_way():
    g = TemporalGraph.from_time_edges(["a", "b"], [("a", "b", 1)], directed=True)
    assert reachable(g, "a") == {"a", "b"}
    assert reachable(g, "b") == {"b"}


def test_temporal_distance_and_default_start():
    g = figure_2()
    assert temporal_distance(g, "u1", "u4", 0) == 4
    assert temporal_distance(g, "u1", "u1", 0) == 0
    assert temporal_distance(g, "u5", "u3", 0) is None
    assert earliest_arrival(g, "u1") == earliest_arrival(g, "u1", 0)


def test_journey_properties():
    journey = foremost_journey(figure_2(), "u1", "u4", 0)
    assert journey.nodes == ["u1", "u3", "u4"]
    assert (journey.departure, journey.arrival, journey.duration, journey.hops) == (1, 4, 4, 2)
    assert journey.labels == [1, 4]
    with pytest.raises(ValueError):
        Journey(())


# -- other optimality criteria -----------------------------------------------

def test_enumeration_matches_table_2():
    journeys = {str(j) for j in enumerate_journeys(figure_2(), "u1", "u5")}
    assert journeys == {
        "u1 -1-> u3 -2-> u2 -3-> u5",
        "u1 -1-> u3 -2-> u2 -6-> u4 -7-> u5",
        "u1 -1-> u3 -4-> u4 -7-> u5",
        "u1 -5-> u2 -6-> u4 -7-> u5",
    }


def test_latest_departure():
    assert latest_departure(figure_2(), "u5") == {"u5": 7, "u4": 7, "u2": 6, "u1": 5, "u3": 4}
    assert latest_departure(figure_2(), "u5", deadline=3) == {"u5": 3, "u2": 3, "u3": 2, "u1": 1}


def test_fastest_and_shortest():
    g = TemporalGraph.from_time_edges(
        list("sabz"), [("s", "a", 1), ("a", "z", 9), ("s", "b", 7), ("b", "z", 8), ("s", "z", 12)]
    )
    assert str(foremost_journey(g, "s", "z")) == "s -7-> b -8-> z"
    assert fastest_journey(g, "s", "z").duration == 1
    assert shortest_journey(g, "s", "z").hops == 1
    assert fastest_journey(g, "z", "s") is None or fastest_journey(g, "z", "s").duration >= 1


def test_missing_journeys_and_errors():
    g = example_2_2()
    assert foremost_journey(g, "A", "C") is None
    assert shortest_journey(g, "A", "C") is None
    assert fastest_journey(g, "A", "C") is None
    for function in (foremost_journey, fastest_journey, shortest_journey):
        with pytest.raises(ValueError, match="differ"):
            function(g, "A", "A")
    with pytest.raises(ValueError, match="not declared"):
        earliest_arrival(g, "Z")


# -- cross-checks against brute force ----------------------------------------

def random_graph(rng, n=6, labels=10, max_t=8, directed=False):
    nodes = [f"n{i}" for i in range(n)]
    edges = {}
    for _ in range(labels):
        u, v = rng.sample(nodes, 2)
        edges[(min(u, v), max(u, v), rng.randint(1, max_t))] = (u, v)
    by_t = {}
    for (_, _, t), (u, v) in edges.items():
        by_t.setdefault(t, []).append(Edge(u, v, directed=directed))
    g = TemporalGraph(nodes)
    for t, items in by_t.items():
        g.add_snapshot(t, items)
    return g


def expansion_bfs(graph, source, start):
    expansion = static_expansion(graph)
    arcs = {}
    for a, b in expansion.arcs:
        arcs.setdefault(a, []).append(b)
    origin = (source, max(start, expansion.first_level))
    seen = {origin}
    queue = deque([origin])
    while queue:
        node = queue.popleft()
        for nxt in arcs.get(node, []):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    best = {}
    for node, level in seen:
        best[node] = min(best.get(node, level), level)
    best[source] = start
    return best


@pytest.mark.parametrize("seed", range(60))
@pytest.mark.parametrize("directed", [False, True])
def test_foremost_matches_static_expansion_bfs(seed, directed):
    rng = random.Random(seed)
    g = random_graph(rng, directed=directed)
    start = rng.choice([0, 2])
    assert earliest_arrival(g, "n0", start) == expansion_bfs(g, "n0", start)


@pytest.mark.parametrize("seed", range(40))
def test_criteria_match_exhaustive_enumeration(seed):
    rng = random.Random(1000 + seed)
    g = random_graph(rng, n=5, labels=9, max_t=6)
    for target in g.nodes[1:]:
        journeys = list(enumerate_journeys(g, "n0", target))
        foremost = foremost_journey(g, "n0", target)
        fastest = fastest_journey(g, "n0", target)
        shortest = shortest_journey(g, "n0", target)
        if not journeys:
            assert foremost is fastest is shortest is None
            continue
        assert foremost.arrival == min(j.arrival for j in journeys)
        assert fastest.duration == min(j.duration for j in journeys)
        assert shortest.hops == min(j.hops for j in journeys)
        for journey in (foremost, fastest, shortest):
            assert str(journey) in {str(j) for j in journeys}
        latest = latest_departure(g, target)
        assert latest["n0"] == max(j.departure for j in journeys)
