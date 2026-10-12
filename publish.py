"""AC10: commit the brief and the README index, then push. Only these two paths, ever.

All or nothing before the commit (rolled back on failure). If the push fails, the commit stays
and the next --publish run only pushes."""
import re
import subprocess
from pathlib import Path

INDEX = re.compile(r"(<!-- index:start -->\n)(.*?)(<!-- index:end -->)", re.S)
HEADER = "| Week | Issues | Status | Top theme |\n|---|---|---|---|\n"


def git(repo, *args, identity=None):
    pre = ["-c", f"user.name={identity[0]}", "-c", f"user.email={identity[1]}"] if identity else []
    return subprocess.run(["git", "-C", str(repo), *pre, *args], capture_output=True, text=True, check=True).stdout


def push_origin(repo):
    git(repo, "push", "origin", "HEAD:main")


def git_identity(repo) -> tuple[str, str]:
    return git(repo, "config", "user.name").strip(), git(repo, "config", "user.email").strip()


def _unpushed(repo, rel) -> bool:
    try:
        ahead = git(repo, "log", "--format=%H", "origin/main..HEAD", "--", rel)
    except subprocess.CalledProcessError:  # no remote branch yet: everything is unpushed
        ahead = git(repo, "log", "--format=%H", "--", rel)
    return bool(ahead.strip())


def publish(repo: Path, week: str, md: str, stats: dict, push=push_origin, identity=None) -> str:
    repo = Path(repo)
    identity = identity or git_identity(repo)
    if not identity[1].endswith("@users.noreply.github.com"):
        raise RuntimeError(f"commit email {identity[1]!r} is not a GitHub noreply address")
    if git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip() != "main":
        raise RuntimeError("publish only from the main branch")
    rel = f"briefs/{week}.md"
    target = repo / rel
    if target.exists():
        if git(repo, "ls-files", rel).strip() and _unpushed(repo, rel):
            push(repo)  # resume: committed earlier, push failed
            return str(target)
        raise FileExistsError(f"{target} is already published; re-publishing an edited brief is Ask first")
    if git(repo, "status", "--porcelain", "--", "README.md", "briefs").strip():
        raise RuntimeError("README.md or briefs/ has uncommitted changes; publish needs a clean tree")
    readme = (repo / "README.md").read_text()
    m = INDEX.search(readme)
    if not m:
        raise ValueError("README.md has no <!-- index:start --> / <!-- index:end --> markers")

    lines = m[2].splitlines()
    rows = [r for r in lines if r.startswith("| [")]
    other = [r for r in lines if not r.startswith("| [") and r not in HEADER.splitlines()]
    row = (f"| [{week}](briefs/{week}.md) | {stats['issues']} | Published, {stats['pass_rate']:.0%} verified "
           f"| {stats['top']} |")
    body = "\n".join(other + [""] if other else []) + HEADER + "\n".join(sorted([row, *rows], reverse=True)) + "\n"
    try:
        target.parent.mkdir(exist_ok=True)
        target.write_text(md)
        (repo / "README.md").write_text(readme[:m.start(2)] + body + readme[m.end(2):])
        allow = [rel, "README.md"]
        git(repo, "add", "--", *allow)
        staged = git(repo, "diff", "--cached", "--name-only").split()
        if sorted(staged) != sorted(allow):
            raise RuntimeError(f"refusing to commit unexpected files: {staged}")
        git(repo, "commit", "-m", f"Brief: week of {week}", "--no-verify", identity=identity)
    except Exception:
        git(repo, "reset", "-q", "--", rel, "README.md")
        target.unlink(missing_ok=True)
        (repo / "README.md").write_text(readme)
        raise
    push(repo)
    return str(target)
