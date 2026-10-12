"""AC10: decide publish or hold. Pass rate uses the LLM checker only; code failures are hard blockers."""
from pathlib import Path

PUBLISH_BAR = 0.95  # floor
MIN_CLAIMS = 10


def effective_bar(env: str | None, configured: float) -> float:
    """The bar can be raised (forced-fail tests) but never lowered below 95%."""
    return max(PUBLISH_BAR, configured, float(env) if env else 0.0)


def decide(llm_verdicts: list[dict], code_failures: list[dict], tldr_ok: bool, bar: float = PUBLISH_BAR,
           links: int = 0) -> dict:
    n = len(llm_verdicts)
    need = max(MIN_CLAIMS, links)  # every linked issue implies at least one claim to check
    rate = sum(v["verdict"] == "SUPPORTED" for v in llm_verdicts) / n if n else 0.0
    reasons = []
    if n < need:
        reasons.append(f"only {n} claims checked (need {need})")
    if rate < bar:
        reasons.append(f"{rate:.0%} of claims verified (need {bar:.0%})")
    if code_failures:
        reasons.append(f"{len(code_failures)} code check failures (quotes, numbers, links or sanitizer)")
    if not tldr_ok:
        reasons.append("TL;DR is over 5 lines or a line is 120 characters or more")
    return {"publish": not reasons, "pass_rate": rate, "claims": n, "reasons": reasons}


def write_hold(d: Path, week: str, decision: dict, failures: list[dict]) -> Path:
    rows = "\n".join(f"| {f.get('claim', '')} | {f['verdict']} | {f.get('reason', '')} |" for f in failures)
    text = (f"# HOLD: week of {week}\n**Not published.** {decision['pass_rate']:.0%} of "
            f"{decision['claims']} claims verified. One automatic revision was tried.\n\n"
            "## Why\n" + "\n".join(f"- {r}" for r in decision["reasons"]) +
            "\n\n## Failed claims\n| Claim | Verdict | Reason |\n|---|---|---|\n" + rows +
            f"\n\n## How to fix\n1. Edit `data/{week}/brief.md` by hand.\n"
            f"2. Run `python3 run.py --week {week} --skip-fetch --recheck --publish`.\n")
    p = Path(d) / "HOLD.md"
    p.write_text(text)
    return p
