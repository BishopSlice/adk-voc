"""The only place that calls Claude. Headless `claude -p` on the user's subscription."""
import subprocess


class ClaudeError(RuntimeError):
    pass


def ask_claude(prompt: str, model: str) -> str:
    out = subprocess.run(["claude", "-p", "--model", model], input=prompt,
                         capture_output=True, text=True, timeout=900)
    if out.returncode != 0:
        raise ClaudeError(out.stderr.strip() or out.stdout.strip())
    return out.stdout


def fence(text: str) -> str:
    """Untrusted issue text can't close our data tags."""
    import re
    return re.sub(r"</?\s*(issue|source)\b[^>]*>", "[tag removed]", text, flags=re.I)
