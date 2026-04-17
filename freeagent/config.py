"""Runtime configuration — API keys, model choice, workspace paths."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_MODEL = "glm-4.5-flash"
DEFAULT_BASE_URL = "https://api.z.ai/api/paas/v4"


@dataclass
class Config:
    api_key: str
    base_url: str
    model: str
    workspace: Path

    @classmethod
    def load(cls, workspace: Path | None = None) -> "Config":
        load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)
        load_dotenv(dotenv_path=Path.home() / ".freeagent" / ".env", override=False)

        api_key = os.getenv("ZAI_API_KEY") or os.getenv("Z_API_KEY") or ""
        base_url = os.getenv("ZAI_BASE_URL", DEFAULT_BASE_URL)
        model = os.getenv("FREEAGENT_MODEL", DEFAULT_MODEL)
        ws = (workspace or Path.cwd()).resolve()

        return cls(api_key=api_key, base_url=base_url, model=model, workspace=ws)

    def require_key(self) -> None:
        if not self.api_key:
            raise RuntimeError(
                "No z.ai API key found. Set ZAI_API_KEY in your environment or "
                "in a .env file. Get a free key at https://z.ai."
            )
