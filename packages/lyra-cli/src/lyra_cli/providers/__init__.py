"""Pluggable LLM providers for Lyra.

Providers in this package implement
:class:`harness_core.models.LLMProvider` so they're drop-in
replacements for ``AnthropicLLM`` / ``MockLLM``. The CLI's
:mod:`lyra_cli.llm_factory` wires them into the ``--llm auto``
cascade so the tool works with whatever the user has.

Shipped in this package
-----------------------

Cloud (require an API key env var):

* :class:`~lyra_cli.providers.openai_compatible.OpenAICompatibleLLM`
  — generic OpenAI chat-completions base used by all the "OpenAI-dialect"
  providers. Presets in
  :data:`~lyra_cli.providers.openai_compatible.PRESETS` cover:

  - **openai**       — GPT-5 / GPT-4o (``OPENAI_API_KEY``)
  - **openai-reasoning** — o3 / o3-mini (``OPENAI_API_KEY``)
  - **deepseek**     — deepseek-chat / coder / reasoner
    (``DEEPSEEK_API_KEY``)
  - **xai**          — Grok-4 / grok-code-fast-1 (``XAI_API_KEY``)
  - **groq**         — Llama / Kimi / Qwen hosted on Groq
    (``GROQ_API_KEY``)
  - **cerebras**     — Llama / Qwen on Cerebras (``CEREBRAS_API_KEY``)
  - **mistral**      — Codestral / Mistral-Large (``MISTRAL_API_KEY``)
  - **openrouter**   — meta-provider, 300+ models behind one key
    (``OPENROUTER_API_KEY``)
  - **lmstudio**     — local LM Studio server (no key, probe-based)

* :class:`~lyra_cli.providers.gemini.GeminiLLM` — Google
  Gemini 2.5 Pro / Flash / Flash-Lite (``GEMINI_API_KEY`` or
  ``GOOGLE_API_KEY``).

Local (no key required):

* :class:`~lyra_cli.providers.ollama.OllamaLLM` — Ollama
  daemon on ``127.0.0.1:11434``.

All providers are pure-stdlib at import time (``urllib`` + ``json``).
No new hard dependencies are added to the CLI package.
"""
from __future__ import annotations

from .gemini import (
    GEMINI_DEFAULT_BASE_URL,
    GEMINI_DEFAULT_MODEL,
    GeminiLLM,
    gemini_configured,
)
from .ollama import (
    OLLAMA_DEFAULT_HOST,
    OLLAMA_DEFAULT_MODEL,
    OllamaConnectionError,
    OllamaLLM,
    list_pulled_models,
    ollama_reachable,
)
from .openai_compatible import (
    PRESETS,
    OpenAICompatibleLLM,
    ProviderHTTPError,
    ProviderNotConfigured,
    configured_presets,
    iter_presets,
    preset_by_name,
)

__all__ = [
    # Ollama
    "OLLAMA_DEFAULT_HOST",
    "OLLAMA_DEFAULT_MODEL",
    "OllamaConnectionError",
    "OllamaLLM",
    "list_pulled_models",
    "ollama_reachable",
    # OpenAI-compatible
    "OpenAICompatibleLLM",
    "PRESETS",
    "ProviderHTTPError",
    "ProviderNotConfigured",
    "configured_presets",
    "iter_presets",
    "preset_by_name",
    # Gemini
    "GEMINI_DEFAULT_BASE_URL",
    "GEMINI_DEFAULT_MODEL",
    "GeminiLLM",
    "gemini_configured",
]
