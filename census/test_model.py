import pathlib
import unittest

from census.analysis import (
    classify_widgets,
    implementation_totals,
    load_widget_packages,
    package_frame,
)
from census.model import ImplementationSignal, WidgetPackage

ROOT = pathlib.Path(__file__).resolve().parents[1]


class SnapshotModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packages = load_widget_packages(ROOT)
        cls.classified = classify_widgets(package_frame(cls.packages))

    def test_snapshot_decodes_to_domain_records(self):
        self.assertEqual(len(self.packages), 628)
        self.assertIsInstance(self.packages[0], WidgetPackage)
        self.assertTrue(
            all(
                isinstance(signal, ImplementationSignal)
                for package in self.packages
                for signal in package.current_implementation_signals
            )
        )

    def test_unclassified_current_releases_are_excluded(self):
        self.assertEqual(self.classified.height, 614)
        self.assertNotIn(
            "unclassified", self.classified.get_column("implementation").to_list()
        )

    def test_binary_total_counts_ports_as_anywidget(self):
        totals = {
            row["implementation"]: row["count"]
            for row in implementation_totals(self.classified).to_dicts()
        }
        self.assertEqual(totals, {"anywidget": 322, "without anywidget": 292})


if __name__ == "__main__":
    unittest.main()
