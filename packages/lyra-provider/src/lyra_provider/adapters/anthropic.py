"""
Anthropic provider adapter — translates Lyra canonical interface to Anthropic Messages API.

Handles:
- Message format: Lyra Message → Anthropic content blocks
- Tool schema: Lyra ToolSchema → Anthropic tool format
- Streaming: Anthropic SSE → Lyra StreamEvent iterator
- Usage: Anthropic usage block → Lyra LLMUsage
- Effort: Lyra effort → Anthropic ``budget_tokens`` + extended thinking
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, AsyncIterator

from ..interface import (
    AbstractProvider,
    ChatRequest,
    ChatResponse,
    ErrorCode,
    LLMUsage,
    Message,
    MessageRole,
    ProviderConfig,
    ProviderError,
    StreamEvent,
    ToolCall,
    ToolSchema,
)

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────
# Message translation: Lyra → Anthropic
# ────────────────────────────────────────────────────────────────────


def _to_anthropic_message(msg: Message) -> dict[str, Any]:
    """Convert a Lyra Message to Anthropic Messages API format."""
    if msg.role == MessageRole.SYSTEM:
        return {"role": "system", "content": msg.content}

    if msg.role == MessageRole.USER:
        return {"role": "user", "content": msg.content}

    if msg.role == MessageRole.ASSISTANT:
        result: dict[str, Any] = {"role": "assistant", "content": msg.content}
        if msg.tool_calls:
            result["content"] = [
                {
                    "type": "tool_use",
                    "id": tc.id,
                    "name": tc.name,
                    "input": tc.arguments,
                }
                for tc in msg.tool_calls
            ]
        return result

    if msg.role == MessageRole.TOOL:
        return {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": msg.tool_result.tool_call_id if msg.tool_result else "",
                    "content": msg.content,
                    "is_error": msg.tool_result.is_error if msg.tool_result else False,
                }
            ],
        }

    return {"role": "user", "content": str(msg.content)}


def _from_anthropic_message(anthropic_msg: dict[str, Any]) -> Message:
    """Convert an Anthropic response message to Lyra format."""
    role = MessageRole.ASSISTANT if anthropic_msg.get("role") == "assistant" else MessageRole.USER
    content_blocks = anthropic_msg.get("content", [])

    if isinstance(content_blocks, str):
        return Message(role=role, content=content_blocks)

    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []

    for block in content_blocks:
        if block.get("type") == "text":
            text_parts.append(block.get("text", ""))
        elif block.get("type") == "tool_use":
            tool_calls.append(ToolCall(
                id=block.get("id", ""),
                name=block.get("name", ""),
                arguments=block.get("input", {}),
            ))

    return Message(
        role=role,
        content="\n".join(text_parts),
        tool_calls=tool_calls if tool_calls else None,
    )


# ────────────────────────────────────────────────────────────────────
# Tool translation: Lyra → Anthropic
# ────────────────────────────────────────────────────────────────────


def _to_anthropic_tool(tool: ToolSchema) -> dict[str, Any]:
    """Convert a Lyra ToolSchema to Anthropic tool format."""
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.parameters,
    }


def _from_anthropic_usage(usage_data: dict[str, Any]) -> LLMUsage:
    """Convert Anthropic usage block to Lyra LLMUsage."""
    return LLMUsage(
        input_tokens=usage_data.get("input_tokens", 0),
        output_tokens=usage_data.get("output_tokens", 0),
        cache_read_tokens=usage_data.get("cache_read_input_tokens", 0),
        cache_write_tokens=usage_data.get("cache_creation_input_tokens", 0),
    )


# ────────────────────────────────────────────────────────────────────
# Provider implementation
# ────────────────────────────────────────────────────────────────────


class AnthropicProvider(AbstractProvider):
    """
    Anthropic Messages API provider adapter.

    Translates Lyra's canonical interface to Anthropic-specific API calls
    via the ``anthropic`` Python SDK (or raw HTTP if SDK unavailable).

    Effort mapping: Uses Anthropic's native ``budget_tokens`` extended thinking
    parameter. The ``effort_budget_tokens`` field from ChatRequest is passed
    directly as ``thinking.budget_tokens``.

    Streaming: Normalizes Anthropic SSE events into Lyra StreamEvent types.
    """

    # Well-known Anthropic model context windows
    _CONTEXT_WINDOWS: dict[str, int] = {
        "claude-opus-4-20250514": 200_000,
        "claude-sonnet-4-20250514": 200_000,
        "claude-haiku-4-20250514": 200_000,
        "claude-opus-4-8-20250514": 200_000,
        "claude-sonnet-4-6-20250514": 200_000,
        "claude-haiku-4-5-20250514": 200_000,
    }

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        self._base_url = config.base_url or "https://api.anthropic.com/v1"

    @property
    def provider_name(self) -> str:
        return "anthropic"

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Send a chat completion to Anthropic and return the response.

        Uses raw HTTP (httpx/aiohttp) to avoid requiring the anthropic SDK.
        Converts Lyra Message → Anthropic messages format, and Anthropic
        response → Lyra ChatResponse.
        """
        start = time.perf_counter()

        # Build Anthropic request body
        system_messages = [m for m in request.messages if m.role == MessageRole.SYSTEM]
        conversation = [m for m in request.messages if m.role != MessageRole.SYSTEM]

        body: dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "messages": [_to_anthropic_message(m) for m in conversation],
        }

        if system_messages:
            body["system"] = "\n".join(
                str(m.content) for m in system_messages
            )

        if request.tools:
            body["tools"] = [_to_anthropic_tool(t) for t in request.tools]

        # Effort → Anthropic extended thinking
        if request.effort_budget_tokens:
            body["thinking"] = {
                "type": "enabled",
                "budget_tokens": request.effort_budget_tokens,
            }

        if request.temperature is not None:
            body["temperature"] = request.temperature

        try:
            import httpx

            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                response = await client.post(
                    f"{self._base_url}/messages",
                    json=body,
                    headers={
                        "x-api-key": self.config.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()

        except ImportError:
            return await self._chat_via_http(request, body)
        except Exception as e:
            raise self._translate_error(e)

        elapsed = (time.perf_counter() - start) * 1000

        # Parse Anthropic response → Lyra ChatResponse
        content_block = data.get("content", [])
        msg = _from_anthropic_message({"role": "assistant", "content": content_block})

        return ChatResponse(
            content=msg.content if isinstance(msg.content, str) else "",
            model=data.get("model", request.model),
            usage=_from_anthropic_usage(data.get("usage", {})),
            tool_calls=msg.tool_calls,
            finish_reason=data.get("stop_reason", "stop"),
            latency_ms=elapsed,
            provider="anthropic",
            raw=data,
        )

    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[StreamEvent]:
        """Stream a chat completion from Anthropic and yield Lyra StreamEvents."""
        system_messages = [m for m in request.messages if m.role == MessageRole.SYSTEM]
        conversation = [m for m in request.messages if m.role != MessageRole.SYSTEM]

        body: dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "messages": [_to_anthropic_message(m) for m in conversation],
            "stream": True,
        }

        if system_messages:
            body["system"] = "\n".join(str(m.content) for m in system_messages)

        if request.tools:
            body["tools"] = [_to_anthropic_tool(t) for t in request.tools]

        if request.effort_budget_tokens:
            body["thinking"] = {
                "type": "enabled",
                "budget_tokens": request.effort_budget_tokens,
            }

        try:
            import httpx

            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/messages",
                    json=body,
                    headers={
                        "x-api-key": self.config.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                ) as response:
                    response.raise_for_status()

                    current_tool: dict[str, Any] | None = None

                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break

                        try:
                            event = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        event_type = event.get("type", "")

                        if event_type == "content_block_start":
                            block = event.get("content_block", {})
                            if block.get("type") == "tool_use":
                                current_tool = {
                                    "id": block.get("id", ""),
                                    "name": block.get("name", ""),
                                    "arguments": "",
                                }
                                yield StreamEvent(
                                    type="tool_call_start",
                                    tool_call=ToolCall(
                                        id=current_tool["id"],
                                        name=current_tool["name"],
                                        arguments={},
                                    ),
                                )

                        elif event_type == "content_block_delta":
                            delta = event.get("delta", {})
                            if delta.get("type") == "text_delta":
                                yield StreamEvent(
                                    type="text_delta",
                                    content=delta.get("text", ""),
                                )
                            elif delta.get("type") == "input_json_delta" and current_tool:
                                current_tool["arguments"] += delta.get("partial_json", "")

                        elif event_type == "content_block_stop":
                            if current_tool:
                                try:
                                    args = json.loads(current_tool["arguments"])
                                except json.JSONDecodeError:
                                    args = {}
                                yield StreamEvent(
                                    type="tool_call_end",
                                    tool_call=ToolCall(
                                        id=current_tool["id"],
                                        name=current_tool["name"],
                                        arguments=args,
                                    ),
                                )
                                current_tool = None

                        elif event_type == "message_delta":
                            usage = event.get("usage", {})
                            yield StreamEvent(
                                type="done",
                                usage=_from_anthropic_usage(usage),
                            )

        except ImportError:
            yield StreamEvent(
                type="error",
                error="httpx not installed — required for Anthropic provider",
            )
        except Exception as e:
            yield StreamEvent(type="error", error=str(e))

    async def validate_api_key(self) -> bool:
        """Check the API key by listing models (lightweight endpoint)."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self._base_url}/models",
                    headers={"x-api-key": self.config.api_key, "anthropic-version": "2023-06-01"},
                )
                return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """Return well-known Anthropic model IDs."""
        return list(self._CONTEXT_WINDOWS.keys())

    def supports_feature(self, feature: str) -> bool:
        return feature in {
            "tool_calling", "json_mode", "vision", "streaming", "prompt_caching",
        }

    def get_context_window(self, model: str) -> int:
        return self._CONTEXT_WINDOWS.get(model, 200_000)

    # ── Internal ─────────────────────────────────────────────────

    async def _chat_via_http(self, request: ChatRequest, body: dict[str, Any]) -> ChatResponse:
        """Fallback: use aiohttp if httpx is not available."""
        try:
            import aiohttp
        except ImportError:
            raise ProviderError(
                code=ErrorCode.PROVIDER_ERROR,
                message="Neither httpx nor aiohttp available. Install one to use AnthropicProvider.",
                provider="anthropic",
            )

        start = time.perf_counter()
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self._base_url}/messages",
                json=body,
                headers={
                    "x-api-key": self.config.api_key,
                    "anthropic-version": "2023-06-01",
                },
            ) as response:
                data = await response.json()

        elapsed = (time.perf_counter() - start) * 1000
        content_block = data.get("content", [])
        msg = _from_anthropic_message({"role": "assistant", "content": content_block})

        return ChatResponse(
            content=msg.content if isinstance(msg.content, str) else "",
            model=data.get("model", request.model),
            usage=_from_anthropic_usage(data.get("usage", {})),
            tool_calls=msg.tool_calls,
            finish_reason=data.get("stop_reason", "stop"),
            latency_ms=elapsed,
            provider="anthropic",
            raw=data,
        )

    @staticmethod
    def _translate_error(error: Exception) -> ProviderError:
        """Translate provider-specific errors to Lyra ProviderError taxonomy."""
        msg = str(error).lower()
        if "401" in msg or "unauthorized" in msg or "invalid api key" in msg:
            return ProviderError(code=ErrorCode.AUTH_ERROR, message=str(error), provider="anthropic")
        if "429" in msg or "rate limit" in msg:
            return ProviderError(code=ErrorCode.RATE_LIMIT, message=str(error), provider="anthropic", retryable=True)
        if "400" in msg or "invalid" in msg:
            return ProviderError(code=ErrorCode.INVALID_REQUEST, message=str(error), provider="anthropic")
        return ProviderError(code=ErrorCode.UNKNOWN, message=str(error), provider="anthropic")
