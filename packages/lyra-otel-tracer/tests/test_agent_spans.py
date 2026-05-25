"""Tests for lyra_otel_tracer.agent_spans."""

from __future__ import annotations

import pytest

from lyra_otel_tracer.agent_spans import AgentSpan, SpanContext, SpanEvent, SpanManager, Trace
from lyra_otel_tracer.exceptions import SpanError


class TestSpanContext:
    def test_span_context_creation(self) -> None:
        ctx = SpanContext(trace_id="trace-1", span_id="span-1")
        assert ctx.trace_id == "trace-1"
        assert ctx.span_id == "span-1"
        assert ctx.parent_span_id == ""

    def test_span_context_with_parent(self) -> None:
        ctx = SpanContext(trace_id="t1", span_id="s1", parent_span_id="s0")
        assert ctx.parent_span_id == "s0"

    def test_span_context_frozen(self) -> None:
        ctx = SpanContext(trace_id="t1", span_id="s1")
        with pytest.raises(AttributeError):
            ctx.trace_id = "changed"  # type: ignore[misc]


class TestSpanEvent:
    def test_span_event_creation(self) -> None:
        event = SpanEvent(name="test_event", timestamp=100.0)
        assert event.name == "test_event"
        assert event.timestamp == 100.0
        assert event.attributes == ()

    def test_span_event_with_attributes(self) -> None:
        attrs = (("key1", "val1"), ("key2", "val2"))
        event = SpanEvent(name="evt", timestamp=200.0, attributes=attrs)
        assert len(event.attributes) == 2

    def test_span_event_frozen(self) -> None:
        event = SpanEvent(name="e", timestamp=1.0)
        with pytest.raises(AttributeError):
            event.name = "changed"  # type: ignore[misc]


class TestAgentSpan:
    def test_agent_span_creation(self) -> None:
        ctx = SpanContext(trace_id="t1", span_id="s1")
        span = AgentSpan(
            context=ctx,
            agent_id="agent-1",
            operation="code_gen",
            start_time=100.0,
        )
        assert span.agent_id == "agent-1"
        assert span.operation == "code_gen"
        assert span.start_time == 100.0
        assert span.end_time == 0.0
        assert span.status == "running"

    def test_agent_span_with_all_fields(self) -> None:
        ctx = SpanContext(trace_id="t1", span_id="s1")
        events = (SpanEvent(name="e1", timestamp=1.0),)
        meta = (("key", "val"),)
        span = AgentSpan(
            context=ctx,
            agent_id="a1",
            operation="op",
            start_time=100.0,
            end_time=200.0,
            status="ok",
            events=events,
            metadata=meta,
        )
        assert span.status == "ok"
        assert len(span.events) == 1
        assert len(span.metadata) == 1

    def test_agent_span_frozen(self) -> None:
        ctx = SpanContext(trace_id="t1", span_id="s1")
        span = AgentSpan(context=ctx, agent_id="a1", operation="op", start_time=0.0)
        with pytest.raises(AttributeError):
            span.agent_id = "changed"  # type: ignore[misc]


class TestTrace:
    def test_trace_creation(self) -> None:
        ctx = SpanContext(trace_id="t1", span_id="s1")
        root = AgentSpan(context=ctx, agent_id="a1", operation="op", start_time=0.0)
        trace = Trace(trace_id="t1", root_span=root)
        assert trace.trace_id == "t1"
        assert trace.root_span.agent_id == "a1"
        assert trace.child_spans == ()
        assert trace.duration_ms == 0.0

    def test_trace_with_children(self) -> None:
        ctx = SpanContext(trace_id="t1", span_id="s1")
        root = AgentSpan(context=ctx, agent_id="a1", operation="op", start_time=0.0, end_time=1.0)
        child_ctx = SpanContext(trace_id="t1", span_id="s2", parent_span_id="s1")
        child = AgentSpan(context=child_ctx, agent_id="a2", operation="sub_op", start_time=0.5, end_time=0.8)
        trace = Trace(trace_id="t1", root_span=root, child_spans=(child,), duration_ms=1000.0)
        assert len(trace.child_spans) == 1
        assert trace.duration_ms == 1000.0

    def test_trace_frozen(self) -> None:
        ctx = SpanContext(trace_id="t1", span_id="s1")
        root = AgentSpan(context=ctx, agent_id="a1", operation="op", start_time=0.0)
        trace = Trace(trace_id="t1", root_span=root)
        with pytest.raises(AttributeError):
            trace.trace_id = "changed"  # type: ignore[misc]


class TestSpanManager:
    @pytest.mark.asyncio
    async def test_start_span(self) -> None:
        mgr = SpanManager()
        span = await mgr.start_span(agent_id="agent-1", operation="code_gen")
        assert span.agent_id == "agent-1"
        assert span.operation == "code_gen"
        assert span.context.span_id != ""
        assert span.context.trace_id != ""
        assert span.status == "running"

    @pytest.mark.asyncio
    async def test_start_span_child(self) -> None:
        mgr = SpanManager()
        parent = await mgr.start_span(agent_id="parent", operation="plan")
        child = await mgr.start_span(
            agent_id="child", operation="execute", parent=parent.context
        )
        assert child.context.parent_span_id == parent.context.span_id
        assert child.context.trace_id == parent.context.trace_id

    @pytest.mark.asyncio
    async def test_end_span(self) -> None:
        mgr = SpanManager()
        span = await mgr.start_span(agent_id="a1", operation="op")
        ended = await mgr.end_span(span, status="ok")
        assert ended.status == "ok"
        assert ended.end_time > 0.0

    @pytest.mark.asyncio
    async def test_end_span_already_ended_raises(self) -> None:
        mgr = SpanManager()
        span = await mgr.start_span(agent_id="a1", operation="op")
        await mgr.end_span(span)
        with pytest.raises(SpanError, match="not running"):
            await mgr.end_span(
                AgentSpan(
                    context=span.context,
                    agent_id=span.agent_id,
                    operation=span.operation,
                    start_time=span.start_time,
                    end_time=span.end_time,
                    status="ok",
                )
            )

    @pytest.mark.asyncio
    async def test_end_span_not_running_raises(self) -> None:
        mgr = SpanManager()
        span = await mgr.start_span(agent_id="a1", operation="op")
        await mgr.end_span(span)
        with pytest.raises(SpanError, match="not running"):
            await mgr.end_span(span)

    @pytest.mark.asyncio
    async def test_add_event(self) -> None:
        mgr = SpanManager()
        span = await mgr.start_span(agent_id="a1", operation="op")
        updated = await mgr.add_event(span, "cache_hit", {"key": "value"})
        assert len(updated.events) == 1
        assert updated.events[0].name == "cache_hit"

    @pytest.mark.asyncio
    async def test_add_event_empty_attributes(self) -> None:
        mgr = SpanManager()
        span = await mgr.start_span(agent_id="a1", operation="op")
        updated = await mgr.add_event(span, "simple_event")
        assert len(updated.events) == 1
        assert updated.events[0].attributes == ()

    @pytest.mark.asyncio
    async def test_add_event_multiple(self) -> None:
        mgr = SpanManager()
        span = await mgr.start_span(agent_id="a1", operation="op")
        span = await mgr.add_event(span, "event1", {"a": "1"})
        span = await mgr.add_event(span, "event2", {"b": "2"})
        assert len(span.events) == 2

    @pytest.mark.asyncio
    async def test_get_trace(self) -> None:
        mgr = SpanManager()
        root = await mgr.start_span(agent_id="root", operation="main")
        child = await mgr.start_span(
            agent_id="child", operation="sub", parent=root.context
        )
        await mgr.end_span(child)
        root = await mgr.end_span(root)
        trace = await mgr.get_trace(root.context.trace_id)
        assert trace.trace_id == root.context.trace_id
        assert trace.root_span.agent_id == "root"

    @pytest.mark.asyncio
    async def test_get_trace_not_found_raises(self) -> None:
        mgr = SpanManager()
        with pytest.raises(SpanError, match="not found"):
            await mgr.get_trace("nonexistent")

    @pytest.mark.asyncio
    async def test_get_active_spans_empty(self) -> None:
        mgr = SpanManager()
        active = await mgr.get_active_spans()
        assert active == ()

    @pytest.mark.asyncio
    async def test_get_active_spans(self) -> None:
        mgr = SpanManager()
        await mgr.start_span(agent_id="a1", operation="op1")
        s2 = await mgr.start_span(agent_id="a2", operation="op2")
        await mgr.end_span(s2)
        active = await mgr.get_active_spans()
        assert len(active) == 1
        assert active[0].agent_id == "a1"

    @pytest.mark.asyncio
    async def test_span_manager_trace_with_duration(self) -> None:
        mgr = SpanManager()
        span = await mgr.start_span(agent_id="a1", operation="op")
        await mgr.end_span(span)
        trace = await mgr.get_trace(span.context.trace_id)
        assert trace.duration_ms > 0.0

    @pytest.mark.asyncio
    async def test_span_id_uniqueness(self) -> None:
        mgr = SpanManager()
        s1 = await mgr.start_span(agent_id="a1", operation="op1")
        s2 = await mgr.start_span(agent_id="a2", operation="op2")
        assert s1.context.span_id != s2.context.span_id

    @pytest.mark.asyncio
    async def test_child_spans_in_trace(self) -> None:
        mgr = SpanManager()
        root = await mgr.start_span(agent_id="root", operation="main")
        c1 = await mgr.start_span(agent_id="c1", operation="sub1", parent=root.context)
        c2 = await mgr.start_span(agent_id="c2", operation="sub2", parent=root.context)
        await mgr.end_span(c1)
        await mgr.end_span(c2)
        root = await mgr.end_span(root)
        trace = await mgr.get_trace(root.context.trace_id)
        assert len(trace.child_spans) >= 2

    @pytest.mark.asyncio
    async def test_span_with_metadata(self) -> None:
        mgr = SpanManager()
        span = await mgr.start_span(agent_id="a1", operation="op")
        updated = AgentSpan(
            context=span.context,
            agent_id=span.agent_id,
            operation=span.operation,
            start_time=span.start_time,
            metadata=(("model", "sonnet"), ("tier", "standard")),
        )
        assert len(updated.metadata) == 2
