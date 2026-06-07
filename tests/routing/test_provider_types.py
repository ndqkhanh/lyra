"""
Unit tests for provider abstraction data types.

Tests immutability, equality, defaults, and enum values.
"""

from __future__ import annotations

import pytest

from lyra.routing.provider.types import (
    Capability,
    CompletionChunk,
    CompletionRequest,
    CompletionResponse,
    CostEstimate,
    EffortLevel,
    Message,
    ModelInfo,
    RouteContext,
    RouteDecision,
    ToolCall,
    ToolDef,
    TokenUsage,
)


class TestMessage:
    """Message dataclass tests."""

    def test_create(self) -> None:
        msg = Message(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"
        assert msg.tool_calls is None
        assert msg.tool_call_id is None
        assert msg.name is None

    def test_frozen(self) -> None:
        msg = Message(role="user", content="hello")
        with pytest.raises(AttributeError):
            msg.role = "assistant"  # type: ignore[misc]

    def test_equality(self) -> None:
        a = Message(role="user", content="hello")
        b = Message(role="user", content="hello")
        assert a == b
        assert hash(a) == hash(b)

    def test_inequality(self) -> None:
        a = Message(role="user", content="hello")
        b = Message(role="assistant", content="hello")
        assert a != b


class TestToolDef:
    """ToolDef dataclass tests."""

    def test_create(self) -> None:
        td = ToolDef(
            name="get_weather",
            description="Get weather",
            parameters={"type": "object", "properties": {}},
        )
        assert td.name == "get_weather"
        assert td.parameters["type"] == "object"

    def test_frozen(self) -> None:
        td = ToolDef(name="t", description="d", parameters={})
        with pytest.raises(AttributeError):
            td.name = "new_name"  # type: ignore[misc]


class TestToolCall:
    """ToolCall dataclass tests."""

    def test_create(self) -> None:
        tc = ToolCall(id="call_1", name="get_weather", arguments={"location": "Paris"})
        assert tc.id == "call_1"
        assert tc.arguments["location"] == "Paris"

    def test_defaults(self) -> None:
        tc = ToolCall(id="call_1", name="get_weather", arguments={"location": "Paris"})
        assert tc.arguments == {"location": "Paris"}


class TestTokenUsage:
    """TokenUsage dataclass tests."""

    def test_defaults(self) -> None:
        usage = TokenUsage()
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.cache_read_tokens == 0
        assert usage.cache_write_tokens == 0

    def test_create(self) -> None:
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50

    def test_cache_fields(self) -> None:
        usage = TokenUsage(
            input_tokens=100,
            output_tokens=50,
            cache_read_tokens=30,
            cache_write_tokens=20,
        )
        assert usage.cache_read_tokens == 30
        assert usage.cache_write_tokens == 20


class TestCompletionRequest:
    """CompletionRequest dataclass tests."""

    def test_defaults(self) -> None:
        req = CompletionRequest(
            messages=(Message(role="user", content="hi"),),
            model="test-model",
        )
        assert req.max_tokens == 4096
        assert req.temperature == 0.0
        assert req.tools is None
        assert req.effort == EffortLevel.MEDIUM

    def test_create(self) -> None:
        msg = Message(role="user", content="hello")
        req = CompletionRequest(
            messages=(msg,),
            model="test-model",
            max_tokens=100,
            temperature=0.7,
            effort=EffortLevel.HIGH,
        )
        assert req.model == "test-model"
        assert req.effort == EffortLevel.HIGH

    def test_frozen(self) -> None:
        req = CompletionRequest(
            messages=(Message(role="user", content="hi"),),
            model="test-model",
        )
        with pytest.raises(AttributeError):
            req.model = "other"  # type: ignore[misc]


class TestCompletionResponse:
    """CompletionResponse dataclass tests."""

    def test_create(self) -> None:
        resp = CompletionResponse(
            content="Hello!",
            tool_calls=None,
            usage=TokenUsage(input_tokens=10, output_tokens=5),
            finish_reason="stop",
            model="test-model",
            latency_ms=100.0,
        )
        assert resp.content == "Hello!"
        assert resp.finish_reason == "stop"
        assert resp.latency_ms == 100.0

    def test_with_tool_calls(self) -> None:
        tc = ToolCall(id="call_1", name="get_weather", arguments={"location": "Paris"})
        resp = CompletionResponse(
            content="",
            tool_calls=(tc,),
            usage=TokenUsage(input_tokens=10, output_tokens=5),
            finish_reason="tool_use",
            model="test-model",
            latency_ms=100.0,
        )
        assert resp.tool_calls is not None
        assert len(resp.tool_calls) == 1


class TestCompletionChunk:
    """CompletionChunk dataclass tests."""

    def test_defaults(self) -> None:
        chunk = CompletionChunk()
        assert chunk.content_delta == ""
        assert chunk.tool_call_delta is None
        assert chunk.finish_reason is None

    def test_with_content(self) -> None:
        chunk = CompletionChunk(content_delta="hello")
        assert chunk.content_delta == "hello"


class TestCostEstimate:
    """CostEstimate dataclass tests."""

    def test_defaults(self) -> None:
        cost = CostEstimate()
        assert cost.input_cost == 0.0
        assert cost.total_max_cost == 0.0

    def test_create(self) -> None:
        cost = CostEstimate(input_cost=0.001, output_cost=0.002, total_max_cost=0.003)
        assert cost.total_max_cost == 0.003


class TestModelInfo:
    """ModelInfo dataclass tests."""

    def test_create(self) -> None:
        info = ModelInfo(
            name="claude-sonnet-4-6",
            provider="anthropic",
            capabilities={Capability.TEXT_GENERATION, Capability.TOOL_USE},
            context_window=200000,
        )
        assert info.name == "claude-sonnet-4-6"
        assert info.supports_streaming is True
        assert info.supports_vision is False

    def test_defaults(self) -> None:
        info = ModelInfo(
            name="test",
            provider="test",
            capabilities=set(),
            context_window=4096,
        )
        assert info.input_cost_per_1k == 0.0
        assert info.supports_effort is False


class TestRouteDecision:
    """RouteDecision dataclass tests."""

    def test_create(self) -> None:
        decision = RouteDecision(
            provider_name="anthropic",
            model="claude-sonnet-4-6",
            effort=EffortLevel.MEDIUM,
        )
        assert decision.provider_name == "anthropic"
        assert decision.effort == EffortLevel.MEDIUM
        assert decision.fallback_chain == ()

    def test_with_fallback(self) -> None:
        fallback = RouteDecision(
            provider_name="deepseek",
            model="deepseek-chat",
            effort=EffortLevel.LOW,
        )
        primary = RouteDecision(
            provider_name="anthropic",
            model="claude-sonnet-4-6",
            effort=EffortLevel.HIGH,
            fallback_chain=(fallback,),
        )
        assert len(primary.fallback_chain) == 1


class TestRouteContext:
    """RouteContext dataclass tests."""

    def test_defaults(self) -> None:
        ctx = RouteContext()
        assert ctx.task_type == "standard"
        assert ctx.budget_remaining == 10.0
        assert ctx.requires_vision is False

    def test_create(self) -> None:
        ctx = RouteContext(
            task_type="complex_reasoning",
            estimated_complexity="high",
            requires_vision=True,
        )
        assert ctx.task_type == "complex_reasoning"
        assert ctx.requires_vision is True


class TestCapability:
    """Capability enum tests."""

    def test_values(self) -> None:
        assert Capability.TEXT_GENERATION.value == "text_generation"
        assert Capability.TOOL_USE.value == "tool_use"
        assert Capability.VISION.value == "vision"
        assert Capability.STREAMING.value == "streaming"
        assert Capability.JSON_MODE.value == "json_mode"
        assert Capability.LONG_CONTEXT.value == "long_context"
        assert Capability.AUDIO_INPUT.value == "audio_input"
        assert Capability.AUDIO_OUTPUT.value == "audio_output"

    def test_unique(self) -> None:
        values = [c.value for c in Capability]
        assert len(values) == len(set(values))


class TestEffortLevel:
    """EffortLevel enum tests."""

    def test_values(self) -> None:
        assert EffortLevel.LOW.value == "low"
        assert EffortLevel.MEDIUM.value == "medium"
        assert EffortLevel.HIGH.value == "high"
        assert EffortLevel.XHIGH.value == "xhigh"
        assert EffortLevel.MAX.value == "max"

    def test_order(self) -> None:
        levels = [EffortLevel.LOW, EffortLevel.MEDIUM, EffortLevel.HIGH, EffortLevel.XHIGH, EffortLevel.MAX]
        # Just verify we can enumerate in order
        assert len(levels) == 5
