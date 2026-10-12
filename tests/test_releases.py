from releases import regressions, recent_release, rate_changes, render_since_release


def i(url, title, body="", created="2026-10-06"):
    return {"url": url, "title": title, "body": body, "created": created, "repo": "adk-python"}


def test_regression_phrases_match():
    xs = [i("a", "x hangs (regression in 2.11.0)"), i("b", "y", "Since 2.11.0, the dev UI 404s"),
          i("c", "z", "After upgrading to v2.11.0 the runner fails")]
    assert regressions(xs, "2.11.0") == {"a", "b", "c"}


def test_version_mention_alone_is_not_a_regression():
    xs = [i("a", "Exporter drops span status (2.11.0)"), i("b", "since 2.11.01 something")]
    assert regressions(xs, "2.11.0") == set()


def test_recent_release_within_two_weeks():
    rel = [{"tag": "v2.11.0", "date": "2026-10-01"}, {"tag": "v2.10.0", "date": "2026-09-10"}]
    assert recent_release(rel, "2026-10-05")["tag"] == "v2.11.0"
    assert recent_release([{"tag": "v1", "date": "2026-09-01"}], "2026-10-05") is None


def test_rate_change_needs_2x_and_enough_data():
    xs = [i(f"o{k}", "t", created=d) for k, d in enumerate(
        ["2026-09-29", "2026-10-02", "2026-10-03", "2026-10-04", "2026-10-05", "2026-10-06", "2026-10-07"])]
    labels = {x["url"]: "Multi-agent orchestration" for x in xs}
    # before Oct 1: 1 issue over 3 days (0.33/day); from Oct 1: 6 over 11 days (0.55/day) -> 1.6x, no flag
    assert rate_changes(xs, labels, "2026-10-01", "2026-09-28", "2026-10-11") == []


def test_render_no_release_is_one_line():
    md = render_since_release({"adk-go": None}, {}, {})
    assert md.strip().endswith("adk-go: no release in this window.")
