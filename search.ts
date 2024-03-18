import * as cli from "jsr:@std/cli";

let wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function code_search({ token }: { token: string }) {
	let url = new URL("https://api.github.com/search/code");
	url.searchParams.set(
		"q",
		"anywidget.AnyWidget -repo:manzt/anywidget language:python -path:/venv -path:/.venv -filename:jupyter_chart.py -filename:test_ipywidget.py",
	);
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

	let all = items.map((d) => ({
		repo: d.repository.full_name,
		filename: d.name,
		url: d.html_url,
	}));

	return Object.values(Object.groupBy(all, (d) => d.repo)).map((d) =>
		d?.at(0)!
	);
}

let results = await code_search({ token: Deno.env.get("GITHUB_TOKEN")! });
let exclude_repos = new Set(
	Deno.readTextFileSync("exclude_repos_anywidget.txt")
		.split("\n")
		.filter(Boolean),
);

console.log("## Results");
for (let item of results) {
	if (exclude_repos.has(item.repo)) {
		continue;
	}
	console.log(`- [ ] ${item.repo} [${item.filename}](${item.url})`);
}
