"""MetaClaw — cross-run evolution engine for persistent self-improvement.

Inspired by AutoResearchClaw MetaClaw: enables skills and insights to
persist across independent runs, accumulating compound improvements
over time through cross-run pattern analysis and skill evolution.
"""

from time import time
from typing import Any

from .models import CrossRunInsight


class MetaClaw:
    """Cross-run evolution engine.

    Three core capabilities:
    1. Insight extraction — distill learnings from completed runs
    2. Cross-run correlation — find patterns spanning multiple runs
    3. Actionable recommendation — surface insights as concrete actions
    """

    def __init__(self, max_insights: int = 200):
        self._insights: dict[str, CrossRunInsight] = {}
        self._run_history: dict[str, dict[str, Any]] = {}
        self._max_insights = max_insights

    def record_run(self, run_id: str, summary: dict[str, Any]) -> None:
        """Record the outcome of a completed run."""
        self._run_history[run_id] = {
            "summary": summary,
            "recorded_at": time(),
        }
        self._extract_insights(run_id, summary)

    def _extract_insights(self, run_id: str, summary: dict[str, Any]) -> None:
        """Extract insights from a run summary."""
        import uuid

        if "errors" in summary and summary["errors"]:
            for error in summary["errors"][:3]:
                insight_id = str(uuid.uuid4())
                self._insights[insight_id] = CrossRunInsight(
                    id=insight_id,
                    insight=f"Error pattern: {str(error)[:200]}",
                    category="error",
                    evidence_count=1,
                    run_ids=(run_id,),
                    confidence=0.5,
                    actionable=True,
                    action_description=f"Investigate and fix: {str(error)[:100]}",
                )

        if "improvements" in summary and summary["improvements"]:
            for imp in summary["improvements"][:3]:
                insight_id = str(uuid.uuid4())
                self._insights[insight_id] = CrossRunInsight(
                    id=insight_id,
                    insight=f"Improvement: {str(imp)[:200]}",
                    category="improvement",
                    evidence_count=1,
                    run_ids=(run_id,),
                    confidence=0.6,
                    actionable=True,
                    action_description=f"Adopt improvement: {str(imp)[:100]}",
                )

        if "metrics" in summary:
            metrics = summary["metrics"]
            if isinstance(metrics, dict):
                for key, value in metrics.items():
                    if isinstance(value, (int, float)):
                        insight_id = str(uuid.uuid4())
                        self._insights[insight_id] = CrossRunInsight(
                            id=insight_id,
                            insight=f"Metric '{key}': {value}",
                            category="metric",
                            evidence_count=1,
                            run_ids=(run_id,),
                            confidence=0.3,
                        )

        self._enforce_limit()

    def _enforce_limit(self) -> None:
        if len(self._insights) <= self._max_insights:
            return
        oldest = sorted(self._insights.values(), key=lambda i: i.created_at)
        for insight in oldest[: len(self._insights) - self._max_insights]:
            self._insights.pop(insight.id, None)

    def correlate(self) -> list[CrossRunInsight]:
        """Find insights that span multiple runs (cross-run correlation)."""
        multi_run: list[CrossRunInsight] = []
        seen: dict[str, CrossRunInsight] = {}
        for insight in self._insights.values():
            key = insight.insight[:100]
            if key in seen:
                existing = seen[key]
                merged = CrossRunInsight(
                    id=existing.id,
                    insight=existing.insight,
                    category=existing.category,
                    evidence_count=existing.evidence_count + 1,
                    run_ids=existing.run_ids + insight.run_ids,
                    confidence=min(existing.confidence + 0.15, 1.0),
                    actionable=existing.actionable,
                    action_description=existing.action_description,
                )
                self._insights[existing.id] = merged
                multi_run.append(merged)
            else:
                seen[key] = insight
        return multi_run

    def actionable_insights(self) -> list[CrossRunInsight]:
        """Get all actionable insights sorted by confidence."""
        actionable = [i for i in self._insights.values() if i.actionable]
        return sorted(actionable, key=lambda i: (i.evidence_count, i.confidence), reverse=True)

    def by_category(self, category: str) -> list[CrossRunInsight]:
        return [i for i in self._insights.values() if i.category == category]

    def top_insights(self, n: int = 5) -> list[CrossRunInsight]:
        return sorted(
            self._insights.values(),
            key=lambda i: (i.confidence * i.evidence_count),
            reverse=True,
        )[:n]

    @property
    def insight_count(self) -> int:
        return len(self._insights)

    @property
    def run_count(self) -> int:
        return len(self._run_history)
