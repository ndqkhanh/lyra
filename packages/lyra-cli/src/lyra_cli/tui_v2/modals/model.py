"""ModelPicker — choose an LLM provider/model.

Lists every provider Lyra supports, marks the ones whose API key is
configured (via ``provider_has_credentials``), and previews the env
var Lyra reads for each. The returned key is a ``build_llm(...)``-
compatible argument — passing it straight to harness-tui's ``/model``
handler or the legacy CLI flag gives the same effect.
"""
from __future__ import annotations

from ...llm_factory import provider_env_var, provider_has_credentials
from .base import Entry, LyraPickerModal


# Canonical provider catalogue. Mirrors ``_AUTHJSON_PROVIDER_TO_ENV`` in
# ``llm_factory`` plus the three credential-free local backends. When a
# new provider lands in llm_factory, add it here too — the test asserts
# both lists stay in sync.
PROVIDERS: tuple[str, ...] = (
    "auto",
    "anthropic",
    "openai",
    "openai-reasoning",
    "gemini",
    "deepseek",
    "qwen",
    "dashscope",
    "xai",
    "groq",
    "cerebras",
    "mistral",
    "openrouter",
    "copilot",
    "ollama",
    "lmstudio",
    "mock",
)


_LABELS = {
    "auto": "auto · best configured backend",
    "anthropic": "Anthropic (Claude)",
    "openai": "OpenAI",
    "openai-reasoning": "OpenAI Reasoning",
    "gemini": "Google Gemini",
    "deepseek": "DeepSeek",
    "qwen": "Qwen / DashScope",
    "dashscope": "DashScope",
    "xai": "xAI Grok",
    "groq": "Groq",
    "cerebras": "Cerebras",
    "mistral": "Mistral",
    "openrouter": "OpenRouter",
    "copilot": "GitHub Copilot",
    "ollama": "Ollama (local)",
    "lmstudio": "LM Studio (local)",
    "mock": "mock · scripted fixtures",
}


def model_entries(current: str = "") -> list[Entry]:
    """Return the picker rows. Pure — testable without Textual."""
    return [_build_entry(p, current=current) for p in PROVIDERS]


class ModelPicker(LyraPickerModal):
    picker_title = "Switch model · pick a provider"

    def __init__(self, current: str = "") -> None:
        self._current = current
        super().__init__()

    def entries(self) -> list[Entry]:
        return model_entries(self._current)


# ---------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------


def _build_entry(key: str, *, current: str) -> Entry:
    env_var = provider_env_var(key)
    configured = provider_has_credentials(key) if key != "auto" else True

    bullet = "●" if key == current else " "
    badge = "[green]✓[/]" if configured else "[dim]·[/]"
    label = f"{bullet} {badge} {_LABELS.get(key, key.title())}"

    meta: dict[str, str] = {"provider": key}
    if env_var is None:
        meta["auth"] = "none required"
    else:
        meta["env var"] = env_var
        meta["configured"] = "yes" if configured else "no"

    description = _describe(key, env_var=env_var, configured=configured)
    return Entry(key=key, label=label, description=description, meta=meta)


def _describe(key: str, *, env_var: str | None, configured: bool) -> str:
    if key == "auto":
        return (
            "Lyra picks the best-configured backend at runtime\n"
            "(DeepSeek → Anthropic → OpenAI → Gemini → …)."
        )
    if env_var is None:
        return f"{_LABELS.get(key, key)} — no API key required."
    if configured:
        return f"{env_var} is set — ready to use."
    return (
        f"[yellow]No {env_var} configured.[/]\n"
        f"Add the key via [bold]lyra setup[/] or export\n"
        f"{env_var}=… before switching to this provider."
    )
