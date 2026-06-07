"""
Anthropic provider adapter — Claude models via the Anthropic Messages API.

Reads ``ANTHROPIC_API_KEY`` from the environment.
"""

from __future__ import annotations

import os
import time
import structlog
from collections.abc import AsyncIterator
from typing import Any

import anthropic

from src.routing.provider.base import ProviderBackend
from src.routing.provider.types import (
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
# Pricing per 1M tokens (USD) — Anthropic published rates as of mid-2025.
# Source: https://docs.anthropic.com/en/docs/about-claude/pricing
# ---------------------------------------------------------------------------
_CLAUDE_PRICING: dict[str, dict[str, float]] = {
    "claude-opus-4-5": {"input": 15.00, "output": 75.00},
    "claude-opus-4-0": {"input": 15.00, "output": 75.00},
    "claude-opus-4-5-haiku-2-0": {"input": 1.00, "output": 5.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
    "claude-sonnet-3-5": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-5-haiku": {"input": 1.00, "output": 5.00},
    "claude-haiku-3-5": {"input": 0.80, "output": 4.00},
    "claude-haiku-3": {"input": 0.25, "output": 1.25},
}

_DEFAULT_INPUT_PRICE = 3.00
_DEFAULT_OUTPUT_PRICE = 15.00

# Cache write costs (read is free, write has a surcharge)
_CACHE_WRITE_MULTIPLIER = 1.25  # 125% of input price


def _get_pricing(model: str) -> tuple[float, float]:
    """Return (input_price_per_1M, output_price_per_1M) for *model*."""
    pricing = _CLAUDE_PRICING.get(model)
    if pricing is not None:
        return pricing["input"], pricing["output"]
    # Try prefix matching for unknown models
    for key, val in sorted(_CLAUDE_PRICING.items(), key=lambda x: -len(x[0])):
        if model.startswith(key):
            return val["input"], val["output"]
    return _DEFAULT_INPUT_PRICE, _DEFAULT_OUTPUT_PRICE


# ---------------------------------------------------------------------------
# Effort level → Anthropic thinking budget tokens
# ---------------------------------------------------------------------------
_EFFORT_BUDGET: dict[EffortLevel, int] = {
    EffortLevel.LOW: 1024,
    EffortLevel.MEDIUM: 4096,
    EffortLevel.HIGH: 16384,
    EffortLevel.XHIGH: 32000,
    EffortLevel.MAX: 64000,
}

_SUPPORTED_CAPABILITIES: frozenset[Capability] = frozenset(
    {
        Capability.TEXT_GENERATION,
        Capability.TOOL_USE,
        Capability.VISION,
        Capability.STREAMING,
        Capability.JSON_MODE,
        Capability.LONG_CONTEXT,
    },
)


def _count_tokens_heuristic(text: str) -> int:
    """Rough token count heuristic (~4 chars per token)."""
    return max(1, len(text) // 4)


def _messages_to_anthropic(messages: tuple[Message, ...]) -> list[dict[str, Any]]:
    """Convert Lyra ``Message`` sequence to Anthropic Messages API format."""
    result: list[dict[str, Any]] = []
    for msg in messages:
        if msg.role == "system":
            # Anthropic uses a separate ``system`` parameter, not a message.
            # We skip it here; the caller should pass it via the ``system`` key.
            continue
        entry: dict[str, Any] = {"role": msg.role, "content": []}
        if msg.content:
            entry["content"].append({"type": "text", "text": msg.content})
        if msg.tool_calls:
            for tc in msg.tool_calls:
                entry["content"].append(
                    {
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments,
                    },
                )
        if msg.tool_call_id:
            entry["content"].append(
                {
                    "type": "tool_result",
                    "tool_use_id": msg.tool_call_id,
                    "content": msg.content,
                },
            )
        if msg.name:
            entry["content"].append(
                {
                    "type": "tool_result",
                    "tool_use_id": msg.tool_call_id or "",
                    "content": msg.content,
                },
            )
        # If content is a plain string with no tool annotations, simplify
        if len(entry["content"]) == 1 and entry["content"][0]["type"] == "text":
            entry["content"] = msg.content
        result.append(entry)
    return result


def _tools_to_anthropic(tools: tuple[ToolDef, ...]) -> list[dict[str, Any]]:
    """Convert Lyra ``ToolDef`` sequence to Anthropic tool format."""
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.parameters,
        }
        for t in tools
    ]


def _extract_system_message(
    messages: tuple[Message, ...],
) -> str | None:
    """Extract the last system message from the message list."""
    for msg in reversed(messages):
        if msg.role == "system":
            return msg.content
    return None


def _parse_anthropic_response(
    response: anthropic.types.Message,
    latency_ms: float,
) -> CompletionResponse:
    """Convert an Anthropic ``Message`` into a ``CompletionResponse``."""
    content_parts: list[str] = []
    tool_calls: list[ToolCall] = []

    for block in response.content:
        if isinstance(block, anthropic.types.TextBlock):
            content_parts.append(block.text)
        elif isinstance(block, anthropic.types.ToolUseBlock):
            tool_calls.append(
                ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=dict(block.input) if isinstance(block.input, dict) else {},
                ),
            )
        # ``thinking`` / ``redacted_thinking`` blocks are silently skipped
        # in v1—they contribute context but no visible output.

    finish = response.stop_reason or "end_turn"
    usage = response.usage

    return CompletionResponse(
        content="".join(content_parts),
        tool_calls=tuple(tool_calls) if tool_calls else None,
        usage=TokenUsage(
            input_tokens=usage.input_tokens or 0,
            output_tokens=usage.output_tokens or 0,
            cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            cache_write_tokens=getattr(usage, "cache_write_input_tokens", 0) or 0,
        ),
        finish_reason=finish,
        model=response.model,
        latency_ms=latency_ms,
    )


class AnthropicAdapter(ProviderBackend):
    """Provider adapter for Anthropic's Claude models.

    Uses the ``anthropic`` Python SDK to call the Messages API.
    Supports text generation, tool use, vision, streaming, JSON mode,
    and long context.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        max_retries: int = 3,
    ) -> None:
        """Initialize the adapter.

        Args:
            api_key: Anthropic API key. Falls back to ``ANTHROPIC_API_KEY`` env var.
            base_url: Optional custom base URL.
            max_retries: Number of retries on transient errors.
        """
        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise ValueError(
                "Anthropic API key not provided. Set ANTHROPIC_API_KEY "
                "environment variable or pass api_key= to the constructor.",
            )
        self._client = anthropic.AsyncAnthropic(
            api_key=resolved_key,
            base_url=base_url,
            max_retries=max_retries,
        )
        self._pricing_cache: dict[str, tuple[float, float]] = {}

    # ------------------------------------------------------------------
    # ProviderBackend interface
    # ------------------------------------------------------------------

    @property
    def provider_name(self) -> str:
        return "anthropic"

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Send a completion request to the Anthropic Messages API.

        Args:
            request: The normalized completion request.

        Returns:
            The model's response.
        """
        system_text = _extract_system_message(request.messages)
        anthropic_messages = _messages_to_anthropic(request.messages)
        anthropic_tools = (
            _tools_to_anthropic(request.tools) if request.tools else None
        )

        kwargs: dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "messages": anthropic_messages,
            "temperature": request.temperature,
        }

        if system_text:
            kwargs["system"] = [{"type": "text", "text": system_text}]

        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        # Map effort level → thinking config
        _effort = request.effort
        if _effort != EffortLevel.MEDIUM:
            budget = _EFFORT_BUDGET.get(_effort, 4096)
            # Ensure max_tokens is large enough to accommodate thinking
            kwargs["max_tokens"] = max(request.max_tokens, budget + 1024)
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}

        start = time.monotonic()
        try:
            response = await self._client.messages.create(**kwargs)
        except anthropic.APIStatusError as exc:
            logger.error(
                "anthropic API error",
                status_code=exc.status_code,
                body=str(exc.body),
                model=request.model,
            )
            raise
        except anthropic.APITimeoutError:
            logger.error("anthropic API timeout", model=request.model)
            raise
        latency_ms = (time.monotonic() - start) * 1000

        return _parse_anthropic_response(response, latency_ms)

    async def complete_stream(
        self,
        request: CompletionRequest,
    ) -> AsyncIterator[CompletionChunk]:
        """Stream a completion from the Anthropic Messages API.

        Args:
            request: The normalized completion request.

        Yields:
            ``CompletionChunk`` instances as they arrive.
        """
        system_text = _extract_system_message(request.messages)
        anthropic_messages = _messages_to_anthropic(request.messages)
        anthropic_tools = (
            _tools_to_anthropic(request.tools) if request.tools else None
        )

        kwargs: dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "messages": anthropic_messages,
            "temperature": request.temperature,
        }

        if system_text:
            kwargs["system"] = [{"type": "text", "text": system_text}]

        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        _effort = request.effort
        if _effort != EffortLevel.MEDIUM:
            budget = _EFFORT_BUDGET.get(_effort, 4096)
            kwargs["max_tokens"] = max(request.max_tokens, budget + 1024)
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}

        try:
            async with self._client.messages.stream(**kwargs) as stream:
                async for text_delta in stream.text_stream:
                    yield CompletionChunk(content_delta=text_delta)

                # After the stream ends, check for tool calls
                final_message = await stream.get_final_message()
                for block in final_message.content:
                    if isinstance(block, anthropic.types.ToolUseBlock):
                        import json
                        yield CompletionChunk(
                            content_delta="",
                            tool_call_delta=json.dumps(
                                {
                                    "id": block.id,
                                    "name": block.name,
                                    "arguments": block.input,
                                },
                            ),
                            finish_reason="tool_use",
                        )
        except anthropic.APIStatusError as exc:
            logger.error(
                "anthropic stream API error",
                status_code=exc.status_code,
                model=request.model,
            )
            yield CompletionChunk(finish_reason="error")
        except anthropic.APITimeoutError:
            logger.error("anthropic stream timeout", model=request.model)
            yield CompletionChunk(finish_reason="error")

    def supports(self, capability: Capability) -> bool:
        """Return ``True`` if this adapter supports *capability*."""
        return capability in _SUPPORTED_CAPABILITIES

    def cost_estimate(self, request: CompletionRequest) -> CostEstimate:
        """Estimate cost for *request* using Anthropic's published pricing.

        Uses a heuristic token count (4 chars per token) for estimation.
        """
        input_price, output_price = _get_pricing(request.model)
        input_tokens = sum(_count_tokens_heuristic(m.content or "") for m in request.messages)
        output_tokens = request.max_tokens  # worst case

        input_cost = (input_tokens / 1_000_000) * input_price
        output_cost = (output_tokens / 1_000_000) * output_price

        return CostEstimate(
            input_cost=round(input_cost, 6),
            output_cost=round(output_cost, 6),
            total_max_cost=round(input_cost + output_cost, 6),
        )

    # ------------------------------------------------------------------
    # Additional helpers
    # ------------------------------------------------------------------

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
