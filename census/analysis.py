"""Reusable transformations for the widget census notebook."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from pathlib import Path

import msgspec
import polars as pl

from census.model import WidgetPackage, WidgetRepository

SNAPSHOT_DATE = date(2026, 9, 29)
ANYWIDGET_LAUNCH = date(2023, 1, 18)
IMPLEMENTATION_COLORS = {
    "legend": True,
    "domain": ["anywidget", "ported to anywidget", "without anywidget"],
    "range": ["#024B7A", "#45B7C2", "#FFAF4A"],
}
BINARY_COLORS = {
    "legend": True,
    "domain": ["anywidget", "without anywidget"],
    "range": ["#024B7A", "#FFAF4A"],
}


def load_widget_packages(root: Path) -> list[WidgetPackage]:
    """Decode and validate the committed package-level snapshot."""
    decoder = msgspec.json.Decoder(list[WidgetPackage])
    return decoder.decode((root / "assets/widgets.json").read_bytes())


def package_frame(packages: Sequence[WidgetPackage]) -> pl.DataFrame:
    return pl.from_dicts([msgspec.to_builtins(package) for package in packages])


def classify_widgets(widgets: pl.DataFrame) -> pl.DataFrame:
    """Prepare evidence-backed rows used by the plots.

    Rows without a current implementation signal are excluded. A port means
    traditional source was observed in an earlier inspected release.
    """
    return widgets.with_columns(
        pl.col("first_widget_observed_by")
        .str.slice(0, 10)
        .str.to_date(strict=False)
        .alias("created"),
        pl.when(pl.col("current_implementation_signals").list.len() == 0)
        .then(pl.lit("unclassified"))
        .when(pl.col("traditional_before_anywidget_observed"))
        .then(pl.lit("ported to anywidget"))
        .when(pl.col("current_implementation_signals").list.contains("anywidget"))
        .then(pl.lit("anywidget"))
        .otherwise(pl.lit("without anywidget"))
        .alias("implementation"),
    ).filter(
        (pl.col("implementation") != "unclassified") & pl.col("created").is_not_null()
    )


def annual_counts(widgets: pl.DataFrame) -> pl.DataFrame:
    return (
        widgets.with_columns(pl.col("created").dt.year().cast(pl.Utf8).alias("year"))
        .group_by("year", "implementation")
        .len(name="count")
        .with_columns(pl.col("count").cast(pl.Int32))
        .sort("year", "implementation")
    )


def cumulative_counts(widgets: pl.DataFrame) -> pl.DataFrame:
    return (
        widgets.group_by("created")
        .len(name="new")
        .sort("created")
        .with_columns(
            pl.col("new").cast(pl.Int32),
            pl.col("new").cum_sum().cast(pl.Int32).alias("count"),
        )
    )


def implementation_totals(widgets: pl.DataFrame) -> pl.DataFrame:
    """Count ports as anywidget for the binary summary."""
    return (
        widgets.with_columns(
            pl.when(pl.col("implementation") == "ported to anywidget")
            .then(pl.lit("anywidget"))
            .otherwise(pl.col("implementation"))
            .alias("implementation")
        )
        .group_by("implementation")
        .len(name="count")
        .with_columns(pl.col("count").cast(pl.Int32))
        .sort("implementation")
    )


def load_widget_repositories(root: Path) -> list[WidgetRepository]:
    """Decode and validate the committed repository-level snapshot."""
    decoder = msgspec.json.Decoder(list[WidgetRepository])
    return decoder.decode((root / "assets/repositories.json").read_bytes())


def repository_frame(repositories: Sequence[WidgetRepository]) -> pl.DataFrame:
    return (
        pl.from_dicts([msgspec.to_builtins(repo) for repo in repositories])
        .filter("in_package_census")
        .drop("in_package_census")
        .with_columns(
            pl.col("created").str.to_date(),
            pl.col("last_push").str.to_date(),
        )
    )
