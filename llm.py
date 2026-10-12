"""The only place that calls Claude. Headless `claude -p` on the user's subscription."""
import re
import subprocess
import tempfile


class ClaudeError(RuntimeError):
    pass


# Issue text is untrusted, so the headless run gets nothing to act with: no built-in tools,
# no MCP servers or connectors, no skills, no settings, hooks or CLAUDE.md, and an empty folder.
LOCKDOWN = ["--tools", "", "--strict-mcp-config", "--disable-slash-commands",
            "--setting-sources", "", "--no-session-persistence"]


def ask_claude(prompt: str, model: str) -> str:
    with tempfile.TemporaryDirectory() as empty:
        out = subprocess.run(["claude", "-p", "--model", model, *LOCKDOWN], input=prompt,
                             capture_output=True, text=True, timeout=900, cwd=empty)
    if out.returncode != 0:
        err = (out.stderr.strip() or out.stdout.strip())[:300]
        raise ClaudeError(re.sub(r"/Users/[^\s:]+", "<path>", err))  # no local paths in logs
    return out.stdout


def fence(text: str) -> str:
    """Untrusted text can't open or close any tag: every angle bracket is replaced."""
    return text.replace("<", "‹").replace(">", "›")
