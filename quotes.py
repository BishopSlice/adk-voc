"""AC5 exact quotes and AC9 table recompute (issues, trend, pain), checked in code (not by an LLM)."""
import re

QUOTE = re.compile(r'^> ["\u201c](.+)["\u201d][ \t]*\n((?:.*\n?){0,3})', re.M)
MIN_QUOTE = 20  # the link is within the next 3 lines
LINK = re.compile(r"https://github\.com/google/[\w-]+/issues/\d+")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def quote_failures(brief_md: str, issues: list[dict], min_quotes: int = 0) -> list[dict]:
    bodies = {x["url"]: _norm(x["body"]) for x in issues}
    found = QUOTE.findall(brief_md)
    fails = [] if len(found) >= min_quotes else [
        {"claim": "one quote per top theme", "verdict": "NOT_SUPPORTED",
         "reason": f"found {len(found)} quotes, need {min_quotes}"}]
    for q, next_line in found:
        m = LINK.search(next_line)
        if len(_norm(q)) < MIN_QUOTE:
            fails.append({"claim": f'quote "{q}"', "verdict": "NOT_SUPPORTED",
                          "reason": f"shorter than {MIN_QUOTE} characters"})
        elif not m:
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
    pat = r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([\d.]+)\s*\|"
    found = re.findall(pat, brief_md, re.M)
    need = min(5, len(rows))
    if len(found) < need:
        fails.append({"claim": "Top 5 table", "verdict": "NOT_SUPPORTED",
                      "reason": f"matched {len(found)} table rows, expected {need} (format drift?)"})
    for rank, theme, n, tr, pain in found:
        if int(rank) <= len(rows) and rows[int(rank) - 1]["theme"] != theme:
            fails.append({"claim": f"#{rank} {theme}", "verdict": "NOT_SUPPORTED",
                          "reason": f"rank {rank} is {rows[int(rank) - 1]['theme']}"})
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
