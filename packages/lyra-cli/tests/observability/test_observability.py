"""Tests for Phase 5 Observability modules."""

import pytest
import time

from lyra_cli.observability.tracing import (
    SpanKind,
    TracingProvider,
    MetricsProvider,
)
from lyra_cli.observability.aer import (
    ActionType,
    AERSystem,
)
from lyra_cli.observability.monitoring import (
    MonitoringDashboard,
)


# ============================================================================
# Tracing Tests
# ============================================================================

@pytest.fixture
def tracing_provider():
    """Create tracing provider."""
    return TracingProvider()


def test_tracing_start_trace(tracing_provider):
    """Test starting a trace."""
    trace_id = tracing_provider.start_trace("trace_001")

    assert trace_id == "trace_001"
    assert trace_id in tracing_provider.traces
    assert tracing_provider.stats["total_traces"] == 1


def test_tracing_start_span(tracing_provider):
    """Test starting a span."""
    trace_id = tracing_provider.start_trace("trace_001")

    span = tracing_provider.start_span(
        trace_id=trace_id,
        span_id="span_001",
        name="test_operation",
        kind=SpanKind.INTERNAL,
    )

    assert span.span_id == "span_001"
    assert span.name == "test_operation"
    assert tracing_provider.stats["total_spans"] == 1
    assert tracing_provider.stats["active_spans"] == 1


def test_tracing_end_span(tracing_provider):
    """Test ending a span."""
    trace_id = tracing_provider.start_trace("trace_001")
    span = tracing_provider.start_span(
        trace_id=trace_id,
        span_id="span_001",
        name="test_operation",
    )

    time.sleep(0.01)  # Small delay

    tracing_provider.end_span("span_001", status="ok")

    assert span.end_time is not None
    assert span.status == "ok"
    assert span.duration_ms() is not None
    assert span.duration_ms() > 0
    assert tracing_provider.stats["active_spans"] == 0
    assert tracing_provider.stats["completed_spans"] == 1


def test_tracing_nested_spans(tracing_provider):
    """Test nested spans."""
    trace_id = tracing_provider.start_trace("trace_001")

    parent_span = tracing_provider.start_span(
        trace_id=trace_id,
        span_id="parent",
        name="parent_operation",
    )

    child_span = tracing_provider.start_span(
        trace_id=trace_id,
        span_id="child",
        name="child_operation",
        parent_span_id="parent",
    )

    assert child_span.parent_span_id == "parent"
    assert tracing_provider.stats["total_spans"] == 2


def test_tracing_span_events(tracing_provider):
    """Test adding span events."""
    trace_id = tracing_provider.start_trace("trace_001")
    span = tracing_provider.start_span(
        trace_id=trace_id,
        span_id="span_001",
        name="test_operation",
    )

    tracing_provider.add_span_event(
        "span_001",
        "checkpoint_reached",
        {"checkpoint": "validation"}
    )

    assert len(span.events) == 1
    assert span.events[0].name == "checkpoint_reached"


def test_tracing_export_trace(tracing_provider):
    """Test exporting a trace."""
    trace_id = tracing_provider.start_trace("trace_001")
    tracing_provider.start_span(
        trace_id=trace_id,
        span_id="span_001",
        name="test_operation",
    )
    tracing_provider.end_span("span_001")

    exported = tracing_provider.export_trace(trace_id)

    assert exported is not None
    assert exported["trace_id"] == trace_id
    assert len(exported["spans"]) == 1


# ============================================================================
# Metrics Tests
# ============================================================================

@pytest.fixture
def metrics_provider():
    """Create metrics provider."""
    return MetricsProvider()


def test_metrics_counter(metrics_provider):
    """Test counter metrics."""
    metrics_provider.increment_counter("requests", 1.0)
    metrics_provider.increment_counter("requests", 2.0)

    assert metrics_provider.get_counter("requests") == 3.0


def test_metrics_gauge(metrics_provider):
    """Test gauge metrics."""
    metrics_provider.set_gauge("temperature", 25.5)
    metrics_provider.set_gauge("temperature", 26.0)

    assert metrics_provider.get_gauge("temperature") == 26.0


def test_metrics_histogram(metrics_provider):
    """Test histogram metrics."""
    metrics_provider.record_histogram("response_time", 100.0)
    metrics_provider.record_histogram("response_time", 150.0)
    metrics_provider.record_histogram("response_time", 200.0)

    stats = metrics_provider.get_histogram_stats("response_time")

    assert stats is not None
    assert stats["count"] == 3
    assert stats["avg"] == 150.0
    assert stats["min"] == 100.0
    assert stats["max"] == 200.0


def test_metrics_export(metrics_provider):
    """Test exporting metrics."""
    metrics_provider.increment_counter("requests", 5.0)
    metrics_provider.set_gauge("active_users", 10.0)
    metrics_provider.record_histogram("latency", 50.0)

    exported = metrics_provider.export_metrics()

    assert "counters" in exported
    assert "gauges" in exported
    assert "histograms" in exported
    assert exported["counters"]["requests"] == 5.0


# ============================================================================
# AER Tests
# ============================================================================

@pytest.fixture
def aer_system():
    """Create AER system."""
    return AERSystem()


def test_aer_start_execution(aer_system):
    """Test starting execution recording."""
    record_id = aer_system.start_execution(
        agent_id="agent_001",
        session_id="session_001",
        task_description="Test task",
    )

    assert record_id is not None
    assert aer_system.stats["total_records"] == 1


def test_aer_record_action(aer_system):
    """Test recording an action."""
    record_id = aer_system.start_execution(
        agent_id="agent_001",
        session_id="session_001",
        task_description="Test task",
    )

    action_id = aer_system.record_action(
        agent_id="agent_001",
        action_type=ActionType.TOOL_CALL,
        description="Call search tool",
        inputs={"query": "test"},
        outputs={"results": ["result1"]},
    )

    assert action_id is not None
    assert aer_system.stats["total_actions"] == 1


def test_aer_record_decision(aer_system):
    """Test recording a decision."""
    record_id = aer_system.start_execution(
        agent_id="agent_001",
        session_id="session_001",
        task_description="Test task",
    )

    decision_id = aer_system.record_decision(
        agent_id="agent_001",
        question="Which approach to use?",
        options=["approach_a", "approach_b"],
        selected_option="approach_a",
        reasoning="Approach A is more efficient",
        confidence=0.8,
    )

    assert decision_id is not None
    assert aer_system.stats["total_decisions"] == 1


def test_aer_end_execution(aer_system):
    """Test ending execution recording."""
    record_id = aer_system.start_execution(
        agent_id="agent_001",
        session_id="session_001",
        task_description="Test task",
    )

    aer_system.end_execution(
        agent_id="agent_001",
        status="success",
        final_output="Task completed",
    )

    record = aer_system.get_record(record_id)
    assert record.final_status == "success"
    assert record.end_time is not None
    assert aer_system.stats["successful_executions"] == 1


def test_aer_export_record(aer_system):
    """Test exporting a record."""
    record_id = aer_system.start_execution(
        agent_id="agent_001",
        session_id="session_001",
        task_description="Test task",
    )

    aer_system.record_action(
        agent_id="agent_001",
        action_type=ActionType.TOOL_CALL,
        description="Test action",
    )

    aer_system.end_execution("agent_001", "success")

    exported = aer_system.export_record(record_id)

    assert exported is not None
    assert exported["record_id"] == record_id
    assert len(exported["actions"]) == 1


# ============================================================================
# Monitoring Tests
# ============================================================================

@pytest.fixture
def dashboard():
    """Create monitoring dashboard."""
    return MonitoringDashboard()


def test_dashboard_initialization(dashboard):
    """Test dashboard initializes with default metrics."""
    assert "agent.tasks.completed" in dashboard.metrics
    assert "system.active_agents" in dashboard.metrics


def test_dashboard_record_metric(dashboard):
    """Test recording a metric."""
    dashboard.record_metric("agent.tasks.completed", 5.0)

    metric = dashboard.metrics["agent.tasks.completed"]
    assert metric.get_latest() == 5.0


def test_dashboard_update_agent_status(dashboard):
    """Test updating agent status."""
    dashboard.update_agent_status(
        agent_id="agent_001",
        status="active",
        current_task="Processing request",
        tasks_completed=10,
    )

    assert "agent_001" in dashboard.agent_statuses
    assert dashboard.agent_statuses["agent_001"].status == "active"
    assert dashboard.agent_statuses["agent_001"].tasks_completed == 10


def test_dashboard_system_health(dashboard):
    """Test system health calculation."""
    # Add some agent statuses
    dashboard.update_agent_status(
        "agent_001",
        "active",
        tasks_completed=10,
        tasks_failed=2,
    )

    dashboard.update_system_health()

    assert dashboard.system_health.active_agents == 1
    assert dashboard.system_health.total_tasks == 12
    assert dashboard.system_health.success_rate > 0.8


def test_dashboard_get_data(dashboard):
    """Test getting dashboard data."""
    dashboard.update_agent_status("agent_001", "active")
    dashboard.record_metric("agent.tasks.completed", 5.0)

    data = dashboard.get_dashboard_data()

    assert "system_health" in data
    assert "agents" in data
    assert "metrics" in data


def test_dashboard_metric_history(dashboard):
    """Test getting metric history."""
    for i in range(10):
        dashboard.record_metric("agent.tasks.completed", float(i))

    history = dashboard.get_metric_history("agent.tasks.completed", last_n=5)

    assert len(history) == 5
    assert history[-1]["value"] == 9.0


def test_dashboard_agent_summary(dashboard):
    """Test getting agent summary."""
    dashboard.update_agent_status("agent_001", "active")
    dashboard.update_agent_status("agent_002", "idle")
    dashboard.update_agent_status("agent_003", "error")

    summary = dashboard.get_agent_summary()

    assert summary["total_agents"] == 3
    assert summary["active_agents"] == 1
    assert summary["idle_agents"] == 1
    assert summary["error_agents"] == 1
