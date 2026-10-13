"""AC11, AC12: the run log (runs.csv), which week is due, and holds for auth or usage-limit errors."""
import argparse
import csv
import datetime as dt
import re
from pathlib import Path

COLUMNS = ["week", "run_start", "run_end", "fetched", "spam", "claims", "pass_rate", "retries",
           "tokens", "other_share", "outcome", "note"]
MAX_ERRORS = 3  # transient errors retry on the hourly check, then wait for a human


def append(f: Path, row: dict) -> None:
    unknown = set(row) - set(COLUMNS)
    if unknown:
        raise KeyError(f"unknown run-log columns: {sorted(unknown)}")
    f = Path(f)
    f.parent.mkdir(parents=True, exist_ok=True)
    new = not f.exists()
    with open(f, "a", newline="") as fh:
        w = csv.DictWriter(fh, COLUMNS, restval="n/a")
        if new:
            w.writeheader()
        w.writerow(row)


def other_share(labels: dict, urls: list) -> float:
    return round(sum(labels.get(u) == "Other" for u in urls) / len(urls), 3) if urls else 0.0


def drift(share: float, bar: float) -> bool:
    return share > bar


def due_week(now: dt.datetime, f: Path) -> str | None:
    """The last full Monday-Sunday week, once it's Monday 09:00 or later. None if it already ran."""
    monday = (now - dt.timedelta(days=now.weekday())).replace(hour=9, minute=0, second=0, microsecond=0)
    if now < monday:
        monday -= dt.timedelta(days=7)
    week = (monday - dt.timedelta(days=7)).date().isoformat()
    past = [r["outcome"] for r in csv.DictReader(open(f)) if r["week"] == week] if Path(f).exists() else []
    if {"pass", "hold"} & set(past) or past.count("error") >= MAX_ERRORS:
        return None
    return week


def error_count(f: Path, week: str) -> int:
    return sum(r["week"] == week and r["outcome"] == "error" for r in csv.DictReader(open(f))) if Path(f).exists() else 0


def give_up_note(f: Path, week: str) -> str:
    """Said on the last automatic retry, so a dismissed banner isn't the only warning."""
    if error_count(f, week) + 1 < MAX_ERRORS:
        return ""
    return f" Giving up after {MAX_ERRORS} tries. Fix it, then run app/run_weekly.sh {week}."


def deadline(week: str) -> str:
    """On schedule means published by Wednesday 23:59 of the week the run happens."""
    wed = dt.date.fromisoformat(week) + dt.timedelta(days=9)
    return f"Wednesday {wed.isoformat()}, 23:59"


AUTH = re.compile(r"/login|claude login|api key|oauth|unauthori[sz]ed|authenticat|not logged in", re.I)
LIMIT = re.compile(r"usage limit|limit reached|rate limit|quota|resets? (at )?\d", re.I)


def error_kind(e: Exception) -> str | None:
    msg = str(e)
    if LIMIT.search(msg):
        return "limit"
    if AUTH.search(msg):
        return "auth"
    return None


def write_auth_hold(d: Path, week: str, kind: str, step: str) -> Path:
    what = ("returned an authentication error" if kind == "auth" else "hit a usage limit")
    fix = ("Run `claude login`." if kind == "auth" else "Wait for the usage limit to reset.")
    text = (f"# HOLD: week of {week}\n**Not published.** The run stopped at the {step} step. "
            f"`claude -p` {what}.\n\n## Next step\n1. {fix}\n2. Run `app/run_weekly.sh {week}`.\n"
            f"Deadline to stay on schedule: {deadline(week)}.\n")
    p = Path(d) / "HOLD.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def main():  # used by run_weekly.sh
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["due_week"])
    ap.add_argument("--log", required=True)
    a = ap.parse_args()
    w = due_week(dt.datetime.now(), Path(a.log))
    if w:
        print(w)


if __name__ == "__main__":
    main()
