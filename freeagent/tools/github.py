"""GitHub integration — wraps the `gh` CLI."""

from __future__ import annotations

import json as _json
import shutil
import subprocess
from pathlib import Path


def _run(cmd: list[str], cwd: Path, timeout: float = 120) -> str:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        raise RuntimeError(out.strip() or f"command failed: {' '.join(cmd)}")
    return out.strip()


def _need_gh() -> None:
    if shutil.which("gh") is None:
        raise RuntimeError(
            "gh CLI not installed. macOS: 'brew install gh'. "
            "Linux/Windows: https://cli.github.com"
        )


# ── tools ───────────────────────────────────────────────────────────────
def status(workspace: Path) -> str:
    """Return the current `gh auth` status + active user."""
    _need_gh()
    try:
        auth = _run(["gh", "auth", "status"], workspace)
    except RuntimeError as e:
        return f"not authenticated\n{e}\nrun: gh auth login"
    try:
        user = _run(["gh", "api", "user", "-q", ".login"], workspace)
        return f"authenticated as {user}\n{auth}"
    except RuntimeError:
        return auth


def list_repos(workspace: Path, limit: int = 30) -> str:
    _need_gh()
    out = _run(
        ["gh", "repo", "list", "--limit", str(limit),
         "--json", "name,description,visibility,url",
         "--jq", '.[] | "\(.visibility|ascii_downcase)\t\(.name)\t\(.description // "")\t\(.url)"'],
        workspace,
    )
    return out or "(no repos)"


def create_repo(
    workspace: Path,
    name: str,
    description: str = "",
    private: bool = True,
) -> str:
    _need_gh()
    if shutil.which("git") is None:
        raise RuntimeError("git not installed")

    log: list[str] = []
    if not (workspace / ".git").exists():
        log.append(_run(["git", "init", "-b", "main"], workspace))

    log.append(_run(["git", "add", "-A"], workspace))

    try:
        log.append(_run(["git", "commit", "-m", "Initial commit"], workspace))
    except RuntimeError as e:
        if "nothing to commit" not in str(e).lower():
            raise

    visibility = "--private" if private else "--public"
    cmd = ["gh", "repo", "create", name, visibility, "--source", ".",
           "--remote", "origin", "--push"]
    if description:
        cmd += ["--description", description]
    log.append(_run(cmd, workspace))

    url = _run(["gh", "repo", "view", "--json", "url", "-q", ".url"], workspace)
    return f"created {url}\n" + "\n".join(l for l in log if l)


def create_pr(
    workspace: Path,
    title: str,
    body: str = "",
    base: str = "",
    draft: bool = False,
) -> str:
    """Open a PR for the current branch. Pushes if needed."""
    _need_gh()
    if shutil.which("git") is None:
        raise RuntimeError("git not installed")

    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], workspace)
    if branch in ("main", "master"):
        raise RuntimeError(f"current branch is {branch!r} — checkout a feature branch first")

    # Push (sets upstream if missing). gh pr create will also do this for you,
    # but doing it ourselves makes the error message clearer.
    try:
        _run(["git", "push", "-u", "origin", branch], workspace)
    except RuntimeError as e:
        if "Everything up-to-date" not in str(e):
            raise

    cmd = ["gh", "pr", "create", "--title", title, "--body", body or title]
    if base:
        cmd += ["--base", base]
    if draft:
        cmd += ["--draft"]
    return _run(cmd, workspace)
