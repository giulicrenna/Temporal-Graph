"""Temporal design: label a static digraph so that journeys preserve its paths.

Arcs are ``(u, v)`` pairs of a static digraph; labelings come back as directed
:class:`~temporal_graph.graph.TemporalGraph` objects.
"""

from __future__ import annotations

import bisect
from collections import deque
from typing import Deque, Dict, Iterable, Iterator, List, Optional, Sequence, Set, Tuple

from .graph import Edge, TemporalGraph
from .journeys import reachable, traversal_labels

Arc = Tuple[str, str]


def _check_arcs(nodes: Sequence[str], arcs: Iterable[Arc]) -> List[Arc]:
    declared = set(nodes)
    result = []
    for u, v in arcs:
        if u not in declared or v not in declared:
            raise ValueError(f"Arc {(u, v)} uses an undeclared node")
        if u == v:
            raise ValueError(f"Self-loop {(u, v)} is not allowed")
        result.append((u, v))
    return result


def _from_labels(nodes: Sequence[str], labels: Dict[Arc, Set[int]]) -> TemporalGraph:
    by_t: Dict[int, List[Edge]] = {}
    for (u, v), instants in labels.items():
        for t in instants:
            by_t.setdefault(t, []).append(Edge(u, v, directed=True))
    graph = TemporalGraph(nodes)
    for t in sorted(by_t):
        edges = by_t[t]
        keys = [e.key() for e in edges]
        if len(keys) != len(set(keys)):
            raise ValueError(f"Opposite arcs share instant {t}; cannot store both")
        graph.add_snapshot(t, edges)
    return graph


def temporality(graph: TemporalGraph) -> int:
    """Maximum number of labels on a single edge."""
    counts: Dict[Tuple[str, str], int] = {}
    for _, edges in graph.snapshots():
        for edge in edges:
            counts[edge.key()] = counts.get(edge.key(), 0) + 1
    return max(counts.values(), default=0)


def temporal_cost(graph: TemporalGraph) -> int:
    """Total number of labels |λ|."""
    return graph.label_count



# Labelings


def topological_order(nodes: Sequence[str], arcs: Iterable[Arc]) -> List[str]:
    """Kahn's algorithm; ``ValueError`` if the digraph has a cycle."""
    arc_list = _check_arcs(nodes, arcs)
    indegree = {n: 0 for n in nodes}
    successors: Dict[str, List[str]] = {n: [] for n in nodes}
    for u, v in arc_list:
        successors[u].append(v)
        indegree[v] += 1
    ready: Deque[str] = deque(n for n in nodes if indegree[n] == 0)
    order: List[str] = []
    while ready:
        u = ready.popleft()
        order.append(u)
        for v in successors[u]:
            indegree[v] -= 1
            if indegree[v] == 0:
                ready.append(v)
    if len(order) != len(nodes):
        raise ValueError("The digraph has a cycle")
    return order


def dag_labeling(nodes: Sequence[str], arcs: Iterable[Arc]) -> TemporalGraph:
    """One label per arc, equal to the topological index of its origin.

    Every path then has strictly increasing labels: temporality 1.
    """
    arc_list = _check_arcs(nodes, arcs)
    index = {node: i for i, node in enumerate(topological_order(nodes, arc_list), start=1)}
    return _from_labels(nodes, {(u, v): {index[u]} for u, v in arc_list})


def directed_ring_labeling(n: int) -> TemporalGraph:
    """Ring ``u1 -> u2 -> ... -> un -> u1`` with labels ``{i, n + i}`` on arc ``i``.

    Preserves every simple path with temporality 2, which is optimal.
    """
    if n < 2:
        raise ValueError("n must be >= 2")
    nodes = [f"u{i}" for i in range(1, n + 1)]
    labels = {(nodes[i - 1], nodes[i % n]): {i, n + i} for i in range(1, n + 1)}
    return _from_labels(nodes, labels)


def _bfs_tree(root: str, neighbours: Dict[str, List[str]]) -> Dict[str, Tuple[str, int]]:
    """``{node: (parent, depth)}`` of a breadth-first tree from ``root``."""
    tree: Dict[str, Tuple[str, int]] = {}
    seen = {root}
    queue: Deque[Tuple[str, int]] = deque([(root, 0)])
    while queue:
        node, depth = queue.popleft()
        for nxt in neighbours.get(node, []):
            if nxt not in seen:
                seen.add(nxt)
                tree[nxt] = (node, depth + 1)
                queue.append((nxt, depth + 1))
    return tree


def reachability_labeling(
    nodes: Sequence[str], arcs: Iterable[Arc], root: Optional[str] = None
) -> TemporalGraph:
    """At most two labels per arc preserving every reachability of a strongly
    connected digraph.

    An in-tree towards ``root`` is labelled level by level from the leaves
    (1, 2, ..., h); an out-tree from ``root`` continues from the root down
    (h + 1, h + 2, ...). Every node reaches the root and the root reaches
    every node afterwards.
    """
    arc_list = _check_arcs(nodes, arcs)
    root = root if root is not None else nodes[0]
    if root not in nodes:
        raise ValueError(f"Root {root!r} is not a node")
    forward: Dict[str, List[str]] = {n: [] for n in nodes}
    backward: Dict[str, List[str]] = {n: [] for n in nodes}
    for u, v in arc_list:
        forward[u].append(v)
        backward[v].append(u)
    in_tree = _bfs_tree(root, backward)
    out_tree = _bfs_tree(root, forward)
    if len(in_tree) != len(nodes) - 1 or len(out_tree) != len(nodes) - 1:
        raise ValueError("The digraph is not strongly connected")

    labels: Dict[Arc, Set[int]] = {}
    height = max((depth for _, depth in in_tree.values()), default=0)
    for child, (parent, depth) in in_tree.items():
        labels.setdefault((child, parent), set()).add(height - depth + 1)
    for child, (parent, depth) in out_tree.items():
        labels.setdefault((parent, child), set()).add(height + depth)
    return _from_labels(nodes, labels)



# Checks


def simple_paths(nodes: Sequence[str], arcs: Iterable[Arc]) -> Iterator[List[str]]:
    """Every simple directed path with at least one arc (exponential)."""
    arc_list = _check_arcs(nodes, arcs)
    successors: Dict[str, List[str]] = {n: [] for n in nodes}
    for u, v in arc_list:
        successors[u].append(v)

    def extend(path: List[str], seen: Set[str]) -> Iterator[List[str]]:
        for nxt in successors[path[-1]]:
            if nxt not in seen:
                path.append(nxt)
                yield list(path)
                seen.add(nxt)
                yield from extend(path, seen)
                seen.discard(nxt)
                path.pop()

    for start in nodes:
        yield from extend([start], {start})


def has_journey_along(graph: TemporalGraph, path: Sequence[str]) -> bool:
    """True if the node sequence ``path`` can be crossed with increasing labels."""
    labels = traversal_labels(graph)
    current = float("-inf")
    for u, v in zip(path, path[1:]):
        instants = labels.get((u, v), [])
        index = bisect.bisect_right(instants, current)
        if index == len(instants):
            return False
        current = instants[index]
    return True


def preserves_all_paths(graph: TemporalGraph, arcs: Iterable[Arc]) -> bool:
    """True if every simple path of the digraph is realized by some journey."""
    return all(has_journey_along(graph, p) for p in simple_paths(graph.nodes, arcs))


def preserves_reachability(graph: TemporalGraph, arcs: Iterable[Arc]) -> bool:
    """True if ``v`` is temporally reachable from ``u`` whenever the digraph
    has a ``u -> v`` path."""
    arc_list = _check_arcs(graph.nodes, arcs)
    successors: Dict[str, List[str]] = {n: [] for n in graph.nodes}
    for u, v in arc_list:
        successors[u].append(v)
    for u in graph.nodes:
        static = set(_bfs_tree(u, successors)) | {u}
        if not static <= reachable(graph, u):
            return False
    return True
