"""Produce review tables without rewriting the original curated census."""

import collections
import csv
import json

from collect import LEGACY_CUTOFF, OUT, ROOT, now, read_json, write_json
from packaging.version import InvalidVersion, Version

CRON_CUTOFF = "2025-01-24"
INFRASTRUCTURE = {"anywidget", "ipywidgets", "widgetsnbextension", "jupyterlab-widgets"}


def prerelease(version):
    try:
        return Version(version).is_prerelease
    except InvalidVersion:
        return None


OBSERVABLE_FIELDS = (
    "package",
    "summary",
    "pypi_url",
    "repositories",
    "known_in_legacy",
    "review_status",
    "role",
    "current_implementation_signals",
    "historical_implementation_signals",
    "first_package_release",
    "first_widget_observed_by",
    "first_widget_evidence_version",
    "first_anywidget_observed_by",
    "first_anywidget_evidence_version",
    "first_anywidget_evidence_is_prerelease",
    "first_stable_anywidget_observed_by",
    "first_stable_anywidget_evidence_version",
    "first_anywidget_dependency_observed",
    "earliest_extant_release_has_widget_evidence",
    "traditional_before_anywidget_observed",
    "migration_review",
    "first_widget_artifact_url",
    "first_anywidget_artifact_url",
    "review_note",
)


def observable_export(rows):
    records = [{key: row[key] for key in OBSERVABLE_FIELDS} for row in rows]
    text = (
        "[\n"
        + ",\n".join(
            json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            for record in records
        )
        + "\n]\n"
    )
    (ROOT / "assets/widgets.json").write_text(text)


def csv_file(name, rows, fields=None):
    fields = fields or list(rows[0]) if rows else fields or []
    with (OUT / name).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(
            {
                k: json.dumps(v, ensure_ascii=False)
                if isinstance(v, (list, dict))
                else v
                for k, v in row.items()
            }
            for row in rows
        )


def main():
    packages = read_json(OUT / "packages.json")
    latest = read_json(OUT / "latest-artifacts.json")
    discovery = read_json(OUT / "discovery.json")
    identities = read_json(OUT / "repository-identities.json")
    legacy = read_json(ROOT / "assets/repos.json")
    decisions = (
        read_json(ROOT / "census/decisions.json")
        if (ROOT / "census/decisions.json").exists()
        else {}
    )
    old_exclusions = {
        line.strip().casefold()
        for filename in ["exclude_repos_anywidget.txt", "exclude_repos_ipywidgets.txt"]
        for line in (ROOT / "assets" / filename).read_text().splitlines()
        if line.strip()
    }

    def canonical_repo(repo):
        repo = repo.strip().casefold()
        return identities.get(repo, {}).get("full_name", repo).casefold()

    legacy_by_repo = collections.defaultdict(list)
    for entry in legacy:
        legacy_by_repo[canonical_repo(entry["repo"])].append(entry)
    rows = []
    events = []
    for name, package in sorted(packages.items()):
        path = OUT / "history" / (name + ".json")
        history = read_json(path) if path.exists() else {}
        repo_names = set(package.get("github_repos", []))
        repo_names.update(
            o["repo"].strip() for o in package.get("discovery", []) if o.get("repo")
        )
        canonical = sorted({canonical_repo(repo) for repo in repo_names})
        old_rows = [
            entry for repo in canonical for entry in legacy_by_repo.get(repo, [])
        ]
        scans = history.get("artifact_scans", [])
        custom = [s for s in scans if s.get("custom_kinds")]
        current = latest.get(name, {})
        if current.get("custom_kinds") and not any(
            s.get("sha256") == current.get("sha256") for s in custom
        ):
            custom.append(current)
        custom.sort(key=lambda s: s.get("uploaded_at", "9999"))
        aw = [s for s in custom if "anywidget" in s["custom_kinds"]]
        traditional = [
            s for s in custom if "traditional_custom_widget" in s["custom_kinds"]
        ]
        first = custom[0] if custom else {}
        first_aw = aw[0] if aw else {}
        stable_aw = next(
            (s for s in aw if prerelease(s.get("version", "")) is False), {}
        )
        dep = history.get("first_observed_anywidget_dependency") or {}
        first_release = (
            package.get("releases", [{}])[0] if package.get("releases") else {}
        )
        first_release_scan = next(
            (s for s in custom if s.get("version") == first_release.get("version")), {}
        )
        prior_traditional = [
            s
            for s in traditional
            if first_aw and s["uploaded_at"] < first_aw["uploaded_at"]
        ]
        classification = "source_supported_candidate" if custom else "unresolved"
        role = "custom_widget_candidate" if custom else "unresolved"
        if name in INFRASTRUCTURE:
            role = "widget_infrastructure"
        elif old_rows and all(r.get("kind") == "framework" for r in old_rows):
            role = "legacy_framework"
        decision = decisions.get(name, {})
        role = decision.get("role", role)
        classification = decision.get("status", classification)
        in_scope = bool(custom) and role not in {
            "widget_infrastructure",
            "legacy_framework",
            "host_framework",
            "example_or_test",
            "duplicate_distribution",
        }
        row = {
            "package": name,
            "summary": package.get("summary", ""),
            "pypi_url": f"https://pypi.org/project/{name}/",
            "repositories": canonical,
            "legacy_repositories": sorted({r["repo"].strip() for r in old_rows}),
            "known_in_legacy": bool(old_rows),
            "role": role,
            "review_status": classification,
            "legacy_exclusion_list_match": any(
                repo.strip().casefold() in old_exclusions for repo in repo_names
            ),
            "source_supported_widget_candidate": in_scope,
            "current_implementation_signals": current.get("custom_kinds", []),
            "historical_implementation_signals": sorted(
                {k for s in custom for k in s["custom_kinds"]}
            ),
            "first_package_release": package.get("first_package_release", ""),
            "first_widget_observed_by": first.get("uploaded_at", ""),
            "first_widget_evidence_version": first.get("version", ""),
            "first_anywidget_observed_by": first_aw.get("uploaded_at", ""),
            "first_anywidget_evidence_version": first_aw.get("version", ""),
            "first_anywidget_evidence_is_prerelease": prerelease(
                first_aw.get("version", "")
            ),
            "first_stable_anywidget_observed_by": stable_aw.get("uploaded_at", ""),
            "first_stable_anywidget_evidence_version": stable_aw.get("version", ""),
            "first_anywidget_dependency_observed": dep.get("uploaded_at", ""),
            "earliest_extant_release_has_widget_evidence": bool(first_release_scan),
            "earliest_extant_release_widget_kinds": first_release_scan.get(
                "custom_kinds", []
            ),
            "traditional_before_anywidget_observed": bool(prior_traditional),
            "migration_review": decision.get(
                "migration_review",
                "review_component_continuity"
                if prior_traditional
                else "not_established",
            ),
            "published_since_curation": (package.get("first_package_release") or "")[
                :10
            ]
            > LEGACY_CUTOFF,
            "published_since_cron_stopped": (
                package.get("first_package_release") or ""
            )[:10]
            > CRON_CUTOFF,
            "widget_observed_since_curation": first.get("uploaded_at", "")[:10]
            > LEGACY_CUTOFF,
            "latest_version": package.get("latest_version", ""),
            "release_count": len(package.get("releases", [])),
            "historical_artifacts_inspected": len(scans),
            "release_metadata_inspected": history.get(
                "metadata_scanned_release_count", 0
            ),
            "metadata_history_truncated": history.get(
                "metadata_history_truncated", False
            ),
            "metadata_errors": history.get("metadata_errors", 0),
            "latest_artifact_status": current.get("status", ""),
            "first_widget_artifact_url": first.get("url", ""),
            "first_anywidget_artifact_url": first_aw.get("url", ""),
            "evidence_file": "history/" + name + ".json" if history else "",
            "discovery_sources": sorted(
                {o["source"] for o in package.get("discovery", [])}
            ),
            "review_note": decision.get("note", ""),
        }
        rows.append(row)
        if in_scope:
            observations = [
                (
                    "first_extant_package_release",
                    row["first_package_release"],
                    first_release.get("version", ""),
                    row["pypi_url"],
                    "exact_upload_of_available_release",
                ),
                (
                    "custom_widget_present_by",
                    row["first_widget_observed_by"],
                    row["first_widget_evidence_version"],
                    row["first_widget_artifact_url"],
                    "observed_by",
                ),
                (
                    "anywidget_implementation_present_by",
                    row["first_anywidget_observed_by"],
                    row["first_anywidget_evidence_version"],
                    row["first_anywidget_artifact_url"],
                    "observed_by",
                ),
                (
                    "anywidget_dependency_observed",
                    dep.get("uploaded_at", ""),
                    dep.get("version", ""),
                    dep.get("url", ""),
                    "dependency_observation_only",
                ),
            ]
            for kind, date, version, url, certainty in observations:
                if date and date[:10] > LEGACY_CUTOFF:
                    events.append(
                        {
                            "package": name,
                            "event": kind,
                            "date": date,
                            "version": version,
                            "certainty": certainty,
                            "evidence_url": url,
                            "prerelease": prerelease(version),
                            "known_in_legacy": bool(old_rows),
                            "after_cron_stopped": date[:10] > CRON_CUTOFF,
                        }
                    )

    widgets = [r for r in rows if r["source_supported_widget_candidate"]]
    additions = [r for r in widgets if not r["known_in_legacy"]]
    gap = [r for r in additions if r["published_since_curation"]]
    cohorts = [r for r in widgets if r["earliest_extant_release_has_widget_evidence"]]
    enriched_legacy = []
    for old in legacy:
        repo = canonical_repo(old["repo"])
        matched = [r for r in rows if repo in r["repositories"]]
        enriched_legacy.append(
            {
                **old,
                "canonical_repo": repo,
                "repository_status": identities.get(old["repo"].strip().casefold(), {}),
                "package_names": [r["package"] for r in matched],
                "source_supported_packages": [
                    r["package"]
                    for r in matched
                    if r["source_supported_widget_candidate"]
                ],
                "mapping_status": "package_links_found" if matched else "unresolved",
                "legacy_widget_date_is_unverified": True,
            }
        )
    write_json(OUT / "repos-enriched.json", enriched_legacy)
    write_json(OUT / "package-review.json", rows)
    csv_file("package-review.csv", rows)
    csv_file("widget-candidates.csv", widgets)
    observable_export(widgets)
    csv_file("new-candidates.csv", additions)
    csv_file("gap-events.csv", sorted(events, key=lambda e: e["date"]))
    csv_file("newly-published-in-gap.csv", gap)
    csv_file(
        "legacy-repository-review.csv",
        [
            {
                "legacy_repo": r["repo"],
                "canonical_repo": r["canonical_repo"],
                "github_status": r["repository_status"].get("status"),
                "package_names": r["package_names"],
                "source_supported_packages": r["source_supported_packages"],
                "mapping_status": r["mapping_status"],
                "legacy_uses_anywidget": r["uses_anywidget"],
                "legacy_widget_created": r.get("widget_created"),
            }
            for r in enriched_legacy
        ],
    )
    counts = collections.Counter()
    for row in cohorts:
        kinds = row["earliest_extant_release_widget_kinds"]
        category = (
            "both"
            if len(kinds) > 1
            else "anywidget"
            if "anywidget" in kinds
            else "traditional"
        )
        counts[(row["first_package_release"][:4], category)] += 1
    cohort_rows = [
        {
            "year": year,
            "implementation_in_first_extant_release": kind,
            "packages": count,
        }
        for (year, kind), count in sorted(counts.items())
    ]
    csv_file("publication-cohorts.csv", cohort_rows)
    summary = {
        "generated_at": now(),
        "curation_cutoff": LEGACY_CUTOFF,
        "cron_cutoff": CRON_CUTOFF,
        "legacy_rows_preserved": len(enriched_legacy),
        "legacy_unique_canonical_repositories": len(legacy_by_repo),
        "legacy_rows_with_package_links": sum(
            bool(r["package_names"]) for r in enriched_legacy
        ),
        "package_candidates": len(rows),
        "pypi_metadata_found": sum(p.get("status") == 200 for p in packages.values()),
        "source_supported_widget_candidates": len(widgets),
        "source_supported_candidates_outside_legacy": len(additions),
        "outside_legacy_first_published_since_curation": len(gap),
        "outside_legacy_first_published_since_cron": sum(
            r["published_since_cron_stopped"] for r in additions
        ),
        "widget_evidence_in_first_extant_release": len(cohorts),
        "packages_with_anywidget_source": sum(
            bool(r["first_anywidget_observed_by"]) for r in widgets
        ),
        "traditional_then_anywidget_candidates": sum(
            r["traditional_before_anywidget_observed"] for r in widgets
        ),
        "assistant_reviewed_packages": sum(
            r["review_status"] == "accepted_after_assistant_review" for r in widgets
        ),
        "assistant_reviewed_new_packages": sum(
            r["review_status"] == "accepted_after_assistant_review" for r in additions
        ),
        "assistant_reviewed_component_transitions": sum(
            r["migration_review"] == "component_transition_supported" for r in widgets
        ),
        "latest_artifact_statuses": dict(
            collections.Counter(r["latest_artifact_status"] for r in rows)
        ),
        "github_search_coverage": [
            c for c in discovery["coverage"] if c["source"] == "github_code_search"
        ],
        "sampled_reverse_dependency_responses": sum(
            c.get("sample_truncated", False) for c in discovery["coverage"]
        ),
        "history_packages": len(list((OUT / "history").glob("*.json"))),
        "release_metadata_observations": sum(
            r["release_metadata_inspected"] for r in rows
        ),
        "historical_artifact_observations": sum(
            r["historical_artifacts_inspected"] for r in rows
        ),
        "cohorts": cohort_rows,
    }
    write_json(OUT / "summary.json", summary)
    render_html(rows, summary)
    render_plot(cohort_rows)
    text = f"""Enrichment snapshot — September 29, 2026

The original {len(legacy)} records are preserved in assets/repos.json. The enriched copy is repos-enriched.json. This pass works at package level; do not add package counts to the old repository count.

The collection examined {len(rows):,} package candidates and found released-source evidence for {len(widgets):,} candidate widget packages. Of these, {len(additions):,} are outside the legacy repository inventory, including {len(gap):,} whose earliest currently available PyPI release falls after November 24, 2024. These are candidates for inclusion; source detection does not settle aliases, forks, templates, or component continuity.

{summary["legacy_rows_with_package_links"]} of the {len(legacy)} legacy records now have package links. All unresolved and unavailable repositories remain in the data. Repository redirects reduce the original inventory to {len(legacy_by_repo)} distinct canonical repository identities.

There are {summary["traditional_then_anywidget_candidates"]} packages with a traditional custom-widget signal before an anywidget source signal. These are migration review candidates, not automatically confirmed ports of the same component.

The data includes {summary["release_metadata_observations"]:,} historical release metadata observations and {summary["historical_artifact_observations"]:,} historical artifact inspections. Dates from inspected artifacts mean “present by this release,” not the date of invention. Missing or deleted earlier releases, alternate distribution contents, and incomplete static analysis prevent an exhaustive historical claim.

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
"""
    (OUT / "report.md").write_text(text)
    print(
        json.dumps(
            {
                k: v
                for k, v in summary.items()
                if k
                not in {"cohorts", "github_search_coverage", "latest_artifact_statuses"}
            },
            indent=2,
        )
    )


def render_html(rows, summary):
    payload = json.dumps(rows, ensure_ascii=False).replace("<", "\\u003c")
    page = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Widget census review · September 2026</title><style>
body{font:15px system-ui,sans-serif;margin:32px;color:#172d39;background:#f8fafb}h1{font-size:28px;margin-bottom:8px}p{max-width:1000px;line-height:1.55}a{color:#006e99}input,select,button{font:inherit;padding:9px;border:1px solid #bccdd5;border-radius:6px;background:white}nav{display:flex;gap:12px;flex-wrap:wrap;position:sticky;top:0;background:#f8fafb;padding:12px 0}table{width:100%;border-collapse:collapse;background:white}th,td{padding:11px;border-bottom:1px solid #dbe3e8;text-align:left;vertical-align:top}th{font-size:13px;color:#415c6b}small{display:block;color:#5c707b;margin-top:5px}details{max-width:400px}summary{cursor:pointer}code{font-size:12px}#count{font-weight:600;margin:14px 0}.badge{font-size:12px;color:#175a43}td:first-child{min-width:150px}</style>
<h1>Widget census review</h1><p>Collection through September 29, 2026. Evidence from published package contents; inclusion and migration decisions remain reviewable. “Observed by” dates are supported by an inspected artifact and may be later than the actual origin.</p>
<p><a href="report.md">Method and findings</a> · <a href="widget-candidates.csv">Widget candidates CSV</a> · <a href="gap-events.csv">Dated gap events CSV</a> · <a href="legacy-repository-review.csv">Legacy repository review</a></p>
<nav><input id="search" placeholder="Find package or repository" aria-label="Search packages"><select id="scope" aria-label="Candidate scope"><option value="new">New source-supported candidates</option value="gap">New candidates published in the gap</option><option value="widgets">All source-supported candidates</option><option value="legacy">Linked to legacy census</option><option value="migration">Traditional → anywidget evidence</option><option value="all">All discovered packages</option></select><select id="implementation" aria-label="Implementation"><option value="all">Any implementation</option><option value="anywidget">Anywidget source observed</option><option value="traditional_custom_widget">Traditional source observed</option></select><select id="sort" aria-label="Sort order"><option value="newest">Newest package first</option><option value="oldest">Oldest package first</option><option value="name">Package name</option></select></nav>
<div id="count" aria-live="polite"></div><table><thead><tr><th>Package / repository</th><th>Package first published</th><th>Custom widget observed by</th><th>Anywidget observed by</th><th>Evidence / review</th></tr></thead><tbody id="rows"></tbody></table>
<script type="application/json" id="data">PAYLOAD</script><script>
const data=JSON.parse(document.querySelector('#data').textContent);const byId=id=>document.getElementById(id);
const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const date=s=>s?escape(s.slice(0,10)):'Unknown';
function render(){const q=byId('search').value.toLowerCase(),scope=byId('scope').value,impl=byId('implementation').value;
let rows=data.filter(r=>(r.package+' '+r.repositories.join(' ')+' '+r.summary).toLowerCase().includes(q)).filter(r=>impl==='all'||r.historical_implementation_signals.includes(impl)).filter(r=>scope==='all'||(scope==='widgets'&&r.source_supported_widget_candidate)||(scope==='new'&&r.source_supported_widget_candidate&&!r.known_in_legacy)||(scope==='gap'&&r.source_supported_widget_candidate&&!r.known_in_legacy&&r.published_since_curation)||(scope==='legacy'&&r.known_in_legacy)||(scope==='migration'&&r.traditional_before_anywidget_observed));
const sort=byId('sort').value;rows.sort((a,b)=>sort==='name'?a.package.localeCompare(b.package):(sort==='oldest'?1:-1)*(a.first_package_release||'').localeCompare(b.first_package_release||''));byId('count').textContent=rows.length+' packages';
byId('rows').innerHTML=rows.map(r=>`<tr><td><a href="${escape(r.pypi_url)}">${escape(r.package)}</a><small>${r.repositories.map(repo=>`<a href="https://github.com/${escape(repo)}">${escape(repo)}</a>`).join('<br>')}</small><small>${escape(r.summary)}</small></td><td>${date(r.first_package_release)}<small>${r.earliest_extant_release_has_widget_evidence?'Widget code verified in first available release':'First release widget status unresolved'}</small></td><td>${date(r.first_widget_observed_by)}<small>${escape(r.first_widget_evidence_version)}</small></td><td>${date(r.first_anywidget_observed_by)}<small>${escape(r.first_anywidget_evidence_version)}</small></td><td><span class="badge">${escape(r.review_status)}</span><small>${escape(r.historical_implementation_signals.join(', '))}</small><details><summary>Evidence and caveats</summary><p>${escape(r.review_note||'Source evidence collected; scope and historical interpretation need review.')}</p>${r.evidence_file?`<a href="${escape(r.evidence_file)}">Release/source observations</a><br>`:''}${r.first_widget_artifact_url?`<a href="${escape(r.first_widget_artifact_url)}">First observed widget artifact</a><br>`:''}<small>${r.historical_artifacts_inspected} historical artifacts; ${r.release_metadata_inspected} release metadata observations. ${escape(r.latest_artifact_status)}</small><small>Discovery: ${escape(r.discovery_sources.join(', '))}</small></details></td></tr>`).join('');}
for(const id of ['search','scope','implementation','sort'])byId(id).addEventListener('input',render);render();
</script></html>"""
    (OUT / "review.html").write_text(page.replace("PAYLOAD", payload))


def render_plot(cohorts):
    import os

    os.environ.setdefault("MPLCONFIGDIR", str(OUT / ".matplotlib"))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    years = sorted({int(r["year"]) for r in cohorts})
    fig, ax = plt.subplots(figsize=(11, 5.5), layout="constrained")
    bottom = [0] * len(years)
    for kind, label, color in [
        ("traditional", "Traditional custom module", "#eda94d"),
        ("anywidget", "Anywidget", "#07648d"),
        ("both", "Both", "#59b5b9"),
    ]:
        counts = [
            sum(
                r["packages"]
                for r in cohorts
                if int(r["year"]) == year
                and r["implementation_in_first_extant_release"] == kind
            )
            for year in years
        ]
        ax.bar(years, counts, bottom=bottom, label=label, color=color)
        bottom = [a + b for a, b in zip(bottom, counts)]
    ax.axvspan(2024.9, 2026.5, color="#cad6dd", alpha=0.22, zorder=-1)
    ax.set(
        title="Published packages with widget evidence in their first available release",
        xlabel="Earliest currently available PyPI release year",
        ylabel="Package candidates",
    )
    ax.set_ylim(0, max(bottom, default=1) * 1.12)
    ax.set_xticks(years)
    ax.set_xticklabels(
        [str(y) + ("*" if y == 2026 else "") for y in years], rotation=45
    )
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False)
    fig.text(
        0.01,
        -0.025,
        "* 2026 through September 29. Evidence-qualified subset; aliases and scope still need review. Not an exhaustive widget-birth count.",
        fontsize=9,
    )
    fig.savefig(OUT / "publication-cohorts.png", dpi=160, bbox_inches="tight")
    fig.savefig(OUT / "publication-cohorts.svg", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
