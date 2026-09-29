"""Dated dependency and implementation observations, with explicit coverage gaps."""

import asyncio
from urllib.parse import quote

from collect import OUT, ROOT, Fetcher, dependencies, now, read_json, write_json
from inspect_artifacts import Inspector, select_file
from packaging.version import InvalidVersion, Version

ANYWIDGET_EARLIEST_PYPI = "2022-10-26"


def observations_for_release(data):
    raw = data["info"].get("requires_dist")
    return {
        "dependencies": dependencies(data["info"]),
        "requires_dist_reported": raw is not None,
    }


async def main():
    packages = read_json(OUT / "packages.json")
    latest = read_json(OUT / "latest-artifacts.json")
    legacy = {r["repo"].casefold(): r for r in read_json(ROOT / "assets/repos.json")}
    identities_path = OUT / "repository-identities.json"
    identities = read_json(identities_path) if identities_path.exists() else {}
    for row in list(legacy.values()):
        legacy[row["repo"].strip().casefold()] = row
        resolved = identities.get(row["repo"].strip().casefold(), {})
        if resolved.get("full_name"):
            legacy[resolved["full_name"].casefold()] = row
    targets = {}
    for name, package in packages.items():
        linked_repos = set(repo.casefold() for repo in package.get("github_repos", []))
        linked_repos.update(
            o["repo"].casefold() for o in package.get("discovery", []) if o.get("repo")
        )
        legacy_rows = [legacy[repo] for repo in linked_repos if repo in legacy]
        if name in {
            "anywidget",
            "ipywidgets",
            "widgetsnbextension",
            "jupyterlab-widgets",
        }:
            continue
        if (latest.get(name, {}).get("custom_kinds") or legacy_rows) and package.get(
            "releases"
        ):
            targets[name] = package
    print(f"History targets: {len(targets)} packages", flush=True)
    fetcher = Fetcher()
    inspector = Inspector(fetcher)
    results = {}
    active = asyncio.Semaphore(10)
    release_counter = 0
    done = 0

    async def one(name, package):
        nonlocal release_counter, done
        async with active:
            releases = package["releases"]
            later = [
                r for r in releases if r["uploaded_at"][:10] >= ANYWIDGET_EARLIEST_PYPI
            ]
            # Preserve a declared bound on exceptionally large histories.
            selected = later if len(later) <= 1000 else later[:500] + later[-500:]
            metadata_results = []

            async def release_metadata(release):
                nonlocal release_counter
                url = f"https://pypi.org/pypi/{quote(name, safe='')}/{quote(release['version'], safe='')}/json"
                response = await fetcher.get(url)
                record = {
                    "version": release["version"],
                    "uploaded_at": release["uploaded_at"],
                    "url": url,
                    "status": response["status"],
                }
                if response["status"] == 200:
                    record.update(observations_for_release(response["data"]))
                metadata_results.append(record)
                release_counter += 1
                if release_counter % 500 == 0:
                    print(f"Historical release metadata: {release_counter}", flush=True)

            await asyncio.gather(*(release_metadata(r) for r in selected))
            metadata_results.sort(key=lambda r: r["uploaded_at"])
            anywidget_releases = [
                r
                for r in metadata_results
                if any(d.get("name") == "anywidget" for d in r.get("dependencies", []))
            ]
            history_scans = []
            scanned_versions = set()

            async def scan_release(release, reason):
                version = release["version"]
                if version in scanned_versions:
                    return next(
                        (r for r in history_scans if r["version"] == version), None
                    )
                scanned_versions.add(version)
                file = select_file(release["files"])
                if not file:
                    record = {
                        "version": version,
                        "release_uploaded_at": release["uploaded_at"],
                        "reason": reason,
                        "status": "no_supported_artifact_under_16MiB",
                    }
                else:
                    record = {
                        "version": version,
                        "release_uploaded_at": release["uploaded_at"],
                        "reason": reason,
                        **await inspector.scan(file),
                    }
                history_scans.append(record)
                return record

            # Verify the first extant release; scan forward a bounded number if inconclusive.
            for release in releases[:12]:
                scanned = await scan_release(release, "earliest_release_search")
                if scanned and scanned.get("custom_kinds"):
                    break
            # Verify the dependency transition against distributed source; also inspect its predecessor.
            if anywidget_releases:
                first = anywidget_releases[0]
                index = next(
                    i
                    for i, r in enumerate(releases)
                    if r["version"] == first["version"]
                )
                # Dependencies can be added after an implementation ships (e.g. optional imports).
                # Walk backward from the metadata boundary to find earlier source evidence.
                first_available_scan = next(
                    (
                        s
                        for s in history_scans
                        if s["version"] == releases[0]["version"]
                    ),
                    {},
                )
                if index and "anywidget" not in first_available_scan.get(
                    "custom_kinds", []
                ):
                    for previous in reversed(releases[max(0, index - 20) : index]):
                        scanned = await scan_release(
                            previous, "before_first_observed_anywidget_dependency"
                        )
                        if (
                            scanned
                            and "traditional_custom_widget"
                            in scanned.get("custom_kinds", [])
                            and "anywidget" not in scanned.get("custom_kinds", [])
                        ):
                            break
                for release in releases[index : index + 8]:
                    scanned = await scan_release(
                        release, "anywidget_implementation_search"
                    )
                    if scanned and "anywidget" in scanned.get("custom_kinds", []):
                        break
                for observation in anywidget_releases:
                    try:
                        stable = not Version(observation["version"]).is_prerelease
                    except InvalidVersion:
                        stable = False
                    if stable:
                        release = next(
                            r
                            for r in releases
                            if r["version"] == observation["version"]
                        )
                        await scan_release(
                            release, "first_stable_release_with_anywidget_dependency"
                        )
                        break
            if (
                latest.get(name, {}).get("status") == "ok"
                and package["latest_version"] not in scanned_versions
            ):
                release = next(
                    (r for r in releases if r["version"] == package["latest_version"]),
                    None,
                )
                if release:
                    await scan_release(release, "latest_release")
            history_scans.sort(
                key=lambda r: r.get("uploaded_at") or r["release_uploaded_at"]
            )
            record = {
                "name": name,
                "completed_at": now(),
                "first_package_release": releases[0]["uploaded_at"],
                "release_count": len(releases),
                "metadata_eligible_release_count": len(later),
                "metadata_scanned_release_count": len(metadata_results),
                "metadata_history_truncated": len(selected) < len(later),
                "metadata_errors": sum(r["status"] != 200 for r in metadata_results),
                "first_observed_anywidget_dependency": anywidget_releases[0]
                if anywidget_releases
                else None,
                "release_metadata": metadata_results,
                "artifact_scans": history_scans,
                "date_interpretation": "Source observations establish present-by dates; they do not prove first invention or complete release coverage.",
            }
            write_json(OUT / "history" / (name + ".json"), record)
            results[name] = {
                "release_count": len(releases),
                "metadata_scanned": len(metadata_results),
                "artifact_scans": len(history_scans),
            }
            done += 1
            if done % 20 == 0:
                print(
                    f"History complete {done}/{len(targets)} packages; metadata {release_counter}",
                    flush=True,
                )

    try:
        await asyncio.gather(*(one(name, package) for name, package in targets.items()))
        write_json(OUT / "history-index.json", results)
        write_json(
            OUT / "run-history.json",
            {
                "finished_at": now(),
                "targets": len(targets),
                "release_metadata_observations": release_counter,
                "new_requests": fetcher.calls,
                "errors": fetcher.errors,
            },
        )
    finally:
        await fetcher.close()


if __name__ == "__main__":
    asyncio.run(main())
