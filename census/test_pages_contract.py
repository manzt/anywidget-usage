import json
import pathlib
import unittest


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


class LegacyPagesContractTests(unittest.TestCase):
    def test_observable_payload_remains_compatible(self):
        rows = json.loads((ROOT / "assets/repos-complete.json").read_text())
        self.assertEqual(len(rows), 326)
        self.assertTrue(all(REQUIRED_FIELDS <= row.keys() for row in rows))


if __name__ == "__main__":
    unittest.main()
