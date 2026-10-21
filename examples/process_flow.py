"""A delivery pipeline whose handoffs change as the project matures.

Directed edges show who hands work to whom. Weights grow with the amount of
work flowing through a handoff. The script also checks that every snapshot is
free of directed cycles.

Run from the repo root with::

    python examples/process_flow.py

Writes ``output/process_flow_connections.svg`` and
``output/process_flow_decisions.svg``.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from temporal_graph import Edge, TemporalGraph, analysis, render  # noqa: E402

PRIMARY = "#1f77b4"
REWORK = "#d62728"
AUTOMATED = "#2ca02c"


def build_graph() -> TemporalGraph:
    g = TemporalGraph(["intake", "review", "build", "test", "deploy"])

    g.add_snapshot(0, [
        Edge("intake", "review", directed=True, color=PRIMARY),
        Edge("review", "build", directed=True, color=PRIMARY),
    ])
    g.add_snapshot(1, [
        Edge("intake", "review", directed=True, weight=2.0, color=PRIMARY),
        Edge("review", "build", directed=True, weight=2.0, color=PRIMARY),
        Edge("build", "test", directed=True, color=PRIMARY),
    ])
    g.add_snapshot(2, [
        Edge("intake", "review", directed=True, weight=3.0, color=PRIMARY),
        Edge("review", "build", directed=True, weight=3.0, color=PRIMARY),
        Edge("build", "test", directed=True, weight=2.0, color=PRIMARY),
        Edge("test", "deploy", directed=True, color=PRIMARY),
    ])
    g.add_snapshot(3, [
        Edge("intake", "review", directed=True, weight=3.0, color=PRIMARY),
        Edge("review", "build", directed=True, weight=2.0, color=REWORK),
        Edge("build", "test", directed=True, weight=3.0, color=AUTOMATED),
        Edge("test", "deploy", directed=True, weight=2.0, color=AUTOMATED),
        Edge("build", "deploy", directed=True, color=AUTOMATED),
    ])
    return g


def main() -> None:
    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    g = build_graph()
    print("acyclic in every snapshot:", analysis.is_temporally_acyclic(g))
    for mode in ("connections", "decisions"):
        figure = render(g, mode)
        for extension in ("svg", "png"):
            path = figure.savefig(out_dir / f"process_flow_{mode}.{extension}")
            print(Path(path).relative_to(ROOT))


if __name__ == "__main__":
    main()
