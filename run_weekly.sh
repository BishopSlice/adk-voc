#!/bin/sh
# AC11: the unattended weekly run. launchd calls this at Monday 09:00, at login and every hour.
# It runs only when a week is due (runlog.py due_week), so the hourly calls are the catch-up after sleep.
# Only the most recent full week is caught up. If the Mac missed two Mondays, run the older week by hand.
# Manual rerun after a hold: ./run_weekly.sh 2026-10-12
set -u
cd "$(dirname "$0")"
# The Framework Python has the packages; Homebrew's python3 does not, so it must come first.
export PATH="/Library/Frameworks/Python.framework/Versions/3.13/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
mkdir -p data
HEADER="week,run_start,run_end,fetched,spam,claims,pass_rate,retries,tokens,other_share,outcome,note"

notify() { "${ADKVOC_NOTIFY:-osascript}" -e "display notification \"$2\" with title \"adk-voc: $1\"" >/dev/null 2>&1; }
error_row() {  # week, note. For failures where Python could not log.
  [ -f data/runs.csv ] || echo "$HEADER" > data/runs.csv
  now=$(date '+%Y-%m-%dT%H:%M')
  echo "$1,$now,$now,n/a,n/a,n/a,n/a,n/a,n/a,n/a,error,$2" >> data/runs.csv
  notify "error, week $1" "$2"
}

# One run at a time. A lock whose process is gone, or older than 2 hours, is stale: clear it and say so.
if ! mkdir data/.lock 2>/dev/null; then
  pid=$(cat data/.lock/pid 2>/dev/null || echo "")
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null && [ -z "$(find data/.lock -maxdepth 0 -mmin +120)" ]; then
    exit 0  # a run is in progress
  fi
  rm -f data/.lock/pid; rmdir data/.lock
  notify "stale lock cleared" "A previous run died mid-way. Starting again."
  mkdir data/.lock || exit 1
fi
echo $$ > data/.lock/pid
trap 'rm -f data/.lock/pid; rmdir data/.lock' EXIT

if [ $# -gt 0 ]; then
  week=$1
else
  week=$(python3 runlog.py due_week --log data/runs.csv) || { error_row unknown "due_week failed; see /tmp/adkvoc.err"; exit 1; }
fi
[ -n "$week" ] || exit 0  # nothing due
case "$week" in
  [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) ;;
  *) echo "week must be YYYY-MM-DD" >&2; exit 2 ;;
esac

echo "$(date '+%F %T') run week $week" >> data/weekly.log
before=$(cat data/runs.csv 2>/dev/null | wc -l)
python3 run.py --week "$week" --publish >> data/weekly.log 2>&1
code=$?
# If Python itself failed (missing package, broken install), run.py never logged. Log and notify here.
if [ "$code" -ne 0 ] && [ "$(cat data/runs.csv 2>/dev/null | wc -l)" = "$before" ]; then
  error_row "$week" "run.py exit $code before logging; see data/weekly.log"
fi
exit "$code"
