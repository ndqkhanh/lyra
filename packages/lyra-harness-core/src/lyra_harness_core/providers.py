"""Multi-provider abstraction layer — normalized interface across LLM providers.

Supports: Claude (Anthropic), DeepSeek, Qwen, GPT (OpenAI), open-weights (Ollama/vLLM).

Key features:
- Streaming generation (async iterator of token chunks)
- Token usage tracking with cost accounting
- Provider registry with health checks and circuit breaker pattern
- Normalized tool-call schema across all providers
- Provider-aware message format conversion
"""
from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .messages import Message, StopReason, ToolCall

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ProviderKind(str, Enum):
    """Known LLM provider families."""

    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    OPENAI = "openai"
    OPEN_WEIGHTS = "open_weights"  # Ollama, vLLM, etc.
    MOCK = "mock"


class ProviderHealth(str, Enum):
    """Health status of a registered provider."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Data transfer objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TokenUsage:
    """Token accounting for a single generation call."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    total_tokens: int = 0

    @property
    def cache_hit_ratio(self) -> float:
        if self.input_tokens == 0:
            return 0.0
        return self.cache_read_tokens / self.input_tokens


@dataclass(frozen=True)
class StreamChunk:
    """A single chunk from a streaming generation."""

    content: str = ""
    tool_call: ToolCall | None = None
    stop_reason: StopReason | None = None
    usage: TokenUsage | None = None


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""

    kind: ProviderKind
    model: str
    api_key: str = ""
    base_url: str = ""
    max_tokens: int = 4096
    temperature: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderInfo:
    """Runtime information about a registered provider."""

    config: ProviderConfig
    health: ProviderHealth = ProviderHealth.UNKNOWN
    last_health_check: float = 0.0
    consecutive_failures: int = 0
    total_requests: int = 0
    total_tokens: int = 0
    total_errors: int = 0

    @property
    def error_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_errors / self.total_requests


# ---------------------------------------------------------------------------
# Abstract provider
# ---------------------------------------------------------------------------


class LLMProvider(ABC):
    """Abstract LLM provider with streaming and token accounting.

    Subclasses implement ``_generate_impl`` and optionally ``_stream_impl``.
    """

    kind: ProviderKind

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    # -- Synchronous ----------------------------------------------------------

    @abstractmethod
    def generate(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> Message:
        """Return one assistant Message (may contain tool_calls)."""
        raise NotImplementedError

    # -- Streaming ------------------------------------------------------------

    async def stream_generate(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> AsyncIterator[StreamChunk]:
        """Stream token-by-token output as an async iterator.

        Default implementation calls `generate()` and yields a single chunk.
        Providers with native streaming support should override this.
        """
        msg = self.generate(messages, tools, max_tokens, temperature)
        yield StreamChunk(
            content=msg.content,
            stop_reason=msg.stop_reason,
        )

    # -- Health ---------------------------------------------------------------

    async def health_check(self) -> ProviderHealth:
        """Verify the provider is reachable and functional."""
        try:
            msg = self.generate(
                [Message.user(content="ping")],
                max_tokens=4,
            )
            return ProviderHealth.HEALTHY if msg.content else ProviderHealth.DEGRADED
        except Exception:
            return ProviderHealth.UNHEALTHY

    # -- Token accounting -----------------------------------------------------

    @property
    def total_input_tokens(self) -> int:
        return self._total_input_tokens

    @property
    def total_output_tokens(self) -> int:
        return self._total_output_tokens

    def _record_usage(self, input_tokens: int, output_tokens: int) -> None:
        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens


# ---------------------------------------------------------------------------
# Provider Registry
# ---------------------------------------------------------------------------


class ProviderRegistry:
    """Registry of LLM providers with health monitoring and failover.

    Supports:
    - Registering multiple providers per kind
    - Health checking with circuit breaker pattern
    - Default provider selection
    - Failover to fallback providers on failure
    """

    def __init__(self) -> None:
        self._providers: dict[str, tuple[LLMProvider, ProviderInfo]] = {}
        self._default_name: str | None = None

    # -- Registration ---------------------------------------------------------

    def register(
        self,
        name: str,
        provider: LLMProvider,
        set_default: bool = False,
    ) -> None:
        """Register a provider under a unique name."""
        if name in self._providers:
            raise ValueError(f"Provider {name!r} already registered")
        self._providers[name] = (provider, ProviderInfo(config=provider.config))
        if set_default or self._default_name is None:
            self._default_name = name
        logger.info("Registered provider %s (kind=%s, model=%s, default=%s)",
                     name, provider.kind.value, provider.config.model, set_default)

    def unregister(self, name: str) -> None:
        """Remove a provider from the registry."""
        self._providers.pop(name, None)
        if self._default_name == name:
            self._default_name = next(iter(self._providers), None)

    def set_default(self, name: str) -> None:
        """Set the default provider by name."""
        if name not in self._providers:
            raise KeyError(f"Provider {name!r} not registered")
        self._default_name = name

    # -- Access ---------------------------------------------------------------

    def get(self, name: str | None = None) -> LLMProvider | None:
        """Get a provider by name, or the default provider."""
        key = name or self._default_name
        if key is None:
            return None
        entry = self._providers.get(key)
        return entry[0] if entry else None

    def get_info(self, name: str | None = None) -> ProviderInfo | None:
        """Get runtime info for a provider."""
        key = name or self._default_name
        if key is None:
            return None
        entry = self._providers.get(key)
        return entry[1] if entry else None

    def list_providers(self) -> dict[str, ProviderInfo]:
        """Return all registered providers and their info."""
        return {name: info for name, (_, info) in self._providers.items()}

    def list_by_kind(self, kind: ProviderKind) -> list[str]:
        """Return names of providers matching a kind."""
        return [
            name
            for name, (prov, _) in self._providers.items()
            if prov.kind == kind
        ]

    # -- Health ---------------------------------------------------------------

    async def health_check_all(self) -> dict[str, ProviderHealth]:
        """Run health checks on all registered providers."""
        results: dict[str, ProviderHealth] = {}
        for name, (provider, info) in self._providers.items():
            health = await provider.health_check()
            info.health = health
            info.last_health_check = time.time()
            results[name] = health
        return results

    async def health_check(self, name: str) -> ProviderHealth:
        """Run health check on a specific provider."""
        entry = self._providers.get(name)
        if entry is None:
            raise KeyError(f"Provider {name!r} not found")
        provider, info = entry
        health = await provider.health_check()
        info.health = health
        info.last_health_check = time.time()
        return health

    def record_failure(self, name: str) -> None:
        """Record a provider failure for circuit breaker tracking."""
        entry = self._providers.get(name)
        if entry is None:
            return
        _, info = entry
        info.consecutive_failures += 1
        info.total_errors += 1
        if info.consecutive_failures >= 3:
            info.health = ProviderHealth.DEGRADED
        if info.consecutive_failures >= 5:
            info.health = ProviderHealth.UNHEALTHY

    def record_success(self, name: str, tokens: int = 0) -> None:
        """Record a successful provider call."""
        entry = self._providers.get(name)
        if entry is None:
            return
        _, info = entry
        info.consecutive_failures = 0
        info.total_requests += 1
        info.total_tokens += tokens
        if info.health == ProviderHealth.DEGRADED:
            info.health = ProviderHealth.HEALTHY

    def get_healthy(
        self,
        kind: ProviderKind | None = None,
    ) -> list[str]:
        """Return names of healthy providers, optionally filtered by kind."""
        return [
            name
            for name, (prov, info) in self._providers.items()
            if info.health in (ProviderHealth.HEALTHY, ProviderHealth.UNKNOWN)
            and (kind is None or prov.kind == kind)
        ]

    @property
    def default_name(self) -> str | None:
        return self._default_name


# ---------------------------------------------------------------------------
# Anthropic provider
# ---------------------------------------------------------------------------


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider with native streaming."""

    kind = ProviderKind.ANTHROPIC

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        try:
            import anthropic
        except ImportError as e:
            raise ImportError(
                "anthropic package not installed. "
                "Install with: pip install anthropic"
            ) from e
        self._client = anthropic.Anthropic(
            api_key=config.api_key,
            base_url=config.base_url or None,
        )

    def generate(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> Message:
        system, turns = _to_anthropic_format(messages)
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": max(max_tokens, self.config.max_tokens),
            "temperature": temperature or self.config.temperature,
            "messages": turns,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools

        resp = self._client.messages.create(**kwargs)
        self._record_usage(
            getattr(resp.usage, "input_tokens", 0),
            getattr(resp.usage, "output_tokens", 0),
        )
        return _anthropic_response_to_msg(resp)

    async def stream_generate(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> AsyncIterator[StreamChunk]:
        system, turns = _to_anthropic_format(messages)
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": max(max_tokens, self.config.max_tokens),
            "temperature": temperature or self.config.temperature,
            "messages": turns,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools

        with self._client.messages.stream(**kwargs) as stream:
            for event in stream:
                if event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        yield StreamChunk(content=event.delta.text)
                elif event.type == "message_delta":
                    yield StreamChunk(
                        stop_reason=StopReason(event.delta.stop_reason)
                        if event.delta.stop_reason
                        else None,
                    )
                elif event.type == "message_complete":
                    usage = event.usage
                    token_usage = TokenUsage(
                        input_tokens=getattr(usage, "input_tokens", 0),
                        output_tokens=getattr(usage, "output_tokens", 0),
                    )
                    self._record_usage(token_usage.input_tokens, token_usage.output_tokens)
                    yield StreamChunk(usage=token_usage)


def _to_anthropic_format(
    messages: list[Message],
) -> tuple[str, list[dict[str, Any]]]:
    """Convert Lyra Messages to Anthropic API format."""
    system = ""
    turns: list[dict[str, Any]] = []
    for m in messages:
        if m.role == "system":
            system = m.content
        elif m.role == "tool":
            content = [
                {
                    "type": "tool_result",
                    "tool_use_id": r.call_id,
                    "content": r.content,
                    "is_error": r.is_error,
                }
                for r in m.tool_results
            ]
            turns.append({"role": "user", "content": content})
        else:
            parts: list[dict[str, Any]] = []
            if m.content:
                parts.append({"type": "text", "text": m.content})
            for c in m.tool_calls:
                parts.append({
                    "type": "tool_use",
                    "id": c.id,
                    "name": c.name,
                    "input": c.args,
                })
            turns.append({"role": m.role, "content": parts or m.content})
    return system, turns


def _anthropic_response_to_msg(resp: Any) -> Message:
    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    for block in getattr(resp, "content", []):
        if getattr(block, "type", None) == "text":
            text_parts.append(block.text)
        elif getattr(block, "type", None) == "tool_use":
            tool_calls.append(
                ToolCall(id=block.id, name=block.name, args=dict(block.input or {}))
            )
    stop_raw = getattr(resp, "stop_reason", "end_turn")
    try:
        stop = StopReason(stop_raw)
    except ValueError:
        stop = StopReason.END_TURN
    return Message.assistant(
        content="\n".join(text_parts),
        tool_calls=tool_calls,
        stop_reason=stop,
    )


# ---------------------------------------------------------------------------
# OpenAI-compatible provider (GPT, DeepSeek, Qwen, open-weights)
# ---------------------------------------------------------------------------


class OpenAICompatibleProvider(LLMProvider):
    """Provider for any OpenAI-compatible API (GPT, DeepSeek, Qwen, Ollama, vLLM).

    Uses the openai Python SDK. Set ``kind`` via ProviderKind in config.
    """

    kind = ProviderKind.OPENAI  # overridden per-instance via config

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        self.kind = config.kind
        try:
            from openai import AsyncOpenAI, OpenAI
        except ImportError as e:
            raise ImportError(
                "openai package not installed. "
                "Install with: pip install openai"
            ) from e

        api_key = config.api_key or "not-needed"
        base_url = config.base_url or None

        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    def generate(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> Message:
        oai_messages, oai_tools = _to_openai_format(messages, tools)
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": max(max_tokens, self.config.max_tokens),
            "temperature": temperature or self.config.temperature,
            "messages": oai_messages,
        }
        if oai_tools:
            kwargs["tools"] = oai_tools

        resp = self._client.chat.completions.create(**kwargs)
        usage = resp.usage
        if usage:
            self._record_usage(
                getattr(usage, "prompt_tokens", 0),
                getattr(usage, "completion_tokens", 0),
            )
        return _openai_response_to_msg(resp)

    async def stream_generate(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> AsyncIterator[StreamChunk]:
        oai_messages, oai_tools = _to_openai_format(messages, tools)
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": max(max_tokens, self.config.max_tokens),
            "temperature": temperature or self.config.temperature,
            "messages": oai_messages,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if oai_tools:
            kwargs["tools"] = oai_tools

        stream = await self._async_client.chat.completions.create(**kwargs)
        tool_call_buf: dict[int, dict[str, Any]] = {}

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue

            if delta.content:
                yield StreamChunk(content=delta.content)

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_call_buf:
                        tool_call_buf[idx] = {
                            "id": tc.id or "",
                            "name": tc.function.name if tc.function else "",
                            "args": "",
                        }
                    if tc.id:
                        tool_call_buf[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_call_buf[idx]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_call_buf[idx]["args"] += tc.function.arguments

            if chunk.choices[0].finish_reason:
                reason = chunk.choices[0].finish_reason
                stop = _openai_stop_reason(reason)
                yield StreamChunk(stop_reason=stop)

            if chunk.usage:
                yield StreamChunk(usage=TokenUsage(
                    input_tokens=getattr(chunk.usage, "prompt_tokens", 0),
                    output_tokens=getattr(chunk.usage, "completion_tokens", 0),
                ))


def _to_openai_format(
    messages: list[Message],
    tools: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]] | None]:
    """Convert Lyra Messages to OpenAI-compatible format."""
    oai_messages: list[dict[str, Any]] = []
    for m in messages:
        if m.role == "tool":
            for r in m.tool_results:
                oai_messages.append({
                    "role": "tool",
                    "tool_call_id": r.call_id,
                    "content": r.content,
                })
        else:
            msg: dict[str, Any] = {
                "role": m.role if m.role != "tool" else "assistant",
            }
            if m.content:
                msg["content"] = m.content
            if m.tool_calls:
                msg["tool_calls"] = [
                    {
                        "id": c.id,
                        "type": "function",
                        "function": {"name": c.name, "arguments": str(c.args)},
                    }
                    for c in m.tool_calls
                ]
            oai_messages.append(msg)

    oai_tools = None
    if tools:
        oai_tools = []
        for t in tools:
            oai_tools.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {}),
                },
            })
    return oai_messages, oai_tools


def _openai_response_to_msg(resp: Any) -> Message:
    choice = resp.choices[0]
    msg = choice.message
    content = msg.content or ""
    tool_calls: list[ToolCall] = []
    if msg.tool_calls:
        for tc in msg.tool_calls:
            tool_calls.append(
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    args=_parse_json_args(tc.function.arguments),
                )
            )
    stop = _openai_stop_reason(choice.finish_reason)
    return Message.assistant(content=content, tool_calls=tool_calls, stop_reason=stop)


def _openai_stop_reason(reason: str | None) -> StopReason:
    mapping = {
        "stop": StopReason.END_TURN,
        "length": StopReason.MAX_TOKENS,
        "tool_calls": StopReason.TOOL_USE,
    }
    return mapping.get(reason or "", StopReason.END_TURN)


def _parse_json_args(args_str: str) -> dict[str, Any]:
    import json

    try:
        return json.loads(args_str)
    except (json.JSONDecodeError, TypeError):
        return {}


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_provider(config: ProviderConfig) -> LLMProvider:
    """Create a provider instance from configuration.

    >>> config = ProviderConfig(kind=ProviderKind.ANTHROPIC, model="claude-sonnet-4-6", api_key="...")
    >>> provider = create_provider(config)
    """
    if config.kind == ProviderKind.ANTHROPIC:
        return AnthropicProvider(config)
    if config.kind in (
        ProviderKind.OPENAI,
        ProviderKind.DEEPSEEK,
        ProviderKind.QWEN,
        ProviderKind.OPEN_WEIGHTS,
    ):
        return OpenAICompatibleProvider(config)
    raise ValueError(f"Unsupported provider kind: {config.kind}")


def create_provider_registry() -> ProviderRegistry:
    """Build a registry and auto-register providers from environment variables.

    Environment variables checked:
    - ANTHROPIC_API_KEY → Claude
    - DEEPSEEK_API_KEY → DeepSeek
    - QWEN_API_KEY → Qwen
    - OPENAI_API_KEY → GPT-4o
    - OLLAMA_BASE_URL → local Ollama
    """
    registry = ProviderRegistry()

    if key := os.environ.get("ANTHROPIC_API_KEY", "").strip():
        registry.register(
            "claude",
            AnthropicProvider(ProviderConfig(
                kind=ProviderKind.ANTHROPIC,
                model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
                api_key=key,
                base_url=os.environ.get("ANTHROPIC_BASE_URL", ""),
            )),
            set_default=True,
        )

    if key := os.environ.get("DEEPSEEK_API_KEY", "").strip():
        registry.register(
            "deepseek",
            OpenAICompatibleProvider(ProviderConfig(
                kind=ProviderKind.DEEPSEEK,
                model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
                api_key=key,
                base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            )),
            set_default=registry.default_name is None,
        )

    if key := os.environ.get("QWEN_API_KEY", "").strip():
        registry.register(
            "qwen",
            OpenAICompatibleProvider(ProviderConfig(
                kind=ProviderKind.QWEN,
                model=os.environ.get("QWEN_MODEL", "qwen-max"),
                api_key=key,
                base_url=os.environ.get("QWEN_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"),
            )),
        )

    if key := os.environ.get("OPENAI_API_KEY", "").strip():
        registry.register(
            "gpt",
            OpenAICompatibleProvider(ProviderConfig(
                kind=ProviderKind.OPENAI,
                model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
                api_key=key,
            )),
            set_default=registry.default_name is None,
        )

    if url := os.environ.get("OLLAMA_BASE_URL", "").strip():
        registry.register(
            "ollama",
            OpenAICompatibleProvider(ProviderConfig(
                kind=ProviderKind.OPEN_WEIGHTS,
                model=os.environ.get("OLLAMA_MODEL", "llama3"),
                api_key="ollama",
                base_url=url.rstrip("/") + "/v1",
            )),
        )

    return registry


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_provider_registry: ProviderRegistry | None = None


def get_provider_registry() -> ProviderRegistry:
    """Return the global provider registry singleton."""
    global _provider_registry
    if _provider_registry is None:
        _provider_registry = create_provider_registry()
    return _provider_registry
