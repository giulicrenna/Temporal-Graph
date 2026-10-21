"""Serialization of :class:`~temporal_graph.graph.TemporalGraph`."""

from __future__ import annotations

import csv
import json
import os
import xml.etree.ElementTree as ET
from typing import Any, Dict, Tuple

from .graph import Edge, TemporalGraph

CSV_COLUMNS = ("t", "u", "v", "directed", "weight", "color")
GEXF_NAMESPACE = "http://gexf.net/1.3"


def to_dict(graph: TemporalGraph) -> Dict[str, Any]:
    """Return a JSON-compatible dict describing ``graph``."""
    return {
        "nodes": graph.nodes,
        "snapshots": [
            {
                "t": t,
                "edges": [
                    {
                        "u": e.u,
                        "v": e.v,
                        "directed": e.directed,
                        "weight": e.weight,
                        "color": e.color,
                    }
                    for e in edges
                ],
            }
            for t, edges in graph.snapshots()
        ],
    }


def from_dict(data: Dict[str, Any]) -> TemporalGraph:
    """Rebuild a graph from the output of :func:`to_dict`."""
    graph = TemporalGraph(data["nodes"])
    for snapshot in data["snapshots"]:
        graph.add_snapshot(snapshot["t"], [Edge(**e) for e in snapshot["edges"]])
    return graph


def to_json(graph: TemporalGraph, indent: int = 2) -> str:
    """Serialize ``graph`` to a JSON string."""
    return json.dumps(to_dict(graph), indent=indent)


def from_json(text: str) -> TemporalGraph:
    """Rebuild a graph from a string produced by :func:`to_json`."""
    return from_dict(json.loads(text))


def to_csv(graph: TemporalGraph, path: str) -> str:
    """Write one row per edge and snapshot. Returns the absolute path written."""
    abs_path = _prepare_path(path)
    with open(abs_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(CSV_COLUMNS)
        for t, edges in graph.snapshots():
            for e in edges:
                writer.writerow([t, e.u, e.v, e.directed, e.weight, e.color or ""])
    return abs_path


def to_gexf(graph: TemporalGraph, path: str) -> str:
    """Write a dynamic GEXF file (integer time) readable by Gephi.

    Each edge carries one spell per continuous interval of presence. An edge
    is directed in the file if it is directed in any snapshot, and its weight
    is the one it has in its first snapshot.
    """
    first_seen: Dict[Tuple[str, str], Edge] = {}
    for _, edges in graph.snapshots():
        for e in edges:
            first_seen.setdefault(e.key(), e)
    directed_keys = {
        e.key() for _, edges in graph.snapshots() for e in edges if e.directed
    }

    root = ET.Element("gexf", {"xmlns": GEXF_NAMESPACE, "version": "1.3"})
    graph_el = ET.SubElement(
        root,
        "graph",
        {"mode": "dynamic", "defaultedgetype": "undirected", "timeformat": "integer"},
    )
    nodes_el = ET.SubElement(graph_el, "nodes")
    for n in graph.nodes:
        ET.SubElement(nodes_el, "node", {"id": n, "label": n})

    edges_el = ET.SubElement(graph_el, "edges")
    intervals = graph.edge_intervals()
    for i, key in enumerate(sorted(intervals)):
        source = first_seen[key]
        attrs = {
            "id": str(i),
            "source": source.u,
            "target": source.v,
            "weight": f"{source.weight:g}",
            "type": "directed" if key in directed_keys else "undirected",
        }
        edge_el = ET.SubElement(edges_el, "edge", attrs)
        spells_el = ET.SubElement(edge_el, "spells")
        for start, end in intervals[key]:
            ET.SubElement(spells_el, "spell", {"start": str(start), "end": str(end - 1)})

    abs_path = _prepare_path(path)
    ET.ElementTree(root).write(abs_path, encoding="utf-8", xml_declaration=True)
    return abs_path


def _prepare_path(path: str) -> str:
    abs_path = os.path.abspath(path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    return abs_path
