"""Tests for harness_core.cost — types + pricing + tracker."""
from __future__ import annotations

import time

import pytest

from harness_core.cost import (
    BillingPeriod,
    CostEntry,
    CostReport,
    CostThresholdAlert,
    CostTracker,
    PricingTable,
)


# --- CostEntry ---------------------------------------------------------


class TestCostEntry:
    def test_create(self):
        e = CostEntry.create(
            operation="llm_call",
            project="polaris",
            user_id="alice",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.0125,
        )
        assert e.cost_usd == 0.0125
        assert e.total_tokens == 1500
        assert e.entry_id

    def test_invalid_negative_tokens(self):
        with pytest.raises(ValueError):
            CostEntry.create(
                operation="x", project="p", input_tokens=-1, cost_usd=0.0,
            )

    def test_invalid_negative_cost(self):
        with pytest.raises(ValueError):
            CostEntry.create(operation="x", project="p", cost_usd=-1.0)

    def test_empty_operation_rejected(self):
        with pytest.raises(ValueError):
            CostEntry.create(operation="", project="p", cost_usd=0.0)

    def test_empty_project_rejected(self):
        with pytest.raises(ValueError):
            CostEntry.create(operation="x", project="", cost_usd=0.0)


class TestBillingPeriod:
    def test_valid(self):
        p = BillingPeriod(start=100.0, end=200.0)
        assert p.duration_seconds == 100.0

    def test_end_before_start_rejected(self):
        with pytest.raises(ValueError):
            BillingPeriod(start=200.0, end=100.0)

    def test_negative_start_rejected(self):
        with pytest.raises(ValueError):
            BillingPeriod(start=-1, end=100.0)

    def test_contains(self):
        p = BillingPeriod(start=100.0, end=200.0)
        assert p.contains(150.0) is True
        assert p.contains(50.0) is False
        assert p.contains(250.0) is False
        # Inclusive at boundaries.
        assert p.contains(100.0) is True
        assert p.contains(200.0) is True

    def test_last_n_seconds(self):
        p = BillingPeriod.last_n_seconds(60, now=1000.0)
        assert p.start == 940.0
        assert p.end == 1000.0


# --- PricingTable ------------------------------------------------------


class TestPricingTable:
    def test_compute_cost_basic(self):
        p = PricingTable(prices={
            "llm_call": {"input_per_M": 3.0, "output_per_M": 15.0},
        })
        cost = p.compute_cost(
            operation="llm_call",
            input_tokens=1_000_000,
            output_tokens=500_000,
        )
        # 1M * $3 + 0.5M * $15 = $3 + $7.5 = $10.5
        assert cost == pytest.approx(10.5)

    def test_compute_cost_unknown_operation_uses_default(self):
        p = PricingTable(
            prices={"llm_call": {"input_per_M": 3.0, "output_per_M": 15.0}},
            default_input_per_M=0.5,
            default_output_per_M=2.0,
        )
        cost = p.compute_cost(
            operation="unknown_op",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        # 1M * $0.5 + 1M * $2 = $2.5
        assert cost == pytest.approx(2.5)

    def test_compute_cost_zero_tokens(self):
        p = PricingTable(prices={"x": {"input_per_M": 1.0, "output_per_M": 1.0}})
        assert p.compute_cost(operation="x", input_tokens=0, output_tokens=0) == 0.0

    def test_compute_cost_negative_tokens_rejected(self):
        p = PricingTable()
        with pytest.raises(ValueError):
            p.compute_cost(operation="x", input_tokens=-1, output_tokens=0)


# --- CostTracker -------------------------------------------------------


class TestCostTrackerRecord:
    def test_record_explicit_cost(self):
        tracker = CostTracker()
        entry = tracker.record(
            operation="llm_call",
            project="polaris",
            user_id="alice",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.025,
        )
        assert entry.cost_usd == 0.025
        assert len(tracker) == 1

    def test_record_computes_cost_from_pricing(self):
        pricing = PricingTable(prices={
            "llm_call": {"input_per_M": 3.0, "output_per_M": 15.0},
        })
        tracker = CostTracker(pricing=pricing)
        entry = tracker.record(
            operation="llm_call",
            project="polaris",
            input_tokens=10_000,
            output_tokens=5_000,
        )
        # 0.01M * $3 + 0.005M * $15 = $0.03 + $0.075 = $0.105
        assert entry.cost_usd == pytest.approx(0.105)

    def test_record_no_pricing_no_explicit_cost_zero(self):
        tracker = CostTracker()
        entry = tracker.record(
            operation="x", project="p", input_tokens=1000, output_tokens=500,
        )
        assert entry.cost_usd == 0.0


class TestCostTrackerAggregation:
    def _populate(self, tracker: CostTracker) -> None:
        # Polaris: alice does 2 LLM calls; bob does 1.
        tracker.record(
            operation="llm_call", project="polaris", user_id="alice",
            cost_usd=0.50, input_tokens=1000, output_tokens=500,
            tags=("research",),
        )
        tracker.record(
            operation="llm_call", project="polaris", user_id="alice",
            cost_usd=0.30, input_tokens=600, output_tokens=300,
            tags=("research",),
        )
        tracker.record(
            operation="llm_call", project="polaris", user_id="bob",
            cost_usd=0.20, input_tokens=400, output_tokens=200,
            tags=("research",),
        )
        # Lyra: alice does 1 retrieval.
        tracker.record(
            operation="retrieval", project="lyra", user_id="alice",
            cost_usd=0.05, input_tokens=200, output_tokens=0,
            tags=("code",),
        )

    def test_total_global(self):
        tracker = CostTracker()
        self._populate(tracker)
        assert tracker.total() == pytest.approx(1.05)

    def test_total_by_project(self):
        tracker = CostTracker()
        self._populate(tracker)
        assert tracker.total(project="polaris") == pytest.approx(1.0)
        assert tracker.total(project="lyra") == pytest.approx(0.05)

    def test_total_by_user(self):
        tracker = CostTracker()
        self._populate(tracker)
        # Alice: 0.50 + 0.30 + 0.05 = 0.85
        assert tracker.total(user_id="alice") == pytest.approx(0.85)
        assert tracker.total(user_id="bob") == pytest.approx(0.20)

    def test_total_by_operation(self):
        tracker = CostTracker()
        self._populate(tracker)
        assert tracker.total(operation="llm_call") == pytest.approx(1.0)
        assert tracker.total(operation="retrieval") == pytest.approx(0.05)

    def test_total_combined_filter(self):
        tracker = CostTracker()
        self._populate(tracker)
        # Polaris + alice = 0.50 + 0.30 = 0.80
        assert tracker.total(project="polaris", user_id="alice") == pytest.approx(0.80)

    def test_total_with_period(self):
        tracker = CostTracker()
        # Inject entries at known timestamps.
        tracker.record(
            operation="x", project="p", cost_usd=1.0, timestamp=100.0,
        )
        tracker.record(
            operation="x", project="p", cost_usd=2.0, timestamp=200.0,
        )
        tracker.record(
            operation="x", project="p", cost_usd=4.0, timestamp=300.0,
        )
        period = BillingPeriod(start=150.0, end=250.0)
        assert tracker.total(period=period) == pytest.approx(2.0)

    def test_total_tokens(self):
        tracker = CostTracker()
        self._populate(tracker)
        # Polaris alice: (1000+500) + (600+300) = 2400
        assert tracker.total_tokens(project="polaris", user_id="alice") == 2400


class TestCostTrackerReport:
    def _populate(self, tracker: CostTracker) -> None:
        tracker.record(
            operation="llm_call", project="polaris", user_id="alice",
            cost_usd=0.50, input_tokens=1000, output_tokens=500,
            tags=("research",),
        )
        tracker.record(
            operation="llm_call", project="polaris", user_id="bob",
            cost_usd=0.30, input_tokens=600, output_tokens=300,
            tags=("research",),
        )
        tracker.record(
            operation="retrieval", project="lyra", user_id="alice",
            cost_usd=0.20, input_tokens=200, output_tokens=0,
            tags=("code",),
        )

    def test_report_by_project(self):
        tracker = CostTracker()
        self._populate(tracker)
        report = tracker.report(group_by="project")
        # Polaris first (highest cost: 0.80).
        assert report.rows[0][0] == "polaris"
        assert report.rows[0][1]["cost_usd"] == pytest.approx(0.80)
        assert report.rows[1][0] == "lyra"
        assert report.grand_total_usd == pytest.approx(1.0)

    def test_report_by_user(self):
        tracker = CostTracker()
        self._populate(tracker)
        report = tracker.report(group_by="user_id")
        # Alice: 0.50 + 0.20 = 0.70; Bob: 0.30
        assert report.rows[0][0] == "alice"
        assert report.rows[0][1]["cost_usd"] == pytest.approx(0.70)

    def test_report_by_operation(self):
        tracker = CostTracker()
        self._populate(tracker)
        report = tracker.report(group_by="operation")
        ops = {r[0] for r in report.rows}
        assert ops == {"llm_call", "retrieval"}

    def test_report_by_tag(self):
        tracker = CostTracker()
        self._populate(tracker)
        report = tracker.report(group_by="tag")
        tags = {r[0] for r in report.rows}
        assert "research" in tags
        assert "code" in tags

    def test_report_by_day(self):
        tracker = CostTracker()
        # Two entries on different UTC days.
        tracker.record(
            operation="x", project="p", cost_usd=1.0, timestamp=86400.0,  # 1970-01-02
        )
        tracker.record(
            operation="x", project="p", cost_usd=2.0, timestamp=172800.0,  # 1970-01-03
        )
        report = tracker.report(group_by="day")
        days = {r[0] for r in report.rows}
        assert "1970-01-02" in days
        assert "1970-01-03" in days

    def test_report_with_period(self):
        tracker = CostTracker()
        tracker.record(operation="x", project="A", cost_usd=1.0, timestamp=100.0)
        tracker.record(operation="x", project="B", cost_usd=2.0, timestamp=300.0)
        period = BillingPeriod(start=200.0, end=400.0)
        report = tracker.report(group_by="project", period=period)
        # Only B falls in the window.
        assert {r[0] for r in report.rows} == {"B"}
        assert report.grand_total_usd == pytest.approx(2.0)

    def test_report_top_n(self):
        tracker = CostTracker()
        for i in range(5):
            tracker.record(
                operation="x", project=f"p{i}", cost_usd=float(i),
            )
        report = tracker.report(group_by="project")
        top2 = report.top_n(n=2)
        assert top2[0][0] == "p4"
        assert top2[1][0] == "p3"

    def test_report_for_key(self):
        tracker = CostTracker()
        tracker.record(operation="x", project="A", cost_usd=1.0)
        report = tracker.report(group_by="project")
        a_row = report.for_key("A")
        assert a_row is not None
        assert a_row["cost_usd"] == pytest.approx(1.0)
        assert report.for_key("missing") is None

    def test_report_invalid_group_by_rejected(self):
        tracker = CostTracker()
        with pytest.raises(ValueError):
            tracker.report(group_by="bogus")

    def test_empty_report(self):
        tracker = CostTracker()
        report = tracker.report(group_by="project")
        assert report.rows == ()
        assert report.grand_total_usd == 0.0


class TestCostTrackerThresholdAlerting:
    def test_no_alert_when_under_threshold(self):
        tracker = CostTracker()
        tracker.record(operation="x", project="p", cost_usd=5.0)
        assert tracker.check_threshold(threshold_usd=10.0) is None

    def test_alert_fires_when_over(self):
        tracker = CostTracker()
        tracker.record(operation="x", project="polaris", cost_usd=15.0)
        alert = tracker.check_threshold(threshold_usd=10.0, project="polaris")
        assert alert is not None
        assert alert.actual_usd == pytest.approx(15.0)
        assert alert.overage_usd == pytest.approx(5.0)
        assert "project=polaris" in alert.scope

    def test_alert_global_scope(self):
        tracker = CostTracker()
        tracker.record(operation="x", project="A", cost_usd=10.0)
        tracker.record(operation="x", project="B", cost_usd=10.0)
        alert = tracker.check_threshold(threshold_usd=15.0)
        assert alert is not None
        assert alert.scope == "global"
        assert alert.actual_usd == pytest.approx(20.0)

    def test_alert_combined_scope(self):
        tracker = CostTracker()
        tracker.record(
            operation="x", project="polaris", user_id="alice", cost_usd=20.0,
        )
        alert = tracker.check_threshold(
            threshold_usd=10.0, project="polaris", user_id="alice",
        )
        assert alert is not None
        assert "project=polaris" in alert.scope
        assert "user=alice" in alert.scope

    def test_alert_negative_threshold_rejected(self):
        tracker = CostTracker()
        with pytest.raises(ValueError):
            tracker.check_threshold(threshold_usd=-1.0)

    def test_alert_with_period(self):
        tracker = CostTracker()
        tracker.record(operation="x", project="p", cost_usd=15.0, timestamp=100.0)
        # Outside period — total in period is 0, no alert.
        period = BillingPeriod(start=200.0, end=300.0)
        assert tracker.check_threshold(threshold_usd=10.0, period=period) is None


# --- End-to-end Polaris-style scenario --------------------------------


class TestPolarisScenario:
    """Realistic spend tracking: Polaris runs multi-user research with per-user
    monthly thresholds + alerting on exceedance."""

    def test_per_user_monthly_alerting(self):
        pricing = PricingTable(prices={
            "llm_call": {"input_per_M": 3.0, "output_per_M": 15.0},
            "embedding": {"input_per_M": 0.13, "output_per_M": 0.0},
            "retrieval": {"input_per_M": 0.0, "output_per_M": 0.0},
        })
        tracker = CostTracker(pricing=pricing)

        # Alice spends ~$5 on LLM calls in 'May 2026'.
        for _ in range(5):
            tracker.record(
                operation="llm_call", project="polaris", user_id="alice",
                input_tokens=100_000, output_tokens=50_000,
                tags=("month-2026-05",),
            )
        # Bob spends ~$1.
        tracker.record(
            operation="llm_call", project="polaris", user_id="bob",
            input_tokens=50_000, output_tokens=20_000,
            tags=("month-2026-05",),
        )
        # Cost-per-user report.
        report = tracker.report(group_by="user_id")
        alice_row = report.for_key("alice")
        bob_row = report.for_key("bob")
        assert alice_row["cost_usd"] > bob_row["cost_usd"]

        # Per-user monthly threshold of $3 — alice triggers, bob doesn't.
        alice_alert = tracker.check_threshold(threshold_usd=3.0, user_id="alice")
        bob_alert = tracker.check_threshold(threshold_usd=3.0, user_id="bob")
        assert alice_alert is not None
        assert bob_alert is None
        assert alice_alert.overage_usd > 0

        # Project total tokens accounting.
        total_tokens = tracker.total_tokens(project="polaris")
        # 5 * 150_000 + 70_000 = 820_000
        assert total_tokens == 820_000
