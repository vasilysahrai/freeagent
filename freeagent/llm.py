"""Thin wrapper over the OpenAI-compatible z.ai chat completions API."""

from __future__ import annotations

from typing import Any, Iterable

from openai import OpenAI

from .config import Config


class LLMClient:
    def __init__(self, config: Config):
        config.require_key()
        self.config = config
        self.client = OpenAI(api_key=config.api_key, base_url=config.base_url)

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
        return self.client.chat.completions.create(**kwargs)
