"""
Tests for the observability dashboard module.
"""

import pytest
from datetime import datetime, timezone

from lyra.observability.dashboard import (
    MetricsDashboard,
    SessionMetrics,
    MetricSnapshot,
)


class TestMetricSnapshot:
    """Tests for MetricSnapshot."""

    def test_now_creates_snapshot(self):
        """now() should create a snapshot with the current timestamp."""
        snap = MetricSnapshot.now(42.0, "test")
        assert snap.value == 42.0
        assert snap.label == "test"
        assert isinstance(snap.timestamp, datetime)
        assert snap.timestamp.tzinfo is not None

    def test_default_label_is_empty(self):
        """A snapshot created directly should default label to empty string."""
        snap = MetricSnapshot(
            timestamp=datetime.now(timezone.utc),
            value=10.0,
        )
        assert snap.label == ""


class TestSessionMetrics:
    """Tests for per-session metrics recording."""

    def test_record_tokens(self):
        """Token recording should increment total and create snapshots."""
        sm = SessionMetrics(session_id="sess-001")
        sm.record_tokens(100)
        sm.record_tokens(200, label="response")
        assert sm.total_tokens == 300
        assert len(sm.token_snapshots) == 2

    def test_record_cost(self):
        """Cost recording should accumulate and create snapshots."""
        sm = SessionMetrics(session_id="sess-cost")
        sm.record_cost(0.015)
        sm.record_cost(0.025)
        assert sm.total_cost == pytest.approx(0.04)
        assert len(sm.cost_snapshots) == 2

    def test_record_latency(self):
        """Latency recording should accumulate and create snapshots."""
        sm = SessionMetrics(session_id="sess-lat")
        sm.record_latency(1.5)
        sm.record_latency(2.5)
        assert sm.total_latency == 4.0
        assert len(sm.latency_snapshots) == 2

    def test_record_tool_call(self):
        """Tool calls should be counted and recorded."""
        sm = SessionMetrics(session_id="sess-tool")
        sm.record_tool_call("read_file")
        sm.record_tool_call("write_file")
        sm.record_tool_call("execute")
        assert sm.tool_calls == 3
        assert len(sm.tool_call_snapshots) == 3
        assert sm.tool_call_snapshots[0].label == "read_file"

    def test_record_error(self):
        """Errors should be counted and recorded."""
        sm = SessionMetrics(session_id="sess-err")
        sm.record_error("timeout")
        sm.record_error("rate_limit")
        assert sm.errors == 2
        assert len(sm.error_snapshots) == 2
        assert sm.error_snapshots[1].label == "rate_limit"

    def test_average_latency(self):
        """average_latency should compute correctly."""
        sm = SessionMetrics(session_id="sess-avg")
        assert sm.average_latency == 0.0
        sm.record_latency(1.0)
        sm.record_latency(3.0)
        sm.record_latency(5.0)
        assert sm.average_latency == 3.0  # (1+3+5)/3

    def test_average_cost_per_token(self):
        """average_cost_per_token should compute correctly."""
        sm = SessionMetrics(session_id="sess-cpt")
        assert sm.average_cost_per_token == 0.0
        sm.record_tokens(1000)
        sm.record_cost(0.02)
        assert sm.average_cost_per_token == pytest.approx(0.00002)

    def test_to_dict(self):
        """to_dict should return a flat dict of key metrics."""
        sm = SessionMetrics(session_id="sess-dict")
        sm.record_tokens(500)
        sm.record_cost(0.01)
        sm.record_latency(2.0)
        sm.record_tool_call("tool1")
        sm.record_error("err1")
        d = sm.to_dict()
        assert d["session_id"] == "sess-dict"
        assert d["total_tokens"] == 500
        assert d["total_cost"] == 0.01
        assert d["tool_calls"] == 1
        assert d["errors"] == 1
        assert "average_latency" in d


class TestMetricsDashboard:
    """Tests for MetricsDashboard session tracking."""

    def test_get_or_create_session(self):
        """get_or_create_session should create if missing."""
        db = MetricsDashboard()
        sm = db.get_or_create_session("sess-new")
        assert sm.session_id == "sess-new"
        # Second call should return the same object
        assert db.get_or_create_session("sess-new") is sm

    def test_get_session_returns_none_for_unknown(self):
        """get_session for an unknown session should return None."""
        db = MetricsDashboard()
        assert db.get_session("ghost") is None

    def test_remove_session(self):
        """remove_session should stop tracking a session."""
        db = MetricsDashboard()
        db.get_or_create_session("sess-remove")
        assert db.remove_session("sess-remove") is True
        assert db.get_session("sess-remove") is None

    def test_remove_nonexistent(self):
        """remove_session for a nonexistent session should return False."""
        db = MetricsDashboard()
        assert db.remove_session("ghost") is False

    def test_record_tokens_via_dashboard(self):
        """Dashboard should delegate token recording to the session."""
        db = MetricsDashboard()
        db.record_tokens("sess-a", 150)
        db.record_tokens("sess-a", 250)
        sm = db.get_session("sess-a")
        assert sm is not None
        assert sm.total_tokens == 400

    def test_record_cost_via_dashboard(self):
        """Dashboard should delegate cost recording to the session."""
        db = MetricsDashboard()
        db.record_cost("sess-b", 0.05)
        db.record_cost("sess-b", 0.03)
        sm = db.get_session("sess-b")
        assert sm is not None
        assert sm.total_cost == pytest.approx(0.08)

    def test_record_latency_via_dashboard(self):
        """Dashboard should delegate latency recording to the session."""
        db = MetricsDashboard()
        db.record_latency("sess-c", 1.0)
        db.record_latency("sess-c", 2.0)
        sm = db.get_session("sess-c")
        assert sm is not None
        assert sm.total_latency == 3.0

    def test_record_tool_call_via_dashboard(self):
        """Dashboard should delegate tool call recording to the session."""
        db = MetricsDashboard()
        db.record_tool_call("sess-d", "deploy")
        sm = db.get_session("sess-d")
        assert sm is not None
        assert sm.tool_calls == 1

    def test_record_error_via_dashboard(self):
        """Dashboard should delegate error recording to the session."""
        db = MetricsDashboard()
        db.record_error("sess-e", "crash")
        sm = db.get_session("sess-e")
        assert sm is not None
        assert sm.errors == 1

    def test_session_count(self):
        """session_count should reflect the number of tracked sessions."""
        db = MetricsDashboard()
        assert db.session_count == 0
        db.get_or_create_session("s1")
        db.get_or_create_session("s2")
        assert db.session_count == 2

    def test_summary_for_specific_session(self):
        """summary with a session_id should return that session's metrics."""
        db = MetricsDashboard()
        db.record_tokens("sess-summary", 100)
        db.record_cost("sess-summary", 0.01)
        summary = db.summary("sess-summary")
        assert summary["total_tokens"] == 100
        assert summary["total_cost"] == 0.01

    def test_summary_for_unknown_session(self):
        """summary for an unknown session should return an error dict."""
        db = MetricsDashboard()
        summary = db.summary("ghost")
        assert "error" in summary

    def test_summary_global(self):
        """summary without a session_id should include global totals."""
        db = MetricsDashboard()
        db.record_tokens("s1", 200)
        db.record_tokens("s2", 300)
        db.record_cost("s1", 0.02)
        db.record_tool_call("s1", "tool_a")
        db.record_error("s2", "err")

        summary = db.summary()
        assert summary["total_sessions"] == 2
        assert summary["global_total_tokens"] == 500
        assert summary["global_total_cost"] == 0.02
        assert summary["global_tool_calls"] == 1
        assert summary["global_errors"] == 1

    def test_top_by_tokens(self):
        """top_by_tokens should return sessions sorted by token usage."""
        db = MetricsDashboard()
        db.record_tokens("large", 1000)
        db.record_tokens("medium", 500)
        db.record_tokens("small", 100)

        top = db.top_by_tokens(2)
        assert len(top) == 2
        assert top[0].session_id == "large"
        assert top[1].session_id == "medium"

    def test_top_by_cost(self):
        """top_by_cost should return sessions sorted by cost."""
        db = MetricsDashboard()
        db.record_cost("expensive", 1.0)
        db.record_cost("cheap", 0.1)
        db.record_cost("medium", 0.5)

        top = db.top_by_cost(2)
        assert top[0].session_id == "expensive"
        assert top[1].session_id == "medium"

    def test_top_by_errors(self):
        """top_by_errors should return sessions sorted by error count."""
        db = MetricsDashboard()
        db.record_error("buggy", "err1")
        db.record_error("buggy", "err2")
        db.record_error("buggy", "err3")
        db.record_error("stable", "err1")

        top = db.top_by_errors(2)
        assert top[0].session_id == "buggy"
        assert top[1].session_id == "stable"
