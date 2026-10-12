# adk-voc

A weekly, cited ranking of new Google ADK issues. Sonnet writes the brief and a separate Opus run checks every claim. A brief is published only if 95% or more of its claims are verified.

## Requirements
- Python 3.11+, git, curl
- Claude Code CLI (`claude`), logged in

## Install
```
cd app
python3 -m pip install -r requirements.txt
git config core.hooksPath .githooks
```

## Run
```
python3 run.py --week 2026-10-05
```
Outputs go to `data/2026-10-05/`: `issues.json`, `brief.md` and `check.json`.

## Test
```
./check.sh              # lint + offline tests
python3 evals/run.py    # evals (uses claude -p)
```
