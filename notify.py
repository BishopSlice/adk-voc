"""A macOS notification, so a hold or error is never silent."""
import subprocess


def _q(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def notify(title: str, message: str) -> None:
    script = f"display notification {_q(message[:200])} with title {_q('adk-voc: ' + title)}"
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=10)
    except Exception:  # noqa: BLE001 - the run log matters more than the banner
        pass
