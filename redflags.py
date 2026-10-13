"""AC7: Sonnet picks up to 5 red flags. Code renders the section and guards the wording."""
import re
from pathlib import Path

import yaml

from brief import SHORT, safe_text
from llm import ask_claude, fence

HERE = Path(__file__).resolve().parent
CATEGORIES = {"security", "data-loss", "side-effects", "safety-gate"}
ALLOWED = re.compile(r"[A-Za-z0-9 ,.'’-]+")
BANNED = re.compile(r"\b(critical|severe|vulnerab\w*|confirmed|alarming|exploit\w*|payload|curl|cve|"
                    r"bypass(es|ed|ing)?|skip\w*|header|password|secret|"  # no exploit steps
                    r"reported by|according to|says|said)\b|\bX-[A-Za-z-]+:", re.I)  # no people


TRIAGE = re.compile(r"\b(P[34]|S[34])\b|infeasible|won'?t fix|working as intended", re.I)


def open_only(issues: list[dict]) -> list[dict]:
    """Policy (Vicky, 2026-10-13): closed issues are likely fixed, so they are never red flags."""
    return [x for x in issues if x.get("state", "open") == "open"]


def why_ok(why: str) -> bool:
    """Plain words only (an allowlist), 20 words or fewer, no hype or exploit words (Never boundary)."""
    return 0 < len(why.split()) <= 20 and bool(ALLOWED.fullmatch(why)) and not BANNED.search(why)


def red_flags(issues: list[dict], ask=ask_claude) -> dict:
    """Returns {url: {"category", "why"}}, at most 5, in the model's order."""
    blocks = "\n".join(f'<issue id="{i}">\n{fence(x["title"])}\n\n{fence(x["body"][:1500])}\n</issue>'
                       for i, x in enumerate(issues, 1))
    prompt = (HERE / "prompts" / "redflags.md").read_text().format(issues=blocks)
    model = yaml.safe_load(open(HERE / "config.yaml"))["models"]["maker"]
    out = {}
    for line in ask(prompt, model).splitlines():
        parts = [p.strip() for p in line.split("\t")]
        ids = [int(i) for i in parts[0].split(",") if i.strip().isdigit() and 0 < int(i) <= len(issues)] \
            if len(parts) == 3 else []
        if ids and len(out) < 5:
            cat = parts[1] if parts[1] in CATEGORIES else "security"
            f = {"category": cat, "why": parts[2]}
            if len(ids) > 1:
                f["also"] = [issues[i - 1]["url"] for i in ids[1:]]  # same bug in other repos
            out[issues[ids[0] - 1]["url"]] = f
    return out


def render_red_flags(flags: dict, issues: list[dict]) -> str:
    by = {x["url"]: x for x in issues}
    lines = ["## Red flags"]
    for url, f in flags.items():
        x = by[url]
        repo = re.search(r"google/([\w-]+)/", url)[1]
        n = url.rsplit("/", 1)[1]
        title = safe_text(x["title"])[:70]
        why = f["why"].rstrip(".") if why_ok(f["why"]) else title  # the title is a fact the issue shows
        state = x.get("state", "open")
        links = [f"[{SHORT.get(repo, repo)}#{n}: {title}]({url})"]
        for u in f.get("also", []):
            r2, n2 = re.search(r"google/([\w-]+)/", u)[1], u.rsplit("/", 1)[1]
            links.append(f"[{SHORT.get(r2, r2)}#{n2}]({u})")
        triage = " The issue mentions an earlier low-priority triage." if any(
            TRIAGE.search(by.get(u, {}).get("body", "")) for u in [url, *f.get("also", [])]) else ""
        lines.append(f"- Reported ({f['category']}, {state}): {why}.{triage} {' · '.join(links)}")
    if not flags:
        lines.append("No red flags this week.")
    return "\n".join(lines) + "\n"
