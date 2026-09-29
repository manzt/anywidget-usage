"""Reconcile source URLs and read package declarations from otherwise unmapped repos."""

import ast
import asyncio
import base64
import configparser
import pathlib
from urllib.parse import quote

import tomllib
from collect import OUT, ROOT, Fetcher, read_json, write_json
from packaging.utils import canonicalize_name


def declared_names(path, text):
    try:
        if path.endswith("pyproject.toml"):
            data = tomllib.loads(text)
            name = data.get("project", {}).get("name") or data.get("tool", {}).get(
                "poetry", {}
            ).get("name")
            return [name] if isinstance(name, str) else []
        if path.endswith("setup.cfg"):
            parser = configparser.ConfigParser(interpolation=None)
            parser.read_string(text)
            name = parser.get("metadata", "name", fallback=None)
            return [name] if name else []
        tree = ast.parse(text)
        constants = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        constants[target.id] = node.value.value
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and (
                (isinstance(node.func, ast.Name) and node.func.id == "setup")
                or (isinstance(node.func, ast.Attribute) and node.func.attr == "setup")
            ):
                for kw in node.keywords:
                    if kw.arg == "name":
                        value = (
                            kw.value.value
                            if isinstance(kw.value, ast.Constant)
                            else constants.get(kw.value.id)
                            if isinstance(kw.value, ast.Name)
                            else None
                        )
                        if isinstance(value, str):
                            names.append(value)
        return names
    except (SyntaxError, ValueError, configparser.Error, tomllib.TOMLDecodeError):
        return []


async def main():
    packages = read_json(OUT / "packages.json")
    discovery = read_json(OUT / "discovery.json")
    identities = read_json(OUT / "repository-identities.json")
    legacy = read_json(ROOT / "assets/repos.json")
    fetcher = Fetcher()
    # Resolve URLs in package metadata as well as URLs from the old inventory.
    repos = {
        repo.strip() for p in packages.values() for repo in p.get("github_repos", [])
    }

    async def resolve(repo):
        if repo.casefold() in identities:
            return
        url = "https://api.github.com/repos/" + quote(repo, safe="/")
        response = await fetcher.get(url)
        result = {"requested_repo": repo, "url": url, "status": response["status"]}
        if response["status"] == 200:
            result.update(
                {
                    k: response["data"].get(k)
                    for k in [
                        "id",
                        "full_name",
                        "html_url",
                        "default_branch",
                        "archived",
                        "fork",
                        "private",
                    ]
                }
            )
        identities[repo.casefold()] = result

    await asyncio.gather(*(resolve(repo) for repo in repos))
    write_json(OUT / "repository-identities.json", identities)

    def canonical(repo):
        key = repo.strip().casefold()
        return identities.get(key, {}).get("full_name", key).casefold()

    matched = set()
    for package in packages.values():
        linked = list(package.get("github_repos", [])) + [
            o["repo"] for o in package.get("discovery", []) if o.get("repo")
        ]
        matched.update(map(canonical, linked))
    targets = {
        canonical(r["repo"]): r["repo"].strip()
        for r in legacy
        if canonical(r["repo"]) not in matched
    }
    print(
        f"After URL reconciliation, reading manifests for {len(targets)} unmapped legacy repository identities",
        flush=True,
    )
    manifest_evidence = []
    repo_sem = asyncio.Semaphore(5)

    async def inspect_repo(canonical_name, original):
        async with repo_sem:
            identity = identities.get(original.casefold(), {})
            if identity.get("status") != 200 or identity.get("private"):
                return
            branch = identity.get("default_branch") or "main"
            tree_url = f"https://api.github.com/repos/{quote(canonical_name, safe='/')}/git/trees/{quote(branch, safe='')}?recursive=1"
            tree = await fetcher.get(tree_url)
            if tree["status"] != 200:
                return
            items = [
                i
                for i in tree["data"].get("tree", [])
                if pathlib.PurePosixPath(i["path"]).name
                in {"pyproject.toml", "setup.py", "setup.cfg"}
                and i["type"] == "blob"
                and i.get("size", 0) < 200000
                and not any(
                    part
                    in {"test", "tests", "examples", "node_modules", ".venv", "venv"}
                    for part in pathlib.PurePosixPath(i["path"]).parts
                )
            ]
            items.sort(
                key=lambda i: (len(pathlib.PurePosixPath(i["path"]).parts), i["path"])
            )
            for item in items[:20]:
                blob = await fetcher.get(item["url"])
                if blob["status"] != 200:
                    continue
                text = base64.b64decode(blob["data"]["content"]).decode(
                    "utf8", errors="replace"
                )
                names = declared_names(item["path"], text)
                for name in names:
                    normalized = canonicalize_name(name)
                    if not normalized or any(
                        c not in "abcdefghijklmnopqrstuvwxyz0123456789-"
                        for c in normalized
                    ):
                        continue
                    observation = {
                        "source": "repository_package_declaration",
                        "repo": canonical_name,
                        "path": item["path"],
                        "blob_sha": item["sha"],
                        "url": item["url"],
                    }
                    entry = discovery["packages"].setdefault(
                        normalized, {"name": normalized, "observations": []}
                    )
                    if observation not in entry["observations"]:
                        entry["observations"].append(observation)
                    manifest_evidence.append({"package": normalized, **observation})
            if tree["data"].get("truncated") or len(items) > 20:
                manifest_evidence.append(
                    {
                        "repo": canonical_name,
                        "coverage_limited": True,
                        "tree_truncated": tree["data"].get("truncated"),
                        "manifests_found": len(items),
                    }
                )

    try:
        await asyncio.gather(
            *(inspect_repo(name, original) for name, original in targets.items())
        )
        write_json(OUT / "discovery.json", discovery)
        write_json(OUT / "manifest-mappings.json", manifest_evidence)
        print(
            f"Added {len(manifest_evidence)} manifest observations; {len(discovery['packages'])} package candidates",
            flush=True,
        )
    finally:
        await fetcher.close()


if __name__ == "__main__":
    asyncio.run(main())
