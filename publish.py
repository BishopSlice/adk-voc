"""AC10: commit the brief and the README index, then push. Only these two paths, ever."""
import re
import subprocess
from pathlib import Path

INDEX = re.compile(r"(<!-- index:start -->\n)(.*?)(<!-- index:end -->)", re.S)
HEADER = "| Week | Issues | Status | Top theme |\n|---|---|---|---|\n"


def git(repo, *args, identity=None):
    pre = ["-c", f"user.name={identity[0]}", "-c", f"user.email={identity[1]}"] if identity else []
    return subprocess.run(["git", "-C", str(repo), *pre, *args], capture_output=True, text=True, check=True).stdout


def push_origin(repo):
    git(repo, "push", "origin", "main")


def publish(repo: Path, week: str, md: str, stats: dict, push=push_origin, identity=None) -> str:
    repo = Path(repo)
    target = repo / "briefs" / f"{week}.md"
    if target.exists():
        raise FileExistsError(f"{target} is already published; re-publishing an edited brief is Ask first")
    target.parent.mkdir(exist_ok=True)
    target.write_text(md)
    readme = (repo / "README.md").read_text()
    m = INDEX.search(readme)
    rows = [r for r in m[2].splitlines() if r.startswith("| [")]
    row = (f"| [{week}](briefs/{week}.md) | {stats['issues']} | Published, {stats['pass_rate']:.0%} verified "
           f"| {stats['top']} |")
    body = HEADER + "\n".join(sorted([row, *rows], reverse=True)) + "\n"
    (repo / "README.md").write_text(readme[:m.start(2)] + body + readme[m.end(2):])
    allow = [f"briefs/{week}.md", "README.md"]
    git(repo, "add", "--", *allow)
    staged = git(repo, "diff", "--cached", "--name-only").split()
    if sorted(staged) != sorted(allow):
        raise RuntimeError(f"refusing to commit unexpected files: {staged}")
    git(repo, "commit", "-m", f"Brief: week of {week}", "--no-verify", identity=identity)
    push(repo)
    return str(target)
