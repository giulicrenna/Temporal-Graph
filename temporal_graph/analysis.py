"""Structural analysis of a :class:`~temporal_graph.graph.TemporalGraph`."""

from __future__ import annotations

from typing import Dict, Iterable, List, Set, Tuple

from .graph import Edge, TemporalGraph


def degree_timeline(graph: TemporalGraph, node: str) -> Dict[int, int]:
    """Number of edges incident to ``node`` at every recorded timestep.

    Edge direction is ignored: a directed edge counts for both endpoints.
    """
    if node not in graph.nodes:
        raise ValueError(f"Node {node!r} is not declared in the graph")
    return {
        t: sum(1 for e in edges if node in (e.u, e.v))
        for t, edges in graph.snapshots()
    }


def connected_components_at(graph: TemporalGraph, t: int) -> List[Set[str]]:
    """Connected components at timestep ``t``, ignoring edge direction.

    Isolated nodes are returned as singleton components. Components are
    ordered by the position of their first node in ``graph.nodes``.
    """
    parent = {n: n for n in graph.nodes}

    def find(n: str) -> str:
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n

    for edge in graph.edges_at(t):
        root_u, root_v = find(edge.u), find(edge.v)
        if root_u != root_v:
            parent[root_v] = root_u

    groups: Dict[str, Set[str]] = {}
    for n in graph.nodes:
        groups.setdefault(find(n), set()).add(n)
    order = {n: i for i, n in enumerate(graph.nodes)}
    return sorted(groups.values(), key=lambda g: min(order[n] for n in g))


def edge_persistence(graph: TemporalGraph) -> Dict[Tuple[str, str], float]:
    """Fraction of recorded snapshots in which each edge is present."""
    snapshots = graph.snapshots()
    if not snapshots:
        return {}
    counts: Dict[Tuple[str, str], int] = {}
    for _, edges in snapshots:
        for e in edges:
            counts[e.key()] = counts.get(e.key(), 0) + 1
    return {key: n / len(snapshots) for key, n in sorted(counts.items())}


def is_temporally_acyclic(graph: TemporalGraph) -> bool:
    """True if the directed edges of every snapshot form a DAG.

    Undirected edges are ignored.
    """
    return all(_is_dag(edges) for _, edges in graph.snapshots())


def _is_dag(edges: Iterable[Edge]) -> bool:
    successors: Dict[str, List[str]] = {}
    indegree: Dict[str, int] = {}
    for e in edges:
        if not e.directed:
            continue
        successors.setdefault(e.u, []).append(e.v)
        indegree[e.v] = indegree.get(e.v, 0) + 1
        indegree.setdefault(e.u, 0)

    ready = [n for n, d in indegree.items() if d == 0]
    visited = 0
    while ready:
        n = ready.pop()
        visited += 1
        for m in successors.get(n, []):
            indegree[m] -= 1
            if indegree[m] == 0:
                ready.append(m)
    return visited == len(indegree)
