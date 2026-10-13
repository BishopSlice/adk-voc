# ADK issues brief

A weekly, cited ranking of new issues across the Google ADK repos (python, go, java, js, docs).
Every claim links to a public issue. A separate AI checker verifies each brief before it's published.

**Not affiliated with Google.** Read only: this project never posts, comments or labels on ADK repos.

## Briefs
Each week is named by its Monday. The brief publishes the following Monday.

<!-- index:start -->
| Week | Issues | Status | Top theme |
|---|---|---|---|
| [2026-10-05](briefs/2026-10-05.md) | 83 | Published, 98% verified | Sessions, state and memory |
<!-- index:end -->

## What the words mean
- **Verified:** a separate AI checker confirmed the claim against the linked issues. Code recomputed every number and checked every quote word for word.
- **Held:** the brief failed the gate after one revision, so it wasn't published.
- **Red flags:** open issues that report a security problem, data loss, repeated side effects or a disabled safety gate. They are reports, not confirmed findings.

Found a wrong claim? Open an issue in this repo.

## How it works
1. Fetch new issues from the GitHub search API (public data only). Remove spam with fixed rules.
2. Sonnet sorts each issue into 10 fixed themes plus Other. Code computes counts, trends and a pain score.
3. Sonnet picks red flags and writes the brief from the computed numbers. Code renders the red flags and release sections.
4. Opus checks every claim in a separate run and must quote its evidence. Code checks every quote, number and link.
5. Publish only if 95% or more of claims are verified and every code check passes. Otherwise revise once, then hold.

Headless Claude runs with no tools, connectors or settings, because issue text is untrusted.

## Run it yourself
Requires Python 3.11+, git, curl and a logged-in Claude Code CLI (`claude`).
```
python3 -m pip install -r requirements.txt
git config core.hooksPath .githooks
python3 run.py --week 2026-10-05            # writes data/2026-10-05/ (local only)
python3 run.py --week 2026-10-05 --publish  # also commits briefs/2026-10-05.md if the gate passes
./check.sh                                  # lint + offline tests
python3 evals/run.py                        # evals (calls claude -p)
python3 spotcheck.py --week 2026-10-05      # 5 random claims to check by hand
```

## Weekly schedule (macOS)
A launchd job runs `run_weekly.sh` on Monday at 09:00, at login and every hour. It only works when a week is due, so the hourly calls catch up after sleep. Each run ends with a row in `data/runs.csv` (pass, hold or error). Holds and errors show a notification.

macOS blocks background jobs under `~/Documents`, so the job runs from a separate clone:
```
git clone https://github.com/BishopSlice/adk-voc.git ~/adk-voc
sed "s|APP_DIR|$HOME/adk-voc|" ~/adk-voc/launchd/com.vicky.adkvoc.plist > ~/Library/LaunchAgents/com.vicky.adkvoc.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.vicky.adkvoc.plist
launchctl print gui/$(id -u)/com.vicky.adkvoc | grep "last exit"   # expect 0
```
The clone runs `git pull` before each run, so pushed changes reach the next run. Only the latest full week is caught up. Run an older week by hand: `./run_weekly.sh 2026-10-12`.

## Human steps
- **Changed themes, weights or repos?** Runs hold until you approve: `python3 gate.py approve-config --by <name>`.
- **Spot-check disagreed?** Publishing holds until the checker prompt is fixed: `python3 spotcheck.py --week <W> --checker-fixed "<what changed>"`.
