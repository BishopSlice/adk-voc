"""AC5 (basic) and AC8: compute stats in code, then Sonnet writes the brief from them."""
import datetime as dt
import re
from pathlib import Path

import yaml

from llm import ask_claude, fence
from score import pain_table

HERE = Path(__file__).resolve().parent
SHORT = {"adk-python": "py", "adk-go": "go", "adk-java": "java", "adk-js": "js", "adk-docs": "docs"}


MENTION = re.compile(r"(?<![\w`])@(?=[A-Za-z0-9])")
EXPLOIT = re.compile(r"\b(curl|wget|rm -rf|base64|eval\(|exec\(|payload|exploit|/etc/passwd|"
                     r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", re.I)


def safe_text(s: str) -> str:
    """Untrusted text (titles) shown as plain words: no Markdown, HTML or @mentions."""
    s = re.sub(r"[\[\]()<>!`*_|\\#]|//", " ", s)
    return re.sub(r"\s+", " ", MENTION.sub("@ ", s)).strip()


def sanitize_brief(md: str, issues: list[dict]) -> tuple[str, list[dict]]:
    """Fail closed before publishing: remove HTML, foreign links, @mentions and risky quotes.

    Returns the cleaned Markdown and one NOT_SUPPORTED row per thing removed."""
    ok = {x["url"] for x in issues}
    problems = []

    def bad(what, why):
        problems.append({"claim": what[:80], "verdict": "NOT_SUPPORTED", "reason": why})

    def link(m):
        if m[2] in ok or m[2] == "#method":
            return m[0]
        bad(m[0], "link to something outside this run's issues; removed")
        return m[1]
    md = re.sub(r"(?<!!)\[([^\]]*)\]\(([^)\s]*)\)", link, md)
    for pat, why in ((r"!\[[^\]]*\]\([^)]*\)", "image; removed"), (r"<[^>]*>", "HTML or autolink; removed"),
                     (r"^\[[^\]]+\]:\s*\S+.*$", "reference link; removed")):
        for m in re.findall(pat, md, re.M):
            bad(m, why)
        md = re.sub(pat, "", md, flags=re.M)
    for u in re.findall(r"(?<!\()https?://[^\s)\]]+", md):
        if u not in ok:
            bad(u, "bare URL outside this run's issues; removed")
            md = md.replace(u, "")
    if MENTION.search(md):
        bad("@mention", "mentions would ping people; neutralized")
        md = MENTION.sub("@ ", md)
    for q in re.findall(r'^> ["\u201c](.+)["\u201d]', md, re.M):
        if EXPLOIT.search(q) or len(q) > 300:
            bad(q, "quote with exploit-style detail or over 300 characters; removed")
            md = md.replace(q, "(quote removed)")
    return md, problems


def foreign_links(md: str, issues: list[dict]) -> list[str]:
    """Any link that isn't one of this run's issues (an injection could plant one)."""
    ok = {x["url"] for x in issues} | {"#method"}
    return [u for u in re.findall(r"\]\(([^)]+)\)", md) if u not in ok]


def insert_sections(md: str, red_flags_md: str, since_md: str) -> str:
    """Code-rendered sections go in fixed places: Red flags before Top 5, Since release before Method."""
    for h in ("## Red flags", "## Since last release"):
        if h in md:
            raise ValueError(f"maker wrote its own {h!r} section")
    for h in ("## Top 5 themes", "## Method"):
        if md.count(h) != 1:
            raise ValueError(f"expected exactly one {h!r} heading, found {md.count(h)}")
    md = md.replace("## Top 5 themes", red_flags_md + "\n## Top 5 themes", 1)
    return md.replace("## Method", since_md + "\n## Method", 1)


def tldr_ok(md: str) -> bool:
    m = re.search(r"^## TL;DR\n(.*?)(?=^## )", md, re.S | re.M)
    if not m:
        return False
    lines = [x for x in m.group(1).splitlines() if x.strip()]
    visible = [re.sub(r"\]\([^)]*\)", "]", x) for x in lines]  # link targets aren't read
    return 0 < len(lines) <= 5 and all(len(x) < 120 for x in visible)


def write_brief(issues, labels, monday, spam_count, ask=ask_claude, flags=None, release_note="") -> str:
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
        weights=" · ".join(f"{t} {w}" for t, w in cfg["themes"].items()),
        flags="\n".join(f"- {u}: {w}" for u, w in (flags or {}).items()) or "none",
        release=release_note or "none")
    return ask(prompt, cfg["models"]["maker"]).strip() + "\n"
