"""Disjoint journeys and separators: the temporal versions of Menger's theorem.

- Out-disjoint journeys (never leaving the same node at the same instant)
  versus departure times: equal for every temporal graph (Mertzios, Michail,
  Chatzigiannakis and Spirakis), computed by max-flow on the static expansion.
- Edge-disjoint journeys versus removed edges: equal for single-label graphs
  (Berman), also by max-flow.
- Node-disjoint journeys: the equality fails and the problem is NP-hard, so
  only an exhaustive search for small graphs is offered.

All journeys here are strict.
"""

from __future__ import annotations

from typing import Hashable, List, Optional, Set, Tuple

from ._flow import FlowNetwork
from .graph import TemporalGraph
from .journeys import Journey, _check_nodes, arcs_by_instant, enumerate_journeys

Departure = Tuple[str, int]


def _levels(graph: TemporalGraph) -> Optional[Tuple[int, int]]:
    groups = arcs_by_instant(graph)
    return (groups[0][0] - 1, groups[-1][0]) if groups else None


def _departure_network(
    graph: TemporalGraph, source: str, target: str
) -> Tuple[FlowNetwork[Hashable], Hashable, Hashable]:
    levels = _levels(graph)
    assert levels is not None
    first, last = levels
    unbounded = graph.label_count * 2 + 1
    network: FlowNetwork[Hashable] = FlowNetwork()
    for node in graph.nodes:
        for i in range(first + 1, last + 1):
            network.add_arc((node, i - 1), (node, i), unbounded)
    for t, arcs in arcs_by_instant(graph):
        for a, b in arcs:
            gate = ("departure", a, t)
            if gate not in network.capacity:
                network.add_arc((a, t - 1), gate, 1)
            network.add_arc(gate, (b, t), 1)
    return network, (source, first), (target, last)


def max_out_disjoint_journeys(graph: TemporalGraph, source: str, target: str) -> int:
    """Maximum number of journeys from ``source`` to ``target`` that never leave
    the same node at the same instant."""
    _check_nodes(graph, source, target)
    if source == target:
        raise ValueError("source and target must differ")
    if _levels(graph) is None:
        return 0
    network, s, z = _departure_network(graph, source, target)
    return network.max_flow(s, z)


def min_departure_separator(graph: TemporalGraph, source: str, target: str) -> Set[Departure]:
    """A smallest set of departure times ``(node, t)`` whose removal (dropping
    every edge leaving ``node`` at ``t``) leaves no journey from ``source`` to
    ``target``. Its size equals :func:`max_out_disjoint_journeys`."""
    _check_nodes(graph, source, target)
    if source == target:
        raise ValueError("source and target must differ")
    if _levels(graph) is None:
        return set()
    network, s, z = _departure_network(graph, source, target)
    network.max_flow(s, z)
    side = network.source_side(s)
    cut: Set[Departure] = set()
    for t, arcs in arcs_by_instant(graph):
        for a, b in arcs:
            gate = ("departure", a, t)
            gate_in = (a, t - 1) in side and gate not in side
            gate_out = gate in side and (b, t) not in side
            if gate_in or gate_out:
                cut.add((a, t))
    return cut


def _single_label_edges(graph: TemporalGraph) -> None:
    seen: Set[Tuple[str, str]] = set()
    for edge in graph.time_edges():
        key = (edge.u, edge.v) if edge.u <= edge.v else (edge.v, edge.u)
        if key in seen:
            raise ValueError(
                f"Edge {key} has several labels; edge-disjoint Menger needs single labels"
            )
        seen.add(key)


def _edge_network(
    graph: TemporalGraph, source: str, target: str
) -> Tuple[FlowNetwork[Hashable], Hashable, Hashable]:
    levels = _levels(graph)
    assert levels is not None
    first, last = levels
    unbounded = graph.label_count * 2 + 1
    network: FlowNetwork[Hashable] = FlowNetwork()
    for node in graph.nodes:
        for i in range(first + 1, last + 1):
            network.add_arc((node, i - 1), (node, i), unbounded)
    for edge in graph.time_edges():
        entry, exit_ = ("edge-in", edge.u, edge.v), ("edge-out", edge.u, edge.v)
        network.add_arc(entry, exit_, 1)
        network.add_arc((edge.u, edge.t - 1), entry, unbounded)
        network.add_arc(exit_, (edge.v, edge.t), unbounded)
        if not edge.directed:
            network.add_arc((edge.v, edge.t - 1), entry, unbounded)
            network.add_arc(exit_, (edge.u, edge.t), unbounded)
    return network, (source, first), (target, last)


def max_edge_disjoint_journeys(graph: TemporalGraph, source: str, target: str) -> int:
    """Maximum number of journeys sharing no edge. Requires single-label edges."""
    _check_nodes(graph, source, target)
    if source == target:
        raise ValueError("source and target must differ")
    _single_label_edges(graph)
    if _levels(graph) is None:
        return 0
    network, s, z = _edge_network(graph, source, target)
    return network.max_flow(s, z)


def min_edge_separator(graph: TemporalGraph, source: str, target: str) -> Set[Tuple[str, str]]:
    """A smallest set of edges whose removal leaves no journey (single labels)."""
    _check_nodes(graph, source, target)
    if source == target:
        raise ValueError("source and target must differ")
    _single_label_edges(graph)
    if _levels(graph) is None:
        return set()
    network, s, z = _edge_network(graph, source, target)
    network.max_flow(s, z)
    side = network.source_side(s)
    return {
        (edge.u, edge.v)
        for edge in graph.time_edges()
        if ("edge-in", edge.u, edge.v) in side and ("edge-out", edge.u, edge.v) not in side
    }


def max_node_disjoint_journeys(
    graph: TemporalGraph, source: str, target: str, limit: int = 100_000
) -> List[Journey]:
    """A largest set of journeys with pairwise disjoint internal nodes.

    NP-hard in general: enumerates all journeys (at most ``limit``, else
    ``ValueError``) and searches exhaustively. A direct ``source``-``target``
    edge counts once, whatever instants it has.
    """
    journeys: List[Journey] = []
    direct_seen = False
    for journey in enumerate_journeys(graph, source, target):
        if journey.hops == 1:
            if direct_seen:
                continue
            direct_seen = True
        journeys.append(journey)
        if len(journeys) > limit:
            raise ValueError(f"More than {limit} journeys; graph too large for exact search")
    interiors = [frozenset(j.nodes[1:-1]) for j in journeys]
    best: List[int] = []

    def search(index: int, chosen: List[int], used: Set[str]) -> None:
        nonlocal best
        if len(chosen) + (len(journeys) - index) <= len(best):
            return
        if index == len(journeys):
            best = list(chosen)
            return
        if not interiors[index] & used:
            chosen.append(index)
            search(index + 1, chosen, used | interiors[index])
            chosen.pop()
        search(index + 1, chosen, used)

    search(0, [], set())
    return [journeys[i] for i in best]
