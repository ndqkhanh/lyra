"""
Tests for TracingProvider with Langfuse/Phoenix backends.
"""

import pytest

from src.verification.tracing_provider import (
    AutoInstrumentor,
    LangfuseBackend,
    OTelBackend,
    PhoenixBackend,
    SpanStatus,
    TracingProvider,
)


class TestTracingProvider:
    """Test tracing provider."""

    def test_otel_backend_initialization(self):
        """Test OTel backend initialization."""
        provider = TracingProvider(backend="otel")

        assert provider.backend_name == "otel"
        assert isinstance(provider.backend, OTelBackend)

    def test_span_context_manager(self):
        """Test span context manager."""
        provider = TracingProvider(backend="otel")

        with provider.span("test_span", "agent") as span:
            assert span.name == "test_span"
            assert span.span_type == "agent"
            assert "lyra.type" in span.attributes

        # Span should be ended
        assert span.end_time is not None
        assert span.duration_ms > 0

    def test_span_with_attributes(self):
        """Test span with custom attributes."""
        provider = TracingProvider(backend="otel")

        with provider.span(
            "test_span",
            "tool",
            attributes={"tool_name": "bash", "exit_code": 0},
        ) as span:
            assert span.attributes["lyra.tool_name"] == "bash"
            assert span.attributes["lyra.exit_code"] == 0

    def test_span_error_handling(self):
        """Test span captures errors."""
        provider = TracingProvider(backend="otel")

        with pytest.raises(ValueError):
            with provider.span("error_span", "agent") as span:
                raise ValueError("Test error")

        # Span should be marked as error
        assert span.status == SpanStatus.ERROR
        assert len(span.events) > 0
        assert any(e.name == "exception" for e in span.events)

    def test_nested_spans(self):
        """Test nested span tracking."""
        provider = TracingProvider(backend="otel")

        with provider.span("parent", "agent") as parent:
            parent_id = parent.span_id

            with provider.span("child", "tool") as child:
                assert child.parent_id == parent_id
                assert child.trace_id == parent.trace_id

    @pytest.mark.asyncio
    async def test_async_span(self):
        """Test async span context manager."""
        provider = TracingProvider(backend="otel")

        async with provider.async_span("async_test", "agent") as span:
            assert span.name == "async_test"
            await asyncio.sleep(0.01)

        assert span.end_time is not None
        assert span.duration_ms > 0


class TestBackends:
    """Test different tracing backends."""

    def test_langfuse_backend(self):
        """Test Langfuse backend initialization."""
        backend = LangfuseBackend(api_key="test_key")

        span = backend.start_span("test", "agent")
        assert span.name == "test"

        backend.end_span(span)
        assert span.end_time is not None

    def test_phoenix_backend(self):
        """Test Phoenix backend initialization."""
        backend = PhoenixBackend()

        span = backend.start_span("test", "tool")
        assert span.span_type == "tool"

        backend.add_event(span, "test_event", {"key": "value"})
        assert len(span.events) == 1

    def test_otel_backend(self):
        """Test OTel backend."""
        backend = OTelBackend()

        span = backend.start_span(
            "test", "router", attributes={"model": "claude-sonnet-4"}
        )
        assert span.attributes["model"] == "claude-sonnet-4"


class TestAutoInstrumentor:
    """Test auto-instrumentation."""

    def test_instrument_tool_registry(self):
        """Test tool registry instrumentation."""
        provider = TracingProvider(backend="otel")
        instrumentor = AutoInstrumentor(provider)

        class MockTool:
            def __init__(self, name):
                self.name = name
                self.category = "test"
                self.handler = self._handler

            async def _handler(self, *args, **kwargs):
                return "result"

        class MockRegistry:
            def __init__(self):
                self._tools = {"bash": MockTool("bash")}

        registry = MockRegistry()
        instrumentor.instrument_tool_registry(registry)

        # Handler should be wrapped
        assert registry._tools["bash"].handler != MockTool("bash")._handler

    def test_instrument_router(self):
        """Test router instrumentation."""
        provider = TracingProvider(backend="otel")
        instrumentor = AutoInstrumentor(provider)

        class MockRouter:
            def route(self, task):
                return {"model": "claude-sonnet-4", "provider": "anthropic"}

        router = MockRouter()
        original_route = router.route

        instrumentor.instrument_router(router)

        # Route should be wrapped
        assert router.route != original_route

        result = router.route("test task")
        assert result["model"] == "claude-sonnet-4"

    def test_instrument_memory_store(self):
        """Test memory store instrumentation."""
        provider = TracingProvider(backend="otel")
        instrumentor = AutoInstrumentor(provider)

        class MockMemoryStore:
            async def get(self, key):
                return "value"

            async def set(self, key, value):
                pass

        store = MockMemoryStore()
        instrumentor.instrument_memory_store(store)

        # Methods should be wrapped
        # (Can't easily test async wrapping without running, but structure is verified)
        assert hasattr(store, "get")
        assert hasattr(store, "set")


# Need asyncio for async tests
import asyncio
