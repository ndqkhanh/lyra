"""
Unit tests for the Anthropic provider adapter.
Mocks all external API calls (anthropic Python SDK) to test public methods,
error paths, and edge cases without a real API key.
"""

from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lyra.routing.provider.adapters.anthropic import (
    AnthropicAdapter,
    _get_pricing,
    _messages_to_anthropic,
    _tools_to_anthropic,
    _extract_system_message,
    _parse_anthropic_response,
    _count_tokens_heuristic,
    _EFFORT_BUDGET,
)
from lyra.routing.provider.types import (
    Capability,
    CompletionRequest,
    CompletionResponse,
    CostEstimate,
    EffortLevel,
    Message,
    ToolCall,
    ToolDef,
    TokenUsage,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helper: build a mock Anthropic Message
# ---------------------------------------------------------------------------

def make_mock_message(
    text: str = "Hello!",
    tool_calls: list | None = None,
    stop_reason: str = "end_turn",
    input_tokens: int = 10,
    output_tokens: int = 20,
    cache_read: int = 0,
    cache_write: int = 0,
    model: str = "claude-sonnet-4-6",
) -> MagicMock:
    """Build a minimal mock of anthropic.types.Message."""
    import anthropic

    msg = MagicMock(spec=anthropic.types.Message)
    msg.content = []
    if text:
        txt_block = MagicMock(spec=anthropic.types.TextBlock)
        txt_block.text = text
        msg.content.append(txt_block)
    if tool_calls:
        for tc in tool_calls:
            tc_block = MagicMock(spec=anthropic.types.ToolUseBlock)
            tc_block.id = tc.get("id", "tc_1")
            tc_block.name = tc.get("name", "get_weather")
            tc_block.input = tc.get("input", {})
            msg.content.append(tc_block)
    msg.stop_reason = stop_reason
    msg.model = model

    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    # Use setattr for dynamic attributes
    setattr(usage, "cache_read_input_tokens", cache_read)
    setattr(usage, "cache_write_input_tokens", cache_write)
    msg.usage = usage

    return msg


# ---------------------------------------------------------------------------
# _get_pricing
# ---------------------------------------------------------------------------


class TestGetPricing:
    def test_exact_match(self) -> None:
        inp, out = _get_pricing("claude-sonnet-4-6")
        assert inp == 3.00
        assert out == 15.00

    def test_prefix_match(self) -> None:
        inp, out = _get_pricing("claude-sonnet-4-6-unknown-version")
        assert inp == 3.00
        assert out == 15.00

    def test_opus_4_5(self) -> None:
        inp, out = _get_pricing("claude-opus-4-5")
        assert inp == 15.00
        assert out == 75.00

    def test_haiku_3(self) -> None:
        inp, out = _get_pricing("claude-haiku-3")
        assert inp == 0.25
        assert out == 1.25

    def test_haiku_3_5(self) -> None:
        inp, out = _get_pricing("claude-haiku-3-5")
        assert inp == 0.80
        assert out == 4.00

    def test_unknown_model(self) -> None:
        inp, out = _get_pricing("unknown-model-v99")
        assert inp == 3.00
        assert out == 15.00

    def test_empty_string(self) -> None:
        inp, out = _get_pricing("")
        assert inp == 3.00
        assert out == 15.00


# ---------------------------------------------------------------------------
# _count_tokens_heuristic
# ---------------------------------------------------------------------------


class TestCountTokensHeuristic:
    def test_empty(self) -> None:
        assert _count_tokens_heuristic("") == 1

    def test_short_text(self) -> None:
        assert _count_tokens_heuristic("abc") == 1

    def test_long_text(self) -> None:
        assert _count_tokens_heuristic("Hello world") == 2  # 11 chars / 4 = 2

    def test_exact(self) -> None:
        assert _count_tokens_heuristic("12345678") == 2


# ---------------------------------------------------------------------------
# _messages_to_anthropic
# ---------------------------------------------------------------------------


class TestMessagesToAnthropic:
    def test_user_message(self) -> None:
        msgs = (Message(role="user", content="Hello"),)
        result = _messages_to_anthropic(msgs)
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_system_message_skipped(self) -> None:
        msgs = (
            Message(role="system", content="You are helpful."),
            Message(role="user", content="Hi"),
        )
        result = _messages_to_anthropic(msgs)
        assert len(result) == 1  # system is skipped
        assert result[0]["role"] == "user"

    def test_tool_calls(self) -> None:
        msgs = (
            Message(
                role="assistant", content="Let me check",
                tool_calls=(
                    ToolCall(id="tc_1", name="get_weather", arguments={"city": "Paris"}),
                ),
            ),
        )
        result = _messages_to_anthropic(msgs)
        assert len(result) == 1
        # Should have both text and tool_use content blocks
        assert len(result[0]["content"]) == 2
        assert result[0]["content"][0]["type"] == "text"
        assert result[0]["content"][1]["type"] == "tool_use"

    def test_tool_result(self) -> None:
        msgs = (
            Message(role="user", content="The weather is sunny", tool_call_id="tc_1"),
        )
        result = _messages_to_anthropic(msgs)
        assert len(result) == 1
        # Both text and tool_result blocks are appended; content stays as a list
        assert isinstance(result[0]["content"], list)
        assert result[0]["content"][0]["type"] == "text"
        assert result[0]["content"][1]["type"] == "tool_result"

    def test_message_with_name(self) -> None:
        msgs = (
            Message(role="user", content="Result", name="get_weather"),
        )
        result = _messages_to_anthropic(msgs)
        assert len(result) == 1
        # name triggers a tool_result block in addition to text
        assert isinstance(result[0]["content"], list)
        assert result[0]["content"][0]["type"] == "text"
        assert result[0]["content"][1]["type"] == "tool_result"

    def test_plain_text_simplified(self) -> None:
        msgs = (Message(role="user", content="Hi"),)
        result = _messages_to_anthropic(msgs)
        assert len(result) == 1
        assert result[0]["content"] == "Hi"  # simplified to plain string

    def test_plain_text_not_simplified_when_multiple_blocks(self) -> None:
        msgs = (
            Message(
                role="assistant", content="Hi",
                tool_calls=(ToolCall(id="tc_1", name="t", arguments={}),),
            ),
        )
        result = _messages_to_anthropic(msgs)
        # Should not simplify because there are multiple content blocks
        assert isinstance(result[0]["content"], list)


# ---------------------------------------------------------------------------
# _tools_to_anthropic
# ---------------------------------------------------------------------------


class TestToolsToAnthropic:
    def test_conversion(self) -> None:
        tools = (
            ToolDef(name="get_weather", description="Get weather",
                    parameters={"type": "object"}),
        )
        result = _tools_to_anthropic(tools)
        assert len(result) == 1
        assert result[0]["name"] == "get_weather"
        assert result[0]["description"] == "Get weather"
        assert result[0]["input_schema"] == {"type": "object"}

    def test_empty(self) -> None:
        result = _tools_to_anthropic(())
        assert result == []


# ---------------------------------------------------------------------------
# _extract_system_message
# ---------------------------------------------------------------------------


class TestExtractSystemMessage:
    def test_last_system_message(self) -> None:
        msgs = (
            Message(role="system", content="First system"),
            Message(role="user", content="Hi"),
            Message(role="system", content="Last system"),
        )
        result = _extract_system_message(msgs)
        assert result == "Last system"

    def test_no_system(self) -> None:
        msgs = (Message(role="user", content="Hi"),)
        result = _extract_system_message(msgs)
        assert result is None

    def test_empty_messages(self) -> None:
        result = _extract_system_message(())
        assert result is None


# ---------------------------------------------------------------------------
# _parse_anthropic_response
# ---------------------------------------------------------------------------


class TestParseAnthropicResponse:
    def test_text_only(self) -> None:
        msg = make_mock_message(text="Hello there!")
        response = _parse_anthropic_response(msg, 150.0)
        assert response.content == "Hello there!"
        assert response.tool_calls is None
        assert response.usage.input_tokens == 10
        assert response.usage.output_tokens == 20
        assert response.finish_reason == "end_turn"
        assert response.model == "claude-sonnet-4-6"
        assert response.latency_ms == 150.0

    def test_with_tool_calls(self) -> None:
        msg = make_mock_message(
            text="Checking weather",
            tool_calls=[{"id": "tc_1", "name": "get_weather", "input": {"city": "Paris"}}],
        )
        response = _parse_anthropic_response(msg, 200.0)
        assert response.tool_calls is not None
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "get_weather"
        assert response.tool_calls[0].arguments == {"city": "Paris"}

    def test_with_cache_usage(self) -> None:
        msg = make_mock_message(text="Cached response", cache_read=50, cache_write=10)
        response = _parse_anthropic_response(msg, 100.0)
        assert response.usage.cache_read_tokens == 50
        assert response.usage.cache_write_tokens == 10

    def test_with_unknown_stop_reason(self) -> None:
        msg = make_mock_message(text="Stopped", stop_reason="max_tokens")
        response = _parse_anthropic_response(msg, 50.0)
        assert response.finish_reason == "max_tokens"


# ---------------------------------------------------------------------------
# AnthropicAdapter
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client():
    """Mock the underlying Anthropic AsyncClient."""
    with patch("lyra.routing.provider.adapters.anthropic.anthropic.AsyncAnthropic") as mock_cls:
        instance = mock_cls.return_value
        yield instance


@pytest.fixture
def adapter(mock_client):
    """AnthropicAdapter with mocked client and env key."""
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-anthropic-key"}):
        yield AnthropicAdapter()


@pytest.fixture
def sample_request():
    return CompletionRequest(
        messages=(
            Message(role="system", content="You are Claude."),
            Message(role="user", content="What is the capital of France?"),
        ),
        model="claude-sonnet-4-6",
        max_tokens=100,
        temperature=0.0,
        effort=EffortLevel.MEDIUM,
    )


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


class TestAnthropicAdapterInit:
    def test_with_explicit_key(self, mock_client):
        with patch("lyra.routing.provider.adapters.anthropic.anthropic.AsyncAnthropic") as mock_cls:
            AnthropicAdapter(api_key="explicit-key")
            mock_cls.assert_called_once_with(
                api_key="explicit-key",
                base_url=None,
                max_retries=3,
            )

    def test_with_env_var(self, mock_client):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key"}, clear=True):
            with patch("lyra.routing.provider.adapters.anthropic.anthropic.AsyncAnthropic") as mock_cls:
                AnthropicAdapter()
                mock_cls.assert_called_once_with(
                    api_key="env-key",
                    base_url=None,
                    max_retries=3,
                )

    def test_custom_base_url(self, mock_client):
        with patch("lyra.routing.provider.adapters.anthropic.anthropic.AsyncAnthropic") as mock_cls:
            AnthropicAdapter(api_key="k", base_url="https://custom.anthropic.com")
            mock_cls.assert_called_once_with(
                api_key="k", base_url="https://custom.anthropic.com", max_retries=3,
            )

    def test_no_key_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Anthropic API key not provided"):
                AnthropicAdapter()

    def test_provider_name(self, adapter):
        assert adapter.provider_name == "anthropic"

    def test_pricing_cache_initialized(self, adapter):
        assert adapter._pricing_cache == {}


# ---------------------------------------------------------------------------
# complete
# ---------------------------------------------------------------------------


class TestAnthropicAdapterComplete:
    async def test_success(self, adapter, mock_client, sample_request):
        mock_client.messages.create = AsyncMock(
            return_value=make_mock_message(text="Paris"),
        )
        response = await adapter.complete(sample_request)
        assert response.content == "Paris"
        assert response.latency_ms > 0
        assert response.usage.input_tokens == 10
        assert response.usage.output_tokens == 20

    async def test_with_tools(self, adapter, mock_client, sample_request):
        req = CompletionRequest(
            messages=sample_request.messages,
            model="claude-sonnet-4-6",
            max_tokens=100,
            tools=(ToolDef(name="get_weather", description="Weather",
                           parameters={"type": "object"}),),
        )
        mock_client.messages.create = AsyncMock(
            return_value=make_mock_message(text="Checking weather"),
        )
        response = await adapter.complete(req)
        assert response.content == "Checking weather"

    async def test_with_system_text(self, adapter, mock_client, sample_request):
        mock_client.messages.create = AsyncMock(
            return_value=make_mock_message(text="Paris"),
        )
        await adapter.complete(sample_request)
        call_kwargs = mock_client.messages.create.call_args.kwargs
        # Should have "system" in kwargs
        assert "system" in call_kwargs
        assert call_kwargs["system"] == [{"type": "text", "text": "You are Claude."}]

    async def test_without_system_text(self, adapter, mock_client):
        request = CompletionRequest(
            messages=(Message(role="user", content="Hi"),),
            model="claude-sonnet-4-6",
            max_tokens=50,
        )
        mock_client.messages.create = AsyncMock(
            return_value=make_mock_message(text="Hello!"),
        )
        await adapter.complete(request)
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "system" not in call_kwargs

    async def test_thinking_effort_low(self, adapter, mock_client, sample_request):
        req = CompletionRequest(
            messages=sample_request.messages,
            model="claude-sonnet-4-6",
            max_tokens=100,
            effort=EffortLevel.LOW,
        )
        mock_client.messages.create = AsyncMock(
            return_value=make_mock_message(text="Low thinking"),
        )
        await adapter.complete(req)
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "thinking" in call_kwargs
        assert call_kwargs["thinking"]["budget_tokens"] == 1024
        assert call_kwargs["max_tokens"] >= 1024 + 1024

    async def test_thinking_effort_high(self, adapter, mock_client, sample_request):
        req = CompletionRequest(
            messages=sample_request.messages,
            model="claude-sonnet-4-6",
            max_tokens=100,
            effort=EffortLevel.HIGH,
        )
        mock_client.messages.create = AsyncMock(
            return_value=make_mock_message(text="High thinking"),
        )
        await adapter.complete(req)
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["thinking"]["budget_tokens"] == 16384
        assert call_kwargs["max_tokens"] >= 16384 + 1024

    async def test_thinking_effort_max(self, adapter, mock_client, sample_request):
        req = CompletionRequest(
            messages=sample_request.messages,
            model="claude-sonnet-4-6",
            max_tokens=100,
            effort=EffortLevel.MAX,
        )
        mock_client.messages.create = AsyncMock(
            return_value=make_mock_message(text="Max thinking"),
        )
        await adapter.complete(req)
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["thinking"]["budget_tokens"] == 64000

    async def test_medium_effort_no_thinking(self, adapter, mock_client, sample_request):
        mock_client.messages.create = AsyncMock(
            return_value=make_mock_message(text="Medium"),
        )
        await adapter.complete(sample_request)  # MEDIUM
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "thinking" not in call_kwargs

    async def test_xhigh_effort_max_tokens_boosted(self, adapter, mock_client, sample_request):
        req = CompletionRequest(
            messages=sample_request.messages,
            model="claude-sonnet-4-6",
            max_tokens=1000,
            effort=EffortLevel.XHIGH,
        )
        mock_client.messages.create = AsyncMock(
            return_value=make_mock_message(text="XHigh"),
        )
        await adapter.complete(req)
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["thinking"]["budget_tokens"] == 32000
        # max_tokens should be max(1000, 32000 + 1024) = 33024
        assert call_kwargs["max_tokens"] == 33024

    async def test_api_status_error(self, adapter, mock_client, sample_request):
        import anthropic
        mock_client.messages.create = AsyncMock(
            side_effect=anthropic.APIStatusError(
                message="err", response=MagicMock(status_code=400), body="{}",
            ),
        )
        with pytest.raises(anthropic.APIStatusError):
            await adapter.complete(sample_request)

    async def test_api_timeout_error(self, adapter, mock_client, sample_request):
        import anthropic
        mock_client.messages.create = AsyncMock(
            side_effect=anthropic.APITimeoutError("timeout"),
        )
        with pytest.raises(anthropic.APITimeoutError):
            await adapter.complete(sample_request)


# ---------------------------------------------------------------------------
# complete_stream
# ---------------------------------------------------------------------------


class TestAnthropicAdapterCompleteStream:
    async def test_stream_text_only(self, adapter, mock_client, sample_request):
        """Test streaming text content."""
        from anthropic.types import Message as AnthMessage

        # Simulate the async context manager pattern
        fake_stream = AsyncMock()
        fake_stream.__aenter__ = AsyncMock(return_value=fake_stream)
        fake_stream.__aexit__ = AsyncMock(return_value=None)
        fake_stream.text_stream = AsyncMock()
        # __aiter__ must return an async iterator; we implement __anext__ to yield values
        async def _agen():
            for val in ["Hello", " world", ""]:
                yield val
        fake_stream.text_stream = _agen()

        # get_final_message should return a message with no tool calls
        final_msg = make_mock_message(text="Hello world", tool_calls=[])
        fake_stream.get_final_message = AsyncMock(return_value=final_msg)

        mock_client.messages.stream.return_value = fake_stream

        chunks = []
        async for ch in adapter.complete_stream(sample_request):
            chunks.append(ch)
        assert len(chunks) == 3
        assert chunks[0].content_delta == "Hello"

    async def test_stream_with_tool_call(self, adapter, mock_client, sample_request):
        """Test streaming that ends with a tool call."""
        fake_stream = AsyncMock()
        fake_stream.__aenter__ = AsyncMock(return_value=fake_stream)
        fake_stream.__aexit__ = AsyncMock(return_value=None)

        async def _tc_text_stream():
            for val in ["Let", " me", " check"]:
                yield val
        fake_stream.text_stream = _tc_text_stream()

        final_msg = make_mock_message(
            text="Let me check",
            tool_calls=[{"id": "tc_1", "name": "get_weather", "input": {"city": "Paris"}}],
            stop_reason="tool_use",
        )
        fake_stream.get_final_message = AsyncMock(return_value=final_msg)
        mock_client.messages.stream.return_value = fake_stream

        chunks = []
        async for ch in adapter.complete_stream(sample_request):
            chunks.append(ch)

        # Should have 3 text deltas + 1 tool call chunk
        assert len(chunks) == 4
        assert chunks[3].finish_reason == "tool_use"
        assert chunks[3].tool_call_delta is not None
        tc_data = json.loads(chunks[3].tool_call_delta)
        assert tc_data["name"] == "get_weather"

    async def test_stream_with_thinking_effort(self, adapter, mock_client, sample_request):
        req = CompletionRequest(
            messages=sample_request.messages, model="claude-sonnet-4-6",
            max_tokens=100, effort=EffortLevel.LOW,
        )
        fake_stream = AsyncMock()
        fake_stream.__aenter__ = AsyncMock(return_value=fake_stream)
        fake_stream.__aexit__ = AsyncMock(return_value=None)

        async def _th_text_stream():
            yield "thinking"
        fake_stream.text_stream = _th_text_stream()
        fake_stream.get_final_message = AsyncMock(
            return_value=make_mock_message(text="thinking"),
        )
        mock_client.messages.stream.return_value = fake_stream

        chunks = []
        async for ch in adapter.complete_stream(req):
            chunks.append(ch)
        assert len(chunks) == 1

        call_kwargs = mock_client.messages.stream.call_args.kwargs
        assert "thinking" in call_kwargs
        assert call_kwargs["thinking"]["budget_tokens"] == 1024

    async def test_stream_api_status_error(self, adapter, mock_client, sample_request):
        import anthropic
        # Use a context manager mock whose __aenter__ raises
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(
            side_effect=anthropic.APIStatusError(
                message="err", response=MagicMock(status_code=500), body="{}",
            ),
        )
        mock_client.messages.stream.return_value = cm
        chunks = []
        async for ch in adapter.complete_stream(sample_request):
            chunks.append(ch)
        assert len(chunks) == 1
        assert chunks[0].finish_reason == "error"

    async def test_stream_api_timeout_error(self, adapter, mock_client, sample_request):
        import anthropic
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(
            side_effect=anthropic.APITimeoutError("timeout"),
        )
        mock_client.messages.stream.return_value = cm
        chunks = []
        async for ch in adapter.complete_stream(sample_request):
            chunks.append(ch)
        assert len(chunks) == 1
        assert chunks[0].finish_reason == "error"


# ---------------------------------------------------------------------------
# supports
# ---------------------------------------------------------------------------


class TestAnthropicAdapterSupports:
    def test_supported(self, adapter):
        assert adapter.supports(Capability.TEXT_GENERATION)
        assert adapter.supports(Capability.TOOL_USE)
        assert adapter.supports(Capability.VISION)
        assert adapter.supports(Capability.STREAMING)
        assert adapter.supports(Capability.JSON_MODE)
        assert adapter.supports(Capability.LONG_CONTEXT)

    def test_unsupported(self, adapter):
        assert not adapter.supports(Capability.AUDIO_INPUT)
        assert not adapter.supports(Capability.AUDIO_OUTPUT)


# ---------------------------------------------------------------------------
# cost_estimate
# ---------------------------------------------------------------------------


class TestAnthropicAdapterCostEstimate:
    def test_known_model(self, adapter):
        request = CompletionRequest(
            messages=(Message(role="user", content="Hello"),),
            model="claude-sonnet-4-6",
            max_tokens=100,
        )
        cost = adapter.cost_estimate(request)
        assert isinstance(cost, CostEstimate)
        assert cost.input_cost > 0
        assert cost.output_cost > 0
        assert cost.total_max_cost > 0

    def test_unknown_model(self, adapter):
        request = CompletionRequest(
            messages=(Message(role="user", content="Hi"),),
            model="some-unknown-model",
            max_tokens=50,
        )
        cost = adapter.cost_estimate(request)
        assert cost.total_max_cost > 0

    def test_empty_messages(self, adapter):
        request = CompletionRequest(
            messages=(),
            model="claude-sonnet-4-6",
            max_tokens=100,
        )
        cost = adapter.cost_estimate(request)
        assert cost.total_max_cost > 0

    def test_large_prompt(self, adapter):
        request = CompletionRequest(
            messages=(Message(role="user", content="A" * 10000),),
            model="claude-sonnet-4-6",
            max_tokens=1000,
        )
        cost = adapter.cost_estimate(request)
        assert cost.input_cost > 0
        assert cost.output_cost > 0


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


class TestAnthropicAdapterClose:
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
            adapter.close()
