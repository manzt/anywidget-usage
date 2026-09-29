# Census methodology

This repository treats the census as a versioned research dataset. The accepted state lives in `assets/widgets.json` and `assets/repositories.json`; `model.py` defines their schema, and `analysis.py` contains the transformations used by the notebook.

Candidates were gathered from the original repository inventory and gallery, dependency indexes, GitHub source search, package manifests, and the PyPI name index. These sources nominate packages for inspection but do not establish that they implement a custom widget.

Published archives were inspected statically and never installed or executed. A direct `anywidget.AnyWidget` subclass counts as an anywidget signal. An ipywidgets subclass counts only when it declares a custom model or view module. Selected historical releases were inspected to find the earliest evidence available, so the exported dates mean **observed by** rather than an exact creation date.

Repository aliases, monorepos, demos, forks, and apparent migrations require review. Traditional evidence followed by anywidget evidence makes a package a port candidate, but that chronology does not prove that the same component was ported. The January 18, 2023 public launch is shown in the plots and is not used as a classification rule.

## Going forward

The intended cadence is one reviewed refresh each quarter, with an additional refresh before publishing updated analysis. A refresh begins in a dated local directory that remains ignored by git. New and changed records are reviewed against the accepted snapshot, with particular attention to classifications, repository identity, evidence versions, artifact URLs, and review notes. Once accepted, the package and repository assets are replaced.

Running `uv run python -m census` validates both typed snapshots and regenerates `assets/repos-complete.json` in the schema consumed by the existing Observable notebook. That export contains one row per canonical repository linked to the package census. Its widget date is the earliest package observation for that repository, and its anywidget status is true when any linked package currently uses anywidget. Packages without a resolved repository remain in `widgets.json` but cannot appear in the repository export.

The resulting data diff is the review surface. Run `uv run --group test pytest` and `uv run marimo check widget_census.py` before committing it.
