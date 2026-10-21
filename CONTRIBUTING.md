# Contributing

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux / macOS
pip install -e ".[dev]"
```

## Checks

```bash
ruff check temporal_graph tests
mypy temporal_graph
pytest --cov=temporal_graph
```

All three must pass before opening a pull request.

## Regenerating font data

`temporal_graph/_font_data.py` and `_colors.py` are generated and committed.
Only change them through the script (needs `pip install -e ".[fonts]"`):

```bash
python tools/generate_font_data.py
```

## Guidelines

- Keep the public API backward compatible within the 0.x series.
- The core package has no runtime dependencies; keep it that way.
- Add tests for every new function and update `CHANGELOG.md`.
- Scratch files and benchmarks go in `./temp` (git-ignored).
