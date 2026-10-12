import pytest

from fetch import build_query, parse_item, week_bounds, fetch_repo, CountMismatch

ITEM = {"html_url": "https://github.com/google/adk-go/issues/1738", "number": 1738,
        "created_at": "2026-10-06T10:00:00Z", "title": "t", "labels": [{"name": "bug"}],
        "comments": 2, "body": "x" * 1500, "author_association": "NONE",
        "reactions": {"total_count": 0}, "state": "open", "user": {"login": "someone"}}


def test_week_bounds_are_monday_to_sunday():
    assert week_bounds("2026-10-05") == ("2026-10-05", "2026-10-11")
    with pytest.raises(ValueError):
        week_bounds("2026-10-06")  # not a Monday


def test_query():
    assert build_query("adk-go", "2026-10-05", "2026-10-11") == \
        "repo:google/adk-go is:issue created:2026-10-05..2026-10-11"


def test_parse_keeps_fields_truncates_body_and_drops_username():
    x = parse_item("adk-go", ITEM)
    assert x["url"] == ITEM["html_url"] and x["n"] == 1738 and x["created"] == "2026-10-06"
    assert x["labels"] == ["bug"] and x["comments"] == 2 and len(x["body"]) == 1000
    assert "someone" not in str(x)


def test_parse_handles_missing_body():
    assert parse_item("adk-go", {**ITEM, "body": None})["body"] == ""


def test_paging_and_count_check():
    pages = {1: {"total_count": 101, "items": [ITEM] * 100}, 2: {"total_count": 101, "items": [ITEM]}}
    got = fetch_repo("adk-go", "2026-10-05", "2026-10-11", get=lambda q, p: pages[p])
    assert len(got) == 101


def test_count_mismatch_raises():
    with pytest.raises(CountMismatch):
        fetch_repo("adk-go", "a", "b", get=lambda q, p: {"total_count": 5, "items": [ITEM] * 3})
