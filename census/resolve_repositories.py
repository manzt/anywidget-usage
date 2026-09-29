"""Resolve legacy repository renames and retain unavailable entries."""

import asyncio
from urllib.parse import quote

from collect import OUT, ROOT, Fetcher, read_json, write_json


async def main():
    legacy = read_json(ROOT / "assets/repos.json")
    gallery = read_json(OUT / "inputs/gallery.json")
    repos = sorted({row["repo"].strip() for row in legacy + gallery})
    fetcher = Fetcher()
    results = {}

    async def one(repo):
        url = "https://api.github.com/repos/" + quote(repo, safe="/")
        response = await fetcher.get(url)
        record = {
            "requested_repo": repo,
            "url": url,
            "status": response["status"],
            "retrieved_at": response["retrieved_at"],
        }
        if response["status"] == 200:
            data = response["data"]
            record.update(
                {
                    k: data.get(k)
                    for k in [
                        "id",
                        "full_name",
                        "html_url",
                        "archived",
                        "fork",
                        "created_at",
                        "pushed_at",
                        "default_branch",
                        "stargazers_count",
                    ]
                }
            )
        results[repo.casefold()] = record

    try:
        await asyncio.gather(*(one(repo) for repo in repos))
        write_json(OUT / "repository-identities.json", results)
        print(
            f"Repository identities: {len(results)}, resolved {sum(r['status'] == 200 for r in results.values())}",
            flush=True,
        )
    finally:
        await fetcher.close()


if __name__ == "__main__":
    asyncio.run(main())
