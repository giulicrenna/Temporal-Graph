import random

import pytest

from temporal_graph import TemporalGraph
from temporal_graph.design import (
    dag_labeling,
    directed_ring_labeling,
    has_journey_along,
    preserves_all_paths,
    preserves_reachability,
    reachability_labeling,
    simple_paths,
    temporal_cost,
    temporality,
    topological_order,
)
from temporal_graph.journeys import earliest_arrival
from temporal_graph.periodic import (
    common_instants,
    edges_coincide,
    linear_availability_graph,
    linear_earliest_arrival,
    next_availability,
    solve_congruences,
)


def ring_arcs(n):
    return [(f"u{i}", f"u{i % n + 1}") for i in range(1, n + 1)]


# -- design ------------------------------------------------------------------

def test_example_7_1_ring_labels_preserve_all_paths():
    g = directed_ring_labeling(4)
    assert {arc: g.labels(*arc) for arc in ring_arcs(4)} == {
        ("u1", "u2"): [1, 5], ("u2", "u3"): [2, 6], ("u3", "u4"): [3, 7], ("u4", "u1"): [4, 8],
    }
    assert temporality(g) == 2 and temporal_cost(g) == 8


@pytest.mark.parametrize("n", [3, 4, 5, 6, 7])
def test_ring_labeling_preserves_all_paths(n):
    assert preserves_all_paths(directed_ring_labeling(n), ring_arcs(n))


def test_single_label_cannot_preserve_ring_paths():
    single = TemporalGraph.from_time_edges(
        ["u1", "u2", "u3", "u4"],
        [(u, v, i) for i, (u, v) in enumerate(ring_arcs(4), start=1)],
        directed=True,
    )
    assert not preserves_all_paths(single, ring_arcs(4))
    assert has_journey_along(single, ["u1", "u2", "u3"])
    assert not has_journey_along(single, ["u4", "u1", "u2"])


def test_exercise_7_1_dag_labeling():
    arcs = [("1", "2"), ("1", "3"), ("2", "4"), ("3", "4"), ("4", "5")]
    g = dag_labeling([str(i) for i in range(1, 6)], arcs)
    assert {arc: g.labels(*arc) for arc in arcs} == {
        ("1", "2"): [1], ("1", "3"): [1], ("2", "4"): [2], ("3", "4"): [3], ("4", "5"): [4],
    }
    assert preserves_all_paths(g, arcs) and temporality(g) == 1


@pytest.mark.parametrize("seed", range(10))
def test_random_dags_have_temporality_1(seed):
    rng = random.Random(seed)
    nodes = [str(i) for i in range(7)]
    arcs = [(nodes[i], nodes[j]) for i in range(7) for j in range(i + 1, 7) if rng.random() < 0.4]
    rng.shuffle(nodes)
    if arcs:
        assert preserves_all_paths(dag_labeling(nodes, arcs), arcs)


def test_cycles_are_rejected_by_dag_labeling():
    with pytest.raises(ValueError, match="cycle"):
        topological_order(["a", "b"], [("a", "b"), ("b", "a")])


def test_example_7_6_and_exercise_7_2_reachability_labeling():
    three = reachability_labeling(["u1", "u2", "u3"], ring_arcs(3), root="u1")
    assert {arc: three.labels(*arc) for arc in ring_arcs(3)} == {
        ("u1", "u2"): [3], ("u2", "u3"): [1, 4], ("u3", "u1"): [2],
    }
    four = reachability_labeling([f"u{i}" for i in range(1, 5)], ring_arcs(4), root="u1")
    assert {arc: four.labels(*arc) for arc in ring_arcs(4)} == {
        ("u1", "u2"): [4], ("u2", "u3"): [1, 5], ("u3", "u4"): [2, 6], ("u4", "u1"): [3],
    }


@pytest.mark.parametrize("seed", range(15))
def test_reachability_labeling_on_random_strongly_connected_digraphs(seed):
    rng = random.Random(seed)
    n = rng.randint(7, 10)
    nodes = [str(i) for i in range(n)]
    arcs = set(ring for ring in zip(nodes, nodes[1:] + nodes[:1]))
    while len(arcs) < 2 * n:
        u, v = rng.sample(nodes, 2)
        if (v, u) not in arcs:
            arcs.add((u, v))
    g = reachability_labeling(nodes, sorted(arcs))
    assert temporality(g) <= 2
    assert preserves_reachability(g, sorted(arcs))


def test_reachability_labeling_requires_strong_connectivity():
    with pytest.raises(ValueError, match="strongly connected"):
        reachability_labeling(["a", "b"], [("a", "b")])


def test_simple_paths_and_arc_validation():
    assert sorted(map(tuple, simple_paths(["a", "b", "c"], [("a", "b"), ("b", "c")]))) == [
        ("a", "b"), ("a", "b", "c"), ("b", "c"),
    ]
    with pytest.raises(ValueError, match="undeclared"):
        list(simple_paths(["a"], [("a", "z")]))


# -- periodic ----------------------------------------------------------------

def test_example_9_2_coincidence():
    assert common_instants([(4, 3), (6, 5)], 4) == [11, 23, 35, 47]
    assert edges_coincide((4, 3), (6, 5))
    assert not edges_coincide((4, 3), (6, 4))


def test_first_common_positive_instant_is_lcm():
    for (a1, a2), lcm in {(4, 6): 12, (3, 7): 21, (12, 18): 36}.items():
        assert common_instants([(a1, 0), (a2, 0)], 2) == [0, lcm]


def test_example_9_4_congruence_systems():
    assert solve_congruences([(2, 3), (3, 5), (2, 7)]) == (23, 105)
    assert solve_congruences([(1, 4), (3, 6)]) == (9, 12)       # also Exercise 9.2
    assert solve_congruences([(1, 6), (4, 10), (7, 15)]) is None


def test_example_9_5_and_exercise_9_1():
    assert common_instants([(7, 15), (4, 3)], 3) == [15, 43, 71]
    assert common_instants([(6, 1), (9, 4)], 4) == [13, 31, 49, 67]


def test_next_availability_and_single_instant_edges():
    assert [next_availability((3, 4), t) for t in (-1, 4, 5)] == [4, 7, 7]
    assert next_availability((0, 5), 5) is None
    assert common_instants([(0, 9), (3, 0)]) == [9]
    assert common_instants([(0, 9), (0, 8)]) == []
    with pytest.raises(ValueError):
        common_instants([(-1, 2)])


@pytest.mark.parametrize("seed", range(20))
def test_linear_foremost_matches_materialized_graph(seed):
    rng = random.Random(seed)
    nodes = [str(i) for i in range(6)]
    functions = {}
    for _ in range(8):
        u, v = rng.sample(nodes, 2)
        functions[(min(u, v), max(u, v))] = (rng.randint(0, 6), rng.randint(0, 9))
    lifetime = 80
    try:
        materialized = linear_availability_graph(nodes, functions, lifetime)
    except ValueError:
        pytest.skip("random functions collide on an instant")
    expected = earliest_arrival(materialized, "0", -1)
    assert linear_earliest_arrival(nodes, functions, "0", -1, lifetime=lifetime) == expected
