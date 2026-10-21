"""temporal_graph — model temporal graphs, compute on them, and render them.

Core API:

- :class:`~temporal_graph.graph.TemporalGraph` and :class:`~temporal_graph.graph.Edge`
- :func:`~temporal_graph.render.render` → :class:`~temporal_graph.figure.Figure`
- :func:`~temporal_graph.animate.animate` → :class:`~temporal_graph.animate.Animation`

Algorithms:

- :mod:`~temporal_graph.journeys`: foremost, latest-departure, fastest and
  shortest journeys, reachability, temporal distance.
- :mod:`~temporal_graph.connectivity`: temporal diameter, connectivity time,
  outgoing influence time, continuous / f- / T-interval connectivity.
- :mod:`~temporal_graph.flows`: temporal Menger (disjoint journeys, separators).
- :mod:`~temporal_graph.expansion`: static expansion.
- :mod:`~temporal_graph.dissemination`: flooding and k-token forwarding.
- :mod:`~temporal_graph.design`: labelings that preserve paths or reachability.
- :mod:`~temporal_graph.periodic`: linear availability ``a·x + b``.
- :mod:`~temporal_graph.generators` and :mod:`~temporal_graph.random_models`.
- :mod:`~temporal_graph.classic`: exact temporal matching, exploration, TSP.

Also :mod:`~temporal_graph.utils`, :mod:`~temporal_graph.analysis` and
:mod:`~temporal_graph.exporters`.
"""

from . import (
    analysis,
    classic,
    connectivity,
    design,
    dissemination,
    expansion,
    exporters,
    flows,
    generators,
    journeys,
    periodic,
    random_models,
    utils,
)
from .animate import Animation, animate
from .figure import Figure
from .graph import Edge, TemporalGraph, TimeEdge
from .journeys import Journey
from .render import render

__all__ = [
    "Animation",
    "Edge",
    "Figure",
    "Journey",
    "TemporalGraph",
    "TimeEdge",
    "analysis",
    "animate",
    "classic",
    "connectivity",
    "design",
    "dissemination",
    "expansion",
    "exporters",
    "flows",
    "generators",
    "journeys",
    "periodic",
    "random_models",
    "render",
    "utils",
]
__version__ = "0.1.0"
