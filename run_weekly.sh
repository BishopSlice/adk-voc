#!/bin/sh
# AC11: the unattended weekly run. launchd calls this at Monday 09:00, at login and every hour.
# It runs only when a week is due (runlog.py due_week), so the hourly calls are the catch-up after sleep.
# Manual rerun after a hold: ./run_weekly.sh 2026-10-12
set -u
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/Library/Frameworks/Python.framework/Versions/3.13/bin:/usr/local/bin:/usr/bin:/bin"
mkdir -p data
# One run at a time: a week's run takes about 15 minutes.
mkdir data/.lock 2>/dev/null || exit 0
trap 'rmdir data/.lock' EXIT

week="${1:-$(python3 runlog.py due_week --log data/runs.csv)}"
[ -n "$week" ] || exit 0
echo "$(date '+%F %T') run week $week" >> data/weekly.log
before=$(wc -l < data/runs.csv 2>/dev/null || echo 0)
python3 run.py --week "$week" --publish >> data/weekly.log 2>&1
code=$?
# If Python itself failed (missing package, broken install), run.py never logged. Log and notify here.
if [ "$code" -ne 0 ] && [ "$(wc -l < data/runs.csv 2>/dev/null || echo 0)" = "$before" ]; then
  [ -f data/runs.csv ] || echo "week,run_start,run_end,fetched,spam,claims,pass_rate,retries,tokens,other_share,outcome,note" > data/runs.csv
  now=$(date '+%Y-%m-%dT%H:%M')
  echo "$week,$now,$now,n/a,n/a,n/a,n/a,n/a,n/a,n/a,error,run.py exit $code before logging; see data/weekly.log" >> data/runs.csv
  "${ADKVOC_NOTIFY:-osascript}" -e "display notification \"run.py failed before logging (exit $code). See data/weekly.log\" with title \"adk-voc: error, week $week\"" >/dev/null 2>&1
fi
exit "$code"
