"""
DeepSeek provider adapter — translates Lyra canonical interface to DeepSeek API.

DeepSeek uses an OpenAI-compatible API format, so this adapter is structurally
similar to OpenAIProvider but handles DeepSeek-specific quirks:
- No native reasoning budget — effort is injected as thinking instructions
- Tool calling is OpenAI-compatible
- Streaming uses standard SSE
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
# Message translation: Lyra → DeepSeek (OpenAI-compatible format)
# ────────────────────────────────────────────────────────────────────


def _to_openai_message(msg: Message) -> dict[str, Any]:
    """Convert a Lyra Message to OpenAI-compatible format (used by DeepSeek)."""
    base: dict[str, Any] = {"role": msg.role.value}

    if msg.role == MessageRole.TOOL and msg.tool_result:
        base["tool_call_id"] = msg.tool_result.tool_call_id
        base["content"] = msg.content
        return base

    if msg.role == MessageRole.ASSISTANT and msg.tool_calls:
        base["content"] = msg.content if isinstance(msg.content, str) else ""
        base["tool_calls"] = [
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
        return base

    base["content"] = msg.content if isinstance(msg.content, str) else str(msg.content)
    return base


def _from_openai_message(openai_msg: dict[str, Any]) -> Message:
    """Convert an OpenAI-compatible response message to Lyra format."""
    role_str = openai_msg.get("role", "assistant")
    try:
        role = MessageRole(role_str)
    except ValueError:
        role = MessageRole.ASSISTANT

    content = openai_msg.get("content", "") or ""

    tool_calls: list[ToolCall] | None = None
    raw_tool_calls = openai_msg.get("tool_calls", [])
    if raw_tool_calls:
        tool_calls = []
        for tc in raw_tool_calls:
            func = tc.get("function", {})
            try:
                arguments = json.loads(func.get("arguments", "{}"))
            except json.JSONDecodeError:
                arguments = {}
            tool_calls.append(ToolCall(
                id=tc.get("id", ""),
                name=func.get("name", ""),
                arguments=arguments,
            ))

    return Message(role=role, content=content, tool_calls=tool_calls)


# ────────────────────────────────────────────────────────────────────
# Tool translation
# ────────────────────────────────────────────────────────────────────


def _to_openai_tool(tool: ToolSchema) -> dict[str, Any]:
    """Convert a Lyra ToolSchema to OpenAI function format."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        },
    }


def _from_openai_usage(usage_data: dict[str, Any] | None) -> LLMUsage:
    """Convert OpenAI-compatible usage to Lyra LLMUsage."""
    if usage_data is None:
        return LLMUsage(input_tokens=0, output_tokens=0)
    return LLMUsage(
        input_tokens=usage_data.get("prompt_tokens", 0),
        output_tokens=usage_data.get("completion_tokens", 0),
    )


# ────────────────────────────────────────────────────────────────────
# Provider implementation
# ────────────────────────────────────────────────────────────────────


class DeepSeekProvider(AbstractProvider):
    """
    DeepSeek API provider adapter.

    DeepSeek uses an OpenAI-compatible API format. Key differences from
    Anthropic:
    - No native reasoning budget → Lyra injects thinking instructions into
      the system prompt via ``effort_instruction``
    - Tool calling is OpenAI-compatible (type: function)
    - Streaming uses standard SSE with ``data: [DONE]`` termination
    """

    _CONTEXT_WINDOWS: dict[str, int] = {
        "deepseek-chat-v4": 128_000,
        "deepseek-reasoner-v4": 128_000,
    }

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        self._base_url = config.base_url or "https://api.deepseek.com/v1"

    @property
    def provider_name(self) -> str:
        return "deepseek"

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Send a chat completion to DeepSeek and return the response.

        Effort is injected as a system-level thinking instruction since
        DeepSeek has no native reasoning_budget parameter.
        """
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
            provider="deepseek",
            raw=data,
        )

    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[StreamEvent]:
        """Stream a chat completion from DeepSeek and yield Lyra StreamEvents."""
        messages = self._build_messages(request)

        body: dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "messages": messages,
            "stream": True,
        }

        if request.tools:
            body["tools"] = [_to_openai_tool(t) for t in request.tools]

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

                        delta = event.get("choices", [{}])[0].get("delta", {})

                        # Check for tool calls in delta
                        tool_calls_delta = delta.get("tool_calls", [])
                        if tool_calls_delta:
                            for tc_delta in tool_calls_delta:
                                func = tc_delta.get("function", {})
                                if tc_delta.get("id"):
                                    # New tool call starting
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
                                # Check for tool call end (when delta has finish_reason)
                                if current_tool and event.get("choices", [{}])[0].get("finish_reason") == "tool_calls":
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

                        # Text content
                        content = delta.get("content", "")
                        if content:
                            yield StreamEvent(type="text_delta", content=content)

                        # Finish
                        finish_reason = event.get("choices", [{}])[0].get("finish_reason")
                        if finish_reason and finish_reason != "tool_calls":
                            usage = _from_openai_usage(event.get("usage"))
                            yield StreamEvent(type="done", usage=usage)

        except ImportError:
            yield StreamEvent(type="error", error="httpx not installed — required for DeepSeek provider")
        except Exception as e:
            yield StreamEvent(type="error", error=str(e))

    async def validate_api_key(self) -> bool:
        """Check the API key by listing models."""
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
        """Return well-known DeepSeek model IDs."""
        return list(self._CONTEXT_WINDOWS.keys())

    def supports_feature(self, feature: str) -> bool:
        return feature in {"tool_calling", "streaming"}

    def get_context_window(self, model: str) -> int:
        return self._CONTEXT_WINDOWS.get(model, 128_000)

    # ── Internal ─────────────────────────────────────────────────

    def _build_messages(self, request: ChatRequest) -> list[dict[str, Any]]:
        """
        Build the messages array, injecting effort instructions as a system
        message prefix when DeepSeek has no native reasoning budget.
        """
        messages = [_to_openai_message(m) for m in request.messages]

        # Inject effort instruction if provided (DeepSeek's effort mechanism)
        if request.effort_instruction:
            # Prepend or append to system message
            system_idx = next(
                (i for i, m in enumerate(messages) if m.get("role") == "system"),
                None,
            )
            if system_idx is not None:
                existing = messages[system_idx].get("content", "")
                messages[system_idx]["content"] = (
                    f"{request.effort_instruction}\n\n{existing}"
                )
            else:
                messages.insert(0, {
                    "role": "system",
                    "content": request.effort_instruction,
                })

        return messages

    async def _chat_via_http(self, request: ChatRequest, body: dict[str, Any]) -> ChatResponse:
        """Fallback using aiohttp."""
        try:
            import aiohttp
        except ImportError:
            raise ProviderError(
                code=ErrorCode.PROVIDER_ERROR,
                message="Neither httpx nor aiohttp available. Install one to use DeepSeekProvider.",
                provider="deepseek",
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
                if response.status >= 400:
                    error_text = await response.text()
                    raise ProviderError(
                        code=ErrorCode.PROVIDER_ERROR,
                        message=f"HTTP {response.status}: {error_text[:500]}",
                        provider="deepseek",
                    )
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
            provider="deepseek",
            raw=data,
        )

    @staticmethod
    def _translate_error(error: Exception) -> ProviderError:
        """Translate DeepSeek errors to Lyra ProviderError taxonomy."""
        msg = str(error).lower()
        if "401" in msg or "unauthorized" in msg:
            return ProviderError(code=ErrorCode.AUTH_ERROR, message=str(error), provider="deepseek")
        if "429" in msg or "rate limit" in msg:
            return ProviderError(code=ErrorCode.RATE_LIMIT, message=str(error), provider="deepseek", retryable=True)
        if "402" in msg or "insufficient" in msg:
            return ProviderError(code=ErrorCode.AUTH_ERROR, message=str(error), provider="deepseek")
        return ProviderError(code=ErrorCode.UNKNOWN, message=str(error), provider="deepseek")
