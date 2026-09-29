"""Collect reproducible, read-only observations; never execute candidate code."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import pathlib
import re
import subprocess
from datetime import datetime, timezone
from urllib.parse import quote, urlencode, urlparse

import httpx
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "census" / "2026-09-29"
CACHE = OUT / "responses"
LEGACY_CUTOFF = "2024-11-24"
COLLECTION_CUTOFF = "2026-09-29T23:59:59Z"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def read_json(path):
    return json.loads(path.read_text())


def now():
    return datetime.now(timezone.utc).isoformat()


def github_repo(url):
    if not isinstance(url, str):
        return None
    parsed = urlparse(url)
    if parsed.hostname not in {"github.com", "www.github.com"}:
        return None
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2:
        return None
    return "/".join(parts[:2]).removesuffix(".git")


def dependencies(info):
    results = []
    for raw in info.get("requires_dist") or []:
        try:
            req = Requirement(raw)
            results.append(
                {
                    "name": canonicalize_name(req.name),
                    "raw": raw,
                    "marker": str(req.marker) if req.marker else None,
                    "extras": sorted(req.extras),
                }
            )
        except InvalidRequirement:
            results.append({"raw": raw, "parse_error": True})
    return results


class Fetcher:
    def __init__(self):
        CACHE.mkdir(parents=True, exist_ok=True)
        self.sem = asyncio.Semaphore(8)
        self.client = httpx.AsyncClient(
            timeout=45,
            follow_redirects=True,
            headers={
                "User-Agent": "anywidget-census/0.1 (https://github.com/manzt/anywidget-usage)"
            },
        )
        self.token = None
        self.calls = 0
        self.errors = []

    async def get(self, url, *, retry_errors=False):
        key = hashlib.sha256(url.encode()).hexdigest()
        path = CACHE / (key + ".json")
        if path.exists():
            item = read_json(path)
            if item["status"] == 200 or not retry_errors:
                return item
        headers = {}
        if urlparse(url).hostname == "api.github.com":
            if self.token is None:
                self.token = subprocess.check_output(
                    ["gh", "auth", "token"], text=True
                ).strip()
            headers = {
                "Authorization": "Bearer " + self.token,
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        async with self.sem:
            for attempt in range(4):
                try:
                    response = await self.client.get(url, headers=headers)
                    if (
                        response.status_code in {429, 500, 502, 503, 504}
                        and attempt < 3
                    ):
                        await asyncio.sleep(min(30, 2**attempt * 2))
                        continue
                    body = response.content
                    try:
                        data = response.json()
                    except ValueError:
                        data = {"body_text": response.text[:10000]}
                    item = {
                        "url": url,
                        "retrieved_at": now(),
                        "status": response.status_code,
                        "sha256": hashlib.sha256(body).hexdigest(),
                        "data": data,
                        "etag": response.headers.get("etag"),
                        "last_modified": response.headers.get("last-modified"),
                    }
                    break
                except httpx.HTTPError as error:
                    if attempt < 3:
                        await asyncio.sleep(2**attempt)
                        continue
                    item = {
                        "url": url,
                        "retrieved_at": now(),
                        "status": 0,
                        "error": str(error),
                    }
            write_json(path, item)
            self.calls += 1
            if item["status"] != 200:
                self.errors.append({"url": url, "status": item["status"]})
            return item

    async def close(self):
        await self.client.aclose()


async def discover(fetcher):
    packages = {}
    repos = {}
    coverage = []

    def add_package(name, source, detail=None):
        name = canonicalize_name(name)
        entry = packages.setdefault(name, {"name": name, "observations": []})
        observation = {"source": source}
        if detail:
            observation.update(detail)
        if observation not in entry["observations"]:
            entry["observations"].append(observation)

    def add_repo(name, source, detail=None):
        entry = repos.setdefault(name.casefold(), {"repo": name, "observations": []})
        observation = {"source": source}
        if detail:
            observation.update(detail)
        if observation not in entry["observations"]:
            entry["observations"].append(observation)

    for row in read_json(ROOT / "assets/repos.json"):
        add_repo(row["repo"], "legacy_census", {"legacy": row})
    gallery_path = OUT / "inputs/gallery.json"
    if gallery_path.exists():
        for row in read_json(gallery_path):
            add_repo(row["repo"], "built_with_anywidget_gallery")
    issue = await fetcher.get(
        "https://api.github.com/repos/manzt/anywidget-usage/issues/4"
    )
    if issue["status"] == 200:
        for name in re.findall(
            r"^- \[[ x]\] ([\w.-]+/[\w.-]+)", issue["data"]["body"], re.M
        ):
            add_repo(name, "legacy_discovery_issue", {"url": issue["data"]["html_url"]})

    async def reverse_dependencies(base):
        result = await fetcher.get(
            f"https://api.deps.dev/v3alpha/systems/pypi/packages/{base}"
        )
        if result["status"] != 200:
            coverage.append(
                {"source": "deps_dev", "base": base, "error": result["status"]}
            )
            return
        versions = result["data"].get("versions", [])

        async def one(version):
            v = version["versionKey"]["version"]
            url = f"https://deps.dev/_/s/pypi/p/{base}/v/{quote(v, safe='')}/dependents"
            response = await fetcher.get(url)
            if response["status"] != 200:
                coverage.append(
                    {
                        "source": "deps_dev_web_dependents",
                        "base": base,
                        "version": v,
                        "url": url,
                        "error": response["status"],
                    }
                )
                return
            data = response["data"]
            direct = data.get("directSample", [])
            coverage.append(
                {
                    "source": "deps_dev_web_dependents",
                    "base": base,
                    "version": v,
                    "url": url,
                    "direct_count": data.get("directCount"),
                    "returned_direct": len(direct),
                    "sample_truncated": data.get("directCount", 0) > len(direct),
                    "limitation": "Undocumented website endpoint; sampled resolved dependents, not all declared requirements.",
                }
            )
            for item in direct:
                add_package(
                    item["package"]["name"],
                    "deps_dev_direct_sample",
                    {
                        "base": base,
                        "base_version": v,
                        "observed_version": item["version"],
                        "url": url,
                    },
                )

        await asyncio.gather(*(one(v) for v in versions))
        print(
            f"Reverse dependencies {base}: {len(versions)} versions; {len(packages)} candidate packages",
            flush=True,
        )

    await asyncio.gather(
        reverse_dependencies("anywidget"), reverse_dependencies("ipywidgets")
    )

    # Literal source patterns complement dependency samples. Query coverage is saved.
    queries = [
        "anywidget filename:pyproject.toml",
        "anywidget filename:setup.py",
        "AnyWidget language:python filename:__init__.py",
        "DOMWidgetModel language:typescript filename:widget.ts",
        "DOMWidgetModel language:javascript filename:widget.js",
        "DOMWidget language:python filename:widget.py",
    ]
    for query in queries:
        count = 0
        total = None
        incomplete = False
        error = None
        for page in range(1, 11):
            url = "https://api.github.com/search/code?" + urlencode(
                {"q": query, "per_page": 100, "page": page}
            )
            response = await fetcher.get(url)
            if response["status"] != 200:
                error = response["status"]
                break
            data = response["data"]
            total = data.get("total_count", 0)
            incomplete |= data.get("incomplete_results", False)
            items = data.get("items", [])
            count += len(items)
            for item in items:
                if item["repository"].get("private"):
                    continue
                add_repo(
                    item["repository"]["full_name"],
                    "github_code_search",
                    {"query": query, "path": item["path"], "url": item["html_url"]},
                )
            print(f"Search {query}: {count}/{total}", flush=True)
            if len(items) < 100 or count >= total:
                break
            await asyncio.sleep(6.5)
        coverage.append(
            {
                "source": "github_code_search",
                "query": query,
                "reported_count": total,
                "returned_count": count,
                "incomplete_results": incomplete,
                "truncated": total is not None and count < total,
                "error": error,
            }
        )
        await asyncio.sleep(6.5)

    print(f"Mapping {len(repos)} repositories to published packages", flush=True)
    mapped = 0

    async def map_repo(entry):
        nonlocal mapped
        url = (
            "https://api.deps.dev/v3alpha/projects/"
            + quote("github.com/" + entry["repo"], safe="")
            + ":packageversions"
        )
        response = await fetcher.get(url)
        entry["mapping_url"] = url
        entry["mapping_status"] = response["status"]
        entry["packages"] = []
        if response["status"] == 200:
            versions = response["data"].get("versions", [])
            entry["mapping_at_result_limit"] = len(versions) >= 1500
            names = set()
            for item in versions:
                key = item["versionKey"]
                if key["system"] != "PYPI" or item["relationType"] != "SOURCE_REPO":
                    continue
                names.add(key["name"])
                # Preserve one mapping observation per provenance type, not thousands of versions.
                add_package(
                    key["name"],
                    "deps_dev_repo_mapping",
                    {
                        "repo": entry["repo"],
                        "provenance": item.get("relationProvenance"),
                        "url": url,
                    },
                )
            entry["packages"] = sorted(names)
        mapped += 1
        if mapped % 100 == 0:
            print(
                f"Mapped {mapped}/{len(repos)} repositories; {len(packages)} package candidates",
                flush=True,
            )

    await asyncio.gather(*(map_repo(entry) for entry in repos.values()))
    result = {
        "collected_at": now(),
        "packages": packages,
        "repositories": repos,
        "coverage": coverage,
    }
    write_json(OUT / "discovery.json", result)
    print(
        f"Saved discovery: {len(packages)} packages, {len(repos)} repositories",
        flush=True,
    )


async def metadata(fetcher):
    discovery = read_json(OUT / "discovery.json")
    packages = discovery["packages"]
    index_path = OUT / "pypi-index-candidates.json"
    if index_path.exists():
        for name in read_json(index_path)["names"]:
            name = canonicalize_name(name)
            entry = packages.setdefault(name, {"name": name, "observations": []})
            observation = {
                "source": "pypi_name_index",
                "pattern": "(^ipy|widget)",
                "url": "https://pypi.org/simple/",
            }
            if observation not in entry["observations"]:
                entry["observations"].append(observation)
        write_json(OUT / "discovery.json", discovery)
    results = {}
    done = 0

    async def one(name):
        nonlocal done
        url = f"https://pypi.org/pypi/{quote(name, safe='')}/json"
        response = await fetcher.get(url)
        entry = {
            "name": name,
            "url": url,
            "status": response["status"],
            "discovery": packages[name]["observations"],
        }
        if response["status"] == 200:
            data = response["data"]
            info = data["info"]
            urls = info.get("project_urls") or {}
            repo_links = sorted(
                {
                    repo
                    for repo in map(
                        github_repo, [*urls.values(), info.get("home_page")]
                    )
                    if repo
                }
            )
            releases = []
            for version, files in data.get("releases", {}).items():
                files = [
                    f
                    for f in files
                    if f.get("upload_time_iso_8601", "9999") <= COLLECTION_CUTOFF
                ]
                dates = [
                    f["upload_time_iso_8601"]
                    for f in files
                    if f.get("upload_time_iso_8601")
                ]
                if dates:
                    releases.append(
                        {"version": version, "uploaded_at": min(dates), "files": files}
                    )
            releases.sort(key=lambda r: r["uploaded_at"])
            entry.update(
                {
                    "canonical_name": info["name"],
                    "summary": info.get("summary"),
                    "latest_version": info["version"],
                    "project_urls": urls,
                    "github_repos": repo_links,
                    "dependencies": dependencies(info),
                    "releases": releases,
                    "first_package_release": releases[0]["uploaded_at"]
                    if releases
                    else None,
                    "latest_package_release": releases[-1]["uploaded_at"]
                    if releases
                    else None,
                    "classifiers": info.get("classifiers", []),
                    "latest_files": data.get("urls", []),
                }
            )
        results[name] = entry
        done += 1
        if done % 100 == 0:
            print(f"PyPI metadata {done}/{len(packages)}", flush=True)

    await asyncio.gather(*(one(name) for name in packages))
    write_json(OUT / "packages.json", results)
    print(f"Saved metadata: {len(results)} packages", flush=True)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["discover", "metadata"])
    args = parser.parse_args()
    fetcher = Fetcher()
    started = now()
    try:
        await {"discover": discover, "metadata": metadata}[args.stage](fetcher)
    finally:
        write_json(
            OUT / f"run-{args.stage}.json",
            {
                "started_at": started,
                "finished_at": now(),
                "new_requests": fetcher.calls,
                "errors": fetcher.errors,
            },
        )
        await fetcher.close()


if __name__ == "__main__":
    asyncio.run(main())
