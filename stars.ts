import { fetch_repo_info } from "./add.ts";

let wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

let url = new URL("assets/repos.json", import.meta.url);
let partial_repos = await Deno.readTextFile(url).then(JSON.parse);

let results = [];
for (let item of partial_repos) {
	let info = await fetch_repo_info(item.repo);
	results.push({ ...info, ...item });
	await wait(300);
}

await Deno.writeTextFile(
	new URL("assets/repos-complete.json", import.meta.url),
	JSON.stringify(results, null, "\t"),
);
