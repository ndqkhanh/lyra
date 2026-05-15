"""Eval-runner data types — EvalCase, EvalResult, EvalSuite, EvalRun."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class EvalCase:
    """One test case in a suite — inputs + expected output + metadata."""

    case_id: str
    inputs: dict[str, Any]
    expected_output: Any = None  # may be None for free-form eval functions
    metadata: dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0

    def __post_init__(self) -> None:
        if not self.case_id:
            raise ValueError("case_id must be non-empty")
        if not self.inputs:
            raise ValueError("inputs must be non-empty")
        if self.weight < 0:
            raise ValueError(f"weight must be >= 0, got {self.weight}")


@dataclass(frozen=True)
class EvalResult:
    """One case's evaluation outcome."""

    result_id: str
    case_id: str
    suite_id: str
    timestamp: float
    score: float  # in [0, 1]
    passed: bool
    actual_output: Any = None
    cost_usd: float = 0.0
    duration_ms: float = 0.0
    error: str = ""
    weight: float = 1.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0, 1], got {self.score}")
        if self.cost_usd < 0:
            raise ValueError(f"cost_usd must be >= 0, got {self.cost_usd}")
        if self.duration_ms < 0:
            raise ValueError(f"duration_ms must be >= 0, got {self.duration_ms}")
        if self.weight < 0:
            raise ValueError(f"weight must be >= 0, got {self.weight}")

    @classmethod
    def create(
        cls,
        *,
        case_id: str,
        suite_id: str,
        score: float,
        passed: bool,
        actual_output: Any = None,
        cost_usd: float = 0.0,
        duration_ms: float = 0.0,
        error: str = "",
        weight: float = 1.0,
        timestamp: Optional[float] = None,
        result_id: Optional[str] = None,
    ) -> "EvalResult":
        return cls(
            result_id=result_id or str(uuid.uuid4()),
            case_id=case_id,
            suite_id=suite_id,
            timestamp=timestamp if timestamp is not None else time.time(),
            score=score,
            passed=passed,
            actual_output=actual_output,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            error=error,
            weight=weight,
        )


@dataclass(frozen=True)
class EvalSuite:
    """A named collection of evaluation cases.

    >>> suite = EvalSuite(
    ...     suite_id="multi-hop-bench",
    ...     cases=(
    ...         EvalCase(case_id="c1", inputs={"q": "X"}, expected_output="Y"),
    ...     ),
    ... )
    >>> suite.suite_id
    'multi-hop-bench'
    """

    suite_id: str
    cases: tuple[EvalCase, ...]
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.suite_id:
            raise ValueError("suite_id must be non-empty")
        if not self.cases:
            raise ValueError("suite must have at least one case")
        # Detect duplicate case_ids.
        seen: set[str] = set()
        for c in self.cases:
            if c.case_id in seen:
                raise ValueError(f"duplicate case_id: {c.case_id!r}")
            seen.add(c.case_id)

    def __len__(self) -> int:
        return len(self.cases)


@dataclass(frozen=True)
class EvalRun:
    """A complete run of a suite — all results + aggregate metrics."""

    run_id: str
    suite_id: str
    timestamp: float
    results: tuple[EvalResult, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("run_id must be non-empty")
        if not self.suite_id:
            raise ValueError("suite_id must be non-empty")

    @property
    def pass_rate(self) -> float:
        """Weighted pass rate (passed cases / total weight)."""
        if not self.results:
            return 0.0
        total_weight = sum(r.weight for r in self.results)
        if total_weight == 0:
            return 0.0
        passed_weight = sum(r.weight for r in self.results if r.passed)
        return passed_weight / total_weight

    @property
    def mean_score(self) -> float:
        """Weighted mean score across results."""
        if not self.results:
            return 0.0
        total_weight = sum(r.weight for r in self.results)
        if total_weight == 0:
            return 0.0
        weighted_sum = sum(r.score * r.weight for r in self.results)
        return weighted_sum / total_weight

    @property
    def total_cost_usd(self) -> float:
        return sum(r.cost_usd for r in self.results)

    @property
    def total_duration_ms(self) -> float:
        return sum(r.duration_ms for r in self.results)

    @property
    def n_passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def n_failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def n_errors(self) -> int:
        return sum(1 for r in self.results if r.error)

    def failed_cases(self) -> list[EvalResult]:
        return [r for r in self.results if not r.passed]

    @classmethod
    def create(
        cls,
        *,
        suite_id: str,
        results: tuple[EvalResult, ...] | list[EvalResult],
        metadata: Optional[dict[str, Any]] = None,
        run_id: Optional[str] = None,
        timestamp: Optional[float] = None,
    ) -> "EvalRun":
        return cls(
            run_id=run_id or str(uuid.uuid4()),
            suite_id=suite_id,
            timestamp=timestamp if timestamp is not None else time.time(),
            results=tuple(results),
            metadata=dict(metadata or {}),
        )


__all__ = ["EvalCase", "EvalResult", "EvalRun", "EvalSuite"]
