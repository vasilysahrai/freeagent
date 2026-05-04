"""Command-line entry point — REPL with bottom status bar + slash commands."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style

from . import __version__, ui
from .agent import Agent
from .config import (
    CATALOG,
    PROVIDERS,
    Config,
    detected_keys,
    save_key_to_env,
    models_for,
)


def _history_path() -> Path:
    home = Path.home() / ".freeagent"
    home.mkdir(parents=True, exist_ok=True)
    return home / "history"


def _print_models(provider_id: str) -> None:
    rows = [(m.provider, m.model, m.tier, m.notes) for m in models_for(provider_id)]
    if not rows:
        ui.info(f"no models registered for {provider_id} (still works — pass any model id).")
        return
    ui.models_table(rows, title=f"Models for {PROVIDERS[provider_id].label}")


def _print_catalog() -> None:
    rows = [(m.provider, m.model, m.tier, m.notes) for m in CATALOG]
    ui.models_table(rows, title="Full FreeAgent catalog")


def _print_keys() -> None:
    rows = []
    for pid, has in detected_keys():
        p = PROVIDERS[pid]
        rows.append((pid, p.env_key or "—", has, p.signup))
    ui.keys_table(rows)


def _print_deps() -> None:
    rows = []
    gh_ok = shutil.which("gh") is not None
    rows.append(("gh", gh_ok, "GitHub CLI" + ("" if gh_ok else " — install from https://cli.github.com")))
    vc_ok = shutil.which("vercel") is not None
    rows.append(("vercel", vc_ok, "Vercel CLI" + ("" if vc_ok else " — npm i -g vercel")))
    git_ok = shutil.which("git") is not None
    rows.append(("git", git_ok, "git"))
    ui.deps_status(rows)


def _gh_or_vc_status(label: str, cmd_check: list[str], cwd: Path) -> None:
    if shutil.which(cmd_check[0]) is None:
        ui.error(f"{label} CLI not installed.")
        return
    try:
        proc = subprocess.run(cmd_check, cwd=str(cwd), capture_output=True, text=True, timeout=20)
        out = ((proc.stdout or "") + (proc.stderr or "")).strip()
        ui.info(out or f"{label}: ok")
    except subprocess.TimeoutExpired:
        ui.error(f"{label} status timed out")


# ── slash command handlers ─────────────────────────────────────────────
def _switch_provider(agent: Agent, prov_id: str) -> None:
    prov_id = prov_id.strip().lower()
    if prov_id not in PROVIDERS:
        ui.error(f"unknown provider {prov_id!r}. Choices: {', '.join(PROVIDERS)}.")
        return
    p = PROVIDERS[prov_id]
    agent.config.provider = prov_id
    agent.config.base_url = p.base_url
    agent.config.model = p.default_model
    if p.env_key:
        agent.config.api_key = os.getenv(p.env_key, "")
    elif not p.needs_key:
        agent.config.api_key = "local-no-key"
    try:
        agent.reload_client()
        ui.info(f"now using {p.label} · {agent.config.model}")
    except Exception as e:  # noqa: BLE001
        ui.error(str(e))


def _switch_model(agent: Agent, model_id: str) -> None:
    agent.config.model = model_id.strip()
    ui.info(f"model → {agent.config.model}")


def _set_key(agent: Agent, value: str) -> None:
    agent.config.api_key = value.strip()
    try:
        agent.reload_client()
        ui.info("api key set for this session.")
    except Exception as e:  # noqa: BLE001
        ui.error(str(e))


def _save_current_key(agent: Agent) -> None:
    p = agent.config.preset()
    if not p.env_key:
        ui.warn(f"{p.label} doesn't use a key.")
        return
    if not agent.config.api_key or agent.config.api_key == "local-no-key":
        ui.error("no key in this session — run /key <value> first.")
        return
    path = save_key_to_env(p.env_key, agent.config.api_key)
    ui.info(f"saved {p.env_key} → {path}")


def _toggle(setting: str, value: str) -> bool | None:
    v = value.strip().lower()
    if v in ("on", "true", "1", "yes"):
        return True
    if v in ("off", "false", "0", "no"):
        return False
    ui.error(f"usage: /{setting} on|off")
    return None


def _handle_slash(cmd: str, agent: Agent) -> bool:
    cmd = cmd.strip()
    if not cmd.startswith("/"):
        return False

    head, _, rest = cmd.partition(" ")
    rest = rest.strip()

    if head in ("/exit", "/quit"):
        raise EOFError
    if head == "/help":
        ui.help_table()
        return True
    if head == "/clear":
        agent.reset()
        ui.info("conversation cleared.")
        return True
    if head == "/cwd":
        ui.info(f"workspace: {agent.config.workspace}")
        return True
    if head == "/model":
        if not rest:
            ui.info(
                f"provider: {agent.config.provider}  ·  "
                f"model: {agent.config.model}  ·  "
                f"base: {agent.config.base_url}"
            )
        else:
            _switch_model(agent, rest)
        return True
    if head == "/provider":
        if not rest:
            ui.info(f"provider: {agent.config.provider} ({PROVIDERS[agent.config.provider].label})")
            ui.info("choices: " + ", ".join(PROVIDERS))
        else:
            _switch_provider(agent, rest)
        return True
    if head == "/key":
        if not rest:
            ui.error("usage: /key <value>")
        else:
            _set_key(agent, rest)
        return True
    if head == "/save-key":
        _save_current_key(agent)
        return True
    if head == "/keys":
        _print_keys()
        return True
    if head == "/models":
        _print_models(agent.config.provider)
        return True
    if head == "/catalog":
        _print_catalog()
        return True
    if head in ("/bypass", "/yolo"):
        if not rest:
            ui.info(f"bypass {'on' if agent.config.bypass_permissions else 'off'}")
            return True
        v = _toggle("bypass", rest)
        if v is None:
            return True
        agent.config.bypass_permissions = v
        if v:
            ui.warn("BYPASS MODE — tool calls run without confirmation. /bypass off to disable.")
        else:
            ui.info("bypass disabled — destructive tools will prompt again.")
        return True
    if head == "/stream":
        if not rest:
            ui.info(f"streaming {'on' if agent.config.stream else 'off'}")
            return True
        v = _toggle("stream", rest)
        if v is not None:
            agent.config.stream = v
            ui.info(f"streaming {'on' if v else 'off'}")
        return True
    if head == "/verbose":
        if not rest:
            ui.info(f"verbose {'on' if agent.verbose else 'off'}")
            return True
        v = _toggle("verbose", rest)
        if v is not None:
            agent.verbose = v
            ui.info(f"verbose {'on' if v else 'off'}")
        return True
    if head == "/gh":
        _gh_or_vc_status("gh", ["gh", "auth", "status"], agent.config.workspace)
        return True
    if head == "/vercel":
        _gh_or_vc_status("vercel", ["vercel", "whoami"], agent.config.workspace)
        return True
    if head == "/deps":
        _print_deps()
        return True

    ui.error(f"unknown command: {head} — type /help")
    return True


# ── REPL with bottom status toolbar ─────────────────────────────────────
def _build_session(agent: Agent) -> PromptSession:
    def toolbar():
        p = PROVIDERS[agent.config.provider]
        mode = '<bypass>BYPASS</bypass>' if agent.config.bypass_permissions else '<ask>ASK</ask>'
        stream = "stream" if agent.config.stream else "no-stream"
        ws = str(agent.config.workspace)
        if len(ws) > 40:
            ws = "…" + ws[-39:]
        return HTML(
            f' <b>{p.label}</b> · <model>{agent.config.model}</model>'
            f' · <ws>{ws}</ws>'
            f' · {mode} · <stream>{stream}</stream>'
            f' · <dim>/help</dim>'
        )

    style = Style.from_dict({
        "bottom-toolbar": "bg:#1a1917 #e7e3d8",
        "bottom-toolbar.text": "bg:#1a1917 #e7e3d8",
        "bottom-toolbar bypass": "bg:#1a1917 #f87171 bold",
        "bottom-toolbar ask": "bg:#1a1917 #7da062 bold",
        "bottom-toolbar model": "bg:#1a1917 #c79a52",
        "bottom-toolbar ws": "bg:#1a1917 #9a958a",
        "bottom-toolbar stream": "bg:#1a1917 #9a958a",
        "bottom-toolbar dim": "bg:#1a1917 #9a958a",
        "prompt": "#c79a52 bold",
    })

    return PromptSession(
        history=FileHistory(str(_history_path())),
        bottom_toolbar=toolbar,
        style=style,
        refresh_interval=0.5,
    )


def _repl(agent: Agent) -> None:
    p = PROVIDERS[agent.config.provider]
    ui.banner(p.label, agent.config.model, agent.config.workspace,
              bypass=agent.config.bypass_permissions)
    if agent.config.bypass_permissions:
        ui.warn("BYPASS MODE active — destructive tools run without confirmation.")
    ui.info("type /help for commands · ctrl-d to exit")

    session = _build_session(agent)
    while True:
        try:
            line = session.prompt(HTML('<prompt>›</prompt> '))
        except (EOFError, KeyboardInterrupt):
            ui.info("bye.")
            return
        line = line.strip()
        if not line:
            continue
        if line.startswith("/"):
            try:
                if _handle_slash(line, agent):
                    continue
            except EOFError:
                ui.info("bye.")
                return
        try:
            agent.turn(line)
        except KeyboardInterrupt:
            ui.info("(interrupted)")
        except Exception as e:  # noqa: BLE001
            ui.error(str(e))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="freeagent",
        description="FreeAgent — an open-source terminal coding agent.",
    )
    parser.add_argument("-p", "--prompt", help="Run a single prompt and exit.")
    parser.add_argument("-C", "--cwd", help="Workspace dir (default: cwd).")
    parser.add_argument("--provider", help="Provider id.")
    parser.add_argument("--model", help="Model id.")
    parser.add_argument("--no-stream", action="store_true", help="Disable token streaming.")
    parser.add_argument("--verbose", action="store_true",
                        help="Always print full tool output.")
    parser.add_argument(
        "--dangerously-skip-permissions", "--yolo",
        dest="bypass", action="store_true",
        help="Run destructive tools without prompting (bash, write_file, edit_file, deploys).",
    )
    parser.add_argument("--list-models", action="store_true")
    parser.add_argument("--list-providers", action="store_true")
    parser.add_argument("--list-keys", action="store_true",
                        help="Show which provider keys are configured.")
    parser.add_argument("--deps", action="store_true",
                        help="Check gh / vercel / git availability.")
    parser.add_argument("--version", action="version", version=f"freeagent {__version__}")
    args = parser.parse_args(argv)

    if args.list_providers:
        for p in PROVIDERS.values():
            print(f"{p.id:11}  {p.tier:6}  {p.label}  —  {p.description}")
        return 0
    if args.list_models:
        for m in CATALOG:
            print(f"{m.tier:6}  {m.provider:11}  {m.model:42}  {m.notes}")
        return 0
    if args.list_keys:
        _print_keys()
        return 0
    if args.deps:
        _print_deps()
        return 0

    try:
        config = Config.load(
            workspace=Path(args.cwd) if args.cwd else None,
            provider=args.provider,
            model=args.model,
            bypass_permissions=args.bypass,
        )
        if args.no_stream:
            config.stream = False
        agent = Agent(config, verbose=args.verbose)
    except Exception as e:  # noqa: BLE001
        ui.error(str(e))
        return 1

    if args.prompt:
        agent.turn(args.prompt)
    else:
        _repl(agent)
    return 0


if __name__ == "__main__":
    sys.exit(main())
