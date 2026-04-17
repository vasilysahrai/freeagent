"""GitHub integration — thin wrapper over the `gh` CLI."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def _run(cmd: list[str], cwd: Path) -> str:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=120)
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        raise RuntimeError(out.strip() or f"command failed: {' '.join(cmd)}")
    return out.strip()


def create_repo(
    workspace: Path,
    name: str,
    description: str = "",
    private: bool = False,
) -> str:
    if shutil.which("gh") is None:
        raise RuntimeError("gh CLI not installed. See https://cli.github.com")
    if shutil.which("git") is None:
        raise RuntimeError("git not installed")

    log: list[str] = []
    if not (workspace / ".git").exists():
        log.append(_run(["git", "init", "-b", "main"], workspace))

    log.append(_run(["git", "add", "-A"], workspace))

    # Only commit if there's something staged; ignore benign "nothing to commit" failures.
    try:
        log.append(_run(["git", "commit", "-m", "Initial commit"], workspace))
    except RuntimeError as e:
        if "nothing to commit" not in str(e).lower():
            raise

    visibility = "--private" if private else "--public"
    cmd = ["gh", "repo", "create", name, visibility, "--source", ".", "--remote", "origin", "--push"]
    if description:
        cmd += ["--description", description]
    log.append(_run(cmd, workspace))

    url = _run(["gh", "repo", "view", "--json", "url", "-q", ".url"], workspace)
    return f"created {url}\n" + "\n".join(l for l in log if l)
