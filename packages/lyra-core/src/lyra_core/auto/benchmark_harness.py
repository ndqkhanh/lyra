"""Phase 4.2b — Unified Benchmarking Harness.

Measures and tracks performance across all 7 Lyra domains:
  Safety, Skills, Memory, Reasoning, Orchestration,
  Evolution, Production

Supports regression detection, trend tracking, and
threshold-based pass/fail gating.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum


class BenchmarkDomain(Enum):
    SAFETY = "safety"
    SKILLS = "skills"
    MEMORY = "memory"
    REASONING = "reasoning"
    ORCHESTRATION = "orchestration"
    EVOLUTION = "evolution"
    PRODUCTION = "production"


class BenchmarkStatus(Enum):
    PASSED = "passed"
    WARNING = "warning"       # Below threshold but above floor
    FAILED = "failed"         # Below floor
    REGRESSION = "regression"  # Was passing, now below threshold


@dataclass(frozen=True)
class BenchmarkResult:
    """Result from a single benchmark run."""

    domain: BenchmarkDomain
    metric_name: str
    score: float                       # 0.0–1.0 or raw
    threshold: float                   # Minimum acceptable
    baseline: float | None             # Historical baseline
    status: BenchmarkStatus
    unit: str                          # "%", "ms", "count", etc.
    metadata: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class BenchmarkRun:
    """A complete benchmark run across all domains."""

    run_id: str
    results: tuple[BenchmarkResult, ...]
    overall_score: float               # Weighted average across domains
    passed: bool                       # All critical domains pass
    domains_covered: int
    timestamp: float
    summary: str


_DOMAIN_WEIGHTS: dict[BenchmarkDomain, float] = {
    BenchmarkDomain.SAFETY: 2.0,
    BenchmarkDomain.SKILLS: 1.5,
    BenchmarkDomain.MEMORY: 1.5,
    BenchmarkDomain.REASONING: 1.5,
    BenchmarkDomain.ORCHESTRATION: 1.0,
    BenchmarkDomain.EVOLUTION: 1.0,
    BenchmarkDomain.PRODUCTION: 1.0,
}


@dataclass
class BenchmarkHarness:
    """Unified benchmarking across all Lyra domains.

    Usage::

        harness = BenchmarkHarness()
        harness.register("safety", "block_rate", lambda: 0.989, threshold=0.95)
        harness.register("skills", "pass_rate", lambda: 0.92, threshold=0.80)
        run = harness.run_all()
        print(f"Overall: {run.overall_score:.2f}")
    """

    _metrics: dict[str, dict[str, Callable[[], float]]] = field(default_factory=dict)
    _thresholds: dict[str, float] = field(default_factory=dict)
    _baselines: dict[str, float] = field(default_factory=dict)
    _history: list[BenchmarkRun] = field(default_factory=list)
    regression_threshold: float = 0.05

    def register(
        self,
        domain: str,
        metric_name: str,
        runner: Callable[[], float],
        *,
        threshold: float = 0.8,
        baseline: float | None = None,
    ) -> None:
        """Register a benchmark metric.

        Args:
            domain: Domain name (e.g., "safety", "skills").
            metric_name: Human-readable metric name.
            runner: Callable that returns the metric score.
            threshold: Minimum acceptable score.
            baseline: Historical baseline for regression detection.
        """
        self._metrics.setdefault(domain, {})[metric_name] = runner
        key = f"{domain}:{metric_name}"
        self._thresholds[key] = threshold
        if baseline is not None:
            self._baselines[key] = baseline

    def run_all(self) -> BenchmarkRun:
        """Run all registered benchmarks and produce a report.

        Returns:
            BenchmarkRun with per-metric results and overall score.
        """
        results: list[BenchmarkResult] = []
        domains_covered = 0
        total_weight = 0.0
        weighted_sum = 0.0

        for domain_str, metrics in self._metrics.items():
            try:
                domain = BenchmarkDomain(domain_str)
            except ValueError:
                continue

            domains_covered += 1
            weight = _DOMAIN_WEIGHTS.get(domain, 1.0)

            for name, runner in metrics.items():
                try:
                    score = runner()
                except Exception:
                    score = 0.0

                key = f"{domain_str}:{name}"
                threshold = self._thresholds.get(key, 0.8)
                baseline = self._baselines.get(key)

                if baseline is not None and score < baseline - self.regression_threshold:
                    status = BenchmarkStatus.REGRESSION
                elif score >= threshold:
                    status = BenchmarkStatus.PASSED
                elif score >= threshold * 0.7:
                    status = BenchmarkStatus.WARNING
                else:
                    status = BenchmarkStatus.FAILED

                results.append(BenchmarkResult(
                    domain=domain,
                    metric_name=name,
                    score=round(score, 4),
                    threshold=threshold,
                    baseline=baseline,
                    status=status,
                    unit="score",
                    metadata=(),
                ))
                weighted_sum += score * weight
                total_weight += weight

        overall = round(weighted_sum / max(total_weight, 0.001), 4)
        critical_passed = all(
            r.status != BenchmarkStatus.FAILED
            for r in results
            if r.domain == BenchmarkDomain.SAFETY
        )

        passed_count = sum(1 for r in results if r.status == BenchmarkStatus.PASSED)
        summary = (
            f"{passed_count}/{len(results)} metrics passed, "
            f"overall={overall:.3f}, safety={'OK' if critical_passed else 'FAIL'}"
        )

        run = BenchmarkRun(
            run_id=f"br-{uuid.uuid4().hex[:12]}",
            results=tuple(results),
            overall_score=overall,
            passed=critical_passed,
            domains_covered=domains_covered,
            timestamp=time.time(),
            summary=summary,
        )
        self._history.append(run)
        return run

    def set_baseline(self) -> None:
        """Snapshot current scores as baselines for regression detection."""
        for domain_str, metrics in self._metrics.items():
            for name, runner in metrics.items():
                try:
                    score = runner()
                    self._baselines[f"{domain_str}:{name}"] = score
                except Exception:
                    pass

    def check_regressions(self) -> tuple[BenchmarkResult, ...]:
        """Run benchmarks and return only regressions/warnings."""
        run = self.run_all()
        return tuple(
            r for r in run.results
            if r.status in (BenchmarkStatus.REGRESSION, BenchmarkStatus.FAILED)
        )

    def get_domain_score(self, domain: BenchmarkDomain) -> float | None:
        """Get the latest score for a domain."""
        if not self._history:
            return None
        last = self._history[-1]
        domain_results = [r for r in last.results if r.domain == domain]
        if not domain_results:
            return None
        return sum(r.score for r in domain_results) / len(domain_results)

    @property
    def history(self) -> tuple[BenchmarkRun, ...]:
        return tuple(self._history)

    @property
    def metric_count(self) -> int:
        return sum(len(m) for m in self._metrics.values())

    def clear_history(self) -> None:
        self._history.clear()


__all__ = [
    "BenchmarkDomain",
    "BenchmarkHarness",
    "BenchmarkResult",
    "BenchmarkRun",
    "BenchmarkStatus",
]
