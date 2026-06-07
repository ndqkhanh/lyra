"""
Data types for the provider abstraction layer.

All data classes are frozen (immutable) and support equality comparison.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Capability(Enum):
    """Capabilities that a provider backend can support."""

    TEXT_GENERATION = "text_generation"
    TOOL_USE = "tool_use"
    VISION = "vision"
    STREAMING = "streaming"
    JSON_MODE = "json_mode"
    LONG_CONTEXT = "long_context"
    AUDIO_INPUT = "audio_input"
    AUDIO_OUTPUT = "audio_output"


class EffortLevel(Enum):
    """Reasoning effort level for model calls."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"
    MAX = "max"


@dataclass(frozen=True)
class Message:
    """A normalized message in a conversation.

    Args:
        role: One of "system", "user", "assistant", "tool".
        content: Text content of the message.
        tool_calls: Tool calls associated with an assistant message.
        tool_call_id: ID of the tool call this message is responding to.
        name: Name of the tool that produced this result.
    """

    role: str
    content: str
    tool_calls: tuple[ToolCall, ...] | None = None
    tool_call_id: str | None = None
    name: str | None = None


@dataclass(frozen=True)
class ToolDef:
    """Definition of a tool that can be provided to a model.

    Args:
        name: Unique tool name.
        description: Human-readable description.
        parameters: JSON Schema object describing the parameters.
    """

    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    """A tool call returned by the model.

    Args:
        id: Unique identifier for this tool call invocation.
        name: Name of the tool to invoke.
        arguments: Dictionary of argument values.
    """

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class TokenUsage:
    """Token usage for a completion response.

    Args:
        input_tokens: Number of input (prompt) tokens.
        output_tokens: Number of output (completion) tokens.
        cache_read_tokens: Tokens read from cache.
        cache_write_tokens: Tokens written to cache.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


@dataclass(frozen=True)
class CompletionRequest:
    """A request to a provider backend to generate a completion.

    Args:
        messages: Conversation history.
        model: Model identifier string.
        max_tokens: Maximum tokens to generate.
        temperature: Sampling temperature (0.0-1.0).
        tools: Optional tool definitions.
        effort: Reasoning effort level.
    """

    messages: tuple[Message, ...]
    model: str
    max_tokens: int = 4096
    temperature: float = 0.0
    tools: tuple[ToolDef, ...] | None = None
    effort: EffortLevel = EffortLevel.MEDIUM


@dataclass(frozen=True)
class CompletionResponse:
    """A complete response from a provider backend.

    Args:
        content: Generated text content.
        tool_calls: Tool calls requested by the model.
        usage: Token usage statistics.
        finish_reason: Reason the generation finished (e.g. "end_turn",
            "stop_sequence", "max_tokens", "tool_use").
        model: Model that generated this response.
        latency_ms: Wall-clock time for the request in milliseconds.
    """

    content: str
    tool_calls: tuple[ToolCall, ...] | None
    usage: TokenUsage
    finish_reason: str
    model: str
    latency_ms: float


@dataclass(frozen=True)
class CompletionChunk:
    """A streaming chunk from a provider backend.

    Args:
        content_delta: Incremental text content.
        tool_call_delta: Partial JSON for a tool call argument.
        finish_reason: Set on the final chunk when generation finishes.
    """

    content_delta: str = ""
    tool_call_delta: str | None = None
    finish_reason: str | None = None


@dataclass(frozen=True)
class CostEstimate:
    """Estimated cost of a completion request in USD.

    Args:
        input_cost: Estimated cost for input tokens.
        output_cost: Estimated cost for output tokens.
        total_max_cost: Maximum total cost (input + worst-case output).
    """

    input_cost: float = 0.0
    output_cost: float = 0.0
    total_max_cost: float = 0.0


@dataclass(frozen=True)
class ModelInfo:
    """Metadata about a specific model available through a provider.

    Args:
        name: Model identifier string.
        provider: Provider name.
        capabilities: Set of capabilities this model supports.
        context_window: Maximum context window in tokens.
        input_cost_per_1k: Cost per 1K input tokens in USD.
        output_cost_per_1k: Cost per 1K output tokens in USD.
        supports_effort: Whether this model supports reasoning effort levels.
        supports_streaming: Whether this model supports streaming.
        supports_vision: Whether this model supports vision inputs.
    """

    name: str
    provider: str
    capabilities: set[Capability]
    context_window: int
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0
    supports_effort: bool = False
    supports_streaming: bool = True
    supports_vision: bool = False


@dataclass(frozen=True)
class RouteDecision:
    """The result of routing a request to a provider/model combination.

    Args:
        provider_name: Selected provider.
        model: Selected model name.
        effort: Recommended effort level.
        fallback_chain: Ordered list of fallback decisions.
        estimated_cost: Estimated cost for this route.
    """

    provider_name: str
    model: str
    effort: EffortLevel
    fallback_chain: tuple[RouteDecision, ...] = ()
    estimated_cost: CostEstimate | None = None


@dataclass(frozen=True)
class RouteContext:
    """Context information used by the router to make routing decisions.

    Args:
        task_type: Type of task (e.g. "simple_lookup", "standard",
            "complex_reasoning", "research").
        estimated_complexity: Estimated complexity ("low", "medium",
            "high", "research").
        requires_vision: Whether the task requires vision capability.
        requires_json_mode: Whether the task requires JSON mode.
        budget_remaining: Remaining budget in USD for the session.
    """

    task_type: str = "standard"
    estimated_complexity: str = "medium"
    requires_vision: bool = False
    requires_json_mode: bool = False
    budget_remaining: float = 10.0
