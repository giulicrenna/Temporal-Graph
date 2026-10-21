"""Journeys: paths whose edges are crossed at increasing instants.

A journey ``(u1, t1, u2, t2, ..., uk)`` crosses edge ``(u_i, u_i+1)`` at an
instant ``t_i`` where it is available, with ``t1 < t2 < ...`` (``strict=True``,
the default) or ``t1 <= t2 <= ...`` (``strict=False``, for instantaneous
contacts that can be chained within one instant). Undirected edges can be
crossed both ways, directed ones only from ``u`` to ``v``.

``start`` is the instant at which the walker is ready at the source: strict
journeys then use edges at instants ``> start``, non-strict ones ``>= start``.
When omitted, the walker is ready before the first recorded instant.
"""

from __future__ import annotations

import bisect
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Iterator, List, Mapping, Optional, Set, Tuple

from .graph import TemporalGraph

Step = Tuple[str, str, int]  # from, to, instant
Parents = Dict[str, Optional[Tuple[str, int]]]


@dataclass(frozen=True)
class Journey:
    """A sequence of ``(from, to, instant)`` steps."""

    steps: Tuple[Step, ...]

    def __post_init__(self) -> None:
        if not self.steps:
            raise ValueError("A journey needs at least one step")

    @property
    def source(self) -> str:
        return self.steps[0][0]

    @property
    def target(self) -> str:
        return self.steps[-1][1]

    @property
    def departure(self) -> int:
        return self.steps[0][2]

    @property
    def arrival(self) -> int:
        return self.steps[-1][2]

    @property
    def duration(self) -> int:
        """``arrival - departure + 1``, as in the literature."""
        return self.arrival - self.departure + 1

    @property
    def hops(self) -> int:
        return len(self.steps)

    @property
    def nodes(self) -> List[str]:
        return [self.steps[0][0]] + [step[1] for step in self.steps]

    @property
    def labels(self) -> List[int]:
        return [step[2] for step in self.steps]

    def __str__(self) -> str:
        parts = [self.steps[0][0]]
        for _, to, t in self.steps:
            parts.append(f"-{t}-> {to}")
        return " ".join(parts)



# Shared machinery


def arcs_by_instant(graph: TemporalGraph) -> List[Tuple[int, List[Tuple[str, str]]]]:
    """Traversable ``(from, to)`` pairs grouped by instant, in increasing order."""
    groups: List[Tuple[int, List[Tuple[str, str]]]] = []
    for edge in graph.time_edges():
        if not groups or groups[-1][0] != edge.t:
            groups.append((edge.t, []))
        arcs = groups[-1][1]
        arcs.append((edge.u, edge.v))
        if not edge.directed:
            arcs.append((edge.v, edge.u))
    return groups


def traversal_labels(graph: TemporalGraph) -> Dict[Tuple[str, str], List[int]]:
    """Sorted instants at which ``from -> to`` can be crossed."""
    labels: Dict[Tuple[str, str], List[int]] = {}
    for t, arcs in arcs_by_instant(graph):
        for arc in arcs:
            labels.setdefault(arc, []).append(t)
    return labels


def _check_nodes(graph: TemporalGraph, *nodes: str) -> None:
    declared = set(graph.nodes)
    for node in nodes:
        if node not in declared:
            raise ValueError(f"Node {node!r} is not declared in the graph")


def _default_start(graph: TemporalGraph, start: Optional[int], strict: bool) -> int:
    if start is not None:
        return start
    timesteps = graph.timesteps
    if not timesteps:
        return 0
    return timesteps[0] - 1 if strict else timesteps[0]


def _usable(ready: int, t: int, strict: bool) -> bool:
    return ready < t if strict else ready <= t


def foremost_search(
    graph: TemporalGraph, ready: Mapping[str, int], strict: bool = True
) -> Tuple[Dict[str, int], Parents]:
    """Earliest arrival from several sources, each ready at its own instant.

    One pass over the edges in instant order (the static expansion explored
    breadth-first without building it): O(n + |λ|) after sorting. Returns
    ``(arrival, parent)``; following ``parent`` rebuilds a foremost journey.
    """
    arrival: Dict[str, int] = dict(ready)
    parent: Parents = {node: None for node in ready}
    for t, arcs in arcs_by_instant(graph):
        if strict:
            reached: Dict[str, Tuple[str, int]] = {}
            for a, b in arcs:
                if b not in arrival and b not in reached and a in arrival and arrival[a] < t:
                    reached[b] = (a, t)
            for b, origin in reached.items():
                arrival[b] = t
                parent[b] = origin
        else:
            adjacency: Dict[str, List[str]] = {}
            for a, b in arcs:
                adjacency.setdefault(a, []).append(b)
            queue: Deque[str] = deque(
                a for a in adjacency if a in arrival and arrival[a] <= t
            )
            while queue:
                a = queue.popleft()
                for b in adjacency.get(a, ()):
                    if b not in arrival:
                        arrival[b] = t
                        parent[b] = (a, t)
                        queue.append(b)
    return arrival, parent


def _rebuild(parent: Parents, target: str) -> Journey:
    steps: List[Step] = []
    node = target
    while True:
        origin = parent[node]
        if origin is None:
            break
        previous, t = origin
        steps.append((previous, node, t))
        node = previous
    return Journey(tuple(reversed(steps)))



# Foremost, reachability and distance


def earliest_arrival(
    graph: TemporalGraph, source: str, start: Optional[int] = None, strict: bool = True
) -> Dict[str, int]:
    """Earliest arrival instant at every node reachable from ``source``.

    The source maps to ``start``; unreachable nodes are absent.
    """
    _check_nodes(graph, source)
    arrival, _ = foremost_search(graph, {source: _default_start(graph, start, strict)}, strict)
    return arrival


def foremost_journey(
    graph: TemporalGraph,
    source: str,
    target: str,
    start: Optional[int] = None,
    strict: bool = True,
) -> Optional[Journey]:
    """A journey that reaches ``target`` as early as possible, or ``None``."""
    _check_nodes(graph, source, target)
    if source == target:
        raise ValueError("source and target must differ")
    _, parent = foremost_search(graph, {source: _default_start(graph, start, strict)}, strict)
    return _rebuild(parent, target) if target in parent else None


def reachable(
    graph: TemporalGraph, source: str, start: Optional[int] = None, strict: bool = True
) -> Set[str]:
    """Nodes reachable from ``source`` by a journey (``source`` included)."""
    return set(earliest_arrival(graph, source, start, strict))


def reachability(
    graph: TemporalGraph, start: Optional[int] = None, strict: bool = True
) -> Dict[str, Set[str]]:
    """``{u: nodes reachable from u}``. Not symmetric nor transitive in general."""
    return {u: reachable(graph, u, start, strict) for u in graph.nodes}


def is_temporally_connected(
    graph: TemporalGraph, start: Optional[int] = None, strict: bool = True
) -> bool:
    """True if every ordered pair is joined by a journey within the lifetime."""
    everyone = set(graph.nodes)
    return all(reached == everyone for reached in reachability(graph, start, strict).values())


def temporal_distance(
    graph: TemporalGraph,
    source: str,
    target: str,
    start: Optional[int] = None,
    strict: bool = True,
) -> Optional[int]:
    """Time from ``start`` until the foremost arrival at ``target`` (0 if equal)."""
    begin = _default_start(graph, start, strict)
    arrival = earliest_arrival(graph, source, begin, strict)
    return arrival[target] - begin if target in arrival else None



# Latest departure


def latest_departure(
    graph: TemporalGraph, target: str, deadline: Optional[int] = None, strict: bool = True
) -> Dict[str, int]:
    """Latest instant each node can take its first edge and still reach ``target``.

    Journeys must arrive no later than ``deadline`` (default: the last
    recorded instant). The target maps to the deadline; nodes that cannot
    make it are absent.
    """
    _check_nodes(graph, target)
    timesteps = graph.timesteps
    end = deadline if deadline is not None else (timesteps[-1] if timesteps else 0)
    # Internally, "leave by" for the target is end + 1 in the strict case so
    # that edges at instants <= end qualify.
    leave: Dict[str, int] = {target: end + 1 if strict else end}
    for t, arcs in reversed(arcs_by_instant(graph)):
        if t > end:
            continue
        if strict:
            found = [a for a, b in arcs if a not in leave and b in leave and t < leave[b]]
            for a in found:
                leave.setdefault(a, t)
        else:
            reverse: Dict[str, List[str]] = {}
            for a, b in arcs:
                reverse.setdefault(b, []).append(a)
            queue: Deque[str] = deque(b for b in reverse if b in leave and leave[b] >= t)
            while queue:
                b = queue.popleft()
                for a in reverse.get(b, ()):
                    if a not in leave:
                        leave[a] = t
                        queue.append(a)
    leave[target] = end
    return leave



# Fastest and shortest


def fastest_journey(
    graph: TemporalGraph,
    source: str,
    target: str,
    start: Optional[int] = None,
    strict: bool = True,
) -> Optional[Journey]:
    """A journey of minimum duration (ties: earliest arrival), or ``None``.

    Runs one foremost search per distinct departure instant of ``source``,
    so it costs O(deg⁺(source) · (n + |λ|)).
    """
    _check_nodes(graph, source, target)
    if source == target:
        raise ValueError("source and target must differ")
    begin = _default_start(graph, start, strict)
    departures = sorted({
        t for t, arcs in arcs_by_instant(graph)
        if _usable(begin, t, strict) and any(a == source for a, _ in arcs)
    })
    best: Optional[Journey] = None
    for departure in departures:
        ready = departure - 1 if strict else departure
        _, parent = foremost_search(graph, {source: ready}, strict)
        if target not in parent:
            continue
        journey = _rebuild(parent, target)
        if best is None or (journey.duration, journey.arrival) < (best.duration, best.arrival):
            best = journey
    return best


def shortest_journey(
    graph: TemporalGraph,
    source: str,
    target: str,
    start: Optional[int] = None,
    strict: bool = True,
) -> Optional[Journey]:
    """A journey with the fewest edges (ties: earliest arrival), or ``None``.

    Bellman-Ford over hop counts: round ``k`` keeps the earliest arrival using
    at most ``k`` edges. O(n · |λ|).
    """
    _check_nodes(graph, source, target)
    if source == target:
        raise ValueError("source and target must differ")
    begin = _default_start(graph, start, strict)
    groups = arcs_by_instant(graph)
    best: Dict[str, int] = {source: begin}
    layers: List[Parents] = [{source: None}]
    for _ in range(len(graph.nodes) - 1):
        current = dict(best)
        parents = dict(layers[-1])
        for t, arcs in groups:
            for a, b in arcs:
                improves = b not in current or t < current[b]
                if improves and a in best and _usable(best[a], t, strict):
                    current[b] = t
                    parents[b] = (a, t)
        layers.append(parents)
        if target in current:
            return _rebuild_layered(layers, target)
        if current == best:
            return None
        best = current
    return None


def _rebuild_layered(layers: List[Parents], target: str) -> Journey:
    steps: List[Step] = []
    node = target
    for parents in reversed(layers):
        origin = parents.get(node)
        if origin is None:
            break
        previous, t = origin
        steps.append((previous, node, t))
        node = previous
    return Journey(tuple(reversed(steps)))



# Enumeration


def enumerate_journeys(
    graph: TemporalGraph,
    source: str,
    target: str,
    start: Optional[int] = None,
    strict: bool = True,
) -> Iterator[Journey]:
    """Every journey from ``source`` to ``target`` (exponential; small graphs).

    Each yielded journey has pairwise distinct nodes; every choice of
    instant along a node sequence is a separate journey.
    """
    _check_nodes(graph, source, target)
    if source == target:
        raise ValueError("source and target must differ")
    outgoing: Dict[str, List[Tuple[int, str]]] = {}
    for (a, b), instants in traversal_labels(graph).items():
        for t in instants:
            outgoing.setdefault(a, []).append((t, b))
    for edges in outgoing.values():
        edges.sort()

    def extend(node: str, ready: int, visited: Set[str], steps: List[Step]) -> Iterator[Journey]:
        edges = outgoing.get(node, [])
        first = bisect.bisect_right(edges, (ready, chr(0x10FFFF))) if strict else (
            bisect.bisect_left(edges, (ready, ""))
        )
        for t, nxt in edges[first:]:
            if nxt in visited:
                continue
            steps.append((node, nxt, t))
            if nxt == target:
                yield Journey(tuple(steps))
            else:
                visited.add(nxt)
                yield from extend(nxt, t, visited, steps)
                visited.discard(nxt)
            steps.pop()

    yield from extend(source, _default_start(graph, start, strict), {source}, [])
