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
python3 run.py --week "$week" --publish >> data/weekly.log 2>&1
