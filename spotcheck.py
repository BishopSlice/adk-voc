"""AC13: pick 5 random supported claims for Vicky to check by hand, and record agreement."""
import argparse
import csv
import datetime as dt
import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


SHORT = {"adk-python": "py", "adk-go": "go", "adk-java": "java", "adk-js": "js", "adk-docs": "docs"}


def kind(c: dict, flag_refs: set = frozenset()) -> str:
    t = c.get("claim", "")
    if any(t.startswith(r + ":") or t.startswith(r + " reporter") for r in flag_refs):
        return "red flag"
    if '"' in t or "\u201c" in t or re.search(r"\bquote", t, re.I):
        return "quote"
    if re.search(r"\d+\s*issues|[▲▼]|\d+%|pain|→", t, re.I):
        return "number"
    return "other"


def flag_refs(week_dir: Path) -> set:
    f = week_dir / "flags.json"
    if not f.exists():
        return set()
    refs = set()
    for url in [u for u, v in json.loads(f.read_text()).items() for u in [u, *v.get("also", [])]]:
        m = re.search(r"google/([\w-]+)/issues/(\d+)", url)
        refs.add(f"{SHORT.get(m[1], m[1])}#{m[2]}")
    return refs


def sample(claims: list[dict], k: int = 5, seed: int | None = None, flag_refs: set = frozenset()) -> list[dict]:
    """At least one quote, one number and one red-flag line when the brief has them; the rest random."""
    rng = random.Random(seed)
    supported = [c for c in claims if c["verdict"] == "SUPPORTED"]
    picked = []
    for want in ("quote", "number", "red flag"):
        pool = [c for c in supported if kind(c, flag_refs) == want and c not in picked]
        if pool:
            picked.append(rng.choice(pool))
    rest = [c for c in supported if c not in picked]
    return picked + rng.sample(rest, min(k - len(picked), len(rest)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", required=True)
    ap.add_argument("--agree", type=int, help="how many of the 5 you agreed with (records it)")
    a = ap.parse_args()
    d = HERE / "data" / a.week
    if a.agree is None:
        refs = flag_refs(d)
        for c in sample(json.loads((d / "check.json").read_text())["claims"], seed=a.week, flag_refs=refs):
            print(f"- {c['id']} ({kind(c, refs)}): {c['claim']}\n  evidence: {c.get('evidence', '')[:200]}")
        print(f"\nCheck each against its issue, then run: python3 spotcheck.py --week {a.week} --agree N")
        return
    f = HERE / "data" / "spotcheck.csv"
    new = not f.exists()
    with open(f, "a", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["week", "date", "agreed_of_5"])
        w.writerow([a.week, dt.date.today().isoformat(), a.agree])
    print("Recorded." + (" Disagreement: fix the checker prompt before the next run." if a.agree < 5 else ""))


if __name__ == "__main__":
    main()
