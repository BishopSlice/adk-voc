from brief import split_code_sections, revise

MD = ("# T\n## TL;DR\n- a\n## Red flags\n- rf\n\n## Top 5 themes\n| 1 | A | 1 | new | 1.0 |\n"
      "## Since last release\n- sr\n\n## Method\nm\n")


def test_code_sections_are_lifted_out_and_restored():
    body, rf, since = split_code_sections(MD)
    assert "## Red flags" not in body and "## Since last release" not in body
    assert rf.startswith("## Red flags") and since.startswith("## Since last release")


def test_revise_sends_only_maker_text_and_failures_then_restores_sections():
    seen = []

    def fake(prompt, model):
        seen.append(prompt)
        return "# T\n## TL;DR\n- a shorter\n## Top 5 themes\n| 1 | A | 1 | new | 1.0 |\n## Method\nm\n"
    out = revise(MD, [{"claim": "TL;DR too long", "reason": "6 lines"}], ask=fake)
    assert "## Red flags" not in seen[0] and "TL;DR too long" in seen[0]
    assert "- rf" in out and "- sr" in out and "a shorter" in out
