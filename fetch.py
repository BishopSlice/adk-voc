"""AC1: fetch issues created in week W and W-1 from the GitHub search API."""
import datetime as dt
import json
import subprocess
import time
import urllib.parse
from pathlib import Path

import yaml

API = "https://api.github.com/search/issues"
HERE = Path(__file__).resolve().parent


class CountMismatch(RuntimeError):
    pass


def week_bounds(monday: str) -> tuple[str, str]:
    d = dt.date.fromisoformat(monday)
    if d.weekday() != 0:
        raise ValueError(f"{monday} is not a Monday")
    return monday, (d + dt.timedelta(days=6)).isoformat()


def build_query(repo: str, start: str, end: str) -> str:
    return f"repo:google/{repo} is:issue created:{start}..{end}"


def parse_item(repo: str, it: dict) -> dict:
    # No usernames: only the fields the spec lists.
    return {"repo": repo, "n": it["number"], "url": it["html_url"],
            "created": it["created_at"][:10], "state": it["state"], "title": it["title"],
            "labels": [x["name"] for x in it["labels"]], "comments": it["comments"],
            "author_role": it.get("author_association", ""),
            "reactions": it.get("reactions", {}).get("total_count", 0),
            "body": (it.get("body") or "")[:1000]}


def curl_get(query: str, page: int) -> dict:
    # curl, not urllib: Python's SSL certificates are broken on this Mac.
    url = f"{API}?q={urllib.parse.quote(query)}&per_page=100&page={page}"
    for attempt in range(3):
        out = subprocess.run(["curl", "-sS", "-H", "Accept: application/vnd.github+json", url],
                             capture_output=True, text=True, timeout=60)
        try:
            data = json.loads(out.stdout or "{}")
        except ValueError:
            data = {"message": "non-JSON response"}
        if "items" in data:
            time.sleep(7)  # stay under 10 search requests per minute
            return data
        time.sleep(30 * (attempt + 1))  # rate limited or a transient error
    raise RuntimeError(f"GitHub search failed for {query}: {data.get('message')}")


def fetch_repo(repo: str, start: str, end: str, get=curl_get) -> list[dict]:
    q = build_query(repo, start, end)
    items, page = [], 1
    while True:
        data = get(q, page)
        items += [parse_item(repo, it) for it in data["items"]]
        if len(items) >= data["total_count"] or not data["items"]:
            break
        page += 1
    if len(items) != data["total_count"]:
        raise CountMismatch(f"{repo}: got {len(items)}, GitHub says {data['total_count']}")
    return items


def fetch_week(monday: str, get=curl_get) -> list[dict]:
    """Issues created in W and W-1, all repos in config.yaml."""
    prev = (dt.date.fromisoformat(monday) - dt.timedelta(days=7)).isoformat()
    _, end = week_bounds(monday)
    repos = yaml.safe_load(open(HERE / "config.yaml"))["repos"]
    return [x for r in repos for x in fetch_repo(r, prev, end, get)]
