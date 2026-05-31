"""
Canonical provider interface — the single abstraction every Lyra provider must implement.

This protocol normalizes:
- **Message format**: All providers accept/return the same Message types
- **Tool calling**: Unified ToolSchema and ToolCall, regardless of provider format
- **Streaming**: Single ``AsyncIterator[StreamEvent]`` across all providers
- **Token accounting**: Standardized ``LLMUsage`` from provider-specific usage fields
- **Errors**: Standardized ``ProviderError`` taxonomy

Design rationale: The provider abstraction sits at the BOUNDARY. Components above
this interface (router, skills, swarm, voice) contain ZERO provider-specific code.
Components below (individual adapters) contain ONLY provider-specific code. This is
the seam that makes Lyra multi-provider.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator


# ────────────────────────────────────────────────────────────────────
# Message types — Lyra canonical format
# ────────────────────────────────────────────────────────────────────


class MessageRole(str, Enum):
    """Canonical message roles across all providers."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True)
class ToolCall:
    """A tool call from the model (canonical format)."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    """A tool result returned to the model (canonical format)."""

    tool_call_id: str
    name: str
    content: str
    is_error: bool = False


@dataclass
class Message:
    """
    A single message in a conversation (canonical format).

    All provider adapters convert their native message schemas to/from this type.
    """

    role: MessageRole
    content: str | list[dict[str, Any]]
    tool_calls: list[ToolCall] | None = None
    tool_result: ToolResult | None = None
    name: str | None = None


# ────────────────────────────────────────────────────────────────────
# Tool schema — Lyra canonical format
# ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ToolSchema:
    """
    Tool definition in Lyra canonical format.

    All provider adapters convert their native tool schemas to/from this type.
    Uses JSON Schema for the parameters (the common denominator across providers).
    """

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema object


# ────────────────────────────────────────────────────────────────────
# Request / Response
# ────────────────────────────────────────────────────────────────────


@dataclass
class ChatRequest:
    """
    A chat completion request in Lyra canonical format.

    All providers accept this format. Adapters translate to provider-specific
    API parameters (budget_tokens for Anthropic, reasoning_effort for OpenAI, etc.).
    """

    messages: list[Message]
    model: str
    tools: list[ToolSchema] | None = None
    max_tokens: int = 4096
    temperature: float | None = None
    stream: bool = False
    # Provider-agnostic effort parameters (translated per-provider by the adapter)
    effort_budget_tokens: int | None = None
    effort_instruction: str | None = None
    effort_reasoning: str | None = None
    # Additional provider-specific passthrough (use sparingly)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMUsage:
    """Token usage across all providers (canonical format)."""

    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


@dataclass
class ChatResponse:
    """A chat completion response in Lyra canonical format."""

    content: str
    model: str
    usage: LLMUsage | None = None
    tool_calls: list[ToolCall] | None = None
    finish_reason: str = "stop"
    latency_ms: float = 0.0
    # Provider that served this response
    provider: str = ""
    # Raw provider response for debugging
    raw: Any = None


# ────────────────────────────────────────────────────────────────────
# Streaming
# ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class StreamEvent:
    """
    A single streaming event (canonical format).

    Types follow the SSE pattern:
    - ``text_delta``: A chunk of text content
    - ``tool_call_start``: A tool call has begun
    - ``tool_call_delta``: Arguments for an in-progress tool call
    - ``tool_call_end``: A tool call is complete
    - ``done``: Stream finished (usage data attached)
    - ``error``: Stream errored
    """

    type: str  # text_delta | tool_call_start | tool_call_delta | tool_call_end | done | error
    content: str = ""
    tool_call: ToolCall | None = None
    usage: LLMUsage | None = None
    error: str | None = None


# ────────────────────────────────────────────────────────────────────
# Error taxonomy
# ────────────────────────────────────────────────────────────────────


class ErrorCode(str, Enum):
    """Provider-agnostic error taxonomy."""

    AUTH_ERROR = "auth_error"
    RATE_LIMIT = "rate_limit"
    CONTEXT_OVERFLOW = "context_overflow"
    INVALID_REQUEST = "invalid_request"
    PROVIDER_ERROR = "provider_error"
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ProviderError(Exception):
    """Standardized error across all providers."""

    code: ErrorCode
    message: str
    provider: str = ""
    retryable: bool = False
    raw: Any = None

    def __str__(self) -> str:
        return f"[{self.provider}] {self.code.value}: {self.message}"


# ────────────────────────────────────────────────────────────────────
# Provider configuration
# ────────────────────────────────────────────────────────────────────


@dataclass
class ProviderConfig:
    """Configuration for a single provider instance."""

    provider: str
    api_key: str = ""
    base_url: str = ""
    default_model: str = ""
    max_retries: int = 3
    timeout_seconds: float = 120.0
    max_concurrent: int = 50
    extra: dict[str, Any] = field(default_factory=dict)


# ────────────────────────────────────────────────────────────────────
# Abstract Provider Protocol
# ────────────────────────────────────────────────────────────────────


class AbstractProvider(abc.ABC):
    """
    The canonical interface every Lyra provider must implement.

    Subclasses implement the provider-specific API translation. The rest of
    Lyra only depends on this abstract interface — never on concrete adapters.

    Implementors must handle:
    1. **Message translation**: Provider format ↔ Lyra Message
    2. **Tool schema translation**: Provider format ↔ Lyra ToolSchema
    3. **Streaming normalization**: Provider SSE → Lyra StreamEvent iterator
    4. **Usage extraction**: Provider usage fields → Lyra LLMUsage
    5. **Error normalization**: Provider error → Lyra ProviderError
    """

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Identifier for this provider (e.g. ``anthropic``, ``deepseek``)."""
        ...

    @abc.abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Send a chat completion request and return the complete response.

        Args:
            request: Canonical chat request.

        Returns:
            Complete chat response with content, usage, and optional tool calls.

        Raises:
            ProviderError: On any provider-level failure.
        """
        ...

    @abc.abstractmethod
    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[StreamEvent]:
        """
        Send a chat completion request and stream the response.

        Args:
            request: Canonical chat request with ``stream=True`` set.

        Yields:
            StreamEvent instances for each chunk, ending with ``type="done"``.
        """
        ...

    @abc.abstractmethod
    async def validate_api_key(self) -> bool:
        """Check whether the configured API key is valid."""
        ...

    @abc.abstractmethod
    async def list_models(self) -> list[str]:
        """Return available model IDs for this provider."""
        ...

    @abc.abstractmethod
    def supports_feature(self, feature: str) -> bool:
        """
        Check whether this provider supports a specific feature.

        Args:
            feature: Feature name (``tool_calling``, ``json_mode``,
                     ``vision``, ``streaming``, ``prompt_caching``).

        Returns:
            True if the provider supports the feature.
        """
        ...

    @abc.abstractmethod
    def get_context_window(self, model: str) -> int:
        """Return the context window size for a model, or a default."""
        ...
