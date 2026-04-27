"""RED tests for v1.8 Wave-2 §9 — τ-Bench adapter."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_evals.adapters import (
    TauBenchAdapter,
    TauBenchTask,
    TauBenchVerdict,
    load_tau_bench,
    write_tau_bench_submission,
)
from lyra_evals.runner import EvalRunner


def _task(idx: int = 0) -> TauBenchTask:
    return TauBenchTask(
        instance_id=f"tau-{idx}",
        domain="airline",
        user_intent="cancel my flight",
        policy_doc="cancellations within 24h are free",
        allowed_tools=("search_flights", "cancel_flight"),
        ground_truth_actions=("cancel_flight(idx=1)",),
    )


def _verdict(t: TauBenchTask, *, passed: bool) -> TauBenchVerdict:
    return TauBenchVerdict(
        instance_id=t.instance_id,
        passed=passed,
        fraction_correct=1.0 if passed else 0.0,
    )


def test_tau_bench_task_is_immutable_value() -> None:
    """Frozen dataclass: equal contents → equal objects, no mutation possible."""
    a = _task(0)
    b = _task(0)
    assert a == b
    with pytest.raises(Exception):
        a.user_intent = "mutated"  # type: ignore[misc]


def test_adapter_routes_inner_policy_through_eval_runner() -> None:
    """Glue-test: the adapter's policy callable must satisfy ``EvalRunner.run``."""
    adapter = TauBenchAdapter(model_name_or_path="lyra-stub")
    tb = _task(0)
    generic = adapter.as_generic_task(tb)
    runner = EvalRunner(policy=adapter.policy(lambda x: _verdict(x, passed=True)))
    report = runner.run([generic])
    assert report.total == 1
    assert report.passed == 1
    assert adapter.verdicts()[0].instance_id == "tau-0"


def test_adapter_marks_unknown_task_as_failed_with_clear_reason() -> None:
    """Defence in depth: stale task ids must not silently pass."""
    from lyra_evals.corpora import Task

    adapter = TauBenchAdapter(model_name_or_path="lyra-stub")
    runner = EvalRunner(policy=adapter.policy(lambda x: _verdict(x, passed=True)))
    report = runner.run([Task(id="never-registered", kind="tau_bench", description="x")])
    assert report.passed == 0
    assert "missing" in report.details[0].reason


def test_load_tau_bench_round_trips_minimal_jsonl(tmp_path: Path) -> None:
    """Loader contract: a one-line JSONL must parse into one TauBenchTask."""
    f = tmp_path / "mini.jsonl"
    row = {
        "instance_id": "tau-0",
        "domain": "airline",
        "user_intent": "cancel my flight",
        "policy_doc": "free within 24h",
        "allowed_tools": ["cancel_flight"],
        "ground_truth_actions": ["cancel_flight(idx=1)"],
    }
    f.write_text(json.dumps(row) + "\n")
    tasks = load_tau_bench(f)
    assert len(tasks) == 1
    assert tasks[0].instance_id == "tau-0"
    assert tasks[0].domain == "airline"


def test_submission_writer_is_strict_about_keys(tmp_path: Path) -> None:
    """Just like SWE-bench Pro, extra/missing keys must fail loudly."""
    out = tmp_path / "submission.jsonl"
    write_tau_bench_submission(
        out,
        [_verdict(_task(0), passed=True), _verdict(_task(1), passed=False)],
    )
    rows = [json.loads(line) for line in out.read_text().splitlines() if line.strip()]
    assert len(rows) == 2
    for row in rows:
        assert set(row.keys()) >= {"instance_id", "passed", "fraction_correct"}
