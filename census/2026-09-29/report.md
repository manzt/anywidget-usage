Enrichment snapshot — September 29, 2026

The original 327 records are preserved in assets/repos.json. The enriched copy is repos-enriched.json. This pass works at package level; do not add package counts to the old repository count.

The collection examined 2,554 package candidates and found released-source evidence for 628 candidate widget packages. Of these, 347 are outside the legacy repository inventory, including 198 whose earliest currently available PyPI release falls after November 24, 2024. These are candidates for inclusion; source detection does not settle aliases, forks, templates, or component continuity.

299 of the 327 legacy records now have package links. All unresolved and unavailable repositories remain in the data. Repository redirects reduce the original inventory to 323 distinct canonical repository identities.

There are 27 packages with a traditional custom-widget signal before an anywidget source signal. These are migration review candidates, not automatically confirmed ports of the same component.

The data includes 9,500 historical release metadata observations and 3,108 historical artifact inspections. Dates from inspected artifacts mean “present by this release,” not the date of invention. Missing or deleted earlier releases, alternate distribution contents, and incomplete static analysis prevent an exhaustive historical claim.

Open review.html to filter and inspect packages. The CSV files support spreadsheet or notebook analysis:

- widget-candidates.csv: packages with a released-source implementation signal, with known infrastructure/framework roles excluded.
- new-candidates.csv: those outside the reconciled legacy inventory.
- newly-published-in-gap.csv: new candidates first published after the curation cutoff.
- gap-events.csv: individually dated package, source, and dependency observations, with their distinct meanings retained.
- legacy-repository-review.csv: every original repository and its current identity/package mapping.
- publication-cohorts.csv and publication-cohorts.png: a conservative subset with widget evidence in the earliest currently available package release. This is not a corrected version of the original widget-birth chart.

The manual curation cutoff is November 24, 2024. The automated collection cutoff is January 24, 2025. Both flags are available. The 2026 cohort covers data retrieved through September 29.

Discovery combines the legacy inventory and issue, the local gallery, sampled resolved dependents across all available versions of anywidget and ipywidgets, GitHub source queries, repository/package mappings, and a complete PyPI index scan for names matching (^ipy|widget). This remains incomplete discovery: reverse-dependency results are sampled, some GitHub queries hit the 1,000-result ceiling, indirect implementations can be missed, and unrelated package names can escape these routes. The bulk PyPI BigQuery dependency census was not run.

Static inspection resolves direct import aliases and some local subclass inheritance. Traditional custom-widget signals require a declared custom model/view module; ordinary control composition is not counted. Tests/examples/docs are excluded by path. At most one supported artifact under 16 MiB is chosen for a release. Source files above 2 MiB and source totals above 48 MiB are skipped. Parse failures and skipped artifacts remain visible. No candidate package was installed or executed.

Historical dependency metadata is scanned from anywidget's earliest PyPI publication, October 26, 2022. This is different from its January 2023 public launch and is not used to infer port status. Histories over 1,000 eligible releases are explicitly capped. Source searches inspect up to 12 initial releases, up to 20 releases before the dependency boundary, up to eight from that boundary, the first stable dependency release, and the latest release. These are evidence observations, not a proof that intervening releases lacked widgets.

Raw source responses, retrieval times, content digests, query coverage, immutable artifact URLs and SHA-256 hashes are stored alongside the tables. Inclusion decisions belong in census/decisions.json and are kept separate from collection. See census/README.md for reproduction and interpretation.
