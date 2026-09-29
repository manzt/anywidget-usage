# anywidget usage

An evidence-backed census of custom Jupyter widget packages and their adoption of anywidget.

The current snapshot contains 628 package candidates collected through September 29, 2026. See [census/README.md](./census/README.md) for the methodology and update process.

## Explore the snapshot

```sh
uv run marimo edit widget_census.py
```

The notebook loads [assets/widgets.json](./assets/widgets.json) and [assets/repositories.json](./assets/repositories.json) through the typed models and transforms under `census/`.

The original Observable notebook continues to load [repos-complete.json](https://manzt.github.io/anywidget-usage/repos-complete.json), a repository-level projection of the widget snapshot.

## Validate the snapshot

```sh
uv run python -m census
uv run --group test pytest
uv run marimo check widget_census.py
```
