"""Random temporal graphs: a clique where each edge gets one uniform label in ``[r]``."""

from __future__ import annotations

import itertools
import math
import random
from typing import Optional

from .graph import TemporalGraph


def random_temporal_graph(n: int, r: int, seed: Optional[int] = None) -> TemporalGraph:
    """Undirected clique on ``v1 .. vn``; every edge independently gets a single
    instant drawn uniformly from ``1 .. r``. Reproducible with ``seed``."""
    if n < 2 or r < 1:
        raise ValueError("Need n >= 2 and r >= 1")
    rng = random.Random(seed)
    nodes = [f"v{i}" for i in range(1, n + 1)]
    time_edges = [(u, v, rng.randint(1, r)) for u, v in itertools.combinations(nodes, 2)]
    return TemporalGraph.from_time_edges(nodes, time_edges)


def path_journey_probability(k: int, r: int) -> float:
    """P(a fixed path of ``k`` edges is a journey) = C(r, k) / r^k."""
    if k < 1 or r < 1:
        raise ValueError("Need k >= 1 and r >= 1")
    return float(math.comb(r, k) / r ** k)


def expected_journey_count(n: int, k: int, r: int) -> float:
    """E[number of journeys of length ``k``] = (n)_{k+1} · C(r, k) / r^k."""
    if not 1 <= k < n:
        raise ValueError("Need 1 <= k < n")
    return math.perm(n, k + 1) * path_journey_probability(k, r)


def foremost_within_two_probability(n: int, r: int) -> float:
    """Exact P(foremost journey between two fixed nodes arrives by instant 2)
    = 1 - ((r - 2) / r) · (1 - 1 / r²)^(n - 2), for ``r >= 2``."""
    if n < 2 or r < 2:
        raise ValueError("Need n >= 2 and r >= 2")
    return 1 - (r - 2) / r * (1 - 1 / r ** 2) ** (n - 2)
