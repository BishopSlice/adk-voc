from brief import tldr_ok

def test_tldr_limits():
    good = "# T\n\n## TL;DR\n- a\n- b\n\n## Next\n"
    assert tldr_ok(good)
    assert not tldr_ok("# T\n\n## TL;DR\n" + "- x\n" * 6 + "\n## Next\n")
    assert not tldr_ok("# T\n\n## Next\n")


def test_tldr_counts_visible_text_not_urls():
    line = "- Tools: 5 issues, e.g. [py#1: short](https://github.com/google/adk-python/issues/" + "1" * 120 + ")"
    assert tldr_ok("## TL;DR\n" + line + "\n\n## Next\n")
