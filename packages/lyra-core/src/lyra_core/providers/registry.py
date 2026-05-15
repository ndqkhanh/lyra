"""Canonical LLM provider metadata.

The registry is a pure-data module — no imports of concrete HTTP
clients — so it's safe to query at startup or from tests that don't
want to pay import cost for every provider adapter. The actual
``LLMProvider`` instances live in ``lyra_cli.providers``; this
registry only describes them.

Context-window numbers track each provider's best publicly-documented
model. They're informative, not authoritative — the CLI does not
refuse requests based on these values, but planners can use them to
pick a model with enough room for a given task.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ProviderKey = Literal[
    "openai",
    "openai-reasoning",
    "anthropic",
    "gemini",
    "deepseek",
    "xai",
    "groq",
    "cerebras",
    "mistral",
    "openrouter",
    "lmstudio",
    "ollama",
    "mock",
]


@dataclass(frozen=True)
class ProviderSpec:
    """Static description of one LLM provider."""

    key: str
    display_name: str
    env_vars: tuple[str, ...] = ()
    default_model: str = ""
    context_window: int = 0
    supports_tools: bool = False
    supports_reasoning: bool = False
    supports_streaming: bool = True
    supports_vision: bool = False
    notes: str = ""
    models: tuple[str, ...] = field(default_factory=tuple)


PROVIDER_REGISTRY: tuple[ProviderSpec, ...] = (
    ProviderSpec(
        key="anthropic",
        display_name="Anthropic Claude",
        env_vars=("ANTHROPIC_API_KEY",),
        default_model="claude-opus-4.5",
        context_window=200_000,
        supports_tools=True,
        supports_reasoning=True,
        supports_vision=True,
        models=("claude-opus-4.5", "claude-sonnet-4.5", "claude-haiku-4"),
    ),
    ProviderSpec(
        key="openai",
        display_name="OpenAI GPT",
        env_vars=("OPENAI_API_KEY",),
        default_model="gpt-4o",
        context_window=128_000,
        supports_tools=True,
        supports_reasoning=False,
        supports_vision=True,
        models=("gpt-4o", "gpt-4o-mini", "gpt-5", "gpt-5-mini"),
    ),
    ProviderSpec(
        key="openai-reasoning",
        display_name="OpenAI o-series (reasoning)",
        env_vars=("OPENAI_API_KEY",),
        default_model="o3-mini",
        context_window=128_000,
        supports_tools=True,
        supports_reasoning=True,
        models=("o3", "o3-mini", "o1", "o1-mini"),
    ),
    ProviderSpec(
        key="gemini",
        display_name="Google Gemini",
        env_vars=("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        default_model="gemini-2.5-pro",
        context_window=2_000_000,
        supports_tools=True,
        supports_reasoning=True,
        supports_vision=True,
        models=("gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite"),
    ),
    ProviderSpec(
        key="deepseek",
        display_name="DeepSeek",
        env_vars=("DEEPSEEK_API_KEY",),
        default_model="deepseek-chat",
        context_window=128_000,
        supports_tools=True,
        supports_reasoning=True,
        models=("deepseek-chat", "deepseek-coder", "deepseek-reasoner"),
    ),
    ProviderSpec(
        key="xai",
        display_name="xAI Grok",
        env_vars=("XAI_API_KEY",),
        default_model="grok-4",
        context_window=256_000,
        supports_tools=True,
        supports_reasoning=False,
        models=("grok-4", "grok-code-fast-1"),
    ),
    ProviderSpec(
        key="groq",
        display_name="Groq",
        env_vars=("GROQ_API_KEY",),
        default_model="llama-3.3-70b-versatile",
        context_window=128_000,
        supports_tools=True,
        notes="Fast inference; good for chat.",
        models=(
            "llama-3.3-70b-versatile",
            "kimi-k2",
            "qwen-3-coder",
            "qwen-3-30b",
        ),
    ),
    ProviderSpec(
        key="cerebras",
        display_name="Cerebras",
        env_vars=("CEREBRAS_API_KEY",),
        default_model="llama3.3-70b",
        context_window=128_000,
        supports_tools=True,
        notes="Ultra-low latency host for Llama/Qwen.",
        models=("llama3.3-70b", "qwen-3-32b", "qwen-3-coder"),
    ),
    ProviderSpec(
        key="mistral",
        display_name="Mistral",
        env_vars=("MISTRAL_API_KEY",),
        default_model="codestral-latest",
        context_window=256_000,
        supports_tools=True,
        models=("codestral-latest", "mistral-large-latest", "mistral-medium"),
    ),
    ProviderSpec(
        key="openrouter",
        display_name="OpenRouter",
        env_vars=("OPENROUTER_API_KEY",),
        default_model="openrouter/auto",
        context_window=200_000,
        supports_tools=True,
        supports_reasoning=True,
        notes="Meta-provider routing to 300+ upstream models.",
        models=("openrouter/auto",),
    ),
    ProviderSpec(
        key="lmstudio",
        display_name="LM Studio (local OpenAI-compatible server)",
        env_vars=(),
        default_model="",
        context_window=32_768,
        supports_tools=True,
        notes="Probed locally at http://localhost:1234/v1.",
    ),
    ProviderSpec(
        key="ollama",
        display_name="Ollama (local)",
        env_vars=(),
        default_model="llama3.2",
        context_window=8_192,
        supports_tools=True,
        notes="Runs on 127.0.0.1:11434; no API key required.",
        models=("llama3.2", "qwen2.5-coder", "mistral"),
    ),
    ProviderSpec(
        key="mock",
        display_name="Mock (deterministic tests)",
        env_vars=(),
        default_model="mock-1",
        context_window=8_192,
        supports_tools=True,
        notes="In-process scripted provider used by the test harness.",
    ),
)


def get_provider(key: str) -> ProviderSpec | None:
    """Return the spec for ``key`` (case-insensitive) or ``None``."""
    norm = (key or "").strip().lower()
    for spec in PROVIDER_REGISTRY:
        if spec.key.lower() == norm:
            return spec
    return None


def providers_by_capability(
    *,
    tools: bool | None = None,
    reasoning: bool | None = None,
    vision: bool | None = None,
    min_context_window: int | None = None,
) -> list[ProviderSpec]:
    """Filter providers by capability flags."""
    out: list[ProviderSpec] = []
    for spec in PROVIDER_REGISTRY:
        if tools is not None and spec.supports_tools != tools:
            continue
        if reasoning is not None and spec.supports_reasoning != reasoning:
            continue
        if vision is not None and spec.supports_vision != vision:
            continue
        if min_context_window is not None and spec.context_window < min_context_window:
            continue
        out.append(spec)
    return out


# ---------------------------------------------------------------------------
# Model max-output-tokens (for context-window preflight + plugin override)
# ---------------------------------------------------------------------------
#
# claw-code parity: plugin config `plugins.maxOutputTokens` in
# `~/.lyra/settings.json` (or `$LYRA_HOME/settings.json` when set)
# wins over per-model defaults. The defaults below intentionally match
# the order-of-magnitude claw-code uses so users migrating between the
# two feel no surprise.
#
# A value of ``None`` means "use the model's registered default";
# non-positive values raise to prevent pathological 0-token responses.
import json as _json
import os as _os
from pathlib import Path as _Path


_PER_MODEL_MAX_OUTPUT: dict[str, int] = {
    "claude-opus-4.5": 32_000,
    "claude-sonnet-4.5": 64_000,
    "claude-haiku-4": 64_000,
    "gpt-5": 128_000,
    "gpt-4o": 16_000,
    "gpt-4o-mini": 16_000,
    "o3-mini": 100_000,
    "gemini-2.5-pro": 64_000,
    "gemini-2.5-flash": 64_000,
    "deepseek-chat": 8_000,
    "deepseek-reasoner": 16_000,
    "grok-4": 64_000,
    "grok-4-mini": 64_000,
    "grok-3": 64_000,
    "grok-3-mini": 64_000,
    "kimi-k2.5": 16_384,
    "kimi-k1.5": 16_384,
    "llama-3.3-70b-versatile": 8_192,
}


def max_tokens_for_model(model: str) -> int:
    """Return the registered max output for *model* (safe fallback)."""
    if model in _PER_MODEL_MAX_OUTPUT:
        return _PER_MODEL_MAX_OUTPUT[model]
    return 32_000 if "opus" in model.lower() else 64_000


def max_tokens_for_model_with_override(
    model: str,
    plugin_override: int | None,
) -> int:
    """Plugin override wins over the registered default.

    ``None`` falls back to :func:`max_tokens_for_model`. Zero or
    negative values raise :class:`ValueError` because they would
    guarantee an empty completion.
    """
    if plugin_override is None:
        return max_tokens_for_model(model)
    if plugin_override <= 0:
        raise ValueError(
            f"plugin maxOutputTokens must be > 0, got {plugin_override}"
        )
    return plugin_override


def _lyra_home() -> _Path:
    """Resolve the Lyra config home directory.

    Honours ``LYRA_HOME`` (useful for tests + multi-tenant hosts),
    otherwise defaults to ``~/.lyra``. Creation is NOT attempted here —
    callers expect ``None`` when the config file is missing.
    """
    raw = _os.environ.get("LYRA_HOME", "").strip()
    if raw:
        return _Path(raw)
    return _Path.home() / ".lyra"


def plugin_max_output_tokens() -> int | None:
    """Read ``plugins.maxOutputTokens`` from ``settings.json``.

    Returns ``None`` when (a) the file is missing, (b) malformed JSON,
    (c) the key is absent, or (d) the value isn't a positive int.
    Every failure mode is a benign "fall back to model default", not
    an exception — misconfiguring the file shouldn't break every
    invocation.
    """
    try:
        body = (_lyra_home() / "settings.json").read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    try:
        data = _json.loads(body)
    except _json.JSONDecodeError:
        return None
    plugins = data.get("plugins") if isinstance(data, dict) else None
    if not isinstance(plugins, dict):
        return None
    val = plugins.get("maxOutputTokens")
    if isinstance(val, int) and val > 0:
        return val
    return None


def provider_routing_for(provider_name: str) -> dict | None:
    """Read ``provider_routing.<name>`` from ``settings.json``.

    Returns the matching ``dict`` (suitable for forwarding into
    ``ProviderRouting(**...)``) or ``None`` when the file is missing,
    malformed, or has no entry for ``provider_name``. Honours the same
    ``LYRA_HOME`` override as :func:`plugin_max_output_tokens`.

    The CLI uses this to inject OpenRouter-style routing knobs at
    preset-build time without baking them into source — users tune
    ``sort`` / ``only`` / ``ignore`` / ``order`` / ``require_parameters``
    / ``data_collection`` in ``~/.lyra/settings.json`` and the next
    invocation picks them up automatically.

    Example ``~/.lyra/settings.json``::

        {
          "provider_routing": {
            "openrouter": {
              "sort": "price",
              "only": ["openai", "anthropic"],
              "data_collection": "deny"
            }
          }
        }
    """
    if not provider_name:
        return None
    try:
        body = (_lyra_home() / "settings.json").read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    try:
        data = _json.loads(body)
    except _json.JSONDecodeError:
        return None
    routing_section = data.get("provider_routing") if isinstance(data, dict) else None
    if not isinstance(routing_section, dict):
        return None
    entry = routing_section.get(provider_name)
    if not isinstance(entry, dict):
        return None
    return entry


__all__ = [
    "PROVIDER_REGISTRY",
    "ProviderSpec",
    "ProviderKey",
    "get_provider",
    "providers_by_capability",
    "max_tokens_for_model",
    "max_tokens_for_model_with_override",
    "plugin_max_output_tokens",
    "provider_routing_for",
]
