"""Tour of the algorithms on the worked examples of the temporal-graphs notes.

Run from the repo root with::

    python examples/temporal_algorithms.py

Prints journeys, connectivity metrics, Menger quantities, labelings,
periodic coincidences, random-model formulas and exact classic problems,
and saves an animation of the moving-star graph to ``output/moving_star.gif``.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from temporal_graph import TemporalGraph, animate  # noqa: E402
from temporal_graph import (  # noqa: E402
    classic,
    connectivity,
    design,
    flows,
    generators,
    journeys,
    periodic,
    random_models,
)


def figure_2() -> TemporalGraph:
    return TemporalGraph.from_time_edges(
        ["u1", "u2", "u3", "u4", "u5"],
        [("u1", "u2", 5), ("u1", "u3", 1), ("u2", "u3", 2), ("u2", "u4", 6),
         ("u2", "u5", 3), ("u3", "u4", 4), ("u4", "u5", 7)],
    )


def section(title: str) -> None:
    print(f"\n== {title}")


def main() -> None:
    g = figure_2()

    section("Journeys (figure 2, from u1 at t=0)")
    print("earliest arrival:", journeys.earliest_arrival(g, "u1", 0))
    print("foremost u1->u5: ", journeys.foremost_journey(g, "u1", "u5", 0))
    print("fastest  u1->u5: ", journeys.fastest_journey(g, "u1", "u5"))
    print("shortest u1->u4: ", journeys.shortest_journey(g, "u1", "u4"))
    print("latest departure to u5:", journeys.latest_departure(g, "u5"))
    print("all journeys u1->u5:")
    for journey in journeys.enumerate_journeys(g, "u1", "u5"):
        print("   ", journey)

    section("Menger (figure 2)")
    print("node-disjoint:", len(flows.max_node_disjoint_journeys(g, "u1", "u5")))
    print("out-disjoint: ", flows.max_out_disjoint_journeys(g, "u1", "u5"),
          "separator", sorted(flows.min_departure_separator(g, "u1", "u5")))
    print("edge-disjoint:", flows.max_edge_disjoint_journeys(g, "u1", "u5"))

    section("Connectivity metrics, n = 8 (table 4)")
    for name, family in (("moving star", generators.moving_star),
                         ("alternating matchings", generators.alternating_matchings),
                         ("Soifer", generators.soifer_graph)):
        graph = family(8, 40)
        print(f"{name:>22}: ct={connectivity.connectivity_time(graph)} "
              f"oit={connectivity.outgoing_influence_time(graph)} "
              f"d={connectivity.temporal_diameter(graph)}")

    section("Design")
    ring = design.directed_ring_labeling(4)
    arcs = [("u1", "u2"), ("u2", "u3"), ("u3", "u4"), ("u4", "u1")]
    print("ring labels:", {arc: ring.labels(*arc) for arc in arcs},
          "preserves all paths:", design.preserves_all_paths(ring, arcs))
    tree = design.reachability_labeling([f"u{i}" for i in range(1, 5)], arcs, root="u1")
    print("reachability labeling:", {arc: tree.labels(*arc) for arc in arcs},
          "temporality:", design.temporality(tree))

    section("Periodic availability a*x + b")
    print("4x+3 and 6x+5 meet at:", periodic.common_instants([(4, 3), (6, 5)], 4))
    print("t = 2 mod 3, 3 mod 5, 2 mod 7:",
          periodic.solve_congruences([(2, 3), (3, 5), (2, 7)]))

    section("Random temporal graphs")
    print("P(journey on a path, k=2, r=10) =", random_models.path_journey_probability(2, 10))
    print("E[journeys of length 3], n=8, r=6 =",
          round(random_models.expected_journey_count(8, 3, 6), 2))
    print("P(foremost by t=2), n=20, r=5 =",
          round(random_models.foremost_within_two_probability(20, 5), 4))

    section("Classic problems, exact")
    star = generators.rotating_center_star(8, 100)
    exploration = classic.temporal_exploration(star, "l0", 0)
    assert exploration is not None
    print("exploration of the rotating star from l0 finishes at", exploration.finish)

    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    path = animate(generators.moving_star(6, 10), frame_duration=500).save(
        out_dir / "moving_star.gif", scale=1.0
    )
    print("\nanimation:", Path(path).relative_to(ROOT))


if __name__ == "__main__":
    main()
