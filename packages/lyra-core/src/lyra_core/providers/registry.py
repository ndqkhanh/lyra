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
    "anthropic",
    "openai",
    "openai-reasoning",
    "gemini",
    "deepseek",
    "qwen",
    "kimi",
    "xai",
    "groq",
    "cerebras",
    "mistral",
    "openrouter",
    "lmstudio",
    "ollama",
    "bedrock",
    "mock",
]


@dataclass(frozen=True)
class ModelSpec:
    """Description of a single model variant."""

    slug: str
    display_name: str
    description: str = ""
    tags: tuple[str, ...] = ()
    context_window: int = 0
    max_output_tokens: int = 0

    @property
    def is_reasoning(self) -> bool:
        return "reasoning" in self.tags

    @property
    def is_fast(self) -> bool:
        return "fast" in self.tags


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
    models: tuple[ModelSpec, ...] = field(default_factory=tuple)
    icon: str = ""
    website: str = ""
    api_key_url: str = ""


PROVIDER_REGISTRY: tuple[ProviderSpec, ...] = (
    ProviderSpec(
        key="anthropic",
        display_name="Anthropic Claude",
        env_vars=("ANTHROPIC_API_KEY",),
        default_model="claude-opus-4.7",
        context_window=200_000,
        supports_tools=True,
        supports_reasoning=True,
        supports_vision=True,
        icon="🅐",
        website="https://console.anthropic.com/",
        api_key_url="https://console.anthropic.com/settings/keys",
        notes="Creator of Claude — best-in-class coding and reasoning models.",
        models=(
            ModelSpec(
                slug="claude-opus-4.7",
                display_name="Opus 4.7",
                description="Most capable for complex reasoning and architecture work",
                tags=("reasoning",),
                context_window=200_000,
                max_output_tokens=32_000,
            ),
            ModelSpec(
                slug="claude-sonnet-4.6",
                display_name="Sonnet 4.6",
                description="Best for everyday coding tasks",
                tags=("coding",),
                context_window=200_000,
                max_output_tokens=64_000,
            ),
            ModelSpec(
                slug="claude-haiku-4.5",
                display_name="Haiku 4.5",
                description="Fastest for quick answers and simple tasks",
                tags=("fast",),
                context_window=200_000,
                max_output_tokens=64_000,
            ),
        ),
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
        icon="🅞",
        website="https://platform.openai.com/",
        api_key_url="https://platform.openai.com/api-keys",
        notes="Industry-standard models with broad capability.",
        models=(
            ModelSpec(
                slug="gpt-4o",
                display_name="GPT-4o",
                description="Versatile multimodal model with vision support",
                tags=("reasoning",),
                context_window=128_000,
                max_output_tokens=16_000,
            ),
            ModelSpec(
                slug="gpt-4-turbo",
                display_name="GPT-4 Turbo",
                description="Fast reasoning at lower cost than GPT-4o",
                tags=("coding",),
                context_window=128_000,
                max_output_tokens=4_096,
            ),
            ModelSpec(
                slug="gpt-3.5-turbo",
                display_name="GPT-3.5 Turbo",
                description="Economical for simple tasks and classification",
                tags=("fast",),
                context_window=16_385,
                max_output_tokens=4_096,
            ),
        ),
    ),
    ProviderSpec(
        key="openai-reasoning",
        display_name="OpenAI o-series",
        env_vars=("OPENAI_API_KEY",),
        default_model="o3-mini",
        context_window=128_000,
        supports_tools=True,
        supports_reasoning=True,
        icon="🅞",
        website="https://platform.openai.com/",
        api_key_url="https://platform.openai.com/api-keys",
        notes="Chain-of-thought reasoning specialists.",
        models=(
            ModelSpec(
                slug="o3",
                display_name="O3",
                description="Deepest reasoning for complex problems",
                tags=("reasoning",),
                context_window=200_000,
                max_output_tokens=100_000,
            ),
            ModelSpec(
                slug="o3-mini",
                display_name="O3 Mini",
                description="Cost-effective deep reasoning",
                tags=("reasoning",),
                context_window=200_000,
                max_output_tokens=100_000,
            ),
            ModelSpec(
                slug="o1",
                display_name="O1",
                description="Strong reasoning for scientific and technical work",
                tags=("reasoning",),
                context_window=200_000,
                max_output_tokens=100_000,
            ),
        ),
    ),
    ProviderSpec(
        key="gemini",
        display_name="Google Gemini",
        env_vars=("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        default_model="gemini-2.5-pro-preview",
        context_window=2_000_000,
        supports_tools=True,
        supports_reasoning=True,
        supports_vision=True,
        icon="🅖",
        website="https://aistudio.google.com/",
        api_key_url="https://aistudio.google.com/app/apikey",
        notes="Massive 2M context window with strong multimodal capabilities.",
        models=(
            ModelSpec(
                slug="gemini-2.5-pro-preview",
                display_name="Gemini 2.5 Pro",
                description="2M context · Deep reasoning · Strong coding",
                tags=("reasoning",),
                context_window=2_000_000,
                max_output_tokens=64_000,
            ),
            ModelSpec(
                slug="gemini-3.1-pro",
                display_name="Gemini 3.1 Pro",
                description="Latest flagship with enhanced reasoning",
                tags=("reasoning",),
                context_window=2_000_000,
                max_output_tokens=64_000,
            ),
            ModelSpec(
                slug="gemini-2.5-flash",
                display_name="Gemini 2.5 Flash",
                description="Fast, lightweight for high-throughput tasks",
                tags=("fast",),
                context_window=1_000_000,
                max_output_tokens=64_000,
            ),
        ),
    ),
    ProviderSpec(
        key="deepseek",
        display_name="DeepSeek",
        env_vars=("DEEPSEEK_API_KEY",),
        default_model="deepseek-v4-pro",
        context_window=128_000,
        supports_tools=True,
        supports_reasoning=True,
        icon="🅓",
        website="https://platform.deepseek.com/",
        api_key_url="https://platform.deepseek.com/api_keys",
        notes="Strong open-weight reasoning models at competitive pricing.",
        models=(
            ModelSpec(
                slug="deepseek-v4-pro",
                display_name="DeepSeek V4 Pro",
                description="Flagship reasoning model for complex analysis",
                tags=("reasoning",),
                context_window=128_000,
                max_output_tokens=32_000,
            ),
            ModelSpec(
                slug="deepseek-v4-flash",
                display_name="DeepSeek V4 Flash",
                description="Fast, cost-effective for everyday coding",
                tags=("coding", "fast"),
                context_window=128_000,
                max_output_tokens=16_000,
            ),
            ModelSpec(
                slug="deepseek-reasoner",
                display_name="DeepSeek Reasoner",
                description="Dedicated chain-of-thought reasoning model",
                tags=("reasoning",),
                context_window=128_000,
                max_output_tokens=16_000,
            ),
            ModelSpec(
                slug="deepseek-chat",
                display_name="DeepSeek Chat",
                description="General-purpose conversational model",
                tags=("fast",),
                context_window=128_000,
                max_output_tokens=8_000,
            ),
        ),
    ),
    ProviderSpec(
        key="qwen",
        display_name="Alibaba Qwen",
        env_vars=("QWEN_API_KEY", "DASHSCOPE_API_KEY"),
        default_model="qwen-3.7-max",
        context_window=128_000,
        supports_tools=True,
        supports_reasoning=True,
        icon="🅠",
        website="https://dashscope.console.aliyun.com/",
        api_key_url="https://dashscope.console.aliyun.com/apiKey",
        notes="Alibaba's flagship models with strong multilingual support.",
        models=(
            ModelSpec(
                slug="qwen-3.7-max",
                display_name="Qwen 3.7 Max",
                description="Most capable Qwen model for complex tasks",
                tags=("reasoning",),
                context_window=128_000,
                max_output_tokens=8_192,
            ),
            ModelSpec(
                slug="qwen-turbo",
                display_name="Qwen Turbo",
                description="Fast, cost-effective for high-throughput",
                tags=("fast",),
                context_window=128_000,
                max_output_tokens=8_192,
            ),
            ModelSpec(
                slug="qwen-plus",
                display_name="Qwen Plus",
                description="Balanced performance and cost",
                tags=("coding",),
                context_window=128_000,
                max_output_tokens=8_192,
            ),
        ),
    ),
    ProviderSpec(
        key="kimi",
        display_name="Moonshot Kimi",
        env_vars=("KIMI_API_KEY", "MOONSHOT_API_KEY"),
        default_model="kimi-k2.6",
        context_window=128_000,
        supports_tools=True,
        supports_reasoning=True,
        icon="🅚",
        website="https://platform.moonshot.cn/",
        api_key_url="https://platform.moonshot.cn/console/api-keys",
        notes="Moonshot's long-context models with strong Chinese-English bilingual capability.",
        models=(
            ModelSpec(
                slug="kimi-k2.6",
                display_name="Kimi K2.6",
                description="Latest flagship with enhanced reasoning and coding",
                tags=("reasoning", "coding"),
                context_window=128_000,
                max_output_tokens=16_384,
            ),
        ),
    ),
    ProviderSpec(
        key="xai",
        display_name="xAI Grok",
        env_vars=("XAI_API_KEY",),
        default_model="grok-4",
        context_window=256_000,
        supports_tools=True,
        supports_reasoning=False,
        icon="🅧",
        website="https://x.ai/",
        api_key_url="https://console.x.ai/",
        notes="Real-time knowledge with a unique personality.",
        models=(
            ModelSpec(
                slug="grok-4",
                display_name="Grok 4",
                description="xAI's latest flagship model",
                tags=("reasoning",),
                context_window=256_000,
                max_output_tokens=64_000,
            ),
            ModelSpec(
                slug="grok-code-fast-1",
                display_name="Grok Code Fast",
                description="Ultra-fast model optimized for coding",
                tags=("coding", "fast"),
                context_window=256_000,
                max_output_tokens=64_000,
            ),
        ),
    ),
    ProviderSpec(
        key="groq",
        display_name="Groq",
        env_vars=("GROQ_API_KEY",),
        default_model="llama-3.3-70b-versatile",
        context_window=128_000,
        supports_tools=True,
        icon="🅖",
        website="https://console.groq.com/",
        api_key_url="https://console.groq.com/keys",
        notes="Ultra-fast inference for open-weight models.",
        models=(
            ModelSpec(
                slug="llama-3.3-70b-versatile",
                display_name="Llama 3.3 70B",
                description="Versatile open-weight model at high speed",
                tags=("coding",),
                context_window=128_000,
                max_output_tokens=8_192,
            ),
            ModelSpec(
                slug="qwen-3-coder",
                display_name="Qwen 3 Coder",
                description="Code-specialized model on Groq's fast infrastructure",
                tags=("coding", "fast"),
                context_window=128_000,
                max_output_tokens=8_192,
            ),
        ),
    ),
    ProviderSpec(
        key="cerebras",
        display_name="Cerebras",
        env_vars=("CEREBRAS_API_KEY",),
        default_model="llama3.3-70b",
        context_window=128_000,
        supports_tools=True,
        icon="🅒",
        website="https://cloud.cerebras.ai/",
        api_key_url="https://cloud.cerebras.ai/",
        notes="Ultra-low latency host for Llama/Qwen.",
        models=(
            ModelSpec(
                slug="llama3.3-70b",
                display_name="Llama 3.3 70B",
                description="Fast inference on wafer-scale hardware",
                tags=("fast",),
                context_window=128_000,
                max_output_tokens=8_192,
            ),
            ModelSpec(
                slug="qwen-3-32b",
                display_name="Qwen 3 32B",
                description="Balanced performance with fast inference",
                tags=("fast",),
                context_window=128_000,
                max_output_tokens=8_192,
            ),
        ),
    ),
    ProviderSpec(
        key="mistral",
        display_name="Mistral",
        env_vars=("MISTRAL_API_KEY",),
        default_model="codestral-latest",
        context_window=256_000,
        supports_tools=True,
        icon="🅜",
        website="https://console.mistral.ai/",
        api_key_url="https://console.mistral.ai/api-keys/",
        notes="European AI leader with strong coding and multilingual models.",
        models=(
            ModelSpec(
                slug="codestral-latest",
                display_name="Codestral",
                description="Specialized code generation model",
                tags=("coding",),
                context_window=256_000,
                max_output_tokens=8_192,
            ),
            ModelSpec(
                slug="mistral-large-latest",
                display_name="Mistral Large",
                description="Flagship general-purpose model",
                tags=("reasoning",),
                context_window=256_000,
                max_output_tokens=8_192,
            ),
        ),
    ),
    ProviderSpec(
        key="openrouter",
        display_name="OpenRouter",
        env_vars=("OPENROUTER_API_KEY",),
        default_model="openrouter/auto",
        context_window=200_000,
        supports_tools=True,
        supports_reasoning=True,
        icon="🅡",
        website="https://openrouter.ai/",
        api_key_url="https://openrouter.ai/keys",
        notes="Meta-provider routing to 300+ upstream models.",
        models=(
            ModelSpec(
                slug="openrouter/auto",
                display_name="Auto (Best Available)",
                description="Automatically selects the best available model",
                tags=("reasoning", "coding", "fast"),
                context_window=200_000,
                max_output_tokens=16_000,
            ),
        ),
    ),
    ProviderSpec(
        key="lmstudio",
        display_name="LM Studio",
        env_vars=(),
        default_model="",
        context_window=32_768,
        supports_tools=True,
        icon="🅛",
        website="https://lmstudio.ai/",
        api_key_url="",
        notes="Local OpenAI-compatible server. Probed at http://localhost:1234/v1.",
    ),
    ProviderSpec(
        key="ollama",
        display_name="Ollama",
        env_vars=(),
        default_model="llama3.2",
        context_window=8_192,
        supports_tools=True,
        icon="🅞",
        website="https://ollama.com/",
        api_key_url="",
        notes="Local LLM runtime. No API key required. Pull models with `ollama pull <name>`.",
        models=(
            ModelSpec(
                slug="llama3.2",
                display_name="Llama 3.2",
                description="Lightweight local model",
                tags=("fast",),
                context_window=8_192,
                max_output_tokens=4_096,
            ),
            ModelSpec(
                slug="qwen2.5-coder",
                display_name="Qwen 2.5 Coder",
                description="Code-optimized local model",
                tags=("coding",),
                context_window=8_192,
                max_output_tokens=4_096,
            ),
            ModelSpec(
                slug="mistral",
                display_name="Mistral",
                description="General-purpose local model",
                tags=("fast",),
                context_window=8_192,
                max_output_tokens=4_096,
            ),
        ),
    ),
    ProviderSpec(
        key="bedrock",
        display_name="Amazon Bedrock",
        env_vars=("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"),
        default_model="anthropic.claude-opus-4.7-v1",
        context_window=200_000,
        supports_tools=True,
        supports_reasoning=True,
        icon="🅑",
        website="https://aws.amazon.com/bedrock/",
        api_key_url="https://console.aws.amazon.com/iam/",
        notes="AWS managed models with enterprise security and compliance.",
        models=(
            ModelSpec(
                slug="anthropic.claude-opus-4.7-v1",
                display_name="Claude Opus 4.7 (Bedrock)",
                description="Most capable Claude on AWS infrastructure",
                tags=("reasoning",),
                context_window=200_000,
                max_output_tokens=32_000,
            ),
            ModelSpec(
                slug="anthropic.claude-sonnet-4.6-v1",
                display_name="Claude Sonnet 4.6 (Bedrock)",
                description="Best balance for everyday coding on AWS",
                tags=("coding",),
                context_window=200_000,
                max_output_tokens=64_000,
            ),
        ),
    ),
    ProviderSpec(
        key="mock",
        display_name="Mock (Tests)",
        env_vars=(),
        default_model="mock-1",
        context_window=8_192,
        supports_tools=True,
        icon="🅜",
        website="",
        api_key_url="",
        notes="In-process scripted provider for the test harness.",
    ),
)


def get_provider(key: str) -> ProviderSpec | None:
    """Return the spec for ``key`` (case-insensitive) or ``None``."""
    norm = (key or "").strip().lower()
    for spec in PROVIDER_REGISTRY:
        if spec.key.lower() == norm:
            return spec
    return None


def get_model_spec(model_slug: str) -> ModelSpec | None:
    """Find a model by slug across all providers."""
    for spec in PROVIDER_REGISTRY:
        for model in spec.models:
            if model.slug == model_slug:
                return model
    return None


def get_models_for_provider(provider_key: str) -> tuple[ModelSpec, ...]:
    """Return all models registered for a provider."""
    spec = get_provider(provider_key)
    return spec.models if spec else ()


def get_all_models() -> list[tuple[ProviderSpec, ModelSpec]]:
    """Return flat list of (provider, model) pairs."""
    result: list[tuple[ProviderSpec, ModelSpec]] = []
    for spec in PROVIDER_REGISTRY:
        for model in spec.models:
            result.append((spec, model))
    return result


def get_available_providers() -> list[str]:
    """Return provider keys that have credentials configured."""
    import os
    available: list[str] = []
    for spec in PROVIDER_REGISTRY:
        if spec.key == "mock":
            continue
        if spec.key in ("ollama", "lmstudio"):
            available.append(spec.key)
            continue
        for env_var in spec.env_vars:
            if os.environ.get(env_var):
                available.append(spec.key)
                break
    return available


def get_default_fallback_chain() -> list[str]:
    """Default fallback order for multi-LLM orchestration."""
    return [
        "anthropic", "deepseek", "gemini", "openai",
        "bedrock", "kimi", "qwen", "ollama",
    ]


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
    "claude-opus-4.7": 32_000,
    "claude-sonnet-4.5": 64_000,
    "claude-sonnet-4.6": 64_000,
    "claude-haiku-4": 64_000,
    "claude-haiku-4.5": 64_000,
    "gpt-5": 128_000,
    "gpt-4o": 16_000,
    "gpt-4o-mini": 16_000,
    "gpt-4-turbo": 4_096,
    "gpt-3.5-turbo": 4_096,
    "o3-mini": 100_000,
    "o3": 100_000,
    "o1": 100_000,
    "gemini-2.5-pro": 64_000,
    "gemini-2.5-pro-preview": 64_000,
    "gemini-3.1-pro": 64_000,
    "gemini-2.5-flash": 64_000,
    "deepseek-chat": 8_000,
    "deepseek-coder": 8_000,
    "deepseek-reasoner": 16_000,
    "deepseek-v4-pro": 32_000,
    "deepseek-v4-flash": 16_000,
    "grok-4": 64_000,
    "grok-code-fast-1": 64_000,
    "qwen-3.7-max": 8_192,
    "qwen-turbo": 8_192,
    "qwen-plus": 8_192,
    "kimi-k2.6": 16_384,
    "codestral-latest": 8_192,
    "mistral-large-latest": 8_192,
    "llama-3.3-70b-versatile": 8_192,
    "llama3.3-70b": 8_192,
    "qwen-3-coder": 8_192,
    "qwen-3-32b": 8_192,
    "llama3.2": 4_096,
    "qwen2.5-coder": 4_096,
}


def max_tokens_for_model(model: str) -> int:
    """Return the registered max output for *model* (safe fallback).

    Checks ModelSpec first, then the legacy per-model dict,
    then falls back to heuristic based on model name."""
    model_spec = get_model_spec(model)
    if model_spec and model_spec.max_output_tokens:
        return model_spec.max_output_tokens
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
    "ModelSpec",
    "ProviderSpec",
    "ProviderKey",
    "get_provider",
    "get_model_spec",
    "get_models_for_provider",
    "get_all_models",
    "get_available_providers",
    "get_default_fallback_chain",
    "providers_by_capability",
    "max_tokens_for_model",
    "max_tokens_for_model_with_override",
    "plugin_max_output_tokens",
    "provider_routing_for",
]
