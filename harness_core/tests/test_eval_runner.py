"""Tests for harness_core.eval_runner — types + runner + drift monitor."""
from __future__ import annotations

import pytest

from harness_core.cost import CostTracker
from harness_core.eval_runner import (
    DriftAlert,
    DriftMonitor,
    EvalCase,
    EvalResult,
    EvalRun,
    EvalRunner,
    EvalSuite,
)


# --- EvalCase / EvalResult / EvalSuite / EvalRun ----------------------


class TestEvalCase:
    def test_valid(self):
        c = EvalCase(case_id="c1", inputs={"q": "x"}, expected_output="X")
        assert c.weight == 1.0

    def test_empty_id_rejected(self):
        with pytest.raises(ValueError):
            EvalCase(case_id="", inputs={"q": "x"})

    def test_empty_inputs_rejected(self):
        with pytest.raises(ValueError):
            EvalCase(case_id="c", inputs={})

    def test_negative_weight_rejected(self):
        with pytest.raises(ValueError):
            EvalCase(case_id="c", inputs={"q": "x"}, weight=-1.0)


class TestEvalResult:
    def test_create(self):
        r = EvalResult.create(
            case_id="c1", suite_id="s1",
            score=0.8, passed=True, actual_output="X",
        )
        assert r.passed is True
        assert r.score == 0.8

    def test_invalid_score(self):
        with pytest.raises(ValueError):
            EvalResult.create(
                case_id="c", suite_id="s", score=1.5, passed=True,
            )

    def test_negative_cost_rejected(self):
        with pytest.raises(ValueError):
            EvalResult.create(
                case_id="c", suite_id="s", score=0.5, passed=True,
                cost_usd=-1.0,
            )


class TestEvalSuite:
    def test_valid(self):
        s = EvalSuite(suite_id="x", cases=(
            EvalCase(case_id="c1", inputs={"q": "x"}),
        ))
        assert len(s) == 1

    def test_empty_id_rejected(self):
        with pytest.raises(ValueError):
            EvalSuite(suite_id="", cases=(EvalCase(case_id="c", inputs={"q": "x"}),))

    def test_no_cases_rejected(self):
        with pytest.raises(ValueError):
            EvalSuite(suite_id="x", cases=())

    def test_duplicate_case_id_rejected(self):
        with pytest.raises(ValueError):
            EvalSuite(suite_id="x", cases=(
                EvalCase(case_id="c1", inputs={"q": "x"}),
                EvalCase(case_id="c1", inputs={"q": "y"}),  # dup
            ))


class TestEvalRun:
    def test_pass_rate_empty(self):
        r = EvalRun.create(suite_id="x", results=[])
        assert r.pass_rate == 0.0
        assert r.mean_score == 0.0

    def test_pass_rate(self):
        r = EvalRun.create(suite_id="x", results=[
            EvalResult.create(case_id="c1", suite_id="x", score=1.0, passed=True),
            EvalResult.create(case_id="c2", suite_id="x", score=0.0, passed=False),
            EvalResult.create(case_id="c3", suite_id="x", score=1.0, passed=True),
        ])
        assert r.pass_rate == pytest.approx(2 / 3)

    def test_mean_score_weighted(self):
        r = EvalRun.create(suite_id="x", results=[
            EvalResult.create(case_id="c1", suite_id="x", score=1.0, passed=True, weight=1.0),
            EvalResult.create(case_id="c2", suite_id="x", score=0.0, passed=False, weight=3.0),
        ])
        # Weighted mean: (1*1 + 0*3) / (1+3) = 0.25
        assert r.mean_score == pytest.approx(0.25)

    def test_total_cost_and_duration(self):
        r = EvalRun.create(suite_id="x", results=[
            EvalResult.create(case_id="c1", suite_id="x", score=1.0, passed=True,
                               cost_usd=0.5, duration_ms=100.0),
            EvalResult.create(case_id="c2", suite_id="x", score=1.0, passed=True,
                               cost_usd=0.3, duration_ms=200.0),
        ])
        assert r.total_cost_usd == pytest.approx(0.8)
        assert r.total_duration_ms == 300.0

    def test_n_passed_failed_errors(self):
        r = EvalRun.create(suite_id="x", results=[
            EvalResult.create(case_id="c1", suite_id="x", score=1.0, passed=True),
            EvalResult.create(case_id="c2", suite_id="x", score=0.0, passed=False),
            EvalResult.create(case_id="c3", suite_id="x", score=0.0, passed=False, error="boom"),
        ])
        assert r.n_passed == 1
        assert r.n_failed == 2
        assert r.n_errors == 1
        assert len(r.failed_cases()) == 2


# --- EvalRunner --------------------------------------------------------


def _exact_match_eval(case, output) -> float:
    return 1.0 if output == case.expected_output else 0.0


class TestEvalRunner:
    def test_basic_run(self):
        def upper(inputs):
            return inputs["q"].upper()

        suite = EvalSuite(suite_id="upper", cases=(
            EvalCase(case_id="c1", inputs={"q": "hi"}, expected_output="HI"),
            EvalCase(case_id="c2", inputs={"q": "bye"}, expected_output="BYE"),
        ))
        runner = EvalRunner(program=upper, eval_fn=_exact_match_eval)
        run = runner.run(suite)
        assert run.pass_rate == 1.0
        assert run.mean_score == 1.0

    def test_failed_case(self):
        def fail_one(inputs):
            return inputs["q"].lower()  # lowercase, not uppercase

        suite = EvalSuite(suite_id="x", cases=(
            EvalCase(case_id="c1", inputs={"q": "HI"}, expected_output="HI"),
        ))
        runner = EvalRunner(program=fail_one, eval_fn=_exact_match_eval)
        run = runner.run(suite)
        assert run.pass_rate == 0.0
        assert run.failed_cases()[0].case_id == "c1"

    def test_program_exception_recorded(self):
        def broken(inputs):
            raise RuntimeError("boom")

        suite = EvalSuite(suite_id="x", cases=(
            EvalCase(case_id="c1", inputs={"q": "x"}, expected_output="x"),
        ))
        runner = EvalRunner(program=broken, eval_fn=_exact_match_eval)
        run = runner.run(suite)
        assert run.n_errors == 1
        assert "boom" in run.results[0].error

    def test_eval_fn_exception_recorded(self):
        def upper(inputs):
            return inputs["q"].upper()

        def broken_eval(case, output):
            raise RuntimeError("eval-down")

        suite = EvalSuite(suite_id="x", cases=(
            EvalCase(case_id="c1", inputs={"q": "hi"}),
        ))
        runner = EvalRunner(program=upper, eval_fn=broken_eval)
        run = runner.run(suite)
        assert "eval-down" in run.results[0].error

    def test_eval_out_of_range_recorded(self):
        suite = EvalSuite(suite_id="x", cases=(
            EvalCase(case_id="c1", inputs={"q": "x"}),
        ))
        runner = EvalRunner(
            program=lambda i: "x",
            eval_fn=lambda case, out: 1.5,  # out of range
        )
        run = runner.run(suite)
        assert "out-of-range" in run.results[0].error

    def test_pass_threshold(self):
        suite = EvalSuite(suite_id="x", cases=(
            EvalCase(case_id="c1", inputs={"q": "x"}),
            EvalCase(case_id="c2", inputs={"q": "y"}),
        ))
        # eval scores: 0.4 and 0.7
        scores = iter([0.4, 0.7])
        runner = EvalRunner(
            program=lambda i: "x",
            eval_fn=lambda c, o: next(scores),
            pass_threshold=0.5,
        )
        run = runner.run(suite)
        # First case: 0.4 < 0.5 → fail; Second: 0.7 >= 0.5 → pass.
        assert run.pass_rate == 0.5

    def test_invalid_pass_threshold(self):
        with pytest.raises(ValueError):
            EvalRunner(
                program=lambda i: "x",
                eval_fn=lambda c, o: 0.5,
                pass_threshold=1.5,
            )

    def test_max_cases_caps_run(self):
        suite = EvalSuite(suite_id="x", cases=tuple(
            EvalCase(case_id=f"c{i}", inputs={"q": "x"}) for i in range(10)
        ))
        runner = EvalRunner(
            program=lambda i: "x",
            eval_fn=lambda c, o: 1.0,
            max_cases=3,
        )
        run = runner.run(suite)
        assert len(run.results) == 3

    def test_cost_fn(self):
        suite = EvalSuite(suite_id="x", cases=(
            EvalCase(case_id="c1", inputs={"q": "x"}),
        ))
        runner = EvalRunner(
            program=lambda i: "x",
            eval_fn=lambda c, o: 1.0,
            cost_fn=lambda c, o: 0.05,
        )
        run = runner.run(suite)
        assert run.results[0].cost_usd == pytest.approx(0.05)

    def test_cost_tracker_delta(self):
        # Each program call records into cost tracker; runner reads delta.
        tracker = CostTracker()

        def my_program(inputs):
            tracker.record(operation="x", project="p", cost_usd=0.1)
            return "answer"

        suite = EvalSuite(suite_id="x", cases=(
            EvalCase(case_id="c1", inputs={"q": "x"}),
        ))
        runner = EvalRunner(
            program=my_program,
            eval_fn=lambda c, o: 1.0,
            cost_tracker=tracker,
        )
        run = runner.run(suite)
        assert run.results[0].cost_usd == pytest.approx(0.1)


# --- DriftMonitor -----------------------------------------------------


def _run_with_score(suite_id: str, score: float, *, timestamp: float) -> EvalRun:
    """Build a single-case run with the given mean score + timestamp."""
    return EvalRun.create(
        suite_id=suite_id,
        results=[EvalResult.create(
            case_id="c1", suite_id=suite_id,
            score=score, passed=score >= 0.5, timestamp=timestamp,
        )],
        timestamp=timestamp,
    )


class TestDriftMonitor:
    def test_detect_regression(self):
        monitor = DriftMonitor(baseline_window=3)
        # Three baseline runs at 0.9, 0.85, 0.95.
        monitor.add_run(_run_with_score("bench", 0.9, timestamp=1.0))
        monitor.add_run(_run_with_score("bench", 0.85, timestamp=2.0))
        monitor.add_run(_run_with_score("bench", 0.95, timestamp=3.0))
        # Drop to 0.5 → big regression.
        monitor.add_run(_run_with_score("bench", 0.5, timestamp=4.0))
        alert = monitor.detect_regression(suite_id="bench", threshold=0.1)
        assert alert is not None
        assert alert.is_regression is True
        assert alert.delta < -0.1

    def test_no_regression_when_stable(self):
        monitor = DriftMonitor()
        monitor.add_run(_run_with_score("bench", 0.85, timestamp=1.0))
        monitor.add_run(_run_with_score("bench", 0.85, timestamp=2.0))
        # No alert — 0 delta.
        alert = monitor.detect_regression(suite_id="bench", threshold=0.05)
        assert alert is None

    def test_no_regression_when_only_one_run(self):
        monitor = DriftMonitor()
        monitor.add_run(_run_with_score("bench", 0.5, timestamp=1.0))
        # Need at least 2 runs to compute baseline.
        assert monitor.detect_regression(suite_id="bench") is None

    def test_invalid_threshold(self):
        monitor = DriftMonitor()
        monitor.add_run(_run_with_score("bench", 0.5, timestamp=1.0))
        monitor.add_run(_run_with_score("bench", 0.4, timestamp=2.0))
        with pytest.raises(ValueError):
            monitor.detect_regression(suite_id="bench", threshold=1.5)

    def test_baseline_window_limits(self):
        monitor = DriftMonitor(baseline_window=2)
        # Five baseline runs; only the last 2 (0.9, 0.95) form the baseline.
        monitor.add_run(_run_with_score("bench", 0.1, timestamp=1.0))
        monitor.add_run(_run_with_score("bench", 0.2, timestamp=2.0))
        monitor.add_run(_run_with_score("bench", 0.3, timestamp=3.0))
        monitor.add_run(_run_with_score("bench", 0.9, timestamp=4.0))
        monitor.add_run(_run_with_score("bench", 0.95, timestamp=5.0))
        # Final run drops to 0.5 — baseline of last-2 is (0.9 + 0.95)/2 = 0.925.
        monitor.add_run(_run_with_score("bench", 0.5, timestamp=6.0))
        alert = monitor.detect_regression(suite_id="bench", threshold=0.1)
        assert alert is not None
        assert alert.baseline_mean == pytest.approx(0.925)

    def test_invalid_baseline_window(self):
        with pytest.raises(ValueError):
            DriftMonitor(baseline_window=0)

    def test_detect_improvement(self):
        monitor = DriftMonitor()
        monitor.add_run(_run_with_score("bench", 0.5, timestamp=1.0))
        monitor.add_run(_run_with_score("bench", 0.5, timestamp=2.0))
        monitor.add_run(_run_with_score("bench", 0.9, timestamp=3.0))
        improvement = monitor.detect_improvement(suite_id="bench", threshold=0.1)
        assert improvement is not None
        assert improvement.delta > 0.1

    def test_trend(self):
        monitor = DriftMonitor()
        for i, score in enumerate([0.5, 0.6, 0.7, 0.8]):
            monitor.add_run(_run_with_score("bench", score, timestamp=float(i)))
        trend = monitor.trend("bench", window=3)
        # Last 3, oldest first: 0.6, 0.7, 0.8.
        assert trend == [0.6, 0.7, 0.8]

    def test_summary(self):
        monitor = DriftMonitor()
        monitor.add_run(_run_with_score("bench", 0.5, timestamp=1.0))
        monitor.add_run(_run_with_score("bench", 0.7, timestamp=2.0))
        s = monitor.summary("bench")
        assert s["n_runs"] == 2
        assert s["first_score"] == 0.5
        assert s["latest_score"] == 0.7
        assert s["mean_score"] == pytest.approx(0.6)

    def test_summary_unknown_suite(self):
        s = DriftMonitor().summary("nonexistent")
        assert s["n_runs"] == 0


# --- End-to-end: nightly CI scenario -----------------------------------


class TestNightlyCIScenario:
    """Realistic Polaris-style nightly eval CI: run a suite + record cost +
    detect regressions automatically."""

    def test_nightly_run_then_drift_alert(self):
        # Build a suite + a program that scores by inputs["want"].
        suite = EvalSuite(suite_id="multi-hop-bench", cases=(
            EvalCase(case_id="q1", inputs={"q": "easy"}, expected_output="A"),
            EvalCase(case_id="q2", inputs={"q": "medium"}, expected_output="B"),
            EvalCase(case_id="q3", inputs={"q": "hard"}, expected_output="C"),
        ))
        # Day-1: program is good.
        good_program = lambda inputs: {"easy": "A", "medium": "B", "hard": "C"}[inputs["q"]]
        runner = EvalRunner(program=good_program, eval_fn=_exact_match_eval)
        day1_run = runner.run(suite)
        assert day1_run.pass_rate == 1.0

        monitor = DriftMonitor(baseline_window=3)
        monitor.add_run(day1_run)
        # Days 2 + 3: also good.
        for _ in range(2):
            monitor.add_run(runner.run(suite))

        # Day-4: program degrades on hard cases.
        degraded_program = lambda inputs: {
            "easy": "A", "medium": "B", "hard": "WRONG",
        }[inputs["q"]]
        bad_runner = EvalRunner(program=degraded_program, eval_fn=_exact_match_eval)
        day4_run = bad_runner.run(suite)
        # 2/3 pass-rate; mean_score = 2/3 ≈ 0.667.
        assert day4_run.pass_rate == pytest.approx(2 / 3)
        monitor.add_run(day4_run)

        # Drift detector sees: baseline (1.0, 1.0, 1.0) → current 0.667.
        alert = monitor.detect_regression(
            suite_id="multi-hop-bench", threshold=0.1,
        )
        assert alert is not None
        assert alert.is_regression is True
        assert alert.baseline_mean == pytest.approx(1.0)
        assert alert.current_score == pytest.approx(2 / 3)

    def test_with_cost_tracking(self):
        tracker = CostTracker()

        def expensive_program(inputs):
            tracker.record(
                operation="llm_call", project="polaris",
                cost_usd=0.05,
            )
            return inputs["q"].upper()

        suite = EvalSuite(suite_id="x", cases=tuple(
            EvalCase(case_id=f"c{i}", inputs={"q": "hi"}, expected_output="HI")
            for i in range(3)
        ))
        runner = EvalRunner(
            program=expensive_program,
            eval_fn=_exact_match_eval,
            cost_tracker=tracker,
        )
        run = runner.run(suite)
        # Each case cost $0.05; total $0.15.
        assert run.total_cost_usd == pytest.approx(0.15)
        assert run.pass_rate == 1.0
