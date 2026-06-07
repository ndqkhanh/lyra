"""
Integration tests for the Anthropic adapter.

These tests require a valid ``ANTHROPIC_API_KEY`` environment variable.
If it is not set the tests are skipped.
"""

from __future__ import annotations

import os

import pytest
from pytest import FixtureRequest

from src.routing.provider.adapters.anthropic import AnthropicAdapter
from src.routing.provider.types import (
    Capability,
    CompletionRequest,
    EffortLevel,
    Message,
    ToolDef,
)


# ---------------------------------------------------------------------------
# Skip if no API key
# ---------------------------------------------------------------------------
pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY environment variable not set",
)

integration = pytest.mark.integration


@pytest.fixture
def adapter() -> AnthropicAdapter:
    """AnthropicAdapter instance with API key from environment."""
    return AnthropicAdapter()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_simple_completion(adapter: AnthropicAdapter) -> None:
    """Test a basic text completion."""
    request = CompletionRequest(
        messages=(
            Message(role="user", content="Say exactly 'hello world' and nothing else."),
        ),
        model="claude-sonnet-4-6",
        max_tokens=50,
        temperature=0.0,
        effort=EffortLevel.LOW,
    )
    response = await adapter.complete(request)

    assert response.content
    assert response.finish_reason in ("end_turn", "stop")
    assert response.usage.input_tokens > 0
    assert response.usage.output_tokens > 0
    assert response.latency_ms > 0
    assert response.model


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tool_use(adapter: AnthropicAdapter) -> None:
    """Test a completion with tool definitions."""
    request = CompletionRequest(
        messages=(
            Message(role="user", content="What's the weather in Paris? Use the get_weather tool."),
        ),
        model="claude-sonnet-4-6",
        max_tokens=200,
        temperature=0.0,
        tools=(
            ToolDef(
                name="get_weather",
                description="Get current weather for a city",
                parameters={
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City name",
                        },
                    },
                    "required": ["location"],
                },
            ),
        ),
        effort=EffortLevel.MEDIUM,
    )
    response = await adapter.complete(request)

    # The model should either respond with text or call the tool
    assert response.content or response.tool_calls
    assert response.usage.input_tokens > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_streaming(adapter: AnthropicAdapter) -> None:
    """Test streaming completion."""
    request = CompletionRequest(
        messages=(
            Message(role="user", content="Count from 1 to 3, one number per line."),
        ),
        model="claude-sonnet-4-6",
        max_tokens=50,
        temperature=0.0,
        effort=EffortLevel.LOW,
    )
    chunks: list[str] = []
    async for chunk in adapter.complete_stream(request):
        if chunk.content_delta:
            chunks.append(chunk.content_delta)

    assert len(chunks) > 0
    assert any("1" in c for c in chunks) or any("2" in c for c in chunks)


@pytest.mark.integration
def test_cost_estimate(adapter: AnthropicAdapter) -> None:
    """Test cost estimation."""
    request = CompletionRequest(
        messages=(
            Message(role="system", content="You are helpful."),
            Message(role="user", content="What is the capital of France?" * 100),
        ),
        model="claude-sonnet-4-6",
        max_tokens=100,
        effort=EffortLevel.MEDIUM,
    )
    cost = adapter.cost_estimate(request)

    assert cost.input_cost > 0
    assert cost.output_cost > 0
    assert cost.total_max_cost > 0
    assert cost.total_max_cost >= cost.input_cost + cost.output_cost - 0.0001


class TestSupports:
    """AnthropicAdapter.supports() tests."""

    def test_supported_capabilities(self, adapter: AnthropicAdapter) -> None:
        assert adapter.supports(Capability.TEXT_GENERATION)
        assert adapter.supports(Capability.TOOL_USE)
        assert adapter.supports(Capability.VISION)
        assert adapter.supports(Capability.STREAMING)
        assert adapter.supports(Capability.JSON_MODE)
        assert adapter.supports(Capability.LONG_CONTEXT)

    def test_unsupported_capabilities(self, adapter: AnthropicAdapter) -> None:
        assert not adapter.supports(Capability.AUDIO_INPUT)
        assert not adapter.supports(Capability.AUDIO_OUTPUT)


@pytest.mark.integration
def test_provider_name(adapter: AnthropicAdapter) -> None:
    """Test provider_name property."""
    assert adapter.provider_name == "anthropic"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling() -> None:
    """Test graceful error handling with invalid API key."""
    bad_adapter = AnthropicAdapter(api_key="sk-invalid-key-test")
    request = CompletionRequest(
        messages=(
            Message(role="user", content="hello"),
        ),
        model="claude-sonnet-4-6",
        max_tokens=10,
    )
    with pytest.raises(Exception):
        await bad_adapter.complete(request)
