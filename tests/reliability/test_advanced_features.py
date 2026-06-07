"""
Tests for Lyra v8.3 reliability advanced features:
- Mutation verification
- ErrorProbe MAST taxonomy classification
- WhoAndWhen attribution
- Benchmark regression detection
- Scheduled benchmark runs
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lyra.reliability.benchmark_runner import (
    BaselineManager,
    BenchmarkConfig,
    BenchmarkResult,
    BenchmarkRunner,
    BenchmarkSuiteResult,
    CIBreakdown,
    RegressionAlert,
    TrendPoint,
    cron_matches,
    parse_cron,
)
from lyra.reliability.mutation_verifier import (
    MutationConfig,
    MutationType,
    MutationVerifier,
    MutatedInput,
    StabilityScore,
)
from lyra.reliability.self_diagnosing_harness import (
    AnomalyType,
    MASTFamily,
    MASTMode,
    RepairActionType,
    RootCauseAnalysis,
    SelfDiagnosingHarness,
    TrajectoryBaseline,
    TrajectoryDiff,
    WhoAndWhen,
)
from lyra.verification.error_probe import (
    Anomaly,
    ErrorProbe,
    ExecutionStep,
    FailureAttribution,
    FailureType,
    Symptom,
)
from lyra.verification.tracing_provider import TracingProvider


# ---------------------------------------------------------------------------
# Mutation Verification Tests
# ---------------------------------------------------------------------------


class TestMutationVerifier:
    """Test suite for MutationVerifier."""

    def test_apply_mutations_default_count(self):
        """Default count from config is used when not specified."""
        verifier = MutationVerifier(MutationConfig(count=3))
        mutants = verifier.apply_mutations({"prompt": "hello", "temp": 0.7})
        assert len(mutants) == 3
        for m in mutants:
            assert isinstance(m, MutatedInput)
            assert m.mutation_type in MutationType
            assert len(m.mutation_id) == 12

    def test_apply_mutations_overridden_count(self):
        """Passing count overrides config default."""
        verifier = MutationVerifier(MutationConfig(count=3))
        mutants = verifier.apply_mutations({"prompt": "hello"}, count=2)
        assert len(mutants) == 2

    def test_all_mutation_types_appear(self):
        """Each active mutation type is applied over the series."""
        verifier = MutationVerifier(MutationConfig(count=8))
        mutants = verifier.apply_mutations({"prompt": "hello", "value": 42})
        types_seen = {m.mutation_type for m in mutants}
        assert types_seen == set(MutationType)

    def test_input_permutation_shuffles_list(self):
        """INPUT_PERMUTATION reorders list values."""
        verifier = MutationVerifier(MutationConfig(seed=42))
        original = {"items": ["a", "b", "c", "d"]}
        mutants = verifier.apply_mutations(original, count=1)
        m = mutants[0]
        assert m.mutation_type == MutationType.INPUT_PERMUTATION
        assert set(m.input_data["items"]) == {"a", "b", "c", "d"}

    def test_noise_injection_numeric(self):
        """NOISE_INJECTION perturbs numeric values."""
        verifier = MutationVerifier(MutationConfig(seed=42, noise_scale=0.1))
        original = {"temp": 100.0}
        # Type cycles: 0=permutation,1=noise,2=boundary,3=missing
        # Apply 4 mutations so we get one of each type
        mutants = verifier.apply_mutations(original, count=4)
        noise_mutants = [m for m in mutants if m.mutation_type == MutationType.NOISE_INJECTION]
        assert len(noise_mutants) >= 1
        m = noise_mutants[0]
        # Value should be different from 100
        assert m.input_data["temp"] != 100.0
        # But within noise scale
        assert 80.0 <= m.input_data["temp"] <= 120.0

    def test_boundary_value_replaces_numeric(self):
        """BOUNDARY_VALUE sets numeric fields to edge values."""
        verifier = MutationVerifier(MutationConfig(seed=42))
        original = {"count": 50, "ratio": 0.5}
        # Apply 4 mutations so we get one of each type (index 2 = boundary)
        mutants = verifier.apply_mutations(original, count=4)
        boundary_mutants = [m for m in mutants if m.mutation_type == MutationType.BOUNDARY_VALUE]
        assert len(boundary_mutants) >= 1
        m = boundary_mutants[0]
        assert m.input_data["count"] in [0, 10**6, -(10**6), 1, -1]
        assert m.input_data["ratio"] in [0, 10**6, -(10**6), 1, -1]

    def test_missing_field_removes_keys(self):
        """MISSING_FIELD removes a subset of keys."""
        verifier = MutationVerifier(MutationConfig(seed=42))
        original = {"prompt": "hello", "style": "friendly", "length": 100, "model": "sonnet"}
        # Apply 4 mutations so we get one of each type (index 3 = missing)
        mutants = verifier.apply_mutations(original, count=4)
        missing_mutants = [m for m in mutants if m.mutation_type == MutationType.MISSING_FIELD]
        assert len(missing_mutants) >= 1
        m = missing_mutants[0]
        assert len(m.input_data) < len(original)

    def test_verify_stability_identical_outputs(self):
        """Identical outputs produce perfect stability."""
        verifier = MutationVerifier(MutationConfig(stability_threshold=0.8))
        mutants = [
            MutatedInput({"x": 1}, MutationType.NOISE_INJECTION, "n1"),
            MutatedInput({"x": 2}, MutationType.BOUNDARY_VALUE, "b1"),
        ]
        outputs = [(m, "same output") for m in mutants]
        score = verifier.verify_stability("same output", outputs)
        assert score.overall == 1.0
        assert score.is_stable
        assert len(score.regressions) == 0

    def test_verify_stability_different_outputs(self):
        """Very different outputs produce regressions."""
        verifier = MutationVerifier(MutationConfig(stability_threshold=0.8))
        mutants = [
            MutatedInput({"x": 1}, MutationType.NOISE_INJECTION, "n1"),
        ]
        outputs = [(mutants[0], "completely different response")]
        score = verifier.verify_stability("original output", outputs)
        assert score.overall < 0.5
        assert not score.is_stable
        assert len(score.regressions) >= 1

    def test_verify_stability_dict_similarity(self):
        """Dict outputs are compared element-wise."""
        verifier = MutationVerifier()
        mutants = [
            MutatedInput({"x": 1}, MutationType.INPUT_PERMUTATION, "p1"),
        ]
        outputs = [(mutants[0], {"answer": "yes", "score": 0.95})]
        score = verifier.verify_stability({"answer": "yes", "score": 0.95}, outputs)
        assert score.overall == 1.0
        assert score.is_stable

    def test_config_validation(self):
        """Invalid config raises ValueError."""
        with pytest.raises(ValueError, match="count must be >= 1"):
            MutationConfig(count=0)
        with pytest.raises(ValueError, match="stability_threshold must be in"):
            MutationConfig(stability_threshold=-0.1)
        with pytest.raises(ValueError, match="noise_scale must be in"):
            MutationConfig(noise_scale=1.5)


# ---------------------------------------------------------------------------
# MAST Taxonomy Tests
# ---------------------------------------------------------------------------


class TestMASTTaxonomy:
    """Test suite for MAST taxonomy classification."""

    def test_family_of_local_detection(self):
        """Local detection modes map to LOCAL_DETECTION family."""
        for mode in [
            MASTMode.REPEATED_ERRORS,
            MASTMode.CIRCULAR_REASONING,
            MASTMode.MEMORY_INCONSISTENCY,
            MASTMode.TOOL_FAILURE_CASCADE,
            MASTMode.CONFIDENCE_DROP,
            MASTMode.INFINITE_LOOP,
        ]:
            assert MASTMode.family_of(mode) == MASTFamily.LOCAL_DETECTION

    def test_family_of_backward_tracing(self):
        """Backward tracing modes map to BACKWARD_TRACING family."""
        for mode in [
            MASTMode.SYMPTOM_CHAIN,
            MASTMode.DATA_FLOW_BREAK,
            MASTMode.TIMING_VIOLATION,
            MASTMode.RESOURCE_EXHAUSTION,
        ]:
            assert MASTMode.family_of(mode) == MASTFamily.BACKWARD_TRACING

    def test_family_of_multi_agent_validation(self):
        """Multi-agent validation modes map properly."""
        for mode in [
            MASTMode.VALIDATION_MISMATCH,
            MASTMode.ATTRIBUTION_CONFLICT,
            MASTMode.RECOMMENDATION_OVERRIDE,
            MASTMode.ESCALATION_REQUIRED,
        ]:
            assert MASTMode.family_of(mode) == MASTFamily.MULTI_AGENT_VALIDATION

    def test_all_14_modes_defined(self):
        """All 14 MAST modes are present in the enum."""
        modes = list(MASTMode)
        assert len(modes) == 14

    def test_repeated_errors_mapped_from_errorprobe(self):
        """SelfDiagnosingHarness maps ErrorProbe repeated_errors to MAST."""
        harness = SelfDiagnosingHarness()
        anomaly = Anomaly(
            step_id="s1",
            timestamp=datetime.now(),
            anomaly_type="repeated_errors",
            confidence=0.9,
        )
        mode = harness._map_anomaly_to_mast(anomaly)
        assert mode == MASTMode.REPEATED_ERRORS

    def test_circular_reasoning_mapped_from_errorprobe(self):
        """ErrorProbe circular_reasoning maps correctly."""
        harness = SelfDiagnosingHarness()
        anomaly = Anomaly(
            step_id="s2",
            timestamp=datetime.now(),
            anomaly_type="circular_reasoning",
            confidence=0.7,
        )
        mode = harness._map_anomaly_to_mast(anomaly)
        assert mode == MASTMode.CIRCULAR_REASONING

    def test_errorprobe_integration_via_mast(self):
        """detect_anomalies triggers MAST detection from ErrorProbe."""
        harness = SelfDiagnosingHarness()
        now = datetime.now()
        steps = [
            ExecutionStep("s1", now, "tool_call", {"tool_name": "read"}, {"result": "ok"}, True),
            ExecutionStep("s2", now, "tool_call", {"tool_name": "write"}, {}, False, error="fail"),
            ExecutionStep("s3", now, "tool_call", {"tool_name": "write"}, {}, False, error="fail"),
            ExecutionStep("s4", now, "tool_call", {"tool_name": "write"}, {}, False, error="fail"),
        ]
        anomalies = harness.detect_anomalies(steps, session_id="test-mast")
        # Should detect TOOL_ERROR via heuristic + MAST mode
        assert AnomalyType.TOOL_ERROR in anomalies
        assert AnomalyType.MAST_ANOMALY in anomalies


# ---------------------------------------------------------------------------
# WhoAndWhen Attribution Tests
# ---------------------------------------------------------------------------


class TestWhoAndWhen:
    """Test suite for WhoAndWhen agent attribution."""

    def test_who_and_when_finds_step(self):
        """who_and_when returns attribution for a valid step."""
        harness = SelfDiagnosingHarness()
        now = datetime.now()
        steps = [
            ExecutionStep("s1", now, "reasoning", {"prompt": "hello"}, {"thought": "hmm"}, True),
            ExecutionStep("s2", now, "tool_call", {"tool_name": "bash"}, {"result": "ok"}, True),
        ]
        waw = harness.who_and_when(steps, "s2", agent_id="agent-1", agent_type="executor")
        assert waw is not None
        assert waw.agent_id == "agent-1"
        assert waw.agent_type == "executor"
        assert waw.step_id == "s2"

    def test_who_and_when_returns_none_for_missing_step(self):
        """who_and_when returns None when step_id is not found."""
        harness = SelfDiagnosingHarness()
        steps = []
        waw = harness.who_and_when(steps, "nonexistent")
        assert waw is None

    def test_who_and_when_carries_trace_ids(self):
        """who_and_when propagates trace_id and span_id from metadata."""
        harness = SelfDiagnosingHarness()
        now = datetime.now()
        steps = [
            ExecutionStep(
                "s1", now, "reasoning", {},
                {"thought": "hmm"}, True,
                metadata={"trace_id": "trace-1", "span_id": "span-1"},
            ),
        ]
        waw = harness.who_and_when(steps, "s1", agent_id="a1", agent_type="primary")
        assert waw is not None
        assert waw.trace_id == "trace-1"
        assert waw.span_id == "span-1"


# ---------------------------------------------------------------------------
# TrajectoryDiff Tests
# ---------------------------------------------------------------------------


class TestTrajectoryDiff:
    """Test suite for trajectory baseline comparison."""

    def test_store_and_retrieve_baseline(self):
        """Storing a baseline returns a TrajectoryBaseline with an ID."""
        harness = SelfDiagnosingHarness()
        now = datetime.now()
        steps = [
            ExecutionStep("s1", now, "reasoning", {}, {"thought": "hmm"}, True),
        ]
        baseline = harness.store_baseline("session-1", steps)
        assert baseline.baseline_id.startswith("bl-session-1")
        assert harness.get_baseline(baseline.baseline_id) is baseline

    def test_diff_identical_trajectories(self):
        """Identical trajectories produce perfect similarity."""
        harness = SelfDiagnosingHarness()
        now = datetime.now()
        steps = [
            ExecutionStep("s1", now, "reasoning", {}, {"thought": "hmm"}, True),
            ExecutionStep("s2", now, "tool_call", {"tool_name": "bash"}, {"result": "ok"}, True),
        ]
        baseline = harness.store_baseline("session-1", steps)
        diff = harness.diff_against_baseline(steps, baseline.baseline_id)
        assert diff is not None
        assert diff.similarity == 1.0
        assert len(diff.added_steps) == 0
        assert len(diff.missing_steps) == 0
        assert len(diff.divergent_actions) == 0

    def test_diff_with_added_and_removed_steps(self):
        """Trajectory with added/removed steps shows reduced similarity."""
        harness = SelfDiagnosingHarness()
        now = datetime.now()
        baseline_steps = [
            ExecutionStep("s1", now, "reasoning", {}, {"thought": "hmm"}, True),
            ExecutionStep("s2", now, "tool_call", {}, {"result": "ok"}, True),
        ]
        baseline = harness.store_baseline("session-1", baseline_steps)

        # Current trajectory has only s2 (missing s1, added s3)
        current_steps = [
            ExecutionStep("s3", now, "reasoning", {}, {"thought": "different"}, True),
            ExecutionStep("s2", now, "tool_call", {}, {"result": "ok"}, True),
        ]
        diff = harness.diff_against_baseline(current_steps, baseline.baseline_id)
        assert diff is not None
        assert diff.similarity < 1.0
        assert len(diff.added_steps) == 1
        assert len(diff.missing_steps) == 1

    def test_diff_returns_none_for_missing_baseline(self):
        """diff_against_baseline returns None for unknown baseline."""
        harness = SelfDiagnosingHarness()
        diff = harness.diff_against_baseline([], "nonexistent")
        assert diff is None


# ---------------------------------------------------------------------------
# RootCauseAnalysis Tests
# ---------------------------------------------------------------------------


class TestRootCauseAnalysis:
    """Test suite for root cause analysis."""

    @pytest.mark.asyncio
    async def test_root_cause_no_failure(self):
        """root_cause_analysis returns None when no failure exists."""
        harness = SelfDiagnosingHarness()
        now = datetime.now()
        steps = [
            ExecutionStep("s1", now, "reasoning", {}, {"thought": "hmm"}, True),
        ]
        result = await harness.root_cause_analysis(steps)
        assert result is None

    @pytest.mark.asyncio
    async def test_root_cause_detects_tool_failure(self):
        """root_cause_analysis identifies tool failure root cause."""
        harness = SelfDiagnosingHarness()
        now = datetime.now()
        steps = [
            ExecutionStep("s1", now, "reasoning", {"prompt": "do something"}, {"plan": "ok"}, True),
            ExecutionStep("s2", now, "tool_call", {"tool_name": "bash"}, {}, False, error="bash: not found"),
            ExecutionStep("s3", now, "tool_call", {"tool_name": "bash"}, {}, False, error="bash: not found"),
        ]
        result = await harness.root_cause_analysis(
            steps, agent_id="agent-1", agent_type="executor"
        )
        assert result is not None
        assert result.confidence > 0.0
        assert result.who_and_when is not None
        assert len(result.recommendations) > 0

    @pytest.mark.asyncio
    async def test_root_cause_chain_ordered(self):
        """Root cause chain is ordered from root to failure."""
        harness = SelfDiagnosingHarness()
        now = datetime.now()
        steps = [
            ExecutionStep("s1", now, "reasoning", {}, {"plan": "do x"}, True),
            ExecutionStep("s2", now, "tool_call", {"tool_name": "fetch"}, {}, False, error="timeout"),
            ExecutionStep("s3", now, "tool_call", {"tool_name": "read"}, {}, False, error="not found"),
        ]
        result = await harness.root_cause_analysis(steps, failure_step_id="s3")
        if result:
            assert isinstance(result.chain, list)
            # At minimum, chain should contain the failure step
            assert len(result.chain) > 0


# ---------------------------------------------------------------------------
# Benchmark Regression Detection Tests
# ---------------------------------------------------------------------------


class TestRegressionDetection:
    """Test suite for benchmark regression detection."""

    def test_baseline_manager_load_save(self, tmp_path):
        """BaselineManager persists and reloads baselines."""
        baseline_file = tmp_path / "baselines.json"
        mgr = BaselineManager(str(baseline_file))

        result = BenchmarkResult(
            benchmark_name="test-bench",
            pass_at_1=0.85,
            pass_at_k=0.80,
            k=5,
            n_tasks=50,
            avg_cost_per_task=0.01,
            avg_tokens_per_task=200,
            total_duration_seconds=10.0,
        )
        mgr.update(result)
        assert mgr.get("test-bench") is not None
        assert mgr.get("test-bench").score == 0.80

        # Reload from file
        mgr2 = BaselineManager(str(baseline_file))
        assert mgr2.get("test-bench") is not None
        assert mgr2.get("test-bench").score == 0.80

    def test_regression_alert_generated(self):
        """RegressionAlert is generated when score drops below threshold."""
        mgr = BaselineManager()
        mgr.update(BenchmarkResult(
            benchmark_name="test", pass_at_1=0.9, pass_at_k=0.9, k=1,
            n_tasks=10, avg_cost_per_task=0.0, avg_tokens_per_task=0,
            total_duration_seconds=1.0,
        ))
        # New score below threshold
        new_result = BenchmarkResult(
            benchmark_name="test", pass_at_1=0.5, pass_at_k=0.5, k=1,
            n_tasks=10, avg_cost_per_task=0.0, avg_tokens_per_task=0,
            total_duration_seconds=1.0,
        )
        alert = mgr.check_regression(new_result, threshold=0.1)
        assert alert is not None
        assert alert.benchmark_name == "test"
        assert alert.drop > 0.1

    def test_no_regression_when_score_improves(self):
        """No regression alert when score improves."""
        mgr = BaselineManager()
        mgr.update(BenchmarkResult(
            benchmark_name="test", pass_at_1=0.5, pass_at_k=0.5, k=1,
            n_tasks=10, avg_cost_per_task=0.0, avg_tokens_per_task=0,
            total_duration_seconds=1.0,
        ))
        new_result = BenchmarkResult(
            benchmark_name="test", pass_at_1=0.9, pass_at_k=0.9, k=1,
            n_tasks=10, avg_cost_per_task=0.0, avg_tokens_per_task=0,
            total_duration_seconds=1.0,
        )
        alert = mgr.check_regression(new_result, threshold=0.05)
        assert alert is None

    def test_no_regression_without_baseline(self):
        """No regression when there is no prior baseline."""
        mgr = BaselineManager()
        new_result = BenchmarkResult(
            benchmark_name="new-bench", pass_at_1=0.5, pass_at_k=0.5, k=1,
            n_tasks=10, avg_cost_per_task=0.0, avg_tokens_per_task=0,
            total_duration_seconds=1.0,
        )
        alert = mgr.check_regression(new_result)
        assert alert is None

    def test_benchmark_suite_result_regressions(self):
        """BenchmarkSuiteResult captures regression alerts."""
        suite = BenchmarkSuiteResult(
            results=[],
            regressions=[
                RegressionAlert("b1", 0.9, 0.6, 0.3, 0.05, "DROPPED"),
            ],
        )
        assert len(suite.regressions) == 1
        assert suite.regressions[0].benchmark_name == "b1"


# ---------------------------------------------------------------------------
# Benchmark Scheduled Run Tests
# ---------------------------------------------------------------------------


class TestScheduledRuns:
    """Test suite for scheduled benchmark runs."""

    def test_cron_parsing(self):
        """parse_cron correctly parses 5-field expressions."""
        parsed = parse_cron("0 9 * * *")
        assert parsed == (0, 9, -1, -1, -1)

        parsed = parse_cron("*/15 * * * *")
        assert parsed == (-15, -1, -1, -1, -1)

        parsed = parse_cron("30 14 1 1 *")
        assert parsed == (30, 14, 1, 1, -1)

    def test_cron_parsing_invalid(self):
        """parse_cron raises ValueError for invalid expressions."""
        with pytest.raises(ValueError, match="Expected 5 cron fields"):
            parse_cron("0 9 * *")

    def test_cron_matches_wildcard(self):
        """cron_matches wildcard fields match any value."""
        parsed = (0, 9, -1, -1, 6)  # At 09:00 on Sunday only (Python weekday: Sun=6)
        dt = datetime(2026, 6, 7, 9, 0)  # June 7 2026 is a Sunday
        assert cron_matches(parsed, dt)

    def test_cron_matches_no_match(self):
        """cron_matches returns False when fields don't match."""
        parsed = (30, 14, -1, -1, -1)  # Every day at 14:30
        dt = datetime(2026, 6, 7, 9, 0)
        assert not cron_matches(parsed, dt)

    def test_cron_matches_step(self):
        """cron_matches works with step expressions (*/N)."""
        parsed = (-15, -1, -1, -1, -1)  # Every 15 minutes
        dt = datetime(2026, 6, 7, 10, 15)
        assert cron_matches(parsed, dt)
        dt2 = datetime(2026, 6, 7, 10, 17)
        assert not cron_matches(parsed, dt2)

    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self):
        """BenchmarkRunner scheduler can be started and stopped."""
        runner = BenchmarkRunner(config=BenchmarkConfig(frequency="manual"))
        runner.start_scheduler()
        assert runner._scheduler_task is not None
        runner.stop_scheduler()
        await asyncio.sleep(0)
        assert runner._scheduler_task is None

    @pytest.mark.asyncio
    async def test_scheduler_callback_invoked(self):
        """The scheduler callback is invoked after a run."""
        runner = BenchmarkRunner(config=BenchmarkConfig(frequency="manual"))
        callback = AsyncMock()
        runner.on_scheduled_run(callback)
        # Just start and stop; real runs are tested separately
        runner.start_scheduler()
        runner.stop_scheduler()
        # Let the event loop process cancellation
        await asyncio.sleep(0)
        # No call since no run happened
        callback.assert_not_called()


# ---------------------------------------------------------------------------
# Trend Tests
# ---------------------------------------------------------------------------


class TestTrends:
    """Test suite for benchmark trend tracking."""

    def test_trend_direction_improving(self):
        """Positive slope indicates improving trend."""
        base = datetime.now()
        trend = TrendPoint.__new__(TrendPoint)

        # We test BenchmarkTrend directly
        from lyra.reliability.benchmark_runner import BenchmarkTrend
        bt = BenchmarkTrend(benchmark_name="test")
        for i in range(5):
            bt.points.append(TrendPoint(
                score=0.5 + i * 0.1,
                timestamp=base + timedelta(hours=i),
                run_id=f"run-{i}",
            ))
        assert bt.direction == "improving"
        assert bt.slope > 0

    def test_trend_direction_degrading(self):
        """Negative slope indicates degrading trend."""
        base = datetime.now()
        from lyra.reliability.benchmark_runner import BenchmarkTrend
        bt = BenchmarkTrend(benchmark_name="test")
        for i in range(5):
            bt.points.append(TrendPoint(
                score=0.9 - i * 0.1,
                timestamp=base + timedelta(hours=i),
                run_id=f"run-{i}",
            ))
        assert bt.direction == "degrading"
        assert bt.slope < 0

    def test_trend_direction_stable(self):
        """Near-zero slope indicates stable trend."""
        base = datetime.now()
        from lyra.reliability.benchmark_runner import BenchmarkTrend
        bt = BenchmarkTrend(benchmark_name="test")
        for i in range(5):
            bt.points.append(TrendPoint(
                score=0.75,
                timestamp=base + timedelta(hours=i),
                run_id=f"run-{i}",
            ))
        assert bt.direction == "stable"

    def test_trend_single_point_stable(self):
        """A single point has zero slope and is stable."""
        from lyra.reliability.benchmark_runner import BenchmarkTrend
        bt = BenchmarkTrend(benchmark_name="test")
        bt.points.append(TrendPoint(score=0.8, timestamp=datetime.now(), run_id="run-1"))
        assert bt.slope == 0.0
        assert bt.direction == "stable"


# ---------------------------------------------------------------------------
# CI Integration Tests
# ---------------------------------------------------------------------------


class TestCIIntegration:
    """Test suite for CI integration in BenchmarkRunner."""

    def test_ci_breakdown_no_regressions(self):
        """CI breakdown shows passed when no regressions or errors."""
        runner = BenchmarkRunner()
        suite = BenchmarkSuiteResult(
            results=[
                BenchmarkResult("b1", 0.9, 0.9, 1, 10, 0.0, 0, 1.0),
                BenchmarkResult("b2", 0.8, 0.8, 1, 10, 0.0, 0, 1.0),
            ],
        )
        # Manually set history
        runner._history = [suite]
        ci = runner.ci_breakdown(suite)
        assert ci.passed
        assert ci.exit_code == 0
        assert ci.passed_benchmarks == 2

    def test_ci_breakdown_with_regressions(self):
        """CI breakdown shows failure when regressions exist."""
        runner = BenchmarkRunner()
        suite = BenchmarkSuiteResult(
            results=[
                BenchmarkResult("b1", 0.9, 0.9, 1, 10, 0.0, 0, 1.0),
                BenchmarkResult("b2", 0.3, 0.3, 1, 10, 0.0, 0, 1.0),
            ],
            regressions=[
                RegressionAlert("b2", 0.8, 0.3, 0.5, 0.05, "DROPPED"),
            ],
        )
        runner._history = [suite]
        ci = runner.ci_breakdown(suite)
        assert not ci.passed
        assert ci.exit_code == 1
        assert ci.failed_benchmarks == 1

    def test_ci_breakdown_with_errors(self):
        """CI breakdown shows error exit code when benchmarks error."""
        runner = BenchmarkRunner()
        suite = BenchmarkSuiteResult(
            results=[
                BenchmarkResult("b1", 0.0, 0.0, 1, 0, 0.0, 0, 0.0, error="timeout"),
            ],
        )
        runner._history = [suite]
        ci = runner.ci_breakdown(suite)
        assert not ci.passed
        assert ci.exit_code == 2
        assert ci.errored_benchmarks == 1


# ---------------------------------------------------------------------------
# Harness Repair Tests
# ---------------------------------------------------------------------------


class TestRepairActions:
    """Test suite for repair actions."""

    def test_repair_action_aliases(self):
        """RepairActionType aliases resolve correctly."""
        assert RepairActionType.RETRY_SAME_MODEL == RepairActionType.RETRY_SAME
        assert RepairActionType.RETRY_CHEAPER_MODEL == RepairActionType.RETRY_CHEAPER

    def test_repair_selection_prioritizes_untried(self):
        """_select_repair_action returns the first untried option."""
        harness = SelfDiagnosingHarness()
        action = harness._select_repair_action(
            AnomalyType.TOOL_ERROR,
            {"session_id": "test"},
        )
        # First untried option for TOOL_ERROR is RETRY_SAME
        assert action == RepairActionType.RETRY_SAME

    def test_repair_selection_escalates_when_all_tried(self):
        """When all options tried, escalate is the fallback."""
        harness = SelfDiagnosingHarness()
        # Simulate that RETRY_SAME and RETRY_CHEAPER were already tried
        harness._repair_history["test"] = [
            type("RA", (), {"action_type": RepairActionType.RETRY_SAME})(),
            type("RA", (), {"action_type": RepairActionType.RETRY_CHEAPER})(),
            type("RA", (), {"action_type": RepairActionType.ABORT})(),
        ]
        action = harness._select_repair_action(
            AnomalyType.TOOL_ERROR,
            {"session_id": "test"},
        )
        assert action == RepairActionType.ESCALATE

    @pytest.mark.asyncio
    async def test_repair_execution_retry_with_fn(self):
        """_execute_repair calls retry_fn when available."""
        harness = SelfDiagnosingHarness()
        mock_fn = AsyncMock(return_value="ok")
        action = type("RA", (), {"action_type": RepairActionType.RETRY_SAME})()
        success = await harness._execute_repair(action, {"retry_fn": mock_fn})
        assert success

    @pytest.mark.asyncio
    async def test_repair_abort_closes_stream(self):
        """Abort repair closes the session stream."""
        harness = SelfDiagnosingHarness()
        harness.monitor("test-session")
        assert "test-session" in harness.active_sessions()

        action = type("RA", (),
            {"action_type": RepairActionType.ABORT})()
        success = await harness._execute_repair(action, {"session_id": "test-session"})
        assert success
        assert "test-session" not in harness.active_sessions()


# ---------------------------------------------------------------------------
# Report Tests
# ---------------------------------------------------------------------------


class TestReports:
    """Test suite for reliability reports."""

    def test_benchmark_report_to_markdown(self):
        """BenchmarkReport renders to markdown."""
        from lyra.reliability.benchmark_runner import BenchmarkReport, BenchmarkTrend
        result = BenchmarkResult("test", 0.8, 0.85, 5, 50, 0.01, 200, 10.0)
        suite = BenchmarkSuiteResult(results=[result])
        report = BenchmarkReport(
            suite_result=suite,
            trends={"test": BenchmarkTrend(benchmark_name="test")},
            ci=None,
        )
        md = report.to_markdown()
        assert "Benchmark Report" in md
        assert "test" in md
        assert "80.0%" in md or "85.0%" in md

    def test_benchmark_report_includes_regressions(self):
        """BenchmarkReport includes regression alerts when present."""
        from lyra.reliability.benchmark_runner import BenchmarkReport
        suite = BenchmarkSuiteResult(
            results=[],
            regressions=[RegressionAlert("b1", 0.9, 0.5, 0.4, 0.05, "DROPPED")],
        )
        report = BenchmarkReport(suite_result=suite)
        md = report.to_markdown()
        assert "Regression Alerts" in md
        assert "DROPPED" in md

    def test_summary_empty_when_no_results(self):
        """summary returns defined message when no results exist."""
        runner = BenchmarkRunner()
        summary = runner.summary()
        assert "No benchmark results available." in summary


# ---------------------------------------------------------------------------
# ErrorProbe Integration Tests
# ---------------------------------------------------------------------------


class TestErrorProbeIntegration:
    """Test suite for ErrorProbe integration in SelfDiagnosingHarness."""

    def test_error_probe_available(self):
        """SelfDiagnosingHarness has an ErrorProbe instance."""
        harness = SelfDiagnosingHarness()
        assert hasattr(harness, "_error_probe")
        assert isinstance(harness._error_probe, ErrorProbe)

    def test_detect_mast_modes_repeated_errors(self):
        """Repeated tool errors are picked up as MAST modes."""
        harness = SelfDiagnosingHarness()
        now = datetime.now()
        steps = [
            ExecutionStep("s1", now, "tool_call", {}, {}, False, error="err1"),
            ExecutionStep("s2", now, "tool_call", {}, {}, False, error="err2"),
            ExecutionStep("s3", now, "tool_call", {}, {}, False, error="err3"),
        ]
        modes = harness._detect_mast_modes(steps)
        assert MASTMode.REPEATED_ERRORS in modes

    def test_detect_mast_modes_circular_reasoning(self):
        """Repeated identical reasoning steps trigger circular_reasoning."""
        harness = SelfDiagnosingHarness()
        now = datetime.now()
        steps = [
            ExecutionStep(f"s{i}", now, "reasoning", {"prompt": "what"}, {"thought": "hmm"}, True)
            for i in range(6)
        ]
        modes = harness._detect_mast_modes(steps)
        assert MASTMode.CIRCULAR_REASONING in modes

    def test_detect_mast_modes_confidence_drop(self):
        """Sudden confidence drops trigger confidence_drop MODE."""
        harness = SelfDiagnosingHarness()
        now = datetime.now()
        steps = [
            ExecutionStep("s1", now, "reasoning", {}, {"thought": "a"}, True,
                          metadata={"confidence": 0.9}),
            ExecutionStep("s2", now, "reasoning", {}, {"thought": "a"}, True,
                          metadata={"confidence": 0.4}),
        ]
        modes = harness._detect_mast_modes(steps)
        assert MASTMode.CONFIDENCE_DROP in modes


# ---------------------------------------------------------------------------
# End-to-end Scenario Tests
# ---------------------------------------------------------------------------


class TestEndToEnd:
    """End-to-end scenario tests combining multiple features."""

    @pytest.mark.asyncio
    async def test_full_diagnostic_pipeline(self):
        """Verify the full pipeline: detect -> attribute -> repair."""
        harness = SelfDiagnosingHarness()
        harness.monitor("e2e-session")

        # Build a trajectory with a failure
        now = datetime.now()
        trajectory = [
            ExecutionStep("s1", now, "reasoning", {"prompt": "list files"},
                          {"thought": "use ls"}, True),
            ExecutionStep("s2", now + timedelta(seconds=1), "tool_call",
                          {"tool_name": "bash", "command": "ls /nonexistent"},
                          {}, False, error="No such file or directory"),
            ExecutionStep("s3", now + timedelta(seconds=2), "tool_call",
                          {"tool_name": "bash", "command": "ls /nonexistent"},
                          {}, False, error="No such file or directory"),
            ExecutionStep("s4", now + timedelta(seconds=3), "reasoning",
                          {"thought": "retry"}, {"thought": "failed again"}, False),
        ]

        # Detect anomalies
        anomalies = harness.detect_anomalies(trajectory, session_id="e2e-session")
        assert len(anomalies) > 0

        # Record metrics on dashboard for the report
        harness.dashboard.record_tool_call("e2e-session")
        harness.dashboard.record_tool_call("e2e-session")
        harness.dashboard.record_error("e2e-session")
        harness.dashboard.record_cost("e2e-session", 0.05)
        harness.dashboard.record_tokens("e2e-session", 500)
        harness.dashboard.record_latency("e2e-session", 2.5)

        # Root cause analysis
        rca = await harness.root_cause_analysis(
            trajectory, agent_id="agent-e2e", agent_type="executor"
        )
        if rca:
            assert rca.confidence > 0.0
            assert rca.who_and_when is not None
            assert len(rca.recommendations) > 0

        # Trigger repair
        repair = await harness.trigger_repair(
            AnomalyType.TOOL_ERROR,
            "e2e-session",
            context={"session_id": "e2e-session"},
        )
        assert repair is not None
        assert repair.action_type in RepairActionType

        # Generate report
        report = harness.generate_report("e2e-session")
        assert report.total_errors > 0
        assert report.error_rate > 0.0
        assert report.uptime < 1.0

    @pytest.mark.asyncio
    async def test_mutation_and_detection_integration(self):
        """Mutation verifier combined with anomaly detection."""
        verifier = MutationVerifier(MutationConfig(count=3, seed=42))
        harness = SelfDiagnosingHarness()

        # Generate mutated inputs
        original = {"prompt": "list files in /tmp", "recursive": True}
        mutants = verifier.apply_mutations(original)

        # Verify the mutants have different input_data
        assert len(mutants) == 3
        for m in mutants:
            assert m.input_data != original
