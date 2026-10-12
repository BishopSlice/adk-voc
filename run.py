"""Run slice-1 pipeline for one week: fetch, spam, classify, brief, check."""
import argparse
import datetime
import json
from pathlib import Path

import yaml

import brief
import check
import classify
import fetch
import quotes
import redflags
import releases
import spam
from score import pain_table

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", required=True, help="Monday, YYYY-MM-DD")
    ap.add_argument("--skip-fetch", action="store_true", help="reuse data/<week>/issues.json")
    ap.add_argument("--recheck", action="store_true", help="reuse labels and brief, rerun only the checker")
    a = ap.parse_args()
    cfg = yaml.safe_load(open(HERE / "config.yaml"))
    start, end = fetch.week_bounds(a.week)
    prev_start = (datetime.date.fromisoformat(a.week) - datetime.timedelta(days=7)).isoformat()
    d = HERE / "data" / a.week
    d.mkdir(parents=True, exist_ok=True)

    f = d / "issues.json"
    if not (a.skip_fetch and f.exists()):
        f.write_text(json.dumps(fetch.fetch_week(a.week), indent=1))
    issues = json.loads(f.read_text())
    this_week = [x for x in issues if start <= x["created"] <= end]
    kept = [x for x in this_week if not spam.is_spam(x)]
    both = [x for x in issues if not spam.is_spam(x)]  # W and W-1, for trends
    print(f"fetched {len(issues)} (W {len(this_week)}), spam {len(this_week) - len(kept)}")

    rel_facts = "(not recorded)"
    if a.recheck:
        md = (d / "brief.md").read_text()
        if (d / "releases.json").exists():
            rel_facts = (d / "releases.json").read_text()
        labels = json.loads((d / "labels.json").read_text())
        missing = [x["url"] for x in both if x["url"] not in labels]
        if missing:
            raise SystemExit(f"--recheck: {len(missing)} issues unlabeled (old labels.json?). Rerun without --recheck.")
    else:
        labels = classify.classify(both)
        (d / "labels.json").write_text(json.dumps(labels, indent=1))
        flags = redflags.red_flags(kept)
        (d / "flags.json").write_text(json.dumps(flags, indent=1))  # raw lines, before the wording guard
        recent, regs, changes = {}, {}, {}
        for repo in cfg["repos"]:
            recent[repo] = releases.recent_release(releases.fetch_releases(repo), a.week)
            if recent[repo]:
                mine = [x for x in both if x["repo"] == repo and x["created"] >= recent[repo]["date"]]
                regs[repo] = sorted(releases.regressions(mine, recent[repo]["tag"]))
                changes[repo] = releases.rate_changes([x for x in both if x["repo"] == repo], labels,
                                                      recent[repo]["date"], prev_start, end)
        rel_facts = json.dumps({"latest_release": recent, "regression_scan_by_code (all issues since each "
                                "release, both weeks)": regs, "repos": cfg["repos"]})
        (d / "releases.json").write_text(rel_facts)
        titles = {x["url"]: x["title"][:70] for x in both}
        since_md = releases.render_since_release(recent, regs, changes, titles)
        md = brief.write_brief(both, labels, a.week, len(this_week) - len(kept), flags=flags, release_note=since_md)
        md = brief.insert_sections(md, redflags.render_red_flags(flags, both), since_md)
        md, cleaned = brief.sanitize_brief(md, both)  # fail closed: strip anything unsafe before checking
        (d / "brief.md").write_text(md)
        (d / "sanitized.json").write_text(json.dumps(cleaned, indent=1))
    print("TL;DR within limits:", brief.tldr_ok(md))

    facts = (f"fetched: {len(issues)} issues (weeks W and W-1); this week: {len(this_week)}; "
             f"spam removed: {len(this_week) - len(kept)}; classified: {len(kept)} this week, {len(both)} across both weeks; "
             "method: GitHub search API, rule-based spam filter, Sonnet themes, counted in code, "
             "quotes copied from issue bodies; pain = issues x severity weight x repos affected x "
             "(1 + median comments / 10), computed in code; severity weights: "
             + ", ".join(f"{t} {w}" for t, w in cfg["themes"].items())
             + "; the Since last release and Red flags sections are rendered by code from the GitHub "
             "releases API and the red-flag picker; latest release per repo in the window (GitHub releases "
             "API): " + rel_facts)
    v = check.check_brief(md, a.week, facts=facts)
    rows = pain_table(both, labels, a.week, cfg["themes"])
    v += quotes.quote_failures(md, both, min(5, len(rows))) + quotes.table_failures(md, rows)
    v += [{"claim": f"link {u}", "verdict": "NOT_SUPPORTED", "reason": "not one of this run's issues"}
          for u in brief.foreign_links(md, both)]
    if (d / "sanitized.json").exists():
        v += json.loads((d / "sanitized.json").read_text())  # anything removed counts against the gate  # code checks, never skipped
    rate = check.pass_rate(v)
    (d / "check.json").write_text(json.dumps({"pass_rate": rate, "claims": v}, indent=1))
    print(f"checker: {sum(x['verdict'] == 'SUPPORTED' for x in v)}/{len(v)} supported ({rate:.0%})")


if __name__ == "__main__":
    main()
