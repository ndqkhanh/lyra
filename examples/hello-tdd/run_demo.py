"""End-to-end driver for the hello-tdd example.

Shows four Lyra primitives without any LLM call:
    1. RedProof validation (a fake failing pytest result).
    2. Impact map for an edited source file.
    3. Coverage-regression gate with tolerance.
    4. Eval runner over the golden corpus with a stub policy.

Run from the `projects/lyra/` directory:
    python examples/hello-tdd/run_demo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from lyra_core.tdd.coverage import CoverageDelta, check_coverage_delta
from lyra_core.tdd.impact_map import tests_for_edit
from lyra_core.tdd.red_proof import RedProof, validate_red_proof
from lyra_evals import EvalRunner, Task, TaskResult, golden_tasks


HERE = Path(__file__).parent.resolve()


def step_red_proof() -> None:
    test_file = HERE / "tests" / "test_greet.py"
    proof = RedProof(
        test_id="tests/test_greet.py::test_refuses_empty_name",
        status="failed",
        exit_code=1,
        duration_ms=12,
        stderr="AssertionError: empty-name check missing",
    )
    validate_red_proof(proof, repo_root=HERE)
    print("[1/4] RedProof validated            ok")
    assert test_file.exists(), test_file


def step_impact_map() -> None:
    edited = HERE / "src" / "greet" / "__init__.py"
    hits = tests_for_edit(edited, repo_root=HERE)
    rel = sorted(str(p.relative_to(HERE)) for p in hits)
    print(f"[2/4] Impact map for greet/__init__.py -> {rel}")
    assert any(str(p).endswith("test_greet.py") for p in hits), hits


def step_coverage_gate() -> None:
    delta = CoverageDelta(before=71.0, after=72.5, tolerance_pct=1.0)
    check_coverage_delta(delta)
    print(
        f"[3/4] Coverage delta {delta.before}% -> {delta.after}%  "
        f"(tolerance {delta.tolerance_pct}%)   ok"
    )


def step_evals() -> None:
    def _pass(task: Task) -> TaskResult:
        return TaskResult(task_id=task.id, passed=True, reason="hello-tdd stub")

    runner = EvalRunner(policy=_pass, drift_gate=0.85)
    report = runner.run(golden_tasks())
    print(
        f"[4/4] Golden-corpus smoke            "
        f"success_rate={report.success_rate:.2f}  "
        f"drift_gate_tripped={report.drift_gate_tripped}"
    )


def main() -> int:
    try:
        step_red_proof()
        step_impact_map()
        step_coverage_gate()
        step_evals()
    except Exception as e:
        print(f"demo failed: {e!r}", file=sys.stderr)
        return 1
    print("hello-tdd demo passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
