"""Vercel integration — wraps the `vercel` CLI."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def _need_vc() -> None:
    if shutil.which("vercel") is None:
        raise RuntimeError("vercel CLI not installed. Run: npm i -g vercel")


def _run(cmd: list[str], cwd: Path, timeout: float = 600) -> str:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
    out = ((proc.stdout or "") + (proc.stderr or "")).strip()
    if proc.returncode != 0:
        raise RuntimeError(out or f"command failed: {' '.join(cmd)}")
    return out


# ── tools ───────────────────────────────────────────────────────────────
def status(workspace: Path) -> str:
    """Show whoami + linked project (if any)."""
    _need_vc()
    try:
        whoami = _run(["vercel", "whoami"], workspace, timeout=20)
    except RuntimeError as e:
        return f"not authenticated\n{e}\nrun: vercel login"
    linked = (workspace / ".vercel" / "project.json").exists()
    project = ""
    if linked:
        try:
            project = "linked: " + (workspace / ".vercel" / "project.json").read_text(
                encoding="utf-8"
            )
        except OSError:
            project = "linked: yes"
    else:
        project = "no project linked in this directory"
    return f"authenticated: {whoami}\n{project}"


def list_projects(workspace: Path) -> str:
    _need_vc()
    return _run(["vercel", "projects", "ls"], workspace, timeout=60)


def deploy(workspace: Path, cwd: str = ".", prod: bool = False) -> str:
    _need_vc()
    target = (workspace / cwd).resolve()
    if not target.exists():
        raise FileNotFoundError(cwd)
    cmd = ["vercel", "--yes"]
    if prod:
        cmd.append("--prod")
    return _run(cmd, target, timeout=600)


def logs(workspace: Path, url_or_project: str, follow: bool = False) -> str:
    """Tail recent logs for a deployment URL or project name."""
    _need_vc()
    cmd = ["vercel", "logs", url_or_project]
    # `--follow` blocks; we only run in one-shot mode so default to off
    if follow:
        cmd.append("--follow")
    return _run(cmd, workspace, timeout=60)
