# Brief judge rubric (Opus judge, Sonnet maker)
Score each criterion from 1 to 5. A brief passes when every criterion scores 4 or more.

| Criterion | 5 | 3 | 1 |
|---|---|---|---|
| Scannable | TL;DR of 5 lines or fewer gives the top 3 problems and the red flags | TL;DR is present but buries the red flags or runs over 5 lines | No TL;DR, or it's prose |
| Cited | Every claim has an issue link, and each quote is followed by its source | 1 or 2 claims lack a link | Many claims are unlinked |
| Calm tone | Facts only, no adjectives like "alarming", neutral red flags | Some loaded words | Hype, emojis or opinions |
| No causal leaps | Changes stated as week over week, never "because of the release" without evidence | One implied cause | Several unsupported causes |
| Format tokens | Arrows, link titles, section order and dates match `prompts/style.md` | 1 or 2 deviations | Ignores the style |

Calibration: Vicky grades the first 10 briefs or drafts by hand. If Vicky and the judge agree on fewer than 8, fix the rubric.
Example 5 brief: `03-design/prototype/briefs/2026-10-05.md`.
