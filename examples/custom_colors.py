"""Color and weight as data: a load-balancer sharing traffic with servers.

Edge color encodes health (green, amber, red) and weight encodes traffic. The
same edges change both attributes over time without being new edges.

Run from the repo root with::

    python examples/custom_colors.py

Writes ``output/custom_colors_connections.svg`` and
``output/custom_colors_decisions.svg``.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from temporal_graph import Edge, TemporalGraph, render  # noqa: E402

HEALTHY = "#2ca02c"
DEGRADED = "#ff7f0e"
FAILING = "#d62728"

SERVERS = ["s1", "s2", "s3"]
LOAD_BALANCER = "lb"

# (health color, traffic weight) per server and timestep. None means the
# server is out of rotation at that step.
TIMELINE = {
    "s1": [(HEALTHY, 1.0), (HEALTHY, 2.0), (DEGRADED, 3.0), (FAILING, 3.0), None],
    "s2": [(HEALTHY, 1.0), (HEALTHY, 1.0), (HEALTHY, 2.0), (HEALTHY, 3.0), (HEALTHY, 3.5)],
    "s3": [None, None, (HEALTHY, 1.0), (HEALTHY, 2.0), (HEALTHY, 3.0)],
}


def build_graph() -> TemporalGraph:
    g = TemporalGraph([LOAD_BALANCER, *SERVERS])
    steps = len(next(iter(TIMELINE.values())))
    for t in range(steps):
        edges = [
            Edge(LOAD_BALANCER, server, directed=True, color=state[0], weight=state[1])
            for server, states in TIMELINE.items()
            if (state := states[t]) is not None
        ]
        g.add_snapshot(t, edges)
    return g


def main() -> None:
    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    g = build_graph()
    for mode in ("connections", "decisions"):
        figure = render(g, mode)
        for extension in ("svg", "png"):
            path = figure.savefig(out_dir / f"custom_colors_{mode}.{extension}")
            print(Path(path).relative_to(ROOT))


if __name__ == "__main__":
    main()
