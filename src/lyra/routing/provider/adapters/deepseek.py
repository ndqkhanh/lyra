"""
DeepSeek provider adapter — DeepSeek models via the OpenAI-compatible API.

Reads ``DEEPSEEK_API_KEY`` from the environment.
"""

from __future__ import annotations

import json
import os
import time
import structlog
from collections.abc import AsyncIterator
from typing import Any

import openai

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
# DeepSeek published pricing (per 1M tokens) as of mid-2025.
# DeepSeek-V3 (V4 Flash equiv.): input=$0.27, output=$1.10
# DeepSeek-R1 (V4 Pro equiv.):    input=$0.55, output=$2.19
# ---------------------------------------------------------------------------
_DEEPSEEK_PRICING: dict[str, dict[str, float]] = {
    "deepseek-chat": {"input": 0.27, "output": 1.10},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
    "deepseek-v4-flash": {"input": 0.27, "output": 1.10},
    "deepseek-v4-pro": {"input": 0.55, "output": 2.19},
}

_DEFAULT_INPUT_PRICE = 0.27
_DEFAULT_OUTPUT_PRICE = 1.10

_DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

_SUPPORTED_CAPABILITIES: frozenset[Capability] = frozenset(
    {
        Capability.TEXT_GENERATION,
        Capability.TOOL_USE,
        Capability.STREAMING,
        Capability.JSON_MODE,
        Capability.LONG_CONTEXT,
    },
)


def _get_pricing(model: str) -> tuple[float, float]:
    """Return (input_price_per_1M, output_price_per_1M) for *model*."""
    pricing = _DEEPSEEK_PRICING.get(model)
    if pricing is not None:
        return pricing["input"], pricing["output"]
    for key, val in sorted(_DEEPSEEK_PRICING.items(), key=lambda x: -len(x[0])):
        if model.startswith(key):
            return val["input"], val["output"]
    return _DEFAULT_INPUT_PRICE, _DEFAULT_OUTPUT_PRICE


def _count_tokens_heuristic(text: str) -> int:
    """Rough token count heuristic (~4 chars per token)."""
    return max(1, len(text) // 4)


def _messages_to_openai(messages: tuple[Message, ...]) -> list[dict[str, Any]]:
    """Convert Lyra ``Message`` sequence to OpenAI Chat Completions format."""
    result: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.role
        if role == "system":
            entry: dict[str, Any] = {"role": "system", "content": msg.content}
        elif role == "user":
            entry = {"role": "user", "content": msg.content}
        elif role == "assistant":
            entry: dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
            if msg.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in msg.tool_calls
                ]
        elif role == "tool":
            entry = {
                "role": "tool",
                "tool_call_id": msg.tool_call_id or "",
                "content": msg.content,
            }
        else:
            entry = {"role": "user", "content": msg.content}
        result.append(entry)
    return result


def _tools_to_openai(tools: tuple[ToolDef, ...]) -> list[dict[str, Any]]:
    """Convert Lyra ``ToolDef`` sequence to OpenAI tool format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        for t in tools
    ]


def _parse_openai_response(
    response: openai.types.chat.ChatCompletion,
    latency_ms: float,
) -> CompletionResponse:
    """Convert an OpenAI ``ChatCompletion`` into a ``CompletionResponse``."""
    choice = response.choices[0]
    message = choice.message

    content = message.content or ""
    tool_calls: list[ToolCall] = []
    if message.tool_calls:
        for tc in message.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(
                ToolCall(id=tc.id, name=tc.function.name, arguments=args),
            )

    usage = response.usage
    finish = choice.finish_reason or "stop"

    return CompletionResponse(
        content=content,
        tool_calls=tuple(tool_calls) if tool_calls else None,
        usage=TokenUsage(
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            cache_read_tokens=getattr(usage, "prompt_tokens_details", None)
            and getattr(usage.prompt_tokens_details, "cached_tokens", 0) or 0,
        ),
        finish_reason=finish,
        model=response.model,
        latency_ms=latency_ms,
    )


class DeepSeekAdapter(ProviderBackend):
    """Provider adapter for DeepSeek models via the OpenAI-compatible API.

    Uses the ``openai`` Python SDK configured with DeepSeek's base URL.
    Supports text generation, tool use, streaming, JSON mode.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        max_retries: int = 3,
    ) -> None:
        """Initialize the adapter.

        Args:
            api_key: DeepSeek API key. Falls back to ``DEEPSEEK_API_KEY`` env var.
            base_url: Custom base URL (defaults to DeepSeek API endpoint).
            max_retries: Number of retries on transient errors.
        """
        resolved_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not resolved_key:
            raise ValueError(
                "DeepSeek API key not provided. Set DEEPSEEK_API_KEY "
                "environment variable or pass api_key= to the constructor.",
            )
        self._client = openai.AsyncOpenAI(
            api_key=resolved_key,
            base_url=base_url or _DEEPSEEK_BASE_URL,
            max_retries=max_retries,
        )

    # ------------------------------------------------------------------
    # ProviderBackend interface
    # ------------------------------------------------------------------

    @property
    def provider_name(self) -> str:
        return "deepseek"

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Send a completion request via the DeepSeek API.

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

        if request.effort in (EffortLevel.LOW, EffortLevel.MEDIUM):
            pass  # default sampling
        else:
            # DeepSeek reasoner uses a separate model identifier
            pass

        start = time.monotonic()
        try:
            response: openai.types.chat.ChatCompletion = await self._client.chat.completions.create(**kwargs)
        except openai.APIStatusError as exc:
            logger.error(
                "deepseek API error",
                status_code=exc.status_code,
                body=str(exc.body),
                model=request.model,
            )
            raise
        except openai.APITimeoutError:
            logger.error("deepseek API timeout", model=request.model)
            raise
        latency_ms = (time.monotonic() - start) * 1000

        return _parse_openai_response(response, latency_ms)

    async def complete_stream(
        self,
        request: CompletionRequest,
    ) -> AsyncIterator[CompletionChunk]:
        """Stream a completion from the DeepSeek API.

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

        try:
            stream = await self._client.chat.completions.create(**kwargs)
            async for chunk in stream:  # type: ignore[arg-type]
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue

                content_delta = delta.content or ""
                finish_reason = chunk.choices[0].finish_reason if chunk.choices else None

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
                "deepseek stream API error",
                status_code=exc.status_code,
                model=request.model,
            )
            yield CompletionChunk(finish_reason="error")
        except openai.APITimeoutError:
            logger.error("deepseek stream timeout", model=request.model)
            yield CompletionChunk(finish_reason="error")

    def supports(self, capability: Capability) -> bool:
        """Return ``True`` if this adapter supports *capability*."""
        return capability in _SUPPORTED_CAPABILITIES

    def cost_estimate(self, request: CompletionRequest) -> CostEstimate:
        """Estimate cost for *request* using DeepSeek's published pricing."""
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
