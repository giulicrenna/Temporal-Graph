"""Small Edmonds-Karp max-flow, used for the temporal Menger theorems."""

from __future__ import annotations

from collections import deque
from typing import Deque, Dict, Generic, Hashable, Set, TypeVar

N = TypeVar("N", bound=Hashable)


class FlowNetwork(Generic[N]):
    def __init__(self) -> None:
        self.capacity: Dict[N, Dict[N, int]] = {}

    def add_arc(self, u: N, v: N, capacity: int) -> None:
        self.capacity.setdefault(u, {})
        self.capacity.setdefault(v, {})
        self.capacity[u][v] = self.capacity[u].get(v, 0) + capacity
        self.capacity[v].setdefault(u, 0)

    def max_flow(self, source: N, sink: N) -> int:
        """Value of a maximum flow; afterwards ``capacity`` holds the residual."""
        if source not in self.capacity or sink not in self.capacity:
            return 0
        total = 0
        while True:
            parent: Dict[N, N] = {source: source}
            queue: Deque[N] = deque([source])
            while queue and sink not in parent:
                u = queue.popleft()
                for v, residual in self.capacity[u].items():
                    if residual > 0 and v not in parent:
                        parent[v] = u
                        queue.append(v)
            if sink not in parent:
                return total
            bottleneck = None
            v = sink
            while v != source:
                u = parent[v]
                residual = self.capacity[u][v]
                bottleneck = residual if bottleneck is None else min(bottleneck, residual)
                v = u
            assert bottleneck is not None
            v = sink
            while v != source:
                u = parent[v]
                self.capacity[u][v] -= bottleneck
                self.capacity[v][u] += bottleneck
                v = u
            total += bottleneck

    def source_side(self, source: N) -> Set[N]:
        """Nodes reachable from ``source`` in the residual network (a min cut)."""
        seen = {source}
        queue: Deque[N] = deque([source])
        while queue:
            u = queue.popleft()
            for v, residual in self.capacity.get(u, {}).items():
                if residual > 0 and v not in seen:
                    seen.add(v)
                    queue.append(v)
        return seen
