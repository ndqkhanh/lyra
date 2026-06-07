"""
Provider adapters — concrete implementations of AbstractProvider.

Each adapter translates Lyra's canonical interface to a specific provider's API:
- ``AnthropicProvider`` — Claude models via Anthropic API
- ``DeepSeekProvider`` — DeepSeek models via DeepSeek API
- ``OpenAIProvider`` — GPT models via OpenAI-compatible API
- ``GoogleProvider`` — Gemini models via Google Generative Language API
"""

from __future__ import annotations

from .anthropic import AnthropicProvider
from .deepseek import DeepSeekProvider
from .google import GoogleProvider
from .openai import OpenAIProvider

__all__ = [
    "AnthropicProvider",
    "DeepSeekProvider",
    "GoogleProvider",
    "OpenAIProvider",
]
