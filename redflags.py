"""AC7: Sonnet picks up to 5 red flags. Code renders the section and guards the wording."""
import re
from pathlib import Path

import yaml

from llm import ask_claude, fence

HERE = Path(__file__).resolve().parent
SHORT = {"adk-python": "py", "adk-go": "go", "adk-java": "java", "adk-js": "js", "adk-docs": "docs"}
EXPLOIT = re.compile(r"`|https?://|\b(curl|payload|exploit|inject|POST|GET)\b|\{.*:", re.I)


def why_ok(why: str) -> bool:
    """Neutral and short, with no exploit-style detail (Never boundary)."""
    return 0 < len(why.split()) <= 25 and not EXPLOIT.search(why)


def red_flags(issues: list[dict], ask=ask_claude) -> dict:
    """Returns {url: why}, at most 5, in the model's order."""
    blocks = "\n".join(f'<issue id="{i}">\n{fence(x["title"])}\n\n{fence(x["body"][:800])}\n</issue>'
                       for i, x in enumerate(issues, 1))
    prompt = (HERE / "prompts" / "redflags.md").read_text().format(issues=blocks)
    model = yaml.safe_load(open(HERE / "config.yaml"))["models"]["maker"]
    out = {}
    for line in ask(prompt, model).splitlines():
        i, _, why = line.partition("\t")
        if i.strip().isdigit() and 0 < int(i) <= len(issues) and len(out) < 5:
            out[issues[int(i) - 1]["url"]] = why.strip()
    return out


def render_red_flags(flags: dict, issues: list[dict]) -> str:
    by = {x["url"]: x for x in issues}
    lines = ["## Red flags"]
    for url, why in flags.items():
        x = by[url]
        repo = re.search(r"google/([\w-]+)/", url)[1]
        n = url.rsplit("/", 1)[1]
        why = why if why_ok(why) else "Reported as a severe issue. See the linked issue."
        lines.append(f"- {why} [{SHORT.get(repo, repo)}#{n}: {x['title'][:70]}]({url})")
    if not flags:
        lines.append("No red flags this week.")
    return "\n".join(lines) + "\n"
