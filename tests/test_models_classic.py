import pytest

from temporal_graph import Edge, TemporalGraph
from temporal_graph.classic import max_temporal_matching, temporal_exploration, temporal_tsp
from temporal_graph.dissemination import flooding_times, harmonic_potential, k_token_dissemination
from temporal_graph.generators import (
    alternating_matchings,
    moving_star,
    rotating_center_star,
    soifer_graph,
)
from temporal_graph.journeys import earliest_arrival
from temporal_graph.random_models import (
    expected_journey_count,
    foremost_within_two_probability,
    path_journey_probability,
    random_temporal_graph,
)

# -- generators --------------------------------------------------------------

def test_soifer_snapshots_are_perfect_matchings_with_period_n_minus_1():
    g = soifer_graph(8, 14)
    for _, edges in g.snapshots():
        assert len(edges) == 4
        assert len({n for e in edges for n in e.key()}) == 8
    keys = {e.key() for t in range(1, 8) for e in g.edges_at(t)}
    assert len(keys) == 28
    assert all(len(g.labels(*key)) == 2 and g.labels(*key)[1] - g.labels(*key)[0] == 7
               for key in keys)


def test_generator_validation():
    with pytest.raises(ValueError):
        alternating_matchings(5, 3)
    with pytest.raises(ValueError):
        moving_star(2, 3)
    with pytest.raises(ValueError):
        soifer_graph(8, 0)


# -- random model ------------------------------------------------------------

def test_formula_5_values():
    assert path_journey_probability(2, 10) == pytest.approx(0.45)
    assert path_journey_probability(4, 8) == pytest.approx(0.01709, abs=1e-5)
    assert path_journey_probability(6, 20) == pytest.approx(0.00061, abs=1e-5)


def test_formula_6_values():
    assert expected_journey_count(8, 3, 6) == pytest.approx(155.56, abs=0.01)
    assert expected_journey_count(7, 3, 5) == pytest.approx(67.20, abs=0.01)
    assert expected_journey_count(9, 4, 9) == pytest.approx(290.37, abs=0.01)


@pytest.mark.parametrize(
    "n, r, value",
    [(20, 5, 0.7122), (50, 7, 0.7345), (100, 10, 0.7012), (100, 25, 0.2136), (400, 20, 0.6677)],
)
def test_formula_7_values(n, r, value):
    assert foremost_within_two_probability(n, r) == pytest.approx(value, abs=1e-4)


def test_formula_7_against_simulation():
    trials = 400
    hits = sum(
        earliest_arrival(random_temporal_graph(20, 5, seed=s), "v1", 0).get("v2", 99) <= 2
        for s in range(trials)
    )
    assert hits / trials == pytest.approx(foremost_within_two_probability(20, 5), abs=0.06)


@pytest.mark.parametrize(
    "call",
    [
        lambda: random_temporal_graph(1, 3),
        lambda: path_journey_probability(0, 3),
        lambda: expected_journey_count(4, 4, 3),
        lambda: foremost_within_two_probability(5, 1),
        lambda: harmonic_potential(0),
    ],
)
def test_model_parameter_validation(call):
    with pytest.raises(ValueError):
        call()


def test_random_graph_is_a_single_label_clique_and_reproducible():
    g = random_temporal_graph(6, 4, seed=7)
    assert g.label_count == 15
    assert all(1 <= e.t <= 4 for e in g.time_edges())
    assert g.time_edges() == random_temporal_graph(6, 4, seed=7).time_edges()


# -- classic problems --------------------------------------------------------

def test_example_8_2_temporal_matching():
    one_label = TemporalGraph.from_time_edges(
        list("abcd"), [("a", "b", 1), ("c", "d", 1), ("b", "c", 2), ("d", "a", 2)]
    )
    assert len(max_temporal_matching(one_label)) == 1
    two_labels = TemporalGraph.from_time_edges(
        list("abcd"),
        [("a", "b", 1), ("a", "b", 2), ("c", "d", 1), ("c", "d", 2), ("b", "c", 2), ("d", "a", 2)],
    )
    matching = max_temporal_matching(two_labels)
    assert len(matching) == 2 and len({t for _, _, t in matching}) == 2


@pytest.mark.parametrize("n", [6, 8, 10])
def test_figure_7_exploration_time_is_half_n_squared(n):
    result = temporal_exploration(rotating_center_star(n, 4 * n * n), "l0", 0)
    assert result.finish == (n // 2) ** 2
    visited = {"l0"} | {to for _, to, _ in result.walk}
    assert len(visited) == n
    instants = [t for _, _, t in result.walk]
    assert instants == sorted(instants) and len(set(instants)) == len(instants)


def test_exploration_impossible_and_limits():
    g = TemporalGraph.from_time_edges(list("abc"), [("a", "b", 1)])
    assert temporal_exploration(g, "a") is None
    with pytest.raises(ValueError, match="limited"):
        temporal_exploration(moving_star(6, 5), "u1", max_nodes=5)


def test_temporal_tsp_picks_cheap_instants():
    nodes = list("abc")
    g = TemporalGraph(nodes)
    costs = {1: (2, 1, 1), 2: (1, 2, 2), 3: (1, 1, 1)}  # (ab, bc, ac) per instant
    for t, (ab, bc, ac) in costs.items():
        g.add_snapshot(t, [Edge("a", "b", weight=ab), Edge("b", "c", weight=bc),
                           Edge("a", "c", weight=ac)])
    # Three edges need instants 1, 2, 3: a-c(1) + c-b(2) + b-a(1) = 4 beats a-b-c-a = 5.
    tour = temporal_tsp(g, "a")
    assert tour.cost == 4
    assert tour.steps == [("a", "c", 1), ("c", "b", 2), ("b", "a", 3)]
    assert temporal_tsp(TemporalGraph.from_time_edges(nodes, [("a", "b", 1)]), "a") is None


# -- dissemination -----------------------------------------------------------

def test_exercise_5_1_potential():
    assert 16 * harmonic_potential(16) == pytest.approx(54.1, abs=0.05)
    assert harmonic_potential(16) == pytest.approx(3.381, abs=1e-3)


def test_single_token_reaches_everyone_within_n_minus_1_on_continuously_connected():
    g = moving_star(8, 20)
    for source in g.nodes:
        times = flooding_times(g, [source], 0)
        assert len(times) == 8 and max(times.values()) <= 7  # Exercise 5.2


def test_k_token_forwarding_completes_and_reports_progress():
    g = soifer_graph(8, 80)
    result = k_token_dissemination(g, {str(i): {i} for i in range(1, 9)})
    assert result.completion is not None
    assert all(known == frozenset(range(1, 9)) for known in result.knowledge.values())
    totals = [total for _, total in result.progress]
    assert totals == sorted(totals) and totals[-1] == 64


def test_k_token_policies_and_timeout():
    g = alternating_matchings(6, 4)
    stuck = k_token_dissemination(g, {"1": {"x"}}, rounds=2)
    assert stuck.completion is None
    seeded = k_token_dissemination(soifer_graph(6, 40), {"1": {"a"}, "2": {"b"}},
                                   policy="random", seed=1)
    assert seeded == k_token_dissemination(soifer_graph(6, 40), {"1": {"a"}, "2": {"b"}},
                                           policy="random", seed=1)
    silent = k_token_dissemination(soifer_graph(6, 10), {"1": {"a"}},
                                   policy=lambda node, known, t: None)
    assert silent.completion is None
    with pytest.raises(ValueError, match="policy"):
        k_token_dissemination(g, {"1": {"a"}}, policy="loud")
