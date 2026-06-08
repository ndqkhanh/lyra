"""
Unit tests for the DeepSeek provider adapter.

Mocks all external API calls (OpenAI SDK) to test public methods,
error paths, and edge cases without a real API key.
"""

from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from lyra.routing.provider.adapters import deepseek as ds_module
from lyra.routing.provider.adapters.deepseek import (
    DeepSeekAdapter,
    _count_tokens_heuristic,
    _get_pricing,
    _messages_to_openai,
    _parse_openai_response,
    _tools_to_openai,
)
from lyra.routing.provider.types import (
    Capability,
    CompletionChunk,
    CompletionRequest,
    CostEstimate,
    EffortLevel,
    Message,
    TokenUsage,
    ToolCall,
    ToolDef,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# _get_pricing
# ---------------------------------------------------------------------------


class TestGetPricing:
    def test_exact_match(self) -> None:
        inp, out = _get_pricing("deepseek-chat")
        assert inp == 0.27
        assert out == 1.10

    def test_reasoner_exact_match(self) -> None:
        inp, out = _get_pricing("deepseek-reasoner")
        assert inp == 0.55
        assert out == 2.19

    def test_prefix_match(self) -> None:
        inp, out = _get_pricing("deepseek-chat-v2")
        assert inp == 0.27
        assert out == 1.10

    def test_unknown_model(self) -> None:
        inp, out = _get_pricing("gpt-42")
        assert inp == 0.27  # _DEFAULT_INPUT_PRICE
        assert out == 1.10  # _DEFAULT_OUTPUT_PRICE

    def test_empty_string(self) -> None:
        inp, out = _get_pricing("")
        assert inp == _DEFAULT_INPUT_PRICE
        assert out == _DEFAULT_OUTPUT_PRICE


# ---------------------------------------------------------------------------
# _count_tokens_heuristic
# ---------------------------------------------------------------------------


class TestCountTokensHeuristic:
    def test_normal_text(self) -> None:
        assert _count_tokens_heuristic("hello world") == 2  # 11 chars // 4

    def test_empty_string(self) -> None:
        assert _count_tokens_heuristic("") == 1  # max(1, 0) -- guards div-by-zero

    def test_short_text(self) -> None:
        assert _count_tokens_heuristic("ab") == 1


# ---------------------------------------------------------------------------
# _messages_to_openai
# ---------------------------------------------------------------------------


class TestMessagesToOpenAI:
    def test_system_message(self) -> None:
        msgs = (Message(role="system", content="Be helpful."),)
        result = _messages_to_openai(msgs)
        assert result == [{"role": "system", "content": "Be helpful."}]

    def test_user_message(self) -> None:
        msgs = (Message(role="user", content="Hello"),)
        result = _messages_to_openai(msgs)
        assert result == [{"role": "user", "content": "Hello"}]

    def test_assistant_message_no_tool_calls(self) -> None:
        msgs = (Message(role="assistant", content="Hi there"),)
        result = _messages_to_openai(msgs)
        assert result == [{"role": "assistant", "content": "Hi there"}]

    def test_assistant_message_with_tool_calls(self) -> None:
        tc = ToolCall(id="call_1", name="get_weather", arguments={"city": "Paris"})
        msgs = (Message(role="assistant", content="", tool_calls=(tc,)),)
        result = _messages_to_openai(msgs)
        assert len(result) == 1
        entry = result[0]
        assert entry["role"] == "assistant"
        assert entry["tool_calls"][0]["id"] == "call_1"
        assert entry["tool_calls"][0]["function"]["name"] == "get_weather"
        assert json.loads(entry["tool_calls"][0]["function"]["arguments"]) == {"city": "Paris"}

    def test_tool_message(self) -> None:
        msgs = (Message(role="tool", content='{"temperature": 22}', tool_call_id="call_1"),)
        result = _messages_to_openai(msgs)
        assert result == [
            {"role": "tool", "tool_call_id": "call_1", "content": '{"temperature": 22}'},
        ]

    def test_unknown_role_fallback_to_user(self) -> None:
        msgs = (Message(role="unknown_role", content="something"),)
        result = _messages_to_openai(msgs)
        assert result == [{"role": "user", "content": "something"}]

    def test_mixed_messages(self) -> None:
        msgs = (
            Message(role="system", content="S1"),
            Message(role="user", content="U1"),
            Message(role="assistant", content="A1"),
            Message(role="tool", content="T1", tool_call_id="c1"),
        )
        result = _messages_to_openai(msgs)
        assert len(result) == 4
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"
        assert result[2]["role"] == "assistant"
        assert result[3]["role"] == "tool"


# ---------------------------------------------------------------------------
# _tools_to_openai
# ---------------------------------------------------------------------------


class TestToolsToOpenAI:
    def test_single_tool(self) -> None:
        tools = (
            ToolDef(
                name="get_weather",
                description="Get weather for a city",
                parameters={"type": "object", "properties": {"city": {"type": "string"}}},
            ),
        )
        result = _tools_to_openai(tools)
        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "get_weather"

    def test_multiple_tools(self) -> None:
        tools = (
            ToolDef(name="a", description="tool a", parameters={}),
            ToolDef(name="b", description="tool b", parameters={}),
        )
        result = _tools_to_openai(tools)
        assert len(result) == 2

    def test_empty_tuple(self) -> None:
        assert _tools_to_openai(()) == []


# ---------------------------------------------------------------------------
# _parse_openai_response
# ---------------------------------------------------------------------------


class TestParseOpenAIResponse:
    def _make_mock(self, content: str = "Hello!", finish: str = "stop", prompt_tokens: int = 10,
                   completion_tokens: int = 20, cached_tokens: int | None = None,
                   tool_calls: list | None = None, model: str = "deepseek-chat") -> MagicMock:
        import openai
        choice = MagicMock(spec=openai.types.chat.chat_completion.Choice)
        choice.message = MagicMock(spec=openai.types.chat.ChatCompletionMessage)
        choice.message.content = content
        choice.message.tool_calls = tool_calls
        choice.finish_reason = finish

        usage = MagicMock(spec=openai.types.CompletionUsage)
        usage.prompt_tokens = prompt_tokens
        usage.completion_tokens = completion_tokens
        if cached_tokens is not None:
            details = MagicMock()
            details.cached_tokens = cached_tokens
            usage.prompt_tokens_details = details
        else:
            usage.prompt_tokens_details = None

        response = MagicMock(spec=openai.types.chat.ChatCompletion)
        response.choices = [choice]
        response.usage = usage
        response.model = model
        return response

    def test_basic_response(self) -> None:
        resp = self._make_mock()
        result = _parse_openai_response(resp, 42.0)
        assert result.content == "Hello!"
        assert result.finish_reason == "stop"
        assert result.model == "deepseek-chat"
        assert result.latency_ms == 42.0
        assert result.usage.input_tokens == 10
        assert result.usage.output_tokens == 20
        assert result.usage.cache_read_tokens == 0
        assert result.tool_calls is None

    def test_with_cached_tokens(self) -> None:
        resp = self._make_mock(cached_tokens=50)
        result = _parse_openai_response(resp, 1.0)
        assert result.usage.cache_read_tokens == 50

    def test_with_tool_calls(self) -> None:
        tc_mock = MagicMock()
        tc_mock.id = "call_x"
        tc_mock.function.name = "get_weather"
        tc_mock.function.arguments = '{"city": "London"}'
        resp = self._make_mock(tool_calls=[tc_mock])
        result = _parse_openai_response(resp, 5.0)
        assert result.tool_calls is not None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].id == "call_x"
        assert result.tool_calls[0].name == "get_weather"
        assert result.tool_calls[0].arguments == {"city": "London"}

    def test_with_malformed_tool_call_json(self) -> None:
        tc_mock = MagicMock()
        tc_mock.id = "call_y"
        tc_mock.function.name = "bad_tool"
        tc_mock.function.arguments = "{invalid json}"
        resp = self._make_mock(tool_calls=[tc_mock])
        result = _parse_openai_response(resp, 3.0)
        assert result.tool_calls is not None
        assert result.tool_calls[0].arguments == {}

    def test_no_usage(self) -> None:
        resp = self._make_mock()
        resp.usage = None
        result = _parse_openai_response(resp, 0.0)
        assert result.usage.input_tokens == 0
        assert result.usage.output_tokens == 0

    def test_finish_reason_fallback(self) -> None:
        resp = self._make_mock()
        resp.choices[0].finish_reason = None
        result = _parse_openai_response(resp, 0.0)
        assert result.finish_reason == "stop"


# ---------------------------------------------------------------------------
# DeepSeekAdapter
# ---------------------------------------------------------------------------

_DEFAULT_INPUT_PRICE = 0.27
_DEFAULT_OUTPUT_PRICE = 1.10


@pytest.fixture
def mock_client():
    """Mock the OpenAI AsyncClient used by DeepSeekAdapter."""
    with patch("lyra.routing.provider.adapters.deepseek.openai.AsyncOpenAI") as mock_cls:
        instance = mock_cls.return_value
        yield instance


@pytest.fixture
def adapter(mock_client):
    """DeepSeekAdapter with a mocked client and env key."""
    with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key-123"}):
        yield DeepSeekAdapter()


@pytest.fixture
def sample_request():
    return CompletionRequest(
        messages=(
            Message(role="system", content="Be helpful."),
            Message(role="user", content="What is the capital of France?"),
        ),
        model="deepseek-chat",
        max_tokens=100,
        temperature=0.0,
        effort=EffortLevel.MEDIUM,
    )


class TestDeepSeekAdapterInit:
    def test_with_explicit_api_key(self, mock_client):
        with patch("lyra.routing.provider.adapters.deepseek.openai.AsyncOpenAI") as mock_cls:
            DeepSeekAdapter(api_key="explicit-key")
            mock_cls.assert_called_once_with(
                api_key="explicit-key",
                base_url="https://api.deepseek.com/v1",
                max_retries=3,
            )

    def test_with_env_var(self, mock_client):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "env-key"}, clear=True):
            with patch("lyra.routing.provider.adapters.deepseek.openai.AsyncOpenAI") as mock_cls:
                DeepSeekAdapter()
                mock_cls.assert_called_once_with(
                    api_key="env-key",
                    base_url="https://api.deepseek.com/v1",
                    max_retries=3,
                )

    def test_custom_base_url(self, mock_client):
        DeepSeekAdapter(api_key="k", base_url="https://custom.example.com")
        mock_client.return_value  # client is created by the class
        # Verify via the init
        import lyra.routing.provider.adapters.deepseek as m
        m.openai.AsyncOpenAI.assert_called_with(
            api_key="k",
            base_url="https://custom.example.com",
            max_retries=3,
        )

    def test_custom_max_retries(self, mock_client):
        with patch("lyra.routing.provider.adapters.deepseek.openai.AsyncOpenAI") as mock_cls:
            DeepSeekAdapter(api_key="k", max_retries=5)
            mock_cls.assert_called_once_with(
                api_key="k", base_url="https://api.deepseek.com/v1", max_retries=5,
            )

    def test_no_key_raises(self, mock_client):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="DeepSeek API key not provided"):
                DeepSeekAdapter()

    def test_provider_name(self, adapter):
        assert adapter.provider_name == "deepseek"


class TestDeepSeekAdapterComplete:
    async def test_success(self, adapter, mock_client, sample_request):
        """Happy path: complete returns a proper CompletionResponse."""
        # Build a realistic mock ChatCompletion response
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = "Paris"
        mock_completion.choices[0].message.tool_calls = None
        mock_completion.choices[0].finish_reason = "stop"
        mock_completion.usage.prompt_tokens = 15
        mock_completion.usage.completion_tokens = 5
        mock_completion.usage.prompt_tokens_details = None
        mock_completion.model = "deepseek-chat"

        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        response = await adapter.complete(sample_request)
        assert response.content == "Paris"
        assert response.finish_reason == "stop"
        assert response.usage.input_tokens == 15
        assert response.usage.output_tokens == 5
        assert response.latency_ms > 0
        assert response.model == "deepseek-chat"

    async def test_with_tools(self, adapter, mock_client, sample_request):
        """Complete with tools passes them in kwargs."""
        tools = (
            ToolDef(name="get_weather", description="Get weather",
                    parameters={"type": "object", "properties": {"city": {"type": "string"}}}),
        )
        req = CompletionRequest(
            messages=sample_request.messages,
            model="deepseek-chat",
            max_tokens=100,
            temperature=0.0,
            tools=tools,
        )
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = "Sunny"
        mock_completion.choices[0].message.tool_calls = None
        mock_completion.choices[0].finish_reason = "stop"
        mock_completion.usage.prompt_tokens = 20
        mock_completion.usage.completion_tokens = 5
        mock_completion.usage.prompt_tokens_details = None
        mock_completion.model = "deepseek-chat"

        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        response = await adapter.complete(req)
        assert response.content == "Sunny"

        # Verify tools were passed
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert "tools" in call_kwargs
        assert len(call_kwargs["tools"]) == 1

    async def test_low_effort_does_not_pass_reasoning(self, adapter, mock_client, sample_request):
        """DeepSeek adapter ignores effort (no reasoning_effort param)."""
        req = CompletionRequest(
            messages=sample_request.messages,
            model="deepseek-chat",
            max_tokens=100,
            temperature=0.0,
            effort=EffortLevel.LOW,
        )
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = "reply"
        mock_completion.choices[0].message.tool_calls = None
        mock_completion.choices[0].finish_reason = "stop"
        mock_completion.usage.prompt_tokens = 5
        mock_completion.usage.completion_tokens = 5
        mock_completion.usage.prompt_tokens_details = None
        mock_completion.model = "deepseek-chat"

        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        response = await adapter.complete(req)
        assert response.content == "reply"
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert "reasoning_effort" not in call_kwargs

    async def test_api_status_error(self, adapter, mock_client, sample_request):
        """APIStatusError is logged and re-raised."""
        import openai
        mock_client.chat.completions.create = AsyncMock(
            side_effect=openai.APIStatusError(
                message="Bad Request",
                response=MagicMock(status_code=400),
                body='{"error": "invalid"}',
            ),
        )
        with pytest.raises(openai.APIStatusError):
            await adapter.complete(sample_request)

    async def test_api_timeout_error(self, adapter, mock_client, sample_request):
        """APITimeoutError is logged and re-raised."""
        import openai
        mock_client.chat.completions.create = AsyncMock(
            side_effect=openai.APITimeoutError("timed out"),
        )
        with pytest.raises(openai.APITimeoutError):
            await adapter.complete(sample_request)


class TestDeepSeekAdapterCompleteStream:
    async def test_stream_success(self, adapter, mock_client, sample_request):
        """Streaming yields CompletionChunk instances with text deltas."""
        # Build mock streaming chunks
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
        assert chunks[1].content_delta == " world"
        assert chunks[2].finish_reason == "stop"

    async def test_stream_with_tool_call_delta(self, adapter, mock_client, sample_request):
        """Streaming yields tool_call_delta when delta.tool_calls is present."""
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
        chunks: list[CompletionChunk] = []
        async for ch in adapter.complete_stream(sample_request):
            chunks.append(ch)

        assert len(chunks) == 1
        assert chunks[0].tool_call_delta is not None
        parsed = json.loads(chunks[0].tool_call_delta)
        assert parsed["id"] == "tc_1"
        assert parsed["function"]["name"] == "get_weather"

    async def test_stream_skips_choice_none(self, adapter, mock_client, sample_request):
        """Chunk with choices=None is skipped."""
        async def _mock_stream():
            chunk = MagicMock()
            chunk.choices = None
            yield chunk

        mock_client.chat.completions.create = AsyncMock(return_value=_mock_stream())
        chunks = []
        async for ch in adapter.complete_stream(sample_request):
            chunks.append(ch)
        assert len(chunks) == 0

    async def test_stream_skips_delta_none(self, adapter, mock_client, sample_request):
        """Chunk with choices[0].delta=None is skipped."""
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

    async def test_stream_api_status_error(self, adapter, mock_client, sample_request):
        """APIStatusError yields an error chunk."""
        import openai
        mock_client.chat.completions.create = AsyncMock(
            side_effect=openai.APIStatusError(
                message="err", response=MagicMock(status_code=500), body="{}",
            ),
        )
        chunks = []
        async for ch in adapter.complete_stream(sample_request):
            chunks.append(ch)
        assert len(chunks) == 1
        assert chunks[0].finish_reason == "error"

    async def test_stream_api_timeout_error(self, adapter, mock_client, sample_request):
        """APITimeoutError yields an error chunk."""
        import openai
        mock_client.chat.completions.create = AsyncMock(
            side_effect=openai.APITimeoutError("timeout"),
        )
        chunks = []
        async for ch in adapter.complete_stream(sample_request):
            chunks.append(ch)
        assert len(chunks) == 1
        assert chunks[0].finish_reason == "error"


class TestDeepSeekAdapterSupports:
    def test_supported(self, adapter):
        assert adapter.supports(Capability.TEXT_GENERATION)
        assert adapter.supports(Capability.TOOL_USE)
        assert adapter.supports(Capability.STREAMING)
        assert adapter.supports(Capability.JSON_MODE)
        assert adapter.supports(Capability.LONG_CONTEXT)

    def test_unsupported(self, adapter):
        assert not adapter.supports(Capability.VISION)
        assert not adapter.supports(Capability.AUDIO_INPUT)
        assert not adapter.supports(Capability.AUDIO_OUTPUT)


class TestDeepSeekAdapterCostEstimate:
    def test_cost_estimate_known_model(self, adapter):
        request = CompletionRequest(
            messages=(Message(role="user", content="Hello"),),
            model="deepseek-chat",
            max_tokens=100,
        )
        cost = adapter.cost_estimate(request)
        # input: 1 token (1 char // 4) * 0.27 / 1M = 6.75e-8 -> rounds to 0.000000
        # output: 100 * 1.10 / 1M = 0.00011
        assert isinstance(cost, CostEstimate)
        assert cost.total_max_cost > 0
        assert cost.output_cost > 0

    def test_cost_estimate_unknown_model(self, adapter):
        request = CompletionRequest(
            messages=(Message(role="user", content="Hi"),),
            model="unknown-model",
            max_tokens=50,
        )
        cost = adapter.cost_estimate(request)
        # Falls back to _DEFAULT_INPUT_PRICE / _DEFAULT_OUTPUT_PRICE
        assert cost.total_max_cost > 0
        assert cost.output_cost > 0

    def test_cost_estimate_empty_messages(self, adapter):
        request = CompletionRequest(
            messages=(),
            model="deepseek-chat",
            max_tokens=10,
        )
        cost = adapter.cost_estimate(request)
        assert cost.total_max_cost > 0


class TestDeepSeekAdapterClose:
    def test_close_running_loop(self, adapter, mock_client):
        """close() when loop is running should call loop.create_task."""
        import asyncio
        # Mock the client.close() to avoid errors
        mock_client.close.return_value = asyncio.Future()
        mock_client.close.return_value.set_result(None)
        with patch("asyncio.get_event_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_loop.is_running.return_value = True
            mock_get_loop.return_value = mock_loop
            adapter.close()
            mock_loop.create_task.assert_called_once_with(mock_client.close())

    def test_close_not_running_loop(self, adapter, mock_client):
        """close() when loop is not running should call run_until_complete."""
        import asyncio
        with patch("asyncio.get_event_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_loop.is_running.return_value = False
            mock_get_loop.return_value = mock_loop
            adapter.close()
            mock_loop.run_until_complete.assert_called_once_with(mock_client.close())

    def test_close_runtime_error(self, adapter, mock_client):
        """close() catches RuntimeError silently."""
        with patch("asyncio.get_event_loop", side_effect=RuntimeError("no loop")):
            adapter.close()  # should not raise
