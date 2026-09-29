"""Static inspection of published artifacts; candidate code is never imported."""

from __future__ import annotations

import ast
import asyncio
import hashlib
import io
import pathlib
import tarfile
import warnings
import zipfile
from urllib.parse import urlparse

from collect import OUT, Fetcher, now, read_json, write_json

MAX_ARCHIVE = 16 * 1024 * 1024
MAX_SOURCE = 2 * 1024 * 1024
MAX_UNPACKED_SOURCE = 48 * 1024 * 1024
SKIP_PARTS = {
    "test",
    "tests",
    "testing",
    "example",
    "examples",
    "demo",
    "demos",
    "docs",
    "doc",
    "node_modules",
    ".venv",
    "venv",
    "site-packages",
}
BUILTIN_MODULES = {
    "@jupyter-widgets/base",
    "@jupyter-widgets/controls",
    "jupyter-js-widgets",
}


def dotted(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = dotted(node.value)
        return prefix + "." + node.attr if prefix else None
    return None


def source_findings(source, path):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError):
        return [], False
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                aliases[alias.asname or alias.name.split(".")[0]] = (
                    alias.name if alias.asname else alias.name.split(".")[0]
                )
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            for alias in node.names:
                aliases[alias.asname or alias.name] = node.module + "." + alias.name

    def resolve(node):
        name = dotted(node)
        if not name:
            return ""
        head, *tail = name.split(".")
        return ".".join([aliases.get(head, head), *tail])

    results = []
    local_classes = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        bases = [resolve(base) for base in node.bases]
        attributes = {}
        for statement in node.body:
            if isinstance(statement, ast.Assign):
                for target in statement.targets:
                    if isinstance(target, ast.Name):
                        attributes[target.id] = ast.unparse(statement.value)
            elif (
                isinstance(statement, ast.AnnAssign)
                and isinstance(statement.target, ast.Name)
                and statement.value
            ):
                attributes[statement.target.id] = ast.unparse(statement.value)
        kind = None
        custom = False
        if any(
            base == "anywidget.AnyWidget"
            or base == "anywidget.widget.AnyWidget"
            or local_classes.get(base) == "anywidget"
            for base in bases
        ):
            kind = "anywidget"
            custom = True
        elif any(
            base.startswith("ipywidgets.") or base.startswith("IPython.html.widgets.")
            for base in bases
        ):
            kind = "ipywidgets_subclass"
            module_values = [
                value
                for name, value in attributes.items()
                if name in {"_model_module", "_view_module"}
            ]
            custom = bool(module_values) and not all(
                any(module in value for module in BUILTIN_MODULES)
                for value in module_values
            )
            if custom:
                kind = "traditional_custom_widget"
        if kind:
            local_classes[node.name] = kind
            results.append(
                {
                    "kind": kind,
                    "custom_signal": custom,
                    "path": path,
                    "class": node.name,
                    "line": node.lineno,
                    "bases": bases,
                    "attributes": {
                        k: v[:500]
                        for k, v in attributes.items()
                        if k.startswith(("_model", "_view", "_esm"))
                    },
                    "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                    "snippet": "\n".join(
                        source.splitlines()[
                            node.lineno - 1 : min(node.end_lineno, node.lineno + 9)
                        ]
                    ),
                }
            )
    return results, True


def inspect_archive(body, filename):
    members = []
    findings = []
    scanned = 0
    parse_errors = 0
    skipped_large = 0
    total_size = 0
    if filename.endswith((".whl", ".zip")):
        archive = zipfile.ZipFile(io.BytesIO(body))
        members = [
            (item.filename, item.file_size, lambda item=item: archive.read(item))
            for item in archive.infolist()
            if not item.is_dir()
        ]
    else:
        archive = tarfile.open(fileobj=io.BytesIO(body), mode="r:*")
        members = [
            (item.name, item.size, lambda item=item: archive.extractfile(item).read())
            for item in archive.getmembers()
            if item.isfile()
        ]
    try:
        for path, size, read in members:
            parts = pathlib.PurePosixPath(path).parts
            # Strip the source-distribution root, then ignore non-product examples/tests.
            relative = (
                parts[1:] if not filename.endswith(".whl") and len(parts) > 1 else parts
            )
            if any(part.casefold() in SKIP_PARTS for part in relative):
                continue
            if not path.endswith(".py"):
                continue
            if size > MAX_SOURCE or total_size + size > MAX_UNPACKED_SOURCE:
                skipped_large += 1
                continue
            total_size += size
            source = read().decode("utf-8", errors="replace")
            scanned += 1
            result, parsed = source_findings(source, path)
            findings.extend(result)
            parse_errors += not parsed
        return {
            "findings": findings,
            "python_files_scanned": scanned,
            "parse_errors": parse_errors,
            "oversized_files_skipped": skipped_large,
            "custom_kinds": sorted({r["kind"] for r in findings if r["custom_signal"]}),
        }
    finally:
        archive.close()


def select_file(files):
    usable = [
        f
        for f in files
        if f.get("size", MAX_ARCHIVE + 1) <= MAX_ARCHIVE
        and (f["filename"].endswith((".whl", ".tar.gz", ".zip", ".tar.bz2")))
    ]
    # Prefer universal wheels, then other wheels, then source archives.
    return min(
        usable,
        key=lambda f: (
            not f["filename"].endswith("none-any.whl"),
            not f["filename"].endswith(".whl"),
            f.get("size", 0),
        ),
        default=None,
    )


class Inspector:
    def __init__(self, fetcher):
        self.fetcher = fetcher
        self.sem = asyncio.Semaphore(6)
        self.locks = {}

    async def scan(self, file):
        digest = file.get("digests", {}).get("sha256")
        if not digest:
            return {"status": "missing_digest"}
        result_path = OUT / "artifact-evidence" / (digest + ".json")
        async with self.locks.setdefault(digest, asyncio.Lock()):
            if result_path.exists():
                return read_json(result_path)
            url = file["url"]
            if urlparse(url).hostname != "files.pythonhosted.org":
                return {"status": "unexpected_artifact_host", "url": url}
            async with self.sem:
                record = {
                    "url": url,
                    "filename": file["filename"],
                    "sha256": digest,
                    "uploaded_at": file.get("upload_time_iso_8601"),
                    "inspected_at": now(),
                    "yanked": file.get("yanked", False),
                }
                try:
                    for attempt in range(3):
                        body = bytearray()
                        async with self.fetcher.client.stream("GET", url) as response:
                            if (
                                response.status_code in {429, 500, 502, 503, 504}
                                and attempt < 2
                            ):
                                await asyncio.sleep(2 ** (attempt + 1))
                                continue
                            response.raise_for_status()
                            async for block in response.aiter_bytes():
                                body.extend(block)
                                if len(body) > MAX_ARCHIVE:
                                    raise ValueError("Archive exceeds size limit")
                            break
                    if hashlib.sha256(body).hexdigest() != digest:
                        raise ValueError("Artifact SHA-256 mismatch")
                    record.update(inspect_archive(body, file["filename"]))
                    record["status"] = "ok"
                    record["bytes"] = len(body)
                except Exception as error:
                    record.update({"status": "error", "error": str(error)})
                write_json(result_path, record)
                return record


async def latest(fetcher):
    packages = read_json(OUT / "packages.json")
    results = {}
    inspector = Inspector(fetcher)
    done = 0

    async def one(name, entry):
        nonlocal done
        sources = {o["source"] for o in entry.get("discovery", [])}
        dependency_names = {d.get("name") for d in entry.get("dependencies", [])}
        if sources == {"pypi_name_index"} and not (
            name.startswith("ipy")
            or dependency_names & {"anywidget", "ipywidgets"}
            or any("Jupyter" in c for c in entry.get("classifiers", []))
        ):
            results[name] = {
                "status": "name_only_without_widget_metadata_signal",
                "version": entry.get("latest_version"),
            }
            done += 1
            return
        file = select_file(entry.get("latest_files", []))
        if file:
            result = await inspector.scan(file)
            results[name] = {"version": entry.get("latest_version"), **result}
        else:
            results[name] = {
                "status": "no_supported_artifact_under_16MiB",
                "version": entry.get("latest_version"),
            }
        done += 1
        if done % 100 == 0:
            print(
                f"Inspected latest artifacts {done}/{len(packages)}; custom signals in {sum(bool(r.get('custom_kinds')) for r in results.values())}",
                flush=True,
            )

    await asyncio.gather(*(one(name, entry) for name, entry in packages.items()))
    write_json(OUT / "latest-artifacts.json", results)


async def main():
    fetcher = Fetcher()
    try:
        await latest(fetcher)
    finally:
        await fetcher.close()


if __name__ == "__main__":
    asyncio.run(main())
