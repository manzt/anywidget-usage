# /// script
# dependencies = [
#     "anywidget>=0.11.0",
#     "marimo==0.25.0",
#     "polars==1.44.2",
#     "pyobsplot==0.5.4",
#     "quak>=0.3.5",
# ]
# requires-python = ">=3.12"
# ///

import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # anywidget usage

    A package-level census of custom Jupyter widgets. Read more about the
    methodology in the [repository](https://github.com/manzt/anywidget-usage).

    ## Adoption overview

    These views summarize when widgets appeared and current anywidget adoption.
    """)
    return


@app.cell(hide_code=True)
def _(IMPLEMENTATION_COLORS, Plot, data, js, pl):
    _yearly = (
        data.with_columns(pl.col("created").dt.year().alias("year"))
        .group_by("year", "implementation")
        .len(name="count")
        .sort("year", "implementation")
    )
    Plot.plot(
        {
            "title": "Custom Widgets Per Year",
            "style": {"fontSize": "15px"},
            "x": {"tickFormat": js("d => String(d)"), "label": None},
            "y": {"grid": True},
            "color": IMPLEMENTATION_COLORS,
            "marks": [
                Plot.barY(
                    _yearly,
                    {"x": "year", "y": "count", "fill": "implementation"},
                ),
                Plot.ruleY([0]),
            ],
        }
    )
    return


@app.cell(hide_code=True)
def _(Plot, anywidget_release_date, data, pl, snapshot_label):
    _events = (
        data.group_by("created")
        .len(name="new")
        .sort("created")
        .with_columns(pl.col("new").cum_sum().alias("count"))
    )
    Plot.plot(
        {
            "title": "Custom Jupyter Widgets Over Time",
            "subtitle": f"as of {snapshot_label}",
            "y": {"grid": True, "label": "count"},
            "marks": [
                Plot.text(
                    pl.DataFrame(
                        {
                            "date": [anywidget_release_date],
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
                Plot.ruleX([anywidget_release_date], {"stroke": "red"}),
                Plot.lineY(_events, {"x": "created", "y": "count"}),
            ],
        }
    )
    return


@app.cell(hide_code=True)
def _(BINARY_COLORS, Plot, data, pl, snapshot_label):
    _totals = (
        data.with_columns(
            pl.when(pl.col("uses_anywidget"))
            .then(pl.lit("anywidget"))
            .otherwise(pl.lit("not anywidget"))
            .alias("category")
        )
        .group_by("category")
        .len(name="count")
    )
    Plot.plot(
        {
            "title": "Total number of custom Jupyter Widgets",
            "subtitle": f"as of {snapshot_label}",
            "y": {"grid": True},
            "color": BINARY_COLORS,
            "marks": [
                Plot.barY(
                    _totals,
                    {"x": "category", "y": "count", "fill": "category"},
                ),
                Plot.ruleY([0]),
            ],
        }
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Explore packages

    Use [quak's](https://github.com/manzt/quak) column controls to filter the census. The remaining package
    names drive both the bubble view and its detail distributions.

    Bubble area represents GitHub stars; hover to preview or click to pin a package.
    """)
    return


@app.cell(hide_code=True)
def _(data, mo, pl, quak, stars_by_repo):
    _selector_metrics = pl.from_dicts(
        prepare_bubbles(data, stars_by_repo)
    ).select("package", "category", "stars")
    selector_data = (
        data.select(
            "package",
            "implementation",
            "created",
            pl.col("repositories").list.join(", ").alias("repositories"),
            pl.col("known_in_legacy").alias("legacy"),
            pl.col("earliest_extant_release_has_widget_evidence").alias(
                "complete_history"
            ),
        )
        .join(_selector_metrics, on="package", how="left")
        .select(
            "package",
            "category",
            "implementation",
            "created",
            "stars",
            "repositories",
            "legacy",
            "complete_history",
        )
        .sort("package")
    )
    filter_table = mo.ui.anywidget(quak.Widget(selector_data))
    filter_table
    return (filter_table,)


@app.cell(hide_code=True, expand_output=True)
def _(bubble_chart):
    bubble_chart
    return


@app.cell(hide_code=True)
def _(bubble_chart, escape, math, mo):
    selected = bubble_chart.value["selected"]
    packages = bubble_chart.value["packages"]
    _card_style = (
        "box-sizing: border-box; border: 1px solid #ddd; border-radius: 6px; "
        "height: 142px; padding: 10px 12px; max-width: 640px;"
    )

    def _histogram_svg(values, current=None, bins=18):
        _values = [math.log1p(max(0, value)) for value in values]
        _high = max(_values, default=0)
        _step = _high / bins if _high else 1
        _counts = [0] * bins
        for _value in _values:
            _index = min(bins - 1, int(_value / _step)) if _high else 0
            _counts[_index] += 1
        _selected_bin = None
        if current is not None:
            _current = math.log1p(max(0, current))
            _selected_bin = min(bins - 1, int(_current / _step)) if _high else 0
        _peak = max(_counts, default=1) or 1
        _bars = []
        for _index, _count in enumerate(_counts):
            _height = max(1, round(26 * _count / _peak))
            _fill = "#222" if _index == _selected_bin else "#d5d5d5"
            _bars.append(
                f'<rect x="{_index * 8}" y="{28 - _height}" width="6" '
                f'height="{_height}" fill="{_fill}" />'
            )
        return f'<svg viewBox="0 0 {bins * 8} 28" width="144" height="28">{"".join(_bars)}</svg>'

    _star_values = [row["stars"] for row in packages]
    _repository_values = [len(row["repositories"]) for row in packages]
    _category_counts = {
        category: sum(row["category"] == category for row in packages)
        for category in ("anywidget", "not anywidget")
    }
    _category_total = sum(_category_counts.values()) or 1

    if selected:
        _package = escape(selected["package"])
        _repositories = selected["repositories"]
        _repository_label = escape(", ".join(_repositories))
        _pypi_url = escape(selected.get("pypi_url") or "", quote=True)
        _stars = selected["stars"]
        _repository_count = len(_repositories)
        _category = selected["category"]
        _percentile = round(
            100 * sum(value <= _stars for value in _star_values) / len(_star_values)
        )
        _star_value = f'{_stars} <small style="color:#777;">p{_percentile}</small>'
        _repository_value = str(_repository_count)
        _category_value = escape(_category)
        _pypi_link = (
            f'<a href="{_pypi_url}" target="_blank" rel="noopener noreferrer" '
            'style="margin-left: auto; flex: none;">PyPI ↗</a>'
        )
    else:
        _package = ""
        _repository_label = ""
        _stars = None
        _repository_count = None
        _category = None
        _star_value = ""
        _repository_value = ""
        _category_value = ""
        _pypi_link = ""

    _star_histogram = _histogram_svg(_star_values, _stars)
    _repository_histogram = _histogram_svg(
        _repository_values, _repository_count
    )
    _category_segments = []
    for _name, _color in (
        ("anywidget", "#024B7A"),
        ("not anywidget", "#FFAF4A"),
    ):
        _share = 100 * _category_counts[_name] / _category_total
        _opacity = 1 if _category in (None, _name) else 0.25
        _outline = "box-shadow: inset 0 0 0 2px #222;" if _category == _name else ""
        _category_segments.append(
            f'<div title="{_name}: {_category_counts[_name]}" style="height: 12px; '
            f'width: {_share}%; background: {_color}; opacity: {_opacity}; {_outline}"></div>'
        )
    _category_distribution = "".join(_category_segments)

    _detail_card = mo.Html(
        f"""
        <div style="{_card_style}">
          <div style="display: flex; align-items: baseline; gap: 8px; height: 34px;">
            <strong>{_package}</strong>
            <span title="{_repository_label}" style="color: #666; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{_repository_label}</span>
            {_pypi_link}
          </div>
          <div style="display: grid; grid-template-columns: 120px 110px 1fr; align-items: center; row-gap: 3px;">
            <span>GitHub stars</span><strong>{_star_value}</strong>{_star_histogram}
            <span>Repositories</span><strong>{_repository_value}</strong>{_repository_histogram}
            <span>Implementation</span><strong>{_category_value}</strong>
            <div style="display: flex; height: 12px; width: 144px;">{_category_distribution}</div>
          </div>
        </div>
        """
    )
    _detail_card
    return


@app.cell(hide_code=True)
def _(bubble_chart, data, filter_table, stars_by_repo):
    _filtered_data = filter_table.data()
    if _filtered_data is None:
        bubble_data = data
    else:
        _selected_packages = _filtered_data.pl().select("package")
        bubble_data = data.join(_selected_packages, on="package", how="semi")
    bubble_chart.packages = prepare_bubbles(bubble_data, stars_by_repo)
    return


@app.cell(hide_code=True)
def _(BubbleChart, mo):
    bubble_chart = mo.ui.anywidget(BubbleChart())
    return (bubble_chart,)


@app.cell(hide_code=True)
def _(anywidget, traitlets):
    class BubbleChart(anywidget.AnyWidget):
        packages = traitlets.List(traitlets.Dict()).tag(sync=True)
        selected = traitlets.Dict().tag(sync=True)

        _esm = r"""
    import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7/+esm";

    function render({model, el}) {
      const width = 640;
      const height = 640;
      const colors = new Map([
        ["anywidget", "#024B7A"],
        ["not anywidget", "#FFAF4A"]
      ]);

      function select(row) {
        model.set("selected", row ?? {});
        model.save_changes();
      }

      function draw() {
        const rows = model.get("packages");
        select(null);
        el.replaceChildren();

        const container = document.createElement("div");
        container.className = "anywidget-bubbles";
        el.append(container);

        const header = document.createElement("div");
        header.className = "anywidget-bubbles__header";
        header.innerHTML = `
          <span><i style="background:#024B7A"></i>anywidget</span>
          <span><i style="background:#FFAF4A"></i>not anywidget</span>
          <span class="anywidget-bubbles__detail">${rows.length} packages</span>
        `;
        container.append(header);

        const root = d3.pack().size([width, height]).padding(3)(
          d3.hierarchy({children: rows})
            .sum(d => d.children ? 0 : Math.sqrt(d.stars + 1))
        );
        const leaves = root.leaves();
        const uid = `bubble-${crypto.randomUUID()}`;

        const svg = d3.create("svg")
          .attr("viewBox", `0 0 ${width} ${height}`)
          .attr("role", "img")
          .attr("aria-label", "Custom Jupyter widget packages");
        container.append(svg.node());

        const leaf = svg.selectAll("g")
          .data(leaves)
          .join("g")
          .attr("transform", d => `translate(${d.x},${d.y})`)
          .attr("tabindex", 0)
          .attr("role", "link")
          .attr("aria-label", d => `${d.data.package}, ${d.data.stars} GitHub stars`);

        leaf.append("clipPath")
          .attr("id", (_, i) => `${uid}-${i}`)
          .append("circle")
          .attr("r", d => Math.max(0, d.r - 2));

        leaf.append("circle")
          .attr("r", d => d.r)
          .attr("fill", d => colors.get(d.data.category))
          .attr("fill-opacity", 0.9)
          .attr("stroke", "white")
          .attr("stroke-width", 1.5);

        leaf.append("text")
          .attr("clip-path", (_, i) => `url(#${uid}-${i})`)
          .attr("text-anchor", "middle")
          .attr("dominant-baseline", "central")
          .attr("fill", d => d.data.category === "anywidget" ? "white" : "#222")
          .attr("font-size", d => Math.max(8, Math.min(11, d.r / 3)))
          .attr("opacity", d => d.r >= 18 ? 1 : 0)
          .text(d => d.data.package);

        let pinned = null;

        function preview(_, d) {
          if (pinned === null) select(d.data);
        }

        function clearPreview() {
          if (pinned === null) select(null);
        }

        function clearPin() {
          pinned = null;
          leaf.attr("data-pinned", false);
          select(null);
        }

        function togglePin(event, d) {
          event.stopPropagation();
          if (pinned === d.data.package) {
            clearPin();
            return;
          }
          pinned = d.data.package;
          leaf.attr("data-pinned", node => node.data.package === pinned);
          select(d.data);
        }

        svg.on("click", clearPin);
        leaf
          .on("pointerenter", preview)
          .on("pointerleave", clearPreview)
          .on("focus", preview)
          .on("blur", clearPreview)
          .on("click", togglePin)
          .on("keydown", (event, d) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              togglePin(event, d);
            }
          });
      }

      draw();
      model.on("change:packages", draw);
      return () => model.off("change:packages", draw);
    }

    export default {render};
    """

        _css = r"""
    .anywidget-bubbles {
      color: #222;
      font: 13px system-ui, sans-serif;
      max-width: 640px;
    }
    .anywidget-bubbles__header {
      align-items: center;
      display: flex;
      gap: 16px;
      min-height: 28px;
    }
    .anywidget-bubbles__header span {
      align-items: center;
      display: inline-flex;
      gap: 6px;
    }
    .anywidget-bubbles__header i {
      display: inline-block;
      height: 12px;
      width: 12px;
    }
    .anywidget-bubbles__detail {
      margin-left: auto;
    }
    .anywidget-bubbles svg {
      display: block;
      height: auto;
      overflow: visible;
      width: 100%;
    }
    .anywidget-bubbles g[role="link"],
    .anywidget-bubbles g[role="link"]:focus {
      cursor: pointer;
      outline: none !important;
    }
    .anywidget-bubbles g[role="link"]:is(:hover, :focus) circle,
    .anywidget-bubbles g[data-pinned="true"] circle {
      stroke: #333;
      stroke-width: 2px;
    }
    .anywidget-bubbles text {
      pointer-events: none;
    }
    """

    return (BubbleChart,)


@app.function(hide_code=True)
def prepare_bubbles(data, stars_by_repo):
    packages = []
    for row in data.select(
        "package", "pypi_url", "repositories", "uses_anywidget"
    ).to_dicts():
        packages.append(
            {
                **row,
                "category": (
                    "anywidget" if row["uses_anywidget"] else "not anywidget"
                ),
                "stars": max(
                    (
                        stars_by_repo.get(repo.casefold(), 0)
                        for repo in row["repositories"]
                    ),
                    default=0,
                ),
            }
        )

    by_category = {
        category: sorted(
            (row for row in packages if row["category"] == category),
            key=lambda row: row["package"],
        )
        for category in ("anywidget", "not anywidget")
    }
    return [
        row
        for pair in zip(
            by_category["anywidget"],
            by_category["not anywidget"],
            strict=False,
        )
        for row in pair
    ] + by_category["anywidget"][len(by_category["not anywidget"]):] + by_category[
        "not anywidget"
    ][len(by_category["anywidget"]):]


@app.cell(hide_code=True)
def _():
    import json
    import math
    from datetime import date, datetime
    from html import escape
    from urllib.request import urlopen

    import anywidget
    import marimo as mo
    import polars as pl
    import quak
    import traitlets
    from pyobsplot import Plot, js


    def load_data():
        def read_json(url):
            with urlopen(url) as response:
                return json.load(response)

        widgets = read_json(
            "https://raw.githubusercontent.com/manzt/anywidget-usage/"
            "refs/heads/main/assets/widgets.json"
        )
        repositories = read_json(
            "https://raw.githubusercontent.com/manzt/anywidget-usage/"
            "refs/heads/main/assets/repos-complete.json"
        )
        stars_by_repo = {
            row["repo"].casefold(): row.get("stars", 0)
            for row in repositories
        }
        data = (
            pl.from_dicts(widgets)
            .with_columns(
                pl.col("first_widget_observed_by")
                .str.slice(0, 10)
                .str.to_date(strict=False)
                .alias("created"),
                pl.col("current_implementation_signals")
                .list.contains("anywidget")
                .alias("uses_anywidget"),
                pl.when(pl.col("current_implementation_signals").list.len() == 0)
                .then(pl.lit("unclassified"))
                .when(pl.col("traditional_before_anywidget_observed"))
                .then(pl.lit("ported to anywidget"))
                .when(pl.col("current_implementation_signals").list.contains("anywidget"))
                .then(pl.lit("anywidget"))
                .otherwise(pl.lit("without anywidget"))
                .alias("implementation"),
            )
            .filter(
                (pl.col("implementation") != "unclassified")
                & pl.col("created").is_not_null()
            )
        )
        return data, stars_by_repo


    data, stars_by_repo = load_data()
    anywidget_release_date = date(2023, 1, 18)
    snapshot_label = datetime.now().strftime("%b %d, %Y").replace(" 0", " ")

    IMPLEMENTATION_COLORS = {
        "legend": True,
        "domain": ["anywidget", "ported to anywidget", "without anywidget"],
        "range": ["#024B7A", "#45B7C2", "#FFAF4A"],
    }
    BINARY_COLORS = {
        "legend": True,
        "domain": ["anywidget", "not anywidget"],
        "range": ["#024B7A", "#FFAF4A"],
    }
    return (
        BINARY_COLORS,
        IMPLEMENTATION_COLORS,
        Plot,
        anywidget,
        anywidget_release_date,
        data,
        escape,
        js,
        math,
        mo,
        pl,
        quak,
        snapshot_label,
        stars_by_repo,
        traitlets,
    )


if __name__ == "__main__":
    app.run()
