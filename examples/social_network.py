"""Friendships forming and breaking in a small group over five weeks.

Run from the repo root with::

    python examples/social_network.py

Writes ``output/social_network_connections.svg`` and
``output/social_network_decisions.svg``.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from temporal_graph import Edge, TemporalGraph, render  # noqa: E402

CLOSE_FRIEND = "#d62728"
FRIEND = "#1f77b4"
ACQUAINTANCE = "#9467bd"


def build_graph() -> TemporalGraph:
    g = TemporalGraph(["alice", "bob", "carol", "dave", "erin", "frank"])

    g.add_snapshot(0, [
        Edge("alice", "bob", color=FRIEND),
        Edge("bob", "carol", color=FRIEND),
        Edge("dave", "erin", color=ACQUAINTANCE),
    ])
    g.add_snapshot(1, [
        Edge("alice", "bob", weight=2.0, color=CLOSE_FRIEND),
        Edge("bob", "carol", color=FRIEND),
        Edge("carol", "dave", color=ACQUAINTANCE),
        Edge("dave", "erin", color=ACQUAINTANCE),
    ])
    g.add_snapshot(2, [
        Edge("alice", "bob", weight=3.0, color=CLOSE_FRIEND),
        Edge("carol", "dave", color=FRIEND),
        Edge("dave", "erin", weight=2.0, color=FRIEND),
        Edge("erin", "frank", color=ACQUAINTANCE),
    ])
    g.add_snapshot(3, [
        Edge("alice", "bob", weight=3.0, color=CLOSE_FRIEND),
        Edge("dave", "erin", weight=2.0, color=FRIEND),
        Edge("erin", "frank", weight=2.0, color=FRIEND),
        Edge("alice", "frank", color=ACQUAINTANCE),
    ])
    g.add_snapshot(4, [
        Edge("dave", "erin", weight=2.0, color=FRIEND),
        Edge("erin", "frank", weight=2.0, color=FRIEND),
        Edge("alice", "frank", color=FRIEND),
    ])
    return g


def main() -> None:
    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    g = build_graph()
    for mode in ("connections", "decisions"):
        figure = render(g, mode)
        for extension in ("svg", "png"):
            path = figure.savefig(out_dir / f"social_network_{mode}.{extension}")
            print(Path(path).relative_to(ROOT))


if __name__ == "__main__":
    main()
