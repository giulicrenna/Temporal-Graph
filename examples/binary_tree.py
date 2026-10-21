"""A large binary tree that is built up and then taken apart.

The tree is complete with ``DEPTH`` levels below the root (63 nodes for
depth 5). Nodes use heap numbering: node ``i`` has children ``2i`` and
``2i + 1``. Edges are directed parent -> child and colored by depth.

- Build: edges are added in breadth-first order, ``EDGES_PER_STEP`` at a time.
- Teardown: leaves are pruned in reverse breadth-first order at the same pace,
  so the tree shrinks from the bottom right back to the bare root.

Run from the repo root with::

    python examples/binary_tree.py

Writes to ``output/``:

- ``binary_tree.gif``: the animated evolution, with a hierarchical layout.
- ``binary_tree_full.png`` / ``.svg``: the frame where the tree is complete.
- ``binary_tree_decisions.png`` / ``.svg``: the timeline view of every change.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from temporal_graph import Edge, TemporalGraph, animate, render  # noqa: E402

DEPTH = 5
EDGES_PER_STEP = 6
LEVEL_HEIGHT = 2.5  # vertical gap between levels, in leaf spacings
LEVEL_COLORS = ["#1f77b4", "#2ca02c", "#ff7f0e", "#d62728", "#9467bd", "#8c564b"]
FRAME_DURATION_MS = 450
TIMELINE_PNG_SCALE = 0.5


def node_count(depth: int = DEPTH) -> int:
    return 2 ** (depth + 1) - 1


def level(i: int) -> int:
    return i.bit_length() - 1


def tree_edges(depth: int = DEPTH) -> List[Edge]:
    """Every parent -> child edge in breadth-first order."""
    return [
        Edge(str(child // 2), str(child), directed=True, color=LEVEL_COLORS[level(child) - 1])
        for child in range(2, node_count(depth) + 1)
    ]


def tree_positions(depth: int = DEPTH) -> Dict[str, Tuple[float, float]]:
    """Leaves one unit apart; each parent centered above its children."""
    positions = {}
    for i in range(1, node_count(depth) + 1):
        d = level(i)
        span = 2 ** (depth - d)
        positions[str(i)] = ((i - 2 ** d + 0.5) * span, d * LEVEL_HEIGHT)
    return positions


def build_graph(depth: int = DEPTH, step: int = EDGES_PER_STEP) -> TemporalGraph:
    edges = tree_edges(depth)
    g = TemporalGraph([str(i) for i in range(1, node_count(depth) + 1)])
    t = 0
    for count in range(0, len(edges), step):
        g.add_snapshot(t, edges[:count])
        t += 1
    for count in range(len(edges), -1, -step):
        g.add_snapshot(t, edges[:count])
        t += 1
    if g.edges_at(t - 1):
        g.add_snapshot(t, [])
    return g


def main() -> None:
    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    g = build_graph()
    print(f"{len(g.nodes)} nodes, {len(g.timesteps)} timesteps")

    animation = animate(g, frame_duration=FRAME_DURATION_MS, positions=tree_positions())
    print(Path(animation.save(out_dir / "binary_tree.gif", scale=1.0)).relative_to(ROOT))

    full = max(range(len(g.timesteps)), key=lambda i: len(g.edges_at(g.timesteps[i])))
    for extension in ("png", "svg"):
        path = animation.frames[full].savefig(out_dir / f"binary_tree_full.{extension}")
        print(Path(path).relative_to(ROOT))

    timeline = render(g, "decisions")
    for extension in ("png", "svg"):
        path = timeline.savefig(
            out_dir / f"binary_tree_decisions.{extension}", scale=TIMELINE_PNG_SCALE
        )
        print(Path(path).relative_to(ROOT))


if __name__ == "__main__":
    main()
