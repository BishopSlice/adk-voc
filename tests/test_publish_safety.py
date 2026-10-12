import subprocess

import pytest

from gate import decide, effective_bar
from publish import publish

ID = ("t", "t@users.noreply.github.com")
S = {"verdict": "SUPPORTED"}


def _repo(tmp_path):
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True)
    (tmp_path / "README.md").write_text("# r\n<!-- index:start -->\nnote kept\n<!-- index:end -->\n")
    g = ["git", "-C", str(tmp_path), "-c", f"user.name={ID[0]}", "-c", f"user.email={ID[1]}"]
    subprocess.run(g + ["add", "-A"], check=True)
    subprocess.run(g + ["commit", "-qm", "init", "--no-verify"], check=True)
    return tmp_path


def _boom(repo):
    raise RuntimeError("push failed")


def test_bar_can_only_be_raised_never_lowered():
    assert effective_bar("0.5", 0.95) == 0.95 and effective_bar(None, 0.8) == 0.95
    assert effective_bar("1.01", 0.95) == 1.01


def test_checker_must_cover_every_linked_issue():
    assert not decide([S] * 12, [], True, links=20)["publish"]
    assert decide([S] * 20, [], True, links=20)["publish"]


def test_failed_push_keeps_commit_and_rerun_only_pushes(tmp_path):
    repo = _repo(tmp_path)
    stats = {"issues": 1, "pass_rate": 1.0, "top": "x"}
    with pytest.raises(RuntimeError):
        publish(repo, "2026-10-05", "# b\n", stats, push=_boom, identity=ID)
    pushed = []
    publish(repo, "2026-10-05", "# b\n", stats, push=lambda r: pushed.append(1), identity=ID)  # resume
    assert pushed and "note kept" in (repo / "README.md").read_text()


def test_failure_before_commit_rolls_back(tmp_path):
    repo = _repo(tmp_path)
    (repo / "README.md").write_text("# r\nno markers\n")
    subprocess.run(["git", "-C", str(repo), "-c", f"user.name={ID[0]}", "-c", f"user.email={ID[1]}",
                    "commit", "-qam", "drop markers", "--no-verify"], check=True)
    with pytest.raises(ValueError):
        publish(repo, "2026-10-05", "# b\n", {"issues": 1, "pass_rate": 1, "top": "x"}, push=print, identity=ID)
    assert not (repo / "briefs" / "2026-10-05.md").exists()


def test_refuses_dirty_tree_wrong_branch_and_non_noreply_identity(tmp_path):
    repo = _repo(tmp_path)
    st = {"issues": 1, "pass_rate": 1, "top": "x"}
    (repo / "README.md").write_text((repo / "README.md").read_text() + "local edit\n")
    with pytest.raises(RuntimeError, match="clean"):
        publish(repo, "2026-10-05", "# b\n", st, push=print, identity=ID)
    subprocess.run(["git", "-C", str(repo), "checkout", "-q", "--", "README.md"], check=True)
    subprocess.run(["git", "-C", str(repo), "checkout", "-qb", "other"], check=True)
    with pytest.raises(RuntimeError, match="main"):
        publish(repo, "2026-10-05", "# b\n", st, push=print, identity=ID)
    subprocess.run(["git", "-C", str(repo), "checkout", "-q", "main"], check=True)
    with pytest.raises(RuntimeError, match="noreply"):
        publish(repo, "2026-10-05", "# b\n", st, push=print, identity=("me", "me@gmail.com"))
