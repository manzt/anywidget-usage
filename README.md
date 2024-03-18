## anywidget-usage

Tracking Jupyter Widgets in the wild (and their usage of anywidget)

The repo is broken into two main parts:

- A daily cron job that searches github for anywidget/ipywidget projects and
  updates an [issue](https://github.com/manzt/anywidget-stats/issues/4) with
  repos that need classification.
- A [dataset](./assets/repos.json) with classified repos.

A repo may be added manually to `repos.json`, or via the CLI (requires
`GITHUB_TOKEN`):

```sh
$ deno task add manzt/anywidget
# ┌  Add a new widget project
# │
# ◇  Repository
# │  manzt/anywidget
# │
# ◇  Uses anywidget?
# │  Yes
# │
# ◇  HIDIVE?
# │  Yes
# │
# ◇  Description
# │  jupyter widgets made easy
# │
# ◇  Widget Created
# │  YYYY-MM-DD (if different from repo created)
# │
# ◇  Integration kind
# │  Widget
# │
# ◇  Add repo to exclude file: assets/exclude_repos_anywidget.txt?
# │  Yes
# {
#   repo: "manzt/anywidget",
#   url: "https://github.com/manzt/anywidget",
#   hidive: true,
#   widget_created: undefined,
#   description: "jupyter widgets made easy",
#   uses_anywidget: true,
#   repo_created: "2022-10-26",
#   kind: "widget"
# }
# │
# ◇  Add this entry?
# │  Yes
# │
# └  Done
```

Another daily cron job extends `repos.json` with the latest commit / stars and
publishes the result to GitHub Pages, visualized on
[Observable](https://observablehq.com/d/b6e391914ebea31d).
