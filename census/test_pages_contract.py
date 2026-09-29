import json
import pathlib

from census.__main__ import compatibility_record
from census.analysis import load_widget_repositories


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
    expected = [
        compatibility_record(repository)
        for repository in load_widget_repositories(ROOT)
    ]
    assert rows == expected
    assert len(rows) > 326
    assert all(REQUIRED_FIELDS <= row.keys() for row in rows)
