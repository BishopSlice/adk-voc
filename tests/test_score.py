from score import pain_table, trend

ISS = [{"url": f"u{i}", "repo": r, "comments": c, "created": d} for i, (r, c, d) in enumerate([
    ("adk-go", 2, "2026-10-06"), ("adk-js", 0, "2026-10-07"), ("adk-go", 4, "2026-10-08"),
    ("adk-python", 1, "2026-10-06"), ("adk-go", 0, "2026-09-30")])]
LAB = {"u0": "Tools", "u1": "Tools", "u2": "Tools", "u3": "Docs, CI and dev setup", "u4": "Tools"}
W = {"Tools": 1.5, "Docs, CI and dev setup": 1.0}


def test_pain_formula_matches_hand_math():
    rows = pain_table(ISS, LAB, "2026-10-05", W)
    tools = rows[0]
    # 3 issues x 1.5 x 2 repos x (1 + median(2,0,4)=2 / 10) = 10.8
    assert tools["theme"] == "Tools" and tools["pain"] == 10.8
    assert tools["count"] == 3 and tools["prev"] == 1 and tools["repos"] == ["adk-go", "adk-js"]


def test_ranking_is_deterministic_and_ties_break_by_count_then_name():
    lab = {"u0": "B", "u3": "A"}
    rows = pain_table(ISS, lab, "2026-10-05", {"A": 1.0, "B": 1.0})
    assert [r["theme"] for r in rows] == ["B", "A"]  # B: 1x1x1x1.2=1.2 > A: 1.1


def test_trend_tokens():
    assert trend(0, 4) == "new"
    assert trend(3, 13) == "▲ 3 → 13"
    assert trend(4, 2) == "▼ 4 → 2"
    assert trend(8, 15) == "▲ +88%"
    assert trend(6, 5) == "▼ −17%"
    assert trend(9, 9) == "– 0%"
