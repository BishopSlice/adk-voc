"""AC5 (basic) and AC8: compute stats in code, then Sonnet writes the brief from them."""
import datetime as dt
import re
from pathlib import Path

import yaml

from llm import ask_claude, fence
from score import pain_table

HERE = Path(__file__).resolve().parent
SHORT = {"adk-python": "py", "adk-go": "go", "adk-java": "java", "adk-js": "js", "adk-docs": "docs"}


def tldr_ok(md: str) -> bool:
    m = re.search(r"^## TL;DR\n(.*?)(?=^## )", md, re.S | re.M)
    if not m:
        return False
    lines = [x for x in m.group(1).splitlines() if x.strip()]
    visible = [re.sub(r"\]\([^)]*\)", "]", x) for x in lines]  # link targets aren't read
    return 0 < len(lines) <= 5 and all(len(x) < 120 for x in visible)


def write_brief(issues, labels, monday, spam_count, ask=ask_claude) -> str:
    cfg = yaml.safe_load(open(HERE / "config.yaml"))
    ranked = pain_table(issues, labels, monday, cfg["themes"])
    by_url = {x["url"]: x for x in issues}
    week_n = sum(r["count"] for r in ranked)
    stat_lines = "\n".join(f"- {r['theme']}: {r['count']} issues, vs last week {r['trend']}, pain {r['pain']}, "
                           f"repos {', '.join(SHORT.get(x, x) for x in r['repos'])}" for r in ranked)
    cand = []
    for r in ranked[:5]:
        cand.append(f"\n### {r['theme']}")
        top = sorted(r["urls"], key=lambda u: -by_url[u]["comments"])[:4]
        cand += [f"- {u} | {fence(by_url[u]['title'])} | {fence(by_url[u]['body'][:600])!r}" for u in top]
    prompt = (HERE / "prompts" / "brief.md").read_text().format(
        style=(HERE / "prompts" / "style.md").read_text(), week=monday,
        end=(dt.date.fromisoformat(monday) + dt.timedelta(days=6)).isoformat(),
        header=f"{week_n} new issues across {len(cfg['repos'])} repos ({spam_count} spam removed)",
        stats=stat_lines, issues="\n".join(cand),
        weights=" · ".join(f"{t} {w}" for t, w in cfg["themes"].items()))
    return ask(prompt, cfg["models"]["maker"]).strip() + "\n"
