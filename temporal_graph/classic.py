"""Temporal versions of classic problems, solved exactly for small instances.

Temporal matching, exploration and the temporal travelling salesman are
NP-hard (or worse to approximate), so these are exponential searches meant
for experiments and for checking hand-made examples. All are strict.
"""

from __future__ import annotations

import bisect
import heapq
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Tuple

from .graph import TemporalGraph
from .journeys import Step, _check_nodes, _default_start, arcs_by_instant, traversal_labels

TimeEdgeChoice = Tuple[str, str, int]


def max_temporal_matching(graph: TemporalGraph) -> List[TimeEdgeChoice]:
    """A largest set of edges, each with one of its instants, such that no two
    share an endpoint and no two use the same instant."""
    options: Dict[Tuple[str, str], List[int]] = {}
    for edge in graph.time_edges():
        key = (edge.u, edge.v) if edge.u <= edge.v else (edge.v, edge.u)
        options.setdefault(key, []).append(edge.t)
    edges = sorted(options)
    best: List[TimeEdgeChoice] = []

    def search(
        index: int, chosen: List[TimeEdgeChoice], nodes: FrozenSet[str], instants: FrozenSet[int]
    ) -> None:
        nonlocal best
        free = len(graph.nodes) - len(nodes)
        if len(chosen) + min(len(edges) - index, free // 2) <= len(best):
            return
        if index == len(edges):
            best = list(chosen)
            return
        u, v = edges[index]
        if u not in nodes and v not in nodes:
            for t in options[(u, v)]:
                if t not in instants:
                    chosen.append((u, v, t))
                    search(index + 1, chosen, nodes | {u, v}, instants | {t})
                    chosen.pop()
        search(index + 1, chosen, nodes, instants)

    search(0, [], frozenset(), frozenset())
    return best


@dataclass(frozen=True)
class Exploration:
    finish: int          # instant at which the last new node is reached
    walk: List[Step]     # edges crossed, revisits allowed


def temporal_exploration(
    graph: TemporalGraph, start_node: str, start: Optional[int] = None, max_nodes: int = 20
) -> Optional[Exploration]:
    """Fastest walk from ``start_node`` that visits every node (waiting and
    revisiting allowed), or ``None`` if impossible within the lifetime.

    Dijkstra over ``(node, visited set)`` states: O(2^n · n · deg · log).
    """
    _check_nodes(graph, start_node)
    nodes = graph.nodes
    if len(nodes) > max_nodes:
        raise ValueError(f"Exact exploration limited to {max_nodes} nodes")
    bit = {node: 1 << i for i, node in enumerate(nodes)}
    everyone = (1 << len(nodes)) - 1
    labels = traversal_labels(graph)
    outgoing: Dict[str, List[Tuple[str, List[int]]]] = {n: [] for n in nodes}
    for (a, b), instants in labels.items():
        outgoing[a].append((b, instants))

    begin = _default_start(graph, start, strict=True)
    origin = (start_node, bit[start_node])
    best: Dict[Tuple[str, int], int] = {origin: begin}
    parent: Dict[Tuple[str, int], Optional[Tuple[Tuple[str, int], Step]]] = {origin: None}
    queue: List[Tuple[int, str, int]] = [(begin, start_node, bit[start_node])]
    while queue:
        t, node, mask = heapq.heappop(queue)
        state = (node, mask)
        if best.get(state) != t:
            continue
        if mask == everyone:
            walk: List[Step] = []
            link = parent[state]
            while link is not None:
                previous, step = link
                walk.append(step)
                link = parent[previous]
            return Exploration(t, list(reversed(walk)))
        for nxt, instants in outgoing[node]:
            index = bisect.bisect_right(instants, t)
            if index == len(instants):
                continue
            when = instants[index]
            new_state = (nxt, mask | bit[nxt])
            if when < best.get(new_state, when + 1):
                best[new_state] = when
                parent[new_state] = (state, (node, nxt, when))
                heapq.heappush(queue, (when, nxt, mask | bit[nxt]))
    return None


@dataclass(frozen=True)
class Tour:
    cost: float
    steps: List[Step]


def temporal_tsp(
    graph: TemporalGraph, start_node: str, start: Optional[int] = None, max_nodes: int = 12
) -> Optional[Tour]:
    """Cheapest temporal Hamiltonian cycle from ``start_node``.

    Visits every other node exactly once and returns, crossing edges at
    strictly increasing instants; the cost of crossing an edge at ``t`` is its
    weight in that snapshot (so TTSP(1, 2) uses weights 1 and 2). Keeps the
    Pareto front of (instant, cost) per ``(visited set, node)``.
    """
    _check_nodes(graph, start_node)
    nodes = graph.nodes
    if len(nodes) > max_nodes:
        raise ValueError(f"Exact TSP limited to {max_nodes} nodes")
    if len(nodes) < 3:
        raise ValueError("A tour needs at least 3 nodes")
    bit = {node: 1 << i for i, node in enumerate(nodes)}
    everyone = (1 << len(nodes)) - 1
    weight: Dict[Tuple[str, str, int], float] = {}
    for edge in graph.time_edges():
        weight[(edge.u, edge.v, edge.t)] = edge.weight
        if not edge.directed:
            weight[(edge.v, edge.u, edge.t)] = edge.weight

    Label = Tuple[int, float, Tuple[Step, ...]]
    fronts: Dict[Tuple[int, str], List[Label]] = {
        (bit[start_node], start_node): [(_default_start(graph, start, True), 0.0, ())]
    }
    best: Optional[Tour] = None
    for t, arcs in arcs_by_instant(graph):
        additions: List[Tuple[Tuple[int, str], Label]] = []
        for a, b in arcs:
            cost = weight[(a, b, t)]
            for (mask, node), labels in fronts.items():
                if node != a:
                    continue
                closing = b == start_node and mask == everyone
                if not closing and mask & bit[b]:
                    continue
                for ready, spent, steps in labels:
                    if ready >= t:
                        continue
                    total = spent + cost
                    path = steps + ((a, b, t),)
                    if closing:
                        if best is None or total < best.cost:
                            best = Tour(total, list(path))
                    else:
                        additions.append(((mask | bit[b], b), (t, total, path)))
        for key, label in additions:
            front = fronts.setdefault(key, [])
            if any(r <= label[0] and c <= label[1] for r, c, _ in front):
                continue
            front[:] = [x for x in front if not (label[0] <= x[0] and label[1] <= x[1])]
            front.append(label)
    return best
