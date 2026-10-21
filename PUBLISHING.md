# Publishing to PyPI

The distribution name is `temporal-graph`; the import name is `temporal_graph`.
The version lives in one place: `__version__` in `temporal_graph/__init__.py`
(`pyproject.toml` reads it dynamically).

## 1. One-time setup

1. Create accounts on [test.pypi.org](https://test.pypi.org) and
   [pypi.org](https://pypi.org) and enable 2FA on both.
2. Check that `temporal-graph` is free on PyPI. If it is taken, change
   `name` in `pyproject.toml`.
3. Add `[project.urls]` to `pyproject.toml` once the GitHub repository has a
   public URL (Homepage, Issues, Changelog).
4. PyPI renders the README outside the repository, so relative image links
   break. Before the first release replace `output/example_decisions.png` in
   `README.md` with the absolute `raw.githubusercontent.com` URL of that file.

## 2. Release checklist

```bash
pip install -e ".[dev]"
ruff check temporal_graph tests
mypy temporal_graph
pytest
```

1. Set the new version in `temporal_graph/__init__.py`.
2. Move the `[Unreleased]` entries of `CHANGELOG.md` under the new version.
3. Commit, then tag: `git tag v0.1.0 && git push --tags`.

## 3. Build and check locally

```bash
rm -rf dist
python -m build
twine check dist/*
```

`dist/` must contain one `.tar.gz` and one `.whl`.

## 4. Dry run on TestPyPI

Create an API token at test.pypi.org (Account settings, API tokens), then:

```bash
twine upload --repository testpypi dist/*
```

Username is `__token__`, password is the token. Verify in a clean virtualenv:

```bash
python -m venv /tmp/check && /tmp/check/bin/pip install \
  --index-url https://test.pypi.org/simple/ temporal-graph
/tmp/check/bin/python -c "import temporal_graph; print(temporal_graph.__version__)"
```

TestPyPI never accepts the same version twice, so a failed dry run needs a
version bump (for example `0.1.1`) before retrying.

## 5. Release to PyPI

Manual:

```bash
twine upload dist/*
```

Automated (recommended): `.github/workflows/publish.yml` publishes when a
GitHub release is created, using PyPI Trusted Publishing (no stored token).

1. On pypi.org open the project, then Publishing, and add a trusted publisher:
   your GitHub owner and repository, workflow `publish.yml`, environment `pypi`.
   For the very first release use "Add a pending publisher" from your account
   page.
2. In the GitHub repository create an environment named `pypi`.
3. Create a release from the tag. The workflow builds, checks and uploads.

## 6. Afterwards

* A published version can be yanked but never replaced or deleted from reuse.
* Bump to the next development version and open a new `[Unreleased]` section.
