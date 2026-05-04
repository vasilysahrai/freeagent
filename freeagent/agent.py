"""Agent loop — streams tokens, then dispatches any tool calls and loops."""

from __future__ import annotations

import json
from typing import Any

from . import ui
from .config import Config
from .llm import LLMClient
from .tools import dispatch, schemas


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
    if len(val) > 60:
        val = val[:60] + "…"
    return f"{head}={val}"


class Agent:
    def __init__(self, config: Config):
        self.config = config
        self.llm = LLMClient(config)
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        self.tools = schemas()

    def reset(self) -> None:
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def reload_client(self) -> None:
        """Re-instantiate the LLM client (after a /provider or /model change)."""
        self.llm = LLMClient(self.config)

    def turn(self, user_text: str) -> None:
        self.messages.append({"role": "user", "content": user_text})

        for _ in range(MAX_TURNS):
            stream_started = {"v": False}

            def on_token(t: str) -> None:
                if not stream_started["v"]:
                    ui.assistant_open()
                    stream_started["v"] = True
                ui.stream_token(t)

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
                result, ok = dispatch(name, args, self.config.workspace)
                ui.tool_result(name, result, ok=ok)
                self.messages.append(
                    {"role": "tool", "tool_call_id": tc["id"], "content": result}
                )

        ui.info("(reached tool-call limit — pausing)")
