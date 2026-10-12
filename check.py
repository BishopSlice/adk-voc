"""AC9: Opus checks every claim in a separate run, recomputing numbers from the data."""
import json
import re
import subprocess
from pathlib import Path

import yaml

from llm import ask_claude

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"


def parse_verdicts(raw: str) -> list[dict]:
    v = json.loads(raw[raw.index("["):raw.rindex("]") + 1])
    for x in v:
        if x["verdict"] != "SUPPORTED":
            x["verdict"] = "NOT_SUPPORTED"  # unsure counts as not supported
    return v


def pass_rate(verdicts: list[dict]) -> float:
    return sum(x["verdict"] == "SUPPORTED" for x in verdicts) / len(verdicts) if verdicts else 0.0


def _known_issues() -> dict:
    known = {}
    for f in DATA.glob("*/issues.json"):
        known |= {x["url"]: x for x in json.loads(f.read_text())}
    cache = DATA / "cache.json"
    if cache.exists():
        known |= json.loads(cache.read_text())
    return known


def source_body(url: str, known: dict) -> str:
    if url not in known:
        m = re.match(r"https://github.com/google/([\w-]+)/issues/(\d+)", url)
        out = subprocess.run(["curl", "-sS", f"https://api.github.com/repos/google/{m[1]}/issues/{m[2]}"],
                             capture_output=True, text=True, timeout=60)
        it = json.loads(out.stdout)
        known[url] = {"url": url, "title": it["title"], "body": (it.get("body") or "")[:1000]}
        cache = DATA / "cache.json"
        old = json.loads(cache.read_text()) if cache.exists() else {}
        DATA.mkdir(exist_ok=True)
        cache.write_text(json.dumps(old | {url: known[url]}))
    return f"<source url=\"{url}\">\n{known[url]['title']}\n\n{known[url]['body']}\n</source>"


def data_table(monday: str) -> str:
    d = DATA / monday
    if not (d / "labels.json").exists():
        return "(none)"
    labels = json.loads((d / "labels.json").read_text())
    rows = [x for x in json.loads((d / "issues.json").read_text()) if x["url"] in labels]
    return "\n".join(f"{x['created']}\t{x['repo']}\t{labels[x['url']]}\t{x['url']}" for x in rows)


def _run(task: str, urls: list[str], monday: str | None, ask) -> list[dict]:
    known = _known_issues()
    model = yaml.safe_load(open(HERE / "config.yaml"))["models"]["checker"]
    prompt = (HERE / "prompts" / "check.md").read_text().format(
        task=task, sources="\n".join(source_body(u, known) for u in dict.fromkeys(urls)),
        data=data_table(monday) if monday else "(none)")
    return parse_verdicts(ask(prompt, model))


def check_brief(brief_md: str, monday: str, ask=ask_claude) -> list[dict]:
    urls = re.findall(r"https://github\.com/google/[\w-]+/issues/\d+", brief_md)
    task = ("Split the BRIEF into atomic claims (each number, trend, quote, characterization and "
            "link description is one claim; ids c1, c2...). Check each.\n\nBRIEF:\n" + brief_md)
    return _run(task, urls, monday, ask)


def check_claims(claims: list[dict], ask=ask_claude) -> dict:
    """Eval entry point: claims with ids and sources (issue urls or data:<monday>)."""
    urls = [s for c in claims for s in c["sources"] if s.startswith("http")]
    weeks = {s[5:] for c in claims for s in c["sources"] if s.startswith("data:")}
    task = "Check each claim, using its id.\n\nCLAIMS:\n" + "\n".join(
        f"- {c['id']}: {c['claim']} (sources: {', '.join(c['sources'])})" for c in claims)
    return {x["id"]: x["verdict"] for x in _run(task, urls, next(iter(weeks), None), ask)}
