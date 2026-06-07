"""
OpenAI provider adapter — GPT and o-series models via the OpenAI API.

Reads ``OPENAI_API_KEY`` from the environment.
"""

from __future__ import annotations

import json
import os
import time
import structlog
from collections.abc import AsyncIterator
from typing import Any

import openai

from lyra.routing.provider.adapters.deepseek import (
    _count_tokens_heuristic,
    _messages_to_openai,
    _parse_openai_response,
    _tools_to_openai,
)
from lyra.routing.provider.base import ProviderBackend
from lyra.routing.provider.types import (
    Capability,
    CompletionChunk,
    CompletionRequest,
    CompletionResponse,
    CostEstimate,
    EffortLevel,
    TokenUsage,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# OpenAI published pricing (per 1M tokens) as of mid-2025.
# Source: https://openai.com/api/pricing/
# ---------------------------------------------------------------------------
_OPENAI_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-1": {"input": 2.00, "output": 8.00},
    "gpt-4-1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4-1-nano": {"input": 0.10, "output": 0.40},
    "gpt-4o-audio-preview": {"input": 2.50, "output": 10.00},
    "o3": {"input": 10.00, "output": 40.00},
    "o4-mini": {"input": 1.10, "output": 4.40},
}

_DEFAULT_INPUT_PRICE = 2.50
_DEFAULT_OUTPUT_PRICE = 10.00

_SUPPORTED_CAPABILITIES: frozenset[Capability] = frozenset(
    {
        Capability.TEXT_GENERATION,
        Capability.TOOL_USE,
        Capability.VISION,
        Capability.STREAMING,
        Capability.JSON_MODE,
        Capability.LONG_CONTEXT,
        Capability.AUDIO_INPUT,
        Capability.AUDIO_OUTPUT,
    },
)


def _get_pricing(model: str) -> tuple[float, float]:
    """Return (input_price_per_1M, output_price_per_1M) for *model*."""
    pricing = _OPENAI_PRICING.get(model)
    if pricing is not None:
        return pricing["input"], pricing["output"]
    for key, val in sorted(_OPENAI_PRICING.items(), key=lambda x: -len(x[0])):
        if model.startswith(key):
            return val["input"], val["output"]
    return _DEFAULT_INPUT_PRICE, _DEFAULT_OUTPUT_PRICE


class OpenAIAdapter(ProviderBackend):
    """Provider adapter for OpenAI models (GPT-4o, o-series, etc.).

    Uses the ``openai`` Python SDK. Supports text generation, tool use,
    vision, streaming, JSON mode, long context, and audio capabilities.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        max_retries: int = 3,
    ) -> None:
        """Initialize the adapter.

        Args:
            api_key: OpenAI API key. Falls back to ``OPENAI_API_KEY`` env var.
            base_url: Custom base URL (defaults to OpenAI API endpoint).
            max_retries: Number of retries on transient errors.
        """
        resolved_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not resolved_key:
            raise ValueError(
                "OpenAI API key not provided. Set OPENAI_API_KEY "
                "environment variable or pass api_key= to the constructor.",
            )
        self._client = openai.AsyncOpenAI(
            api_key=resolved_key,
            base_url=base_url,
            max_retries=max_retries,
        )

    # ------------------------------------------------------------------
    # ProviderBackend interface
    # ------------------------------------------------------------------

    @property
    def provider_name(self) -> str:
        return "openai"

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Send a completion request to the OpenAI API.

        Args:
            request: The normalized completion request.

        Returns:
            The model's response.
        """
        openai_messages = _messages_to_openai(request.messages)
        openai_tools = (
            _tools_to_openai(request.tools) if request.tools else None
        )

        kwargs: dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "messages": openai_messages,
            "temperature": request.temperature,
        }

        if openai_tools:
            kwargs["tools"] = openai_tools

        # Map effort levels for reasoning models (o-series)
        if request.effort in (EffortLevel.XHIGH, EffortLevel.MAX):
            kwargs["reasoning_effort"] = "high"
        elif request.effort == EffortLevel.HIGH:
            kwargs["reasoning_effort"] = "medium"
        elif request.effort == EffortLevel.LOW:
            kwargs["reasoning_effort"] = "low"

        start = time.monotonic()
        try:
            response: openai.types.chat.ChatCompletion = (
                await self._client.chat.completions.create(**kwargs)
            )
        except openai.APIStatusError as exc:
            logger.error(
                "openai API error",
                status_code=exc.status_code,
                body=str(exc.body),
                model=request.model,
            )
            raise
        except openai.APITimeoutError:
            logger.error("openai API timeout", model=request.model)
            raise
        latency_ms = (time.monotonic() - start) * 1000

        return _parse_openai_response(response, latency_ms)

    async def complete_stream(
        self,
        request: CompletionRequest,
    ) -> AsyncIterator[CompletionChunk]:
        """Stream a completion from the OpenAI API.

        Args:
            request: The normalized completion request.

        Yields:
            ``CompletionChunk`` instances as they arrive.
        """
        openai_messages = _messages_to_openai(request.messages)
        openai_tools = (
            _tools_to_openai(request.tools) if request.tools else None
        )

        kwargs: dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "messages": openai_messages,
            "temperature": request.temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        if openai_tools:
            kwargs["tools"] = openai_tools

        if request.effort in (EffortLevel.XHIGH, EffortLevel.MAX):
            kwargs["reasoning_effort"] = "high"
        elif request.effort == EffortLevel.HIGH:
            kwargs["reasoning_effort"] = "medium"
        elif request.effort == EffortLevel.LOW:
            kwargs["reasoning_effort"] = "low"

        try:
            stream = await self._client.chat.completions.create(**kwargs)
            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue

                content_delta = delta.content or ""
                finish_reason = (
                    chunk.choices[0].finish_reason if chunk.choices else None
                )

                tool_call_delta = None
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        tool_call_delta = json.dumps(
                            {
                                "id": tc.id or "",
                                "index": tc.index,
                                "function": {
                                    "name": tc.function.name or "",
                                    "arguments": tc.function.arguments or "",
                                },
                            },
                        )

                yield CompletionChunk(
                    content_delta=content_delta,
                    tool_call_delta=tool_call_delta,
                    finish_reason=finish_reason,
                )
        except openai.APIStatusError as exc:
            logger.error(
                "openai stream API error",
                status_code=exc.status_code,
                model=request.model,
            )
            yield CompletionChunk(finish_reason="error")
        except openai.APITimeoutError:
            logger.error("openai stream timeout", model=request.model)
            yield CompletionChunk(finish_reason="error")

    def supports(self, capability: Capability) -> bool:
        """Return ``True`` if this adapter supports *capability*."""
        return capability in _SUPPORTED_CAPABILITIES

    def cost_estimate(self, request: CompletionRequest) -> CostEstimate:
        """Estimate cost for *request* using OpenAI's published pricing."""
        input_price, output_price = _get_pricing(request.model)
        input_tokens = sum(
            _count_tokens_heuristic(m.content or "") for m in request.messages
        )
        output_tokens = request.max_tokens

        input_cost = (input_tokens / 1_000_000) * input_price
        output_cost = (output_tokens / 1_000_000) * output_price

        return CostEstimate(
            input_cost=round(input_cost, 6),
            output_cost=round(output_cost, 6),
            total_max_cost=round(input_cost + output_cost, 6),
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self._client.close())
            else:
                loop.run_until_complete(self._client.close())
        except RuntimeError:
            pass
