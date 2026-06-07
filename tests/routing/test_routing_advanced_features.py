"""
Tests for v8.1 routing advanced features.

Covers:
- ConfidenceEstimator: length anomaly, refusal patterns, inconsistency
- ConfidenceEstimator: combined scoring
- EscalationDecision: creation and serialization
- CascadeStats: computation and aggregation
- CascadeRouter auto_tune: threshold adjustment from outcome data
- CostDashboard: recording, breakdown, budget alerts, optimization suggestions
"""

from __future__ import annotations

import pytest

from lyra.routing.cascade import (
    CascadeConfig,
    CascadeRouter,
    CascadeStats,
    ConfidenceEstimator,
    EscalationDecision,
    OutcomeStats,
)
from lyra.routing.cost_dashboard import CompletionRecord, CostBreakdown, CostDashboard
from lyra.routing.provider.types import (
    CompletionResponse,
    TokenUsage,
)

from tests.routing.conftest import _MockProvider


# ===========================================================================
# ConfidenceEstimator tests
# ===========================================================================


class TestConfidenceEstimator:
    """Multi-signal confidence detection."""

    @pytest.fixture
    def estimator(self) -> ConfidenceEstimator:
        return ConfidenceEstimator()

    def make_response(self, content: str, output_tokens: int) -> CompletionResponse:
        return CompletionResponse(
            content=content,
            tool_calls=None,
            usage=TokenUsage(input_tokens=10, output_tokens=output_tokens),
            finish_reason="stop",
            model="test-model",
            latency_ms=10.0,
        )

    def test_full_confidence(self, estimator: ConfidenceEstimator):
        """A normal-length response without refusal or inconsistency should get high confidence."""
        resp = self.make_response(
            "The capital of France is Paris. It is a beautiful city.", 20,
        )
        conf = estimator.estimate(resp)
        assert conf > 0.8

    def test_very_short_response_low_confidence(self, estimator: ConfidenceEstimator):
        """A very short response (4 tokens) should get low confidence."""
        resp = self.make_response("Yes", 4)
        conf = estimator.estimate(resp)
        assert conf <= 0.3

    def test_empty_response_zero_confidence(self, estimator: ConfidenceEstimator):
        """An empty response should get zero confidence."""
        resp = self.make_response("", 0)
        conf = estimator.estimate(resp)
        assert conf == 0.0

    def test_refusal_pattern_reduces_confidence(self, estimator: ConfidenceEstimator):
        """Refusal patterns like 'I cannot' should reduce confidence."""
        resp = self.make_response(
            "I cannot help with that request as it goes against my guidelines.", 15,
        )
        conf = estimator.estimate(resp)
        # Length gives 0.5, refusal penalty drops from 1.0 to 0.6, min = 0.5
        assert conf < 1.0

    def test_refusal_pattern_i_am_unable(self, estimator: ConfidenceEstimator):
        """'I am unable' pattern should trigger refusal penalty."""
        resp = self.make_response(
            "I am unable to process this request at this time.", 15,
        )
        conf = estimator.estimate(resp)
        assert conf < 1.0

    def test_refusal_pattern_i_apologize(self, estimator: ConfidenceEstimator):
        """'I apologize' pattern should trigger refusal penalty."""
        resp = self.make_response(
            "I apologize, but I cannot answer that question.", 15,
        )
        conf = estimator.estimate(resp)
        assert conf < 1.0

    def test_inconsistency_pattern_reduces_confidence(self, estimator: ConfidenceEstimator):
        """Hedging patterns like 'on the one hand' should reduce confidence."""
        resp = self.make_response(
            "On the one hand, this approach works. On the other hand, it is slow.", 20,
        )
        conf = estimator.estimate(resp)
        assert conf < 1.0

    def test_both_refusal_and_inconsistency(self, estimator: ConfidenceEstimator):
        """Both refusal and inconsistency signals should give very low confidence."""
        resp = self.make_response(
            "I am not sure. On the one hand X, on the other hand Y.", 15,
        )
        conf = estimator.estimate(resp)
        assert conf < 0.8

    def test_no_usage_tokens_fallback(self, estimator: ConfidenceEstimator):
        """When usage has zero output tokens, fall back to content length."""
        resp = CompletionResponse(
            content="A reasonably long response.",
            tool_calls=None,
            usage=None,  # No usage data — fallback to content length
            finish_reason="stop",
            model="test-model",
            latency_ms=10.0,
        )
        conf = estimator.estimate(resp)
        assert conf > 0.0


# ===========================================================================
# EscalationDecision tests
# ===========================================================================


class TestEscalationDecision:
    """Escalation decision data."""

    def test_creation(self):
        decision = EscalationDecision(
            model_tried="anthropic/claude-sonnet-4-6",
            reason="low_confidence",
            confidence=0.35,
            next_tier="premium",
            next_model="claude-opus-4-6",
            estimated_next_cost=0.05,
        )
        assert decision.model_tried == "anthropic/claude-sonnet-4-6"
        assert decision.reason == "low_confidence"
        assert decision.confidence == 0.35

    def test_to_dict(self):
        decision = EscalationDecision(
            model_tried="test-model",
            reason="failure",
        )
        d = decision.to_dict()
        assert d["model_tried"] == "test-model"
        assert d["reason"] == "failure"
        assert d["confidence"] is None

    def test_default_values(self):
        decision = EscalationDecision(
            model_tried="test-model",
            reason="testing",
        )
        assert decision.confidence is None
        assert decision.next_tier is None
        assert decision.next_model is None
        assert decision.estimated_next_cost == 0.0


# ===========================================================================
# CascadeStats tests
# ===========================================================================


class TestCascadeStats:
    """Aggregate cascade statistics."""

    def test_empty_stats(self):
        stats = CascadeStats()
        assert stats.total_requests == 0
        assert stats.overall_success_rate == 0.0
        assert stats.avg_cost_per_request == 0.0
        assert stats.avg_latency_ms == 0.0

    def test_with_data(self):
        stats = CascadeStats(
            total_requests=100,
            successful_routes=85,
            failed_routes=15,
            total_cost=12.50,
            total_latency_ms=50000.0,
        )
        assert stats.overall_success_rate == 0.85
        assert stats.avg_cost_per_request == 0.125
        assert stats.avg_latency_ms == 500.0

    def test_with_per_model_data(self):
        stats = CascadeStats(
            total_requests=10,
            successful_routes=9,
            per_model={
                "model-a": OutcomeStats(success_count=5, failure_count=0, total_latency_ms=100.0),
                "model-b": OutcomeStats(success_count=4, failure_count=1, total_latency_ms=200.0),
            },
        )
        assert stats.per_model["model-a"].success_rate == 1.0
        assert stats.per_model["model-b"].success_rate == 0.8

    def test_to_dict(self):
        stats = CascadeStats(
            total_requests=10,
            successful_routes=9,
            failed_routes=1,
            total_cost=5.0,
        )
        d = stats.to_dict()
        assert d["total_requests"] == 10
        assert d["overall_success_rate"] == 0.9
        assert "per_model" in d


# ===========================================================================
# CascadeRouter auto_tune tests
# ===========================================================================


class TestCascadeRouterAutoTune:
    """Auto-tuning of confidence thresholds from outcome data."""

    def test_auto_tune_no_data(self):
        """With no outcome data, auto_tune returns empty dict."""
        router = CascadeRouter()
        tuned = router.auto_tune()
        assert tuned == {}

    def test_auto_tune_insufficient_data(self):
        """With fewer than 5 outcomes, no tuning occurs."""
        router = CascadeRouter()
        router.record_outcome("test-model", "standard", success=True, latency=10.0)
        router.record_outcome("test-model", "standard", success=True, latency=10.0)
        router.record_outcome("test-model", "standard", success=False, latency=0.0)
        tuned = router.auto_tune()
        assert tuned == {}

    def test_auto_tune_reliable_model_loosens(self):
        """A model with >= 90% success rate gets a loosened threshold."""
        router = CascadeRouter()
        for _ in range(9):
            router.record_outcome("opus-model", "hard", success=True, latency=100.0)
        router.record_outcome("opus-model", "hard", success=True, latency=100.0)
        tuned = router.auto_tune()
        assert "opus-model" in tuned
        # Should be loosened (lower) from default 0.7
        assert tuned["opus-model"] < 0.7

    def test_auto_tune_unreliable_model_tightens(self):
        """A model with < 50% success rate gets a tightened threshold."""
        router = CascadeRouter()
        for _ in range(3):
            router.record_outcome("flaky-model", "standard", success=False, latency=0.0)
        for _ in range(2):
            router.record_outcome("flaky-model", "standard", success=True, latency=50.0)
        tuned = router.auto_tune()
        assert "flaky-model" in tuned
        # Should be tightened (higher) from default 0.7
        assert tuned["flaky-model"] > 0.7

    def test_get_effective_threshold_default(self):
        """Without auto-tuning, effective threshold is the config default."""
        router = CascadeRouter()
        threshold = router.get_effective_threshold("unknown-model")
        assert threshold == 0.7

    def test_get_effective_threshold_tuned(self):
        """After auto-tuning, effective threshold uses the tuned value."""
        router = CascadeRouter()
        for _ in range(10):
            router.record_outcome("good-model", "standard", success=True, latency=10.0)
        router.auto_tune()
        threshold = router.get_effective_threshold("good-model")
        assert threshold < 0.7


# ===========================================================================
# CostDashboard tests
# ===========================================================================


class TestCostDashboard:
    """Real-time cost tracking, breakdown, alerts, optimization."""

    @pytest.fixture
    def dashboard(self) -> CostDashboard:
        return CostDashboard(budget_limit=10.0)

    def test_record_completion(self, dashboard: CostDashboard):
        """Recording a completion returns a record and adds to list."""
        record = dashboard.record_completion(
            model="claude-sonnet-4-6",
            provider="anthropic",
            task_type="code_review",
            input_tokens=500,
            output_tokens=200,
            input_cost=0.0015,
            output_cost=0.0060,
            latency_ms=1200,
        )
        assert isinstance(record, CompletionRecord)
        assert len(dashboard.records) == 1
        assert record.total_cost == 0.0075
        assert record.total_tokens == 700

    def test_breakdown_aggregation(self, dashboard: CostDashboard):
        """Breakdown correctly aggregates by model and task type."""
        dashboard.record_completion(
            model="sonnet", provider="p1", task_type="code",
            input_tokens=100, output_tokens=50,
            input_cost=0.001, output_cost=0.002,
        )
        dashboard.record_completion(
            model="sonnet", provider="p1", task_type="chat",
            input_tokens=200, output_tokens=100,
            input_cost=0.003, output_cost=0.006,
        )
        dashboard.record_completion(
            model="haiku", provider="p1", task_type="code",
            input_tokens=400, output_tokens=200,
            input_cost=0.004, output_cost=0.008,
        )

        breakdown = dashboard.breakdown()
        # Two sonnet records and one haiku
        assert breakdown.total_cost == pytest.approx(0.024, rel=0.01)
        assert "p1/sonnet" in breakdown.by_model
        assert "p1/haiku" in breakdown.by_model

    def test_breakdown_empty(self, dashboard: CostDashboard):
        """Empty dashboard has zero total cost."""
        breakdown = dashboard.breakdown()
        assert breakdown.total_cost == 0.0
        assert breakdown.by_model == {}
        assert breakdown.by_task_type == {}

    def test_breakdown_by_session(self, dashboard: CostDashboard):
        """Breakdown by session filters correctly."""
        dashboard.record_completion(
            model="m1", provider="p1", task_type="t1",
            input_tokens=10, output_tokens=5,
            input_cost=0.001, output_cost=0.002,
            session_id="session-a",
        )
        dashboard.record_completion(
            model="m1", provider="p1", task_type="t1",
            input_tokens=20, output_tokens=10,
            input_cost=0.002, output_cost=0.004,
            session_id="session-b",
        )
        session_a = dashboard.breakdown_by_session("session-a")
        session_b = dashboard.breakdown_by_session("session-b")

        assert session_a.total_cost == pytest.approx(0.003, rel=0.01)
        assert session_b.total_cost == pytest.approx(0.006, rel=0.01)

    def test_budget_status_ok(self, dashboard: CostDashboard):
        """Budget status returns ok when spend is low."""
        dashboard.record_completion(
            model="m", provider="p", task_type="t",
            input_tokens=10, output_tokens=5,
            input_cost=0.5, output_cost=0.5,
        )
        status = dashboard.budget_status()
        assert status["alert"] == "ok"
        assert status["total_spent"] == 1.0
        assert status["remaining"] == 9.0

    def test_budget_status_warning(self):
        """Budget status returns warning when spend exceeds 80%."""
        dashboard = CostDashboard(budget_limit=10.0)
        dashboard.record_completion(
            model="m", provider="p", task_type="t",
            input_tokens=10, output_tokens=5,
            input_cost=4.5, output_cost=4.5,
        )
        status = dashboard.budget_status()
        assert status["alert"] == "warning"

    def test_budget_status_critical(self):
        """Budget status returns critical when spend exceeds 100%."""
        dashboard = CostDashboard(budget_limit=10.0)
        dashboard.record_completion(
            model="m", provider="p", task_type="t",
            input_tokens=10, output_tokens=5,
            input_cost=6.0, output_cost=6.0,
        )
        status = dashboard.budget_status()
        assert status["alert"] == "critical"
        assert status["remaining"] == 0.0

    def test_budget_alerts_empty_when_ok(self, dashboard: CostDashboard):
        """No alerts when spend is low."""
        alerts = dashboard.budget_alerts()
        assert alerts == []

    def test_budget_alerts_info_at_50_percent(self):
        """Info-level alert at 50% utilisation."""
        dashboard = CostDashboard(budget_limit=10.0)
        dashboard.record_completion(
            model="m", provider="p", task_type="t",
            input_tokens=10, output_tokens=5,
            input_cost=2.5, output_cost=2.5,
        )
        alerts = dashboard.budget_alerts()
        assert len(alerts) >= 1
        assert alerts[0]["level"] in ("info", "warning")

    def test_budget_alerts_warning_at_80_percent(self):
        """Warning-level alert at 80% utilisation."""
        dashboard = CostDashboard(budget_limit=10.0)
        dashboard.record_completion(
            model="m", provider="p", task_type="t",
            input_tokens=10, output_tokens=5,
            input_cost=4.0, output_cost=4.0,
        )
        alerts = dashboard.budget_alerts()
        assert any(a["level"] == "warning" for a in alerts)

    def test_budget_alerts_critical_when_exceeded(self):
        """Critical alert when budget is exceeded."""
        dashboard = CostDashboard(budget_limit=10.0)
        dashboard.record_completion(
            model="m", provider="p", task_type="t",
            input_tokens=10, output_tokens=5,
            input_cost=6.0, output_cost=6.0,
        )
        alerts = dashboard.budget_alerts()
        assert any(a["level"] == "critical" for a in alerts)

    def test_optimization_suggestions_empty(self, dashboard: CostDashboard):
        """No suggestions when no records exist."""
        suggestions = dashboard.optimization_suggestions()
        assert suggestions == []

    def test_optimization_suggestions_expensive_model_simple_task(self, dashboard: CostDashboard):
        """Suggestion to switch from Opus to Sonnet for simple tasks."""
        dashboard.record_completion(
            model="claude-opus-4-6", provider="anthropic", task_type="simple_lookup",
            input_tokens=100, output_tokens=50,
            input_cost=0.5, output_cost=1.0,
        )
        suggestions = dashboard.optimization_suggestions()
        assert len(suggestions) >= 1
        assert any("Opus" in s["message"] or "opus" in s["message"].lower() for s in suggestions)

    def test_optimization_suggestions_dominant_task_type(self, dashboard: CostDashboard):
        """Suggestion for dominant task type."""
        for _ in range(5):
            dashboard.record_completion(
                model="sonnet", provider="p", task_type="simple_lookup",
                input_tokens=10, output_tokens=5,
                input_cost=0.04, output_cost=0.02,
            )
        dashboard.record_completion(
            model="sonnet", provider="p", task_type="rare_task",
            input_tokens=10, output_tokens=5,
            input_cost=0.01, output_cost=0.005,
        )
        suggestions = dashboard.optimization_suggestions()
        assert len(suggestions) >= 1

    def test_summary(self, dashboard: CostDashboard):
        """Summary contains all dashboard state."""
        dashboard.record_completion(
            model="sonnet", provider="p", task_type="code",
            input_tokens=100, output_tokens=50,
            input_cost=0.01, output_cost=0.02,
        )
        summary = dashboard.summary()
        assert "breakdown" in summary
        assert "budget_status" in summary
        assert "budget_alerts" in summary
        assert "optimization_suggestions" in summary
        assert summary["total_completions"] == 1
        assert summary["latest_timestamp"] is not None


class TestCompletionRecord:
    """CompletionRecord properties."""

    def test_total_cost(self):
        record = CompletionRecord(
            model="m", provider="p", task_type="t",
            input_tokens=100, output_tokens=50,
            input_cost=0.001, output_cost=0.002,
        )
        assert record.total_cost == 0.003
        assert record.total_tokens == 150

    def test_session_id_optional(self):
        record = CompletionRecord(
            model="m", provider="p", task_type="t",
            input_tokens=10, output_tokens=5,
            input_cost=0.0, output_cost=0.0,
        )
        assert record.session_id is None


class TestCostBreakdown:
    """CostBreakdown construction and serialization."""

    def test_to_dict(self):
        breakdown = CostBreakdown(
            by_model={"m1": 5.0, "m2": 3.0},
            by_task_type={"code": 4.0, "chat": 4.0},
            total_cost=8.0,
        )
        d = breakdown.to_dict()
        # Sorted by descending cost
        models = list(d["by_model"].keys())
        assert models[0] == "m1"  # 5.0 > 3.0
        assert d["total_cost"] == 8.0
