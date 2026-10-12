from check import parse_verdicts, pass_rate


def test_parse_and_unsure_counts_as_not_supported():
    raw = 'noise\n[{"id":"c1","claim":"x","verdict":"SUPPORTED","reason":"r"},' \
          '{"id":"c2","claim":"y","verdict":"UNSURE","reason":"r"}]\n'
    v = parse_verdicts(raw)
    assert [x["verdict"] for x in v] == ["SUPPORTED", "NOT_SUPPORTED"]
    assert pass_rate(v) == 0.5


def test_empty_is_zero():
    assert pass_rate([]) == 0.0


def test_run_facts_reach_the_checker(tmp_path, monkeypatch):
    import check
    monkeypatch.setattr(check, "DATA", tmp_path)
    seen = []
    check.check_brief("no links", "2026-10-05", ask=lambda p, m: seen.append(p) or "[]",
                      facts="spam removed: 5")
    assert "spam removed: 5" in seen[0]
