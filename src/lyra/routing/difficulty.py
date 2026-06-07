"""
Task difficulty estimation using content heuristics.

Provides ``DifficultyScore`` (enum) and ``DifficultyEstimator`` (class) for
rating how complex a routing task is based on its type, message length,
complexity keywords, and multi-step patterns.
"""

from __future__ import annotations

import re
import structlog
from enum import Enum

from lyra.routing.provider.types import Message

logger = structlog.get_logger(__name__)


class DifficultyScore(Enum):
    """Estimated difficulty of a task for routing purposes."""

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


# -- Keyword sets per difficulty level ---------------------------------------

_COMPLEXITY_KEYWORDS: dict[DifficultyScore, set[str]] = {
    DifficultyScore.COMPLEX: {
        "analyze",
        "compare",
        "contrast",
        "evaluate",
        "synthesize",
        "explain why",
        "reason about",
        "multi-step",
        "step by step",
        "debug",
        "refactor",
        "review",
        "optimize",
        "complex",
        "trade-off",
        "implications",
    },
    DifficultyScore.VERY_COMPLEX: {
        "research",
        "investigate",
        "comprehensive",
        "thorough",
        "deep dive",
        "state of the art",
        "literature",
        "survey",
        "architecture",
        "design document",
        "agentic",
        "autonomous",
        "multi-agent",
        "coordinated",
        "orchestrate",
        "novel",
        "breakthrough",
    },
}

# -- Regex patterns that hint at structured / multi-step tasks ----------------

_MULTI_STEP_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?:first|then|finally|step\s+\d)", re.IGNORECASE),
    re.compile(r"(?:\d+\.\s)", re.IGNORECASE),  # numbered lists
    re.compile(r"(?:-\s+\[[\sx]\])", re.IGNORECASE),  # checklists
    re.compile(r"(?:plan|outline|agenda|pipeline)", re.IGNORECASE),
]

# -- Baseline task-type-to-difficulty mapping ---------------------------------

_TASK_DIFFICULTY: dict[str, DifficultyScore] = {
    "simple_lookup": DifficultyScore.SIMPLE,
    "standard": DifficultyScore.MODERATE,
    "complex_reasoning": DifficultyScore.COMPLEX,
    "research": DifficultyScore.VERY_COMPLEX,
    "code_generation": DifficultyScore.MODERATE,
    "code_review": DifficultyScore.COMPLEX,
    "security_scan": DifficultyScore.COMPLEX,
    "debugging": DifficultyScore.COMPLEX,
    "agentic": DifficultyScore.VERY_COMPLEX,
}

# -- Internal helpers ---------------------------------------------------------


def _count_tokens(text: str) -> int:
    """Rough token count estimate (4 chars per token)."""
    return len(text) // 4


def _has_complexity_keywords(text: str, level: DifficultyScore) -> bool:
    """Check if *text* contains keywords associated with *level*."""
    lower = text.lower()
    keywords = _COMPLEXITY_KEYWORDS.get(level, set())
    return any(kw in lower for kw in keywords)


def _count_multi_step_patterns(text: str) -> int:
    """Count occurrences of multi-step patterns in *text*.

    Only examines the first 10 000 characters to avoid ``re`` module
    crashes on very long inputs.
    """
    sample = text[:10000]
    count = 0
    for pattern in _MULTI_STEP_PATTERNS:
        count += len(pattern.findall(sample))
    return count


# -- Ordinal helper for enum comparison (Enum does not support >) --------------

_ORDINALS: dict[DifficultyScore, int] = {
    DifficultyScore.SIMPLE: 0,
    DifficultyScore.MODERATE: 1,
    DifficultyScore.COMPLEX: 2,
    DifficultyScore.VERY_COMPLEX: 3,
}


def _higher(a: DifficultyScore, b: DifficultyScore) -> DifficultyScore:
    """Return the *DifficultyScore* with the higher ordinal."""
    return a if _ORDINALS[a] >= _ORDINALS[b] else b


# -- Public API ---------------------------------------------------------------


class DifficultyEstimator:
    """Estimates task difficulty using content heuristics.

    Combines task-type baseline, token count, complexity keywords, and
    multi-step patterns to produce a ``DifficultyScore``.

    Usage::

        estimator = DifficultyEstimator()
        score = estimator.estimate("code_review", messages)
        confidence = estimator.to_float(score)
    """

    def __init__(
        self,
        long_context_threshold: int = 8000,
        very_long_context_threshold: int = 32000,
    ) -> None:
        self._long_context_threshold = long_context_threshold
        self._very_long_context_threshold = very_long_context_threshold

    def estimate(
        self,
        task_type: str,
        messages: tuple[Message, ...] | None = None,
    ) -> DifficultyScore:
        """Estimate the difficulty of a task.

        Args:
            task_type: The type identifier (e.g. ``"simple_lookup"``).
                Unknown types default to ``MODERATE``.
            messages: Optional conversation messages for content analysis.

        Returns:
            A ``DifficultyScore`` based on task type and content heuristics.
        """
        # Baseline from task type
        score = _TASK_DIFFICULTY.get(task_type, DifficultyScore.MODERATE)

        if not messages:
            return score

        # Analyze message content for possible escalation
        full_text = " ".join(m.content for m in messages if m.content)
        token_estimate = _count_tokens(full_text)

        # Escalate based on context length
        if token_estimate > self._very_long_context_threshold:
            score = _higher(score, DifficultyScore.VERY_COMPLEX)
        elif token_estimate > self._long_context_threshold:
            score = _higher(score, DifficultyScore.COMPLEX)

        # Escalate based on complexity keywords
        if _has_complexity_keywords(full_text, DifficultyScore.VERY_COMPLEX):
            score = _higher(score, DifficultyScore.VERY_COMPLEX)
        elif _has_complexity_keywords(full_text, DifficultyScore.COMPLEX):
            score = _higher(score, DifficultyScore.COMPLEX)

        # Escalate based on multi-step / structured patterns
        step_count = _count_multi_step_patterns(full_text)
        if step_count >= 3:
            score = _higher(score, DifficultyScore.VERY_COMPLEX)
        elif step_count >= 1:
            score = _higher(score, DifficultyScore.COMPLEX)

        return score

    # -- Score conversion helpers ---------------------------------------------

    def to_float(self, difficulty: DifficultyScore) -> float:
        """Convert a ``DifficultyScore`` to a 0.0-1.0 float."""
        mapping = {
            DifficultyScore.SIMPLE: 0.1,
            DifficultyScore.MODERATE: 0.3,
            DifficultyScore.COMPLEX: 0.6,
            DifficultyScore.VERY_COMPLEX: 0.9,
        }
        return mapping.get(difficulty, 0.3)

    def from_float(self, score: float) -> DifficultyScore:
        """Convert a 0.0-1.0 float to the nearest ``DifficultyScore``."""
        if score >= 0.75:
            return DifficultyScore.VERY_COMPLEX
        if score >= 0.45:
            return DifficultyScore.COMPLEX
        if score >= 0.2:
            return DifficultyScore.MODERATE
        return DifficultyScore.SIMPLE


__all__ = [
    "DifficultyEstimator",
    "DifficultyScore",
]
