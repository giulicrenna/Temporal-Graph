import runpy
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = sorted((ROOT / "examples").rglob("*.py"))


@pytest.mark.parametrize("script", EXAMPLES, ids=lambda p: p.name)
def test_example_runs_and_writes_valid_files(script, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [str(script)])
    runpy.run_path(str(script), run_name="__main__")
    out = capsys.readouterr().out
    assert out

    svg_paths = [
        ROOT / token
        for line in out.splitlines()
        for token in line.split()
        if token.endswith(".svg")
    ]
    for path in svg_paths:
        assert ET.parse(path).getroot().tag.endswith("svg")
