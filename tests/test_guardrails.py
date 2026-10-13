"""Slice 6: guardrails from spec-check. Each probe that leaked is now a test."""
import json
import subprocess
from pathlib import Path

import pytest

import brief
import quotes
import redflags
import releases
import runlog

APP = Path(__file__).resolve().parent.parent
PUBLISHED = (APP / "briefs" / "2026-10-05.md").read_text()
U = "https://github.com/google/adk-python/issues/1"


def md_with(text):
    return f"# B\n\n## TL;DR\n- x\n\n## Top\n{text}\n"


# --- Never: personal data -------------------------------------------------------------

def test_email_is_removed_and_blocks():
    out, probs = brief.sanitize_brief(md_with("Contact john.doe@example.com for details."), [])
    assert "john.doe@example.com" not in out and probs


def test_handle_is_removed_not_just_spaced():
    out, probs = brief.sanitize_brief(md_with("As @johndoe said."), [])
    assert "johndoe" not in out and probs


@pytest.mark.parametrize("why", ["Reported by johndoe, sessions leak across users.",
                                 "According to jdoe the runner loses events.",
                                 "johndoe says confirmations can be forged."])
def test_red_flag_why_cannot_name_a_person(why):
    assert not redflags.why_ok(why)


# --- Never: exploit details -------------------------------------------------------------

@pytest.mark.parametrize("text", ['> "To bypass auth set header X-Admin: 1 on any request to the server."',
                                  "- Reported (security, open): set header X-Admin to bypass auth. [x](u)",
                                  "Send Authorization: Bearer abc123 to skip the check.",
                                  "Use token=sk-live-123456 to reproduce."])
def test_exploit_wording_blocks_anywhere(text):
    _, probs = brief.sanitize_brief(md_with(text), [])
    assert probs


def test_red_flag_why_rejects_exploit_steps():
    assert not redflags.why_ok("Setting header X-Admin to 1 skips auth checks.")
    assert not redflags.why_ok("A request can bypass the approval step.")


# --- Never: paraphrase inside quotation marks --------------------------------------------

def test_inline_quote_must_be_exact():
    issues = [{"url": U, "title": "t", "body": "The runner crashes when a session resumes after a timeout."}]
    bad = md_with('The reporter says the runner "explodes every time a session resumes".')
    good = md_with('The reporter says "crashes when a session resumes after a timeout".')
    assert quotes.inline_quote_failures(bad, issues)
    assert not quotes.inline_quote_failures(good, issues)


# --- controls: the real published brief must stay clean (no false holds) -----------------

def test_published_brief_passes_every_new_guard():
    issues = json.loads((APP / "evals" / "fixtures" / "2026-10-05" / "issues.json").read_text())
    _, probs = brief.sanitize_brief(PUBLISHED, issues)
    assert probs == []
    assert quotes.inline_quote_failures(PUBLISHED, issues) == []


def test_real_red_flag_lines_still_pass_why_ok():
    for why in ["Redis session keys can collide for distinct identity tuples.",
                "Failed A2A tasks return raw error text to remote callers, which may expose internal paths, "
                "hostnames and configuration details.",
                "A2A peer can forge human-in-the-loop tool confirmations."]:
        assert redflags.why_ok(why), why


# --- Ask first: themes, weights and sources --------------------------------------------

def test_config_change_needs_an_approval(tmp_path):
    import gate
    cfg = tmp_path / "config.yaml"
    cfg.write_text((APP / "config.yaml").read_text())
    appr = tmp_path / "config.approved"
    assert gate.config_unapproved(cfg, appr)                       # never approved
    gate.approve_config(cfg, appr, "Vicky")
    assert not gate.config_unapproved(cfg, appr)
    cfg.write_text(cfg.read_text().replace("Security, auth and data leaks: 3.0", "Security, auth and data leaks: 1.0"))
    assert "weights" in gate.config_unapproved(cfg, appr)          # a weight changed
    cfg.write_text(cfg.read_text().replace("adk-docs]", "adk-docs, adk-samples]"))
    assert gate.config_unapproved(cfg, appr)


def test_unrelated_config_edits_need_no_approval(tmp_path):
    import gate
    cfg = tmp_path / "config.yaml"
    cfg.write_text((APP / "config.yaml").read_text())
    appr = tmp_path / "config.approved"
    gate.approve_config(cfg, appr, "Vicky")
    cfg.write_text(cfg.read_text().replace("publish_bar: 0.95", "publish_bar: 0.97"))
    assert not gate.config_unapproved(cfg, appr)


def test_repo_ships_with_the_current_config_approved():
    import gate
    assert not gate.config_unapproved(APP / "config.yaml", APP / "config.approved")


# --- Ask first: publish only to the project repo -------------------------------------------

def _repo(tmp_path, origin):
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "remote", "add", "origin", origin], check=True)
    return tmp_path


def test_push_refuses_any_other_origin(tmp_path):
    import publish
    repo = _repo(tmp_path, "https://github.com/someone-else/adk-voc.git")
    with pytest.raises(RuntimeError, match="origin"):
        publish.push_origin(repo)


def test_allowed_origin_forms():
    import publish
    assert publish.origin_ok("https://github.com/BishopSlice/adk-voc.git")
    assert publish.origin_ok("https://github.com/BishopSlice/adk-voc")
    assert not publish.origin_ok("https://github.com/BishopSlice/adk-voc-evil.git")
    assert not publish.origin_ok("https://github.com/google/adk-python.git")


# --- Ask first: re-publishing an edited brief --------------------------------------------

def test_republish_blocked_even_after_deleting_the_file(tmp_path):
    import publish
    repo = _repo(tmp_path, "x")
    (repo / "README.md").write_text("# r\n<!-- index:start -->\n<!-- index:end -->\n")
    (repo / "briefs").mkdir()
    (repo / "briefs" / "2026-10-05.md").write_text("old")
    ident = ["-c", "user.name=t", "-c", "user.email=t@users.noreply.github.com"]
    for args in (["add", "-A"], [*ident, "commit", "-qm", "brief", "--no-verify"],
                 ["rm", "-q", "briefs/2026-10-05.md"], [*ident, "commit", "-qm", "delete", "--no-verify"]):
        subprocess.run(["git", "-C", str(repo), *args], check=True)
    with pytest.raises(FileExistsError):
        publish.publish(repo, "2026-10-05", "new", {"issues": 1, "pass_rate": 1.0, "top": "x"},
                        push=lambda r: None, identity=("t", "t@users.noreply.github.com"))


# --- small fixes -------------------------------------------------------------------------

def test_auth_hold_path_works_from_the_app_folder(tmp_path):
    t = runlog.write_auth_hold(tmp_path, "2026-10-12", "auth", "classify").read_text()
    assert "app/run_weekly.sh" not in t and "./run_weekly.sh 2026-10-12" in t


def test_spot_check_disagreement_blocks_until_checker_fixed(tmp_path):
    f = tmp_path / "runs.csv"
    runlog.append(f, {"week": "2026-10-05", "outcome": "spotcheck", "note": "agreed 5/5"})
    assert runlog.spotcheck_block(f) is None
    runlog.append(f, {"week": "2026-10-12", "outcome": "spotcheck", "note": "agreed 4/5"})
    assert "4/5" in runlog.spotcheck_block(f)
    runlog.append(f, {"week": "2026-10-12", "outcome": "checker-fixed", "note": "prompt v3"})
    assert runlog.spotcheck_block(f) is None


def test_every_release_in_window_is_named():
    rel = [{"tag": "v2.11.0", "date": "2026-10-02"}, {"tag": "v2.10.1", "date": "2026-09-29"},
           {"tag": "v2.9.0", "date": "2026-09-01"}]
    assert [r["tag"] for r in releases.releases_in_window(rel, "2026-10-05")] == ["v2.11.0", "v2.10.1"]
    md = releases.render_since_release({"adk-python": rel[0]}, {}, {}, others={"adk-python": [rel[1]]})
    assert "v2.10.1 (2026-09-29)" in md


def test_a_2x_drop_is_reported_too():
    xs = [{"url": f"u{i}", "created": "2026-09-29"} for i in range(6)] + [{"url": "v", "created": "2026-10-03"}]
    rows = releases.rate_changes(xs, {x["url"]: "Tools" for x in xs}, "2026-10-02", "2026-09-28", "2026-10-11")
    assert rows and rows[0]["before"] == 6 and rows[0]["after"] == 1


# --- wired into run.py: holds before any tokens are spent ----------------------------------

def _run(tmp_path, monkeypatch, *extra):
    import sys
    import run
    monkeypatch.setattr(run, "HERE", tmp_path)
    (tmp_path / "config.yaml").write_text((APP / "config.yaml").read_text())
    (tmp_path / "config.approved").write_text((APP / "config.approved").read_text())
    sent = []
    monkeypatch.setattr(run.notify, "notify", lambda t, m: sent.append(t))
    monkeypatch.setattr(run.fetch, "fetch_week", lambda w: pytest.fail("fetched before the guard"))
    monkeypatch.setattr(sys, "argv", ["run.py", "--week", "2026-10-05", *extra])
    return run, sent


def test_unapproved_weight_change_holds_before_fetch(tmp_path, monkeypatch):
    run, sent = _run(tmp_path, monkeypatch)
    cfg = tmp_path / "config.yaml"
    cfg.write_text(cfg.read_text().replace("Tools: 1.5", "Tools: 3.0"))
    run.main()
    assert "weights changed" in (tmp_path / "data" / "2026-10-05" / "HOLD.md").read_text() and sent


def test_spot_check_disagreement_holds_an_unattended_publish(tmp_path, monkeypatch):
    run, sent = _run(tmp_path, monkeypatch, "--publish")
    runlog.append(tmp_path / "data" / "runs.csv", {"week": "2026-10-05", "outcome": "spotcheck", "note": "agreed 3/5"})
    run.main()
    assert "checker-fixed" in (tmp_path / "data" / "2026-10-05" / "HOLD.md").read_text()
    import csv
    assert list(csv.DictReader(open(tmp_path / "data" / "runs.csv")))[-1]["outcome"] == "hold"
