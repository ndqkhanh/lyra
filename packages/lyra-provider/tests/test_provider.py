"""
Unit tests for the Lyra Provider Abstraction Layer (lyra_provider).

Covers:
- Message translation (Lyra ↔ provider formats)
- Tool schema translation
- CapabilityMatrix queries
- Error taxonomy
- Provider adapter instantiation (Anthropic, DeepSeek, OpenAI, Google)
"""

from __future__ import annotations

import pytest

from lyra_provider import (
    CapabilityMatrix,
    ChatRequest,
    ChatResponse,
    ErrorCode,
    LLMUsage,
    Message,
    MessageRole,
    ProviderConfig,
    ProviderError,
    StreamEvent,
    ToolCall,
    ToolResult,
    ToolSchema,
    get_capability_matrix,
)
from lyra_provider.adapters import (
    AnthropicProvider,
    DeepSeekProvider,
    GoogleProvider,
    OpenAIProvider,
)
from lyra_provider.adapters.anthropic import (
    _from_anthropic_message,
    _from_anthropic_usage,
    _to_anthropic_message,
    _to_anthropic_tool,
)
from lyra_provider.adapters.deepseek import (
    _from_openai_message,
    _from_openai_usage,
    _to_openai_message,
    _to_openai_tool,
)
from lyra_provider.capability import ProviderCapability


# ────────────────────────────────────────────────────────────────────
# Message translation tests
# ────────────────────────────────────────────────────────────────────


class TestMessageTranslation:
    """Message format translation between Lyra canonical and provider formats."""

    def test_user_message_to_anthropic(self) -> None:
        msg = Message(role=MessageRole.USER, content="Hello, Claude!")
        result = _to_anthropic_message(msg)
        assert result["role"] == "user"
        assert result["content"] == "Hello, Claude!"

    def test_system_message_to_anthropic(self) -> None:
        msg = Message(role=MessageRole.SYSTEM, content="You are helpful.")
        result = _to_anthropic_message(msg)
        assert result["role"] == "system"
        assert result["content"] == "You are helpful."

    def test_assistant_with_tool_calls_to_anthropic(self) -> None:
        msg = Message(
            role=MessageRole.ASSISTANT,
            content="",
            tool_calls=[
                ToolCall(id="tc_1", name="read_file", arguments={"path": "/tmp/x"}),
            ],
        )
        result = _to_anthropic_message(msg)
        assert result["role"] == "assistant"
        assert isinstance(result["content"], list)
        assert result["content"][0]["type"] == "tool_use"
        assert result["content"][0]["name"] == "read_file"

    def test_tool_result_to_anthropic(self) -> None:
        msg = Message(
            role=MessageRole.TOOL,
            content="file contents here",
            tool_result=ToolResult(tool_call_id="tc_1", name="read_file", content="file contents here"),
        )
        result = _to_anthropic_message(msg)
        assert result["role"] == "user"
        assert isinstance(result["content"], list)
        assert result["content"][0]["type"] == "tool_result"

    def test_from_anthropic_text_message(self) -> None:
        anthropic_msg = {
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello back!"}],
        }
        result = _from_anthropic_message(anthropic_msg)
        assert result.role == MessageRole.ASSISTANT
        assert result.content == "Hello back!"

    def test_from_anthropic_tool_use_message(self) -> None:
        anthropic_msg = {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Let me check that file."},
                {
                    "type": "tool_use",
                    "id": "toolu_01",
                    "name": "read_file",
                    "input": {"path": "/tmp/x"},
                },
            ],
        }
        result = _from_anthropic_message(anthropic_msg)
        assert result.tool_calls is not None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "read_file"
        assert result.tool_calls[0].arguments == {"path": "/tmp/x"}

    def test_user_message_to_openai(self) -> None:
        msg = Message(role=MessageRole.USER, content="Hello!")
        result = _to_openai_message(msg)
        assert result["role"] == "user"
        assert result["content"] == "Hello!"

    def test_assistant_with_tool_calls_to_openai(self) -> None:
        msg = Message(
            role=MessageRole.ASSISTANT,
            content="",
            tool_calls=[
                ToolCall(id="tc_1", name="search", arguments={"query": "test"}),
            ],
        )
        result = _to_openai_message(msg)
        assert result["role"] == "assistant"
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["function"]["name"] == "search"

    def test_from_openai_tool_call_message(self) -> None:
        openai_msg = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "tc_1",
                    "type": "function",
                    "function": {
                        "name": "search",
                        "arguments": '{"query": "test"}',
                    },
                },
            ],
        }
        result = _from_openai_message(openai_msg)
        assert result.tool_calls is not None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "search"
        assert result.tool_calls[0].arguments == {"query": "test"}


# ────────────────────────────────────────────────────────────────────
# Tool schema translation tests
# ────────────────────────────────────────────────────────────────────


class TestToolSchemaTranslation:
    """Tool schema translation between Lyra canonical and provider formats."""

    def test_to_anthropic_tool(self) -> None:
        tool = ToolSchema(
            name="read_file",
            description="Read a file from disk",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                },
                "required": ["path"],
            },
        )
        result = _to_anthropic_tool(tool)
        assert result["name"] == "read_file"
        assert result["input_schema"]["type"] == "object"

    def test_to_openai_tool(self) -> None:
        tool = ToolSchema(
            name="search",
            description="Search the web",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string"}},
            },
        )
        result = _to_openai_tool(tool)
        assert result["type"] == "function"
        assert result["function"]["name"] == "search"


# ────────────────────────────────────────────────────────────────────
# Usage translation tests
# ────────────────────────────────────────────────────────────────────


class TestUsageTranslation:
    """Token usage translation to Lyra LLMUsage."""

    def test_from_anthropic_usage(self) -> None:
        usage = _from_anthropic_usage({
            "input_tokens": 500,
            "output_tokens": 200,
            "cache_read_input_tokens": 100,
            "cache_creation_input_tokens": 50,
        })
        assert usage.input_tokens == 500
        assert usage.output_tokens == 200
        assert usage.cache_read_tokens == 100
        assert usage.cache_write_tokens == 50

    def test_from_openai_usage(self) -> None:
        usage = _from_openai_usage({
            "prompt_tokens": 300,
            "completion_tokens": 150,
        })
        assert usage.input_tokens == 300
        assert usage.output_tokens == 150

    def test_from_openai_usage_none(self) -> None:
        usage = _from_openai_usage(None)
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0


# ────────────────────────────────────────────────────────────────────
# CapabilityMatrix tests
# ────────────────────────────────────────────────────────────────────


class TestCapabilityMatrix:
    """Tests for the provider capability matrix."""

    def test_anthropic_supports_vision(self) -> None:
        matrix = get_capability_matrix()
        assert matrix.supports("anthropic", "vision") is True

    def test_deepseek_does_not_support_vision(self) -> None:
        matrix = get_capability_matrix()
        assert matrix.supports("deepseek", "vision") is False

    def test_anthropic_supports_prompt_caching(self) -> None:
        matrix = get_capability_matrix()
        assert matrix.supports("anthropic", "prompt_caching") is True

    def test_openweights_does_not_support_tool_calling(self) -> None:
        matrix = get_capability_matrix()
        assert matrix.supports("openweights", "tool_calling") is False

    def test_unknown_provider_returns_false(self) -> None:
        matrix = get_capability_matrix()
        assert matrix.supports("nonexistent", "vision") is False

    def test_list_providers_supporting_vision(self) -> None:
        matrix = get_capability_matrix()
        vision_providers = matrix.list_providers_supporting("vision")
        assert "anthropic" in vision_providers
        assert "openai" in vision_providers
        assert "google" in vision_providers
        assert "deepseek" not in vision_providers

    def test_context_windows(self) -> None:
        matrix = get_capability_matrix()
        assert matrix.get_context_window("anthropic") == 200_000
        assert matrix.get_context_window("google") == 1_000_000
        assert matrix.get_context_window("deepseek") == 128_000

    def test_all_known_providers_registered(self) -> None:
        matrix = get_capability_matrix()
        providers = matrix.list_providers()
        assert "anthropic" in providers
        assert "deepseek" in providers
        assert "openai" in providers
        assert "google" in providers
        assert "openrouter" in providers
        assert "openweights" in providers

    def test_provider_capability_attributes(self) -> None:
        cap = get_capability_matrix().get("anthropic")
        assert cap is not None
        assert cap.tool_calling is True
        assert cap.json_mode is True
        assert cap.streaming is True
        assert cap.max_context_tokens == 200_000


# ────────────────────────────────────────────────────────────────────
# ProviderError tests
# ────────────────────────────────────────────────────────────────────


class TestProviderError:
    """Tests for the provider error taxonomy."""

    def test_auth_error(self) -> None:
        err = ProviderError(code=ErrorCode.AUTH_ERROR, message="Invalid key", provider="anthropic")
        assert err.code == ErrorCode.AUTH_ERROR
        assert not err.retryable
        assert "anthropic" in str(err)

    def test_rate_limit_is_retryable(self) -> None:
        err = ProviderError(code=ErrorCode.RATE_LIMIT, message="Too many requests", provider="deepseek", retryable=True)
        assert err.retryable is True

    def test_error_can_be_raised(self) -> None:
        with pytest.raises(ProviderError) as exc_info:
            raise ProviderError(code=ErrorCode.TIMEOUT, message="Request timed out", provider="openai")
        assert exc_info.value.code == ErrorCode.TIMEOUT


# ────────────────────────────────────────────────────────────────────
# Provider adapter instantiation (no network calls)
# ────────────────────────────────────────────────────────────────────


class TestProviderAdapters:
    """Provider adapter creation and basic attribute tests."""

    def test_create_anthropic_provider(self) -> None:
        config = ProviderConfig(provider="anthropic", api_key="test-key")
        provider = AnthropicProvider(config)
        assert provider.provider_name == "anthropic"
        assert provider.supports_feature("tool_calling") is True
        assert provider.supports_feature("vision") is True
        assert provider.supports_feature("prompt_caching") is True
        assert provider.supports_feature("nonexistent") is False

    def test_create_deepseek_provider(self) -> None:
        config = ProviderConfig(provider="deepseek", api_key="test-key")
        provider = DeepSeekProvider(config)
        assert provider.provider_name == "deepseek"
        assert provider.supports_feature("tool_calling") is True
        assert provider.supports_feature("vision") is False

    def test_create_openai_provider(self) -> None:
        config = ProviderConfig(provider="openai", api_key="test-key")
        provider = OpenAIProvider(config)
        assert provider.provider_name == "openai"
        assert provider.supports_feature("vision") is True

    def test_create_google_provider(self) -> None:
        config = ProviderConfig(provider="google", api_key="test-key")
        provider = GoogleProvider(config)
        assert provider.provider_name == "google"

    def test_google_provider_chat_raises_not_implemented(self) -> None:
        import asyncio
        config = ProviderConfig(provider="google", api_key="test-key")
        provider = GoogleProvider(config)
        with pytest.raises(ProviderError, match="not yet implemented"):
            asyncio.get_event_loop().run_until_complete(
                provider.chat(ChatRequest(messages=[], model="gemini-2.5-flash"))
            )

    def test_context_windows_per_model(self) -> None:
        config = ProviderConfig(provider="anthropic", api_key="test-key")
        provider = AnthropicProvider(config)
        assert provider.get_context_window("claude-sonnet-4-20250514") == 200_000
        assert provider.get_context_window("unknown-model") == 200_000  # default

    def test_deepseek_context_windows(self) -> None:
        config = ProviderConfig(provider="deepseek", api_key="test-key")
        provider = DeepSeekProvider(config)
        assert provider.get_context_window("deepseek-chat-v4") == 128_000


# ────────────────────────────────────────────────────────────────────
# Data model roundtrip tests
# ────────────────────────────────────────────────────────────────────


class TestDataModels:
    """Lyra canonical data models create/read correctly."""

    def test_chat_request_defaults(self) -> None:
        req = ChatRequest(messages=[Message(role=MessageRole.USER, content="Hi")], model="test")
        assert req.stream is False
        assert req.max_tokens == 4096
        assert req.tools is None

    def test_chat_response_with_tool_calls(self) -> None:
        resp = ChatResponse(
            content="",
            model="claude-sonnet-4",
            tool_calls=[ToolCall(id="1", name="search", arguments={"query": "x"})],
        )
        assert resp.tool_calls is not None
        assert len(resp.tool_calls) == 1

    def test_stream_event_types(self) -> None:
        text_event = StreamEvent(type="text_delta", content="Hello")
        assert text_event.type == "text_delta"

        done_event = StreamEvent(type="done", usage=LLMUsage(input_tokens=10, output_tokens=5))
        assert done_event.type == "done"
        assert done_event.usage is not None
        assert done_event.usage.input_tokens == 10

        error_event = StreamEvent(type="error", error="Something went wrong")
        assert error_event.type == "error"
        assert error_event.error == "Something went wrong"

    def test_message_frozen(self) -> None:
        """ToolCall and ToolResult should be frozen (immutable)."""
        tc = ToolCall(id="1", name="test", arguments={})
        with pytest.raises(Exception):  # FrozenInstanceError or similar
            tc.name = "changed"  # type: ignore[misc]
