"""Terminal rendering — mimics the Claude Code look (boxed panels, muted labels)."""

from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text


console = Console()


def banner() -> None:
    art = Text()
    art.append("  freecode ", style="bold magenta")
    art.append("◆", style="dim")
    art.append(" a free open-source coding agent", style="dim")
    console.print(Panel(art, border_style="magenta", padding=(0, 2)))


def assistant(text: str) -> None:
    if not text.strip():
        return
    console.print(Markdown(text))


def user_prompt_label() -> str:
    return "[bold cyan]›[/bold cyan] "


def tool_call(name: str, args_preview: str) -> None:
    header = Text()
    header.append("⚙ ", style="yellow")
    header.append(name, style="bold yellow")
    if args_preview:
        header.append(f"  {args_preview}", style="dim")
    console.print(header)


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
    label = "result" if ok else "error"
    console.print(
        Panel(
            content or "(empty)",
            title=f"[dim]{name} · {label}[/dim]",
            border_style=style,
            padding=(0, 1),
        )
    )


def code(body: str, lang: str = "text") -> None:
    console.print(Syntax(body, lang, theme="monokai", line_numbers=False))


def info(text: str) -> None:
    console.print(f"[dim]{text}[/dim]")


def error(text: str) -> None:
    console.print(f"[bold red]error[/bold red] {text}")


def rule() -> None:
    console.rule(style="dim")


def help_table() -> None:
    table = Table(title="Slash commands", show_header=False, border_style="dim")
    table.add_column("cmd", style="bold cyan")
    table.add_column("desc")
    for cmd, desc in (
        ("/help",   "show this help"),
        ("/clear",  "reset the conversation"),
        ("/model",  "print the active model"),
        ("/cwd",    "print the working directory"),
        ("/exit",   "leave the session (ctrl-d also works)"),
    ):
        table.add_row(cmd, desc)
    console.print(table)
