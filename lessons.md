# Lessons
One line per real failure: date, what broke, the rule that prevents it.
- 2026-10-12: a camelCase regex under re.I matched any two letters, so spam passed as technical. Rule: never mix case-sensitive patterns into a re.I pattern.
