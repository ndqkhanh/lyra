"""
OpenAI provider adapter — translates Lyra canonical interface to OpenAI API.

OpenAI uses the standard chat completions API with reasoning_effort support.
Structurally similar to DeepSeekProvider (both use OpenAI-compatible format)
but adds reasoning_effort and native vision support.
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
    ProviderConfig,
    ProviderError,
    StreamEvent,
    ToolCall,
)

from .deepseek import (
    _from_openai_message,
    _from_openai_usage,
    _to_openai_message,
    _to_openai_tool,
)

logger = logging.getLogger(__name__)


class OpenAIProvider(AbstractProvider):
    """
    OpenAI API provider adapter.

    Uses the standard chat completions API. Key features vs DeepSeek:
    - Native ``reasoning_effort`` parameter for o-series models
    - Vision support (image inputs in content blocks)
    - JSON mode via ``response_format``
    """

    _CONTEXT_WINDOWS: dict[str, int] = {
        "gpt-4o-mini-2025": 128_000,
        "gpt-4o-2025": 128_000,
        "gpt-5": 256_000,
    }

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        self._base_url = config.base_url or "https://api.openai.com/v1"

    @property
    def provider_name(self) -> str:
        return "openai"

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Send a chat completion to OpenAI and return the response."""
        start = time.perf_counter()

        messages = self._build_messages(request)

        body: dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "messages": messages,
        }

        if request.tools:
            body["tools"] = [_to_openai_tool(t) for t in request.tools]

        if request.temperature is not None:
            body["temperature"] = request.temperature

        # Effort → OpenAI reasoning_effort (for o-series)
        if request.effort_reasoning:
            body["reasoning_effort"] = request.effort_reasoning

        try:
            import httpx

            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    json=body,
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()

        except ImportError:
            return await self._chat_via_http(request, body)
        except Exception as e:
            raise self._translate_error(e)

        elapsed = (time.perf_counter() - start) * 1000
        choice = data.get("choices", [{}])[0]
        msg = _from_openai_message(choice.get("message", {}))

        return ChatResponse(
            content=msg.content if isinstance(msg.content, str) else "",
            model=data.get("model", request.model),
            usage=_from_openai_usage(data.get("usage")),
            tool_calls=msg.tool_calls,
            finish_reason=choice.get("finish_reason", "stop"),
            latency_ms=elapsed,
            provider="openai",
            raw=data,
        )

    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[StreamEvent]:
        """Stream a chat completion from OpenAI."""
        messages = self._build_messages(request)

        body: dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "messages": messages,
            "stream": True,
        }

        if request.tools:
            body["tools"] = [_to_openai_tool(t) for t in request.tools]

        if request.effort_reasoning:
            body["reasoning_effort"] = request.effort_reasoning

        try:
            import httpx

            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/chat/completions",
                    json=body,
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
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

                        choice = event.get("choices", [{}])[0]
                        delta = choice.get("delta", {})

                        # Tool calls
                        tool_calls_delta = delta.get("tool_calls", [])
                        for tc_delta in tool_calls_delta:
                            func = tc_delta.get("function", {})
                            if tc_delta.get("id"):
                                current_tool = {
                                    "id": tc_delta["id"],
                                    "name": func.get("name", ""),
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
                            if current_tool and func.get("arguments"):
                                current_tool["arguments"] += func["arguments"]

                        # Text
                        content = delta.get("content", "")
                        if content:
                            yield StreamEvent(type="text_delta", content=content)

                        # Done
                        if choice.get("finish_reason"):
                            if current_tool:
                                try:
                                    args = json.loads(current_tool.get("arguments", "{}"))
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
                            yield StreamEvent(
                                type="done",
                                usage=_from_openai_usage(event.get("usage")),
                            )

        except ImportError:
            yield StreamEvent(type="error", error="httpx not installed")
        except Exception as e:
            yield StreamEvent(type="error", error=str(e))

    async def validate_api_key(self) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self._base_url}/models",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                )
                return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        return list(self._CONTEXT_WINDOWS.keys())

    def supports_feature(self, feature: str) -> bool:
        return feature in {"tool_calling", "json_mode", "vision", "streaming"}

    def get_context_window(self, model: str) -> int:
        return self._CONTEXT_WINDOWS.get(model, 128_000)

    def _build_messages(self, request: ChatRequest) -> list[dict[str, Any]]:
        return [_to_openai_message(m) for m in request.messages]

    async def _chat_via_http(self, request: ChatRequest, body: dict[str, Any]) -> ChatResponse:
        try:
            import aiohttp
        except ImportError:
            raise ProviderError(
                code=ErrorCode.PROVIDER_ERROR,
                message="Neither httpx nor aiohttp available.",
                provider="openai",
            )
        start = time.perf_counter()
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self._base_url}/chat/completions",
                json=body,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
            ) as response:
                data = await response.json()
        elapsed = (time.perf_counter() - start) * 1000
        choice = data.get("choices", [{}])[0]
        msg = _from_openai_message(choice.get("message", {}))
        return ChatResponse(
            content=msg.content if isinstance(msg.content, str) else "",
            model=data.get("model", request.model),
            usage=_from_openai_usage(data.get("usage")),
            tool_calls=msg.tool_calls,
            finish_reason=choice.get("finish_reason", "stop"),
            latency_ms=elapsed,
            provider="openai",
            raw=data,
        )

    @staticmethod
    def _translate_error(error: Exception) -> ProviderError:
        msg = str(error).lower()
        if "401" in msg or "unauthorized" in msg:
            return ProviderError(code=ErrorCode.AUTH_ERROR, message=str(error), provider="openai")
        if "429" in msg or "rate limit" in msg:
            return ProviderError(code=ErrorCode.RATE_LIMIT, message=str(error), provider="openai", retryable=True)
        return ProviderError(code=ErrorCode.UNKNOWN, message=str(error), provider="openai")
