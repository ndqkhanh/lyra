"""
Skill Evaluator - Performance metrics, A/B testing, and quality scoring.

Implements comprehensive skill evaluation with:
- Performance metrics (success rate, latency, token efficiency)
- A/B testing framework for skill comparison
- Quality scoring with multiple dimensions
- Benchmark integration
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class MetricType(StrEnum):
    """Types of metrics tracked."""

    SUCCESS_RATE = "success_rate"
    AVG_LATENCY_MS = "avg_latency_ms"
    TOKEN_EFFICIENCY = "token_efficiency"
    USER_RATING = "user_rating"
    BENCHMARK_SCORE = "benchmark_score"


class QualityDimension(StrEnum):
    """Dimensions of skill quality."""

    CORRECTNESS = "correctness"  # Produces correct outputs
    EFFICIENCY = "efficiency"  # Token/latency efficient
    ROBUSTNESS = "robustness"  # Works across diverse inputs
    GENERALITY = "generality"  # Transfers to unseen tasks


@dataclass
class SkillExecution:
    """Record of a single skill execution."""

    execution_id: str
    skill_name: str
    timestamp: str
    success: bool
    latency_ms: float
    tokens_used: int
    error_message: str | None = None
    user_rating: float | None = None  # 0.0-1.0


@dataclass
class PerformanceMetrics:
    """Performance metrics for a skill."""

    skill_name: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    avg_tokens_used: float
    token_efficiency: float  # success per 1k tokens
    avg_user_rating: float
    last_updated: str


@dataclass
class QualityScore:
    """Multi-dimensional quality score."""

    skill_name: str
    correctness: float  # 0.0-1.0
    efficiency: float  # 0.0-1.0
    robustness: float  # 0.0-1.0
    generality: float  # 0.0-1.0
    composite_score: float  # Weighted average
    confidence: float  # Statistical confidence (0.0-1.0)
    sample_size: int


@dataclass
class ABTestResult:
    """Result of A/B test between two skills."""

    skill_a: str
    skill_b: str
    metric: MetricType
    skill_a_value: float
    skill_b_value: float
    improvement_pct: float
    p_value: float
    is_significant: bool  # p < 0.05
    sample_size_a: int
    sample_size_b: int
    winner: str | None


class SkillEvaluator:
    """
    Comprehensive skill evaluation system.

    Features:
    - Track execution metrics (success, latency, tokens)
    - Calculate performance statistics
    - Multi-dimensional quality scoring
    - A/B testing framework
    - Benchmark integration
    """

    def __init__(self):
        # Execution history: {skill_name: [executions]}
        self._executions: dict[str, list[SkillExecution]] = {}

        # Quality scores cache
        self._quality_scores: dict[str, QualityScore] = {}

        # Quality dimension weights
        self._quality_weights = {
            QualityDimension.CORRECTNESS: 0.35,
            QualityDimension.EFFICIENCY: 0.25,
            QualityDimension.ROBUSTNESS: 0.25,
            QualityDimension.GENERALITY: 0.15,
        }

    def record_execution(self, execution: SkillExecution) -> None:
        """Record a skill execution."""
        if execution.skill_name not in self._executions:
            self._executions[execution.skill_name] = []

        self._executions[execution.skill_name].append(execution)

        # Invalidate quality score cache
        if execution.skill_name in self._quality_scores:
            del self._quality_scores[execution.skill_name]

    def get_performance_metrics(self, skill_name: str) -> PerformanceMetrics | None:
        """
        Calculate performance metrics for a skill.

        Args:
            skill_name: Name of the skill

        Returns:
            PerformanceMetrics or None if no executions
        """
        if skill_name not in self._executions:
            return None

        executions = self._executions[skill_name]
        if not executions:
            return None

        successful = [e for e in executions if e.success]
        failed = [e for e in executions if not e.success]

        # Latency percentiles
        latencies = [e.latency_ms for e in executions]
        latencies.sort()

        def percentile(data: list[float], p: float) -> float:
            if not data:
                return 0.0
            k = (len(data) - 1) * p
            f = int(k)
            c = f + 1
            if c >= len(data):
                return data[-1]
            return data[f] + (k - f) * (data[c] - data[f])

        # Token efficiency: successes per 1k tokens
        total_tokens = sum(e.tokens_used for e in executions)
        token_efficiency = (
            (len(successful) / (total_tokens / 1000.0)) if total_tokens > 0 else 0.0
        )

        # User ratings
        ratings = [e.user_rating for e in executions if e.user_rating is not None]
        avg_rating = statistics.mean(ratings) if ratings else 0.0

        return PerformanceMetrics(
            skill_name=skill_name,
            total_executions=len(executions),
            successful_executions=len(successful),
            failed_executions=len(failed),
            success_rate=len(successful) / len(executions),
            avg_latency_ms=statistics.mean(latencies),
            p50_latency_ms=percentile(latencies, 0.50),
            p95_latency_ms=percentile(latencies, 0.95),
            p99_latency_ms=percentile(latencies, 0.99),
            avg_tokens_used=statistics.mean([e.tokens_used for e in executions]),
            token_efficiency=token_efficiency,
            avg_user_rating=avg_rating,
            last_updated=datetime.now().isoformat(),
        )

    def calculate_quality_score(
        self,
        skill_name: str,
        benchmark_results: dict[str, float] | None = None,
    ) -> QualityScore | None:
        """
        Calculate multi-dimensional quality score.

        Args:
            skill_name: Name of the skill
            benchmark_results: Optional benchmark scores

        Returns:
            QualityScore or None if insufficient data
        """
        # Check cache
        if skill_name in self._quality_scores:
            return self._quality_scores[skill_name]

        metrics = self.get_performance_metrics(skill_name)
        if not metrics or metrics.total_executions < 5:
            return None  # Need at least 5 executions

        # Correctness: success rate
        correctness = metrics.success_rate

        # Efficiency: normalized by baseline (500ms, 1000 tokens)
        baseline_latency = 500.0
        baseline_tokens = 1000.0
        latency_score = min(1.0, baseline_latency / max(metrics.avg_latency_ms, 1.0))
        token_score = min(1.0, baseline_tokens / max(metrics.avg_tokens_used, 1.0))
        efficiency = (latency_score + token_score) / 2.0

        # Robustness: consistency across executions (inverse of variance)
        executions = self._executions[skill_name]
        success_values = [1.0 if e.success else 0.0 for e in executions]
        if len(success_values) > 1:
            variance = statistics.variance(success_values)
            robustness = 1.0 - min(variance, 1.0)
        else:
            robustness = correctness

        # Generality: from benchmark results or user ratings
        if benchmark_results:
            generality = statistics.mean(benchmark_results.values())
        else:
            generality = metrics.avg_user_rating if metrics.avg_user_rating > 0 else 0.5

        # Composite score (weighted average)
        composite = (
            correctness * self._quality_weights[QualityDimension.CORRECTNESS]
            + efficiency * self._quality_weights[QualityDimension.EFFICIENCY]
            + robustness * self._quality_weights[QualityDimension.ROBUSTNESS]
            + generality * self._quality_weights[QualityDimension.GENERALITY]
        )

        # Statistical confidence based on sample size
        confidence = min(1.0, metrics.total_executions / 50.0)

        score = QualityScore(
            skill_name=skill_name,
            correctness=correctness,
            efficiency=efficiency,
            robustness=robustness,
            generality=generality,
            composite_score=composite,
            confidence=confidence,
            sample_size=metrics.total_executions,
        )

        # Cache the score
        self._quality_scores[skill_name] = score

        return score

    def compare_skills(
        self,
        skill_a: str,
        skill_b: str,
        metric: MetricType = MetricType.SUCCESS_RATE,
    ) -> ABTestResult | None:
        """
        Compare two skills using A/B testing.

        Args:
            skill_a: First skill name
            skill_b: Second skill name
            metric: Metric to compare

        Returns:
            ABTestResult or None if insufficient data
        """
        metrics_a = self.get_performance_metrics(skill_a)
        metrics_b = self.get_performance_metrics(skill_b)

        if not metrics_a or not metrics_b:
            return None

        # Get metric values
        if metric == MetricType.SUCCESS_RATE:
            value_a = metrics_a.success_rate
            value_b = metrics_b.success_rate
        elif metric == MetricType.AVG_LATENCY_MS:
            value_a = metrics_a.avg_latency_ms
            value_b = metrics_b.avg_latency_ms
        elif metric == MetricType.TOKEN_EFFICIENCY:
            value_a = metrics_a.token_efficiency
            value_b = metrics_b.token_efficiency
        elif metric == MetricType.USER_RATING:
            value_a = metrics_a.avg_user_rating
            value_b = metrics_b.avg_user_rating
        else:
            return None

        # Calculate improvement
        if value_b > 0:
            improvement_pct = ((value_a - value_b) / value_b) * 100.0
        else:
            improvement_pct = 0.0

        # Simple statistical test (t-test approximation)
        # For production, use scipy.stats.ttest_ind
        sample_size_a = metrics_a.total_executions
        sample_size_b = metrics_b.total_executions

        # Simplified p-value calculation
        # In production, use proper statistical test
        diff = abs(value_a - value_b)
        pooled_std = (value_a + value_b) / 2.0 * 0.1  # Rough estimate
        if pooled_std > 0:
            z_score = diff / pooled_std
            # Rough p-value approximation
            p_value = max(0.001, 1.0 / (1.0 + z_score**2))
        else:
            p_value = 1.0

        is_significant = p_value < 0.05

        # Determine winner (based on observed difference, regardless of statistical significance)
        if metric == MetricType.AVG_LATENCY_MS:
            # Lower is better for latency
            winner = skill_a if value_a < value_b else skill_b
        else:
            # Higher is better for other metrics
            winner = skill_a if value_a > value_b else skill_b

        return ABTestResult(
            skill_a=skill_a,
            skill_b=skill_b,
            metric=metric,
            skill_a_value=value_a,
            skill_b_value=value_b,
            improvement_pct=improvement_pct,
            p_value=p_value,
            is_significant=is_significant,
            sample_size_a=sample_size_a,
            sample_size_b=sample_size_b,
            winner=winner,
        )

    def get_top_skills(
        self,
        metric: MetricType = MetricType.SUCCESS_RATE,
        limit: int = 10,
        min_executions: int = 5,
    ) -> list[tuple[str, float]]:
        """
        Get top-performing skills by metric.

        Args:
            metric: Metric to rank by
            limit: Maximum number of skills to return
            min_executions: Minimum executions required

        Returns:
            List of (skill_name, metric_value) tuples
        """
        results = []

        for skill_name in self._executions.keys():
            metrics = self.get_performance_metrics(skill_name)
            if not metrics or metrics.total_executions < min_executions:
                continue

            if metric == MetricType.SUCCESS_RATE:
                value = metrics.success_rate
            elif metric == MetricType.AVG_LATENCY_MS:
                value = metrics.avg_latency_ms
            elif metric == MetricType.TOKEN_EFFICIENCY:
                value = metrics.token_efficiency
            elif metric == MetricType.USER_RATING:
                value = metrics.avg_user_rating
            else:
                continue

            results.append((skill_name, value))

        # Sort by value
        if metric == MetricType.AVG_LATENCY_MS:
            # Lower is better for latency
            results.sort(key=lambda x: x[1])
        else:
            # Higher is better for other metrics
            results.sort(key=lambda x: x[1], reverse=True)

        return results[:limit]

    def get_skills_needing_improvement(
        self,
        threshold: float = 0.7,
        min_executions: int = 10,
    ) -> list[tuple[str, QualityScore]]:
        """
        Identify skills that need improvement.

        Args:
            threshold: Quality score threshold
            min_executions: Minimum executions required

        Returns:
            List of (skill_name, quality_score) tuples
        """
        results = []

        for skill_name in self._executions.keys():
            metrics = self.get_performance_metrics(skill_name)
            if not metrics or metrics.total_executions < min_executions:
                continue

            quality = self.calculate_quality_score(skill_name)
            if quality and quality.composite_score < threshold:
                results.append((skill_name, quality))

        # Sort by composite score (worst first)
        results.sort(key=lambda x: x[1].composite_score)

        return results

    def generate_report(self, skill_name: str) -> dict:
        """
        Generate comprehensive evaluation report for a skill.

        Args:
            skill_name: Name of the skill

        Returns:
            Dictionary with all evaluation data
        """
        metrics = self.get_performance_metrics(skill_name)
        quality = self.calculate_quality_score(skill_name)

        if not metrics:
            return {"error": "No execution data available"}

        report = {
            "skill_name": skill_name,
            "performance": {
                "total_executions": metrics.total_executions,
                "success_rate": f"{metrics.success_rate:.2%}",
                "avg_latency_ms": f"{metrics.avg_latency_ms:.1f}",
                "p95_latency_ms": f"{metrics.p95_latency_ms:.1f}",
                "token_efficiency": f"{metrics.token_efficiency:.2f}",
                "avg_user_rating": f"{metrics.avg_user_rating:.2f}",
            },
        }

        if quality:
            report["quality"] = {
                "correctness": f"{quality.correctness:.2%}",
                "efficiency": f"{quality.efficiency:.2%}",
                "robustness": f"{quality.robustness:.2%}",
                "generality": f"{quality.generality:.2%}",
                "composite_score": f"{quality.composite_score:.2%}",
                "confidence": f"{quality.confidence:.2%}",
            }

        return report

    def clear_history(self, skill_name: str | None = None) -> None:
        """
        Clear execution history.

        Args:
            skill_name: Specific skill to clear, or None for all
        """
        if skill_name:
            if skill_name in self._executions:
                del self._executions[skill_name]
            if skill_name in self._quality_scores:
                del self._quality_scores[skill_name]
        else:
            self._executions.clear()
            self._quality_scores.clear()
