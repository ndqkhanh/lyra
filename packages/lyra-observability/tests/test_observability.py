"""Tests for lyra_observability package."""

from __future__ import annotations

import json

import pytest
from lyra_observability.dashboard import Dashboard, DashboardPanel
from lyra_observability.logger import LogEntry, LogLevel, StructuredLogger
from lyra_observability.metrics import MetricsCollector, MetricType, MetricValue
from lyra_observability.tracer import Tracer

# ---------------------------------------------------------------------------
# Tracer tests
# ---------------------------------------------------------------------------


class TestTracer:
    @pytest.mark.asyncio
    async def test_trace_context_manager_creates_span(self) -> None:
        tracer = Tracer()
        async with tracer.trace("op1"):
            pass
        recent = tracer.get_recent_spans()
        assert len(recent) == 1
        assert recent[0].name == "op1"

    @pytest.mark.asyncio
    async def test_span_timing_is_set(self) -> None:
        tracer = Tracer()
        async with tracer.trace("timed_op"):
            await asyncio_sleep(0.01)
        span = tracer.get_recent_spans(1)[0]
        assert span.start_time is not None
        assert span.end_time is not None
        assert span.duration is not None
        assert span.duration >= 0.005

    @pytest.mark.asyncio
    async def test_nested_spans_have_parent_child_relation(self) -> None:
        tracer = Tracer()
        child_id: str | None = None
        async with tracer.trace("parent"):
            async with tracer.trace("child") as cid:
                child_id = cid
        spans = tracer.get_recent_spans()
        parent = next(s for s in spans if s.span_id != child_id)
        child = next(s for s in spans if s.span_id == child_id)
        assert child.parent_id == parent.span_id
        assert parent.parent_id is None

    @pytest.mark.asyncio
    async def test_error_capture_in_span(self) -> None:
        tracer = Tracer()
        with pytest.raises(ValueError, match="boom"):
            async with tracer.trace("failing"):
                msg = "boom"
                raise ValueError(msg)
        span = tracer.get_recent_spans(1)[0]
        assert span.error is not None
        assert "boom" in span.error

    @pytest.mark.asyncio
    async def test_trace_tree_structure(self) -> None:
        tracer = Tracer()
        async with tracer.trace("root"):
            async with tracer.trace("child_a"):
                pass
            async with tracer.trace("child_b"):
                pass
        tree = tracer.get_trace_tree()
        assert "root" in tree
        assert len(tree["root"]) == 1
        root_node = tree["root"][0]
        assert root_node["name"] == "root"
        assert len(root_node["children"]) == 2
        assert root_node["children"][0]["name"] == "child_a"
        assert root_node["children"][1]["name"] == "child_b"

    @pytest.mark.asyncio
    async def test_recent_spans_returns_newest_first(self) -> None:
        tracer = Tracer()
        async with tracer.trace("first"):
            pass
        async with tracer.trace("second"):
            pass
        recent = tracer.get_recent_spans(5)
        assert len(recent) == 2
        assert recent[0].name == "second"
        assert recent[1].name == "first"

    @pytest.mark.asyncio
    async def test_recent_spans_limit(self) -> None:
        tracer = Tracer()
        for i in range(10):
            async with tracer.trace(f"op{i}"):
                pass
        recent = tracer.get_recent_spans(3)
        assert len(recent) == 3

    @pytest.mark.asyncio
    async def test_get_stats(self) -> None:
        tracer = Tracer()
        async with tracer.trace("ok"):
            pass
        async with tracer.trace("also_ok"):
            pass
        stats = tracer.get_stats()
        assert stats["total_spans"] == 2
        assert stats["error_count"] == 0
        assert stats["avg_duration"] >= 0

    @pytest.mark.asyncio
    async def test_stats_includes_errors(self) -> None:
        tracer = Tracer()
        async with tracer.trace("good"):
            pass
        with pytest.raises(RuntimeError):
            async with tracer.trace("bad"):
                msg = "fail"
                raise RuntimeError(msg)
        stats = tracer.get_stats()
        assert stats["total_spans"] == 2
        assert stats["error_count"] == 1

    @pytest.mark.asyncio
    async def test_span_metadata_preserved(self) -> None:
        tracer = Tracer()
        async with tracer.trace("meta", metadata={"key": "val", "num": 42}):
            pass
        span = tracer.get_recent_spans(1)[0]
        assert span.metadata["key"] == "val"
        assert span.metadata["num"] == 42

    @pytest.mark.asyncio
    async def test_multiple_root_spans(self) -> None:
        tracer = Tracer()
        async with tracer.trace("root_a"):
            pass
        async with tracer.trace("root_b"):
            pass
        tree = tracer.get_trace_tree()
        assert len(tree["root"]) == 2

    @pytest.mark.asyncio
    async def test_trace_yields_span_id(self) -> None:
        tracer = Tracer()
        async with tracer.trace("yield_test") as sid:
            assert isinstance(sid, str)
            assert len(sid) > 0

    @pytest.mark.asyncio
    async def test_empty_trace_tree(self) -> None:
        tracer = Tracer()
        tree = tracer.get_trace_tree()
        assert tree == {"root": []}


# ---------------------------------------------------------------------------
# MetricsCollector tests
# ---------------------------------------------------------------------------


class TestMetricsCollector:
    def test_counter_increment(self) -> None:
        mc = MetricsCollector()
        mc.counter("requests")
        assert mc.get_counter("requests") == 1.0

    def test_counter_multiple_increments(self) -> None:
        mc = MetricsCollector()
        mc.counter("requests", 5.0)
        mc.counter("requests", 3.0)
        assert mc.get_counter("requests") == 8.0

    def test_counter_default_value_is_one(self) -> None:
        mc = MetricsCollector()
        mc.counter("events")
        assert mc.get_counter("events") == 1.0

    def test_counter_zero_initial(self) -> None:
        mc = MetricsCollector()
        assert mc.get_counter("nonexistent") == 0.0

    def test_gauge_set_and_get(self) -> None:
        mc = MetricsCollector()
        mc.gauge("temperature", 36.5)
        assert mc.get_gauge("temperature") == 36.5

    def test_gauge_overwrite(self) -> None:
        mc = MetricsCollector()
        mc.gauge("cpu", 0.5)
        mc.gauge("cpu", 0.8)
        assert mc.get_gauge("cpu") == 0.8

    def test_gauge_zero_initial(self) -> None:
        mc = MetricsCollector()
        assert mc.get_gauge("nonexistent") == 0.0

    def test_histogram_record(self) -> None:
        mc = MetricsCollector()
        mc.histogram("latency", 0.1)
        stats = mc.get_histogram_stats("latency")
        assert stats["count"] == 1
        assert stats["sum"] == 0.1

    def test_histogram_multiple_values(self) -> None:
        mc = MetricsCollector()
        for v in [1.0, 2.0, 3.0, 4.0, 5.0]:
            mc.histogram("latency", v)
        stats = mc.get_histogram_stats("latency")
        assert stats["count"] == 5
        assert stats["sum"] == 15.0
        assert stats["avg"] == 3.0

    def test_histogram_percentiles(self) -> None:
        mc = MetricsCollector()
        for v in range(1, 101):
            mc.histogram("latency", float(v))
        stats = mc.get_histogram_stats("latency")
        assert stats["p50"] == 50.5
        assert stats["p95"] == 95.05
        assert stats["p99"] == 99.01

    def test_histogram_empty(self) -> None:
        mc = MetricsCollector()
        stats = mc.get_histogram_stats("nonexistent")
        assert stats["count"] == 0
        assert stats["sum"] == 0.0
        assert stats["avg"] == 0.0
        assert stats["p50"] == 0.0

    def test_labeled_counter(self) -> None:
        mc = MetricsCollector()
        mc.counter("api_calls", labels={"endpoint": "/users", "method": "GET"})
        mc.counter("api_calls", labels={"endpoint": "/posts", "method": "GET"})
        assert mc.get_counter("api_calls", labels={"endpoint": "/users", "method": "GET"}) == 1.0
        assert mc.get_counter("api_calls", labels={"endpoint": "/posts", "method": "GET"}) == 1.0
        assert mc.get_counter("api_calls") == 2.0

    def test_labeled_gauge(self) -> None:
        mc = MetricsCollector()
        mc.gauge("memory", 512, labels={"host": "a"})
        mc.gauge("memory", 256, labels={"host": "b"})
        assert mc.get_gauge("memory", labels={"host": "a"}) == 512
        assert mc.get_gauge("memory") == 768

    def test_labeled_histogram(self) -> None:
        mc = MetricsCollector()
        mc.histogram("latency", 10, labels={"route": "/fast"})
        mc.histogram("latency", 100, labels={"route": "/slow"})
        fast_stats = mc.get_histogram_stats("latency", labels={"route": "/fast"})
        assert fast_stats["count"] == 1
        assert fast_stats["sum"] == 10
        combined = mc.get_histogram_stats("latency")
        assert combined["count"] == 2
        assert combined["sum"] == 110

    def test_get_all_metrics(self) -> None:
        mc = MetricsCollector()
        mc.counter("hits")
        mc.gauge("temp", 25.0)
        mc.histogram("dur", 0.5)
        all_m = mc.get_all_metrics()
        assert "hits" in all_m
        assert "temp" in all_m
        assert "dur" in all_m
        assert len(all_m["hits"]) == 1
        assert len(all_m["temp"]) == 1
        assert len(all_m["dur"]) == 1

    def test_get_all_metrics_types(self) -> None:
        mc = MetricsCollector()
        mc.counter("c")
        mc.gauge("g", 1.0)
        mc.histogram("h", 1.0)
        all_m = mc.get_all_metrics()
        assert all_m["c"][0].type == MetricType.COUNTER
        assert all_m["g"][0].type == MetricType.GAUGE
        assert all_m["h"][0].type == MetricType.HISTOGRAM

    def test_metric_value_frozen(self) -> None:
        mv = MetricValue(name="test", type=MetricType.COUNTER, value=1.0)
        with pytest.raises(AttributeError):
            mv.value = 2.0  # type: ignore[misc]

    def test_metric_type_enum(self) -> None:
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.HISTOGRAM.value == "histogram"


# ---------------------------------------------------------------------------
# StructuredLogger tests
# ---------------------------------------------------------------------------


class TestStructuredLogger:
    def test_debug_log(self) -> None:
        logger = StructuredLogger(LogLevel.DEBUG)
        logger.debug("debug message")
        entries = logger.get_recent()
        assert len(entries) == 1
        assert entries[0].level == LogLevel.DEBUG
        assert entries[0].message == "debug message"

    def test_info_log(self) -> None:
        logger = StructuredLogger()
        logger.info("info message")
        entries = logger.get_recent()
        assert len(entries) == 1
        assert entries[0].level == LogLevel.INFO

    def test_warn_log(self) -> None:
        logger = StructuredLogger()
        logger.warn("warn message")
        entries = logger.get_recent()
        assert len(entries) == 1
        assert entries[0].level == LogLevel.WARN

    def test_error_log(self) -> None:
        logger = StructuredLogger()
        logger.error("error message")
        entries = logger.get_recent()
        assert len(entries) == 1
        assert entries[0].level == LogLevel.ERROR

    def test_default_level_is_info(self) -> None:
        logger = StructuredLogger()
        assert logger.level == LogLevel.INFO

    def test_debug_dropped_when_default_level(self) -> None:
        logger = StructuredLogger()
        logger.debug("should be dropped")
        entries = logger.get_recent()
        assert len(entries) == 0

    def test_level_filtering_set_level(self) -> None:
        logger = StructuredLogger(LogLevel.WARN)
        logger.debug("dropped")
        logger.info("dropped")
        logger.warn("kept")
        logger.error("kept")
        entries = logger.get_recent()
        assert len(entries) == 2

    def test_get_recent_limit(self) -> None:
        logger = StructuredLogger(LogLevel.DEBUG)
        for i in range(10):
            logger.info(f"msg {i}")
        recent = logger.get_recent(3)
        assert len(recent) == 3
        assert recent[0].message == "msg 9"

    def test_to_json(self) -> None:
        logger = StructuredLogger()
        logger.info("hello", user="alice")
        logger.warn("caution")
        output = logger.to_json()
        parsed = json.loads(output)
        assert len(parsed) == 2
        assert parsed[0]["level"] == "INFO"
        assert parsed[0]["message"] == "hello"
        assert parsed[0]["context"]["user"] == "alice"
        assert parsed[1]["level"] == "WARN"

    def test_context_injection(self) -> None:
        logger = StructuredLogger(LogLevel.DEBUG)
        logger.info("request", method="GET", path="/api", status=200)
        entry = logger.get_recent(1)[0]
        assert entry.context["method"] == "GET"
        assert entry.context["path"] == "/api"
        assert entry.context["status"] == 200

    def test_log_entry_frozen(self) -> None:
        entry = LogEntry(level=LogLevel.INFO, message="test")
        with pytest.raises(AttributeError):
            entry.message = "changed"  # type: ignore[misc]

    def test_to_json_empty_logger(self) -> None:
        logger = StructuredLogger()
        output = logger.to_json()
        assert output == "[]"


# ---------------------------------------------------------------------------
# Dashboard tests
# ---------------------------------------------------------------------------


class TestDashboard:
    def test_add_panel(self) -> None:
        dash = Dashboard()
        dash.add_panel("Status", "All systems operational")
        snapshot = dash.get_snapshot()
        assert "Status" in snapshot
        assert snapshot["Status"]["content"] == "All systems operational"

    def test_render_empty(self) -> None:
        dash = Dashboard()
        rendered = dash.render()
        assert rendered == "[Dashboard: No panels]"

    def test_render_with_panels(self) -> None:
        dash = Dashboard()
        dash.add_panel("Panel A", "Content A")
        rendered = dash.render()
        assert "LYRA OBSERVABILITY DASHBOARD" in rendered
        assert "Panel A" in rendered
        assert "Content A" in rendered

    def test_get_snapshot(self) -> None:
        dash = Dashboard()
        dash.add_panel("Test", "content")
        snapshot = dash.get_snapshot()
        assert "Test" in snapshot
        assert snapshot["Test"]["title"] == "Test"
        assert snapshot["Test"]["content"] == "content"
        assert isinstance(snapshot["Test"]["updated_at"], float)

    @pytest.mark.asyncio
    async def test_refresh_with_tracer(self) -> None:
        tracer = Tracer()
        async with tracer.trace("test_op"):
            pass
        dash = Dashboard(tracer=tracer)
        await dash.refresh()
        snapshot = dash.get_snapshot()
        assert "Tracer Stats" in snapshot
        assert "Recent Spans" in snapshot
        assert "test_op" in snapshot["Recent Spans"]["content"]

    @pytest.mark.asyncio
    async def test_refresh_with_metrics(self) -> None:
        metrics = MetricsCollector()
        metrics.counter("hits")
        metrics.gauge("cpu", 0.5)
        dash = Dashboard(metrics=metrics)
        await dash.refresh()
        snapshot = dash.get_snapshot()
        assert "Counters" in snapshot
        assert "Gauges" in snapshot

    @pytest.mark.asyncio
    async def test_refresh_integration(self) -> None:
        tracer = Tracer()
        metrics = MetricsCollector()
        async with tracer.trace("work"):
            metrics.counter("ops")
            metrics.gauge("load", 0.7)
            metrics.histogram("latency", 0.042)
        dash = Dashboard(tracer=tracer, metrics=metrics)
        await dash.refresh()
        snapshot = dash.get_snapshot()
        assert "Tracer Stats" in snapshot
        assert "Counters" in snapshot
        assert "Gauges" in snapshot
        assert "Histograms" in snapshot

    def test_multiple_panels(self) -> None:
        dash = Dashboard()
        dash.add_panel("A", "Content A")
        dash.add_panel("B", "Content B")
        assert len(dash.get_snapshot()) == 2

    def test_panel_overwrite(self) -> None:
        dash = Dashboard()
        dash.add_panel("Status", "Old")
        dash.add_panel("Status", "New")
        assert dash.get_snapshot()["Status"]["content"] == "New"

    def test_dashboard_panel_frozen(self) -> None:
        panel = DashboardPanel(title="T", content="C", updated_at=0.0)
        with pytest.raises(AttributeError):
            panel.content = "x"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestIntegration:
    @pytest.mark.asyncio
    async def test_tracer_and_metrics_together(self) -> None:
        tracer = Tracer()
        metrics = MetricsCollector()

        async with tracer.trace("api_call", metadata={"endpoint": "/users"}):
            metrics.counter("api_requests", labels={"endpoint": "/users"})
            metrics.histogram("response_time", 0.15)

        async with tracer.trace("api_call", metadata={"endpoint": "/posts"}):
            metrics.counter("api_requests", labels={"endpoint": "/posts"})
            metrics.histogram("response_time", 0.12)

        stats = tracer.get_stats()
        assert stats["total_spans"] == 2
        assert stats["error_count"] == 0
        assert metrics.get_counter("api_requests") == 2.0

    @pytest.mark.asyncio
    async def test_full_observability_pipeline(self) -> None:
        tracer = Tracer()
        metrics = MetricsCollector()
        logger = StructuredLogger(LogLevel.DEBUG)
        dash = Dashboard(tracer=tracer, metrics=metrics)

        async with tracer.trace("process_order"):
            metrics.counter("orders_processed")
            metrics.histogram("order_value", 99.99)
            logger.info("order processed", order_id="ord-123")

        await dash.refresh()
        snapshot = dash.get_snapshot()

        assert len(tracer.get_recent_spans()) == 1
        assert metrics.get_counter("orders_processed") == 1.0
        assert len(logger.get_recent()) == 1
        assert logger.get_recent()[0].context["order_id"] == "ord-123"
        assert "Counters" in snapshot
        assert "Histograms" in snapshot


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def asyncio_sleep(duration: float) -> None:
    """Async sleep that works with pytest-asyncio.

    Uses an event-loop-friendly busy-wait for very short durations to
    avoid the overhead of actual asyncio.sleep in test contexts.
    """
    import asyncio

    await asyncio.sleep(duration)
