"""Agent loop — streams tokens, gates destructive tools, recovers from API key errors."""

from __future__ import annotations

import json
from typing import Any

from . import ui
from .config import Config, save_key_to_env
from .llm import LLMClient, is_auth_or_quota
from .tools import DESTRUCTIVE, dispatch, schemas


SYSTEM_PROMPT = """You are FreeAgent, an open-source terminal coding agent.

You help developers plan, write, refactor, and ship real software. You operate
inside a workspace (the current working directory) and have tools for reading
and modifying it, running shell commands, and integrating with GitHub and Vercel.

Working principles:
- Read a file before editing it so your patch matches what's actually there.
- Prefer `edit_file` for small surgical changes; use `write_file` for new files.
- Use `bash` for tests, builds, git, gh, vercel.
- After a meaningful change, suggest a test or verification step.
- When the user asks to publish or deploy, use `github_create_repo` and
  `vercel_deploy` rather than printing manual instructions.
- Be concise. Show your work through tool calls, not narration.
"""


MAX_TURNS = 24


def _args_preview(args: dict[str, Any]) -> str:
    if not args:
        return ""
    head = next(iter(args))
    val = str(args[head])
    if len(val) > 80:
        val = val[:80] + "…"
    return f"{head}={val}"


def _summarize_result(name: str, body: str, ok: bool) -> str | None:
    """Compact one-liner for the ⎿ continuation."""
    if not ok:
        return None
    if name == "read_file":
        n = len(body.splitlines())
        return f"read {n} line{'s' if n != 1 else ''}"
    if name == "write_file":
        return body.strip().replace("\n", " ")[:120]
    if name == "edit_file":
        return body.strip().replace("\n", " ")[:120]
    if name == "list_dir":
        n = len(body.splitlines())
        return f"{n} entr{'ies' if n != 1 else 'y'}"
    if name == "grep":
        n = len(body.splitlines())
        return f"{n} match{'es' if n != 1 else ''}"
    if name == "bash":
        first = body.splitlines()[0] if body else ""
        return first[:120]
    return None


class Agent:
    def __init__(self, config: Config, verbose: bool = False):
        self.config = config
        self.llm = LLMClient(config)
        self.verbose = verbose
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        self.tools = schemas()

    def reset(self) -> None:
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def reload_client(self) -> None:
        self.llm = LLMClient(self.config)

    # ── permission gate ────────────────────────────────────────────────
    def _permitted(self, name: str, args: dict[str, Any]) -> tuple[bool, str]:
        if name not in DESTRUCTIVE:
            return True, ""
        if self.config.bypass_permissions:
            return True, ""
        if name in self.config.always_allow:
            return True, ""
        decision = ui.request_permission(name, _args_preview(args))
        if decision == "allow_session":
            self.config.always_allow.add(name)
            return True, ""
        if decision == "allow_once":
            return True, ""
        return False, "denied by user"

    # ── key recovery ───────────────────────────────────────────────────
    def _recover_key(self, exc: BaseException) -> bool:
        p = self.config.preset()
        ui.warn(f"{type(exc).__name__}: {exc}")
        new_key = ui.prompt_for_new_key(p.label, p.env_key or "API_KEY", p.signup)
        if not new_key:
            return False
        self.config.api_key = new_key
        try:
            self.reload_client()
        except Exception as e:  # noqa: BLE001
            ui.error(str(e))
            return False
        if p.env_key and ui.ask_save_key():
            path = save_key_to_env(p.env_key, new_key)
            ui.info(f"saved {p.env_key} → {path}")
        return True

    # ── main turn ──────────────────────────────────────────────────────
    def turn(self, user_text: str) -> None:
        self.messages.append({"role": "user", "content": user_text})

        for _ in range(MAX_TURNS):
            stream_started = {"v": False}

            def on_token(t: str) -> None:
                if not stream_started["v"]:
                    ui.assistant_open()
                    stream_started["v"] = True
                ui.stream_token(t)

            try:
                if self.config.stream:
                    turn = self.llm.stream(self.messages, tools=self.tools, on_token=on_token)
                    if stream_started["v"]:
                        ui.assistant_close()
                    content = turn.content
                    tool_calls = turn.tool_calls
                else:
                    resp = self.llm.chat(self.messages, tools=self.tools)
                    msg = resp.choices[0].message
                    content = msg.content or ""
                    if content:
                        ui.assistant(content)
                    tool_calls = []
                    if msg.tool_calls:
                        for tc in msg.tool_calls:
                            tool_calls.append(
                                {
                                    "id": tc.id,
                                    "type": "function",
                                    "function": {
                                        "name": tc.function.name,
                                        "arguments": tc.function.arguments or "{}",
                                    },
                                }
                            )
            except BaseException as e:
                if is_auth_or_quota(e):
                    if stream_started["v"]:
                        ui.assistant_close()
                    if self._recover_key(e):
                        continue  # retry this same turn with the new key
                ui.error(str(e))
                return

            assistant_entry: dict[str, Any] = {"role": "assistant", "content": content}
            if tool_calls:
                assistant_entry["tool_calls"] = tool_calls
            self.messages.append(assistant_entry)

            if not tool_calls:
                return

            for tc in tool_calls:
                name = tc["function"]["name"]
                raw = tc["function"]["arguments"] or "{}"
                try:
                    args = json.loads(raw)
                except json.JSONDecodeError:
                    args = {}

                ui.tool_call(name, _args_preview(args))

                allowed, reason = self._permitted(name, args)
                if not allowed:
                    ui.tool_result(name, reason, ok=False, verbose=self.verbose)
                    self.messages.append(
                        {"role": "tool", "tool_call_id": tc["id"], "content": reason}
                    )
                    continue

                result, ok = dispatch(name, args, self.config.workspace)
                ui.tool_result(
                    name, result, ok=ok,
                    summary=_summarize_result(name, result, ok),
                    verbose=self.verbose,
                )
                self.messages.append(
                    {"role": "tool", "tool_call_id": tc["id"], "content": result}
                )

        ui.info("(reached tool-call limit — pausing)")
