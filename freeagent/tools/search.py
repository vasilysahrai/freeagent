"""Regex search across the workspace."""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path


SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next", ".vercel"}
MAX_HITS = 200


def grep(workspace: Path, pattern: str, path: str = ".", glob: str | None = None) -> str:
    rx = re.compile(pattern)
    root = (workspace / path).resolve()
    if not root.exists():
        raise FileNotFoundError(path)

    hits: list[str] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if glob and not fnmatch.fnmatch(p.name, glob):
            continue
        try:
            with p.open("r", encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f, start=1):
                    if rx.search(line):
                        rel = p.relative_to(workspace)
                        hits.append(f"{rel}:{i}: {line.rstrip()}")
                        if len(hits) >= MAX_HITS:
                            hits.append("[hit limit reached]")
                            return "\n".join(hits)
        except (OSError, UnicodeDecodeError):
            continue
    return "\n".join(hits) if hits else "(no matches)"
