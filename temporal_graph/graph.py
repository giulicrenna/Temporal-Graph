"""Data model for ``temporal_graph``.

A :class:`TemporalGraph` represents an undirected or directed graph that
evolves through discrete time steps. Each step stores the set of edges
that are active at that moment, together with the per-edge weight, color
and directionality that apply at that step.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from typing import Dict, Iterable, List, NamedTuple, Optional, Sequence, Tuple

# Default color when the user does not specify one.  Black ink on white
# background — same look as the original minimal library.
DEFAULT_COLOR = "#111111"


@dataclass(frozen=True)
class Edge:
    """An edge between two node labels.

    The graph can hold both undirected and directed edges:

    - ``directed=False`` (the default) makes the edge undirected, so
      ``Edge("a", "b")`` and ``Edge("b", "a")`` are the same logical
      edge and may be deduplicated within a snapshot.
    - ``directed=True`` makes the edge directed from ``u`` to ``v`` and
      is rendered with an arrowhead at the ``v`` end.

    ``weight`` and ``color`` are *per snapshot* values. The same
    logical edge can be re-declared at later snapshots with a different
    weight or color to indicate that those properties change over time.
    """

    u: str
    v: str
    directed: bool = False
    weight: float = 1.0
    color: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.u, str) or not isinstance(self.v, str):
            raise TypeError("Edge endpoints must be strings")
        if self.u == self.v:
            raise ValueError(
                f"Edge endpoints must differ; got self-loop on {self.u!r}"
            )
        if not isinstance(self.directed, bool):
            raise TypeError("directed must be a bool")
        if not isinstance(self.weight, (int, float)):
            raise TypeError("weight must be a number")
        if self.weight < 0:
            raise ValueError(f"weight must be non-negative, got {self.weight!r}")
        if self.color is not None and not isinstance(self.color, str):
            raise TypeError("color must be a string or None")

    # -- identity / hashing -------------------------------------------------

    def key(self) -> Tuple[str, str]:
        """Identity key: (canonical_u, canonical_v).

        Direction, weight and color are deliberately NOT part of the
        identity — the same logical edge can be re-declared at later
        snapshots with different direction / weight / color.
        """
        return self.canonical()

    def canonical(self) -> Tuple[str, str]:
        return (self.u, self.v) if self.u <= self.v else (self.v, self.u)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Edge):
            return NotImplemented
        return self.key() == other.key()

    def __hash__(self) -> int:
        return hash(self.key())

    def other(self, node: str) -> str:
        if node == self.u:
            return self.v
        if node == self.v:
            return self.u
        raise ValueError(f"{node!r} is not an endpoint of edge {self}")

    # -- helpers used by the renderer --------------------------------------

    def endpoints_in_order(self) -> Tuple[str, str]:
        """Return ``(source, target)`` respecting directionality.

        For undirected edges this falls back to the canonical order.
        """
        if self.directed:
            return (self.u, self.v)
        return self.canonical()

    def effective_color(self) -> str:
        return self.color if self.color else DEFAULT_COLOR


class TimeEdge(NamedTuple):
    """An edge available at one instant: the pair ``(e, t)`` of the λ model.

    For a directed edge ``(u, v)`` follows the direction; for an undirected
    one it is the canonical (sorted) pair.
    """

    u: str
    v: str
    t: int
    directed: bool
    weight: float


class TemporalGraph:
    """A graph that evolves through discrete time steps.

    Each snapshot stores the set of edges that are active at that
    moment, together with the per-edge weight and color that apply at
    that step. Snapshots are kept sorted by timestep.

    Timesteps are the *instants* (labels) of the temporal-graph literature:
    a snapshot at ``t`` lists the edges available at instant ``t``, and an
    instant without a recorded snapshot has no edges. Journeys and the
    metrics in :mod:`temporal_graph.journeys` and
    :mod:`temporal_graph.connectivity` follow this reading. The renderer
    and :meth:`change_events` instead compare consecutive *recorded*
    snapshots.
    """

    def __init__(self, nodes: Sequence[str]):
        if not nodes:
            raise ValueError("TemporalGraph requires at least one node")
        seen: set[str] = set()
        for n in nodes:
            if not isinstance(n, str):
                raise TypeError(f"Node labels must be strings, got {type(n).__name__}")
            if n in seen:
                raise ValueError(f"Duplicate node label: {n!r}")
            seen.add(n)
        self._nodes: List[str] = list(nodes)
        self._node_set = frozenset(self._nodes)
        # List of (timestep, {edge_key: Edge_instance}), sorted by timestep.
        self._snapshots: List[Tuple[int, Dict[Tuple[str, str], Edge]]] = []
        self._by_t: Dict[int, Dict[Tuple[str, str], Edge]] = {}
        self._time_edges: Optional[List[TimeEdge]] = None

    @classmethod
    def from_time_edges(
        cls,
        nodes: Sequence[str],
        time_edges: Iterable[Tuple[str, str, int]],
        directed: bool = False,
    ) -> "TemporalGraph":
        """Build a graph from ``(u, v, t)`` triples, one per edge and instant."""
        by_t: Dict[int, List[Edge]] = {}
        for u, v, t in time_edges:
            by_t.setdefault(t, []).append(Edge(u, v, directed=directed))
        graph = cls(nodes)
        for t in sorted(by_t):
            graph.add_snapshot(t, by_t[t])
        return graph

    # -- public API --------------------------------------------------------

    @property
    def nodes(self) -> List[str]:
        return list(self._nodes)

    @property
    def timesteps(self) -> List[int]:
        return [t for t, _ in self._snapshots]

    def edges_at(self, t: int) -> List[Edge]:
        if t not in self._by_t:
            raise KeyError(f"No snapshot recorded for timestep {t}")
        return list(self._by_t[t].values())

    def edge_at(self, t: int, key: Tuple[str, str]) -> Edge:
        if t not in self._by_t:
            raise KeyError(f"No snapshot recorded for timestep {t}")
        edges = self._by_t[t]
        if key not in edges:
            raise KeyError(f"Edge {key!r} not present at timestep {t}")
        return edges[key]

    def time_edges(self) -> List[TimeEdge]:
        """Every ``(u, v, t)`` availability, sorted by instant then endpoints."""
        if self._time_edges is None:
            result: List[TimeEdge] = []
            for t, edges in self._snapshots:
                for key in sorted(edges):
                    edge = edges[key]
                    u, v = edge.endpoints_in_order()
                    result.append(TimeEdge(u, v, t, edge.directed, edge.weight))
            self._time_edges = result
        return list(self._time_edges)

    def labels(self, u: str, v: str) -> List[int]:
        """Instants at which the edge between ``u`` and ``v`` is available: λ(e)."""
        key = (u, v) if u <= v else (v, u)
        return [t for t, edges in self._snapshots if key in edges]

    @property
    def label_count(self) -> int:
        """Total number of labels |λ|, i.e. of edge-instant pairs."""
        return sum(len(edges) for _, edges in self._snapshots)

    @property
    def age(self) -> int:
        """Lifetime α = λ_max − λ_min + 1 over instants that carry edges; 0 if none."""
        used = [t for t, edges in self._snapshots if edges]
        return used[-1] - used[0] + 1 if used else 0

    def add_snapshot(self, t: int, edges: Iterable[Edge]) -> None:
        if not isinstance(t, int) or isinstance(t, bool):
            raise TypeError(f"timestep must be an int, got {type(t).__name__}")

        edge_dict: Dict[Tuple[str, str], Edge] = {}
        for edge in edges:
            if not isinstance(edge, Edge):
                raise TypeError(
                    f"edges must be Edge instances, got {type(edge).__name__}"
                )
            self._validate_endpoint(edge.u)
            self._validate_endpoint(edge.v)
            key = edge.key()
            if key in edge_dict:
                # Duplicate (same identity) within the same snapshot is
                # silently deduplicated — the first one wins.
                continue
            edge_dict[key] = edge

        self._time_edges = None
        index = bisect.bisect_left(self.timesteps, t)
        if t in self._by_t:
            self._snapshots[index] = (t, edge_dict)
        else:
            self._snapshots.insert(index, (t, edge_dict))
        self._by_t[t] = edge_dict

    def snapshots(self) -> List[Tuple[int, List[Edge]]]:
        return [(t, list(edges.values())) for t, edges in self._snapshots]

    # -- helpers -----------------------------------------------------------

    def _validate_endpoint(self, node: str) -> None:
        if node not in self._node_set:
            raise ValueError(
                f"Node {node!r} is not declared in the graph. "
                f"Declared nodes: {self._nodes}"
            )

    # -- derived views used by the renderer --------------------------------

    def change_events(self) -> List[Tuple[int, str, Tuple[str, str]]]:
        """Return ``(timestep, kind, edge_key)`` for connect/disconnect events.

        A re-connection (edge absent at t-1, present at t) is a
        ``"connect"`` event at ``t``. We never emit a connect for an
        edge that was already present in the previous snapshot — the
        user must explicitly include it for it to remain.
        """
        if len(self._snapshots) < 2:
            return []

        events: List[Tuple[int, str, Tuple[str, str]]] = []
        for (prev_t, prev_edges), (curr_t, curr_edges) in zip(
            self._snapshots, self._snapshots[1:]
        ):
            prev_keys = set(prev_edges.keys())
            curr_keys = set(curr_edges.keys())
            for k in sorted(curr_keys - prev_keys):
                events.append((curr_t, "connect", k))
            for k in sorted(prev_keys - curr_keys):
                events.append((curr_t, "disconnect", k))
        events.sort(key=lambda ev: (ev[0], ev[1], ev[2]))
        return events

    def edge_intervals(
        self,
    ) -> Dict[Tuple[str, str], List[Tuple[int, int]]]:
        """Half-open ``(start_t, end_t)`` intervals per edge key.

        Appearances at consecutive *instants* (t and t + 1) are merged into
        a single interval; any gap, including an unrecorded instant, closes
        the previous one. ``end_t`` is exclusive — an edge alive at
        timestep 2 has end_t >= 3.
        """
        intervals: Dict[Tuple[str, str], List[Tuple[int, int]]] = {}
        for t, edges in self._snapshots:
            for key in edges:
                ivs = intervals.setdefault(key, [])
                if ivs and ivs[-1][1] == t:
                    ivs[-1] = (ivs[-1][0], t + 1)
                else:
                    ivs.append((t, t + 1))
        return intervals
