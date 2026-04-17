"""Vercel integration — wraps the `vercel` CLI."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def deploy(workspace: Path, cwd: str = ".", prod: bool = False) -> str:
    if shutil.which("vercel") is None:
        raise RuntimeError("vercel CLI not installed. Run: npm i -g vercel")

    target = (workspace / cwd).resolve()
    if not target.exists():
        raise FileNotFoundError(cwd)

    cmd = ["vercel", "--yes"]
    if prod:
        cmd.append("--prod")

    proc = subprocess.run(cmd, cwd=str(target), capture_output=True, text=True, timeout=600)
    out = ((proc.stdout or "") + (proc.stderr or "")).strip()
    if proc.returncode != 0:
        raise RuntimeError(out or "vercel deploy failed")
    return out
