"""Central registry that aggregates every tool into a dispatch table and
OpenAI-style JSON schemas."""

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


TOOLS: list[Tool] = [
    Tool(
        name="read_file",
        description="Read a UTF-8 text file from the workspace. Returns its contents.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path relative to the workspace."},
            },
            "required": ["path"],
        },
        fn=files.read_file,
    ),
    Tool(
        name="write_file",
        description="Create or overwrite a UTF-8 text file with the given content.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
        fn=files.write_file,
    ),
    Tool(
        name="edit_file",
        description=(
            "Replace the first exact match of old_string with new_string in a file. "
            "Use this for surgical edits. old_string must appear exactly once."
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
            "properties": {
                "path": {"type": "string", "default": "."},
            },
        },
        fn=files.list_dir,
    ),
    Tool(
        name="grep",
        description="Search file contents for a regex pattern. Returns matching lines with paths.",
        parameters={
            "type": "object",
            "properties": {
                "pattern":  {"type": "string"},
                "path":     {"type": "string", "default": "."},
                "glob":     {"type": "string", "description": "Optional glob like '*.py'."},
            },
            "required": ["pattern"],
        },
        fn=search.grep,
    ),
    Tool(
        name="bash",
        description=(
            "Run a shell command in the workspace. Use for build tools, tests, package "
            "install, git, gh, vercel, etc. Returns stdout+stderr."
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
    Tool(
        name="github_create_repo",
        description=(
            "Create a new public GitHub repo under the authenticated user using the "
            "gh CLI, then push the current workspace as the initial commit."
        ),
        parameters={
            "type": "object",
            "properties": {
                "name":        {"type": "string"},
                "description": {"type": "string", "default": ""},
                "private":     {"type": "boolean", "default": False},
            },
            "required": ["name"],
        },
        fn=github.create_repo,
    ),
    Tool(
        name="vercel_deploy",
        description=(
            "Deploy the current workspace (or a subdirectory) to Vercel using the "
            "Vercel CLI. Pass prod=true for production deploys."
        ),
        parameters={
            "type": "object",
            "properties": {
                "cwd":  {"type": "string", "default": "."},
                "prod": {"type": "boolean", "default": False},
            },
        },
        fn=vercel.deploy,
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
    """Execute the named tool with args. Returns (text, ok)."""
    for t in TOOLS:
        if t.name == name:
            try:
                out = t.fn(workspace=workspace, **args)
                return (out, True)
            except Exception as e:  # noqa: BLE001 — surface to LLM
                return (f"{type(e).__name__}: {e}", False)
    return (f"unknown tool: {name}", False)
