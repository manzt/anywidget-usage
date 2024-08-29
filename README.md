# anywidget-usage

Tracking Jupyter Widgets in the wild (and their usage of anywidget)

> [!IMPORTANT]
> Find an issue or missing repo? **Please open an issue or PR**! Our process for
> tracking widgets is semi-automated (see below) and may miss some repositories.

## Overview

The repo is broken into two main parts:

- A daily cron job that searches github for anywidget/ipywidget projects and
  updates an [issue](https://github.com/manzt/anywidget-stats/issues/4) with
  repos that need classification.
- A [dataset](./assets/repos.json) with classified repos.

A repo may be added manually to `repos.json`, or via the CLI (requires
`GITHUB_TOKEN`):

```sh
$ deno task add <username/repo>
```

Another daily cron job extends `repos.json` with the latest commit / stars and
publishes the result to GitHub Pages, visualized on
[Observable](https://observablehq.com/d/b6e391914ebea31d).

## Methodology

Our analysis of widget packages employs a semi-automated process combining daily
automated searches with manual verification to maintain an accurate
representation of the widget ecosystem.

### Process

- **Daily Automated Search**: A daily
  [GitHub Actions workflow](./.github/workflows/update.yml) runs a script
  (`search.ts`) that performs two separate code searches: one for
  `DOMWidgetModel` (for ipywidgets) and another for `anywidget.AnyWidget` (for
  anywidget). The action updates an
  [issue](https://github.com/manzt/anywidget-stats/issues/4) with unclassified
  repositories that need manual verification.

- **Manual Verification**: A maintainer (Trevor) reviews new search results,
  inspects relevant files. If the discovered repository is a widget project that
  is published to PyPI, the maintainer adds the repository to our dataset with
  `deno task add <repo>`.

- **Dataset Maintenance**: Verified repositories are added to our
  [dataset](./assets/repos.json) and respective
  [ignore lists](./assets/exclude_repos_anywidget.txt) to prevent
  reclassification and triage by the automated search.

### Limitations

While our process aims to be comprehensive, it has several limitations. The
search may not capture every relevant repository due to GitHub API indexing
constraints, and there's potential bias towards more recent or actively
maintained projects.

The manual verification step, while helping to ensure accuracy, introduces a
subjective element to the process. As the author of **anywidget**, I may have
increased awareness of anywidget projects shared in our community, which could
introduce some bias in the discovery of new projects.

**We encourage the community to help improve our dataset** by opening issues for
missing widget projects, submitting pull requests with additions or corrections,
and suggesting improvements to our search methodology.
