"""AC2: drop spam with fixed rules. Excluded items are counted in the run log."""
import re

CAMEL = re.compile(r"[a-z][A-Z]")
TECH = re.compile(r"[_.()/:`#\d]|\b(error|crash|bug|fails?|hangs?|leak|nil|null|"
                  r"pointer|timeout|agent|tool|session|runner|model|api|mcp|a2a|adk)\b", re.I)


def is_spam(issue: dict) -> bool:
    title = issue["title"].strip()
    if "spam" in issue["labels"] or not title:
        return True
    if re.fullmatch(r"https?://\S+", title):
        return True
    return len(title.split()) < 3 and not (TECH.search(title) or CAMEL.search(title))
