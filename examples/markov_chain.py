"""A Markov chain seen as a temporal graph, in two ways.

The chain models a shopper moving between the pages of a shop. It is
ergodic but not reversible: ``checkout`` always returns to ``home``, so
probability keeps circulating around the purchase cycle forever.

1. Trajectory. One simulated walk becomes a temporal graph with the edge
   ``x(t-1) -> x(t)`` at instant ``t`` (staying put adds no edge). The
   foremost arrival from the start state is then exactly the *first hitting
   time* of every state. Averaging it over many walks reproduces the
   expected hitting time obtained by solving ``h = 1 + P h``.

2. Probability flow. Starting with all mass on ``home``, the net flow
   ``π_t(u) P(u, v) - π_t(v) P(v, u)`` between every pair becomes a directed
   edge at instant ``t + 1``, pointing the way the mass moves; its weight is
   ``1 + 10 × |net flow|``. Flows that cancel out as the chain equilibrates
   fade below ``FLOW_THRESHOLD`` and disappear, while the cycle current stays.

Run from the repo root with::

    python examples/markov_chain.py

Writes to ``output/``: ``markov_trajectory_connections.png`` / ``.svg``,
``markov_flow.gif`` and ``markov_flow_stationary.png``.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from temporal_graph import Edge, TemporalGraph, animate, render  # noqa: E402
from temporal_graph.journeys import earliest_arrival  # noqa: E402

STATES = ["home", "search", "product", "cart", "checkout"]
TRANSITIONS: Dict[str, Dict[str, float]] = {
    "home": {"home": 0.3, "search": 0.5, "product": 0.2},
    "search": {"search": 0.2, "product": 0.6, "home": 0.2},
    "product": {"product": 0.1, "cart": 0.4, "search": 0.3, "home": 0.2},
    "cart": {"cart": 0.1, "checkout": 0.6, "product": 0.3},
    "checkout": {"home": 1.0},
}
COLORS = {
    "home": "#1f77b4", "search": "#ff7f0e", "product": "#2ca02c",
    "cart": "#d62728", "checkout": "#9467bd",
}
START = "home"
TARGET = "checkout"
SEED = 7
TRAJECTORY_STEPS = 24
MONTE_CARLO_WALKS = 1000
FLOW_STEPS = 14
FLOW_THRESHOLD = 0.01


def step(state: str, rng: random.Random) -> str:
    targets = list(TRANSITIONS[state])
    weights = [TRANSITIONS[state][t] for t in targets]
    return rng.choices(targets, weights)[0]


def walk(rng: random.Random, steps: int) -> List[str]:
    states = [START]
    for _ in range(steps):
        states.append(step(states[-1], rng))
    return states


def walk_until(rng: random.Random, target: str) -> List[str]:
    states = [START]
    while states[-1] != target:
        states.append(step(states[-1], rng))
    return states


def trajectory_graph(states: List[str]) -> TemporalGraph:
    """Edge ``x(t-1) -> x(t)`` at instant ``t``; every instant gets a snapshot."""
    graph = TemporalGraph(STATES)
    for t in range(1, len(states)):
        before, after = states[t - 1], states[t]
        moves = [] if before == after else [Edge(before, after, directed=True,
                                                 color=COLORS[before])]
        graph.add_snapshot(t, moves)
    return graph


def expected_hitting_times(target: str) -> Dict[str, float]:
    """Solve ``h(i) = 1 + sum_j P(i, j) h(j)`` with ``h(target) = 0``."""
    unknowns = [s for s in STATES if s != target]
    index = {s: i for i, s in enumerate(unknowns)}
    size = len(unknowns)
    # Augmented matrix of (I - Q) h = 1, Q = P restricted to the unknowns.
    matrix = [[0.0] * (size + 1) for _ in range(size)]
    for s in unknowns:
        row = matrix[index[s]]
        row[index[s]] += 1.0
        row[size] = 1.0
        for nxt, p in TRANSITIONS[s].items():
            if nxt != target:
                row[index[nxt]] -= p
    for col in range(size):
        pivot = max(range(col, size), key=lambda r: abs(matrix[r][col]))
        matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
        for r in range(size):
            if r != col:
                factor = matrix[r][col] / matrix[col][col]
                matrix[r] = [a - factor * b for a, b in zip(matrix[r], matrix[col])]
    times = {s: matrix[index[s]][size] / matrix[index[s]][index[s]] for s in unknowns}
    times[target] = 0.0
    return times


def evolve(distribution: Dict[str, float]) -> Dict[str, float]:
    result = {s: 0.0 for s in STATES}
    for state, mass in distribution.items():
        for nxt, p in TRANSITIONS[state].items():
            result[nxt] += mass * p
    return result


def stationary_distribution(iterations: int = 500) -> Dict[str, float]:
    distribution = {s: 1.0 / len(STATES) for s in STATES}
    for _ in range(iterations):
        distribution = evolve(distribution)
    return distribution


def total_variation(a: Dict[str, float], b: Dict[str, float]) -> float:
    return 0.5 * sum(abs(a[s] - b[s]) for s in STATES)


def flow_graph(steps: int) -> TemporalGraph:
    """Net probability flow of each step as weighted directed edges."""
    graph = TemporalGraph(STATES)
    distribution = {s: 1.0 if s == START else 0.0 for s in STATES}
    for t in range(1, steps + 1):
        edges = []
        for i, u in enumerate(STATES):
            for v in STATES[i + 1:]:
                net = (distribution[u] * TRANSITIONS[u].get(v, 0.0)
                       - distribution[v] * TRANSITIONS[v].get(u, 0.0))
                if abs(net) < FLOW_THRESHOLD:
                    continue
                source, target = (u, v) if net > 0 else (v, u)
                edges.append(Edge(source, target, directed=True, color=COLORS[source],
                                  weight=round(1 + 10 * abs(net), 1)))
        graph.add_snapshot(t, edges)
        distribution = evolve(distribution)
    return graph


def main() -> None:
    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    rng = random.Random(SEED)

    # 1. One trajectory: foremost arrival = first hitting time.
    states = walk(rng, TRAJECTORY_STEPS)
    trajectory = trajectory_graph(states)
    print("trajectory:", " -> ".join(states))
    hits = earliest_arrival(trajectory, START, start=0)
    print("first hitting times on this walk:",
          {s: hits.get(s, "not reached") for s in STATES})
    figure = render(trajectory, "connections")
    for extension in ("png", "svg"):
        path = figure.savefig(out_dir / f"markov_trajectory_connections.{extension}")
        print(Path(path).relative_to(ROOT))

    # Monte Carlo: average foremost arrival at TARGET over many walks.
    total = 0
    for _ in range(MONTE_CARLO_WALKS):
        graph = trajectory_graph(walk_until(rng, TARGET))
        total += earliest_arrival(graph, START, start=0)[TARGET]
    exact = expected_hitting_times(TARGET)[START]
    print(f"mean hitting time {START} -> {TARGET}: simulated "
          f"{total / MONTE_CARLO_WALKS:.2f}, exact {exact:.2f}")

    # 2. Exact probability flow converging to the stationary distribution.
    stationary = stationary_distribution()
    print("stationary distribution:", {s: round(p, 3) for s, p in stationary.items()})
    distribution = {s: 1.0 if s == START else 0.0 for s in STATES}
    distances = []
    for _ in range(FLOW_STEPS):
        distances.append(round(total_variation(distribution, stationary), 3))
        distribution = evolve(distribution)
    print("total variation to stationary, per step:", distances)

    flows = flow_graph(FLOW_STEPS)
    animation = animate(flows, frame_duration=700)
    print(Path(animation.save(out_dir / "markov_flow.gif")).relative_to(ROOT))
    still = animation.frames[-1].savefig(out_dir / "markov_flow_stationary.png")
    print(Path(still).relative_to(ROOT))


if __name__ == "__main__":
    main()
