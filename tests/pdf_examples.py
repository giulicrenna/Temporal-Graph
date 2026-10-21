"""Worked examples from "Grafos temporales: una introducción desde la
perspectiva algorítmica" (Crenna, 2026), used as fixtures."""

from temporal_graph import TemporalGraph


def figure_2():
    """Menger counterexample: single labels, s = u1, z = u5."""
    return TemporalGraph.from_time_edges(
        ["u1", "u2", "u3", "u4", "u5"],
        [("u1", "u2", 5), ("u1", "u3", 1), ("u2", "u3", 2), ("u2", "u4", 6),
         ("u2", "u5", 3), ("u3", "u4", 4), ("u4", "u5", 7)],
    )


def example_2_6():
    return TemporalGraph.from_time_edges(
        list("abcd"), [("a", "b", 1), ("b", "c", 2), ("c", "d", 3), ("a", "c", 3)]
    )


def example_2_2():
    return TemporalGraph.from_time_edges(list("ABC"), [("A", "B", 2), ("B", "C", 1)])


def example_4_3():
    return TemporalGraph.from_time_edges(
        ["u1", "u2", "u3", "u4"],
        [("u1", "u2", 1), ("u1", "u2", 2), ("u2", "u4", 2), ("u2", "u4", 3),
         ("u1", "u3", 3), ("u2", "u3", 3), ("u3", "u4", 4), ("u3", "u4", 5)],
        directed=True,
    )
