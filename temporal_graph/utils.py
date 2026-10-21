"""Helpers to build and transform :class:`~temporal_graph.graph.TemporalGraph`."""

from __future__ import annotations

from typing import Callable, Dict, Iterable, List, Sequence, Set, Tuple

from .graph import Edge, TemporalGraph


def from_edge_list(
    nodes: Sequence[str],
    snapshots: Dict[int, Iterable[Tuple[str, str]]],
) -> TemporalGraph:
    """Build a graph from ``{timestep: [(u, v), ...]}`` using default edges."""
    graph = TemporalGraph(nodes)
    for t in sorted(snapshots):
        graph.add_snapshot(t, [Edge(u, v) for u, v in snapshots[t]])
    return graph


def snapshot_diff(
    graph: TemporalGraph, t1: int, t2: int
) -> Tuple[List[Edge], List[Edge]]:
    """Return ``(added, removed)`` edges going from ``t1`` to ``t2``.

    ``added`` holds the edges of ``t2`` absent at ``t1``; ``removed`` holds the
    edges of ``t1`` absent at ``t2``. Both are sorted by edge key.
    """
    before = {e.key(): e for e in graph.edges_at(t1)}
    after = {e.key(): e for e in graph.edges_at(t2)}
    added = [after[k] for k in sorted(after.keys() - before.keys())]
    removed = [before[k] for k in sorted(before.keys() - after.keys())]
    return added, removed


def filter_edges(
    graph: TemporalGraph, predicate: Callable[[Edge], bool]
) -> TemporalGraph:
    """Return a new graph keeping only the edges for which ``predicate`` is true.

    Nodes and timesteps are preserved, so snapshots may become empty.
    """
    result = TemporalGraph(graph.nodes)
    for t, edges in graph.snapshots():
        result.add_snapshot(t, [e for e in edges if predicate(e)])
    return result


def subgraph(graph: TemporalGraph, nodes: Iterable[str]) -> TemporalGraph:
    """Return a new graph restricted to ``nodes``.

    Node order follows the original graph. Only edges with both endpoints in
    ``nodes`` are kept. Raises ``ValueError`` if a node is not in the graph or
    if no node remains.
    """
    wanted: Set[str] = set(nodes)
    unknown = wanted - set(graph.nodes)
    if unknown:
        raise ValueError(f"Nodes not in graph: {sorted(unknown)}")
    result = TemporalGraph([n for n in graph.nodes if n in wanted])
    for t, edges in graph.snapshots():
        result.add_snapshot(t, [e for e in edges if e.u in wanted and e.v in wanted])
    return result
