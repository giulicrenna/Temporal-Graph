import csv
import json
import xml.etree.ElementTree as ET

import pytest

from temporal_graph import Edge, TemporalGraph
from temporal_graph.exporters import from_json, to_csv, to_dict, to_gexf, to_json

GEXF = "{http://gexf.net/1.3}"


@pytest.fixture
def graph():
    g = TemporalGraph(["a", "b", "c"])
    g.add_snapshot(0, [Edge("a", "b", weight=2.5, color="#f00")])
    g.add_snapshot(1, [Edge("b", "c", directed=True)])
    g.add_snapshot(2, [Edge("a", "b")])
    g.add_snapshot(3, [Edge("a", "b")])
    return g


def test_json_round_trip(graph):
    restored = from_json(to_json(graph))
    assert to_dict(restored) == to_dict(graph)
    assert restored.edge_at(0, ("a", "b")).color == "#f00"
    assert restored.edge_at(1, ("b", "c")).directed is True


def test_to_json_is_valid_json(graph):
    assert json.loads(to_json(graph))["nodes"] == ["a", "b", "c"]


def test_to_csv(graph, tmp_path):
    out = to_csv(graph, str(tmp_path / "sub" / "g.csv"))
    with open(out, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 4
    assert rows[0] == {
        "t": "0", "u": "a", "v": "b", "directed": "False", "weight": "2.5", "color": "#f00",
    }
    assert rows[1]["directed"] == "True"
    assert rows[1]["color"] == ""


def test_to_gexf(graph, tmp_path):
    out = to_gexf(graph, str(tmp_path / "g.gexf"))
    root = ET.parse(out).getroot()
    assert root.find(f"{GEXF}graph").get("mode") == "dynamic"
    assert [n.get("id") for n in root.iter(f"{GEXF}node")] == ["a", "b", "c"]

    edges = {(e.get("source"), e.get("target")): e for e in root.iter(f"{GEXF}edge")}
    assert edges[("b", "c")].get("type") == "directed"
    assert edges[("a", "b")].get("weight") == "2.5"
    spells = [(s.get("start"), s.get("end")) for s in edges[("a", "b")].iter(f"{GEXF}spell")]
    assert spells == [("0", "0"), ("2", "3")]
