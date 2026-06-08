"""
Unit tests for the Google (Gemini) provider adapter.

Mocks all external API calls (google.genai SDK) to test public methods,
error paths, and edge cases without a real API key.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lyra.routing.provider.adapters.google import (
    GoogleAdapter,
    _count_tokens_heuristic,
    _get_pricing,
    _messages_to_gemini,
    _parse_gemini_response,
    _tools_to_gemini,
)
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
    def test_exact_match(self) -> None:
        inp, out = _get_pricing("gemini-2-5-flash")
        assert inp == 0.15
        assert out == 0.60

    def test_prefix_match(self) -> None:
        inp, out = _get_pricing("gemini-2-5-flash-v2")
        assert inp == 0.15
        assert out == 0.60

    def test_unknown_model(self) -> None:
        inp, out = _get_pricing("some-other-model")
        assert inp == 0.15  # _DEFAULT_INPUT_PRICE
        assert out == 0.60  # _DEFAULT_OUTPUT_PRICE

    def test_empty_string(self) -> None:
        inp, out = _get_pricing("")
        assert inp == 0.15
        assert out == 0.60


# ---------------------------------------------------------------------------
# _count_tokens_heuristic
# ---------------------------------------------------------------------------


class TestCountTokensHeuristic:
    def test_normal_text(self) -> None:
        assert _count_tokens_heuristic("hello world") == 2

    def test_empty_string(self) -> None:
        assert _count_tokens_heuristic("") == 1


# ---------------------------------------------------------------------------
# _messages_to_gemini
# ---------------------------------------------------------------------------


class TestMessagesToGemini:
    def test_system_message_returned_separately(self) -> None:
        msgs = (
            Message(role="system", content="Be a helpful assistant."),
            Message(role="user", content="Hello"),
        )
        contents, system_text = _messages_to_gemini(msgs)
        assert system_text == "Be a helpful assistant."
        assert len(contents) == 1
        assert contents[0].role == "user"

    def test_user_equates_to_user_role(self) -> None:
        msgs = (Message(role="user", content="Hi"),)
        contents, system_text = _messages_to_gemini(msgs)
        assert system_text is None
        assert contents[0].role == "user"

    def test_assistant_equates_to_model_role(self) -> None:
        msgs = (Message(role="assistant", content="Hello back"),)
        contents, system_text = _messages_to_gemini(msgs)
        assert contents[0].role == "model"

    def test_tool_role_becomes_model_role(self) -> None:
        msgs = (Message(role="tool", content="tool result"),)
        contents, system_text = _messages_to_gemini(msgs)
        assert contents[0].role == "model"

    def test_assistant_with_tool_calls(self) -> None:
        tc = ToolCall(id="tc1", name="get_weather", arguments={"city": "Paris"})
        msgs = (Message(role="assistant", content="", tool_calls=(tc,)),)
        contents, system_text = _messages_to_gemini(msgs)
        assert len(contents) == 1
        assert len(contents[0].parts) == 1
        assert contents[0].parts[0].function_call is not None
        assert contents[0].parts[0].function_call.name == "get_weather"

    def test_empty_content_skipped(self) -> None:
        msgs = (Message(role="user", content=""),)
        contents, system_text = _messages_to_gemini(msgs)
        # No parts -> no content added
        assert len(contents) == 0


# ---------------------------------------------------------------------------
# _tools_to_gemini
# ---------------------------------------------------------------------------


class TestToolsToGemini:
    def test_single_tool(self) -> None:
        tools = (
            ToolDef(name="get_weather", description="Weather tool",
                    parameters={"type": "object"}),
        )
        result = _tools_to_gemini(tools)
        assert len(result) == 1
        declarations = result[0].function_declarations
        assert len(declarations) == 1
        assert declarations[0].name == "get_weather"

    def test_multiple_tools(self) -> None:
        tools = (
            ToolDef(name="a", description="tool a", parameters={}),
            ToolDef(name="b", description="tool b", parameters={}),
        )
        result = _tools_to_gemini(tools)
        assert len(result[0].function_declarations) == 2

    def test_empty_tuple(self) -> None:
        from google.genai.types import Tool as GenAITool
        result = _tools_to_gemini(())
        assert len(result) == 1
        assert isinstance(result[0], GenAITool)
        assert len(result[0].function_declarations) == 0


# ---------------------------------------------------------------------------
# _parse_gemini_response
# ---------------------------------------------------------------------------


class TestParseGeminiResponse:
    def test_basic_response(self) -> None:
        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [MagicMock()]
        mock_response.candidates[0].content.parts[0].text = "Hello from Gemini"
        mock_response.candidates[0].content.parts[0].function_call = None
        mock_response.candidates[0].finish_reason = MagicMock()
        mock_response.candidates[0].finish_reason.name = "STOP"
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 20

        result = _parse_gemini_response(mock_response, 15.0, "gemini-2-5-flash")
        assert result.content == "Hello from Gemini"
        assert result.finish_reason == "stop"
        assert result.model == "gemini-2-5-flash"
        assert result.latency_ms == 15.0
        assert result.usage.input_tokens == 10
        assert result.usage.output_tokens == 20
        assert result.tool_calls is None

    def test_with_function_call(self) -> None:
        """Response includes a function_call part."""
        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [MagicMock()]
        mock_response.candidates[0].content.parts[0].text = ""
        fc = MagicMock()
        fc.name = "get_weather"
        fc.args = {"city": "Tokyo"}
        mock_response.candidates[0].content.parts[0].function_call = fc
        mock_response.candidates[0].finish_reason = MagicMock()
        mock_response.candidates[0].finish_reason.name = "STOP"
        mock_response.usage_metadata = None

        result = _parse_gemini_response(mock_response, 5.0, "gemini-2-5-pro")
        assert result.tool_calls is not None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "get_weather"
        assert result.tool_calls[0].arguments == {"city": "Tokyo"}
        # Usage defaults when usage_metadata is missing
        assert result.usage.input_tokens == 0
        assert result.usage.output_tokens == 0

    def test_no_candidates(self) -> None:
        """Empty candidates list returns empty response."""
        mock_response = MagicMock()
        mock_response.candidates = []
        mock_response.usage_metadata = None

        result = _parse_gemini_response(mock_response, 1.0, "gemini-2-5-flash")
        assert result.content == ""
        assert result.finish_reason == "stop"
        assert result.tool_calls is None

    def test_finish_reason_candidates_none(self) -> None:
        """When candidates[0].finish_reason is None, fallback to 'stop'."""
        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [MagicMock()]
        mock_response.candidates[0].content.parts[0].text = "hi"
        mock_response.candidates[0].content.parts[0].function_call = None
        mock_response.candidates[0].finish_reason = None
        mock_response.usage_metadata = None

        result = _parse_gemini_response(mock_response, 1.0, "m")
        assert result.finish_reason == "stop"


# ---------------------------------------------------------------------------
# GoogleAdapter
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_genai_client():
    """Mock the google.genai.Client used by GoogleAdapter."""
    with patch("lyra.routing.provider.adapters.google.GenAIClient") as mock_cls:
        instance = mock_cls.return_value
        yield instance


@pytest.fixture
def adapter(mock_genai_client):
    """GoogleAdapter with a mocked client and env key."""
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-google-key"}):
        yield GoogleAdapter()


@pytest.fixture
def sample_request():
    return CompletionRequest(
        messages=(
            Message(role="system", content="You are a helpful Gemini assistant."),
            Message(role="user", content="What is the capital of Japan?"),
        ),
        model="gemini-2-5-flash",
        max_tokens=100,
        temperature=0.0,
        effort=EffortLevel.MEDIUM,
    )


class TestGoogleAdapterInit:
    def test_with_explicit_api_key(self, mock_genai_client):
        with patch("lyra.routing.provider.adapters.google.GenAIClient") as mock_cls:
            GoogleAdapter(api_key="explicit-key")
            mock_cls.assert_called_once_with(api_key="explicit-key")

    def test_with_env_var(self, mock_genai_client):
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "env-key"}, clear=True):
            with patch("lyra.routing.provider.adapters.google.GenAIClient") as mock_cls:
                GoogleAdapter()
                mock_cls.assert_called_once_with(api_key="env-key")

    def test_no_key_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Google API key not provided"):
                GoogleAdapter()

    def test_provider_name(self, adapter):
        assert adapter.provider_name == "google"


class TestGoogleAdapterComplete:
    async def test_success(self, adapter, mock_genai_client, sample_request):
        """Happy path: complete returns a proper CompletionResponse."""
        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [MagicMock()]
        mock_response.candidates[0].content.parts[0].text = "Tokyo"
        mock_response.candidates[0].content.parts[0].function_call = None
        mock_response.candidates[0].finish_reason = MagicMock()
        mock_response.candidates[0].finish_reason.name = "STOP"
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 5

        mock_genai_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        response = await adapter.complete(sample_request)
        assert response.content == "Tokyo"
        assert response.finish_reason == "stop"
        assert response.usage.input_tokens == 10
        assert response.usage.output_tokens == 5
        assert response.latency_ms > 0

    async def test_with_system_instruction(self, adapter, mock_genai_client, sample_request):
        """System instruction is sent in config."""
        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [MagicMock()]
        mock_response.candidates[0].content.parts[0].text = "OK"
        mock_response.candidates[0].content.parts[0].function_call = None
        mock_response.candidates[0].finish_reason = MagicMock()
        mock_response.candidates[0].finish_reason.name = "STOP"
        mock_response.usage_metadata = None

        mock_genai_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        response = await adapter.complete(sample_request)
        assert response.content == "OK"
        # Verify system_instruction was passed
        call_kwargs = mock_genai_client.aio.models.generate_content.call_args.kwargs
        config = call_kwargs.get("config", {})
        assert config.get("system_instruction") == "You are a helpful Gemini assistant."

    async def test_with_tools(self, adapter, mock_genai_client, sample_request):
        """Tools are passed in config."""
        tools = (
            ToolDef(name="get_weather", description="Weather tool",
                    parameters={"type": "object"}),
        )
        req = CompletionRequest(
            messages=sample_request.messages, model="gemini-2-5-flash",
            max_tokens=100, temperature=0.0, tools=tools,
        )
        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [MagicMock()]
        mock_response.candidates[0].content.parts[0].text = "Sunny"
        mock_response.candidates[0].content.parts[0].function_call = None
        mock_response.candidates[0].finish_reason = MagicMock()
        mock_response.candidates[0].finish_reason.name = "STOP"
        mock_response.usage_metadata = None

        mock_genai_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        response = await adapter.complete(req)
        assert response.content == "Sunny"
        call_kwargs = mock_genai_client.aio.models.generate_content.call_args.kwargs
        assert "tools" in call_kwargs.get("config", {})

    async def test_api_error(self, adapter, mock_genai_client, sample_request):
        """Generic exception is logged and re-raised."""
        mock_genai_client.aio.models.generate_content = AsyncMock(
            side_effect=RuntimeError("API failure"),
        )
        with pytest.raises(RuntimeError, match="API failure"):
            await adapter.complete(sample_request)


class TestGoogleAdapterCompleteStream:
    async def test_stream_success(self, adapter, mock_genai_client, sample_request):
        """Streaming yields CompletionChunk instances with text deltas."""

        async def _mock_stream():
            for text in ["Hello ", "from ", "Gemini"]:
                chunk = MagicMock()
                chunk.text = text
                yield chunk

        mock_genai_client.aio.models.generate_content_stream = AsyncMock(
            return_value=_mock_stream(),
        )

        chunks = []
        async for ch in adapter.complete_stream(sample_request):
            chunks.append(ch)

        assert len(chunks) == 3
        assert chunks[0].content_delta == "Hello "
        assert chunks[1].content_delta == "from "
        assert chunks[2].content_delta == "Gemini"

    async def test_stream_chunk_without_text_attribute(self, adapter, mock_genai_client, sample_request):
        """Chunk without a 'text' attribute yields empty content_delta."""

        async def _mock_stream():
            chunk = MagicMock(spec=[])  # no text attribute
            yield chunk

        mock_genai_client.aio.models.generate_content_stream = AsyncMock(
            return_value=_mock_stream(),
        )

        chunks = []
        async for ch in adapter.complete_stream(sample_request):
            chunks.append(ch)
        assert len(chunks) == 1
        assert chunks[0].content_delta == ""

    async def test_stream_error(self, adapter, mock_genai_client, sample_request):
        """Exception during streaming yields an error chunk."""
        mock_genai_client.aio.models.generate_content_stream = AsyncMock(
            side_effect=RuntimeError("stream failed"),
        )

        chunks = []
        async for ch in adapter.complete_stream(sample_request):
            chunks.append(ch)
        assert len(chunks) == 1
        assert chunks[0].finish_reason == "error"


class TestGoogleAdapterSupports:
    def test_supported(self, adapter):
        assert adapter.supports(Capability.TEXT_GENERATION)
        assert adapter.supports(Capability.VISION)
        assert adapter.supports(Capability.STREAMING)
        assert adapter.supports(Capability.LONG_CONTEXT)
        assert adapter.supports(Capability.AUDIO_INPUT)

    def test_unsupported(self, adapter):
        assert not adapter.supports(Capability.TOOL_USE)
        assert not adapter.supports(Capability.JSON_MODE)
        assert not adapter.supports(Capability.AUDIO_OUTPUT)


class TestGoogleAdapterCostEstimate:
    def test_cost_estimate_known_model(self, adapter):
        request = CompletionRequest(
            messages=(Message(role="user", content="Hello"),),
            model="gemini-2-5-flash",
            max_tokens=100,
        )
        cost = adapter.cost_estimate(request)
        assert isinstance(cost, CostEstimate)
        assert cost.total_max_cost > 0
        assert cost.output_cost > 0

    def test_cost_estimate_unknown_model(self, adapter):
        request = CompletionRequest(
            messages=(Message(role="user", content="Hi"),),
            model="non-existent-model",
            max_tokens=50,
        )
        cost = adapter.cost_estimate(request)
        assert cost.total_max_cost > 0
