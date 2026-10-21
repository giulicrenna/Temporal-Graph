"""Instantaneous versus global connectivity (strict journeys throughout).

Instants run over the lifetime ``[λ_min, λ_max]`` of the edges; an instant
without a recorded snapshot has no edges. Snapshot connectivity treats every
edge as undirected.
"""

from __future__ import annotations

import itertools
import math
from typing import Dict, Iterable, List, Optional, Set, Tuple

from ._flow import FlowNetwork
from .graph import TemporalGraph
from .journeys import foremost_search

Key = Tuple[str, str]


def lifetime(graph: TemporalGraph) -> Optional[Tuple[int, int]]:
    """``(λ_min, λ_max)`` over instants with at least one edge, or ``None``."""
    used = [t for t, edges in graph.snapshots() if edges]
    return (used[0], used[-1]) if used else None


def _edge_keys(graph: TemporalGraph, t: int) -> Set[Key]:
    try:
        return {e.key() for e in graph.edges_at(t)}
    except KeyError:
        return set()


def _connected(nodes: List[str], keys: Iterable[Key]) -> bool:
    parent = {n: n for n in nodes}

    def find(n: str) -> str:
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n

    components = len(nodes)
    for u, v in keys:
        ru, rv = find(u), find(v)
        if ru != rv:
            parent[rv] = ru
            components -= 1
    return components == 1



# Snapshot properties


def is_continuously_connected(graph: TemporalGraph) -> bool:
    """True if the snapshot D(t) is connected at every instant of the lifetime."""
    span = lifetime(graph)
    nodes = graph.nodes
    if len(nodes) == 1:
        return True
    if span is None:
        return False
    return all(_connected(nodes, _edge_keys(graph, t)) for t in range(span[0], span[1] + 1))


def is_interval_connected(graph: TemporalGraph, window: int) -> bool:
    """T-interval connectivity: every ``window`` consecutive instants share a
    connected spanning subgraph, i.e. the edges present throughout connect V."""
    if window < 1:
        raise ValueError("window must be >= 1")
    span = lifetime(graph)
    nodes = graph.nodes
    if len(nodes) == 1:
        return True
    if span is None or span[1] - span[0] + 1 < window:
        return False
    for t in range(span[0], span[1] - window + 2):
        stable = set.intersection(*(_edge_keys(graph, i) for i in range(t, t + window)))
        if not _connected(nodes, stable):
            return False
    return True


def vertex_connectivity_at(graph: TemporalGraph, t: int) -> int:
    """Vertex connectivity κ of the snapshot at ``t`` (``n - 1`` for a clique)."""
    nodes = graph.nodes
    keys = _edge_keys(graph, t)
    if not _connected(nodes, keys):
        return 0
    adjacent = keys | {(v, u) for u, v in keys}
    best = len(nodes) - 1
    for u, v in itertools.combinations(nodes, 2):
        if (u, v) in adjacent:
            continue
        network: FlowNetwork[Tuple[str, str]] = FlowNetwork()
        for node in nodes:
            network.add_arc((node, "in"), (node, "out"), 1 if node not in (u, v) else len(nodes))
        for a, b in adjacent:
            network.add_arc((a, "out"), (b, "in"), len(nodes))
        best = min(best, network.max_flow((u, "out"), (v, "in")))
    return best


def is_f_connected(graph: TemporalGraph, f: int) -> bool:
    """True if every snapshot of the lifetime stays connected after removing
    any ``f - 1`` nodes (vertex connectivity >= ``f``). O(n² max-flows) each."""
    if f < 1:
        raise ValueError("f must be >= 1")
    span = lifetime(graph)
    if span is None:
        return len(graph.nodes) == 1
    return all(vertex_connectivity_at(graph, t) >= f for t in range(span[0], span[1] + 1))



# Global metrics


def connectivity_time(graph: TemporalGraph) -> Optional[int]:
    """ct: smallest ``k`` such that every window of ``k`` consecutive instants
    has a connected union. ``None`` if even the whole lifetime is not enough."""
    nodes = graph.nodes
    if len(nodes) == 1:
        return 1
    span = lifetime(graph)
    if span is None:
        return None
    lo, hi = span
    keys_by_t = {t: _edge_keys(graph, t) for t in range(lo, hi + 1)}

    def works(k: int) -> bool:
        for t in range(lo, hi - k + 2):
            union: Set[Key] = set()
            for i in range(t, t + k):
                union |= keys_by_t[i]
            if not _connected(nodes, union):
                return False
        return True

    age = hi - lo + 1
    if not works(age):
        return None
    low, high = 1, age
    while low < high:
        middle = (low + high) // 2
        if works(middle):
            high = middle
        else:
            low = middle + 1
    return low


def _arrivals_by_start(graph: TemporalGraph) -> Dict[Tuple[str, int], Dict[str, int]]:
    span = lifetime(graph)
    assert span is not None
    lo, hi = span
    return {
        (u, t): foremost_search(graph, {u: t})[0]
        for u in graph.nodes
        for t in range(lo - 1, hi)
    }


def temporal_diameter(graph: TemporalGraph) -> Optional[int]:
    """d: smallest ``d`` such that from every time-node ``(u, t)`` with
    ``λ_min - 1 <= t <= λ_max - d`` every node is reached within ``d``.
    ``None`` if no such ``d`` exists within the lifetime."""
    nodes = graph.nodes
    if len(nodes) == 1:
        return 0
    span = lifetime(graph)
    if span is None:
        return None
    lo, hi = span
    arrivals = _arrivals_by_start(graph)
    worst: Dict[int, float] = {}
    for (u, t), arrival in arrivals.items():
        far = max((arrival[v] - t if v in arrival else math.inf) for v in nodes)
        worst[t] = max(worst.get(t, 0), far)
    for d in range(1, hi - lo + 2):
        if all(worst[t] <= d for t in range(lo - 1, hi - d + 1)):
            return d
    return None


def future_set_sizes(graph: TemporalGraph, node: str, start: int) -> List[Tuple[int, int]]:
    """``[(t', |S_(node,start)(t')|)]`` for ``t'`` from ``start`` to λ_max: how
    many nodes a journey leaving ``node`` after ``start`` has reached by ``t'``."""
    span = lifetime(graph)
    end = span[1] if span else start
    arrival, _ = foremost_search(graph, {node: start})
    return [
        (t, sum(1 for reached in arrival.values() if reached <= t))
        for t in range(start, end + 1)
    ]


def outgoing_influence_time(graph: TemporalGraph) -> Optional[int]:
    """oit: smallest ``k`` such that, for every node and start, the future set
    gains a member every ``k`` instants until it covers V (checked while
    ``t' + k`` stays inside the lifetime). ``None`` if no ``k`` works."""
    nodes = graph.nodes
    n = len(nodes)
    if n == 1:
        return 1
    span = lifetime(graph)
    if span is None:
        return None
    lo, hi = span
    sizes: List[Tuple[int, Dict[int, int]]] = []
    for (_, t), arrival in _arrivals_by_start(graph).items():
        curve = {
            moment: sum(1 for reached in arrival.values() if reached <= moment)
            for moment in range(t, hi + 1)
        }
        sizes.append((t, curve))
    for k in range(1, hi - lo + 2):
        if all(
            curve[moment + k] >= min(curve[moment] + 1, n)
            for t, curve in sizes
            for moment in range(t, hi - k + 1)
        ):
            return k
    return None
