# anywidget usage

An evidence-backed census of custom Jupyter widget packages and their adoption of anywidget.

The current snapshot contains 628 package candidates collected through September 29, 2026. Published package artifacts are inspected statically; candidate packages are never installed or executed. See [CONTEXT.md](./CONTEXT.md) for the domain language and [census/README.md](./census/README.md) for collection details and limitations.

## Explore the snapshot

```sh
uvx marimo edit --sandbox widget_census.py
```

The notebook decodes [assets/widgets.json](./assets/widgets.json) into typed `msgspec.Struct` records and uses the reusable transforms in [census/analysis.py](./census/analysis.py). It does not run network collection when opened.

## Rebuild derived outputs

```sh
uv venv --python 3.12
uv pip install --python .venv/bin/python -r census/requirements.txt
.venv/bin/python census/build.py
.venv/bin/python -m unittest discover -s census -p 'test_*.py'
```

`census/build.py` rebuilds the compact snapshot and review outputs from collected evidence already on disk. A full refresh has separate discovery, metadata, artifact-inspection, and history stages documented in [census/README.md](./census/README.md), because it performs many network requests and should be reviewed as a dated snapshot.

## Legacy collector

The Deno scripts and [assets/repos.json](./assets/repos.json) are the preserved repository-level workflow that produced the original Observable notebook. Its schedules are disabled; the old repository search can only be started manually. The Python census uses that inventory as one discovery and reconciliation input, so it remains available for provenance. New collection and analysis work should use the Python pipeline; repository counts from the legacy inventory are not directly comparable to package counts in the current census.
