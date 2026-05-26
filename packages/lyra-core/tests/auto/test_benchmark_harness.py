"""Tests for Phase 4.2b — Unified Benchmarking Harness."""
from __future__ import annotations

import pytest

from lyra_core.auto.benchmark_harness import (
    BenchmarkDomain,
    BenchmarkHarness,
    BenchmarkResult,
    BenchmarkRun,
    BenchmarkStatus,
)


@pytest.fixture
def harness():
    return BenchmarkHarness()


def make_runner(value):
    return lambda: value


class TestBenchmarkHarness:
    """Unit tests for BenchmarkHarness."""

    def test_register_adds_metric(self, harness):
        harness.register("safety", "block_rate", make_runner(0.99))
        assert harness.metric_count == 1

    def test_register_multiple_domains(self, harness):
        harness.register("safety", "block_rate", make_runner(0.99))
        harness.register("skills", "pass_rate", make_runner(0.92))
        harness.register("memory", "recall_rate", make_runner(0.88))
        assert harness.metric_count == 3

    def test_register_multiple_metrics_same_domain(self, harness):
        harness.register("safety", "block_rate", make_runner(0.99))
        harness.register("safety", "toxicity", make_runner(0.97))
        assert harness.metric_count == 2

    def test_register_with_threshold(self, harness):
        harness.register("safety", "block_rate", make_runner(0.7), threshold=0.95)
        run = harness.run_all()
        r = run.results[0]
        assert r.threshold == 0.95
        assert r.status != BenchmarkStatus.PASSED

    def test_register_with_baseline(self, harness):
        harness.register("skills", "pass_rate", make_runner(0.92), baseline=0.90)
        run = harness.run_all()
        r = run.results[0]
        assert r.baseline == 0.90

    def test_run_all_returns_run(self, harness):
        harness.register("safety", "block_rate", make_runner(0.99))
        run = harness.run_all()
        assert isinstance(run, BenchmarkRun)
        assert run.overall_score >= 0.0

    def test_run_all_passed_metrics(self, harness):
        harness.register("safety", "block_rate", make_runner(0.99), threshold=0.80)
        harness.register("skills", "pass_rate", make_runner(0.92), threshold=0.80)
        run = harness.run_all()
        assert all(r.status == BenchmarkStatus.PASSED for r in run.results)

    def test_run_all_warning_below_threshold(self, harness):
        harness.register("skills", "slow_test", make_runner(0.60), threshold=0.80)
        run = harness.run_all()
        r = run.results[0]
        assert r.status == BenchmarkStatus.WARNING

    def test_run_all_failed_below_floor(self, harness):
        harness.register("skills", "broken", make_runner(0.20), threshold=0.80)
        run = harness.run_all()
        r = run.results[0]
        assert r.status == BenchmarkStatus.FAILED

    def test_run_all_safety_failure_makes_not_passed(self, harness):
        harness.register("safety", "critical", make_runner(0.10), threshold=0.95)
        run = harness.run_all()
        assert run.passed is False

    def test_run_all_safety_ok_makes_passed(self, harness):
        harness.register("safety", "block_rate", make_runner(0.99), threshold=0.95)
        harness.register("skills", "broken", make_runner(0.10), threshold=0.80)
        run = harness.run_all()
        assert run.passed is True  # safety is OK

    def test_run_all_regression_detection(self, harness):
        harness.register("skills", "pass_rate", make_runner(0.80), threshold=0.80, baseline=0.99)
        run = harness.run_all()
        r = run.results[0]
        assert r.status == BenchmarkStatus.REGRESSION

    def test_run_all_no_regression_when_baseline_close(self, harness):
        harness.register("skills", "pass_rate", make_runner(0.96), threshold=0.80, baseline=0.99)
        run = harness.run_all()
        r = run.results[0]
        assert r.status == BenchmarkStatus.PASSED

    def test_runner_exception_returns_zero(self, harness):
        def broken():
            raise RuntimeError("cannot measure")

        harness.register("memory", "recall", broken)
        run = harness.run_all()
        assert run.results[0].score == 0.0

    def test_run_all_summary(self, harness):
        harness.register("safety", "test1", make_runner(0.99))
        harness.register("skills", "test2", make_runner(0.92))
        run = harness.run_all()
        assert "safety" in run.summary.lower() or "OK" in run.summary

    def test_set_baseline_snapshots_scores(self, harness):
        harness.register("skills", "pass_rate", make_runner(0.90))
        harness.set_baseline()
        run = harness.run_all()
        assert run.results[0].baseline == 0.90

    def test_set_baseline_does_not_crash_on_error(self, harness):
        def flaky():
            raise RuntimeError("temporary")

        harness.register("skills", "flaky", flaky)
        harness.set_baseline()  # should not raise

    def test_check_regressions_returns_only_problems(self, harness):
        harness.register("safety", "ok", make_runner(0.99), threshold=0.80)
        harness.register("skills", "broken", make_runner(0.10), threshold=0.80)
        harness.register("memory", "regressed", make_runner(0.70), threshold=0.80, baseline=0.99)
        regressions = harness.check_regressions()
        statuses = {r.status for r in regressions}
        assert BenchmarkStatus.FAILED in statuses or BenchmarkStatus.REGRESSION in statuses

    def test_get_domain_score_averages(self, harness):
        harness.register("safety", "a", make_runner(0.90))
        harness.register("safety", "b", make_runner(0.80))
        harness.run_all()
        score = harness.get_domain_score(BenchmarkDomain.SAFETY)
        assert score == pytest.approx(0.85, rel=0.01)

    def test_get_domain_score_no_history(self, harness):
        assert harness.get_domain_score(BenchmarkDomain.SAFETY) is None

    def test_get_domain_score_empty_domain(self, harness):
        harness.register("safety", "a", make_runner(0.90))
        harness.run_all()
        assert harness.get_domain_score(BenchmarkDomain.SKILLS) is None

    def test_history_accumulates(self, harness):
        harness.register("safety", "a", make_runner(0.90))
        harness.run_all()
        harness.run_all()
        assert len(harness.history) == 2

    def test_clear_history(self, harness):
        harness.register("safety", "a", make_runner(0.90))
        harness.run_all()
        harness.clear_history()
        assert len(harness.history) == 0

    def test_unknown_domain_is_skipped(self, harness):
        harness.register("nonexistent_domain", "metric", make_runner(0.50))
        run = harness.run_all()
        assert run.domains_covered == 0

    def test_domains_covered_count(self, harness):
        harness.register("safety", "a", make_runner(0.90))
        harness.register("skills", "b", make_runner(0.80))
        harness.register("memory", "c", make_runner(0.70))
        run = harness.run_all()
        assert run.domains_covered == 3

    def test_benchmark_result_frozen(self, harness):
        harness.register("safety", "a", make_runner(0.90))
        run = harness.run_all()
        with pytest.raises(Exception):
            run.results[0].score = 1.0  # type: ignore[misc]

    def test_benchmark_domain_enum_values(self):
        assert BenchmarkDomain.SAFETY.value == "safety"
        assert BenchmarkDomain.SKILLS.value == "skills"
        assert BenchmarkDomain.MEMORY.value == "memory"
        assert BenchmarkDomain.REASONING.value == "reasoning"
        assert BenchmarkDomain.ORCHESTRATION.value == "orchestration"
        assert BenchmarkDomain.EVOLUTION.value == "evolution"
        assert BenchmarkDomain.PRODUCTION.value == "production"

    def test_benchmark_status_enum_values(self):
        assert BenchmarkStatus.PASSED.value == "passed"
        assert BenchmarkStatus.WARNING.value == "warning"
        assert BenchmarkStatus.FAILED.value == "failed"
        assert BenchmarkStatus.REGRESSION.value == "regression"

    def test_run_has_unique_id(self, harness):
        harness.register("safety", "a", make_runner(0.90))
        r1 = harness.run_all()
        r2 = harness.run_all()
        assert r1.run_id != r2.run_id
