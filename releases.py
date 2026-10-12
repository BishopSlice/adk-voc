"""AC6: "Since last release", computed in code. No LLM."""
import datetime as dt
import json
import re
import subprocess
from collections import Counter

SHORT = {"adk-python": "py", "adk-go": "go", "adk-java": "java", "adk-js": "js", "adk-docs": "docs"}


def fetch_releases(repo: str) -> list[dict]:
    out = subprocess.run(["curl", "-sS", f"https://api.github.com/repos/google/{repo}/releases?per_page=10"],
                         capture_output=True, text=True, timeout=60)
    try:
        data = json.loads(out.stdout)
        return [{"tag": r["tag_name"], "date": r["published_at"][:10]} for r in data if r.get("published_at")]
    except (ValueError, KeyError, TypeError):
        raise RuntimeError(f"GitHub releases fetch failed for {repo}")


def recent_release(releases: list[dict], monday: str) -> dict | None:
    """The newest release published in W-1 or W (the 14 days we fetch)."""
    start = (dt.date.fromisoformat(monday) - dt.timedelta(days=7)).isoformat()
    end = (dt.date.fromisoformat(monday) + dt.timedelta(days=6)).isoformat()
    inside = [r for r in releases if start <= r["date"] <= end]
    return max(inside, key=lambda r: r["date"]) if inside else None


def regressions(issues: list[dict], version: str) -> set:
    v = re.escape(version.lstrip("v"))
    pat = re.compile(rf"(regress\w*[^.\n]{{0,40}}\bv?{v}(?!\d|\.\d)|\bsince\s+v?{v}(?!\d|\.\d)|"
                     rf"after\s+(upgrading|updating)\s+to\s+v?{v}(?!\d|\.\d)|\bv?{v}(?!\d|\.\d)[^.\n]{{0,30}}regress)",
                     re.I)
    return {x["url"] for x in issues if pat.search(x["title"] + "\n" + x["body"])}


def rate_changes(issues, labels, release_date, start, end, min_after=3) -> list[dict]:
    """Themes whose issues per day at least doubled (or halved) after the release."""
    d = dt.date.fromisoformat
    days_before = (d(release_date) - d(start)).days
    days_after = (d(end) - d(release_date)).days + 1
    if days_before < 3 or days_after < 3:
        return []
    before = Counter(labels[x["url"]] for x in issues if x["url"] in labels and x["created"] < release_date)
    after = Counter(labels[x["url"]] for x in issues if x["url"] in labels and x["created"] >= release_date)
    out = []
    for t in sorted(set(before) | set(after)):
        rb, ra = before[t] / days_before, after[t] / days_after
        if after[t] >= min_after and (rb == 0 or ra / rb >= 2):
            last_before = (d(release_date) - dt.timedelta(days=1)).isoformat()
            out.append({"theme": t, "before": before[t], "after": after[t], "days_before": days_before,
                        "days_after": days_after, "start": start, "last_before": last_before,
                        "release": release_date, "end": end})
    return out


def render_since_release(recent: dict, regs: dict, changes: dict, titles: dict | None = None) -> str:
    """recent: repo -> release or None. regs: repo -> [urls]. changes: repo -> rate_changes rows."""
    titles = titles or {}
    lines, none = ["## Since last release"], []
    for repo, rel in recent.items():
        if rel is None:
            none.append(repo)
            continue
        lines.append(f"**{repo} {rel['tag']}, released {rel['date']}**")
        for u in regs.get(repo, []):
            n = u.rsplit("/", 1)[1]
            lines.append(f"- Regression reported: [{SHORT.get(repo, repo)}#{n}: {titles.get(u, 'issue')}]({u})")
        for c in changes.get(repo, []):
            lines.append(f"- {c['theme']}: {c['before']} issues in {c['days_before']} days before "
                         f"({c['start']} to {c['last_before']}), {c['after']} in {c['days_after']} days after "
                         f"({c['release']} to {c['end']}). At least 2x per day.")
        if not regs.get(repo) and not changes.get(repo):
            lines.append("- No regressions reported and no theme rate changed 2x or more.")
        lines.append("")
    if none:
        lines.append(f"{', '.join(none)}: no release in this window.")
    return "\n".join(lines) + "\n"
