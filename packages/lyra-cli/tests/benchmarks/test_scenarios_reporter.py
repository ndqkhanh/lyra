"""Tests for benchmark scenarios and reporter."""

from __future__ import annotations

import time

import pytest

from lyra_cli.benchmarks.reporter import (
    BenchmarkReporter,
    BenchmarkRunSummary,
    GradeThresholds,
    ReportFormat,
)
from lyra_cli.benchmarks.scenarios import (
    BenchmarkScenario,
    LoadProfile,
    ScenarioCategory,
    get_all_categories,
    get_scenario_by_name,
    get_scenarios_by_category,
)


class TestBenchmarkScenario:
    def test_scenario_creation(self):
        s = BenchmarkScenario(
            name="test_scenario",
            category=ScenarioCategory.ROUTING,
            description="A test",
            load_profile=LoadProfile.MODERATE,
            duration_seconds=10.0,
        )
        assert s.name == "test_scenario"
        assert s.warmup_seconds == 1.0
        assert s.tags == ()

    def test_scenario_immutability(self):
        s = BenchmarkScenario(
            name="test", category=ScenarioCategory.MEMORY,
            description="d", load_profile=LoadProfile.LIGHT,
            duration_seconds=1.0,
        )
        with pytest.raises(Exception):
            s.name = "other"

    def test_scenario_with_tags(self):
        s = BenchmarkScenario(
            name="tagged", category=ScenarioCategory.TOOLS,
            description="d", load_profile=LoadProfile.HEAVY,
            duration_seconds=1.0, tags=("fast", "critical"),
        )
        assert "fast" in s.tags


class TestScenarios:
    def test_scenarios_not_empty(self):
        from lyra_cli.benchmarks.scenarios import SCENARIOS

        assert len(SCENARIOS) > 0

    def test_scenarios_all_have_unique_names(self):
        from lyra_cli.benchmarks.scenarios import SCENARIOS

        names = [s.name for s in SCENARIOS]
        assert len(names) == len(set(names))

    def test_get_scenarios_by_category(self):
        routing = get_scenarios_by_category(ScenarioCategory.ROUTING)
        assert len(routing) > 0
        assert all(s.category == ScenarioCategory.ROUTING for s in routing)

    def test_get_scenario_by_name_exists(self):
        s = get_scenario_by_name("routing_policy_inference")
        assert s is not None
        assert s.category == ScenarioCategory.ROUTING

    def test_get_scenario_by_name_missing(self):
        assert get_scenario_by_name("nonexistent_scenario") is None

    def test_get_all_categories(self):
        categories = get_all_categories()
        assert ScenarioCategory.ROUTING in categories
        assert ScenarioCategory.MEMORY in categories


class TestBenchmarkReporter:
    @pytest.fixture
    def reporter(self):
        return BenchmarkReporter()

    @pytest.fixture
    def summary(self):
        return BenchmarkRunSummary(
            run_id="test-run-001",
            timestamp=time.time(),
            scenario_count=3,
            passed_count=2,
            failed_count=1,
            total_duration_sec=45.0,
            overall_grade="B",
        )

    @pytest.fixture
    def results(self):
        return [
            {"name": "routing_policy", "p95_ms": 5.0, "target_p95_ms": 10.0, "passed": True},
            {"name": "memory_read", "p95_ms": 15.0, "target_p95_ms": 20.0, "passed": True},
            {"name": "compaction", "p95_ms": 800.0, "target_p95_ms": 500.0, "passed": False},
        ]

    def test_text_report(self, reporter, summary, results):
        report = reporter.generate(summary, results, ReportFormat.TEXT)
        assert "test-run-001" in report
        assert "PASS" in report
        assert "FAIL" in report

    def test_json_report(self, reporter, summary, results):
        import json

        report = reporter.generate(summary, results, ReportFormat.JSON)
        data = json.loads(report)
        assert data["run_id"] == "test-run-001"
        assert len(data["results"]) == 3

    def test_markdown_report(self, reporter, summary, results):
        report = reporter.generate(summary, results, ReportFormat.MARKDOWN)
        assert "##" not in report.split("\n")[0]  # starts with #
        assert "| Scenario" in report

    def test_compute_grade_a_plus(self, reporter):
        assert reporter.compute_grade(4.0, 10.0) == "A+"  # 40% of target

    def test_compute_grade_a(self, reporter):
        assert reporter.compute_grade(7.0, 10.0) == "A"   # 70% of target

    def test_compute_grade_b(self, reporter):
        assert reporter.compute_grade(9.0, 10.0) == "B"   # 90% of target

    def test_compute_grade_c(self, reporter):
        assert reporter.compute_grade(13.0, 10.0) == "C"  # 130% of target

    def test_compute_grade_d(self, reporter):
        assert reporter.compute_grade(20.0, 10.0) == "D"  # 200% of target

    def test_compute_overall_grade(self, reporter):
        results = [
            {"p95_ms": 4.0, "target_p95_ms": 10.0},   # A+
            {"p95_ms": 7.0, "target_p95_ms": 10.0},   # A
            {"p95_ms": 4.0, "target_p95_ms": 10.0},   # A+
        ]
        grade = reporter.compute_overall_grade(results)
        assert grade in ("A+", "A")

    def test_grade_thresholds_default(self):
        t = GradeThresholds()
        assert t.a_plus_p95_ratio == 0.5
        assert t.a_p95_ratio == 0.75

    def test_custom_grade_thresholds(self):
        t = GradeThresholds(a_plus_p95_ratio=0.3, b_p95_ratio=1.2)
        reporter = BenchmarkReporter(grade_thresholds=t)
        assert reporter.compute_grade(2.0, 10.0) == "A+"  # ratio=0.2, <= 0.3
        assert reporter.compute_grade(14.0, 10.0) == "C"  # ratio=1.4, between 1.2 and 1.5


class TestReportFormat:
    def test_values(self):
        assert ReportFormat.TEXT == "text"
        assert ReportFormat.JSON == "json"
        assert ReportFormat.MARKDOWN == "markdown"


class TestLoadProfile:
    def test_values(self):
        assert LoadProfile.LIGHT == "light"
        assert LoadProfile.BURST == "burst"


class TestScenarioCategory:
    def test_values(self):
        assert ScenarioCategory.ROUTING == "routing"
        assert ScenarioCategory.SWARM == "swarm"


class TestBenchmarkRunSummary:
    def test_immutability(self):
        s = BenchmarkRunSummary(
            run_id="r", timestamp=1.0, scenario_count=1,
            passed_count=1, failed_count=0, total_duration_sec=1.0,
        )
        with pytest.raises(Exception):
            s.run_id = "other"
