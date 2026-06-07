"""
Google provider adapter — translates Lyra canonical interface to Google Generative Language API.

Google Gemini models have the largest context windows (1M tokens) and use a
different API format from both Anthropic and OpenAI.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

from ..interface import (
    AbstractProvider,
    ChatRequest,
    ChatResponse,
    ErrorCode,
    ProviderConfig,
    ProviderError,
    StreamEvent,
)

logger = logging.getLogger(__name__)


class GoogleProvider(AbstractProvider):
    """
    Google Generative Language API provider adapter (Gemini models).

    Currently a stub — Google's API format differs significantly from
    Anthropic and OpenAI. Full implementation requires google-genai SDK
    or raw REST API translation.

    Key differentiators:
    - 1M token context window (Gemini 2.5 Flash/Pro)
    - Different tool/function calling format
    - Different streaming protocol
    """

    _CONTEXT_WINDOWS: dict[str, int] = {
        "gemini-2.5-flash": 1_000_000,
        "gemini-2.5-pro": 1_000_000,
    }

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        self._base_url = config.base_url or "https://generativelanguage.googleapis.com/v1beta"

    @property
    def provider_name(self) -> str:
        return "google"

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Stub — raises ProviderError until Google adapter is fully implemented."""
        raise ProviderError(
            code=ErrorCode.PROVIDER_ERROR,
            message="GoogleProvider is not yet implemented. Use Anthropic or DeepSeek provider.",
            provider="google",
        )

    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[StreamEvent]:
        """Stub — yields an error event."""
        yield StreamEvent(
            type="error",
            error="GoogleProvider streaming not yet implemented.",
        )

    async def validate_api_key(self) -> bool:
        return False

    async def list_models(self) -> list[str]:
        return list(self._CONTEXT_WINDOWS.keys())

    def supports_feature(self, feature: str) -> bool:
        return feature in {"tool_calling", "json_mode", "vision", "streaming"}

    def get_context_window(self, model: str) -> int:
        return self._CONTEXT_WINDOWS.get(model, 1_000_000)
