from spam import is_spam


def i(title, labels=()):
    return {"title": title, "labels": list(labels)}


def test_spam_rules():
    assert is_spam(i("anything", ["spam"]))
    assert is_spam(i("   "))
    assert is_spam(i("https://example.com/x"))
    assert is_spam(i("hello there"))


def test_short_technical_titles_stay():
    assert not is_spam(i("nil pointer in runner"))
    assert not is_spam(i("LiteLlm crash"))
    assert not is_spam(i("run_async hangs"))
