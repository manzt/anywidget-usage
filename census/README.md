This directory contains the reproducible collection and analysis code for the widget census.

The durable outputs are [assets/widgets.json](../assets/widgets.json) for packages and [assets/repositories.json](../assets/repositories.json) for repositories. `build.py` regenerates both. Dated collection responses, evidence, review tables, and reports remain on disk and are ignored by version control.

The original assets/repos.json is preserved. The enriched repository view keeps every original row, including unavailable projects. New discovery works at Python distribution level: these counts must not be added directly to the old repository count. Repository redirects, package aliases, monorepos, demos, and forks require explicit decisions.

Run with Python 3.12 or newer. `uv run` resolves the locked project dependencies; candidate packages are never installed or executed.

```sh
uv run python census/discover_index.py
uv run python census/collect.py discover
uv run python census/collect.py metadata
uv run python census/resolve_repositories.py
uv run python census/reconcile.py
uv run python census/collect.py metadata
uv run python census/inspect_artifacts.py
uv run python census/history.py
uv run python -m census.build
uv run python -m unittest discover -s census -p 'test_*.py'
```

The collector uses the existing authenticated GitHub CLI for read-only API access. The token remains in memory and is sent only to api.github.com. Search results for private repositories are excluded from discovery. Source response caches stay local and are ignored by git. No workflows, issues, repositories, or external services are modified by these commands.

The checked-in scripts currently target the September 29, 2026 snapshot. To collect a new snapshot, update OUT and COLLECTION_CUTOFF in collect.py, copy or recollect the input gallery in the new snapshot's inputs directory, and preserve the previous snapshot. Repeating a stage uses cached observations, so it resumes collection rather than pretending to refresh already cached data. A new snapshot requires a new response-cache directory.

The collection routes are the legacy inventory and issue, local gallery, reverse-dependency samples across every indexed anywidget/ipywidgets version, GitHub source queries, repository/package mapping, packaging-manifest declarations, and a full PyPI name-index scan. The index query nominates names matching (^ipy|widget); name matches alone do not establish scope. GitHub query coverage and dependency sample truncation are recorded in discovery.json. We did not run a bulk BigQuery dependency query.

The deps.dev website endpoint supplies samples of resolved dependents and is undocumented. Its responses are preserved, and it is a supplemental discovery source, not a complete reverse-dependency census. Repository/package mappings from deps.dev preserve their provenance type; unverified metadata is not treated as an attestation. A source repository declaring a package name supports a mapping but can still be stale or ambiguous.

Static inspection reads archives in memory, verifies their published SHA-256 hashes, and parses Python source. It resolves direct import aliases and some inheritance within a source file. A direct anywidget subclass is a positive source signal. A traditional implementation signal requires an ipywidgets subclass to declare a custom model/view module. Merely using controls or declaring a dependency is insufficient. Indirect, dynamic, vendored, and otherwise unrecognized implementations remain potential false negatives.

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

Review decisions are recorded separately in decisions.json with a reviewer, date, reason, and evidence reference. An assistant review is labeled as such and is not independent human validation. Everything else remains a source-supported candidate or unresolved. The legacy exclusion files mix already processed and rejected projects, so they should not silently suppress fresh evidence.

Validation checks cover import aliases, ordinary control composition, custom module declarations, dependency markers, metadata that lags implementation, prereleases, and repository URL identity. Generated tables should retain all legacy rows and link every accepted date back to a versioned artifact or release response.

Relevant source documentation: [PyPI APIs](https://docs.pypi.org/api/), [distribution metadata dataset](https://docs.pypi.org/api/bigquery/), [deps.dev API](https://docs.deps.dev/api/v3alpha/), and [GitHub search limitations](https://docs.github.com/en/rest/search/search).
