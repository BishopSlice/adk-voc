"""AC5 (basic) and AC8: compute stats in code, then Sonnet writes the brief from them."""
import datetime as dt
import re
from collections import defaultdict
from pathlib import Path

import yaml

from llm import ask_claude

HERE = Path(__file__).resolve().parent
SHORT = {"adk-python": "py", "adk-go": "go", "adk-java": "java", "adk-js": "js", "adk-docs": "docs"}


def theme_stats(issues: list[dict], labels: dict, monday: str) -> dict:
    end = (dt.date.fromisoformat(monday) + dt.timedelta(days=6)).isoformat()
    s = defaultdict(lambda: {"count": 0, "prev": 0, "repos": set(), "urls": []})
    for x in issues:
        t = labels.get(x["url"])
        if t is None:
            continue
        if monday <= x["created"] <= end:
            s[t]["count"] += 1
            s[t]["repos"].add(x["repo"])
            s[t]["urls"].append(x["url"])
        elif x["created"] < monday:
            s[t]["prev"] += 1
    return {t: {**v, "repos": sorted(v["repos"])} for t, v in s.items()}


def tldr_ok(md: str) -> bool:
    m = re.search(r"^## TL;DR\n(.*?)(?=^## )", md, re.S | re.M)
    if not m:
        return False
    lines = [x for x in m.group(1).splitlines() if x.strip()]
    return 0 < len(lines) <= 5 and all(len(x) < 120 for x in lines)


def write_brief(issues, labels, monday, spam_count, ask=ask_claude) -> str:
    cfg = yaml.safe_load(open(HERE / "config.yaml"))
    stats = theme_stats(issues, labels, monday)
    ranked = sorted(((t, v) for t, v in stats.items() if v["count"]), key=lambda kv: (-kv[1]["count"], kv[0]))
    by_url = {x["url"]: x for x in issues}
    week_n = sum(v["count"] for v in stats.values())
    stat_lines = "\n".join(f"- {t}: {v['count']}, repos "
                           f"{', '.join(SHORT[r] for r in v['repos'])}" for t, v in ranked)
    cand = []
    for t, v in ranked[:5]:
        cand.append(f"\n### {t}")
        top = sorted(v["urls"], key=lambda u: -by_url[u]["comments"])[:4]
        cand += [f"- {u} | {by_url[u]['title']} | {by_url[u]['body'][:600]!r}" for u in top]
    prompt = (HERE / "prompts" / "brief.md").read_text().format(
        style=(HERE / "prompts" / "style.md").read_text(), week=monday,
        end=(dt.date.fromisoformat(monday) + dt.timedelta(days=6)).isoformat(),
        header=f"{week_n} new issues across {len({x['repo'] for x in issues})} repos ({spam_count} spam removed)",
        stats=stat_lines, issues="\n".join(cand))
    return ask(prompt, cfg["models"]["maker"]).strip() + "\n"
