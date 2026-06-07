"""
Provider listing endpoint.

Returns all configured LLM providers with their available models and capabilities.
"""

from __future__ import annotations

from typing import Any

from aiohttp import web

from lyra.routing.provider.adapters.anthropic import AnthropicAdapter, _SUPPORTED_CAPABILITIES as ANTHROPIC_CAPS
from lyra.routing.provider.adapters.deepseek import DeepSeekAdapter, _SUPPORTED_CAPABILITIES as DEEPSEEK_CAPS
from lyra.routing.provider.adapters.google import GoogleAdapter, _SUPPORTED_CAPABILITIES as GOOGLE_CAPS
from lyra.routing.provider.adapters.openai import OpenAIAdapter, _SUPPORTED_CAPABILITIES as OPENAI_CAPS
from lyra.routing.provider.config import get_api_key

# ---------------------------------------------------------------------------
# Provider metadata — static for now, loaded from env-based availability
# ---------------------------------------------------------------------------

_KNOWN_PROVIDERS: dict[str, dict[str, Any]] = {
    "anthropic": {
        "label": "Anthropic",
        "models": ["claude-sonnet-4-6", "claude-opus-4-5", "claude-haiku-3-5"],
        "capabilities": [c.value for c in ANTHROPIC_CAPS],
        "adapter_class": AnthropicAdapter,
    },
    "deepseek": {
        "label": "DeepSeek",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "capabilities": [c.value for c in DEEPSEEK_CAPS],
        "adapter_class": DeepSeekAdapter,
    },
    "openai": {
        "label": "OpenAI",
        "models": ["gpt-4o", "gpt-4o-mini", "o3"],
        "capabilities": [c.value for c in OPENAI_CAPS],
        "adapter_class": OpenAIAdapter,
    },
    "google": {
        "label": "Google",
        "models": ["gemini-2-0-flash", "gemini-2-5-flash", "gemini-2-5-pro"],
        "capabilities": [c.value for c in GOOGLE_CAPS],
        "adapter_class": GoogleAdapter,
    },
}


async def handle(request: web.Request) -> web.Response:
    """Return a list of configured providers.

    A provider is included only if its API key is found in the environment.
    """
    providers: list[dict[str, Any]] = []

    for name, meta in _KNOWN_PROVIDERS.items():
        api_key = get_api_key(name)
        if not api_key:
            continue
        default_model = meta["models"][0] if meta["models"] else ""
        providers.append(
            {
                "name": name,
                "label": meta["label"],
                "models": meta["models"],
                "defaultModel": default_model,
                "capabilities": meta["capabilities"],
            },
        )

    return web.json_response({"providers": providers})
