"""AC3: Sonnet sorts each non-spam issue into one fixed theme or Other."""
from pathlib import Path

import yaml

from llm import ask_claude, fence

HERE = Path(__file__).resolve().parent
THEMES = list(yaml.safe_load(open(HERE / "config.yaml"))["themes"])


def build_prompt(issues: list[dict]) -> str:
    blocks = "\n".join(f'<issue id="{i}">\n{fence(x["title"])}\n\n{fence(x["body"][:800])}\n</issue>'
                       for i, x in enumerate(issues, 1))
    tpl = (HERE / "prompts" / "classify.md").read_text()
    return tpl.format(themes=(HERE / "prompts" / "themes.md").read_text(), issues=blocks)


def parse_labels(raw: str, issues: list[dict]) -> dict:
    got = {}
    for line in raw.splitlines():
        i, _, theme = line.partition("\t")
        if i.strip().isdigit() and 0 < int(i) <= len(issues):
            theme = theme.strip()
            got[issues[int(i) - 1]["url"]] = theme if theme in THEMES else "Other"
    return {x["url"]: got.get(x["url"], "Other") for x in issues}


def classify(issues: list[dict], ask=ask_claude, batch: int = 40) -> dict:
    model = yaml.safe_load(open(HERE / "config.yaml"))["models"]["maker"]
    out = {}
    for k in range(0, len(issues), batch):
        part = issues[k:k + batch]
        out |= parse_labels(ask(build_prompt(part), model), part)
    return out
