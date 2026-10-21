"""Deterministic families of temporal graphs from the literature.

Instants start at 1. ``rounds`` is the lifetime to materialize; periodic
families repeat with the period noted in each docstring.
"""

from __future__ import annotations

from typing import List

from .graph import Edge, TemporalGraph


def _check(n: int, minimum: int, even: bool = False) -> None:
    if n < minimum:
        raise ValueError(f"n must be >= {minimum}")
    if even and n % 2:
        raise ValueError("n must be even")


def _check_rounds(rounds: int) -> None:
    if rounds < 1:
        raise ValueError("rounds must be >= 1")


def moving_star(n: int, rounds: int) -> TemporalGraph:
    """Star whose centre walks through ``u1 .. u{n-1}`` cyclically, never ``u{n}``.

    Every snapshot is connected with diameter 2, yet the temporal diameter is
    ``n - 1``. Period ``n - 1``.
    """
    _check(n, 3)
    _check_rounds(rounds)
    nodes = [f"u{i}" for i in range(1, n + 1)]
    graph = TemporalGraph(nodes)
    for t in range(1, rounds + 1):
        center = nodes[(t - 1) % (n - 1)]
        graph.add_snapshot(t, [Edge(center, other) for other in nodes if other != center])
    return graph


def alternating_matchings(n: int, rounds: int) -> TemporalGraph:
    """Ring of ``n`` nodes split into two perfect matchings A and B that alternate.

    A (odd instants) holds ``{1,2}, {3,4}, ...``; B (even instants) the rest.
    Every snapshot is disconnected, yet the temporal diameter is ``n / 2``.
    """
    _check(n, 4, even=True)
    _check_rounds(rounds)
    nodes = [str(i) for i in range(1, n + 1)]
    matching_a = [Edge(str(i), str(i + 1)) for i in range(1, n, 2)]
    matching_b = [Edge(str(i), str(i + 1)) for i in range(2, n, 2)] + [Edge(str(n), "1")]
    graph = TemporalGraph(nodes)
    for t in range(1, rounds + 1):
        graph.add_snapshot(t, matching_a if t % 2 else matching_b)
    return graph


def soifer_graph(n: int, rounds: int) -> TemporalGraph:
    """Soifer's edge colouring of K_n: every snapshot is a perfect matching and
    every edge reappears exactly every ``n - 1`` instants.

    Nodes ``1 .. n``; node ``n`` sits at the centre of an (n-1)-gon. At
    instant ``t`` with ``m(j) = ((t - 1 + j) mod (n - 1)) + 1`` the edges are
    ``{n, m(0)}`` and ``{m(-i), m(i)}`` for ``i = 1 .. n/2 - 1``.
    """
    _check(n, 4, even=True)
    _check_rounds(rounds)
    graph = TemporalGraph([str(i) for i in range(1, n + 1)])
    for t in range(1, rounds + 1):
        def m(j: int) -> str:
            return str(((t - 1 + j) % (n - 1)) + 1)

        edges = [Edge(str(n), m(0))] + [Edge(m(-i), m(i)) for i in range(1, n // 2)]
        graph.add_snapshot(t, edges)
    return graph


def rotating_center_star(n: int, rounds: int) -> TemporalGraph:
    """Star where ``n/2`` nodes ``c0, c1, ...`` take turns as the centre while
    the ``n/2`` nodes ``l0, l1, ...`` stay leaves.

    Continuously connected, but exploring it from a leaf takes ``(n/2)²``
    instants: to hop between leaves the walker must wait for the same ``c``
    node to become the centre again. Period ``n / 2``.
    """
    _check(n, 4, even=True)
    _check_rounds(rounds)
    half = n // 2
    centers = [f"c{i}" for i in range(half)]
    leaves = [f"l{i}" for i in range(half)]
    nodes: List[str] = centers + leaves
    graph = TemporalGraph(nodes)
    for t in range(1, rounds + 1):
        center = centers[(t - 1) % half]
        graph.add_snapshot(t, [Edge(center, other) for other in nodes if other != center])
    return graph
