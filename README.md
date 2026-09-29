# anywidget usage

An evidence-backed census of custom Jupyter widget packages and their adoption of anywidget.

The current snapshot contains 628 package candidates collected through September 29, 2026. Published package artifacts are inspected statically; candidate packages are never installed or executed. See [CONTEXT.md](./CONTEXT.md) for the domain language and [census/README.md](./census/README.md) for collection details and limitations.

## Explore the snapshot

```sh
uv run marimo edit widget_census.py
```

The notebook decodes [assets/widgets.json](./assets/widgets.json) into typed `msgspec.Struct` records and uses the reusable transforms in [census/analysis.py](./census/analysis.py). It does not run network collection when opened.

The original Observable notebook continues to load [repos-complete.json](https://manzt.github.io/anywidget-usage/repos-complete.json). That 326-row payload is committed under `assets/` and deployed unchanged as a compatibility endpoint; rebuilding the Python census does not rewrite it.

## Rebuild derived outputs

```sh
uv run python census/build.py
uv run python -m unittest discover -s census -p 'test_*.py'
```

`census/build.py` rebuilds the compact snapshot and review outputs from collected evidence already on disk. A full refresh has separate discovery, metadata, artifact-inspection, and history stages documented in [census/README.md](./census/README.md), because it performs many network requests and should be reviewed as a dated snapshot.

## Legacy inventory

[assets/repos.json](./assets/repos.json) and the exclusion lists are the preserved inputs from the repository-level workflow that produced the original Observable notebook. The retired Deno collector has been removed. The Python census uses the inventory for discovery and reconciliation; repository counts from it are not directly comparable to package counts in the current census.
