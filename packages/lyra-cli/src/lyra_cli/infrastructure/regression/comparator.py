"""Benchmark run comparator — identifies regressions between two benchmark runs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ComparisonVerdict(StrEnum):
    IMPROVED = "improved"
    REGRESSED = "regressed"
    STABLE = "stable"
    NEW = "new"
    REMOVED = "removed"


@dataclass(frozen=True)
class MetricComparison:
    metric_name: str
    baseline_value: float
    current_value: float
    delta_pct: float
    verdict: ComparisonVerdict
    severity: str = ""  # critical, warning, info


@dataclass(frozen=True)
class BenchmarkComparisonResult:
    baseline_name: str
    current_name: str
    comparisons: tuple[MetricComparison, ...]
    overall_verdict: ComparisonVerdict
    regression_count: int
    improvement_count: int
    stable_count: int
    summary: str = ""


class BenchmarkComparator:
    """Compares two benchmark runs and identifies regressions.

    Usage::

        comp = BenchmarkComparator()
        result = comp.compare("v1.0", "v1.1", baseline_metrics, current_metrics)
        for mc in result.comparisons:
            if mc.verdict == ComparisonVerdict.REGRESSED:
                print(f"Regression: {mc.metric_name} ({mc.delta_pct:+.1f}%)")
    """

    def __init__(
        self,
        regression_threshold_pct: float = 5.0,
        improvement_threshold_pct: float = 1.0,
        lower_is_better: set[str] | None = None,
    ) -> None:
        self._regression_threshold = regression_threshold_pct
        self._improvement_threshold = improvement_threshold_pct
        self._lower_is_better = lower_is_better or set()

    def compare(
        self,
        baseline_name: str,
        current_name: str,
        baseline_metrics: dict[str, float],
        current_metrics: dict[str, float],
    ) -> BenchmarkComparisonResult:
        comparisons: list[MetricComparison] = []
        regression_count = 0
        improvement_count = 0
        stable_count = 0

        all_keys = set(baseline_metrics) | set(current_metrics)
        for key in sorted(all_keys):
            base_val = baseline_metrics.get(key)
            curr_val = current_metrics.get(key)

            if base_val is None:
                comparisons.append(
                    MetricComparison(
                        metric_name=key,
                        baseline_value=0.0,
                        current_value=curr_val or 0.0,
                        delta_pct=100.0,
                        verdict=ComparisonVerdict.NEW,
                    )
                )
                continue
            if curr_val is None:
                comparisons.append(
                    MetricComparison(
                        metric_name=key,
                        baseline_value=base_val,
                        current_value=0.0,
                        delta_pct=-100.0,
                        verdict=ComparisonVerdict.REMOVED,
                    )
                )
                continue

            delta_pct = ((curr_val - base_val) / base_val * 100.0) if base_val != 0 else 0.0
            lower_better = key in self._lower_is_better

            regression_pct = delta_pct if lower_better else -delta_pct
            improvement_pct = -delta_pct if lower_better else delta_pct

            if regression_pct >= self._regression_threshold:
                severity = (
                    "critical" if regression_pct >= 20.0
                    else "warning" if regression_pct >= 10.0
                    else "info"
                )
                verdict = ComparisonVerdict.REGRESSED
                regression_count += 1
            elif improvement_pct >= self._improvement_threshold:
                severity = ""
                verdict = ComparisonVerdict.IMPROVED
                improvement_count += 1
            else:
                severity = ""
                verdict = ComparisonVerdict.STABLE
                stable_count += 1

            comparisons.append(
                MetricComparison(
                    metric_name=key,
                    baseline_value=base_val,
                    current_value=curr_val,
                    delta_pct=round(delta_pct, 2),
                    verdict=verdict,
                    severity=severity,
                )
            )

        overall = ComparisonVerdict.STABLE
        if regression_count > 0:
            overall = ComparisonVerdict.REGRESSED
        elif improvement_count > len(comparisons) * 0.5 and stable_count < improvement_count:
            overall = ComparisonVerdict.IMPROVED

        return BenchmarkComparisonResult(
            baseline_name=baseline_name,
            current_name=current_name,
            comparisons=tuple(comparisons),
            overall_verdict=overall,
            regression_count=regression_count,
            improvement_count=improvement_count,
            stable_count=stable_count,
            summary=self._build_summary(regression_count, improvement_count, stable_count),
        )

    @staticmethod
    def _build_summary(reg: int, imp: int, stable: int) -> str:
        parts = []
        if reg:
            parts.append(f"{reg} regressed")
        if imp:
            parts.append(f"{imp} improved")
        if stable:
            parts.append(f"{stable} stable")
        return ", ".join(parts) if parts else "no changes"
