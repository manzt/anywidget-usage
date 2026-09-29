"""An independently reproducible PyPI name scan; names nominate candidates only."""

import asyncio
import gzip
import hashlib
import re

import httpx
from collect import OUT, now, write_json


async def main():
    url = "https://pypi.org/simple/"
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.get(
            url,
            headers={
                "Accept": "application/vnd.pypi.simple.v1+json",
                "User-Agent": "anywidget-census/0.1 (https://github.com/manzt/anywidget-usage)",
            },
        )
        response.raise_for_status()
    data = response.json()
    pattern = r"(^ipy|widget)"
    matches = [
        p["name"] for p in data["projects"] if re.search(pattern, p["name"], re.I)
    ]
    write_json(
        OUT / "pypi-index-candidates.json",
        {
            "url": url,
            "retrieved_at": now(),
            "sha256": hashlib.sha256(response.content).hexdigest(),
            "index_meta": data.get("meta"),
            "total_project_names": len(data["projects"]),
            "pattern": pattern,
            "names": matches,
            "limitation": "Complete name-pattern scan of this index response, not exhaustive widget discovery.",
        },
    )
    (OUT / "inputs/pypi-simple.json.gz").write_bytes(gzip.compress(response.content))
    print(
        f"PyPI index: {len(matches)} name candidates among {len(data['projects'])} projects",
        flush=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
