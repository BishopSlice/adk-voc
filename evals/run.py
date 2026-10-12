"""Run every eval suite and print scores per slice tag.

Usage (from app/): python3 evals/run.py [--holdout] [--suite classify]
Dev cases run by default. --holdout runs only the holdout set: use it once, before shipping.
Exit code 1 if any suite is unbuilt or misses its bar.
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

# Bars from 04-build/constraints.md
BARS = {"classify": 0.90, "checker": 1.00, "redflag": 1.00, "regression": 1.00}


def load(name, split):
    rows = [json.loads(line) for line in open(ROOT / "goldens" / f"{name}.jsonl")]
    return [r for r in rows if r["split"] == split]


def run_classify(cases):
    from classify import classify  # classify(list[issue]) -> {url: theme}
    got = classify(cases)
    for c in cases:
        if got.get(c["url"]) not in [c["gold"], *c["also_ok"]]:
            print(f"    miss {c['id']}: {c['title'][:70]!r} gold={c['gold']} got={got.get(c['url'])}")
    from baseline.cluster import rules_classify
    rules = rules_classify(cases)
    r = sum(rules[c["url"]] in [c["gold"], *c["also_ok"]] for c in cases) / len(cases)
    m = sum(got.get(c["url"]) in [c["gold"], *c["also_ok"]] for c in cases) / len(cases)
    strict = sum(got.get(c["url"]) == c["gold"] for c in cases) / len(cases)
    print(f"    keyword rules {r:.0%}; classifier margin {(m - r) * 100:+.0f} pts (bar +5); "
          f"strict gold only {strict:.0%}")
    if m - r < 0.05:
        return [("margin vs rules below +5 pts", False)]
    return [(c["gold"], got.get(c["url"]) in [c["gold"], *c["also_ok"]]) for c in cases]


def run_checker(cases):
    import check  # check_claims(list[claim]) -> {claim_id: verdict}
    check.DATA = ROOT / "fixtures"  # frozen data, so count goldens never drift
    got = check.check_claims(cases)
    return [(c["slice"], got.get(c["id"]) == c["gold"]) for c in cases]


def run_redflag(cases):
    from redflags import red_flags  # red_flags(list[issue]) -> set of urls
    got = red_flags(cases)
    return [(c["slice"], (c["url"] in got) == c["gold"]) for c in cases]


def run_regression(cases):
    from releases import regressions  # regressions(list[issue], version) -> set of urls
    got = regressions(cases, "2.11.0")
    return [(c["slice"], (c["url"] in got) == c["gold"]) for c in cases]


SUITES = {"classify": run_classify, "checker": run_checker,
          "redflag": run_redflag, "regression": run_regression}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout", action="store_true")
    ap.add_argument("--suite", choices=SUITES)
    args = ap.parse_args()
    split = "holdout" if args.holdout else "dev"
    ok = True
    for name, fn in SUITES.items():
        if args.suite and name != args.suite:
            continue
        cases = load(name, split)
        if not cases:
            print(f"{name:11} no {split} cases")
            continue
        try:
            results = fn(cases)
        except ImportError as e:
            print(f"{name:11} NOT BUILT ({e.name})")
            ok = False
            continue
        by = defaultdict(list)
        for tag, passed in results:
            by[tag].append(passed)
        score = sum(p for _, p in results) / len(results)
        status = "PASS" if score >= BARS[name] else "FAIL"
        ok &= status == "PASS"
        print(f"{name:11} {score:5.0%}  bar {BARS[name]:.0%}  {status}  ({split}, n={len(results)})")
        for tag, ps in sorted(by.items()):
            print(f"    {tag:40} {sum(ps)}/{len(ps)}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
