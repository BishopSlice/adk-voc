"""AC4: pain score per theme, plus trend tokens. Pure code, deterministic."""
import datetime as dt
import statistics
from collections import defaultdict


def pain_table(issues: list[dict], labels: dict, monday: str, weights: dict) -> list[dict]:
    """pain = count x severity weight x repos affected x (1 + median comments / 10)"""
    end = (dt.date.fromisoformat(monday) + dt.timedelta(days=6)).isoformat()
    cur, prev = defaultdict(list), defaultdict(int)
    for x in issues:
        t = labels.get(x["url"])
        if t is None:
            continue
        if monday <= x["created"] <= end:
            cur[t].append(x)
        elif x["created"] < monday:
            prev[t] += 1
    rows = []
    for t, xs in cur.items():
        repos = sorted({x["repo"] for x in xs})
        med = statistics.median(x["comments"] for x in xs)
        pain = round(len(xs) * weights.get(t, 1.0) * len(repos) * (1 + med / 10), 1)
        rows.append({"theme": t, "count": len(xs), "prev": prev[t], "repos": repos,
                     "pain": pain, "trend": trend(prev[t], len(xs)), "urls": [x["url"] for x in xs]})
    return sorted(rows, key=lambda r: (-r["pain"], -r["count"], r["theme"]))


def trend(prev: int, cur: int) -> str:
    if prev == 0:
        return "new"
    if cur == prev:
        return "– 0%"
    arrow = "▲" if cur > prev else "▼"
    if prev < 5:
        return f"{arrow} {prev} → {cur}"
    pct = round((cur - prev) / prev * 100)
    return f"▲ +{pct}%" if pct > 0 else f"▼ −{-pct}%"
