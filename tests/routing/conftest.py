"""
Shared fixtures for provider abstraction tests.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from pytest import FixtureRequest

from lyra.routing.provider.base import ProviderBackend
from lyra.routing.provider.types import (
    Capability,
    CompletionChunk,
    CompletionRequest,
    CompletionResponse,
    CostEstimate,
    EffortLevel,
    Message,
    ModelInfo,
    TokenUsage,
    ToolCall,
    ToolDef,
)


# ---------------------------------------------------------------------------
# Mock provider for unit-testing the router
# ---------------------------------------------------------------------------

class _MockProvider(ProviderBackend):
    """A mock provider that returns canned responses."""

    def __init__(
        self,
        name: str = "mock",
        capabilities: set[Capability] | None = None,
        fail: bool = False,
    ) -> None:
        self._name = name
        self._capabilities = capabilities or {Capability.TEXT_GENERATION}
        self._fail = fail
        self._last_request: CompletionRequest | None = None
        self._cost_override: CostEstimate | None = None

    @property
    def provider_name(self) -> str:
        return self._name

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        self._last_request = request
        if self._fail:
            msg = f"mock provider '{self._name}' intentionally failing"
            raise RuntimeError(msg)
        return CompletionResponse(
            content="mock response",
            tool_calls=None,
            usage=TokenUsage(input_tokens=10, output_tokens=10),
            finish_reason="stop",
            model="mock-model",
            latency_ms=10.0,
        )

    async def complete_stream(
        self,
        request: CompletionRequest,
    ) -> AsyncIterator[CompletionChunk]:
        self._last_request = request
        yield CompletionChunk(content_delta="mock ", finish_reason=None)
        yield CompletionChunk(content_delta="response", finish_reason="stop")

    def supports(self, capability: Capability) -> bool:
        return capability in self._capabilities

    def cost_estimate(self, request: CompletionRequest) -> CostEstimate:
        if self._cost_override is not None:
            return self._cost_override
        return CostEstimate(
            input_cost=0.001,
            output_cost=0.002,
            total_max_cost=0.003,
        )


@pytest.fixture
def mock_provider() -> _MockProvider:
    """A basic mock provider that succeeds."""
    return _MockProvider()


@pytest.fixture
def mock_provider_with_tools() -> _MockProvider:
    """A mock provider that supports tool use."""
    return _MockProvider(
        name="mock-tools",
        capabilities={Capability.TEXT_GENERATION, Capability.TOOL_USE},
    )


@pytest.fixture
def failing_mock_provider() -> _MockProvider:
    """A mock provider that raises on ``complete()``."""
    return _MockProvider(name="mock-fail", fail=True)


@pytest.fixture
def mock_provider_with_vision() -> _MockProvider:
    """A mock provider that supports vision."""
    return _MockProvider(
        name="mock-vision",
        capabilities={
            Capability.TEXT_GENERATION,
            Capability.VISION,
            Capability.TOOL_USE,
        },
    )


@pytest.fixture
def mock_model_infos() -> list[ModelInfo]:
    """List of mock model info typical for a provider."""
    return [
        ModelInfo(
            name="fast-model",
            provider="mock",
            capabilities={Capability.TEXT_GENERATION, Capability.TOOL_USE, Capability.STREAMING},
            context_window=32000,
            input_cost_per_1k=0.001,
            output_cost_per_1k=0.002,
            supports_effort=False,
            supports_streaming=True,
            supports_vision=False,
        ),
        ModelInfo(
            name="smart-model",
            provider="mock",
            capabilities={Capability.TEXT_GENERATION, Capability.TOOL_USE, Capability.STREAMING, Capability.VISION, Capability.JSON_MODE},
            context_window=128000,
            input_cost_per_1k=0.003,
            output_cost_per_1k=0.015,
            supports_effort=True,
            supports_streaming=True,
            supports_vision=True,
        ),
    ]


@pytest.fixture
def sample_messages() -> tuple[Message, ...]:
    """Common set of test messages."""
    return (
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="What is the capital of France?"),
    )


@pytest.fixture
def sample_tools() -> tuple[ToolDef, ...]:
    """Common set of test tool definitions."""
    return (
        ToolDef(
            name="get_weather",
            description="Get weather for a city",
            parameters={
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"},
                },
                "required": ["location"],
            },
        ),
    )


@pytest.fixture
def sample_completion_request(sample_messages: tuple[Message, ...]) -> CompletionRequest:
    """Standard completion request used across multiple test files."""
    return CompletionRequest(
        messages=sample_messages,
        model="claude-sonnet-4-6",
        max_tokens=100,
        temperature=0.0,
        effort=EffortLevel.MEDIUM,
    )
