"""Validate the accepted snapshot and publish its compatibility export."""

from __future__ import annotations

from pathlib import Path

import msgspec

from census.analysis import load_widget_packages, load_widget_repositories
from census.model import WidgetRepository

ROOT = Path(__file__).resolve().parents[1]


def compatibility_record(repository: WidgetRepository) -> dict[str, object]:
    row = {
        "repo": repository.repo,
        "description": repository.description or "",
        "stars": repository.stars,
        "repo_created": repository.created.isoformat(),
        "repo_updated": (
            repository.last_push.isoformat() if repository.last_push else None
        ),
        "url": repository.url,
        "hidive": repository.hidive,
        "widget_created": (
            repository.widget_created.isoformat()
            if repository.widget_created
            else None
        ),
        "uses_anywidget": repository.implementation == "anywidget",
    }
    if repository.kind:
        row["kind"] = repository.kind
    return row


def main() -> None:
    packages = load_widget_packages(ROOT)
    repositories = load_widget_repositories(ROOT)
    names = [repository.repo.casefold() for repository in repositories]
    if len(names) != len(set(names)):
        raise ValueError("repository snapshot contains duplicate identities")

    rows = [compatibility_record(repository) for repository in repositories]
    payload = b"[\n" + b",\n".join(map(msgspec.json.encode, rows)) + b"\n]\n"
    (ROOT / "assets/repos-complete.json").write_bytes(payload)
    print(f"validated {len(packages)} packages and exported {len(rows)} repositories")


if __name__ == "__main__":
    main()
