"""Analyze a temporal graph and export it to JSON, CSV and GEXF.

Run from the repo root with::

    python examples/analysis_and_export.py

Prints the metrics and writes ``output/network.json``, ``output/network.csv``
and ``output/network.gexf`` (open the last one in Gephi).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from temporal_graph import analysis, exporters, utils  # noqa: E402


def build_graph():
    return utils.from_edge_list(
        ["a", "b", "c", "d", "e"],
        {
            0: [("a", "b"), ("b", "c")],
            1: [("a", "b"), ("b", "c"), ("c", "d")],
            2: [("a", "b"), ("d", "e")],
            3: [("d", "e")],
        },
    )


def main() -> None:
    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    g = build_graph()

    print("degree of b over time:", analysis.degree_timeline(g, "b"))
    for t in g.timesteps:
        components = analysis.connected_components_at(g, t)
        print(f"components at t={t}:", [sorted(c) for c in components])
    print("edge persistence:")
    for key, share in analysis.edge_persistence(g).items():
        print(f"  {key}: {share:.0%}")

    added, removed = utils.snapshot_diff(g, 1, 2)
    print("t=1 -> t=2 added:", [e.key() for e in added], "removed:", [e.key() for e in removed])

    only_ab = utils.subgraph(g, ["a", "b"])
    print("subgraph a,b timesteps with edges:", [t for t in only_ab.timesteps if only_ab.edges_at(t)])

    (out_dir / "network.json").write_text(exporters.to_json(g), encoding="utf-8")
    exporters.to_csv(g, str(out_dir / "network.csv"))
    exporters.to_gexf(g, str(out_dir / "network.gexf"))

    restored = exporters.from_json((out_dir / "network.json").read_text(encoding="utf-8"))
    print("JSON round trip preserves the graph:", exporters.to_dict(restored) == exporters.to_dict(g))


if __name__ == "__main__":
    main()
