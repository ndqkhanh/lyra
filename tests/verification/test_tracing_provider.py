"""Comprehensive tests for TracingProvider and backends."""

from __future__ import annotations

import asyncio
from copy import deepcopy

import pytest

from lyra.verification.tracing_provider import (
    AutoInstrumentor,
    LangfuseBackend,
    OTelBackend,
    PhoenixBackend,
    SpanEvent,
    SpanStatus,
    TraceSpan,
    TracingBackend,
    TracingProvider,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tracing_provider() -> TracingProvider:
    return TracingProvider(backend="otel")


class FakeBackend(TracingBackend):
    """Test backend that records all operations using real span.events append."""

    def __init__(self):
        self.spans: list[TraceSpan] = []
        self.events: list[tuple[TraceSpan, str, dict]] = []

    def start_span(self, name, span_type, trace_id=None, parent_id=None, attributes=None):
        import uuid
        from datetime import datetime

        span = TraceSpan(
            span_id=str(uuid.uuid4()),
            trace_id=trace_id or str(uuid.uuid4()),
            parent_id=parent_id,
            name=name,
            span_type=span_type,
            start_time=datetime.now(),
            attributes=dict(attributes or {}),
        )
        self.spans.append(span)
        return span

    def end_span(self, span, status=SpanStatus.OK):
        from datetime import datetime

        span.end_time = datetime.now()
        span.duration_ms = 1.0
        span.status = status

    def add_event(self, span, name, attributes=None):
        from datetime import datetime

        event = SpanEvent(name=name, timestamp=datetime.now(), attributes=attributes or {})
        span.events.append(event)


@pytest.fixture
def fake_backend() -> FakeBackend:
    return FakeBackend()


# ---------------------------------------------------------------------------
# Tests: Data classes
# ---------------------------------------------------------------------------


class TestSpanEvent:
    def test_create(self):
        from datetime import datetime

        e = SpanEvent(name="test", timestamp=datetime.now(), attributes={"k": "v"})
        assert e.name == "test"


class TestTraceSpan:
    def test_defaults(self):
        from datetime import datetime

        s = TraceSpan(
            span_id="s1", trace_id="t1", parent_id=None, name="test",
            span_type="tool", start_time=datetime.now(),
        )
        assert s.status == SpanStatus.UNSET
        assert s.duration_ms == 0.0
        assert s.end_time is None

    def test_with_parent(self):
        from datetime import datetime

        s = TraceSpan(
            span_id="s1", trace_id="t1", parent_id="parent1", name="child",
            span_type="agent", start_time=datetime.now(),
        )
        assert s.parent_id == "parent1"

    def test_with_attributes(self):
        from datetime import datetime

        s = TraceSpan(
            span_id="s1", trace_id="t1", parent_id=None, name="test",
            span_type="tool", start_time=datetime.now(), attributes={"key": "val"},
        )
        assert s.attributes["key"] == "val"


# ---------------------------------------------------------------------------
# Tests: TracingBackend (base)
# ---------------------------------------------------------------------------


class TestTracingBackend:
    def test_base_methods_raise(self):
        backend = TracingBackend()
        with pytest.raises(NotImplementedError):
            backend.start_span("n", "t")
        with pytest.raises(NotImplementedError):
            backend.end_span(None)
        with pytest.raises(NotImplementedError):
            backend.add_event(None, "n")


# ---------------------------------------------------------------------------
# Tests: OTelBackend
# ---------------------------------------------------------------------------


class TestOTelBackend:
    def test_start_span(self):
        backend = OTelBackend()
        span = backend.start_span("test_op", "tool")
        assert span.name == "test_op"
        assert span.span_type == "tool"
        assert span.span_id in backend._traces

    def test_start_span_with_ids(self):
        backend = OTelBackend()
        span = backend.start_span("child", "agent", trace_id="t1", parent_id="p1")
        assert span.trace_id == "t1"
        assert span.parent_id == "p1"

    def test_end_span(self):
        backend = OTelBackend()
        span = backend.start_span("op", "tool")
        backend.end_span(span, SpanStatus.OK)
        assert span.end_time is not None
        assert span.duration_ms > 0
        assert span.status == SpanStatus.OK

    def test_add_event(self):
        backend = OTelBackend()
        span = backend.start_span("op", "tool")
        backend.add_event(span, "ev", {"k": "v"})
        assert len(span.events) == 1
        assert span.events[0].name == "ev"


# ---------------------------------------------------------------------------
# Tests: PhoenixBackend
# ---------------------------------------------------------------------------


class TestPhoenixBackend:
    def test_start_span(self):
        backend = PhoenixBackend()
        span = backend.start_span("op", "agent")
        assert span.span_type == "agent"

    def test_end_span(self):
        backend = PhoenixBackend()
        span = backend.start_span("op", "tool")
        backend.end_span(span, SpanStatus.OK)
        assert span.duration_ms > 0

    def test_add_event(self):
        backend = PhoenixBackend()
        span = backend.start_span("op", "tool")
        backend.add_event(span, "ev")
        assert len(span.events) == 1


# ---------------------------------------------------------------------------
# Tests: LangfuseBackend
# ---------------------------------------------------------------------------


class TestLangfuseBackend:
    def test_start_span(self):
        backend = LangfuseBackend()
        span = backend.start_span("op", "agent")
        assert span.span_type == "agent"

    def test_end_span(self):
        backend = LangfuseBackend()
        span = backend.start_span("op", "tool")
        backend.end_span(span, SpanStatus.OK)
        assert span.duration_ms > 0

    def test_add_event(self):
        backend = LangfuseBackend()
        span = backend.start_span("op", "tool")
        backend.add_event(span, "ev")
        assert len(span.events) == 1


# ---------------------------------------------------------------------------
# Tests: TracingProvider
# ---------------------------------------------------------------------------


class TestTracingProvider:
    def test_init_backends(self):
        assert isinstance(TracingProvider(backend="otel").backend, OTelBackend)
        assert isinstance(TracingProvider(backend="phoenix").backend, PhoenixBackend)
        assert isinstance(TracingProvider(backend="langfuse").backend, LangfuseBackend)

    def test_init_unknown(self):
        with pytest.raises(ValueError, match="Unknown backend"):
            TracingProvider(backend="unknown")

    def test_span_context_manager(self, fake_backend):
        provider = TracingProvider(backend="otel")
        provider.backend = fake_backend

        with provider.span("test", "tool") as span:
            assert span.name == "test"
            assert span.span_type == "tool"
            assert provider._current_span is span

        assert span.status == SpanStatus.OK
        assert provider._current_span is None

    def test_span_nested(self, fake_backend):
        provider = TracingProvider(backend="otel")
        provider.backend = fake_backend

        with provider.span("parent", "agent") as parent:
            with provider.span("child", "tool") as child:
                assert child.parent_id == parent.span_id
                assert child.trace_id == parent.trace_id
            assert provider._current_span is parent

        assert provider._current_span is None

    def test_span_exception_adds_event(self, fake_backend):
        provider = TracingProvider(backend="otel")
        provider.backend = fake_backend

        with pytest.raises(RuntimeError, match="boom"):
            with provider.span("failing") as span:
                raise RuntimeError("boom")

        assert span.status == SpanStatus.ERROR
        assert len(span.events) == 1
        assert span.events[0].name == "exception"

    def test_span_restores_current_after_exception(self, fake_backend):
        provider = TracingProvider(backend="otel")
        provider.backend = fake_backend

        try:
            with provider.span("outer"):
                with provider.span("inner"):
                    raise ValueError("err")
        except ValueError:
            pass

        # After exception, outer span's finally runs restore to previous (None)
        assert provider._current_span is None

    def test_span_attributes(self, fake_backend):
        provider = TracingProvider(backend="otel")
        provider.backend = fake_backend

        with provider.span("s", "agent", {"custom": "val"}) as span:
            assert span.attributes.get("lyra.type") == "agent"
            assert span.attributes.get("lyra.custom") == "val"

    @pytest.mark.asyncio
    async def test_async_span(self, fake_backend):
        provider = TracingProvider(backend="otel")
        provider.backend = fake_backend

        async with provider.async_span("async_span", "agent") as span:
            assert span.name == "async_span"

        assert span.status == SpanStatus.OK

    @pytest.mark.asyncio
    async def test_async_span_exception(self, fake_backend):
        provider = TracingProvider(backend="otel")
        provider.backend = fake_backend

        with pytest.raises(ValueError, match="async_err"):
            async with provider.async_span("failing") as span:
                raise ValueError("async_err")

        assert span.status == SpanStatus.ERROR

    @pytest.mark.asyncio
    async def test_async_span_nested(self, fake_backend):
        provider = TracingProvider(backend="otel")
        provider.backend = fake_backend

        async with provider.async_span("parent") as parent:
            async with provider.async_span("child") as child:
                assert child.parent_id == parent.span_id

        assert provider._current_span is None

    def test_span_status_enum(self):
        assert SpanStatus.OK.value == "ok"
        assert SpanStatus.ERROR.value == "error"
        assert SpanStatus.UNSET.value == "unset"


# ---------------------------------------------------------------------------
# Tests: AutoInstrumentor
# ---------------------------------------------------------------------------


class TestAutoInstrumentor:
    def test_instrument_tool_registry(self, fake_backend):
        provider = TracingProvider(backend="otel")
        provider.backend = fake_backend
        instrumentor = AutoInstrumentor(provider)

        registry = FakeRegistry()
        instrumentor.instrument_tool_registry(registry)

        # handler should be wrapped - calling it creates a span
        result = asyncio.run(registry._tools["search"].handler("arg"))
        assert result == "search_result"
        # Span should have been created
        assert len(fake_backend.spans) >= 1

    def test_instrument_tool_registry_no_tools(self):
        provider = TracingProvider(backend="otel")
        instrumentor = AutoInstrumentor(provider)
        instrumentor.instrument_tool_registry(object())

    def test_instrument_agent_dispatcher(self, fake_backend):
        provider = TracingProvider(backend="otel")
        provider.backend = fake_backend
        instrumentor = AutoInstrumentor(provider)

        dispatcher = FakeDispatcher()

        # Instrument before calling
        instrumentor.instrument_agent_dispatcher(dispatcher)

        result = asyncio.run(dispatcher.dispatch(agent_name="test_agent"))
        assert result == "dispatched"
        assert len(fake_backend.spans) >= 1

    def test_instrument_agent_dispatcher_no_dispatch(self):
        provider = TracingProvider(backend="otel")
        instrumentor = AutoInstrumentor(provider)
        instrumentor.instrument_agent_dispatcher(object())

    def test_instrument_router_result(self):
        """Instrumenting router should preserve return value."""
        provider = TracingProvider(backend="otel")
        instrumentor = AutoInstrumentor(provider)

        router = FakeRouter()
        instrumentor.instrument_router(router)

        result = router.route("prompt")
        assert result["model"] == "sonnet"
        assert result["provider"] == "anthropic"

    def test_instrument_router_no_route(self):
        provider = TracingProvider(backend="otel")
        instrumentor = AutoInstrumentor(provider)
        instrumentor.instrument_router(object())

    def test_instrument_memory_store(self):
        provider = TracingProvider(backend="otel")
        instrumentor = AutoInstrumentor(provider)

        store = FakeMemoryStore2()
        instrumentor.instrument_memory_store(store)

        val = asyncio.run(store.get("key1"))
        assert val == "value1"
        asyncio.run(store.set("key2", "value2"))
        assert store.data["key2"] == "value2"

    def test_instrument_memory_store_no_methods(self):
        provider = TracingProvider(backend="otel")
        instrumentor = AutoInstrumentor(provider)
        instrumentor.instrument_memory_store(object())

    def test_instrument_hook_engine(self, fake_backend):
        provider = TracingProvider(backend="otel")
        provider.backend = fake_backend
        instrumentor = AutoInstrumentor(provider)

        engine = FakeHookEngine()
        instrumentor.instrument_hook_engine(engine)

        result = asyncio.run(engine.fire("pre_tool"))
        assert result == "fired"
        assert len(fake_backend.spans) >= 1

    def test_instrument_hook_engine_no_fire(self):
        provider = TracingProvider(backend="otel")
        instrumentor = AutoInstrumentor(provider)
        instrumentor.instrument_hook_engine(object())


# ---------------------------------------------------------------------------
# Fake objects for AutoInstrumentor tests
# ---------------------------------------------------------------------------


class FakeTool:
    def __init__(self):
        self.handler = self._handler
        self.category = "search"

    async def _handler(self, *args, **kwargs):
        return "search_result"


class FakeRegistry:
    def __init__(self):
        self._tools = {"search": FakeTool()}


class FakeDispatcher:
    async def dispatch(self, *args, **kwargs):
        return "dispatched"


class FakeRouter:
    def route(self, *args, **kwargs):
        return {"model": "sonnet", "provider": "anthropic"}


class FakeMemoryStore2:
    def __init__(self):
        self.data = {"key1": "value1"}

    async def get(self, key):
        return self.data.get(key)

    async def set(self, key, value):
        self.data[key] = value


class FakeHookEngine:
    async def fire(self, hook_name, *args, **kwargs):
        return "fired"
