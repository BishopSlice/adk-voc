"""Run slice-1 pipeline for one week: fetch, spam, classify, brief, check."""
import argparse
import json
from pathlib import Path

import brief
import check
import classify
import fetch
import spam

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", required=True, help="Monday, YYYY-MM-DD")
    ap.add_argument("--skip-fetch", action="store_true", help="reuse data/<week>/issues.json")
    a = ap.parse_args()
    start, end = fetch.week_bounds(a.week)
    d = HERE / "data" / a.week
    d.mkdir(parents=True, exist_ok=True)

    f = d / "issues.json"
    if not (a.skip_fetch and f.exists()):
        f.write_text(json.dumps(fetch.fetch_week(a.week), indent=1))
    issues = json.loads(f.read_text())
    this_week = [x for x in issues if start <= x["created"] <= end]
    kept = [x for x in this_week if not spam.is_spam(x)]
    print(f"fetched {len(issues)} (W {len(this_week)}), spam {len(this_week) - len(kept)}")

    labels = classify.classify(kept)
    (d / "labels.json").write_text(json.dumps(labels, indent=1))

    md = brief.write_brief(kept, labels, a.week, len(this_week) - len(kept))
    (d / "brief.md").write_text(md)
    print("TL;DR within limits:", brief.tldr_ok(md))

    v = check.check_brief(md, a.week)
    rate = check.pass_rate(v)
    (d / "check.json").write_text(json.dumps({"pass_rate": rate, "claims": v}, indent=1))
    print(f"checker: {sum(x['verdict'] == 'SUPPORTED' for x in v)}/{len(v)} supported ({rate:.0%})")


if __name__ == "__main__":
    main()
