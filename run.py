"""Run one week: fetch, spam, classify, brief, check, gate, then publish or hold."""
import argparse
import re
import os
import datetime
import json
from pathlib import Path

import yaml

import brief
import check
import classify
import fetch
import gate
import notify
import publish
import quotes
import redflags
import releases
import runlog
import spam
from llm import ClaudeError
from score import pain_table

HERE = Path(__file__).resolve().parent


def main():
    """Every run ends with a runs.csv row, and every hold or error with a notification."""
    a = parse_args()
    d = HERE / "data" / a.week
    row = {"week": a.week, "run_start": now(), "outcome": "error"}
    ctx = {"step": "fetch"}
    try:
        run_week(a, row, ctx)
    except ClaudeError as e:
        kind = runlog.error_kind(e)
        if not kind:
            row["note"] = f"{ctx['step']}: {e}"[:200]
            notify.notify(f"error, week {a.week}", row["note"])
            raise
        p = runlog.write_auth_hold(d, a.week, kind, ctx["step"])
        row.update(outcome="hold", note=f"{kind} error at {ctx['step']}")
        notify.notify(f"HOLD, week {a.week}", f"{row['note']}. See {p}")
        print("HOLD:", p)
    except Exception as e:
        row["note"] = f"{ctx['step']}: {type(e).__name__}: {e}"[:200]
        notify.notify(f"error, week {a.week}", row["note"])
        raise
    finally:
        row["run_end"] = now()
        runlog.append(HERE / "data" / "runs.csv", row)


def now():
    return datetime.datetime.now().isoformat(timespec="minutes")


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", required=True, help="Monday, YYYY-MM-DD")
    ap.add_argument("--skip-fetch", action="store_true", help="reuse data/<week>/issues.json")
    ap.add_argument("--recheck", action="store_true", help="reuse labels and brief, rerun only the checker")
    ap.add_argument("--publish", action="store_true", help="commit and push the brief if the gate passes")
    return ap.parse_args()


def run_week(a, row, ctx):
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
    row.update(fetched=len(issues), spam=len(this_week) - len(kept))
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
        ctx["step"] = "classify"
        labels = classify.classify(both)
        (d / "labels.json").write_text(json.dumps(labels, indent=1))
        ctx["step"] = "red flags"
        flags = redflags.red_flags(redflags.open_only(kept))
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
        since_md = releases.render_since_release(recent, regs, changes, titles, prev_start, end)
        ctx["step"] = "write"
        md = brief.write_brief(both, labels, a.week, len(this_week) - len(kept), flags=flags, release_note=since_md)
        md = brief.insert_sections(md, redflags.render_red_flags(flags, both), since_md)
        (d / "brief.md").write_text(md)
    print("TL;DR within limits:", brief.tldr_ok(md))

    facts = (f"fetched: {len(issues)} issues (weeks W and W-1); this week: {len(this_week)}; "
             f"spam removed: {len(this_week) - len(kept)}; classified: {len(kept)} this week, {len(both)} across both weeks; "
             "method: GitHub search API, rule-based spam filter, Sonnet themes, counted in code, "
             "quotes copied from issue bodies; pain = issues x severity weight x repos affected x "
             "(1 + median comments / 10), computed in code, higher means more pain, used to rank themes "
             "within a week; severity weights: "
             + ", ".join(f"{t} {w}" for t, w in cfg["themes"].items())
             + "; the Since last release and Red flags sections are rendered by code from the GitHub "
             "releases API and the red-flag picker; latest release per repo in the window (GitHub releases "
             "API): " + rel_facts)
    rows = pain_table(both, labels, a.week, cfg["themes"])
    bar = gate.effective_bar(os.environ.get("ADKVOC_PUBLISH_BAR"), cfg["publish_bar"])

    def check_all(md, cleaned):
        llm = check.check_brief(md, a.week, facts=facts)
        code = (quotes.quote_failures(md, both, min(5, len(rows))) + quotes.table_failures(md, rows)
                + [{"claim": f"link {u}", "verdict": "NOT_SUPPORTED", "reason": "not one of this run's issues"}
                   for u in brief.foreign_links(md, both)] + cleaned)
        links = len(set(re.findall(r"https://github\.com/google/[\w-]+/issues/\d+", md)))
        return llm, code, gate.decide(llm, code, brief.tldr_ok(md), bar=bar, links=links)

    share = runlog.other_share(labels, [x["url"] for x in kept])
    row["other_share"] = share
    if runlog.drift(share, cfg["other_drift_bar"]):
        row["note"] = f"theme drift: Other {share:.0%} (bar {cfg['other_drift_bar']:.0%})"
        notify.notify(f"theme drift, week {a.week}", row["note"] + ". Review the themes (Ask first).")
    ctx["step"] = "check"
    md, cleaned = brief.sanitize_brief(md, both)  # always, including hand-edited briefs on --recheck
    (d / "brief.md").write_text(md)
    llm, code, decision = check_all(md, cleaned)
    if not decision["publish"]:
        row["retries"] = 1
        ctx["step"] = "revise"
        print("gate: fail ->", "; ".join(decision["reasons"]), "-> one revision")
        failed = [x for x in llm if x["verdict"] != "SUPPORTED"] + code
        if not brief.tldr_ok(md):
            failed.append({"claim": "TL;DR", "reason": "over 5 lines or a line of 120+ visible characters"})
        try:
            md, cleaned = brief.sanitize_brief(brief.revise(md, failed), both)
            (d / "brief.md").write_text(md)
            llm, code, decision = check_all(md, cleaned)
        except ValueError as e:  # the revision broke the structure
            decision = {**decision, "publish": False, "reasons": decision["reasons"] + [f"revision failed: {e}"]}

    row.update(claims=len(llm), pass_rate=round(decision["pass_rate"], 3), retries=row.get("retries", 0))
    (d / "check.json").write_text(json.dumps({**decision, "claims": llm, "code_failures": code}, indent=1))
    print(f"checker: {sum(x['verdict'] == 'SUPPORTED' for x in llm)}/{len(llm)} supported "
          f"({decision['pass_rate']:.0%}); code failures: {len(code)}")
    if not decision["publish"]:
        p = gate.write_hold(d, a.week, decision, [x for x in llm if x["verdict"] != "SUPPORTED"] + code)
        row["outcome"] = "hold"
        notify.notify(f"HOLD, week {a.week}", f"{decision['pass_rate']:.0%} verified. See {p}")
        print("HOLD:", p)
        return
    (d / "HOLD.md").unlink(missing_ok=True)
    if a.publish:
        ctx["step"] = "publish"
        top = rows[0]["theme"] if rows else "n/a"
        print("published:", publish.publish(HERE, a.week, md, {"issues": len(kept), "pass_rate": decision["pass_rate"],
                                                               "top": top}))
        row["outcome"] = "pass"
    else:
        row["outcome"] = "pass (not published)"
        print("gate: pass. Not published (run with --publish).")

if __name__ == "__main__":
    main()
