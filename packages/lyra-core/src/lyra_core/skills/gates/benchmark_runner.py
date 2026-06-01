"""Gate 3: Performance Benchmark Runner.

Runs performance benchmarks on skill candidates.
Threshold: 0.80 (good performance required)
Auto-fix: Not available (requires manual optimization)
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkResult:
    """Result from performance benchmarking."""

    score: float  # 0.0–1.0
    issues: tuple[str, ...]
    metrics: dict[str, float]
    recommendation: str
    passed: bool


class BenchmarkRunner:
    """Gate 3: Runs performance benchmarks on skills.

    Checks:
    - Skill size (line count)
    - Import count (startup time impact)
    - Nested loop complexity (O(n²) detection)
    - Trigger quality (length, clarity)
    """

    THRESHOLD = 0.80

    def validate(
        self,
        skill_name: str,
        skill_triggers: tuple[str, ...],
        skill_body: str,
    ) -> BenchmarkResult:
        """Run performance benchmarks on a skill.

        Args:
            skill_name: Name of the skill
            skill_triggers: Trigger phrases for the skill
            skill_body: The skill implementation code

        Returns:
            BenchmarkResult with score, issues, metrics, and recommendation
        """
        issues: list[str] = []
        metrics: dict[str, float] = {}

        # Analyze line count
        lines = [ln for ln in skill_body.split("\n") if ln.strip()]
        line_count = len(lines)
        metrics["line_count"] = float(line_count)

        if line_count > 500:
            issues.append(f"Skill too large ({line_count} lines); consider splitting")
        if line_count > 1000:
            issues.append("Skill exceeds 1000-line limit — rejected")

        # Analyze import count
        import_count = sum(
            1 for ln in lines if ln.strip().startswith("import ") or ln.strip().startswith("from ")
        )
        metrics["import_count"] = float(import_count)

        if import_count > 20:
            issues.append(f"Excessive imports ({import_count}); may increase startup time")

        # Detect nested loops (O(n²) complexity)
        nested_loops = self._count_nested_loops(lines)
        metrics["nested_loops"] = float(nested_loops)

        if nested_loops > 3:
            issues.append(f"Potential O(n²) complexity: {nested_loops} nested loops")

        # Evaluate trigger quality
        trigger_quality = self._evaluate_trigger_quality(skill_triggers)
        metrics["trigger_quality"] = trigger_quality

        # Calculate composite score
        size_score = max(0.3, 1.0 - (line_count / 2000))
        import_score = max(0.5, 1.0 - (import_count / 40))
        complexity_score = max(0.5, 1.0 - (nested_loops / 10))

        score = min(
            1.0 - (len(issues) * 0.15),
            size_score,
            import_score,
            complexity_score,
            trigger_quality,
        )
        score = max(0.0, min(1.0, score))
        metrics["composite_score"] = score

        # Determine status and recommendation
        if score >= self.THRESHOLD:
            recommendation = "Performance benchmarks passed."
            passed = True
        elif score >= 0.6:
            recommendation = "Performance concerns — review before deploying."
            passed = False
        else:
            recommendation = "Performance unacceptable — optimize before resubmitting."
            passed = False

        return BenchmarkResult(
            score=round(score, 4),
            issues=tuple(issues),
            metrics=metrics,
            recommendation=recommendation,
            passed=passed,
        )

    def _count_nested_loops(self, lines: list[str]) -> int:
        """Count nested loops in code (heuristic for O(n²) detection)."""
        nested_loops = 0
        indent_levels: list[int] = []

        for ln in lines:
            stripped = ln.lstrip()
            if stripped:
                indent = len(ln) - len(stripped)
                indent_levels.append(indent // 4)

                if re.search(r"\b(for|while)\b", stripped):
                    if len(indent_levels) >= 2 and indent_levels[-1] > indent_levels[-2]:
                        nested_loops += 1

        return nested_loops

    def _evaluate_trigger_quality(self, triggers: tuple[str, ...]) -> float:
        """Evaluate quality of trigger phrases."""
        if not triggers:
            return 0.0

        quality = 0.9
        for t in triggers:
            # Too short triggers are ambiguous
            if len(t) < 3:
                quality -= 0.15
            # Too long triggers are hard to remember
            if len(t) > 80:
                quality -= 0.1

        return max(0.0, min(1.0, quality))
