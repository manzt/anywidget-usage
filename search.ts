import * as cli from "jsr:@std/cli";

let wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function code_search(
	query: string,
	{ token, exclude_repos }: { token: string; exclude_repos: string[] },
) {
	let url = new URL("https://api.github.com/search/code");
	url.searchParams.set("q", query);
	url.searchParams.set("per_page", "100");

	let headers = new Headers();
	headers.set("Accept", "application/vnd.github+json");
	headers.set("Authorization", `Bearer ${token}`);
	headers.set("X-GitHub-Api-Version", "2022-11-28");

	let page = 1;
	let items = [];
	while (true) {
		url.searchParams.set("page", page.toString());
		let response = await fetch(url, { headers });
		let json = await response.json();
		if (json.items.length === 0) {
			break;
		}
		items.push(...json.items);
		// rate limiting
		await wait(5000);
		page++;
	}

	let groups = Object.groupBy(
		items.map((d) => ({
			repo: d.repository.full_name,
			filename: d.name,
			url: d.html_url,
		})),
		(d) => d.repo,
	);

	let results = Object.values(groups).map((d) => d?.at(0)!);
	let exclude_set = new Set(exclude_repos);

	console.log("## Results");
	for (let item of results) {
		if (exclude_set.has(item.repo)) {
			continue;
		}
		console.log(`- [ ] ${item.repo} [\`${item.filename}\`](${item.url})`);
	}
}

let query: string;
let exclude_file: string;
if (Deno.args[0] === "anywidget") {
	query =
		"anywidget.AnyWidget -repo:manzt/anywidget language:python -path:/venv -path:/.venv -filename:jupyter_chart.py -filename:test_ipywidget.py";
	exclude_file = "exclude_repos_anywidget.txt";
} else if (Deno.args[0] === "ipywidgets") {
	query =
		"DOMWidgetModel -repo:jupyter-widgets/ipywidgets language:python -path:/venv -path:/.venv -filename:domwidget.py";
	exclude_file = "exclude_repos_anywidget.txt";
} else {
	console.error("Invalid argument");
	Deno.exit(1); // EXIT_FAILURE
}

code_search(query, {
	token: Deno.env.get("GITHUB_TOKEN")!,
	exclude_repos: Deno.readTextFileSync(exclude_file)
		.split("\n")
		.filter(Boolean),
});
