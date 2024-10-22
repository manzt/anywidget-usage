import * as p from "npm:@clack/prompts@0.7.0";
import { z } from "npm:zod@3.22.4";

let RepoSchema = z.object({
	repo: z.string(),
	url: z.string().url(),
	hidive: z.boolean(),
	widget_created: z.string()
		.transform((x) => Temporal.PlainDate.from(x))
		.nullable(),
	description: z.string(),
	uses_anywidget: z.boolean(),
	repo_created: z.string().transform((x) => Temporal.PlainDate.from(x)),
	kind: z.enum(["widget", "framework"]).optional(),
});

let GithubRepo = z.object({
	full_name: z.string(),
	description: z.string().nullable(),
	stargazers_count: z.number(),
	created_at: z.string(),
	pushed_at: z.string(),
});

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
	let json = GithubRepo.parse(await response.json());

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
	let repo_path = new URL("assets/repos.json", import.meta.url);
	let text = await Deno.readTextFile(repo_path);
	let repos = z.array(RepoSchema).parse(JSON.parse(text));

	let repo = await p.text({
		message: "Repository",
		initialValue: Deno.args[0],
		placeholder: "user/repo",
	});
	maybe_exit(repo);

	if (repos.some((r) => r.repo === repo)) {
		p.cancel("Repo already exists");
		console.log(repos.find((r) => r.repo === repo));
		Deno.exit(1);
	}

	let uses_anywidget = await p.confirm({ message: "Uses anywidget?" });
	maybe_exit(uses_anywidget);
	let hidive = await p.confirm({ message: "HIDIVE?", initialValue: false });
	maybe_exit(hidive);
	let info = await fetch_repo_info(repo as string);
	let description = await p.text({
		message: "Description",
		initialValue: info.description,
		placeholder: "Type a description",
		validate(value) {
			if (value.length === 0) return "Description is required";
		},
	});
	maybe_exit(description);
	let widget_created = await p.text({
		message: "Widget Created",
		placeholder: "YYYY-MM-DD (if different from repo created)",
		validate(value) {
			if (value === "") return;
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

	let entry = RepoSchema.parse({
		repo: info.repo,
		url: `https://github.com/${info.repo}`,
		hidive: hidive,
		widget_created: widget_created ?? null,
		description: description,
		uses_anywidget: uses_anywidget,
		repo_created: info.repo_created,
		kind,
	});

	console.log(entry);
	let go = await p.confirm({ message: "Add this entry?" });
	maybe_exit(go);
	if (go) {
		{
			repos.push(entry);
			await Deno.writeTextFile(
				repo_path,
				JSON.stringify(repos, null, "\t") + "\n",
			);
		}

		{
			let url = new URL(exclude_file, import.meta.url);
			let text = await Deno.readTextFile(url);
			let excluded = text.split("\n").filter(Boolean);
			excluded.push(entry.repo);
			Deno.writeTextFileSync(exclude_file, excluded.join("\n") + "\n");
		}
	}

	p.outro("Done");
}
