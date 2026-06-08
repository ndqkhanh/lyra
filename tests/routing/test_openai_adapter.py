"""
Unit tests for the OpenAI provider adapter.

Mocks all external API calls (OpenAI SDK) to test public methods,
error paths, and edge cases without a real API key.
"""

from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lyra.routing.provider.adapters.openai import OpenAIAdapter, _get_pricing
from lyra.routing.provider.types import (
    Capability,
    CompletionRequest,
    CostEstimate,
    EffortLevel,
    Message,
    ToolCall,
    ToolDef,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# _get_pricing
# ---------------------------------------------------------------------------


class TestGetPricing:
    def test_exact_match_gpt4o(self) -> None:
        inp, out = _get_pricing("gpt-4o")
        assert inp == 2.50
        assert out == 10.00

    def test_prefix_match_gpt4(self) -> None:
        inp, out = _get_pricing("gpt-4o-mini")
        assert inp == 0.15
        assert out == 0.60

    def test_o3_pricing(self) -> None:
        inp, out = _get_pricing("o3")
        assert inp == 10.00
        assert out == 40.00

    def test_unknown_model(self) -> None:
        inp, out = _get_pricing("weird-model-v1")
        assert inp == 2.50  # _DEFAULT_INPUT_PRICE
        assert out == 10.00  # _DEFAULT_OUTPUT_PRICE

    def test_empty_string(self) -> None:
        inp, out = _get_pricing("")
        assert inp == 2.50
        assert out == 10.00


# ---------------------------------------------------------------------------
# OpenAIAdapter
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client():
    """Mock the OpenAI AsyncClient used by OpenAIAdapter."""
    with patch("lyra.routing.provider.adapters.openai.openai.AsyncOpenAI") as mock_cls:
        instance = mock_cls.return_value
        yield instance


@pytest.fixture
def adapter(mock_client):
    """OpenAIAdapter with a mocked client and env key."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-openai-key"}):
        yield OpenAIAdapter()


@pytest.fixture
def sample_request():
    return CompletionRequest(
        messages=(
            Message(role="system", content="You are GPT-4o."),
            Message(role="user", content="What is the capital of France?"),
        ),
        model="gpt-4o",
        max_tokens=100,
        temperature=0.0,
        effort=EffortLevel.MEDIUM,
    )


class TestOpenAIAdapterInit:
    def test_with_explicit_api_key(self, mock_client):
        with patch("lyra.routing.provider.adapters.openai.openai.AsyncOpenAI") as mock_cls:
            OpenAIAdapter(api_key="explicit-key")
            mock_cls.assert_called_once_with(
                api_key="explicit-key",
                base_url=None,
                max_retries=3,
            )

    def test_with_env_var(self, mock_client):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}, clear=True):
            with patch("lyra.routing.provider.adapters.openai.openai.AsyncOpenAI") as mock_cls:
                OpenAIAdapter()
                mock_cls.assert_called_once_with(
                    api_key="env-key",
                    base_url=None,
                    max_retries=3,
                )

    def test_custom_base_url(self, mock_client):
        with patch("lyra.routing.provider.adapters.openai.openai.AsyncOpenAI") as mock_cls:
            OpenAIAdapter(api_key="k", base_url="https://custom.openai.com")
            mock_cls.assert_called_once_with(
                api_key="k", base_url="https://custom.openai.com", max_retries=3,
            )

    def test_no_key_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key not provided"):
                OpenAIAdapter()

    def test_provider_name(self, adapter):
        assert adapter.provider_name == "openai"


class TestOpenAIAdapterComplete:
    async def _mock_completion(self, content: str = "Paris", finish: str = "stop",
                                prompt_tokens: int = 15, completion_tokens: int = 5,
                                tool_calls: list | None = None):
        import openai
        choice = MagicMock(spec=openai.types.chat.chat_completion.Choice)
        choice.message = MagicMock(spec=openai.types.chat.ChatCompletionMessage)
        choice.message.content = content
        choice.message.tool_calls = tool_calls
        choice.finish_reason = finish

        usage = MagicMock(spec=openai.types.CompletionUsage)
        usage.prompt_tokens = prompt_tokens
        usage.completion_tokens = completion_tokens
        usage.prompt_tokens_details = None

        response = MagicMock(spec=openai.types.chat.ChatCompletion)
        response.choices = [choice]
        response.usage = usage
        response.model = "gpt-4o"
        return response

    async def test_success(self, adapter, mock_client, sample_request):
        mock_client.chat.completions.create = AsyncMock(
            return_value=await self._mock_completion(),
        )
        response = await adapter.complete(sample_request)
        assert response.content == "Paris"
        assert response.finish_reason == "stop"
        assert response.model == "gpt-4o"
        assert response.usage.input_tokens == 15
        assert response.usage.output_tokens == 5

    async def test_with_tools(self, adapter, mock_client, sample_request):
        req = CompletionRequest(
            messages=sample_request.messages, model="gpt-4o",
            max_tokens=100, temperature=0.0,
            tools=(ToolDef(name="get_weather", description="Weather",
                           parameters={"type": "object"}),),
        )
        mock_client.chat.completions.create = AsyncMock(
            return_value=await self._mock_completion(content="Sunny"),
        )
        response = await adapter.complete(req)
        assert response.content == "Sunny"
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert "tools" in call_kwargs

    async def test_reasoning_effort_low(self, adapter, mock_client, sample_request):
        """Low effort maps to reasoning_effort='low'."""
        req = CompletionRequest(
            messages=sample_request.messages, model="o3",
            max_tokens=100, temperature=0.0, effort=EffortLevel.LOW,
        )
        mock_client.chat.completions.create = AsyncMock(
            return_value=await self._mock_completion(content="answer"),
        )
        await adapter.complete(req)
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs.get("reasoning_effort") == "low"

    async def test_reasoning_effort_high(self, adapter, mock_client, sample_request):
        """High effort maps to reasoning_effort='medium'."""
        req = CompletionRequest(
            messages=sample_request.messages, model="o3",
            max_tokens=100, temperature=0.0, effort=EffortLevel.HIGH,
        )
        mock_client.chat.completions.create = AsyncMock(
            return_value=await self._mock_completion(content="answer"),
        )
        await adapter.complete(req)
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs.get("reasoning_effort") == "medium"

    async def test_reasoning_effort_xhigh(self, adapter, mock_client, sample_request):
        """XHIGH and MAX effort map to reasoning_effort='high'."""
        req = CompletionRequest(
            messages=sample_request.messages, model="o3",
            max_tokens=100, temperature=0.0, effort=EffortLevel.XHIGH,
        )
        mock_client.chat.completions.create = AsyncMock(
            return_value=await self._mock_completion(content="answer"),
        )
        await adapter.complete(req)
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs.get("reasoning_effort") == "high"

    async def test_reasoning_effort_max(self, adapter, mock_client, sample_request):
        req = CompletionRequest(
            messages=sample_request.messages, model="o3",
            max_tokens=100, temperature=0.0, effort=EffortLevel.MAX,
        )
        mock_client.chat.completions.create = AsyncMock(
            return_value=await self._mock_completion(content="answer"),
        )
        await adapter.complete(req)
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs.get("reasoning_effort") == "high"

    async def test_reasoning_effort_medium_no_param(self, adapter, mock_client, sample_request):
        """Medium effort does not pass reasoning_effort."""
        mock_client.chat.completions.create = AsyncMock(
            return_value=await self._mock_completion(content="answer"),
        )
        await adapter.complete(sample_request)  # sample_request is MEDIUM
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert "reasoning_effort" not in call_kwargs

    async def test_api_status_error(self, adapter, mock_client, sample_request):
        import openai
        mock_client.chat.completions.create = AsyncMock(
            side_effect=openai.APIStatusError(
                message="err", response=MagicMock(status_code=400), body="{}",
            ),
        )
        with pytest.raises(openai.APIStatusError):
            await adapter.complete(sample_request)

    async def test_api_timeout_error(self, adapter, mock_client, sample_request):
        import openai
        mock_client.chat.completions.create = AsyncMock(
            side_effect=openai.APITimeoutError("timeout"),
        )
        with pytest.raises(openai.APITimeoutError):
            await adapter.complete(sample_request)


class TestOpenAIAdapterCompleteStream:
    async def test_stream_success(self, adapter, mock_client, sample_request):
        async def _mock_stream():
            for content, finish in [("Hello", None), (" world", None), ("", "stop")]:
                chunk = MagicMock()
                chunk.choices = [MagicMock()]
                chunk.choices[0].delta.content = content
                chunk.choices[0].delta.tool_calls = None
                chunk.choices[0].finish_reason = finish
                yield chunk

        mock_client.chat.completions.create = AsyncMock(return_value=_mock_stream())

        chunks = []
        async for ch in adapter.complete_stream(sample_request):
            chunks.append(ch)

        assert len(chunks) == 3
        assert chunks[0].content_delta == "Hello"
        assert chunks[2].finish_reason == "stop"

    async def test_stream_skips_none_choices(self, adapter, mock_client, sample_request):
        async def _mock_stream():
            chunk = MagicMock()
            chunk.choices = None
            yield chunk

        mock_client.chat.completions.create = AsyncMock(return_value=_mock_stream())
        chunks = []
        async for ch in adapter.complete_stream(sample_request):
            chunks.append(ch)
        assert len(chunks) == 0

    async def test_stream_skips_none_delta(self, adapter, mock_client, sample_request):
        async def _mock_stream():
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta = None
            yield chunk

        mock_client.chat.completions.create = AsyncMock(return_value=_mock_stream())
        chunks = []
        async for ch in adapter.complete_stream(sample_request):
            chunks.append(ch)
        assert len(chunks) == 0

    async def test_stream_with_tool_call_delta(self, adapter, mock_client, sample_request):
        async def _mock_stream():
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta.content = ""
            chunk.choices[0].delta.tool_calls = [MagicMock()]
            chunk.choices[0].delta.tool_calls[0].id = "tc_1"
            chunk.choices[0].delta.tool_calls[0].index = 0
            chunk.choices[0].delta.tool_calls[0].function.name = "get_weather"
            chunk.choices[0].delta.tool_calls[0].function.arguments = '{"city":"Paris"}'
            chunk.choices[0].finish_reason = None
            yield chunk

        mock_client.chat.completions.create = AsyncMock(return_value=_mock_stream())
        chunks = []
        async for ch in adapter.complete_stream(sample_request):
            chunks.append(ch)
        assert len(chunks) == 1
        assert chunks[0].tool_call_delta is not None

    async def test_stream_reasoning_effort(self, adapter, mock_client, sample_request):
        """Streaming also passes reasoning_effort for o-series."""
        req = CompletionRequest(
            messages=sample_request.messages, model="o3",
            max_tokens=100, temperature=0.0, effort=EffortLevel.XHIGH,
        )

        async def _mock_stream():
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta.content = "thinking"
            chunk.choices[0].delta.tool_calls = None
            chunk.choices[0].finish_reason = "stop"
            yield chunk

        mock_client.chat.completions.create = AsyncMock(return_value=_mock_stream())
        chunks = []
        async for ch in adapter.complete_stream(req):
            chunks.append(ch)
        assert len(chunks) == 1

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs.get("reasoning_effort") == "high"

    async def test_stream_api_status_error(self, adapter, mock_client, sample_request):
        import openai
        mock_client.chat.completions.create = AsyncMock(
            side_effect=openai.APIStatusError(
                message="err", response=MagicMock(status_code=500), body="{}",
            ),
        )
        chunks = []
        async for ch in adapter.complete_stream(sample_request):
            chunks.append(ch)
        assert chunks[0].finish_reason == "error"

    async def test_stream_api_timeout_error(self, adapter, mock_client, sample_request):
        import openai
        mock_client.chat.completions.create = AsyncMock(
            side_effect=openai.APITimeoutError("timeout"),
        )
        chunks = []
        async for ch in adapter.complete_stream(sample_request):
            chunks.append(ch)
        assert chunks[0].finish_reason == "error"


class TestOpenAIAdapterSupports:
    def test_supported(self, adapter):
        assert adapter.supports(Capability.TEXT_GENERATION)
        assert adapter.supports(Capability.TOOL_USE)
        assert adapter.supports(Capability.VISION)
        assert adapter.supports(Capability.STREAMING)
        assert adapter.supports(Capability.JSON_MODE)
        assert adapter.supports(Capability.LONG_CONTEXT)
        assert adapter.supports(Capability.AUDIO_INPUT)
        assert adapter.supports(Capability.AUDIO_OUTPUT)

    def test_unsupported(self, adapter):
        # No unsupported capabilities in the current set (all are supported)
        pass


class TestOpenAIAdapterCostEstimate:
    def test_cost_estimate_known_model(self, adapter):
        request = CompletionRequest(
            messages=(Message(role="user", content="Hello"),),
            model="gpt-4o",
            max_tokens=100,
        )
        cost = adapter.cost_estimate(request)
        assert isinstance(cost, CostEstimate)
        assert cost.total_max_cost > 0
        assert cost.output_cost > 0

    def test_cost_estimate_unknown_model(self, adapter):
        request = CompletionRequest(
            messages=(Message(role="user", content="Hi"),),
            model="some-random-model",
            max_tokens=50,
        )
        cost = adapter.cost_estimate(request)
        assert cost.total_max_cost > 0


class TestOpenAIAdapterClose:
    def test_close_running_loop(self, adapter, mock_client):
        import asyncio
        loop = asyncio.get_event_loop()
        with patch("asyncio.get_event_loop", return_value=loop):
            with patch.object(loop, "is_running", return_value=True):
                with patch.object(loop, "create_task") as mock_create_task:
                    adapter.close()
                    mock_create_task.assert_called_once_with(mock_client.close())

    def test_close_not_running_loop(self, adapter, mock_client):
        loop = MagicMock()
        loop.is_running.return_value = False
        with patch("asyncio.get_event_loop", return_value=loop):
            adapter.close()
            loop.run_until_complete.assert_called_once_with(mock_client.close())

    def test_close_runtime_error(self, adapter, mock_client):
        with patch("asyncio.get_event_loop", side_effect=RuntimeError("no loop")):
            adapter.close()  # should not raise
