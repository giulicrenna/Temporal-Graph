"""A hard-disk gas whose collisions form a temporal contact network.

``N`` disks of diameter ``σ`` and mass ``m`` move freely in a periodic square
box and collide elastically. The event-driven simulation is exact: between
collisions every disk moves in a straight line. Each collision is an
instantaneous contact, so binning collision times into instants of width
``BIN`` gives a temporal graph whose journeys are the chains of collisions
through which momentum, energy or any perturbation can travel.

The script checks three results of kinetic theory:

1. Collision frequency. Enskog theory for hard disks predicts
   ``ν = 2 σ n sqrt(π kT / m) g(σ)``, with number density ``n`` and the
   contact value ``g(σ) = (1 - 7η/16) / (1 - η)^2`` (Henderson) at packing
   fraction ``η``. It is measured as ``2 |time edges| / (N T)``.
2. Relaxation to Maxwell-Boltzmann. Every disk starts with the same speed;
   collisions alone drive the speeds to the 2D Maxwell (Rayleigh)
   distribution, for which ``<v^4> / <v^2>^2 = 2``.
3. Spread of causal influence. Foremost journeys from one disk give the set
   of disks it could have influenced by each instant. In a well-mixed gas
   that set grows as a stochastic SI process: with ``k`` disks reached, the
   next one is reached at rate ``λ_k = ν k (N - k) / (N - 1)``, so half the
   gas is reached after ``sum 1 / λ_k`` on average. Reshuffling the
   collision partners at the same instants makes the gas well mixed and
   recovers that prediction; the real gas is slower, because collisions are
   local in space and neighbors that already met keep meeting again.

Run from the repo root with::

    python examples/physics/hard_disk_gas.py

Writes to ``output/physics/``: ``hard_disk_cascade_connections.png`` /
``.svg``, the collisions that first carry the influence of one disk to every
other disk, colored by the number of hops.
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from temporal_graph import Edge, TemporalGraph, render  # noqa: E402
from temporal_graph.journeys import foremost_search  # noqa: E402

PARTICLES = 40
DIAMETER = 1.0
MASS = 1.0
KT = 1.0                   # in 2D, <m v^2 / 2> = kT
PACKING_FRACTION = 0.2
DURATION = 120.0
EQUILIBRATION = 20.0       # collisions before this time are left out of [1] and [3]
BIN = 0.02                 # width of one instant
CASCADE_BIN = 0.5          # coarser instants keep the cascade figure readable
SEED = 3
RELAXATION_RUNS = 20       # independent short runs averaged for [2]
RELAXATION_TIMES = (0.0, 0.5, 1.0, 2.0, 4.0, 8.0)
SPEED_SAMPLE_PERIOD = 0.5
SPEED_BINS = (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, math.inf)
SPREAD_START_SPACING = 10.0   # time between the start instants averaged in [3]
SPREAD_TABLE_TIMES = (1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 10.0)
HALF = PARTICLES // 2
MASTER_EQUATION_STEP = 0.01
CASCADE_SOURCE = 0
# Ordinal blue ramp, light to dark: hop count of the journey that informs a disk.
HOP_COLORS = ["#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"]

Collision = Tuple[float, int, int]


def disk(i: int) -> str:
    return f"p{i}"


def box_side() -> float:
    return math.sqrt(PARTICLES * math.pi * DIAMETER ** 2 / (4.0 * PACKING_FRACTION))


class HardDiskGas:
    """Event-driven molecular dynamics of hard disks with periodic boundaries.

    Each disk keeps its earliest predicted collision. Predictions use the
    minimum image, which is exact only while the relative displacement stays
    below half the box, so they are discarded beyond that horizon and every
    prediction is rebuilt at a period short enough for no collision to slip
    through.
    """

    def __init__(self, rng: random.Random):
        self.side = box_side()
        self.now = 0.0
        self.positions = self._lattice()
        self.velocities = self._equal_speeds(rng)
        self.upcoming: List[Tuple[float, int]] = []
        self.next_refresh = 0.0

    def _lattice(self) -> List[List[float]]:
        columns = math.ceil(math.sqrt(PARTICLES))
        cell = self.side / columns
        return [[(i % columns + 0.5) * cell, (i // columns + 0.5) * cell]
                for i in range(PARTICLES)]

    @staticmethod
    def _equal_speeds(rng: random.Random) -> List[List[float]]:
        """Random directions, zero total momentum, then a common speed with
        ``<v^2> = 2 kT / m``."""
        angles = [rng.uniform(0.0, 2.0 * math.pi) for _ in range(PARTICLES)]
        velocities = [[math.cos(a), math.sin(a)] for a in angles]
        for axis in (0, 1):
            mean = sum(v[axis] for v in velocities) / PARTICLES
            for v in velocities:
                v[axis] -= mean
        target = math.sqrt(2.0 * KT / MASS)
        for v in velocities:
            norm = math.hypot(v[0], v[1])
            v[0] *= target / norm
            v[1] *= target / norm
        return velocities

    def _wrap(self, d: float) -> float:
        return d - self.side * round(d / self.side)

    def _relative(self, i: int, j: int) -> Tuple[float, float, float, float]:
        (xi, yi), (xj, yj) = self.positions[i], self.positions[j]
        (ui, wi), (uj, wj) = self.velocities[i], self.velocities[j]
        return self._wrap(xj - xi), self._wrap(yj - yi), uj - ui, wj - wi

    def _pair_time(self, i: int, j: int) -> float:
        dx, dy, du, dw = self._relative(i, j)
        approach = dx * du + dy * dw
        if approach >= 0.0:
            return math.inf
        speed2 = du * du + dw * dw
        discriminant = approach * approach - speed2 * (dx * dx + dy * dy - DIAMETER ** 2)
        if discriminant < 0.0:
            return math.inf
        t = (-approach - math.sqrt(discriminant)) / speed2
        if t * math.sqrt(speed2) > self.side / 2.0 - DIAMETER:
            return math.inf
        return max(t, 0.0)

    def _predict(self, i: int) -> None:
        best = (math.inf, -1)
        for k in range(PARTICLES):
            if k == i:
                continue
            t = self.now + self._pair_time(i, k)
            if t < best[0]:
                best = (t, k)
            if t < self.upcoming[k][0]:
                self.upcoming[k] = (t, i)
        self.upcoming[i] = best

    def _refresh(self) -> None:
        self.upcoming = [(math.inf, -1)] * PARTICLES
        for i in range(PARTICLES):
            self._predict(i)
        fastest = max(math.hypot(v[0], v[1]) for v in self.velocities)
        self.next_refresh = self.now + (self.side / 2.0 - DIAMETER) / (4.0 * fastest)

    def _advance(self, t: float) -> None:
        dt = t - self.now
        for p, v in zip(self.positions, self.velocities):
            p[0] = (p[0] + v[0] * dt) % self.side
            p[1] = (p[1] + v[1] * dt) % self.side
        self.now = t

    def _collide(self, i: int, j: int) -> None:
        dx, dy, du, dw = self._relative(i, j)
        factor = (dx * du + dy * dw) / DIAMETER ** 2
        self.velocities[i][0] += factor * dx
        self.velocities[i][1] += factor * dy
        self.velocities[j][0] -= factor * dx
        self.velocities[j][1] -= factor * dy
        stale = {k for k in range(PARTICLES) if self.upcoming[k][1] in (i, j)} | {i, j}
        for k in stale:
            self.upcoming[k] = (math.inf, -1)
        for k in stale:
            self._predict(k)

    def speeds_squared(self) -> List[float]:
        return [v[0] ** 2 + v[1] ** 2 for v in self.velocities]

    def run(self, duration: float, sample_times: List[float]) -> Tuple[List[Collision],
                                                                       List[List[float]]]:
        """Collisions up to ``duration`` and ``v^2`` of every disk at each sample time."""
        self._refresh()
        collisions: List[Collision] = []
        samples: List[List[float]] = []
        pending = sorted(sample_times)
        while True:
            i = min(range(PARTICLES), key=lambda k: self.upcoming[k][0])
            t, j = self.upcoming[i]
            event = min(t, self.next_refresh)
            while pending and pending[0] <= min(event, duration):
                samples.append(self.speeds_squared())
                pending.pop(0)
            if event > duration:
                break
            self._advance(event)
            if event == t:
                self._collide(i, j)
                collisions.append((t, i, j))
            else:
                self._refresh()
        self._advance(duration)
        return collisions, samples

    def closest_approach(self) -> float:
        return min(math.hypot(*self._relative(i, j)[:2])
                   for i in range(PARTICLES) for j in range(i + 1, PARTICLES))


def number_density() -> float:
    return PARTICLES / box_side() ** 2


def enskog_frequency() -> float:
    eta = PACKING_FRACTION
    contact = (1.0 - 7.0 * eta / 16.0) / (1.0 - eta) ** 2
    return boltzmann_frequency() * contact


def boltzmann_frequency() -> float:
    return 2.0 * DIAMETER * number_density() * math.sqrt(math.pi * KT / MASS)


def moment_ratio(speeds2: List[float]) -> float:
    """``<v^4> / <v^2>^2``: 1 for equal speeds, 2 for the 2D Maxwell distribution."""
    mean2 = sum(speeds2) / len(speeds2)
    return sum(s * s for s in speeds2) / len(speeds2) / mean2 ** 2


def rayleigh_fraction(low: float, high: float) -> float:
    def cdf(v: float) -> float:
        return 1.0 - math.exp(-MASS * v * v / (2.0 * KT))
    return cdf(high) - cdf(low)


def collision_graph(collisions: List[Collision], width: float = BIN) -> TemporalGraph:
    graph = TemporalGraph([disk(i) for i in range(PARTICLES)])
    by_instant: Dict[int, List[Edge]] = {}
    for t, i, j in collisions:
        by_instant.setdefault(int(t / width), []).append(Edge(disk(i), disk(j)))
    for instant in range(int(DURATION / width) + 1):
        graph.add_snapshot(instant, by_instant.get(instant, []))
    return graph


def shuffled_partners(collisions: List[Collision], rng: random.Random) -> List[Collision]:
    """Same collision instants, partners drawn uniformly: a well-mixed gas."""
    return [(t, *rng.sample(range(PARTICLES), 2)) for t, _, _ in collisions]


def spread_delays(graph: TemporalGraph, horizon: int) -> List[List[float]]:
    """Sorted delays after which journeys from one disk reach each disk, for
    every disk as the source and several start instants."""
    first = int(EQUILIBRATION / BIN)
    spacing = int(SPREAD_START_SPACING / BIN)
    runs = []
    for start in range(first, int(DURATION / BIN) - horizon, spacing):
        for source in graph.nodes:
            arrival, _ = foremost_search(graph, {source: start})
            runs.append(sorted((a - start) * BIN for a in arrival.values()))
    return runs


def mean_reached(runs: List[List[float]], t: float) -> float:
    return sum(sum(1 for d in delays if d <= t) for delays in runs) / len(runs)


def mean_half_time(runs: List[List[float]]) -> float:
    return sum(delays[HALF - 1] for delays in runs) / len(runs)


def well_mixed_rates(frequency: float) -> List[float]:
    """``λ_k``: rate at which the k-th reached disk meets an unreached one."""
    return [frequency * k * (PARTICLES - k) / (PARTICLES - 1) for k in range(PARTICLES + 1)]


def well_mixed_half_time(frequency: float) -> float:
    rates = well_mixed_rates(frequency)
    return sum(1.0 / rates[k] for k in range(1, HALF))


def well_mixed_reached(frequency: float, times: List[float]) -> List[float]:
    """Mean number of disks reached at each of the ascending ``times``, from
    the master equation ``p_k' = λ_(k-1) p_(k-1) - λ_k p_k`` (RK4)."""
    rates = well_mixed_rates(frequency)

    def derivative(p: List[float]) -> List[float]:
        return [(rates[k - 1] * p[k - 1] if k else 0.0) - rates[k] * p[k] for k in range(len(p))]

    def shifted(p: List[float], dp: List[float], h: float) -> List[float]:
        return [x + h * d for x, d in zip(p, dp)]

    p = [0.0] * (PARTICLES + 1)
    p[1] = 1.0
    now = 0.0
    means = []
    for target in times:
        while now < target:
            h = min(MASTER_EQUATION_STEP, target - now)
            k1 = derivative(p)
            k2 = derivative(shifted(p, k1, h / 2))
            k3 = derivative(shifted(p, k2, h / 2))
            k4 = derivative(shifted(p, k3, h))
            p = [x + h / 6 * (a + 2 * b + 2 * c + d)
                 for x, a, b, c, d in zip(p, k1, k2, k3, k4)]
            now += h
        means.append(sum(k * pk for k, pk in enumerate(p)))
    return means


def cascade_graph(graph: TemporalGraph, source: str, start: int) -> TemporalGraph:
    """The foremost-journey tree from ``source``: one directed edge per disk,
    at the instant it is first reached; nodes sorted by arrival."""
    arrival, parent = foremost_search(graph, {source: start})
    hops = {source: 0}
    for node in sorted(arrival, key=arrival.__getitem__):
        link = parent[node]
        if link is not None:
            hops[node] = hops[link[0]] + 1
    tree = TemporalGraph(sorted(arrival, key=lambda n: (arrival[n], n)))
    edges: Dict[int, List[Edge]] = {}
    for node, link in parent.items():
        if link is None:
            continue
        previous, instant = link
        color = HOP_COLORS[min(hops[node], len(HOP_COLORS)) - 1]
        edges.setdefault(instant - start, []).append(
            Edge(previous, node, directed=True, color=color))
    for instant in range(1, max(edges) + 1):
        tree.add_snapshot(instant, edges.get(instant, []))
    return tree


def main() -> None:
    out_dir = ROOT / "output" / "physics"
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    print(f"gas: N = {PARTICLES} disks, sigma = {DIAMETER}, eta = {PACKING_FRACTION}, "
          f"box {box_side():.2f} x {box_side():.2f}, kT = {KT}, m = {MASS}")

    gas = HardDiskGas(rng)
    sample_times = [k * SPEED_SAMPLE_PERIOD
                    for k in range(int(EQUILIBRATION / SPEED_SAMPLE_PERIOD),
                                   int(DURATION / SPEED_SAMPLE_PERIOD) + 1)]
    collisions, speed_samples = gas.run(DURATION, sample_times)
    graph = collision_graph(collisions)
    print(f"{len(collisions)} collisions, {len(graph.time_edges())} time edges over "
          f"{len(graph.timesteps)} instants; closest approach {gas.closest_approach():.3f} "
          f"(>= sigma)")

    # 1. Collision frequency.
    counted = [c for c in collisions if c[0] >= EQUILIBRATION]
    measured = 2.0 * len(counted) / (PARTICLES * (DURATION - EQUILIBRATION))
    print(f"[1] collision frequency per disk: measured {measured:.3f}, "
          f"Enskog {enskog_frequency():.3f} ({100 * (measured / enskog_frequency() - 1):+.1f}%), "
          f"dilute Boltzmann {boltzmann_frequency():.3f}")

    # 2. Relaxation to Maxwell-Boltzmann.
    ratios = [0.0] * len(RELAXATION_TIMES)
    for _ in range(RELAXATION_RUNS):
        _, samples = HardDiskGas(rng).run(max(RELAXATION_TIMES), list(RELAXATION_TIMES))
        for k, speeds2 in enumerate(samples):
            ratios[k] += moment_ratio(speeds2) / RELAXATION_RUNS
    mean_free_time = 1.0 / enskog_frequency()
    print(f"[2] <v^4>/<v^2>^2 averaged over {RELAXATION_RUNS} runs "
          f"(equal speeds 1, Maxwell 2); mean free time {mean_free_time:.2f}")
    for t, ratio in zip(RELAXATION_TIMES, ratios):
        print(f"    t = {t:4.1f} ({t / mean_free_time:4.1f} free times): {ratio:.3f}")
    pooled = [s for sample in speed_samples for s in sample]
    print(f"    equilibrium, {len(pooled)} speeds pooled: {moment_ratio(pooled):.3f}")
    print("    speed range   measured   Rayleigh")
    speeds = [math.sqrt(s) for s in pooled]
    for low, high in zip(SPEED_BINS, SPEED_BINS[1:]):
        share = sum(1 for v in speeds if low <= v < high) / len(speeds)
        print(f"    [{low:.1f}, {high:.1f})  {share:8.3f}   {rayleigh_fraction(low, high):8.3f}")

    # 3. Spread of causal influence.
    horizon = int(max(SPREAD_TABLE_TIMES) / BIN)
    real = spread_delays(graph, horizon)
    mixed = spread_delays(collision_graph(shuffled_partners(collisions, rng)), horizon)
    theory = well_mixed_reached(measured, list(SPREAD_TABLE_TIMES))
    print(f"[3] disks reached from one disk, mean over {len(real)} sources x start instants")
    print("    time   real gas   shuffled partners   well-mixed theory")
    for t, expected in zip(SPREAD_TABLE_TIMES, theory):
        print(f"    {t:4.1f}   {mean_reached(real, t):8.1f}   "
              f"{mean_reached(mixed, t):17.1f}   {expected:17.1f}")
    print(f"    mean time to reach {HALF} disks: real {mean_half_time(real):.2f}, "
          f"shuffled {mean_half_time(mixed):.2f}, "
          f"well-mixed theory {well_mixed_half_time(measured):.2f}")

    start = int(EQUILIBRATION / CASCADE_BIN)
    coarse = collision_graph(collisions, CASCADE_BIN)
    cascade = cascade_graph(coarse, disk(CASCADE_SOURCE), start)
    print(f"    cascade from {disk(CASCADE_SOURCE)} at t = {EQUILIBRATION}: all "
          f"{len(cascade.nodes)} disks reached after {len(cascade.timesteps) * CASCADE_BIN:.1f} "
          f"(instants of {CASCADE_BIN})")
    figure = render(cascade, "connections")
    for extension in ("png", "svg"):
        path = figure.savefig(out_dir / f"hard_disk_cascade_connections.{extension}")
        print(Path(path).relative_to(ROOT))


if __name__ == "__main__":
    main()
