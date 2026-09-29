import pathlib

import polars as pl

from census.analysis import (
    classify_widgets,
    implementation_totals,
    load_widget_repositories,
    load_widget_packages,
    package_frame,
    repository_frame,
)
from census.model import ImplementationSignal, WidgetPackage, WidgetRepository

ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKAGES = load_widget_packages(ROOT)
REPOSITORIES = load_widget_repositories(ROOT)
CLASSIFIED = classify_widgets(package_frame(PACKAGES))


def test_snapshot_decodes_to_domain_records():
    assert len(PACKAGES) == 628
    assert isinstance(PACKAGES[0], WidgetPackage)
    assert all(
        isinstance(signal, ImplementationSignal)
        for package in PACKAGES
        for signal in package.current_implementation_signals
    )


def test_unclassified_current_releases_are_excluded():
    assert CLASSIFIED.height == 614
    assert "unclassified" not in CLASSIFIED.get_column("implementation").to_list()


def test_repository_snapshot_decodes_to_domain_records():
    assert len(REPOSITORIES) == 607
    assert isinstance(REPOSITORIES[0], WidgetRepository)
    frame = repository_frame(REPOSITORIES)
    assert frame.height == 538
    assert frame.schema["created"] == pl.Date


def test_binary_total_counts_ports_as_anywidget():
    totals = {
        row["implementation"]: row["count"]
        for row in implementation_totals(CLASSIFIED).to_dicts()
    }
    assert totals == {"anywidget": 322, "without anywidget": 292}
