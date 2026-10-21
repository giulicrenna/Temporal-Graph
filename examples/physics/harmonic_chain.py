"""The speed of sound in a harmonic chain, measured with temporal journeys.

A chain of point masses ``m`` joined by springs of stiffness ``k`` and rest
length ``a`` obeys ``m u''_n = k (u_(n+1) - 2 u_n + u_(n-1))``. Displacing the
central mass by 1 and releasing it has the exact solution
``u_n(t) = J_2n(2 ω0 t)`` with ``ω0 = sqrt(k / m)`` (Bessel functions of the
first kind). ``J_2n(x)`` is exponentially small for ``x < 2n``, so the
disturbance travels inside the light cone ``|n| a <= c t`` set by the
long-wavelength speed of sound ``c = a ω0``.

The simulation is turned into a temporal graph by sampling it every
``SAMPLE_PERIOD``: spring ``(n, n+1)`` is an edge at instant ``t`` while it
stores at least ``ENERGY_THRESHOLD`` of the initial energy. A journey then
carries energy from site to site, and the foremost arrival at each site is
the arrival of the wavefront. The script checks four results:

1. The velocity Verlet integration matches ``J_2n(2 ω0 t)`` and conserves
   energy.
2. The temporal graph built from the simulation equals the one built from
   the exact solution, label by label.
3. Foremost arrival times grow linearly with distance and the fitted front
   speed approaches ``c = a sqrt(k / m)``. The exponential tail ahead of the
   cone crosses the threshold slightly early, so arrivals lead ``n a / c``
   by a bounded margin that does not grow with distance.
4. Changing the mass changes the speed as ``1 / sqrt(m)``.

Run from the repo root with::

    python examples/physics/harmonic_chain.py

Writes to ``output/physics/``: ``harmonic_chain_connections.png`` / ``.svg``
(the light cone on a timeline) and ``harmonic_chain.gif``.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from temporal_graph import Edge, TemporalGraph, animate, render  # noqa: E402
from temporal_graph.journeys import earliest_arrival, foremost_journey  # noqa: E402

STIFFNESS = 1.0
SPACING = 1.0
REFERENCE_MASS = 1.0
SCAN_MASSES = (0.5, 1.0, 2.0, 4.0)
HALF_LENGTH = 60          # sites on each side of the kicked mass; ends are fixed
OBSERVED_SITES = 20       # sites 0..OBSERVED_SITES become graph nodes
TIME_STEP = 0.01
SAMPLE_PERIOD = 0.25      # physical time between consecutive instants
ENERGY_THRESHOLD = 1e-3   # fraction of the initial energy that activates a spring
FIT_FROM_SITE = 5         # skip the near field when fitting the front speed
TIME_MARGIN = 1.3         # simulate this many times the light-cone crossing time
BESSEL_SAMPLES = 200      # trapezoidal nodes for the Bessel integral
FIGURE_STRIDE = 4         # keep every 4th instant (one time unit) for the figures
FIGURE_SITES = 12
FRAME_DURATION_MS = 350
# Ordinal blue ramp, light to dark: stored energy as a fraction of the initial one.
ENERGY_COLORS: List[Tuple[float, str]] = [
    (0.1, "#0d366b"),
    (0.03, "#184f95"),
    (0.01, "#256abf"),
    (0.003, "#3987e5"),
    (0.0, "#86b6ef"),
]

Field = Callable[[float], List[float]]


def site(n: int) -> str:
    return f"x{n}"


def sound_speed(mass: float) -> float:
    return SPACING * math.sqrt(STIFFNESS / mass)


def bessel_j(order: int, x: float) -> float:
    """``J_n(x) = (1/π) ∫_0^π cos(n τ - x sin τ) dτ``; the trapezoidal rule
    converges exponentially for this periodic integrand."""
    h = math.pi / BESSEL_SAMPLES
    total = 0.5 * (1.0 + math.cos(order * math.pi))
    for k in range(1, BESSEL_SAMPLES):
        tau = k * h
        total += math.cos(order * tau - x * math.sin(tau))
    return total * h / math.pi


def spring_energies(u: List[float]) -> List[float]:
    return [0.5 * STIFFNESS * (u[i + 1] - u[i]) ** 2 for i in range(len(u) - 1)]


def accelerations(u: List[float], mass: float) -> List[float]:
    ratio = STIFFNESS / mass
    acc = [0.0] * len(u)
    for i in range(1, len(u) - 1):
        acc[i] = ratio * (u[i + 1] - 2.0 * u[i] + u[i - 1])
    return acc


def initial_displacement() -> List[float]:
    u = [0.0] * (2 * HALF_LENGTH + 1)
    u[HALF_LENGTH] = 1.0
    return u


def simulate(mass: float, duration: float) -> Tuple[List[List[float]], float, List[float]]:
    """Velocity Verlet run of the whole chain.

    Returns the displacements at every sample instant (index 0 is t = 0), the
    relative energy drift at the end and the final displacements.
    """
    u = initial_displacement()
    v = [0.0] * len(u)
    acc = accelerations(u, mass)
    initial_energy = sum(spring_energies(u))
    steps_per_sample = round(SAMPLE_PERIOD / TIME_STEP)
    samples = [u[:]]
    for step in range(1, round(duration / TIME_STEP) + 1):
        v = [vi + 0.5 * TIME_STEP * ai for vi, ai in zip(v, acc)]
        u = [ui + TIME_STEP * vi for ui, vi in zip(u, v)]
        acc = accelerations(u, mass)
        v = [vi + 0.5 * TIME_STEP * ai for vi, ai in zip(v, acc)]
        if step % steps_per_sample == 0:
            samples.append(u[:])
    energy = sum(spring_energies(u)) + sum(0.5 * mass * vi * vi for vi in v)
    return samples, (energy - initial_energy) / initial_energy, u


def exact_displacements(mass: float, t: float, sites: int) -> List[float]:
    """``u_n(t) = J_2n(2 ω0 t)`` for ``n = -sites..sites`` on an infinite chain."""
    x = 2.0 * math.sqrt(STIFFNESS / mass) * t
    half = [bessel_j(2 * n, x) for n in range(sites + 1)]
    return half[:0:-1] + half


def energy_color(fraction: float) -> str:
    return next(color for level, color in ENERGY_COLORS if fraction >= level)


def chain_graph(samples: List[List[float]], center: int) -> TemporalGraph:
    """Spring ``(n, n+1)`` is an edge at instant ``t`` while it holds at least
    ``ENERGY_THRESHOLD`` of the initial energy (which is ``k``)."""
    graph = TemporalGraph([site(n) for n in range(OBSERVED_SITES + 1)])
    for t, u in enumerate(samples[1:], start=1):
        energies = spring_energies(u[center:center + OBSERVED_SITES + 1])
        edges = [
            Edge(site(n), site(n + 1), color=energy_color(e / STIFFNESS))
            for n, e in enumerate(energies)
            if e >= ENERGY_THRESHOLD * STIFFNESS
        ]
        graph.add_snapshot(t, edges)
    return graph


def arrival_times(graph: TemporalGraph) -> List[Optional[float]]:
    arrival = earliest_arrival(graph, site(0), start=0)
    return [
        arrival[site(n)] * SAMPLE_PERIOD if site(n) in arrival else None
        for n in range(OBSERVED_SITES + 1)
    ]


def fitted_speed(times: List[Optional[float]]) -> float:
    """Inverse slope of the least-squares line ``t_n = n a / v + t_0``."""
    points = [(n * SPACING, t) for n, t in enumerate(times) if n >= FIT_FROM_SITE and t is not None]
    mean_x = sum(x for x, _ in points) / len(points)
    mean_t = sum(t for _, t in points) / len(points)
    slope = (sum((x - mean_x) * (t - mean_t) for x, t in points)
             / sum((x - mean_x) ** 2 for x, _ in points))
    return 1.0 / slope


def label_set(graph: TemporalGraph) -> set:
    return {(te.u, te.v, te.t) for te in graph.time_edges()}


def run(mass: float) -> Dict[str, object]:
    duration = TIME_MARGIN * OBSERVED_SITES * SPACING / sound_speed(mass)
    samples, drift, final = simulate(mass, duration)
    graph = chain_graph(samples, HALF_LENGTH)
    return {"samples": samples, "drift": drift, "final": final,
            "duration": duration, "graph": graph, "times": arrival_times(graph)}


def figure_graph(graph: TemporalGraph, last_instant: int) -> TemporalGraph:
    """Every ``FIGURE_STRIDE``-th snapshot of the first ``FIGURE_SITES`` sites."""
    nodes = [site(n) for n in range(FIGURE_SITES + 1)]
    wanted = set(nodes)
    coarse = TemporalGraph(nodes)
    for t in range(FIGURE_STRIDE, last_instant + 1, FIGURE_STRIDE):
        edges = [e for e in graph.edges_at(t) if e.u in wanted and e.v in wanted]
        coarse.add_snapshot(t // FIGURE_STRIDE, edges)
    return coarse


def main() -> None:
    out_dir = ROOT / "output" / "physics"
    out_dir.mkdir(parents=True, exist_ok=True)
    c = sound_speed(REFERENCE_MASS)
    print(f"chain: k = {STIFFNESS}, m = {REFERENCE_MASS}, a = {SPACING}, "
          f"c = a sqrt(k/m) = {c:.3f}; {2 * HALF_LENGTH + 1} masses, fixed ends")

    # 1. Integrator against the exact solution.
    reference = run(REFERENCE_MASS)
    duration = reference["duration"]
    final = reference["final"]
    exact = exact_displacements(REFERENCE_MASS, duration, HALF_LENGTH // 2)
    offset = HALF_LENGTH - HALF_LENGTH // 2
    error = max(abs(final[offset + i] - x) for i, x in enumerate(exact))
    print(f"[1] t = {duration:.1f}: max |u_n - J_2n(2 w0 t)| = {error:.1e}, "
          f"relative energy drift = {reference['drift']:.1e}")

    # 2. The same temporal graph, built from the exact solution.
    instants = len(reference["samples"]) - 1
    exact_samples = [exact_displacements(REFERENCE_MASS, t * SAMPLE_PERIOD, OBSERVED_SITES + 1)
                     for t in range(instants + 1)]
    exact_graph = chain_graph(exact_samples, OBSERVED_SITES + 1)
    simulated_labels = label_set(reference["graph"])
    exact_labels = label_set(exact_graph)
    agree = len(simulated_labels & exact_labels)
    print(f"[2] time edges: simulated {len(simulated_labels)}, exact {len(exact_labels)}, "
          f"shared {agree}; foremost arrivals identical: "
          f"{arrival_times(exact_graph) == reference['times']}")

    # 3. Wavefront arrival from foremost journeys.
    times = reference["times"]
    print("[3] site  arrival  light cone n*a/c  apparent speed n*a/t")
    for n in range(1, OBSERVED_SITES + 1, 2):
        t = times[n]
        print(f"    {n:4d}  {t:7.2f}  {n * SPACING / c:16.2f}  {n * SPACING / t:20.3f}")
    leads = [n * SPACING / c - t for n, t in enumerate(times)
             if n >= FIT_FROM_SITE and t is not None]
    print(f"    fitted front speed {fitted_speed(times):.3f} (c = {c:.3f}); "
          f"lead over the light cone for n >= {FIT_FROM_SITE}: "
          f"{min(leads):.2f} to {max(leads):.2f}")
    print("    journey to the last site:",
          foremost_journey(reference["graph"], site(0), site(OBSERVED_SITES), start=0))

    # 4. Speed of sound against the mass.
    print("[4] mass   c theory   c fitted   ratio")
    for mass in SCAN_MASSES:
        result = reference if mass == REFERENCE_MASS else run(mass)
        speed = fitted_speed(result["times"])
        print(f"    {mass:4.1f}   {sound_speed(mass):8.3f}   {speed:8.3f}   "
              f"{speed / sound_speed(mass):5.3f}")

    last = round(times[FIGURE_SITES] / SAMPLE_PERIOD) + 2 * FIGURE_STRIDE
    coarse = figure_graph(reference["graph"], last)
    figure = render(coarse, "connections")
    for extension in ("png", "svg"):
        path = figure.savefig(out_dir / f"harmonic_chain_connections.{extension}")
        print(Path(path).relative_to(ROOT))
    positions = {site(n): (n * SPACING, 0.0) for n in range(FIGURE_SITES + 1)}
    animation = animate(coarse, frame_duration=FRAME_DURATION_MS, positions=positions)
    print(Path(animation.save(out_dir / "harmonic_chain.gif")).relative_to(ROOT))


if __name__ == "__main__":
    main()
