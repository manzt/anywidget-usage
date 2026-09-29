# /// script
# dependencies = [
#     "marimo",
#     "polars==1.44.2",
#     "pyobsplot==0.5.4",
# ]
# requires-python = ">=3.14"
# ///

import marimo

__generated_with = "0.25.0"
app = marimo.App()


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    from pyobsplot import Plot
    import polars as pl
    from census.analysis import (
        ANYWIDGET_LAUNCH,
        BINARY_COLORS,
        IMPLEMENTATION_COLORS,
        SNAPSHOT_DATE,
        annual_counts,
        classify_widgets,
        cumulative_counts,
        implementation_totals as count_implementations,
        load_widget_packages,
        load_widget_repositories,
        package_frame,
        repository_frame,
    )

    root = mo.notebook_dir()
    packages = load_widget_packages(root)
    widgets = package_frame(packages)
    mo.md("# anywidget usage")
    return (
        ANYWIDGET_LAUNCH,
        BINARY_COLORS,
        IMPLEMENTATION_COLORS,
        Plot,
        SNAPSHOT_DATE,
        annual_counts,
        classify_widgets,
        count_implementations,
        cumulative_counts,
        load_widget_repositories,
        pl,
        repository_frame,
        root,
        widgets,
    )


@app.cell(hide_code=True)
def _(
    ANYWIDGET_LAUNCH,
    IMPLEMENTATION_COLORS,
    SNAPSHOT_DATE,
    classify_widgets,
    widgets,
):
    from pyobsplot import js

    snapshot_label = SNAPSHOT_DATE.strftime("%b %d, %Y").replace(" 0", " ")
    anywidget_launch = ANYWIDGET_LAUNCH
    colors = IMPLEMENTATION_COLORS
    plot_widgets = classify_widgets(widgets)
    None
    return anywidget_launch, colors, js, plot_widgets, snapshot_label


@app.cell
def _(Plot, annual_counts, colors, pl, plot_widgets):
    widget_cohorts = annual_counts(plot_widgets)
    _years = widget_cohorts.get_column("year").unique().sort().to_list()
    _annotation = pl.DataFrame(
        {
            "year": ["2023"],
            "count": [
                widget_cohorts.group_by("year")
                .agg(pl.col("count").sum())
                .get_column("count")
                .max()
            ],
            "label": ["Release of anywidget - Jan 18, 2023"],
        }
    )
    Plot.plot(
        {
            "title": "Custom Widgets Per Year",
            "style": {"fontSize": "15px"},
            "width": 900,
            "x": {"type": "band", "domain": _years, "label": None},
            "y": {"grid": True},
            "color": colors,
            "marks": [
                Plot.text(
                    _annotation,
                    {
                        "x": "year",
                        "y": "count",
                        "text": "label",
                        "fontSize": 20,
                        "textAnchor": "end",
                        "dx": -40,
                    },
                ),
                Plot.barY(
                    widget_cohorts,
                    {
                        "x": "year",
                        "y": "count",
                        "fill": "implementation",
                    },
                ),
                Plot.ruleY([0]),
            ],
        }
    )
    return


@app.cell
def _(
    Plot,
    anywidget_launch,
    cumulative_counts,
    pl,
    plot_widgets,
    snapshot_label,
):
    _events = cumulative_counts(plot_widgets)
    Plot.plot(
        {
            "title": "Custom Jupyter Widgets Over Time",
            "subtitle": f"as of {snapshot_label}",
            "width": 900,
            "y": {"grid": True, "label": "count"},
            "marks": [
                Plot.text(
                    pl.DataFrame(
                        {
                            "date": [anywidget_launch],
                            "label": ["anywidget release"],
                        }
                    ),
                    {
                        "x": "date",
                        "text": "label",
                        "textAnchor": "end",
                        "dx": -10,
                    },
                ),
                Plot.ruleX([anywidget_launch], {"stroke": "red"}),
                Plot.lineY(_events, {"x": "created", "y": "count"}),
            ],
        }
    )
    return


@app.cell(hide_code=True)
def _(
    BINARY_COLORS,
    Plot,
    count_implementations,
    plot_widgets,
    snapshot_label,
):
    implementation_totals = count_implementations(plot_widgets)
    Plot.plot({
        "title": "Total number of custom Jupyter Widgets",
        "subtitle": f"as of {snapshot_label}",
        "width": 900,
        "y": {"grid": True},
        "color": BINARY_COLORS,
        "marks": [
            Plot.barY(implementation_totals, {"x": "implementation", "y": "count", "fill": "implementation"}),
            Plot.ruleY([0]),
        ],
    })
    return


@app.cell(hide_code=True)
def _(load_widget_repositories, repository_frame, root):
    repositories = load_widget_repositories(root)
    repository_widgets = repository_frame(repositories)
    None
    return (repository_widgets,)


@app.cell(hide_code=True, expand_output=True)
def _(BINARY_COLORS, Plot, js, pl, repository_widgets, snapshot_label):
    _timeline = repository_widgets.filter(
        pl.col("last_push").is_not_null() & (pl.col("last_push") >= pl.col("created"))
    ).sort("created", descending=True)

    repository_timeline_plot = Plot.plot({
        "title": "GitHub Timeline Custom Jupyter Widgets",
        "subtitle": f"as of {snapshot_label}",
        "width": 1000,
        "height": max(500, _timeline.height * 20 + 80),
        "marginLeft": 210,
        "axis": None,
        "x": {"axis": "top", "grid": True},
        "color": BINARY_COLORS,
        "marks": [
            Plot.barX(_timeline, {
                "x1": "created",
                "x2": "last_push",
                "y": "repo",
                "fill": "implementation",
                "sort": {"y": "x1", "reverse": True},
                "opacity": 0.6,
                "href": "url",
            }),
            Plot.text(_timeline, {
                "x": "created",
                "y": "repo",
                "text": js("d => `${d.repo} (${d.stars})`"),
                "textAnchor": "end",
                "dx": -3,
            }),
        ],
    })
    repository_timeline_plot
    return


@app.cell(expand_output=True)
def _(BINARY_COLORS, Plot, js, repository_widgets, snapshot_label):
    import json

    _bubble_rows = repository_widgets.select("repo", "name", "stars", "implementation", "url").to_dicts()
    _packed = js("""(() => {
        const rows = """ + json.dumps(_bubble_rows) + """;
        const root = d3.hierarchy({children: rows})
            .sum(d => d.children ? 0 : Math.sqrt(d.stars + 1))
            .sort((a, b) => b.value - a.value);
        d3.pack().size([850, 650]).padding(3)(root);
        return root.leaves().map(d => ({...d.data, x: d.x, y: d.y, radius: d.r}));
    })()""")
    repository_bubble_plot = Plot.plot({
        "title": "Custom widget repositories · stars",
        "subtitle": f"as of {snapshot_label}",
        "width": 900, "height": 700,
        "margin": 15,
        "x": {"axis": None, "domain": [0, 850], "range": [15, 865]},
        "y": {"axis": None, "domain": [0, 650], "range": [15, 665]},
        "r": {"type": "identity"},
        "color": BINARY_COLORS,
        "marks": [
            Plot.dot(_packed, {"x": "x", "y": "y", "r": "radius", "fill": "implementation", "fillOpacity": 0.9, "stroke": "white", "strokeWidth": 1, "href": "url"}),
            Plot.text(_packed, {"x": "x", "y": "y", "text": js("d => d.radius >= 22 ? (d.name.length > Math.floor(d.radius / 3) ? d.name.slice(0, Math.floor(d.radius / 3)) + '…' : d.name) : ''"), "fontSize": 11, "fill": js("d => d.implementation === 'anywidget' ? 'white' : '#222'"), "pointerEvents": "none"}),
        ],
    })
    repository_bubble_plot
    return


if __name__ == "__main__":
    app.run()
