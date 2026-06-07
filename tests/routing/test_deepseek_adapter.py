"""
Integration tests for the DeepSeek adapter.

These tests require a valid ``DEEPSEEK_API_KEY`` environment variable.
If it is not set the tests are skipped.
"""

from __future__ import annotations

import os

import pytest

from lyra.routing.provider.adapters.deepseek import DeepSeekAdapter
from lyra.routing.provider.types import (
    Capability,
    CompletionRequest,
    EffortLevel,
    Message,
)


# ---------------------------------------------------------------------------
# Skip if no API key
# ---------------------------------------------------------------------------
pytestmark = pytest.mark.skipif(
    not os.environ.get("DEEPSEEK_API_KEY"),
    reason="DEEPSEEK_API_KEY environment variable not set",
)

integration = pytest.mark.integration


@pytest.fixture
def adapter() -> DeepSeekAdapter:
    """DeepSeekAdapter instance with API key from environment."""
    return DeepSeekAdapter()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_simple_completion(adapter: DeepSeekAdapter) -> None:
    """Test a basic text completion via DeepSeek."""
    request = CompletionRequest(
        messages=(
            Message(role="user", content="Say exactly 'hello world' and nothing else."),
        ),
        model="deepseek-chat",
        max_tokens=50,
        temperature=0.0,
        effort=EffortLevel.LOW,
    )
    response = await adapter.complete(request)

    assert response.content
    assert response.finish_reason in ("stop", "end_turn")
    assert response.usage.input_tokens > 0
    assert response.usage.output_tokens > 0
    assert response.latency_ms > 0


@pytest.mark.integration
def test_cost_estimate(adapter: DeepSeekAdapter) -> None:
    """Test cost estimation for DeepSeek."""
    request = CompletionRequest(
        messages=(
            Message(role="user", content="What is the capital of France?" * 100),
        ),
        model="deepseek-chat",
        max_tokens=100,
        effort=EffortLevel.LOW,
    )
    cost = adapter.cost_estimate(request)

    assert cost.input_cost > 0
    assert cost.output_cost > 0
    assert cost.total_max_cost > 0


class TestSupports:
    """DeepSeekAdapter.supports() tests."""

    def test_supported_capabilities(self, adapter: DeepSeekAdapter) -> None:
        assert adapter.supports(Capability.TEXT_GENERATION)
        assert adapter.supports(Capability.TOOL_USE)
        assert adapter.supports(Capability.STREAMING)
        assert adapter.supports(Capability.JSON_MODE)
        assert adapter.supports(Capability.LONG_CONTEXT)

    def test_unsupported_capabilities(self, adapter: DeepSeekAdapter) -> None:
        assert not adapter.supports(Capability.VISION)
        assert not adapter.supports(Capability.AUDIO_INPUT)
        assert not adapter.supports(Capability.AUDIO_OUTPUT)


@pytest.mark.integration
def test_provider_name(adapter: DeepSeekAdapter) -> None:
    """Test provider_name property."""
    assert adapter.provider_name == "deepseek"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_streaming(adapter: DeepSeekAdapter) -> None:
    """Test streaming completion via DeepSeek."""
    request = CompletionRequest(
        messages=(
            Message(role="user", content="Count from 1 to 3."),
        ),
        model="deepseek-chat",
        max_tokens=50,
        temperature=0.0,
        effort=EffortLevel.LOW,
    )
    chunks: list[str] = []
    async for chunk in adapter.complete_stream(request):
        if chunk.content_delta:
            chunks.append(chunk.content_delta)

    assert len(chunks) > 0
