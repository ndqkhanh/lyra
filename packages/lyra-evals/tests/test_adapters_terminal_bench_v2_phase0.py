"""RED tests for v1.8 Wave-2 §9 — Terminal-Bench 2.0 adapter."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_evals.adapters import (
    TerminalBenchTaskV2,
    TerminalBenchV2Adapter,
    TerminalBenchVerdict,
    load_terminal_bench_v2,
    write_terminal_bench_v2_submission,
)
from lyra_evals.runner import EvalRunner


def _task(idx: int = 0) -> TerminalBenchTaskV2:
    return TerminalBenchTaskV2(
        task_id=f"tb2-{idx}",
        description="install ripgrep and grep for TODO",
        initial_filesystem="seed://empty",
        checker_command='test -f /tmp/output.txt && grep -q "found" /tmp/output.txt',
        time_limit_s=120.0,
    )


def _verdict(t: TerminalBenchTaskV2, *, passed: bool) -> TerminalBenchVerdict:
    return TerminalBenchVerdict(
        task_id=t.task_id,
        passed=passed,
        wall_clock_s=42.0,
        exit_code=0 if passed else 1,
    )


def test_terminal_bench_task_is_immutable_value() -> None:
    a = _task(0)
    b = _task(0)
    assert a == b
    with pytest.raises(Exception):
        a.task_id = "mutated"  # type: ignore[misc]


def test_adapter_preserves_default_offline_mode() -> None:
    """Most Terminal-Bench 2.0 tasks are offline; the default reflects that."""
    t = _task(0)
    assert t.allowed_network is False


def test_adapter_routes_inner_policy_through_eval_runner() -> None:
    adapter = TerminalBenchV2Adapter(model_name_or_path="lyra-stub")
    tb = _task(0)
    generic = adapter.as_generic_task(tb)
    runner = EvalRunner(policy=adapter.policy(lambda x: _verdict(x, passed=True)))
    report = runner.run([generic])
    assert report.passed == 1
    assert adapter.verdicts()[0].task_id == "tb2-0"


def test_load_terminal_bench_round_trips_minimal_jsonl(tmp_path: Path) -> None:
    f = tmp_path / "mini.jsonl"
    row = {
        "task_id": "tb2-0",
        "description": "x",
        "initial_filesystem": "seed://empty",
        "checker_command": "true",
        "time_limit_s": 30.0,
    }
    f.write_text(json.dumps(row) + "\n")
    tasks = load_terminal_bench_v2(f)
    assert len(tasks) == 1
    assert tasks[0].task_id == "tb2-0"


def test_submission_writer_emits_one_row_per_verdict(tmp_path: Path) -> None:
    out = tmp_path / "submission.jsonl"
    write_terminal_bench_v2_submission(
        out,
        [_verdict(_task(0), passed=True), _verdict(_task(1), passed=False)],
    )
    rows = [json.loads(line) for line in out.read_text().splitlines() if line.strip()]
    assert len(rows) == 2
    for row in rows:
        assert "task_id" in row and "passed" in row and "wall_clock_s" in row
