import * as p from "npm:@clack/prompts";

export async function fetch_repo_info(
	repo: string,
	options: { token?: string } = {},
) {
	let token = options.token ?? Deno.env.get("GITHUB_TOKEN");
	if (!token) {
		throw Error("Missing GitHub Token");
	}

	let headers = new Headers();
	headers.set("Accept", "application/vnd.github+json");
	headers.set("Authorization", `Bearer ${token}`);
	headers.set("X-GitHub-Api-Version", "2022-11-28");

	let base = new URL("https://api.github.com/repos/");
	let url = new URL(repo, base);
	let response = await fetch(url, { headers });
	let json = await response.json();

	return {
		repo: json.full_name,
		description: json.description,
		stars: json.stargazers_count,
		repo_created: json.created_at.split("T")[0],
		repo_updated: json.pushed_at.split("T")[0],
	};
}

function maybe_exit<T>(x: T | symbol): T {
	if (p.isCancel(x)) {
		p.cancel("Operation cancelled.");
		Deno.exit(1);
	}
	return x;
}

if (import.meta.main) {
	p.intro("Add a new widget project");

	let repo = await p.text({ message: "Repository" });
	maybe_exit(repo);
	let uses_anywidget = await p.confirm({ message: "Use anywidget?" });
	maybe_exit(uses_anywidget);
	let hidive = await p.confirm({ message: "Hidive?", initialValue: false });
	maybe_exit(hidive);
	let s = p.spinner();
	s.start("Fetching repository info");
	let info = await fetch_repo_info(repo as string);
	s.stop();
	let description = await p.text({
		message: "Description",
		initialValue: info.description,
	});
	maybe_exit(description);
	let widget_created = await p.text({
		message: "Widget Created",
		initialValue: "null",
		validate(value) {
			if (value === "null") return;
			if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
				return "Must be a date in the format YYYY-MM-DD";
			}
		},
	});
	maybe_exit(widget_created);
	let kind = await p.select({
		message: "Integration kind",
		options: [
			{ value: "widget", label: "Widget" },
			{ value: "framework", label: "Framework" },
		],
	});
	maybe_exit(kind);

	let exclude_file = uses_anywidget
		? "assets/exclude_repos_anywidget.txt"
		: "assets/exclude_repos_ipywidgets.txt";
	let add_to_ignore = await p.confirm({
		message: `Add repo to exclude file: ${exclude_file}?`,
	});
	maybe_exit(add_to_ignore);

	let entry = {
		repo: info.repo,
		url: `https://github.com/${info.repo}`,
		hidive: hidive,
		widget_created: widget_created === "null" ? null : widget_created,
		description: description,
		use_anywidget: uses_anywidget,
		repo_created: info.repo_created,
		kind: kind,
	};

	{
		let url = new URL("assets/repos.json", import.meta.url);
		let data = await Deno.readTextFile(url).then(JSON.parse);
		data.push(entry);
		await Deno.writeTextFile(url, JSON.stringify(data, null, "\t") + "\n");
	}

	{
		let url = new URL(exclude_file, import.meta.url);
		let data = Deno.readTextFileSync(url).split("\n").filter(Boolean);
		data.push(info.repo);
		Deno.writeTextFileSync(url, data.join("\n") + "\n");
	}
}
