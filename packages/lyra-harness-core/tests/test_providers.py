"""Tests for multi-provider abstraction layer."""
import pytest

from lyra_harness_core.messages import Message, StopReason, ToolCall
from lyra_harness_core.providers import (
    AnthropicProvider,
    OpenAICompatibleProvider,
    ProviderConfig,
    ProviderHealth,
    ProviderInfo,
    ProviderKind,
    ProviderRegistry,
    StreamChunk,
    TokenUsage,
    create_provider,
    create_provider_registry,
    get_provider_registry,
)


# ---------------------------------------------------------------------------
# TokenUsage
# ---------------------------------------------------------------------------


class TestTokenUsage:
    def test_defaults(self):
        u = TokenUsage()
        assert u.input_tokens == 0
        assert u.output_tokens == 0
        assert u.cache_read_tokens == 0
        assert u.cache_write_tokens == 0
        assert u.total_tokens == 0
        assert u.cache_hit_ratio == 0.0

    def test_cache_hit_ratio(self):
        u = TokenUsage(input_tokens=100, cache_read_tokens=40)
        assert u.cache_hit_ratio == 0.4

    def test_cache_hit_ratio_zero_input(self):
        u = TokenUsage(input_tokens=0, cache_read_tokens=10)
        assert u.cache_hit_ratio == 0.0


# ---------------------------------------------------------------------------
# StreamChunk
# ---------------------------------------------------------------------------


class TestStreamChunk:
    def test_content_chunk(self):
        c = StreamChunk(content="hello")
        assert c.content == "hello"
        assert c.tool_call is None

    def test_stop_chunk(self):
        c = StreamChunk(stop_reason=StopReason.END_TURN)
        assert c.stop_reason == StopReason.END_TURN
        assert c.content == ""

    def test_usage_chunk(self):
        u = TokenUsage(input_tokens=10, output_tokens=5, total_tokens=15)
        c = StreamChunk(usage=u)
        assert c.usage == u


# ---------------------------------------------------------------------------
# ProviderConfig
# ---------------------------------------------------------------------------


class TestProviderConfig:
    def test_minimal(self):
        cfg = ProviderConfig(kind=ProviderKind.ANTHROPIC, model="claude-sonnet-4-6")
        assert cfg.kind == ProviderKind.ANTHROPIC
        assert cfg.model == "claude-sonnet-4-6"

    def test_full(self):
        cfg = ProviderConfig(
            kind=ProviderKind.DEEPSEEK,
            model="deepseek-chat",
            api_key="sk-test",
            base_url="https://api.deepseek.com/v1",
            max_tokens=8192,
            temperature=0.7,
        )
        assert cfg.api_key == "sk-test"
        assert cfg.base_url == "https://api.deepseek.com/v1"
        assert cfg.max_tokens == 8192
        assert cfg.temperature == 0.7


# ---------------------------------------------------------------------------
# ProviderInfo
# ---------------------------------------------------------------------------


class TestProviderInfo:
    def test_defaults(self):
        cfg = ProviderConfig(kind=ProviderKind.MOCK, model="mock")
        info = ProviderInfo(config=cfg)
        assert info.health == ProviderHealth.UNKNOWN
        assert info.consecutive_failures == 0
        assert info.total_requests == 0
        assert info.error_rate == 0.0

    def test_error_rate(self):
        cfg = ProviderConfig(kind=ProviderKind.MOCK, model="mock")
        info = ProviderInfo(config=cfg, total_requests=10, total_errors=3)
        assert info.error_rate == 0.3

    def test_error_rate_zero_requests(self):
        cfg = ProviderConfig(kind=ProviderKind.MOCK, model="mock")
        info = ProviderInfo(config=cfg, total_requests=0, total_errors=5)
        assert info.error_rate == 0.0


# ---------------------------------------------------------------------------
# ProviderRegistry
# ---------------------------------------------------------------------------


class TestProviderRegistry:
    def test_register_sets_default(self):
        reg = ProviderRegistry()
        cfg = ProviderConfig(kind=ProviderKind.MOCK, model="mock")
        reg.register("mock", _MockProvider(cfg))
        assert reg.default_name == "mock"

    def test_register_second_does_not_override_default(self):
        reg = ProviderRegistry()
        cfg1 = ProviderConfig(kind=ProviderKind.MOCK, model="m1")
        cfg2 = ProviderConfig(kind=ProviderKind.MOCK, model="m2")
        reg.register("first", _MockProvider(cfg1))
        reg.register("second", _MockProvider(cfg2))
        assert reg.default_name == "first"

    def test_set_default(self):
        reg = ProviderRegistry()
        cfg1 = ProviderConfig(kind=ProviderKind.MOCK, model="m1")
        cfg2 = ProviderConfig(kind=ProviderKind.MOCK, model="m2")
        reg.register("a", _MockProvider(cfg1))
        reg.register("b", _MockProvider(cfg2))
        reg.set_default("b")
        assert reg.default_name == "b"

    def test_set_default_unknown_raises(self):
        reg = ProviderRegistry()
        with pytest.raises(KeyError):
            reg.set_default("nonexistent")

    def test_register_duplicate_raises(self):
        reg = ProviderRegistry()
        cfg = ProviderConfig(kind=ProviderKind.MOCK, model="mock")
        reg.register("x", _MockProvider(cfg))
        with pytest.raises(ValueError):
            reg.register("x", _MockProvider(cfg))

    def test_unregister(self):
        reg = ProviderRegistry()
        cfg = ProviderConfig(kind=ProviderKind.MOCK, model="mock")
        reg.register("x", _MockProvider(cfg))
        reg.unregister("x")
        assert reg.get("x") is None

    def test_unregister_default_falls_back(self):
        reg = ProviderRegistry()
        cfg1 = ProviderConfig(kind=ProviderKind.MOCK, model="m1")
        cfg2 = ProviderConfig(kind=ProviderKind.MOCK, model="m2")
        reg.register("a", _MockProvider(cfg1))
        reg.register("b", _MockProvider(cfg2))
        reg.unregister("a")
        assert reg.default_name == "b"

    def test_get_none(self):
        reg = ProviderRegistry()
        assert reg.get() is None

    def test_get_info(self):
        reg = ProviderRegistry()
        cfg = ProviderConfig(kind=ProviderKind.MOCK, model="mock")
        reg.register("mock", _MockProvider(cfg))
        info = reg.get_info("mock")
        assert info is not None
        assert info.config.kind == ProviderKind.MOCK

    def test_list_providers(self):
        reg = ProviderRegistry()
        cfg = ProviderConfig(kind=ProviderKind.MOCK, model="m1")
        reg.register("a", _MockProvider(cfg))
        reg.register("b", _MockProvider(cfg))
        assert set(reg.list_providers().keys()) == {"a", "b"}

    def test_list_by_kind(self):
        reg = ProviderRegistry()
        cfg_ant = ProviderConfig(kind=ProviderKind.ANTHROPIC, model="claude")
        cfg_oai = ProviderConfig(kind=ProviderKind.OPENAI, model="gpt-4o")
        reg.register("claude", _MockProvider(cfg_ant, kind=ProviderKind.ANTHROPIC))
        reg.register("gpt", _MockProvider(cfg_oai, kind=ProviderKind.OPENAI))
        assert reg.list_by_kind(ProviderKind.ANTHROPIC) == ["claude"]
        assert reg.list_by_kind(ProviderKind.OPENAI) == ["gpt"]

    def test_record_failure_circuit_breaker(self):
        reg = ProviderRegistry()
        cfg = ProviderConfig(kind=ProviderKind.MOCK, model="mock")
        reg.register("mock", _MockProvider(cfg))
        for _ in range(3):
            reg.record_failure("mock")
        info = reg.get_info("mock")
        assert info.health == ProviderHealth.DEGRADED
        for _ in range(2):
            reg.record_failure("mock")
        assert info.health == ProviderHealth.UNHEALTHY

    def test_record_success_resets_failures(self):
        reg = ProviderRegistry()
        cfg = ProviderConfig(kind=ProviderKind.MOCK, model="mock")
        reg.register("mock", _MockProvider(cfg))
        for _ in range(3):
            reg.record_failure("mock")
        reg.record_success("mock")
        info = reg.get_info("mock")
        assert info.consecutive_failures == 0
        assert info.health == ProviderHealth.HEALTHY

    def test_get_healthy(self):
        reg = ProviderRegistry()
        cfg = ProviderConfig(kind=ProviderKind.MOCK, model="mock")
        reg.register("a", _MockProvider(cfg))
        reg.register("b", _MockProvider(cfg))
        for _ in range(5):
            reg.record_failure("b")
        healthy = reg.get_healthy()
        assert "a" in healthy
        assert "b" not in healthy


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class TestCreateProvider:
    def test_creates_anthropic(self):
        cfg = ProviderConfig(kind=ProviderKind.ANTHROPIC, model="claude-sonnet-4-6", api_key="test")
        p = create_provider(cfg)
        assert isinstance(p, AnthropicProvider)

    def test_creates_openai_compatible(self):
        for kind in [ProviderKind.DEEPSEEK, ProviderKind.QWEN, ProviderKind.OPENAI,
                     ProviderKind.OPEN_WEIGHTS]:
            cfg = ProviderConfig(kind=kind, model="test-model", api_key="test")
            p = create_provider(cfg)
            assert isinstance(p, OpenAICompatibleProvider)

    def test_unsupported_kind_raises(self):
        cfg = ProviderConfig(kind=ProviderKind.MOCK, model="mock")
        with pytest.raises(ValueError, match="Unsupported"):
            create_provider(cfg)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _MockProvider(AnthropicProvider if False else object):
    """Minimal mock provider for registry tests.

    Cannot inherit from AnthropicProvider without anthropic SDK,
    so we create a minimal LLM-like stub.
    """

    def __init__(self, config: ProviderConfig, kind: ProviderKind | None = None):
        self.config = config
        self.kind = kind or config.kind
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    def generate(self, messages, tools=None, max_tokens=2048, temperature=0.0):
        return Message.assistant(content="mock response")

    @property
    def total_input_tokens(self):
        return self._total_input_tokens

    @property
    def total_output_tokens(self):
        return self._total_output_tokens
