let wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function code_search(q: Query) {
	let token = Deno.env.get("GITHUB_TOKEN");
	if (!token) {
		throw new Error("GITHUB_TOKEN is not set");
	}

	let exclude_repos: string[] = [];
	if (q.exclude_file) {
		let text = await Deno.readTextFile(q.exclude_file);
		exclude_repos = text.split("\n").filter(Boolean);
	}

	let url = new URL("https://api.github.com/search/code");
	url.searchParams.set("q", q.query);
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

	console.log(`## ${q.title}`);
	for (let item of results) {
		if (exclude_set.has(item.repo)) {
			continue;
		}
		console.log(`- [ ] ${item.repo} [\`${item.filename}\`](${item.url})`);
	}
}

type Query = {
	title: string;
	query: string;
	exclude_file: URL;
};

let anywidget: Query = {
	title: "anywidget",
	query:
		"anywidget.AnyWidget -repo:manzt/anywidget language:python -path:/venv -path:/.venv -filename:jupyter_chart.py -filename:test_ipywidget.py",
	exclude_file: new URL("exclude_repos_anywidget.txt", import.meta.url),
};
let ipywidgets: Query = {
	title: "ipywidgets",
	query:
		"DOMWidgetModel -repo:jupyter-widgets/ipywidgets language:python -path:/venv -path:/.venv -filename:domwidget.py",
	exclude_file: new URL("exclude_repos_ipywidgets.txt", import.meta.url),
};

if (Deno.args[0] === "anywidget") {
	await code_search(anywidget);
} else if (Deno.args[0] === "ipywidgets") {
	await code_search(ipywidgets);
} else {
	await code_search(anywidget);
	console.log("\n\n");
	await code_search(ipywidgets);
}

