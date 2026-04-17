"""Command-line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

from . import __version__, ui
from .agent import Agent
from .config import Config


SLASH_COMMANDS = {"/help", "/clear", "/model", "/cwd", "/exit", "/quit"}


def _history_path() -> Path:
    home = Path.home() / ".freecode"
    home.mkdir(parents=True, exist_ok=True)
    return home / "history"


def _handle_slash(cmd: str, agent: Agent) -> bool:
    """Return True if a slash command was handled."""
    cmd = cmd.strip()
    if cmd in {"/exit", "/quit"}:
        raise EOFError
    if cmd == "/help":
        ui.help_table()
        return True
    if cmd == "/clear":
        agent.reset()
        ui.info("conversation cleared.")
        return True
    if cmd == "/model":
        ui.info(f"model: {agent.config.model}  ·  base: {agent.config.base_url}")
        return True
    if cmd == "/cwd":
        ui.info(f"workspace: {agent.config.workspace}")
        return True
    if cmd.startswith("/"):
        ui.error(f"unknown command: {cmd} — type /help")
        return True
    return False


def _repl(agent: Agent) -> None:
    ui.banner()
    ui.info(
        f"model {agent.config.model} · workspace {agent.config.workspace} · "
        "type /help for commands, ctrl-d to exit"
    )
    ui.rule()

    session: PromptSession = PromptSession(history=FileHistory(str(_history_path())))
    while True:
        try:
            line = session.prompt("› ")
        except (EOFError, KeyboardInterrupt):
            ui.info("bye.")
            return
        line = line.strip()
        if not line:
            continue
        if line.startswith("/") and _handle_slash(line, agent):
            continue
        try:
            agent.turn(line)
        except KeyboardInterrupt:
            ui.info("(interrupted)")
        except Exception as e:  # noqa: BLE001 — surface as friendly error
            ui.error(str(e))


def _one_shot(agent: Agent, prompt: str) -> None:
    agent.turn(prompt)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="freecode",
        description="A free open-source terminal coding agent — Claude Code-style, powered by z.ai.",
    )
    parser.add_argument(
        "-p",
        "--prompt",
        help="Run a single prompt non-interactively and exit.",
    )
    parser.add_argument(
        "-C",
        "--cwd",
        help="Workspace directory (defaults to the current directory).",
    )
    parser.add_argument("--version", action="version", version=f"freecode {__version__}")
    args = parser.parse_args(argv)

    try:
        config = Config.load(workspace=Path(args.cwd) if args.cwd else None)
        agent = Agent(config)
    except Exception as e:  # noqa: BLE001 — startup errors are user-facing
        ui.error(str(e))
        return 1

    if args.prompt:
        _one_shot(agent, args.prompt)
    else:
        _repl(agent)
    return 0


if __name__ == "__main__":
    sys.exit(main())
