"""EvalRunner — execute a suite against a program; record per-case results."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..cost import CostTracker
from .types import EvalCase, EvalResult, EvalRun, EvalSuite


_ProgramFn = Callable[[dict[str, Any]], Any]
_EvalFn = Callable[[EvalCase, Any], float]
_CostFn = Callable[[EvalCase, Any], float]


@dataclass
class EvalRunner:
    """Run a suite against a callable program; record typed results.

    ``program(inputs) -> output`` is the thing being evaluated.
    ``eval_fn(case, output) -> score`` returns a score in [0, 1].
    Optional ``cost_fn(case, output) -> cost_usd`` records per-case cost
    (otherwise the runner reads from ``cost_tracker.total()`` deltas).

    >>> def my_program(inputs):
    ...     return inputs.get("q", "").upper()
    >>> def my_eval(case, output):
    ...     return 1.0 if output == case.expected_output else 0.0
    >>> from harness_core.eval_runner import EvalCase, EvalSuite
    >>> suite = EvalSuite(
    ...     suite_id="upper",
    ...     cases=(
    ...         EvalCase(case_id="c1", inputs={"q": "hi"}, expected_output="HI"),
    ...     ),
    ... )
    >>> runner = EvalRunner(program=my_program, eval_fn=my_eval)
    >>> run = runner.run(suite)
    >>> run.pass_rate
    1.0
    """

    program: _ProgramFn
    eval_fn: _EvalFn
    cost_tracker: Optional[CostTracker] = None
    cost_fn: Optional[_CostFn] = None
    pass_threshold: float = 0.5  # score >= threshold → passed
    max_cases: Optional[int] = None  # cap suite size when set

    def __post_init__(self) -> None:
        if not 0.0 <= self.pass_threshold <= 1.0:
            raise ValueError(
                f"pass_threshold must be in [0, 1], got {self.pass_threshold}"
            )

    def run(self, suite: EvalSuite, *, run_metadata: Optional[dict] = None) -> EvalRun:
        """Execute the suite; return an :class:`EvalRun` with all results."""
        results: list[EvalResult] = []
        cases = suite.cases
        if self.max_cases is not None:
            cases = cases[: self.max_cases]

        for case in cases:
            result = self._run_case(case=case, suite_id=suite.suite_id)
            results.append(result)

        return EvalRun.create(
            suite_id=suite.suite_id,
            results=results,
            metadata=run_metadata or {},
        )

    def _run_case(self, *, case: EvalCase, suite_id: str) -> EvalResult:
        start = time.time()
        cost_before = (
            self.cost_tracker.total() if self.cost_tracker is not None else 0.0
        )

        try:
            output = self.program(case.inputs)
        except Exception as exc:
            duration_ms = (time.time() - start) * 1000.0
            return EvalResult.create(
                case_id=case.case_id,
                suite_id=suite_id,
                score=0.0,
                passed=False,
                actual_output=None,
                cost_usd=0.0,
                duration_ms=duration_ms,
                error=f"program raised {exc.__class__.__name__}: {exc}",
                weight=case.weight,
            )

        try:
            score = self.eval_fn(case, output)
        except Exception as exc:
            duration_ms = (time.time() - start) * 1000.0
            return EvalResult.create(
                case_id=case.case_id,
                suite_id=suite_id,
                score=0.0,
                passed=False,
                actual_output=output,
                cost_usd=0.0,
                duration_ms=duration_ms,
                error=f"eval_fn raised {exc.__class__.__name__}: {exc}",
                weight=case.weight,
            )

        if not 0.0 <= score <= 1.0:
            duration_ms = (time.time() - start) * 1000.0
            return EvalResult.create(
                case_id=case.case_id,
                suite_id=suite_id,
                score=0.0,
                passed=False,
                actual_output=output,
                cost_usd=0.0,
                duration_ms=duration_ms,
                error=f"eval_fn returned out-of-range score: {score}",
                weight=case.weight,
            )

        # Cost: prefer explicit cost_fn; fall back to tracker delta; else zero.
        cost_usd = 0.0
        if self.cost_fn is not None:
            try:
                cost_usd = float(self.cost_fn(case, output))
            except Exception:
                cost_usd = 0.0
        elif self.cost_tracker is not None:
            cost_usd = self.cost_tracker.total() - cost_before

        duration_ms = (time.time() - start) * 1000.0
        passed = score >= self.pass_threshold
        return EvalResult.create(
            case_id=case.case_id,
            suite_id=suite_id,
            score=score,
            passed=passed,
            actual_output=output,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            weight=case.weight,
        )


__all__ = ["EvalRunner"]
