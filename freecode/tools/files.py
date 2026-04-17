"""File operations — sandboxed to the workspace root."""

from __future__ import annotations

from pathlib import Path


MAX_READ_BYTES = 256 * 1024  # 256 KiB guard


def _resolve(workspace: Path, path: str) -> Path:
    p = (workspace / path).resolve()
    ws = workspace.resolve()
    if ws not in p.parents and p != ws:
        raise ValueError(f"path escapes workspace: {path}")
    return p


def read_file(workspace: Path, path: str) -> str:
    p = _resolve(workspace, path)
    if not p.exists():
        raise FileNotFoundError(path)
    if p.is_dir():
        raise IsADirectoryError(path)
    data = p.read_bytes()
    if len(data) > MAX_READ_BYTES:
        data = data[:MAX_READ_BYTES]
        suffix = f"\n\n[truncated: file is larger than {MAX_READ_BYTES} bytes]"
    else:
        suffix = ""
    return data.decode("utf-8", errors="replace") + suffix


def write_file(workspace: Path, path: str, content: str) -> str:
    p = _resolve(workspace, path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"wrote {len(content)} chars to {path}"


def edit_file(workspace: Path, path: str, old_string: str, new_string: str) -> str:
    p = _resolve(workspace, path)
    if not p.exists():
        raise FileNotFoundError(path)
    src = p.read_text(encoding="utf-8")
    count = src.count(old_string)
    if count == 0:
        raise ValueError("old_string not found in file")
    if count > 1:
        raise ValueError(f"old_string matches {count} times — make it unique")
    p.write_text(src.replace(old_string, new_string, 1), encoding="utf-8")
    return f"patched {path}"


def list_dir(workspace: Path, path: str = ".") -> str:
    p = _resolve(workspace, path)
    if not p.exists():
        raise FileNotFoundError(path)
    if not p.is_dir():
        raise NotADirectoryError(path)
    entries = sorted(p.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    rows = []
    for e in entries:
        if e.name.startswith(".") and e.name not in {".env.example", ".gitignore"}:
            continue
        marker = "/" if e.is_dir() else ""
        rows.append(f"{e.name}{marker}")
    return "\n".join(rows) or "(empty)"
