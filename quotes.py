"""AC5 exact quotes and AC9 count recompute, checked in code (not by an LLM)."""
import re

QUOTE = re.compile(r'^> "(.+)"\s*\n(.*)$', re.M)
LINK = re.compile(r"https://github\.com/google/[\w-]+/issues/\d+")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def quote_failures(brief_md: str, issues: list[dict]) -> list[dict]:
    bodies = {x["url"]: _norm(x["body"]) for x in issues}
    fails = []
    for q, next_line in QUOTE.findall(brief_md):
        m = LINK.search(next_line)
        if not m:
            fails.append({"claim": f'quote "{q[:60]}"', "verdict": "NOT_SUPPORTED",
                          "reason": "no source link on the line after the quote"})
        elif _norm(q) not in bodies.get(m[0], ""):
            fails.append({"claim": f'quote "{q[:60]}"', "verdict": "NOT_SUPPORTED",
                          "reason": f"not an exact match for {m[0]}"})
    return fails


def count_failures(brief_md: str, counts: dict) -> list[dict]:
    fails = []
    for theme, n in re.findall(r"^\|\s*\d+\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|", brief_md, re.M):
        if counts.get(theme) != int(n):
            fails.append({"claim": f"{theme}: {n} issues", "verdict": "NOT_SUPPORTED",
                          "reason": f"recomputed count is {counts.get(theme, 0)}"})
    return fails
