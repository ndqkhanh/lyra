"""
Google provider adapter — Gemini models via the Google GenAI SDK.

Reads ``GOOGLE_API_KEY`` from the environment.
"""

from __future__ import annotations

import json
import os
import time
import structlog
from collections.abc import AsyncIterator
from typing import Any

from google.genai import Client as GenAIClient
from google.genai.types import (
    Content,
    FunctionCall,
    FunctionDeclaration,
    GenerateContentResponse,
    Part,
    Tool as GenAITool,
)

from lyra.routing.provider.base import ProviderBackend
from lyra.routing.provider.types import (
    Capability,
    CompletionChunk,
    CompletionRequest,
    CompletionResponse,
    CostEstimate,
    EffortLevel,
    Message,
    ToolCall,
    ToolDef,
    TokenUsage,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Gemini published pricing (per 1M tokens) as of mid-2025.
# Source: https://ai.google.dev/pricing
# ---------------------------------------------------------------------------
_GEMINI_PRICING: dict[str, dict[str, float]] = {
    "gemini-2-5-flash": {"input": 0.15, "output": 0.60},
    "gemini-2-5-pro": {"input": 1.25, "output": 5.00},
    "gemini-2-0-flash": {"input": 0.10, "output": 0.40},
    "gemini-1-5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1-5-flash": {"input": 0.075, "output": 0.30},
}

_DEFAULT_INPUT_PRICE = 0.15
_DEFAULT_OUTPUT_PRICE = 0.60

_SUPPORTED_CAPABILITIES: frozenset[Capability] = frozenset(
    {
        Capability.TEXT_GENERATION,
        Capability.VISION,
        Capability.STREAMING,
        Capability.LONG_CONTEXT,
        Capability.AUDIO_INPUT,
    },
)


def _get_pricing(model: str) -> tuple[float, float]:
    """Return (input_price_per_1M, output_price_per_1M) for *model*."""
    pricing = _GEMINI_PRICING.get(model)
    if pricing is not None:
        return pricing["input"], pricing["output"]
    for key, val in sorted(_GEMINI_PRICING.items(), key=lambda x: -len(x[0])):
        if model.startswith(key):
            return val["input"], val["output"]
    return _DEFAULT_INPUT_PRICE, _DEFAULT_OUTPUT_PRICE


def _count_tokens_heuristic(text: str) -> int:
    """Rough token count heuristic (~4 chars per token)."""
    return max(1, len(text) // 4)


def _messages_to_gemini(
    messages: tuple[Message, ...],
) -> tuple[list[Content], str | None]:
    """Convert Lyra ``Message`` sequence to Gemini ``Content`` list.

    Returns (contents, system_instruction_text).
    """
    contents: list[Content] = []
    system_text: str | None = None

    for msg in messages:
        if msg.role == "system":
            system_text = msg.content
            continue

        role = "user" if msg.role == "user" else "model"

        parts: list[Part] = []
        if msg.content:
            parts.append(Part.from_text(text=msg.content))

        if msg.tool_calls:
            for tc in msg.tool_calls:
                parts.append(
                    Part(
                        function_call=FunctionCall(
                            name=tc.name,
                            args=tc.arguments,
                        ),
                    ),
                )

        if parts:
            contents.append(Content(role=role, parts=parts))

    return contents, system_text


def _tools_to_gemini(tools: tuple[ToolDef, ...]) -> list[GenAITool]:
    """Convert Lyra ``ToolDef`` sequence to Gemini tool format."""
    declarations = []
    for t in tools:
        declarations.append(
            FunctionDeclaration(
                name=t.name,
                description=t.description,
                parameters=t.parameters,
            ),
        )
    return [GenAITool(function_declarations=declarations)]


def _parse_gemini_response(
    response: GenerateContentResponse,
    latency_ms: float,
    model: str,
) -> CompletionResponse:
    """Convert a Gemini ``GenerateContentResponse`` into a ``CompletionResponse``."""
    content_parts: list[str] = []
    tool_calls: list[ToolCall] = []

    if response.candidates:
        candidate = response.candidates[0]
        if candidate.content and candidate.content.parts:
            for part in candidate.content.parts:
                if part.text:
                    content_parts.append(part.text)
                if part.function_call:
                    tool_calls.append(
                        ToolCall(
                            id=part.function_call.name,
                            name=part.function_call.name,
                            arguments=dict(part.function_call.args)
                            if part.function_call.args
                            else {},
                        ),
                    )

    finish = "stop"
    if response.candidates and response.candidates[0].finish_reason:
        finish = response.candidates[0].finish_reason.name.lower()

    # Token usage from response metadata
    input_tokens = 0
    output_tokens = 0
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        input_tokens = response.usage_metadata.prompt_token_count or 0
        output_tokens = response.usage_metadata.candidates_token_count or 0

    return CompletionResponse(
        content="".join(content_parts),
        tool_calls=tuple(tool_calls) if tool_calls else None,
        usage=TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        ),
        finish_reason=finish,
        model=model,
        latency_ms=latency_ms,
    )


class GoogleAdapter(ProviderBackend):
    """Provider adapter for Google Gemini models.

    Uses the ``google.genai`` SDK. Supports text generation, vision,
    streaming, long context, and audio input.
    """

    def __init__(
        self,
        api_key: str | None = None,
        max_retries: int = 3,
    ) -> None:
        """Initialize the adapter.

        Args:
            api_key: Google API key. Falls back to ``GOOGLE_API_KEY`` env var.
            max_retries: Number of retries on transient errors.
        """
        resolved_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not resolved_key:
            raise ValueError(
                "Google API key not provided. Set GOOGLE_API_KEY "
                "environment variable or pass api_key= to the constructor.",
            )
        self._client = GenAIClient(api_key=resolved_key)
        self._max_retries = max_retries

    # ------------------------------------------------------------------
    # ProviderBackend interface
    # ------------------------------------------------------------------

    @property
    def provider_name(self) -> str:
        return "google"

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Send a completion request to the Gemini API.

        Args:
            request: The normalized completion request.

        Returns:
            The model's response.
        """
        contents, system_text = _messages_to_gemini(request.messages)
        gemini_tools = (
            _tools_to_gemini(request.tools) if request.tools else None
        )

        kwargs: dict[str, Any] = {
            "model": request.model,
            "contents": contents,
            "config": {
                "max_output_tokens": request.max_tokens,
                "temperature": request.temperature,
            },
        }

        if system_text:
            kwargs["config"]["system_instruction"] = system_text  # type: ignore[index]

        if gemini_tools:
            kwargs["config"]["tools"] = gemini_tools  # type: ignore[index]

        start = time.monotonic()
        try:
            response = await self._client.aio.models.generate_content(**kwargs)
        except Exception as exc:
            logger.error(
                "google API error",
                error=str(exc),
                model=request.model,
            )
            raise
        latency_ms = (time.monotonic() - start) * 1000

        return _parse_gemini_response(response, latency_ms, request.model)

    async def complete_stream(
        self,
        request: CompletionRequest,
    ) -> AsyncIterator[CompletionChunk]:
        """Stream a completion from the Gemini API.

        Args:
            request: The normalized completion request.

        Yields:
            ``CompletionChunk`` instances as they arrive.
        """
        contents, system_text = _messages_to_gemini(request.messages)
        gemini_tools = (
            _tools_to_gemini(request.tools) if request.tools else None
        )

        kwargs: dict[str, Any] = {
            "model": request.model,
            "contents": contents,
            "config": {
                "max_output_tokens": request.max_tokens,
                "temperature": request.temperature,
            },
        }

        if system_text:
            kwargs["config"]["system_instruction"] = system_text  # type: ignore[index]

        if gemini_tools:
            kwargs["config"]["tools"] = gemini_tools  # type: ignore[index]

        try:
            stream = await self._client.aio.models.generate_content_stream(**kwargs)
            async for chunk in stream:
                text_delta = chunk.text if hasattr(chunk, "text") else ""
                yield CompletionChunk(content_delta=text_delta or "")
        except Exception as exc:
            logger.error(
                "google stream API error",
                error=str(exc),
                model=request.model,
            )
            yield CompletionChunk(finish_reason="error")

    def supports(self, capability: Capability) -> bool:
        """Return ``True`` if this adapter supports *capability*."""
        return capability in _SUPPORTED_CAPABILITIES

    def cost_estimate(self, request: CompletionRequest) -> CostEstimate:
        """Estimate cost for *request* using Google's published pricing."""
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
