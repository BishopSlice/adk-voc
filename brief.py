"""AC5 (basic) and AC8: compute stats in code, then Sonnet writes the brief from them."""
import datetime as dt
import re
from pathlib import Path

import yaml

from llm import ask_claude, fence
from score import pain_table

HERE = Path(__file__).resolve().parent
SHORT = {"adk-python": "py", "adk-go": "go", "adk-java": "java", "adk-js": "js", "adk-docs": "docs"}


# Never: personal data. Emails first (they contain @), then @handles, which are removed, not just spaced.
EMAIL = re.compile(r"(?<![\w/.+-])(?!git@)[\w.+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b(?!:)")
MENTION = re.compile(r"(?<![\w`])@[A-Za-z0-9][\w-]*(?![\w-]*/)")  # not @scope/pkg
# Never: exploit details. Commands, addresses, bypass wording, headers and secrets. A match blocks the brief.
# Narrow on purpose: matched against prose with link text removed, so issue titles can't hold a week.
EXPLOIT = re.compile(r"\b(curl|wget|sudo|exploit)\b|rm -rf|eval\(|exec\(|os\.system|/etc/passwd|\.\./\.\./|"
                     r"\bOR 1=1|\bbypass(es|ed|ing)?\b(?!_)|\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b|"
                     r"\bX-[A-Za-z-]+\s*:\s*\S|\bset\w* (the )?header|Authorization:\s*\S|"
                     r"\bBearer\s+[\w.-]{12,}|\b(token|api[_-]?key|password|secret)\s*[=:]\s*(?=\S*\d)[\w.-]{6,}|"
                     r"\bsk-[\w-]{6,}", re.I)
LINK_TEXT = re.compile(r"\[[^\]]*\]\([^)]*\)")


def safe_text(s: str) -> str:
    """Untrusted text (titles) shown as plain words: no Markdown, HTML or @mentions."""
    s = re.sub(r"[\[\]()<>!`*_|\\#]|//", " ", s)
    return re.sub(r"\s+", " ", MENTION.sub("someone", EMAIL.sub("an email address", s))).strip()


def sanitize_brief(md: str, issues: list[dict]) -> tuple[str, list[dict]]:
    """Fail closed before publishing: remove HTML, foreign links, personal data and exploit detail.

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
    if EMAIL.search(md):
        bad("email address", "personal data; removed")
        md = EMAIL.sub("(email removed)", md)
    if MENTION.search(md):
        bad("@mention", "username (personal data); removed")
        md = MENTION.sub("(name removed)", md)
    for q in re.findall(r'^> ["\u201c](.+)["\u201d]', md, re.M):
        if len(q) > 300:
            bad(q, "quote over 300 characters; removed")
            md = md.replace(q, "(quote removed)")
    lines = md.split("\n")
    for i, line in enumerate(lines):
        if EXPLOIT.search(LINK_TEXT.sub(" ", line)):
            bad(line, "exploit-style detail (command, bypass step, header or secret); line removed")
            lines[i] = "(line removed: exploit-style detail)"
    md = "\n".join(lines)
    return md, problems


def foreign_links(md: str, issues: list[dict]) -> list[str]:
    """Any link that isn't one of this run's issues (an injection could plant one)."""
    ok = {x["url"] for x in issues} | {"#method"}
    return [u for u in re.findall(r"\]\(([^)]+)\)", md) if u not in ok]


def split_code_sections(md: str) -> tuple[str, str, str]:
    """Lift out the code-rendered sections so the maker can't edit them during a revision."""
    def cut(text, h):
        m = re.search(rf"^{re.escape(h)}\n.*?(?=^## |\Z)", text, re.S | re.M)
        return (text[:m.start()] + text[m.end():], m[0]) if m else (text, "")
    md, rf = cut(md, "## Red flags")
    md, since = cut(md, "## Since last release")
    return md, rf, since


def revise(md: str, failures: list[dict], ask=ask_claude) -> str:
    body, rf, since = split_code_sections(md)
    model = yaml.safe_load(open(HERE / "config.yaml"))["models"]["maker"]
    probs = "\n".join(f"- {f.get('claim', '')}: {f.get('reason', '')}" for f in failures)
    prompt = (HERE / "prompts" / "revise.md").read_text().format(failures=fence(probs), brief=body)
    return insert_sections(ask(prompt, model).strip() + "\n", rf, since)


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
    visible = [re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", x) for x in lines]  # a reader sees only link text
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
