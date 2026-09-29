import json
import pathlib

from census.__main__ import compatibility_record
from census.analysis import load_widget_packages, load_widget_repositories


ROOT = pathlib.Path(__file__).resolve().parents[1]
REQUIRED_FIELDS = {
    "repo",
    "url",
    "description",
    "stars",
    "repo_created",
    "repo_updated",
    "widget_created",
    "uses_anywidget",
}


def test_observable_payload_remains_compatible():
    rows = json.loads((ROOT / "assets/repos-complete.json").read_text())
    packages = {
        package.package: package for package in load_widget_packages(ROOT)
    }
    expected = [
        compatibility_record(
            repository,
            [packages[name] for name in repository.packages],
        )
        for repository in load_widget_repositories(ROOT)
        if repository.in_package_census
    ]
    assert rows == expected
    assert len(rows) == 538
    assert all(REQUIRED_FIELDS <= row.keys() for row in rows)
