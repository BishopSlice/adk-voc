"""AC6: "Since last release", computed in code. No LLM."""
import datetime as dt
import json
import re
import subprocess
from collections import Counter

from brief import SHORT


def fetch_releases(repo: str) -> list[dict]:
    out = subprocess.run(["curl", "-sS", f"https://api.github.com/repos/google/{repo}/releases?per_page=10"],
                         capture_output=True, text=True, timeout=60)
    try:
        data = json.loads(out.stdout)
        if not isinstance(data, list):
            raise TypeError(data)
        return [{"tag": r["tag_name"], "date": r["published_at"][:10]} for r in data if r.get("published_at")]
    except (ValueError, KeyError, TypeError):
        raise RuntimeError(f"GitHub releases fetch failed for {repo}")


def recent_release(releases: list[dict], monday: str) -> dict | None:
    """The newest release published in W-1 or W (the 14 days we fetch)."""
    start = (dt.date.fromisoformat(monday) - dt.timedelta(days=7)).isoformat()
    end = (dt.date.fromisoformat(monday) + dt.timedelta(days=6)).isoformat()
    inside = [r for r in releases if start <= r["date"] <= end]
    return max(inside, key=lambda r: r["date"]) if inside else None


def semver(tag: str) -> str | None:
    """2.11.0 from v2.11.0 or main-v2.11.0. None for prereleases like v2.12.0-rc.1."""
    m = re.search(r"(\d+\.\d+\.\d+)(-[\w.]+)?$", tag)
    return m[1] if m and not m[2] else None


NEG = re.compile(r"\b(not|no|isn't|wasn't)\s+(a\s+)?regress", re.I)
FAIL = re.compile(r"\b(regress\w*|broke|broken|break[s]?|fail\w*|error\w*|crash\w*|hang\w*|404\w*|no longer|"
                  r"stopped|missing|not called|drops?|lost)\b", re.I)


def regressions(issues: list[dict], version: str) -> set:
    """Issues whose reporter says something broke in this version. Reporter-stated, not confirmed."""
    v = re.escape(semver(version) or version.lstrip("v"))
    ver = rf"(?<![\d.])v?{v}(?![\w]|\.\d)"
    out = set()
    for x in issues:
        for sent in re.split(r"(?<=[.!?\n])\s+", x["title"] + "\n" + x["body"]):
            if not re.search(ver, sent) or NEG.search(sent):
                continue
            cue = re.search(rf"regress\w*[^.\n]{{0,40}}{ver}|{ver}[^.\n]{{0,30}}regress|"
                            rf"after\s+(upgrading|updating)\s+to\s+{ver}|broken\s+in\s+{ver}", sent, re.I)
            if cue or (re.search(rf"\bsince\s+{ver}", sent, re.I) and FAIL.search(sent)):
                out.add(x["url"])
                break
    return out


def rate_changes(issues, labels, release_date, start, end, min_after=5) -> list[dict]:
    """Themes with at least 2x the issues in an equal-length window after the release."""
    d = dt.date.fromisoformat
    days = min((d(release_date) - d(start)).days, (d(end) - d(release_date)).days + 1)
    if days < 3:
        return []
    days_before = days_after = days
    lo = (d(release_date) - dt.timedelta(days=days)).isoformat()
    hi = (d(release_date) + dt.timedelta(days=days - 1)).isoformat()
    start, end = lo, hi
    before = Counter(labels[x["url"]] for x in issues if x["url"] in labels and lo <= x["created"] < release_date)
    after = Counter(labels[x["url"]] for x in issues if x["url"] in labels and release_date <= x["created"] <= hi)
    out = []
    for t in sorted(set(before) | set(after)):
        rb, ra = before[t] / days_before, after[t] / days_after
        if after[t] >= min_after and ra >= 2 * rb:
            last_before = (d(release_date) - dt.timedelta(days=1)).isoformat()
            out.append({"theme": t, "before": before[t], "after": after[t], "days_before": days_before,
                        "days_after": days_after, "start": start, "last_before": last_before,
                        "release": release_date, "end": end})
    return out


def compare_days(release_date: str, start: str, end: str) -> int:
    d = dt.date.fromisoformat
    return min((d(release_date) - d(start)).days, (d(end) - d(release_date)).days + 1)


def render_since_release(recent: dict, regs: dict, changes: dict, titles: dict | None = None,
                         start: str = "", end: str = "") -> str:
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
            lines.append(f"- Reported regression: [{SHORT.get(repo, repo)}#{n}: {titles.get(u, 'issue')}]({u})")
        for c in changes.get(repo, []):
            lines.append(f"- {c['theme']}: {c['before']} issues in {c['days_before']} days before "
                         f"({c['start']} to {c['last_before']}), {c['after']} in {c['days_after']} days after "
                         f"({c['release']} to {c['end']}). Small counts; not a cause.")
        if not regs.get(repo) and not changes.get(repo):
            n = compare_days(rel["date"], start, end) if start and end else 0
            window = f" comparing {n} days before and {n} days from the release" if n >= 3 else ""
            lines.append(f"- No regressions reported. No theme reached 5 or more issues and 2x{window}.")
        lines.append("")
    if none:
        lines.append(f"{', '.join(none)}: no release in this window.")
    return "\n".join(lines) + "\n"
