# Lessons
One line per real failure: date, what broke, the rule that prevents it.
- 2026-10-12: a camelCase regex under re.I matched any two letters, so spam passed as technical. Rule: never mix case-sensitive patterns into a re.I pattern.
- 2026-10-12: count goldens checked against live data drifted (orchestration 13 → 14 as late issues arrived). Rule: evals that check numbers use a frozen fixture, never live data.
- 2026-10-12: the checker marked process claims ("5 spam removed") unsupported because it never saw the run. Rule: pass the pipeline's run facts to the checker.
- 2026-10-12: the TL;DR length check counted hidden link URLs. Rule: measure what the reader sees.
- 2026-10-12: a gold label contradicted the theme definitions (c7 artifacts). Rule: gold labels and the theme definitions must be reconciled before tuning.
- 2026-10-12: the checker failed every pain number because it never saw comments, weights or the formula. Rule: numbers computed in code are verified in code; give the LLM checker every input a claim depends on.
- 2026-10-12: Sonnet truncated a quote and added a period ("fires again." vs "fires again when the rest arrive."). Rule: the exact-quote check runs in code on every brief; never trust the maker's quotes.
