"""Shell command execution."""

from __future__ import annotations

import subprocess
from pathlib import Path


MAX_OUTPUT = 20_000


def bash(workspace: Path, command: str, timeout: float = 120) -> str:
    proc = subprocess.run(
        command,
        shell=True,
        cwd=str(workspace),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    out = proc.stdout or ""
    err = proc.stderr or ""
    combined = out
    if err:
        combined = (combined + "\n" if combined else "") + err
    if len(combined) > MAX_OUTPUT:
        combined = combined[:MAX_OUTPUT] + "\n[output truncated]"
    status = f"[exit {proc.returncode}]"
    return f"{status}\n{combined}".strip()
