"""Central tool registry — name, JSON schema, Python callable."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from . import files, github, search, shell, vercel


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    fn: Callable[..., str]


# Tools that mutate the user's workspace, run code, or hit external services.
# These go through the permission gate unless --dangerously-skip-permissions / /bypass on.
DESTRUCTIVE: set[str] = {
    "bash",
    "write_file",
    "edit_file",
    "github_create_repo",
    "github_create_pr",
    "vercel_deploy",
}


TOOLS: list[Tool] = [
    # ── files ────────────────────────────────────────────────────────────
    Tool(
        name="read_file",
        description="Read a UTF-8 text file from the workspace. Returns its contents.",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
        fn=files.read_file,
    ),
    Tool(
        name="write_file",
        description="Create or overwrite a UTF-8 text file with the given content.",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        },
        fn=files.write_file,
    ),
    Tool(
        name="edit_file",
        description=(
            "Replace the first exact match of old_string with new_string. "
            "Use for surgical edits; old_string must be unique in the file."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_string": {"type": "string"},
                "new_string": {"type": "string"},
            },
            "required": ["path", "old_string", "new_string"],
        },
        fn=files.edit_file,
    ),
    Tool(
        name="list_dir",
        description="List files and folders inside a directory (non-recursive).",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string", "default": "."}},
        },
        fn=files.list_dir,
    ),
    Tool(
        name="grep",
        description="Search file contents for a regex pattern.",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string", "default": "."},
                "glob": {"type": "string"},
            },
            "required": ["pattern"],
        },
        fn=search.grep,
    ),
    Tool(
        name="bash",
        description=(
            "Run a shell command in the workspace. Use for builds, tests, "
            "package install, git, gh, vercel."
        ),
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "timeout": {"type": "number", "default": 120},
            },
            "required": ["command"],
        },
        fn=shell.bash,
    ),
    # ── GitHub ───────────────────────────────────────────────────────────
    Tool(
        name="github_status",
        description="Show GitHub CLI auth status and the active user.",
        parameters={"type": "object", "properties": {}},
        fn=github.status,
    ),
    Tool(
        name="github_list_repos",
        description="List the authenticated user's repos (via the gh CLI).",
        parameters={
            "type": "object",
            "properties": {"limit": {"type": "integer", "default": 30}},
        },
        fn=github.list_repos,
    ),
    Tool(
        name="github_create_repo",
        description=(
            "Create a new GitHub repo and push the current workspace as the "
            "initial commit. Defaults to PRIVATE."
        ),
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string", "default": ""},
                "private": {"type": "boolean", "default": True},
            },
            "required": ["name"],
        },
        fn=github.create_repo,
    ),
    Tool(
        name="github_create_pr",
        description=(
            "Open a pull request for the current git branch. Pushes the branch "
            "to origin if needed."
        ),
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "body": {"type": "string", "default": ""},
                "base": {"type": "string", "default": ""},
                "draft": {"type": "boolean", "default": False},
            },
            "required": ["title"],
        },
        fn=github.create_pr,
    ),
    # ── Vercel ───────────────────────────────────────────────────────────
    Tool(
        name="vercel_status",
        description="Show Vercel CLI auth + whether this directory is linked to a project.",
        parameters={"type": "object", "properties": {}},
        fn=vercel.status,
    ),
    Tool(
        name="vercel_list_projects",
        description="List Vercel projects in the active team.",
        parameters={"type": "object", "properties": {}},
        fn=vercel.list_projects,
    ),
    Tool(
        name="vercel_deploy",
        description="Deploy the workspace (or a subdirectory) to Vercel. prod=true for production.",
        parameters={
            "type": "object",
            "properties": {
                "cwd": {"type": "string", "default": "."},
                "prod": {"type": "boolean", "default": False},
            },
        },
        fn=vercel.deploy,
    ),
    Tool(
        name="vercel_logs",
        description="Show recent runtime logs for a deployment URL or project name.",
        parameters={
            "type": "object",
            "properties": {
                "url_or_project": {"type": "string"},
                "follow": {"type": "boolean", "default": False},
            },
            "required": ["url_or_project"],
        },
        fn=vercel.logs,
    ),
]


def schemas() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        for t in TOOLS
    ]


def dispatch(name: str, args: dict[str, Any], workspace: Path) -> tuple[str, bool]:
    for t in TOOLS:
        if t.name == name:
            try:
                out = t.fn(workspace=workspace, **args)
                return (out, True)
            except Exception as e:  # noqa: BLE001 — surface to LLM
                return (f"{type(e).__name__}: {e}", False)
    return (f"unknown tool: {name}", False)
