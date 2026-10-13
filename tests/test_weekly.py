"""Slice 5: run log (AC12), catch-up, notifications and auth/limit holds (AC11)."""
import csv
import datetime as dt
import subprocess
import sys
from pathlib import Path

import pytest

import runlog
from llm import ClaudeError

APP = Path(__file__).resolve().parent.parent


def rows(p):
    return list(csv.DictReader(open(p)))


# --- AC12 run log ---------------------------------------------------------------

def test_row_written_with_every_spec_column(tmp_path):
    f = tmp_path / "runs.csv"
    runlog.append(f, {"week": "2026-10-05", "outcome": "pass", "fetched": 150})
    runlog.append(f, {"week": "2026-10-12", "outcome": "hold"})
    r = rows(f)
    assert list(r[0]) == runlog.COLUMNS
    assert {"week", "run_start", "run_end", "fetched", "spam", "claims", "pass_rate", "retries",
            "tokens", "other_share", "outcome"} <= set(runlog.COLUMNS)
    assert r[0]["fetched"] == "150" and r[1]["outcome"] == "hold" and r[1]["claims"] == "n/a"


def test_unknown_column_is_a_bug_not_silently_dropped(tmp_path):
    with pytest.raises(KeyError):
        runlog.append(tmp_path / "runs.csv", {"week": "w", "outcome": "pass", "typo": 1})


def test_other_share_and_drift_flag():
    labels = {f"u{i}": ("Other" if i < 2 else "Tools") for i in range(10)}
    assert runlog.other_share(labels, [f"u{i}" for i in range(10)]) == 0.2
    assert runlog.other_share(labels, []) == 0.0
    assert runlog.drift(0.16, 0.15) and not runlog.drift(0.15, 0.15)


# --- AC11 schedule: which week is due ---------------------------------------------

MON = dt.datetime(2026, 10, 19, 9, 0)  # the run for the week of 2026-10-12


def test_due_week_is_last_full_week_after_monday_0900(tmp_path):
    f = tmp_path / "runs.csv"
    assert runlog.due_week(MON, f) == "2026-10-12"
    assert runlog.due_week(MON - dt.timedelta(minutes=1), f) == "2026-10-05"   # before 09:00
    assert runlog.due_week(dt.datetime(2026, 10, 22, 8), f) == "2026-10-12"   # caught up Thursday after sleep


def test_week_already_passed_or_held_is_not_rerun(tmp_path):
    f = tmp_path / "runs.csv"
    runlog.append(f, {"week": "2026-10-12", "outcome": "hold"})
    assert runlog.due_week(MON, f) is None  # a hold waits for a human; no hourly token burn


def test_errors_retry_at_most_three_times(tmp_path):
    f = tmp_path / "runs.csv"
    for _ in range(2):
        runlog.append(f, {"week": "2026-10-12", "outcome": "error"})
    assert runlog.due_week(MON, f) == "2026-10-12"
    runlog.append(f, {"week": "2026-10-12", "outcome": "error"})
    assert runlog.due_week(MON, f) is None


def test_spotcheck_rows_do_not_count_as_runs(tmp_path):
    f = tmp_path / "runs.csv"
    runlog.append(f, {"week": "2026-10-12", "outcome": "spotcheck", "note": "agreed 5/5"})
    assert runlog.due_week(MON, f) == "2026-10-12"


def test_deadline_is_wednesday_2359_of_the_run_week():
    assert runlog.deadline("2026-10-12") == "Wednesday 2026-10-21, 23:59"


# --- auth and usage-limit errors ---------------------------------------------------

@pytest.mark.parametrize("msg,kind", [
    ("Invalid API key · Please run /login", "auth"),
    ("OAuth token has expired. Please run claude login", "auth"),
    ("Claude AI usage limit reached|1760000000", "limit"),
    ("5-hour limit reached ∙ resets 2pm", "limit"),
    ("connection reset by peer", None),
])
def test_error_kind(msg, kind):
    assert runlog.error_kind(ClaudeError(msg)) == kind


def test_auth_hold_names_the_fix_and_deadline(tmp_path):
    p = runlog.write_auth_hold(tmp_path, "2026-10-12", "auth", "classify")
    t = p.read_text()
    assert "Not published" in t and "claude login" in t and "run_weekly.sh 2026-10-12" in t
    assert "Wednesday 2026-10-21, 23:59" in t and "classify" in t


# --- notify ------------------------------------------------------------------------

def test_notify_uses_osascript_and_escapes_quotes(monkeypatch):
    import notify
    calls = []
    monkeypatch.setattr(notify.subprocess, "run", lambda cmd, **k: calls.append(cmd))
    notify.notify('HOLD "W"', 'bad \\ "thing"')
    cmd = calls[0]
    assert cmd[0] == "osascript" and '\\"thing\\"' in cmd[2] and 'with title "adk-voc: HOLD \\"W\\""' in cmd[2]


def test_notify_never_raises(monkeypatch):
    import notify

    def boom(*a, **k):
        raise FileNotFoundError("osascript")
    monkeypatch.setattr(notify.subprocess, "run", boom)
    notify.notify("t", "m")  # a missing notifier must not crash the run log


# --- run.py end to end with a fake Claude --------------------------------------------

def _fake_week(tmp_path, monkeypatch, ask_error=None):
    import run
    monkeypatch.setattr(run, "HERE", tmp_path)
    (tmp_path / "config.yaml").write_text((APP / "config.yaml").read_text())
    (tmp_path / "config.approved").write_text((APP / "config.approved").read_text())
    d = tmp_path / "data" / "2026-10-05"
    d.mkdir(parents=True)
    (d / "issues.json").write_text("[]")
    sent = []
    monkeypatch.setattr(run.notify, "notify", lambda t, m: sent.append((t, m)))

    def fail(*a, **k):
        raise ask_error
    monkeypatch.setattr(run.classify, "classify", fail)
    monkeypatch.setattr(sys, "argv", ["run.py", "--week", "2026-10-05", "--skip-fetch"])
    return run, d, sent


def test_auth_error_writes_hold_notifies_and_logs(tmp_path, monkeypatch):
    run, d, sent = _fake_week(tmp_path, monkeypatch, ClaudeError("Please run /login"))
    run.main()
    assert "claude login" in (d / "HOLD.md").read_text()
    assert sent and "HOLD" in sent[0][0]
    r = rows(tmp_path / "data" / "runs.csv")
    assert r[-1]["outcome"] == "hold" and r[-1]["week"] == "2026-10-05" and "auth" in r[-1]["note"]


def test_unexpected_error_still_logs_and_notifies_then_raises(tmp_path, monkeypatch):
    run, d, sent = _fake_week(tmp_path, monkeypatch, RuntimeError("boom"))
    with pytest.raises(RuntimeError):
        run.main()
    assert rows(tmp_path / "data" / "runs.csv")[-1]["outcome"] == "error" and sent


# --- spotcheck writes to runs.csv ----------------------------------------------------

def test_spotcheck_records_in_run_log(tmp_path, monkeypatch):
    import spotcheck
    monkeypatch.setattr(spotcheck, "HERE", tmp_path)
    monkeypatch.setattr(sys, "argv", ["spotcheck.py", "--week", "2026-10-05", "--agree", "4"])
    spotcheck.main()
    r = rows(tmp_path / "data" / "runs.csv")[-1]
    assert r["outcome"] == "spotcheck" and r["note"] == "agreed 4/5"


# --- launchd plist and wrapper -------------------------------------------------------

def test_plist_is_valid_monday_0900_with_hourly_catch_up():
    import plistlib
    p = plistlib.loads((APP / "launchd" / "com.vicky.adkvoc.plist").read_bytes())
    assert p["StartCalendarInterval"] == {"Weekday": 1, "Hour": 9, "Minute": 0}
    assert p["StartInterval"] == 3600 and p["RunAtLoad"] is True
    assert p["ProgramArguments"][-1].endswith("run_weekly.sh")


def test_wrapper_shell_syntax_and_publish_flag():
    sh = APP / "run_weekly.sh"
    assert subprocess.run(["sh", "-n", str(sh)]).returncode == 0
    t = sh.read_text()
    assert "--publish" in t and "due_week" in t and "--force" not in t


def test_wrapper_logs_and_counts_an_error_when_python_dies_before_logging(tmp_path):
    import shutil
    app = tmp_path / "app"
    app.mkdir()
    shutil.copy(APP / "run_weekly.sh", app)
    (app / "run.py").write_text("raise SystemExit(3)\n")  # dies before any run-log code
    import os
    env = {**os.environ, "ADKVOC_NOTIFY": "true"}  # no real banner during tests
    r = subprocess.run(["sh", str(app / "run_weekly.sh"), "2026-10-05"], capture_output=True, env=env)
    assert r.returncode == 3
    rows_ = rows(app / "data" / "runs.csv")
    assert rows_[-1]["outcome"] == "error" and rows_[-1]["week"] == "2026-10-05"
    assert list(rows_[0]) == runlog.COLUMNS
    assert not (app / "data" / ".lock").exists()


@pytest.mark.skipif(not Path("/Library/Frameworks/Python.framework/Versions/3.13/bin").exists(),
                    reason="machine-specific: Vicky's Mac")
def test_wrapper_path_finds_a_python_with_the_packages():
    """launchd uses the wrapper's PATH, not the shell's. Its python3 must import the requirements."""
    line = next(x for x in (APP / "run_weekly.sh").read_text().splitlines() if x.startswith("export PATH="))
    path = line.split("=", 1)[1].strip('"').replace("$HOME", str(Path.home()))
    r = subprocess.run(["sh", "-c", "python3 -c 'import yaml'"], env={"PATH": path, "HOME": str(Path.home())})
    assert r.returncode == 0


def test_give_up_note_on_the_last_retry_only(tmp_path):
    f = tmp_path / "runs.csv"
    assert runlog.give_up_note(f, "2026-10-12") == ""
    for _ in range(2):
        runlog.append(f, {"week": "2026-10-12", "outcome": "error"})
    assert "Giving up" in runlog.give_up_note(f, "2026-10-12") and "run_weekly.sh 2026-10-12" in runlog.give_up_note(f, "2026-10-12")


def _wrapper_app(tmp_path, run_py="raise SystemExit(0)\n", runlog_py=None):
    import os
    import shutil
    app = tmp_path / "app"
    (app / "data").mkdir(parents=True)
    shutil.copy(APP / "run_weekly.sh", app)
    (app / "run.py").write_text(run_py)
    (app / "runlog.py").write_text(runlog_py or (APP / "runlog.py").read_text())
    log = tmp_path / "notified"
    stub = tmp_path / "notify.sh"
    stub.write_text(f'#!/bin/sh\necho "$@" >> {log}\n')
    stub.chmod(0o755)
    env = {**os.environ, "ADKVOC_NOTIFY": str(stub), "ADKVOC_NO_PULL": "1"}
    return app, env, log


def test_stale_lock_from_a_dead_run_is_cleared_and_announced(tmp_path):
    app, env, log = _wrapper_app(tmp_path)
    (app / "data" / ".lock").mkdir()
    (app / "data" / ".lock" / "pid").write_text("999999")  # no such process
    r = subprocess.run(["sh", str(app / "run_weekly.sh"), "2026-10-05"], env=env, capture_output=True)
    assert r.returncode == 0 and "stale lock" in log.read_text()
    assert not (app / "data" / ".lock").exists()


def test_live_lock_means_skip_quietly(tmp_path):
    import os
    app, env, log = _wrapper_app(tmp_path, run_py="raise SystemExit(9)\n")
    (app / "data" / ".lock").mkdir()
    (app / "data" / ".lock" / "pid").write_text(str(os.getpid()))  # alive
    r = subprocess.run(["sh", str(app / "run_weekly.sh"), "2026-10-05"], env=env, capture_output=True)
    assert r.returncode == 0 and not log.exists() and (app / "data" / ".lock").exists()


def test_due_week_crash_is_logged_and_notified(tmp_path):
    app, env, log = _wrapper_app(tmp_path, runlog_py="raise SystemExit(1)\n")
    r = subprocess.run(["sh", str(app / "run_weekly.sh")], env=env, capture_output=True)
    assert r.returncode == 1 and "due_week failed" in log.read_text()
    assert rows(app / "data" / "runs.csv")[-1]["outcome"] == "error"


def test_wrapper_runs_the_due_week_end_to_end(tmp_path):
    app, env, log = _wrapper_app(tmp_path, run_py="import sys; open('ran', 'w').write(sys.argv[2])\n")
    r = subprocess.run(["sh", str(app / "run_weekly.sh")], env=env, capture_output=True)
    assert r.returncode == 0 and (app / "ran").read_text() == runlog.due_week(dt.datetime.now(), app / "x")


def test_wrapper_rejects_a_malformed_week(tmp_path):
    app, env, log = _wrapper_app(tmp_path)
    r = subprocess.run(["sh", str(app / "run_weekly.sh"), 'x"; do shell script "id'], env=env, capture_output=True)
    assert r.returncode == 2 and not (app / "data" / "runs.csv").exists()


def test_system_exit_inside_the_run_notifies(tmp_path, monkeypatch):
    run, d, sent = _fake_week(tmp_path, monkeypatch, SystemExit("--recheck: 3 issues unlabeled"))
    with pytest.raises(SystemExit):
        run.main()
    assert sent and rows(tmp_path / "data" / "runs.csv")[-1]["outcome"] == "error"


def test_wrapper_pulls_latest_code_before_running():
    t = (APP / "run_weekly.sh").read_text()
    assert t.index("git pull --ff-only") < t.index("python3 run.py")
