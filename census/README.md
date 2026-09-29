This directory defines the snapshot schema, analysis transforms, and methodology for the widget census.

The durable outputs are [assets/widgets.json](../assets/widgets.json) for packages and [assets/repositories.json](../assets/repositories.json) for repositories. They encode the accepted state as of September 29, 2026. [model.py](model.py) validates their schema and [analysis.py](analysis.py) contains the plot derivations.

The original assets/repos.json is preserved. The enriched repository view keeps every original row, including unavailable projects. New discovery works at Python distribution level: these counts must not be added directly to the old repository count. Repository redirects, package aliases, monorepos, demos, and forks require explicit decisions.

Run with Python 3.12 or newer. `uv run` resolves the locked project dependencies.

```sh
uv run python -m unittest discover -s census -p 'test_*.py'
```

Candidates were discovered from the legacy inventory and gallery, reverse-dependency samples across indexed anywidget and ipywidgets versions, GitHub source queries, repository/package mappings, packaging manifests, and a PyPI name-index scan for names matching `(^ipy|widget)`. These routes are broad but incomplete. Name and dependency matches nominate candidates; they do not establish that a package implements a custom widget.

deps.dev supplied samples of resolved dependents and was treated as a supplemental source rather than a complete census. Repository redirects, package aliases, monorepos, demos, and forks were resolved conservatively.

Published archives were inspected statically and never installed or executed. A direct anywidget subclass is a positive signal. A traditional signal requires an ipywidgets subclass with a custom model or view module. Merely using controls or declaring a dependency is insufficient. Dynamic and indirect implementations may be missed.

The scanner chooses one supported distribution per release, preferring universal wheels, with a 16 MiB archive limit, 2 MiB per-source-file limit, and 48 MiB total inspected source limit. Tests, docs, and examples are excluded by directory name. Platform-specific wheels and alternate artifacts may differ; the evidence is for the exact file whose hash is recorded.

Historical dependency metadata is inspected for releases from October 26, 2022 onward, the date of anywidget's earliest available PyPI release. Histories above 1,000 eligible releases are explicitly truncated. Source inspections cover up to 12 initial releases, up to 20 releases before the first observed anywidget dependency, up to eight from that dependency boundary, the first stable version with the dependency, and the latest release. This targeted coverage establishes dated observations, not exact invention dates.

Interpret the exported dates carefully:

| Field | Meaning |
| --- | --- |
| first_package_release | Earliest available PyPI release upload; deleted history may precede it |
| first_widget_observed_by | Earliest inspected artifact containing a custom implementation signal |
| first_anywidget_observed_by | Earliest inspected artifact containing an anywidget implementation signal |
| first_stable_anywidget_observed_by | Earliest inspected non-prerelease artifact with that signal |
| first_anywidget_dependency_observed | Earliest scanned release metadata declaring anywidget, including optional dependencies |
| traditional_before_anywidget_observed | Both signals exist in chronological order; component continuity needs review before calling this a port |

The public-launch date of January 18, 2023 is not used to decide whether a package was created with anywidget or ported. Prereleases are flagged. Today’s implementation is never retroactively treated as its implementation in every earlier year.

Each exported package retains its review status, evidence versions, artifact URLs, and review note. Future refreshes should produce a new dated snapshot, preserve these meanings, and review changes before replacing the accepted assets.

Relevant source documentation: [PyPI APIs](https://docs.pypi.org/api/), [distribution metadata dataset](https://docs.pypi.org/api/bigquery/), [deps.dev API](https://docs.deps.dev/api/v3alpha/), and [GitHub search limitations](https://docs.github.com/en/rest/search/search).
