from quotes import quote_failures, count_failures

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


def test_table_counts_are_recomputed():
    table = "| # | Theme | Issues | vs last week | Pain |\n|---|---|---|---|---|\n" \
            "| 1 | Tools | 14 | ▲ +40% | 9.0 |\n| 2 | Docs, CI and dev setup | 3 | new | 1.0 |\n"
    f = count_failures(table, {"Tools": 13, "Docs, CI and dev setup": 3})
    assert len(f) == 1 and "13" in f[0]["reason"]
