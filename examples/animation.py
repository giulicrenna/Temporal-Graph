"""Animate the evolution of two example graphs as GIFs.

Run from the repo root with::

    python examples/animation.py

Writes ``output/social_network.gif`` and ``output/process_flow.gif``, plus a
PNG still of one frame.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
EXAMPLES = Path(__file__).resolve().parent
if str(EXAMPLES) not in sys.path:
    sys.path.insert(0, str(EXAMPLES))

import process_flow  # noqa: E402
import social_network  # noqa: E402

from temporal_graph import animate  # noqa: E402


def main() -> None:
    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)

    social = animate(social_network.build_graph(), frame_duration=900)
    print(Path(social.save(out_dir / "social_network.gif")).relative_to(ROOT))

    pipeline = animate(process_flow.build_graph(), frame_duration=700, loop=0)
    print(Path(pipeline.save(out_dir / "process_flow.gif")).relative_to(ROOT))

    still = pipeline.frames[-1].savefig(out_dir / "process_flow_last_frame.png")
    print(Path(still).relative_to(ROOT))


if __name__ == "__main__":
    main()
