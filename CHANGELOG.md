# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/) and the
project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Time-edge model on `TemporalGraph`: `time_edges()`, `labels()`, `age`,
  `label_count`, `from_time_edges()`; O(1) lookup by instant.
- `expansion.static_expansion()`.
- `journeys`: foremost (one pass, strict and non-strict), latest departure,
  fastest, shortest, enumeration, reachability, temporal distance, `Journey`.
- `connectivity`: temporal diameter, connectivity time, outgoing influence
  time, future-set curve, continuous / f- / T-interval connectivity.
- `flows`: temporal Menger for out-disjoint and edge-disjoint journeys with
  min separators; exact node-disjoint search.
- `dissemination`: flooding and k-token forwarding simulation.
- `design`: DAG, directed-ring and reachability-preserving labelings with
  checkers.
- `periodic`: linear availability, generalized CRT, lifetime-independent
  foremost search.
- `generators` (moving star, alternating matchings, Soifer, rotating-centre
  star) and `random_models` (random temporal clique and formulas (5)–(7)).
- `classic`: exact temporal matching, exploration and temporal TSP.
- `examples/temporal_algorithms.py`.
- `examples/markov_chain.py`: hitting times as foremost journeys on a
  simulated trajectory, and the animated net probability flow of the chain.
- Packaging metadata (`pyproject.toml`), MIT license, CI and publish workflows.
- `utils`: `from_edge_list`, `snapshot_diff`, `filter_edges`, `subgraph`.
- `analysis`: `degree_timeline`, `connected_components_at`, `edge_persistence`,
  `is_temporally_acyclic`.
- `exporters`: JSON (round trip), CSV and dynamic GEXF.
- Test suite, `py.typed` marker, `PUBLISHING.md`, `CONTRIBUTING.md`.

- Native PNG export: `render(graph, mode)` returns a `Figure` with
  `savefig(path, format=None, scale=2.0)`, `to_svg()` and `to_png_bytes()`.
  A built-in rasterizer and embedded DejaVu Sans outlines replace `cairosvg`.
- Animated GIF export: `animate(graph, frame_duration=800, loop=0)` returns an
  `Animation` (node-link view, one frame per timestep) with `save("x.gif")`,
  `to_gif_bytes()` and `frames`. Pure-Python GIF encoder with median-cut
  palette and LZW.
- `animate(..., positions={node: (x, y)})` for custom layouts (e.g. trees);
  coordinates are scaled to avoid overlaps and short labels go inside nodes.
- `examples/binary_tree.py`: a 63-node binary tree built and taken apart,
  exported as GIF, PNG/SVG still and timeline image.
- `Figure`, `Animation` and `animate` are exported from the package root.
- `tools/generate_font_data.py` to regenerate the embedded font and color data.

### Changed
- `render(graph, mode, path)` still returns the written path; the format now
  follows the extension (`.png` writes a real PNG, other extensions write SVG).
- The package has no optional or runtime dependencies; `cairosvg` is gone.
- The example scripts write both SVG and PNG.

### Fixed
- In `decisions` mode an edge that persisted between timesteps showed only
  floating dots / arrowheads with no connection line. It is now drawn as a
  faded connection (with its weight and direction) and the legend lists it as
  "unchanged". The PNG rasterizer honors `opacity`, `stroke-opacity` and
  `fill-opacity`.
- Connections in the first column no longer overlap the node labels; the left
  margin is sized from the label widths.
- Weight labels no longer sit under neighbouring lines or on node rows; they
  are drawn last on a white backing and clear of the snake's wobble.
- Dashed disconnect lines use flat caps, so the gaps are visible.
- Arrowheads are plain polygons (no SVG markers) and the line stops at the
  arrow base instead of poking through the tip.
- In `decisions` mode lifelines and event marks of a column share one lane
  assignment, so different edges no longer collide.
- The legend is measured from real text widths, wraps cleanly and is in English.

## [0.1.0]

### Added
- `Edge` and `TemporalGraph` data model.
- SVG renderer with `connections` and `decisions` modes.
