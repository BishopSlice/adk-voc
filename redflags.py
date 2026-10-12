"""AC7: Sonnet picks up to 5 red flags. Code renders the section and guards the wording."""
import re
from pathlib import Path

import yaml

from brief import SHORT, safe_text
from llm import ask_claude, fence

HERE = Path(__file__).resolve().parent
CATEGORIES = {"security", "data-loss", "side-effects", "safety-gate"}
ALLOWED = re.compile(r"[A-Za-z0-9 ,.'’-]+")
BANNED = re.compile(r"\b(critical|severe|vulnerab\w*|confirmed|alarming|exploit\w*|payload|curl|cve)\b", re.I)


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
        if len(parts) == 3 and parts[0].isdigit() and 0 < int(parts[0]) <= len(issues) and len(out) < 5:
            cat = parts[1] if parts[1] in CATEGORIES else "security"
            out[issues[int(parts[0]) - 1]["url"]] = {"category": cat, "why": parts[2]}
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
        lines.append(f"- Reported ({f['category']}, {state}): {why}. [{SHORT.get(repo, repo)}#{n}: {title}]({url})")
    if not flags:
        lines.append("No red flags this week.")
    return "\n".join(lines) + "\n"
