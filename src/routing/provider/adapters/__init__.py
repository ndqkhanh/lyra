"""
Concrete provider adapter implementations.

Available adapters:
- ``AnthropicAdapter`` — Claude models via the Anthropic Messages API.
- ``DeepSeekAdapter`` — DeepSeek models via the OpenAI-compatible API.
- ``OpenAIAdapter`` — OpenAI models (GPT-4o, o-series, etc.).
- ``GoogleAdapter`` — Gemini models via the Google GenAI SDK.
"""

from src.routing.provider.adapters.anthropic import AnthropicAdapter
from src.routing.provider.adapters.deepseek import DeepSeekAdapter
from src.routing.provider.adapters.google import GoogleAdapter
from src.routing.provider.adapters.openai import OpenAIAdapter

__all__ = [
    "AnthropicAdapter",
    "DeepSeekAdapter",
    "GoogleAdapter",
    "OpenAIAdapter",
]
