# Lessons
One line per real failure: date, what broke, the rule that prevents it.
- 2026-10-12: a camelCase regex under re.I matched any two letters, so spam passed as technical. Rule: never mix case-sensitive patterns into a re.I pattern.
- 2026-10-12: count goldens checked against live data drifted (orchestration 13 → 14 as late issues arrived). Rule: evals that check numbers use a frozen fixture, never live data.
- 2026-10-12: the checker marked process claims ("5 spam removed") unsupported because it never saw the run. Rule: pass the pipeline's run facts to the checker.
- 2026-10-12: the TL;DR length check counted hidden link URLs. Rule: measure what the reader sees.
- 2026-10-12: a gold label contradicted the theme definitions (c7 artifacts). Rule: gold labels and the theme definitions must be reconciled before tuning.
- 2026-10-12: the checker failed every pain number because it never saw comments, weights or the formula. Rule: numbers computed in code are verified in code; give the LLM checker every input a claim depends on.
- 2026-10-12: Sonnet truncated a quote and added a period ("fires again." vs "fires again when the rest arrive."). Rule: the exact-quote check runs in code on every brief; never trust the maker's quotes.
- 2026-10-13: rate lines like "0.0 → 0.6 per day" had no windows, so nobody could verify them. Rule: every number in the brief shows its inputs (counts and dates).
- 2026-10-13: a fallback string ("Reported as a severe issue") was itself an unsupported claim. Rule: fallbacks state only facts the source shows, like the title.
- 2026-10-13: Discover notes said v2.11.0 was released 10-01; the releases API says 10-02. Rule: dates come from the API, never from notes.
- 2026-10-13: `claude -p --tools ""` still exposed MCP connectors (Google Drive search, read, create). Rule: headless runs on untrusted text use the full LOCKDOWN flags from an empty temp dir, and a test asserts them.
- 2026-10-13: contract evidence came from a brief generated before the final fixes. Rule: delete outputs and rerun from clean before quoting numbers in a contract.
- 2026-10-13: an edit that rewrote "from test X to end of file" deleted a later test. Rule: compare test counts before and after editing test files.
- 2026-10-13: gh was logged in but git used SSH with no key, so the first push failed. Rule: the repo remote is HTTPS with a repo-local gh credential helper.
- 2026-10-13: the launchd wrapper's PATH put Homebrew python3 (no packages) first, so every scheduled run would crash on import yaml; tests passed because they used the shell's PATH. Rule: test the scheduled command with the scheduler's environment, not yours.
- 2026-10-13: the TL;DR check stripped link URLs but counted [ ] brackets, so a 113-char line measured 123 and a 100%-verified brief held. Rule: compute 'visible' exactly as Markdown renders it.
- 2026-10-13: launchd could not run a script under ~/Documents (exit 126, macOS privacy block), so the job failed before any logging. Rule: scheduled jobs run from a copy outside protected folders; check launchctl's last exit code right after install.
- 2026-10-13: `git commit -a` failed with 'invalid object' because the pre-commit hook's tests ran git in temp repos with the hook's GIT_INDEX_FILE. Rule: tests that shell out to git clear GIT_* env vars (conftest).
