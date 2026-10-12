from brief import theme_stats, tldr_ok

ISS = [{"url": f"u{i}", "repo": r, "comments": c, "created": d}
       for i, (r, c, d) in enumerate([("adk-go", 2, "2026-10-06"), ("adk-js", 0, "2026-10-07"),
                                      ("adk-go", 1, "2026-09-30")])]
LAB = {"u0": "Tools", "u1": "Tools", "u2": "Tools"}


def test_stats_split_by_week():
    s = theme_stats(ISS, LAB, "2026-10-05")
    assert s["Tools"]["count"] == 2 and s["Tools"]["prev"] == 1
    assert s["Tools"]["repos"] == ["adk-go", "adk-js"]


def test_tldr_limits():
    good = "# T\n\n## TL;DR\n- a\n- b\n\n## Next\n"
    assert tldr_ok(good)
    assert not tldr_ok("# T\n\n## TL;DR\n" + "- x\n" * 6 + "\n## Next\n")
    assert not tldr_ok("# T\n\n## Next\n")


def test_tldr_counts_visible_text_not_urls():
    line = "- Tools: 5 issues, e.g. [py#1: short](https://github.com/google/adk-python/issues/" + "1" * 120 + ")"
    assert tldr_ok("## TL;DR\n" + line + "\n\n## Next\n")
