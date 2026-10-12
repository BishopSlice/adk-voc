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
