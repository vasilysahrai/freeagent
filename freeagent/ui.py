"""Terminal rendering — calm, low-chrome panels with streaming support."""

from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


console = Console()


# ── one-shot prints ──────────────────────────────────────────────────────
def banner() -> None:
    art = Text()
    art.append("FreeAgent", style="bold")
    art.append("  ·  ", style="dim")
    art.append("an open-source terminal coding agent", style="dim")
    console.print(art)


def assistant(text: str) -> None:
    if not text.strip():
        return
    console.print(Markdown(text))


# ── streaming tokens ─────────────────────────────────────────────────────
def assistant_open() -> None:
    pass  # nothing — we just print plain text inline


def stream_token(t: str) -> None:
    console.print(t, end="", soft_wrap=True, highlight=False, markup=False)


def assistant_close() -> None:
    console.print("")  # newline


# ── tool calls ───────────────────────────────────────────────────────────
def tool_call(name: str, args_preview: str) -> None:
    h = Text()
    h.append("· ", style="dim")
    h.append(name, style="bold")
    if args_preview:
        h.append(f"  {args_preview}", style="dim")
    console.print(h)


def tool_result(name: str, body: str, ok: bool = True, max_lines: int = 18) -> None:
    lines = body.splitlines()
    truncated = False
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        truncated = True
    content = "\n".join(lines)
    if truncated:
        content += f"\n… ({len(body.splitlines()) - max_lines} more lines)"
    style = "green" if ok else "red"
    label = "ok" if ok else "error"
    console.print(
        Panel(
            content or "(empty)",
            title=f"[dim]{name} · {label}[/dim]",
            border_style=style,
            padding=(0, 1),
        )
    )


# ── small helpers ────────────────────────────────────────────────────────
def info(text: str) -> None:
    console.print(f"[dim]{text}[/dim]")


def error(text: str) -> None:
    console.print(f"[bold red]error[/bold red] {text}")


def rule() -> None:
    console.rule(style="dim")


def help_table() -> None:
    table = Table(title=None, show_header=False, border_style="dim", box=None)
    table.add_column("cmd", style="bold")
    table.add_column("desc", style="dim")
    rows = [
        ("/help",            "show this help"),
        ("/models",          "list models for the current provider"),
        ("/catalog",         "list every model FreeAgent knows about"),
        ("/provider <id>",   "switch provider (zai, groq, openrouter, ollama, openai, …)"),
        ("/model <id>",      "switch model on the current provider"),
        ("/key <value>",     "set/replace the API key for this session"),
        ("/stream on|off",   "toggle token streaming"),
        ("/clear",            "reset the conversation"),
        ("/cwd",              "print the working directory"),
        ("/exit",             "leave the session (ctrl-d also works)"),
    ]
    for c, d in rows:
        table.add_row(c, d)
    console.print(table)


def models_table(rows: list[tuple[str, str, str, str]], title: str) -> None:
    """rows: (provider, model, tier, notes)"""
    table = Table(title=title, border_style="dim")
    table.add_column("provider", style="bold")
    table.add_column("model")
    table.add_column("tier")
    table.add_column("notes", style="dim")
    for provider, model, tier, notes in rows:
        tier_style = {"free": "green", "local": "cyan", "paid": "yellow"}.get(tier, "")
        table.add_row(provider, model, f"[{tier_style}]{tier}[/{tier_style}]", notes)
    console.print(table)
