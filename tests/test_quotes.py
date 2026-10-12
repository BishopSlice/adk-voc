from quotes import quote_failures, table_failures

BODY = "When a client disconnects, the underlying model call keeps running to completion."
ISS = [{"url": "https://github.com/google/adk-java/issues/1618", "body": BODY}]


def md(q):
    return f'> "{q}"\n[java#1618: x](https://github.com/google/adk-java/issues/1618)\n'


def test_exact_quote_passes_and_whitespace_is_normalized():
    assert quote_failures(md("the underlying model call keeps  running to completion."), ISS) == []


def test_one_changed_word_fails():
    f = quote_failures(md("the underlying model call keeps going to completion."), ISS)
    assert len(f) == 1 and f[0]["verdict"] == "NOT_SUPPORTED"


def test_quote_without_a_source_link_fails():
    assert quote_failures('> "keeps running"\n\nno link\n', ISS)


def test_pain_and_trend_columns_are_recomputed():
    table = "| 1 | Tools | 14 | ▲ +40% | 9.0 |\n| 2 | Docs, CI and dev setup | 3 | new | 1.0 |\n"
    rows = [{"theme": "Tools", "count": 14, "trend": "▲ +40%", "pain": 9.5},
            {"theme": "Docs, CI and dev setup", "count": 3, "trend": "▲ 1 → 3", "pain": 1.0}]
    f = table_failures(table, rows)
    assert len(f) == 2 and "9.5" in f[0]["reason"] and "1 → 3" in f[1]["reason"]


def test_link_may_follow_a_blank_line():
    q = '> "the underlying model call keeps running to completion."\n\n[java#1618: x](https://github.com/google/adk-java/issues/1618)\n'
    assert quote_failures(q, ISS) == []


def test_table_must_have_the_top_rows_in_rank_order():
    rows = [{"theme": "A", "count": 2, "trend": "new", "pain": 2.0},
            {"theme": "B", "count": 1, "trend": "new", "pain": 1.0}]
    assert table_failures("no table at all\n", rows)  # format drift fails loudly
    swapped = "| 1 | B | 1 | new | 1.0 |\n| 2 | A | 2 | new | 2.0 |\n"
    assert any("rank" in f["reason"] for f in table_failures(swapped, rows))


def test_curly_and_too_short_quotes():
    link = "[java#1618: x](https://github.com/google/adk-java/issues/1618)\n"
    assert quote_failures("> \u201cthe underlying model call keeps running\u201d\n" + link, ISS) == []
    assert quote_failures('> "keeps running"\n' + link, ISS)  # under 20 characters
