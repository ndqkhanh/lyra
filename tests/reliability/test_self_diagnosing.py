"""
Tests for the Self-Diagnosing Reliability System.

Covers:
- SelfDiagnosingHarness anomaly detection (all 6 anomaly types)
- HealthStream push / iteration
- Auto-repair selection and execution
- ReliabilityReport generation
- BenchmarkRunner execution and regression detection
- BaselineManager regression comparison
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lyra.observability.dashboard import MetricsDashboard
from lyra.reliability.benchmark_runner import (
    BaselineManager,
    BaselineEntry,
    BenchmarkConfig,
    BenchmarkResult,
    BenchmarkRunner,
    BenchmarkSuiteResult,
    HumanEvalRunner,
    RegressionAlert,
    TerminalBenchRunner,
)
from lyra.reliability.self_diagnosing_harness import (
    AnomalyType,
    HealthEvent,
    HealthStream,
    ReliabilityReport,
    RepairAction,
    RepairActionType,
    SelfDiagnosingHarness,
)
from lyra.verification.error_probe import ExecutionStep
from lyra.verification.tracing_provider import TracingProvider


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def dashboard() -> MetricsDashboard:
    return MetricsDashboard()


@pytest.fixture
def harness(dashboard: MetricsDashboard) -> SelfDiagnosingHarness:
    return SelfDiagnosingHarness(dashboard=dashboard)


@pytest.fixture
def healthy_trajectory() -> list[ExecutionStep]:
    now = datetime.now(timezone.utc)
    return [
        ExecutionStep(
            step_id="s1", timestamp=now,
            action="reasoning", input_data={"prompt": "analyze the data"},
            output_data={"confidence": 0.95},
            success=True,
            metadata={"duration_ms": 200},
        ),
        ExecutionStep(
            step_id="s2", timestamp=now,
            action="tool_call", input_data={"tool_name": "read_file"},
            output_data={"result": "content"}, success=True,
            metadata={"duration_ms": 500, "cost": 0.01},
        ),
        ExecutionStep(
            step_id="s3", timestamp=now,
            action="reasoning", input_data={"prompt": "summarize results"},
            output_data={"plan": "done"},
            success=True, metadata={"duration_ms": 100},
        ),
    ]


@pytest.fixture
def tool_error_trajectory() -> list[ExecutionStep]:
    now = datetime.now(timezone.utc)
    return [
        ExecutionStep(
            step_id="e1", timestamp=now,
            action="tool_call", input_data={"tool_name": "read_file"},
            output_data={}, success=False, error="File not found",
            metadata={"duration_ms": 300, "cost": 0.01},
        ),
        ExecutionStep(
            step_id="e2", timestamp=now,
            action="tool_call", input_data={"tool_name": "read_file"},
            output_data={}, success=False, error="Permission denied",
            metadata={"duration_ms": 300, "cost": 0.01},
        ),
        ExecutionStep(
            step_id="e3", timestamp=now,
            action="tool_call", input_data={"tool_name": "list_dir"},
            output_data={}, success=False, error="Timeout",
            metadata={"duration_ms": 300, "cost": 0.01},
        ),
    ]


@pytest.fixture
def low_confidence_trajectory() -> list[ExecutionStep]:
    now = datetime.now(timezone.utc)
    return [
        ExecutionStep(
            step_id="h1", timestamp=now,
            action="reasoning", input_data={},
            output_data={"text": "I think it might be, but I'm not sure"},
            success=True, metadata={"confidence": 0.2, "duration_ms": 100},
        ),
        ExecutionStep(
            step_id="h2", timestamp=now,
            action="tool_call", input_data={"tool_name": "search"},
            output_data={"result": "something"}, success=True,
            metadata={"duration_ms": 200, "cost": 0.01},
        ),
    ]


@pytest.fixture
def loop_trajectory() -> list[ExecutionStep]:
    now = datetime.now(timezone.utc)
    steps = []
    for i in range(6):
        steps.append(
            ExecutionStep(
                step_id=f"l{i}", timestamp=now,
                action="tool_call", input_data={"tool_name": "search"},
                output_data={"result": f"attempt {i}"},
                success=True, metadata={"duration_ms": 500, "cost": 0.01},
            )
        )
    return steps


# ===================================================================
# HealthStream
# ===================================================================


class TestHealthStream:
    def test_push_and_recent(self) -> None:
        stream = HealthStream("test-session")
        assert stream.session_id == "test-session"
        assert stream.event_count == 0

        stream.push(HealthEvent(
            timestamp=datetime.now(timezone.utc),
            event_type="anomaly_detected",
            session_id="test-session",
            detail={"anomaly_type": "tool_error"},
        ))
        assert stream.event_count == 1
        assert len(stream.recent_events) == 1
        assert stream.recent_events[0].event_type == "anomaly_detected"

    def test_close_stops_accepting(self) -> None:
        stream = HealthStream("s")
        stream.close()
        stream.push(HealthEvent(
            timestamp=datetime.now(timezone.utc),
            event_type="heartbeat",
            session_id="s",
        ))
        assert stream.event_count == 0

    @pytest.mark.asyncio
    async def test_async_iteration(self) -> None:
        stream = HealthStream("s")
        stream.push(HealthEvent(
            timestamp=datetime.now(timezone.utc),
            event_type="test",
            session_id="s",
        ))
        stream.close()

        events = [e async for e in stream]
        assert len(events) == 1
        assert events[0].event_type == "test"


# ===================================================================
# Anomaly Detection
# ===================================================================


class TestAnomalyDetection:
    def test_healthy_trajectory_no_anomalies(
        self, harness: SelfDiagnosingHarness, healthy_trajectory: list[ExecutionStep]
    ) -> None:
        anomalies = harness.detect_anomalies(healthy_trajectory)
        assert anomalies == []

    def test_detects_tool_error(
        self, harness: SelfDiagnosingHarness, tool_error_trajectory: list[ExecutionStep]
    ) -> None:
        anomalies = harness.detect_anomalies(tool_error_trajectory, session_id="t1")
        assert AnomalyType.TOOL_ERROR in anomalies

    def test_detects_hallucination(
        self,
        harness: SelfDiagnosingHarness,
        low_confidence_trajectory: list[ExecutionStep],
    ) -> None:
        anomalies = harness.detect_anomalies(low_confidence_trajectory, session_id="h")
        assert AnomalyType.HALLUCINATION in anomalies

    def test_detects_infinite_loop(
        self, harness: SelfDiagnosingHarness, loop_trajectory: list[ExecutionStep]
    ) -> None:
        anomalies = harness.detect_anomalies(loop_trajectory, session_id="l")
        assert AnomalyType.INFINITE_LOOP in anomalies

    def test_detects_cost_spike(
        self, harness: SelfDiagnosingHarness
    ) -> None:
        now = datetime.now(timezone.utc)
        steps = [
            ExecutionStep(
                step_id="c1", timestamp=now,
                action="tool_call", input_data={"tool_name": "expensive"},
                output_data={}, success=True,
                metadata={"cost": 1.0, "duration_ms": 200},
            ),
        ]
        harness.dashboard.record_cost("sid-1", 1.0)
        anomalies = harness.detect_anomalies(steps, session_id="sid-1")
        assert AnomalyType.COST_SPIKE in anomalies

    def test_detects_latency_spike(
        self, harness: SelfDiagnosingHarness
    ) -> None:
        now = datetime.now(timezone.utc)
        steps = [
            ExecutionStep(
                step_id="l1", timestamp=now,
                action="tool_call", input_data={"tool_name": "slow"},
                output_data={}, success=True,
                metadata={"duration_ms": 60000, "cost": 0.01},
            ),
        ]
        harness.latency_spike_threshold = 30.0
        anomalies = harness.detect_anomalies(steps, session_id="ls")
        assert AnomalyType.LATENCY_SPIKE in anomalies

    def test_detects_output_regression(
        self, harness: SelfDiagnosingHarness
    ) -> None:
        harness.dashboard.record_error("reg-s", "tool_failure")
        harness.dashboard.record_tool_call("reg-s")
        harness.dashboard.record_tool_call("reg-s")
        harness.dashboard.record_tool_call("reg-s")
        harness.error_rate_threshold = 0.3
        # 1 error / 3 calls = 0.33 -> above 0.3
        anomalies = harness.detect_anomalies([], session_id="reg-s")
        assert AnomalyType.OUTPUT_REGRESSION in anomalies

    def test_detect_propagates_to_stream(
        self, harness: SelfDiagnosingHarness, tool_error_trajectory: list[ExecutionStep]
    ) -> None:
        harness.monitor("stream-session")
        harness.detect_anomalies(tool_error_trajectory, session_id="stream-session")
        stream = harness._streams["stream-session"]
        # Anomaly events were pushed
        assert any(e.event_type == "anomaly_detected" for e in stream.recent_events)
        # History was recorded
        assert AnomalyType.TOOL_ERROR in harness._anomaly_history["stream-session"]


# ===================================================================
# Auto-Repair
# ===================================================================


class TestAutoRepair:
    @pytest.mark.asyncio
    async def test_trigger_repair_tool_error(self, harness: SelfDiagnosingHarness) -> None:
        harness.monitor("r1")
        action = await harness.trigger_repair(
            anomaly=AnomalyType.TOOL_ERROR,
            session_id="r1",
            context={"retry_fn": AsyncMock(return_value="ok")},
        )
        assert action.anomaly == AnomalyType.TOOL_ERROR
        assert action.session_id == "r1"
        assert action.action_type == RepairActionType.RETRY_SAME_MODEL
        assert action.success is True
        assert action.recovery_time_seconds is not None

    @pytest.mark.asyncio
    async def test_trigger_repair_loop_without_fn(self, harness: SelfDiagnosingHarness) -> None:
        harness.monitor("r2")
        action = await harness.trigger_repair(
            anomaly=AnomalyType.INFINITE_LOOP,
            session_id="r2",
        )
        assert action.success is False  # No retry_fn provided

    @pytest.mark.asyncio
    async def test_repair_history_tracked(self, harness: SelfDiagnosingHarness) -> None:
        harness.monitor("r3")
        fn = AsyncMock(return_value="ok")
        await harness.trigger_repair(
            anomaly=AnomalyType.TOOL_ERROR,
            session_id="r3",
            context={"retry_fn": fn},
        )
        history = harness._repair_history["r3"]
        assert len(history) == 1
        assert history[0].anomaly == AnomalyType.TOOL_ERROR
        assert history[0].success is True

    @pytest.mark.asyncio
    async def test_repair_action_escalates_to_human(
        self, harness: SelfDiagnosingHarness
    ) -> None:
        harness.monitor("r4")
        action = await harness.trigger_repair(
            anomaly=AnomalyType.HALLUCINATION,
            session_id="r4",
        )
        # Hallucination first choice is RETRY_WITH_CONTEXT_COMPACTION -> no fn -> fails
        # Then RETRY_SAME_MODEL -> no fn -> fails
        # Then ESCALATE_TO_HUMAN -> succeeds
        assert action.action_type in (
            RepairActionType.ESCALATE_TO_HUMAN,
            RepairActionType.RETRY_WITH_CONTEXT_COMPACTION,
            RepairActionType.RETRY_SAME_MODEL,
        )

    @pytest.mark.asyncio
    async def test_repair_pushes_health_event(self, harness: SelfDiagnosingHarness) -> None:
        harness.monitor("r5")
        fn = AsyncMock(return_value="ok")
        await harness.trigger_repair(
            anomaly=AnomalyType.TOOL_ERROR,
            session_id="r5",
            context={"retry_fn": fn},
        )
        stream = harness._streams["r5"]
        assert any(e.event_type == "repair_succeeded" for e in stream.recent_events)

    def test_select_repair_action_escalation(self, harness: SelfDiagnosingHarness) -> None:
        """When all actions have been tried recently, fall back to escalate."""
        harness._repair_history["x"] = [
            RepairAction(RepairActionType.RETRY_SAME_MODEL, AnomalyType.TOOL_ERROR, "x", datetime.now(timezone.utc), ""),
            RepairAction(RepairActionType.RETRY_CHEAPER_MODEL, AnomalyType.TOOL_ERROR, "x", datetime.now(timezone.utc), ""),
            RepairAction(RepairActionType.ABORT_SESSION, AnomalyType.TOOL_ERROR, "x", datetime.now(timezone.utc), ""),
        ]
        action_type = harness._select_repair_action(
            AnomalyType.TOOL_ERROR, {"session_id": "x"}
        )
        assert action_type == RepairActionType.ESCALATE_TO_HUMAN

    def test_repair_description_generation(self) -> None:
        desc = SelfDiagnosingHarness._repair_description(
            RepairActionType.RETRY_SAME_MODEL, AnomalyType.TOOL_ERROR
        )
        assert "Retrying same model" in desc
        assert "tool_error" in desc


# ===================================================================
# Reliability Report
# ===================================================================


class TestReliabilityReport:
    def test_from_session_with_data(self, dashboard: MetricsDashboard) -> None:
        dashboard.record_tool_call("sid-r")
        dashboard.record_tool_call("sid-r")
        dashboard.record_error("sid-r", "tool_error")
        dashboard.record_cost("sid-r", 0.10)
        dashboard.record_tokens("sid-r", 1000)

        repairs = [
            RepairAction(
                action_type=RepairActionType.RETRY_SAME_MODEL,
                anomaly=AnomalyType.TOOL_ERROR,
                session_id="sid-r",
                timestamp=datetime.now(timezone.utc),
                description="retry",
                success=True,
                recovery_time_seconds=2.5,
            ),
            RepairAction(
                action_type=RepairActionType.ESCALATE_TO_HUMAN,
                anomaly=AnomalyType.HALLUCINATION,
                session_id="sid-r",
                timestamp=datetime.now(timezone.utc),
                description="escalate",
                success=True,
                recovery_time_seconds=1.0,
            ),
        ]

        report = ReliabilityReport.from_session(
            session_id="sid-r",
            dashboard=dashboard,
            repairs=repairs,
            anomalies=[AnomalyType.TOOL_ERROR, AnomalyType.HALLUCINATION],
        )

        assert report.session_id == "sid-r"
        assert report.total_operations == 2
        assert report.total_errors == 1
        assert report.error_rate == 0.5
        assert report.uptime == 0.5
        assert report.mean_time_to_recovery == pytest.approx(1.75, abs=0.01)
        assert report.total_recovery_time == 3.5
        assert report.total_cost == 0.10
        assert report.anomaly_breakdown == {"tool_error": 1, "hallucination": 1}
        assert report.repair_success_rate == 1.0

    def test_from_session_empty(self, dashboard: MetricsDashboard) -> None:
        report = ReliabilityReport.from_session(
            session_id="nonexistent",
            dashboard=dashboard,
            repairs=[],
            anomalies=[],
        )
        assert report.uptime == 1.0
        assert report.error_rate == 0.0
        assert report.mean_time_to_recovery == 0.0

    def test_report_anomaly_breakdown(self, harness: SelfDiagnosingHarness) -> None:
        harness._anomaly_history["ar"] = [
            AnomalyType.TOOL_ERROR,
            AnomalyType.TOOL_ERROR,
            AnomalyType.COST_SPIKE,
        ]
        harness._repair_history["ar"] = []
        harness.dashboard.record_tool_call("ar")
        harness.dashboard.record_error("ar", "tool")
        report = harness.generate_report("ar")
        assert report.anomaly_breakdown.get("tool_error", 0) == 2
        assert report.anomaly_breakdown.get("cost_spike", 0) == 1


# ===================================================================
# Health Check
# ===================================================================


class TestHarnessHealthCheck:
    def test_health_check_healthy(self, harness: SelfDiagnosingHarness) -> None:
        status = harness.health_check()
        assert status["status"] == "healthy"
        assert status["active_sessions"] == 0
        assert status["repair_success_rate"] == 1.0

    def test_health_check_with_sessions(self, harness: SelfDiagnosingHarness) -> None:
        harness.monitor("a")
        harness.monitor("b")
        status = harness.health_check()
        assert status["active_sessions"] == 2

    def test_monitor_and_close(self, harness: SelfDiagnosingHarness) -> None:
        stream = harness.monitor("close-test")
        assert "close-test" in harness.active_sessions()
        harness.close_stream("close-test")
        assert "close-test" not in harness.active_sessions()


# ===================================================================
# Benchmark Runner
# ===================================================================


class TestBenchmarkRunner:
    @pytest.mark.asyncio
    async def test_run_humaneval_benchmark(self) -> None:
        runner = BenchmarkRunner(config=BenchmarkConfig(which="humaneval", tasks=3, k=2))
        result = await runner.run_benchmark("humaneval")
        assert result.benchmark_name == "humaneval"
        assert result.n_tasks == 3
        assert result.k == 2
        assert result.total_duration_seconds > 0
        # pass@1 / pass@k have plausible float values
        assert 0.0 <= result.pass_at_1 <= 1.0
        assert 0.0 <= result.pass_at_k <= 1.0

    @pytest.mark.asyncio
    async def test_run_terminal_bench_benchmark(self) -> None:
        runner = BenchmarkRunner(config=BenchmarkConfig(which="terminal-bench", tasks=3, k=1))
        result = await runner.run_benchmark("terminal-bench")
        assert result.benchmark_name.startswith("terminal-bench")

    @pytest.mark.asyncio
    async def test_run_suite(self) -> None:
        runner = BenchmarkRunner(
            config=BenchmarkConfig(which=["humaneval", "terminal-bench"], tasks=3, k=1)
        )
        suite_result = await runner.run_suite()
        assert isinstance(suite_result, BenchmarkSuiteResult)
        assert len(suite_result.results) == 2
        assert suite_result.total_duration_seconds > 0

    @pytest.mark.asyncio
    async def test_suite_handles_benchmark_error(self) -> None:
        runner = BenchmarkRunner(
            config=BenchmarkConfig(which=["nonexistent-bench"], tasks=1, k=1)
        )
        suite_result = await runner.run_suite()
        assert len(suite_result.results) == 1
        assert suite_result.results[0].error is not None

    def test_summary_no_results(self) -> None:
        runner = BenchmarkRunner()
        assert "No benchmark results available." in runner.summary()

    def test_unknown_benchmark_raises(self) -> None:
        runner = BenchmarkRunner()
        with pytest.raises(ValueError, match="Unknown benchmark"):
            runner._build_runner("bogus-bench")

    def test_resolve_benchmarks_star(self) -> None:
        runner = BenchmarkRunner(config=BenchmarkConfig(which="*"))
        resolved = runner._resolve_benchmarks()
        assert "tau-bench" in resolved
        assert "humaneval" in resolved

    def test_result_storage(self) -> None:
        runner = BenchmarkRunner()
        runner._results["test-bench"] = BenchmarkResult(
            benchmark_name="test-bench",
            pass_at_1=0.8,
            pass_at_k=0.5,
            k=3,
            n_tasks=10,
            avg_cost_per_task=0.01,
            avg_tokens_per_task=100,
            total_duration_seconds=5.0,
        )
        assert runner.result("test-bench") is not None
        assert runner.result("nonexistent") is None


class TestBenchmarkResult:
    def test_score_pass_at_1(self) -> None:
        r = BenchmarkResult(
            benchmark_name="b", pass_at_1=0.75, pass_at_k=0.5,
            k=1, n_tasks=10, avg_cost_per_task=0.0,
            avg_tokens_per_task=0, total_duration_seconds=1.0,
        )
        assert r.score == 0.75

    def test_score_pass_at_k(self) -> None:
        r = BenchmarkResult(
            benchmark_name="b", pass_at_1=0.75, pass_at_k=0.9,
            k=5, n_tasks=10, avg_cost_per_task=0.0,
            avg_tokens_per_task=0, total_duration_seconds=1.0,
        )
        assert r.score == 0.9


class TestBenchmarkConfig:
    def test_invalid_frequency_raises(self) -> None:
        with pytest.raises(ValueError, match="frequency"):
            BenchmarkConfig(frequency="yearly")

    def test_valid_frequencies(self) -> None:
        for freq in ("daily", "weekly", "manual"):
            config = BenchmarkConfig(frequency=freq)  # type: ignore[arg-type]
            assert config.frequency == freq


# ===================================================================
# Baseline / Regression Detection
# ===================================================================


class TestBaselineManager:
    def test_update_and_get(self, tmp_path) -> None:
        path = tmp_path / "baselines.json"
        mgr = BaselineManager(path=str(path))
        result = BenchmarkResult(
            benchmark_name="humaneval",
            pass_at_1=0.8, pass_at_k=0.9, k=5, n_tasks=50,
            avg_cost_per_task=0.01, avg_tokens_per_task=100,
            total_duration_seconds=10.0,
        )
        mgr.update(result)

        entry = mgr.get("humaneval")
        assert entry is not None
        assert entry.score == 0.9
        assert entry.benchmark_name == "humaneval"

    def test_persists_to_disk(self, tmp_path) -> None:
        path = tmp_path / "baselines.json"
        mgr1 = BaselineManager(path=str(path))
        mgr1.update(BenchmarkResult(
            benchmark_name="tau-bench", pass_at_1=0.5, pass_at_k=0.5, k=1,
            n_tasks=10, avg_cost_per_task=0.0, avg_tokens_per_task=0,
            total_duration_seconds=1.0,
        ))

        mgr2 = BaselineManager(path=str(path))
        entry = mgr2.get("tau-bench")
        assert entry is not None
        assert entry.score == 0.5

    def test_regression_detection(self) -> None:
        mgr = BaselineManager()
        mgr._entries["test-bench"] = BaselineEntry(
            benchmark_name="test-bench", score=0.9,
            timestamp=datetime.now(timezone.utc),
        )

        result = BenchmarkResult(
            benchmark_name="test-bench",
            pass_at_1=0.6, pass_at_k=0.6, k=1, n_tasks=50,
            avg_cost_per_task=0.01, avg_tokens_per_task=100,
            total_duration_seconds=10.0,
        )
        alert = mgr.check_regression(result, threshold=0.05)
        assert alert is not None
        assert alert.benchmark_name == "test-bench"
        assert alert.previous_score == 0.9
        assert alert.current_score == 0.6
        assert "REGRESSION" in alert.message

    def test_no_regression_within_threshold(self) -> None:
        mgr = BaselineManager()
        mgr._entries["b"] = BaselineEntry(
            benchmark_name="b", score=0.5,
            timestamp=datetime.now(timezone.utc),
        )
        result = BenchmarkResult(
            benchmark_name="b", pass_at_1=0.48, pass_at_k=0.48, k=1,
            n_tasks=10, avg_cost_per_task=0.0, avg_tokens_per_task=0,
            total_duration_seconds=1.0,
        )
        assert mgr.check_regression(result, threshold=0.05) is None

    def test_no_baseline_returns_none(self) -> None:
        mgr = BaselineManager()
        result = BenchmarkResult(
            benchmark_name="unseen", pass_at_1=0.5, pass_at_k=0.5, k=1,
            n_tasks=10, avg_cost_per_task=0.0, avg_tokens_per_task=0,
            total_duration_seconds=1.0,
        )
        assert mgr.check_regression(result) is None


class TestRegressionAlert:
    def test_alert_creation(self) -> None:
        alert = RegressionAlert(
            benchmark_name="b",
            previous_score=0.9,
            current_score=0.5,
            drop=0.4,
            threshold=0.05,
            message="REGRESSION: b dropped",
        )
        assert alert.benchmark_name == "b"
        assert alert.drop == 0.4


# ===================================================================
# TerminalBenchRunner / HumanEvalRunner
# ===================================================================


class TestTerminalBenchRunner:
    def test_get_tasks(self) -> None:
        runner = TerminalBenchRunner()
        tasks = runner.get_tasks(n=5)
        assert len(tasks) == 5
        assert all(t.task_id.startswith("terminal-") for t in tasks)

    def test_check_accepts_command_lines(self) -> None:
        runner = TerminalBenchRunner()
        tasks = runner.get_tasks(n=1)

        async def _test():
            result = await runner.check(tasks[0], "Use `grep` to search:\n```\n$ grep -r 'pattern' .\n```")
            assert result is True

        asyncio.run(_test())

    def test_name(self) -> None:
        runner = TerminalBenchRunner()
        assert "terminal-bench" in runner.get_name()


class TestHumanEvalRunner:
    def test_get_tasks(self) -> None:
        runner = HumanEvalRunner()
        tasks = runner.get_tasks(n=3)
        assert len(tasks) == 3

    def test_check_accepts_function(self) -> None:
        runner = HumanEvalRunner()
        tasks = runner.get_tasks(n=1)

        async def _test():
            result = await runner.check(
                tasks[0],
                "def solution(x: int) -> int:\n    return x * 2\n",
            )
            assert result is True

        asyncio.run(_test())

    def test_check_rejects_bare_output(self) -> None:
        runner = HumanEvalRunner()
        tasks = runner.get_tasks(n=1)

        async def _test():
            result = await runner.check(tasks[0], "just some text")
            assert result is False

        asyncio.run(_test())

    def test_name(self) -> None:
        runner = HumanEvalRunner()
        assert runner.get_name() == "humaneval"


# ===================================================================
# BenchmarkSuiteResult
# ===================================================================


class TestBenchmarkSuiteResult:
    def test_by_name_found(self) -> None:
        suite = BenchmarkSuiteResult(
            results=[
                BenchmarkResult(
                    benchmark_name="humaneval",
                    pass_at_1=0.8, pass_at_k=0.9, k=5, n_tasks=50,
                    avg_cost_per_task=0.01, avg_tokens_per_task=100,
                    total_duration_seconds=10.0,
                ),
            ],
        )
        assert suite.by_name("humaneval") is not None
        assert suite.by_name("nonexistent") is None

    def test_tracking_regressions(self) -> None:
        alert = RegressionAlert(
            benchmark_name="b", previous_score=0.9, current_score=0.5,
            drop=0.4, threshold=0.05, message="regression",
        )
        suite = BenchmarkSuiteResult(results=[], regressions=[alert])
        assert len(suite.regressions) == 1
