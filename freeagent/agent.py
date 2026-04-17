"""Agent loop — orchestrates tool-calling turns against the LLM."""

from __future__ import annotations

import json
from typing import Any

from . import ui
from .config import Config
from .llm import LLMClient
from .tools import dispatch, schemas


SYSTEM_PROMPT = """You are FreeAgent, an open-source terminal coding agent inspired by Claude Code.

You help developers plan, write, refactor, and ship real software. You have a
workspace (the current working directory) and a set of tools for reading and
modifying it, running shell commands, and integrating with GitHub and Vercel.

Working principles:
- Before editing, read the relevant file so your patch matches what's there.
- Prefer `edit_file` for small surgical changes; use `write_file` for new files.
- Use `bash` for tests, builds, git, gh, vercel, or any other command.
- After a meaningful change, suggest a test or verification step.
- When the user asks to publish or deploy a project, use `github_create_repo`
  and `vercel_deploy` rather than giving manual instructions.
- Be concise. Show your work through tool calls, not narration.
"""



MAX_TURNS = 20


def _args_preview(args: dict[str, Any]) -> str:
    keys = list(args.keys())
    if not keys:
        return ""
    head = keys[0]
    val = str(args[head])
    if len(val) > 60:
        val = val[:60] + "…"
    return f"{head}={val}"


def _tool_call_to_json(tc: Any) -> tuple[str, dict[str, Any], str]:
    """Extract (name, args, id) from an OpenAI tool_call object."""
    name = tc.function.name
    raw = tc.function.arguments or "{}"
    try:
        args = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError:
        args = {}
    return name, args, tc.id


class Agent:
    def __init__(self, config: Config):
        self.config = config
        self.llm = LLMClient(config)
        self.messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.tools = schemas()

    def reset(self) -> None:
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def turn(self, user_text: str) -> None:
        self.messages.append({"role": "user", "content": user_text})

        for _ in range(MAX_TURNS):
            response = self.llm.chat(self.messages, tools=self.tools)
            msg = response.choices[0].message

            assistant_entry: dict[str, Any] = {
                "role": "assistant",
                "content": msg.content or "",
            }
            if msg.tool_calls:
                assistant_entry["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments or "{}",
                        },
                    }
                    for tc in msg.tool_calls
                ]
            self.messages.append(assistant_entry)

            if msg.content:
                ui.assistant(msg.content)

            if not msg.tool_calls:
                return

            for tc in msg.tool_calls:
                name, args, call_id = _tool_call_to_json(tc)
                ui.tool_call(name, _args_preview(args))
                result, ok = dispatch(name, args, self.config.workspace)
                ui.tool_result(name, result, ok=ok)
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": result,
                    }
                )

        ui.info("(reached tool-call limit — pausing)")
