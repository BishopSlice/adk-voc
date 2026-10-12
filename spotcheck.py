"""AC13: pick 5 random supported claims for Vicky to check by hand, and record agreement."""
import argparse
import csv
import datetime as dt
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sample(claims: list[dict], k: int = 5, seed: int | None = None) -> list[dict]:
    supported = [c for c in claims if c["verdict"] == "SUPPORTED"]
    return random.Random(seed).sample(supported, min(k, len(supported)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", required=True)
    ap.add_argument("--agree", type=int, help="how many of the 5 you agreed with (records it)")
    a = ap.parse_args()
    d = HERE / "data" / a.week
    if a.agree is None:
        for c in sample(json.loads((d / "check.json").read_text())["claims"], seed=a.week):
            print(f"- {c['id']}: {c['claim']}\n  evidence: {c.get('evidence', '')[:200]}")
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
