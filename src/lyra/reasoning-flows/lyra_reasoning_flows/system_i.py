from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class ReasoningTier(str, Enum):
    FAST = "fast"
    SIMULATIVE = "simulative"
    META = "meta"


class TaskCategory(str, Enum):
    LOOKUP = "lookup"
    EDIT = "edit"
    CLASSIFY = "classify"
    GENERATE = "generate"
    PLAN = "plan"
    DEBUG = "debug"


@dataclass(frozen=True)
class ReasoningTrace:
    steps: tuple[str, ...]
    confidence: float
    timing_ms: float
    tier: ReasoningTier = ReasoningTier.FAST
    created_at: datetime = datetime.now(timezone.utc)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence}")


@dataclass(frozen=True)
class TaskAssessment:
    category: TaskCategory
    confidence: float
    estimated_difficulty: float  # 0.0 (trivial) to 1.0 (very hard)
    reasoning_tier: ReasoningTier
    explanation: str
    requires_fallthrough: bool = False


# Known task signatures for fast pattern matching.
_KOWN_PATTERNS: dict[str, TaskCategory] = {
    "search": TaskCategory.LOOKUP,
    "find": TaskCategory.LOOKUP,
    "lookup": TaskCategory.LOOKUP,
    "get": TaskCategory.LOOKUP,
    "edit": TaskCategory.EDIT,
    "update": TaskCategory.EDIT,
    "modify": TaskCategory.EDIT,
    "change": TaskCategory.EDIT,
    "classify": TaskCategory.CLASSIFY,
    "categorize": TaskCategory.CLASSIFY,
    "label": TaskCategory.CLASSIFY,
    "type": TaskCategory.CLASSIFY,
    "generate": TaskCategory.GENERATE,
    "create": TaskCategory.GENERATE,
    "write": TaskCategory.GENERATE,
    "plan": TaskCategory.PLAN,
    "strategy": TaskCategory.PLAN,
    "design": TaskCategory.PLAN,
    "schedule": TaskCategory.PLAN,
    "debug": TaskCategory.DEBUG,
    "fix": TaskCategory.DEBUG,
    "error": TaskCategory.DEBUG,
    "issue": TaskCategory.DEBUG,
}

# Category-to-confidence mapping for quick assessment baseline.
_CATEGORY_CONFIDENCE: dict[TaskCategory, float] = {
    TaskCategory.LOOKUP: 0.95,
    TaskCategory.EDIT: 0.85,
    TaskCategory.CLASSIFY: 0.90,
    TaskCategory.GENERATE: 0.70,
    TaskCategory.PLAN: 0.40,
    TaskCategory.DEBUG: 0.55,
}


class SystemIReasoner:
    """Fast/intuitive System I reasoner for routine tasks.

    Matches task descriptions against known patterns to classify the task
    and estimate confidence. Falls through to System II when confidence
    is below threshold.
    """

    def __init__(self, fallthrough_threshold: float = 0.75) -> None:
        self.fallthrough_threshold = fallthrough_threshold

    def quick_assess(self, task_context: str) -> TaskAssessment:
        task_lower = task_context.lower()
        words = task_lower.split()

        category = TaskCategory.GENERATE
        best_score = 0
        for word in words:
            if word in _KOWN_PATTERNS:
                cat = _KOWN_PATTERNS[word]
                score = _KOWN_PATTERNS.get(word, 0)  # arbitrary
                if isinstance(score, str):
                    score_val = 1
                else:
                    score_val = 1
                # Score by position: earlier keywords are more indicative
                # (this over-simplifies; we treat presence as score 1)
                if score_val > best_score:
                    best_score = score_val
                    category = cat

        # Re-score by counting keyword matches per category.
        category_matches: dict[TaskCategory, int] = {}
        for word in words:
            if word in _KOWN_PATTERNS:
                cat = _KOWN_PATTERNS[word]
                category_matches[cat] = category_matches.get(cat, 0) + 1

        if category_matches:
            category = max(category_matches, key=lambda c: category_matches[c])

        base_confidence = _CATEGORY_CONFIDENCE.get(category, 0.5)
        # Boost confidence by match count.
        match_count = category_matches.get(category, 0)
        confidence = min(1.0, base_confidence + match_count * 0.05)

        # Estimate difficulty inversely from confidence (higher confidence => easier).
        estimated_difficulty = 1.0 - confidence

        requires_fallthrough = confidence < self.fallthrough_threshold
        tier = ReasoningTier.FAST if not requires_fallthrough else ReasoningTier.SIMULATIVE

        explanation = (
            f"Classified as {category.value} "
            f"(confidence={confidence:.2f}, difficulty={estimated_difficulty:.2f})"
        )

        return TaskAssessment(
            category=category,
            confidence=confidence,
            estimated_difficulty=estimated_difficulty,
            reasoning_tier=tier,
            explanation=explanation,
            requires_fallthrough=requires_fallthrough,
        )

    def reason(self, task_context: str) -> ReasoningTrace:
        assess = self.quick_assess(task_context)
        import time

        start = time.time()
        steps = (f"Pattern-match: {assess.category.value}",)
        elapsed = (time.time() - start) * 1000
        return ReasoningTrace(
            steps=steps,
            confidence=assess.confidence,
            timing_ms=elapsed,
            tier=assess.reasoning_tier,
        )

    def reason_with_fallthrough(self, task_context: str) -> TaskAssessment:
        return self.quick_assess(task_context)
