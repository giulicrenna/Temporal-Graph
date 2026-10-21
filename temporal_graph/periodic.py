"""Compact periodic availability: edge ``e`` is available at ``f_e(x) = a·x + b``.

With ``x = 0, 1, 2, ...`` an edge with ``(a, b)`` appears at ``b, b + a,
b + 2a, ...``; ``a = 0`` means the single instant ``b``. These functions
answer coincidence and journey questions in time independent of the
lifetime, which may be exponential in the input size.
"""

from __future__ import annotations

import heapq
import math
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .graph import Edge, TemporalGraph

Linear = Tuple[int, int]  # (a, b)


def _check_linear(function: Linear) -> None:
    a, b = function
    if a < 0 or b < 0:
        raise ValueError(f"Availability {function} must have non-negative a and b")


def solve_congruences(system: Sequence[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
    """Solve ``t ≡ r_i (mod m_i)`` for pairs ``(r_i, m_i)`` with ``m_i >= 1``.

    Returns ``(t0, M)`` with all solutions ``t0 + M·z`` (``0 <= t0 < M``), or
    ``None`` when ``r_i ≢ r_j (mod gcd(m_i, m_j))`` for some pair.
    """
    residue, modulus = 0, 1
    for r, m in system:
        if m < 1:
            raise ValueError("moduli must be >= 1")
        g = math.gcd(modulus, m)
        if (r - residue) % g:
            return None
        # residue + modulus * k ≡ r (mod m)  ->  k ≡ (r - residue)/g · inv(modulus/g) (mod m/g)
        step = m // g
        k = ((r - residue) // g * pow(modulus // g, -1, step)) % step if step > 1 else 0
        residue += modulus * k
        modulus *= step
        residue %= modulus
    return residue, modulus


def common_instants(functions: Sequence[Linear], count: int = 1) -> List[int]:
    """The first ``count`` instants at which all edges are available together."""
    for function in functions:
        _check_linear(function)
    if count < 1 or not functions:
        return []
    fixed = {b for a, b in functions if a == 0}
    if len(fixed) > 1:
        return []
    if fixed:
        t = fixed.pop()
        ok = all(t >= b and (t - b) % a == 0 for a, b in functions if a > 0)
        return [t] if ok else []
    solution = solve_congruences([(b % a, a) for a, b in functions])
    if solution is None:
        return []
    t0, modulus = solution
    floor = max(b for _, b in functions)
    first = t0 + max(0, math.ceil((floor - t0) / modulus)) * modulus
    return [first + i * modulus for i in range(count)]


def edges_coincide(first: Linear, second: Linear) -> bool:
    """True if the two edges share at least one instant (gcd criterion)."""
    return bool(common_instants([first, second]))


def next_availability(function: Linear, after: int) -> Optional[int]:
    """Smallest instant of ``function`` strictly greater than ``after``."""
    a, b = function
    if b > after:
        return b
    if a == 0:
        return None
    return b + ((after - b) // a + 1) * a


def linear_availability_graph(
    nodes: Sequence[str],
    functions: Mapping[Tuple[str, str], Linear],
    lifetime: int,
    directed: bool = False,
) -> TemporalGraph:
    """Materialize instants ``0 .. lifetime`` as a :class:`TemporalGraph`."""
    by_t: Dict[int, List[Edge]] = {}
    for (u, v), function in functions.items():
        _check_linear(function)
        a, b = function
        t = b
        while t <= lifetime:
            by_t.setdefault(t, []).append(Edge(u, v, directed=directed))
            if a == 0:
                break
            t += a
    graph = TemporalGraph(nodes)
    for t in sorted(by_t):
        graph.add_snapshot(t, by_t[t])
    return graph


def linear_earliest_arrival(
    nodes: Sequence[str],
    functions: Mapping[Tuple[str, str], Linear],
    source: str,
    start: int = -1,
    directed: bool = False,
    lifetime: Optional[int] = None,
) -> Dict[str, int]:
    """Foremost arrival times without materializing time (Dijkstra on arrival).

    Strict journeys: an edge is crossed at its next instant after the walker
    is ready. Cost O(m log n), independent of the lifetime.
    """
    declared = set(nodes)
    if source not in declared:
        raise ValueError(f"Node {source!r} is not declared")
    neighbours: Dict[str, List[Tuple[str, Linear]]] = {n: [] for n in nodes}
    for (u, v), function in functions.items():
        if u not in declared or v not in declared:
            raise ValueError(f"Edge {(u, v)} uses an undeclared node")
        _check_linear(function)
        neighbours[u].append((v, function))
        if not directed:
            neighbours[v].append((u, function))
    arrival: Dict[str, int] = {}
    queue: List[Tuple[int, str]] = [(start, source)]
    while queue:
        t, node = heapq.heappop(queue)
        if node in arrival:
            continue
        arrival[node] = t
        for nxt, function in neighbours[node]:
            if nxt in arrival:
                continue
            when = next_availability(function, t)
            if when is not None and (lifetime is None or when <= lifetime):
                heapq.heappush(queue, (when, nxt))
    return arrival
