"""Static expansion of a temporal graph: the time-unrolled DAG ``H = (S, E_H)``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .graph import TemporalGraph

TimeNode = Tuple[str, int]
Arc = Tuple[TimeNode, TimeNode]


@dataclass(frozen=True)
class StaticExpansion:
    """Levels ``first_level .. last_level``, one copy of every node per level.

    A vertical arc ``(u, i-1) -> (u, i)`` models waiting; a diagonal arc
    ``(u, t-1) -> (v, t)`` models crossing an edge available at instant ``t``.
    """

    first_level: int
    last_level: int
    time_nodes: List[TimeNode]
    vertical_arcs: List[Arc]
    diagonal_arcs: List[Arc]

    @property
    def arcs(self) -> List[Arc]:
        return self.vertical_arcs + self.diagonal_arcs


def static_expansion(graph: TemporalGraph, waiting: bool = True) -> StaticExpansion:
    """Unroll ``graph`` over its lifetime.

    With ``n`` nodes, age α and |λ| labels it has ``n (α + 1)`` time-nodes and
    ``n α`` vertical arcs plus one diagonal per directed label (two per
    undirected label). ``waiting=False`` omits the vertical arcs, for nodes
    that cannot keep what they receive.
    """
    time_edges = graph.time_edges()
    if time_edges:
        first, last = time_edges[0].t - 1, time_edges[-1].t
    else:
        first = last = 0
    nodes = graph.nodes
    levels = range(first, last + 1)
    time_nodes = [(u, i) for i in levels for u in nodes]
    vertical: List[Arc] = []
    if waiting:
        vertical = [((u, i - 1), (u, i)) for i in levels if i > first for u in nodes]
    diagonal: List[Arc] = []
    for edge in time_edges:
        diagonal.append(((edge.u, edge.t - 1), (edge.v, edge.t)))
        if not edge.directed:
            diagonal.append(((edge.v, edge.t - 1), (edge.u, edge.t)))
    return StaticExpansion(first, last, time_nodes, vertical, diagonal)
