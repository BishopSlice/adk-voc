import subprocess

from gate import decide, write_hold

S = {"verdict": "SUPPORTED"}
N = {"verdict": "NOT_SUPPORTED", "claim": "x", "reason": "r"}


def test_publish_needs_95_no_code_failures_tldr_and_enough_claims():
    assert decide([S] * 20, [], True)["publish"]
    assert not decide([S] * 18 + [N] * 2, [], True)["publish"]          # 90%
    assert not decide([S] * 20, [N], True)["publish"]                    # a code check failed
    assert not decide([S] * 20, [], False)["publish"]                    # TL;DR too long
    assert not decide([S] * 5, [], True)["publish"]                      # too few claims to trust


def test_pass_rate_counts_llm_verdicts_only_so_nothing_double_counts():
    d = decide([S] * 19 + [N], [N], True)
    assert d["pass_rate"] == 0.95 and not d["publish"] and len(d["reasons"]) == 1


def test_hold_file_lists_failures(tmp_path):
    d = decide([S] * 18 + [N] * 2, [], False)
    write_hold(tmp_path, "2026-10-05", d, [N, N])
    t = (tmp_path / "HOLD.md").read_text()
    assert "Not published" in t and "90%" in t and "TL;DR" in t and t.count("| x |") == 2


def _repo(tmp_path):
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True)
    (tmp_path / "README.md").write_text("# r\n<!-- index:start -->\n<!-- index:end -->\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=t", "-c", "user.email=t@t", "commit",
                    "-qm", "init", "--no-verify"], check=True)
    return tmp_path


def test_publish_commits_only_the_brief_and_index(tmp_path):
    from publish import publish
    repo = _repo(tmp_path)
    (repo / "stray.txt").write_text("not allowed")
    pushed = []
    publish(repo, "2026-10-05", "# brief\n", {"issues": 83, "pass_rate": 0.99, "top": "Core runtime"},
            push=lambda r: pushed.append(r), identity=("t", "t@users.noreply.github.com"))
    files = subprocess.run(["git", "-C", str(repo), "show", "--name-only", "--format="],
                           capture_output=True, text=True).stdout.split()
    assert sorted(files) == ["README.md", "briefs/2026-10-05.md"] and pushed
    assert "| [2026-10-05](briefs/2026-10-05.md) | 83 | Published, 99% verified | Core runtime |" in (
        repo / "README.md").read_text()


def test_publish_refuses_to_overwrite_a_published_week(tmp_path):
    import pytest
    from publish import publish
    repo = _repo(tmp_path)
    (repo / "briefs").mkdir()
    (repo / "briefs" / "2026-10-05.md").write_text("old")
    with pytest.raises(FileExistsError):
        publish(repo, "2026-10-05", "new", {"issues": 1, "pass_rate": 1, "top": "x"}, push=print, identity=("t", "t@users.noreply.github.com"))


def test_spotcheck_samples_five_supported_claims_reproducibly():
    from spotcheck import sample
    claims = [{"id": f"c{i}", "claim": f"claim {i}", "verdict": "SUPPORTED"} for i in range(20)] + [N]
    a, b = sample(claims, seed=1), sample(claims, seed=1)
    assert len(a) == 5 and a == b and all(c["verdict"] == "SUPPORTED" for c in a)
