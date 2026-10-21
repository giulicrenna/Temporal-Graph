"""Run the temporal_graph example and export both SVG modes + their PNGs.

Run from the repo root with::

    python examples/example.py

The four output files (two SVGs and two PNGs) are written to ``output/``.

This example showcases the new features of the library:

- ``directed`` edges get an arrowhead at the destination node end.
- ``weight`` greater than 1.0 is rendered as a "snake" lifeline.
- ``color`` is honored for every line / marker of the edge.
- No re-connection: an edge that disappears must be re-introduced
  explicitly at a later snapshot before it can appear again.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from temporal_graph import Edge, TemporalGraph, render


# Color palette (one per logical edge role).
RED = "#d62728"
BLUE = "#1f77b4"
GREEN = "#2ca02c"
ORANGE = "#ff7f0e"


def build_graph() -> TemporalGraph:
    g = TemporalGraph(nodes=["a", "b", "c", "d"])

    # t=0: a-b-c-d chain, all default weight, undirected, no color.
    g.add_snapshot(
        0,
        [
            Edge("a", "b"),
            Edge("b", "c"),
            Edge("c", "d"),
        ],
    )

    # t=1: a-b stays, now directed a->b and heavier (red). a-c and b-d
    # appear. b-c and c-d are disconnected.
    g.add_snapshot(
        1,
        [
            Edge("a", "b", directed=True, weight=2.5, color=RED),
            Edge("a", "c", weight=1.0, color=BLUE),
            Edge("b", "d", weight=1.0, color=GREEN),
        ],
    )

    # t=2: a-b persists. a-c gets slightly heavier. b-d is disconnected.
    # a-d appears.
    g.add_snapshot(
        2,
        [
            Edge("a", "b", directed=True, weight=2.5, color=RED),
            Edge("a", "c", weight=1.5, color=BLUE),
            Edge("a", "d", weight=1.0, color=ORANGE),
        ],
    )

    # t=3: a-b disconnects. a-c and a-d remain.
    g.add_snapshot(
        3,
        [
            Edge("a", "c", weight=1.0, color=BLUE),
            Edge("a", "d", weight=1.0, color=ORANGE),
        ],
    )

    return g


def main() -> None:
    out_dir = ROOT / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    g = build_graph()

    for mode in ("connections", "decisions"):
        figure = render(g, mode)
        for extension in ("svg", "png"):
            path = Path(figure.savefig(out_dir / f"example_{mode}.{extension}"))
            print(f"  {path.relative_to(ROOT)}  ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
