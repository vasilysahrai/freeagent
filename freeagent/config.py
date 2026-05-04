"""Runtime configuration: provider catalog (free vs paid), API keys, workspace."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class ModelEntry:
    provider: str
    model: str
    label: str
    tier: str  # "free" | "paid" | "local"
    notes: str = ""


@dataclass(frozen=True)
class ProviderPreset:
    id: str
    label: str
    base_url: str
    env_key: str | None
    needs_key: bool
    signup: str
    default_model: str
    description: str
    tier: str  # "free" | "paid" | "local" | "mixed"


PROVIDERS: dict[str, ProviderPreset] = {
    "zai": ProviderPreset(
        id="zai",
        label="z.ai",
        base_url="https://api.z.ai/api/paas/v4",
        env_key="ZAI_API_KEY",
        needs_key=True,
        signup="https://z.ai",
        default_model="glm-4.5-flash",
        description="GLM family. The flash variant is free; larger GLMs are pay-per-token.",
        tier="mixed",
    ),
    "groq": ProviderPreset(
        id="groq",
        label="Groq",
        base_url="https://api.groq.com/openai/v1",
        env_key="GROQ_API_KEY",
        needs_key=True,
        signup="https://console.groq.com/keys",
        default_model="llama-3.3-70b-versatile",
        description="Free tier with rate limits. Very fast inference on Llama, Qwen, DeepSeek.",
        tier="free",
    ),
    "openrouter": ProviderPreset(
        id="openrouter",
        label="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        env_key="OPENROUTER_API_KEY",
        needs_key=True,
        signup="https://openrouter.ai/keys",
        default_model="deepseek/deepseek-r1:free",
        description="Hundreds of models. Many `:free` routes have no per-token cost.",
        tier="mixed",
    ),
    "ollama": ProviderPreset(
        id="ollama",
        label="Ollama (local)",
        base_url="http://localhost:11434/v1",
        env_key=None,
        needs_key=False,
        signup="https://ollama.com/download",
        default_model="qwen2.5-coder:7b",
        description="Runs models on your own machine. No key, no network, no per-token cost.",
        tier="local",
    ),
    "openai": ProviderPreset(
        id="openai",
        label="OpenAI",
        base_url="https://api.openai.com/v1",
        env_key="OPENAI_API_KEY",
        needs_key=True,
        signup="https://platform.openai.com/api-keys",
        default_model="gpt-4o-mini",
        description="GPT-4o, GPT-5, o-series. Pay-per-token.",
        tier="paid",
    ),
    "anthropic": ProviderPreset(
        id="anthropic",
        label="Anthropic",
        base_url="https://api.anthropic.com/v1/",
        env_key="ANTHROPIC_API_KEY",
        needs_key=True,
        signup="https://console.anthropic.com/settings/keys",
        default_model="claude-sonnet-4-5",
        description="Claude Opus and Sonnet via Anthropic's OpenAI-compatible endpoint.",
        tier="paid",
    ),
    "google": ProviderPreset(
        id="google",
        label="Google Gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        env_key="GEMINI_API_KEY",
        needs_key=True,
        signup="https://aistudio.google.com/app/apikey",
        default_model="gemini-2.5-flash",
        description="Gemini 2.x via Google's OpenAI-compatible endpoint. Free tier with quotas.",
        tier="mixed",
    ),
    "xai": ProviderPreset(
        id="xai",
        label="xAI",
        base_url="https://api.x.ai/v1",
        env_key="XAI_API_KEY",
        needs_key=True,
        signup="https://console.x.ai",
        default_model="grok-3-mini",
        description="Grok models. Pay-per-token.",
        tier="paid",
    ),
    "mistral": ProviderPreset(
        id="mistral",
        label="Mistral",
        base_url="https://api.mistral.ai/v1",
        env_key="MISTRAL_API_KEY",
        needs_key=True,
        signup="https://console.mistral.ai/api-keys",
        default_model="mistral-large-latest",
        description="Mistral Large, Codestral, etc.",
        tier="paid",
    ),
}


CATALOG: list[ModelEntry] = [
    # ── Free / no per-token cost ──────────────────────────────────────────
    ModelEntry("zai", "glm-4.5-flash", "GLM-4.5 Flash", "free",
               "z.ai's free tier. Tool calls supported. Good default."),
    ModelEntry("groq", "llama-3.3-70b-versatile", "Llama 3.3 70B", "free",
               "Groq free tier. Very fast. Tool calls supported."),
    ModelEntry("groq", "deepseek-r1-distill-llama-70b", "DeepSeek R1 distill 70B", "free",
               "Groq free tier. Reasoning model."),
    ModelEntry("groq", "qwen-qwq-32b", "Qwen QwQ 32B", "free",
               "Groq free tier. Reasoning."),
    ModelEntry("openrouter", "deepseek/deepseek-r1:free", "DeepSeek R1 (free route)", "free",
               "Free OpenRouter route. Strong reasoning."),
    ModelEntry("openrouter", "meta-llama/llama-3.3-70b-instruct:free", "Llama 3.3 70B (free route)", "free",
               "Free OpenRouter route."),
    ModelEntry("openrouter", "google/gemma-2-9b-it:free", "Gemma 2 9B (free route)", "free",
               "Free OpenRouter route. Lightweight."),
    ModelEntry("google", "gemini-2.5-flash", "Gemini 2.5 Flash", "free",
               "Google AI Studio free quota. Tool calls supported."),

    # ── Local (zero cost, your hardware) ──────────────────────────────────
    ModelEntry("ollama", "qwen2.5-coder:7b", "Qwen2.5 Coder 7B", "local",
               "~5 GB. Runs on most laptops with 16 GB RAM."),
    ModelEntry("ollama", "qwen2.5-coder:32b", "Qwen2.5 Coder 32B", "local",
               "~20 GB. 32 GB+ unified memory or a 24 GB GPU."),
    ModelEntry("ollama", "llama3.1:8b", "Llama 3.1 8B", "local",
               "~5 GB. Solid generalist."),
    ModelEntry("ollama", "deepseek-r1:7b", "DeepSeek R1 7B", "local",
               "~5 GB. Reasoning at home."),

    # ── Paid frontier ─────────────────────────────────────────────────────
    ModelEntry("openai", "gpt-4o-mini", "GPT-4o mini", "paid",
               "Cheap, fast, capable."),
    ModelEntry("openai", "gpt-4o", "GPT-4o", "paid",
               "OpenAI's flagship multimodal."),
    ModelEntry("openai", "gpt-5", "GPT-5", "paid",
               "OpenAI's frontier model. Pricier."),
    ModelEntry("anthropic", "claude-sonnet-4-5", "Claude Sonnet 4.5", "paid",
               "Excellent for code. Strong tool use."),
    ModelEntry("anthropic", "claude-opus-4-5", "Claude Opus 4.5", "paid",
               "Anthropic's strongest. Best on hard refactors."),
    ModelEntry("google", "gemini-2.5-pro", "Gemini 2.5 Pro", "paid",
               "Long-context frontier model."),
    ModelEntry("xai", "grok-3", "Grok 3", "paid",
               "xAI's frontier. Pay-per-token."),
    ModelEntry("mistral", "mistral-large-latest", "Mistral Large", "paid",
               "European frontier. Codestral too."),
    ModelEntry("zai", "glm-4.6", "GLM-4.6", "paid",
               "z.ai's larger, paid model. Better reasoning than flash."),
]


DEFAULT_PROVIDER = "zai"


def env_path() -> Path:
    """Path to the persistent dotenv file we own (~/.freeagent/.env)."""
    p = Path.home() / ".freeagent"
    p.mkdir(parents=True, exist_ok=True)
    return p / ".env"


@dataclass
class Config:
    provider: str
    api_key: str
    base_url: str
    model: str
    workspace: Path
    stream: bool = True
    bypass_permissions: bool = False
    always_allow: set[str] = field(default_factory=set)

    @classmethod
    def load(
        cls,
        workspace: Path | None = None,
        provider: str | None = None,
        model: str | None = None,
        bypass_permissions: bool = False,
    ) -> "Config":
        load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)
        load_dotenv(dotenv_path=env_path(), override=False)

        prov_id = (provider or os.getenv("FREEAGENT_PROVIDER", DEFAULT_PROVIDER)).lower().strip()
        if prov_id not in PROVIDERS:
            raise RuntimeError(
                f"Unknown provider {prov_id!r}. Choices: {', '.join(PROVIDERS)}."
            )
        preset = PROVIDERS[prov_id]

        base_url = os.getenv("FREEAGENT_BASE_URL") or preset.base_url
        chosen_model = model or os.getenv("FREEAGENT_MODEL") or preset.default_model

        api_key = ""
        if preset.env_key:
            api_key = os.getenv(preset.env_key, "")
        if not api_key and not preset.needs_key:
            api_key = "local-no-key"

        ws = (workspace or Path.cwd()).resolve()
        stream = os.getenv("FREEAGENT_STREAM", "1").lower() not in ("0", "false", "no")

        return cls(
            provider=prov_id,
            api_key=api_key,
            base_url=base_url,
            model=chosen_model,
            workspace=ws,
            stream=stream,
            bypass_permissions=bypass_permissions,
        )

    def preset(self) -> ProviderPreset:
        return PROVIDERS[self.provider]

    def require_key(self) -> None:
        p = self.preset()
        if not p.needs_key:
            return
        if self.api_key and self.api_key != "local-no-key":
            return
        env_key = p.env_key or "API_KEY"
        raise RuntimeError(
            f"No API key for provider {p.label!r}. "
            f"Set {env_key} in your environment or run /key <value> in the REPL. "
            f"Sign up at {p.signup}."
        )


def models_for(provider_id: str) -> list[ModelEntry]:
    return [m for m in CATALOG if m.provider == provider_id]


def detected_keys() -> list[tuple[str, bool]]:
    """For each provider that needs a key, report (provider_id, has_key)."""
    out: list[tuple[str, bool]] = []
    for pid, p in PROVIDERS.items():
        if not p.needs_key:
            out.append((pid, True))
            continue
        out.append((pid, bool(os.getenv(p.env_key or "", ""))))
    return out


def save_key_to_env(env_key: str, value: str) -> Path:
    """Persist or replace `env_key=value` in ~/.freeagent/.env. Returns the path."""
    path = env_path()
    lines: list[str] = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
    found = False
    for i, line in enumerate(lines):
        stripped = line.lstrip("# ").strip()
        if stripped.startswith(f"{env_key}="):
            lines[i] = f"{env_key}={value}"
            found = True
            break
    if not found:
        if lines and lines[-1].strip() != "":
            lines.append("")
        lines.append(f"{env_key}={value}")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path
