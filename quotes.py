"""AC5 exact quotes and AC9 table recompute (issues, trend, pain), checked in code (not by an LLM)."""
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


def table_failures(brief_md: str, rows: list[dict]) -> list[dict]:
    """Every Top 5 row: issues, trend and pain must equal what score.pain_table computed."""
    by = {r["theme"]: r for r in rows}
    fails = []
    pat = r"^\|\s*\d+\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([\d.]+)\s*\|"
    for theme, n, tr, pain in re.findall(pat, brief_md, re.M):
        r = by.get(theme)
        if r is None:
            fails.append({"claim": f"theme {theme}", "verdict": "NOT_SUPPORTED", "reason": "not a computed theme"})
            continue
        for name, said, real in (("issues", int(n), r["count"]), ("trend", tr, r["trend"]),
                                 ("pain", float(pain), r["pain"])):
            if said != real:
                fails.append({"claim": f"{theme} {name} {said}", "verdict": "NOT_SUPPORTED",
                              "reason": f"recomputed {name} is {real}"})
    return fails
