from brief import foreign_links
from check import parse_verdicts


def test_claude_runs_with_no_tools(monkeypatch):
    import llm
    seen = {}

    class R:
        returncode, stdout, stderr = 0, "ok", ""
    monkeypatch.setattr(llm.subprocess, "run", lambda cmd, **k: seen.setdefault("cmd", cmd) and R())
    llm.ask_claude("hi", "sonnet")
    assert seen["cmd"][seen["cmd"].index("--tools") + 1] == ""


def test_links_outside_the_run_are_flagged():
    md = "[a](https://github.com/google/adk-go/issues/1) [b](https://evil.example/x)"
    assert foreign_links(md, [{"url": "https://github.com/google/adk-go/issues/1"}]) == ["https://evil.example/x"]


def test_supported_without_evidence_is_not_supported():
    raw = '[{"id":"c1","claim":"x","verdict":"SUPPORTED","reason":"r","evidence":""}]'
    assert parse_verdicts(raw)[0]["verdict"] == "NOT_SUPPORTED"


def test_sections_are_inserted_in_fixed_places():
    from brief import insert_sections
    md = "# T\n## TL;DR\n- a\n## Top 5 themes\nx\n## Method\ny\n"
    out = insert_sections(md, "## Red flags\nRF\n", "## Since last release\nSR\n")
    assert out.index("## Red flags") < out.index("## Top 5") < out.index("## Since last") < out.index("## Method")
