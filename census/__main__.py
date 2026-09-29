"""Validate the accepted snapshot and publish its compatibility export."""

from __future__ import annotations

from pathlib import Path

import msgspec

from census.analysis import load_widget_packages, load_widget_repositories
from census.model import ImplementationSignal, WidgetPackage, WidgetRepository

ROOT = Path(__file__).resolve().parents[1]


def compatibility_record(
    repository: WidgetRepository,
    packages: list[WidgetPackage],
) -> dict[str, object]:
    observed = [package.widget_observed_by for package in packages]
    widget_created = min(date for date in observed if date is not None)
    uses_anywidget = any(
        ImplementationSignal.ANYWIDGET in package.current_implementation_signals
        for package in packages
    )
    row = {
        "repo": repository.repo,
        "description": repository.description
        or next((package.summary for package in packages if package.summary), ""),
        "stars": repository.stars,
        "repo_created": repository.created.isoformat() if repository.created else None,
        "repo_updated": (
            repository.last_push.isoformat() if repository.last_push else None
        ),
        "url": repository.url,
        "hidive": repository.hidive,
        "widget_created": widget_created.isoformat(),
        "uses_anywidget": uses_anywidget,
    }
    if repository.kind:
        row["kind"] = repository.kind
    return row


def main() -> None:
    packages = load_widget_packages(ROOT)
    repositories = load_widget_repositories(ROOT)
    packages_by_name = {package.package: package for package in packages}
    names = [repository.repo.casefold() for repository in repositories]
    if len(names) != len(set(names)):
        raise ValueError("repository snapshot contains duplicate identities")

    rows = []
    linked_package_names = set()
    for repository in repositories:
        if not repository.in_package_census:
            continue
        linked = [packages_by_name[name] for name in repository.packages]
        if not linked:
            raise ValueError(f"{repository.repo} has no linked packages")
        linked_package_names.update(repository.packages)
        rows.append(compatibility_record(repository, linked))
    payload = b"[\n" + b",\n".join(map(msgspec.json.encode, rows)) + b"\n]\n"
    (ROOT / "assets/repos-complete.json").write_bytes(payload)
    print(
        f"validated {len(packages)} packages; projected "
        f"{len(linked_package_names)} onto {len(rows)} repositories"
    )


if __name__ == "__main__":
    main()
