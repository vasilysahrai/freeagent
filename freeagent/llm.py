"""Thin wrapper over OpenAI-compatible chat APIs with streaming + retries."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Iterator

from openai import APIConnectionError, APIError, OpenAI, RateLimitError

from .config import Config


@dataclass
class StreamedTurn:
    """Aggregated result of a streamed assistant turn."""
    content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: str | None = None


class LLMClient:
    def __init__(self, config: Config):
        config.require_key()
        self.config = config
        self.client = OpenAI(api_key=config.api_key, base_url=config.base_url)

    # ── streaming ────────────────────────────────────────────────────────
    def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        on_token: callable | None = None,
        temperature: float = 0.3,
    ) -> StreamedTurn:
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        stream = self._with_retry(lambda: self.client.chat.completions.create(**kwargs))

        result = StreamedTurn()
        tcalls: dict[int, dict[str, Any]] = {}
        finish_reason: str | None = None

        for chunk in stream:
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta
            if delta is None:
                continue
            if delta.content:
                result.content += delta.content
                if on_token:
                    on_token(delta.content)
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index if tc.index is not None else 0
                    slot = tcalls.setdefault(
                        idx,
                        {
                            "id": "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        },
                    )
                    if tc.id:
                        slot["id"] = tc.id
                    fn = tc.function
                    if fn:
                        if fn.name:
                            slot["function"]["name"] += fn.name
                        if fn.arguments:
                            slot["function"]["arguments"] += fn.arguments
            if choice.finish_reason:
                finish_reason = choice.finish_reason

        result.tool_calls = [tcalls[k] for k in sorted(tcalls.keys())]
        result.finish_reason = finish_reason
        return result

    # ── non-stream fallback (kept for one-shot, simple checks) ───────────
    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.3,
    ) -> Any:
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        return self._with_retry(lambda: self.client.chat.completions.create(**kwargs))

    @staticmethod
    def _with_retry(fn, attempts: int = 3, base: float = 0.6):
        last: Exception | None = None
        for i in range(attempts):
            try:
                return fn()
            except (RateLimitError, APIConnectionError) as e:
                last = e
                time.sleep(base * (2 ** i))
            except APIError as e:
                last = e
                if 500 <= getattr(e, "status_code", 0) < 600:
                    time.sleep(base * (2 ** i))
                    continue
                raise
        raise last  # type: ignore[misc]
