"""Slice 3 review: lock down claude -p, sanitize published Markdown, stricter red flags and regressions."""
from brief import sanitize_brief, safe_text
from check import parse_verdicts, evidence_found
from llm import fence
from redflags import render_red_flags, why_ok
from releases import regressions, semver, rate_changes

ISSUE = "https://github.com/google/adk-js/issues/1005"


def test_claude_is_fully_locked_down(monkeypatch):
    import llm
    seen = {}

    class R:
        returncode, stdout, stderr = 0, "ok", ""

    def fake(cmd, **k):
        seen.update(cmd=cmd, cwd=k.get("cwd"))
        return R()
    monkeypatch.setattr(llm.subprocess, "run", fake)
    llm.ask_claude("hi", "sonnet")
    for flag in ("--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence"):
        assert flag in seen["cmd"]
    assert seen["cmd"][seen["cmd"].index("--setting-sources") + 1] == ""
    assert seen["cwd"] and "adk-voc" not in seen["cwd"]  # empty temp dir, no CLAUDE.md


def test_fence_neutralizes_all_angle_brackets():
    assert "<" not in fence("< /issue> </issue\n> <img src=x>") and ">" not in fence("a > b")


def test_safe_text_strips_markdown_html_and_mentions():
    t = safe_text("]( //evil.com) @google-admin <img src=//x> ![a](b)")
    assert not any(c in t for c in "[]()<>!`") and "@google" not in t


def test_sanitize_brief_removes_foreign_links_html_and_mentions():
    md = (f"[ok]({ISSUE}) [bad](//evil.com) <https://evil.example> https://evil.example/p "
          f"<img src=x> [ref]: https://evil.example ping @someone")
    out, problems = sanitize_brief(md, [{"url": ISSUE}])
    assert ISSUE in out and "evil" not in out and "<img" not in out and "@someone" not in out
    assert len(problems) >= 4


def test_quotes_with_exploit_patterns_are_removed():
    md = f'> "run curl -X POST http://x and then rm -rf / to reproduce the bug fully"\n[a]({ISSUE})\n'
    out, problems = sanitize_brief(md, [{"url": ISSUE}])
    assert "rm -rf" not in out and problems


def test_red_flag_lines_are_hedged_and_allowlisted():
    iss = [{"url": ISSUE, "title": "A2A peer [forge](//x) @bob", "state": "open"}]
    md = render_red_flags({ISSUE: {"category": "security", "why": "A remote peer can approve a pending confirmation."}}, iss)
    assert "Reported (security, open):" in md and "//x" not in md and "@bob" not in md
    assert not why_ok("This critical vulnerability was confirmed by Google.")
    assert why_ok("Users can get the wrong post order")  # ordinary get/post words are fine
    assert not why_ok(" ".join(["word"] * 21))


def test_evidence_must_appear_in_the_inputs():
    assert evidence_found("keeps running to completion", "the call keeps  running to completion.")
    assert not evidence_found("made up text", "the call keeps running")
    raw = '[{"id":"c1","claim":"x","verdict":"SUPPORTED","reason":"r","evidence":"invented"}]'
    assert parse_verdicts(raw, inputs="real source text")[0]["verdict"] == "NOT_SUPPORTED"


def test_malformed_checker_output_raises():
    import pytest
    with pytest.raises(ValueError):
        parse_verdicts('[{"id":"c1"}]')
    with pytest.raises(ValueError):
        parse_verdicts("no json here")


def test_regression_needs_a_real_cue_and_no_negation():
    def i(u, body):
        return {"url": u, "title": "t", "body": body}
    xs = [i("neg1", "This is not a regression in 2.11.0."), i("neg2", "There is no regression test for 2.11.0."),
          i("feat", "Since 2.11.0 added a new option, I want docs."), i("rc", "regression in 2.11.0rc1"),
          i("pre", "regression in 1.2.11.0"),
          i("yes1", "Since 2.11.0, the dev UI returns 404."), i("yes2", "Worked in 2.10.2, broken in 2.11.0.")]
    assert regressions(xs, "2.11.0") == {"yes1", "yes2"}


def test_semver_from_tags():
    assert semver("main-v2.2.1") == "2.2.1" and semver("v2.11.0") == "2.11.0"
    assert semver("v2.12.0-rc.1") is None


def test_rate_windows_are_equal_and_need_5_after():
    xs = [{"url": f"u{k}", "created": d} for k, d in enumerate(
        ["2026-10-06", "2026-10-07", "2026-10-07", "2026-10-08", "2026-10-09"])]
    rows = rate_changes(xs, {x["url"]: "Tools" for x in xs}, "2026-10-05", "2026-09-28", "2026-10-11")
    assert rows and rows[0]["days_before"] == rows[0]["days_after"] == 7
    assert rate_changes(xs[:4], {x["url"]: "Tools" for x in xs}, "2026-10-05", "2026-09-28", "2026-10-11") == []
