"""15-category task classifier with confidence-weighted multi-label support.

Expands the original 6-category keyword classifier into the Plan 10
15-category taxonomy for finer-grained routing decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TaskCategory(Enum):
    """15-category task taxonomy for intelligent routing."""

    ARCHITECTURE = "architecture"
    CODE_IMPLEMENTATION = "code_implementation"
    CODE_REVIEW = "code_review"
    DEBUGGING = "debugging"
    REFACTORING = "refactoring"
    TESTING = "testing"
    RESEARCH = "research"
    DATA_ANALYSIS = "data_analysis"
    DOCUMENTATION = "documentation"
    SECURITY_AUDIT = "security_audit"
    DEVOPS = "devops"
    SIMPLE_LOOKUP = "simple_lookup"
    BATCH_PROCESSING = "batch_processing"
    CREATIVE_GENERATION = "creative_generation"
    CONVERSATION = "conversation"


# Weighted keyword patterns per category — each keyword has a confidence weight
_CATEGORY_PATTERNS: dict[TaskCategory, dict[str, float]] = {
    TaskCategory.ARCHITECTURE: {
        "architecture": 0.9, "system design": 0.9, "trade-off": 0.8,
        "design pattern": 0.85, "overview": 0.5, "plan": 0.4,
        "blueprint": 0.85, "component diagram": 0.9, "data flow": 0.8,
        "microservice": 0.7, "monolith": 0.7, "scalability": 0.75,
    },
    TaskCategory.CODE_IMPLEMENTATION: {
        "implement": 0.8, "write code": 0.9, "build": 0.5,
        "create function": 0.85, "add endpoint": 0.85, "api": 0.5,
        "feature": 0.6, "develop": 0.7, "code": 0.3,
    },
    TaskCategory.CODE_REVIEW: {
        "review": 0.7, "code review": 0.95, "audit code": 0.9,
        "inspect": 0.7, "check code": 0.8, "peer review": 0.9,
        "quality gate": 0.85, "approve": 0.5,
    },
    TaskCategory.DEBUGGING: {
        "debug": 0.9, "bug": 0.7, "fix error": 0.85, "troubleshoot": 0.85,
        "stack trace": 0.9, "crash": 0.8, "regression": 0.7,
        "root cause": 0.75, "bisect": 0.8,
    },
    TaskCategory.REFACTORING: {
        "refactor": 0.9, "clean up": 0.7, "restructure": 0.85,
        "extract method": 0.9, "rename": 0.6, "simplify": 0.6,
        "decouple": 0.8, "migrate": 0.6,
    },
    TaskCategory.TESTING: {
        "test": 0.5, "unit test": 0.9, "integration test": 0.9,
        "coverage": 0.8, "mock": 0.7, "assert": 0.7,
        "test case": 0.85, "e2e": 0.9, "fixture": 0.8,
    },
    TaskCategory.RESEARCH: {
        "research": 0.9, "analyze": 0.5, "investigate": 0.7,
        "survey": 0.85, "literature": 0.85, "paper": 0.8,
        "deep dive": 0.85, "explore": 0.6, "study": 0.6,
        "benchmark": 0.7, "compare": 0.6,
    },
    TaskCategory.DATA_ANALYSIS: {
        "data": 0.4, "query": 0.6, "sql": 0.85, "database": 0.7,
        "analytics": 0.85, "metrics": 0.7, "dashboard": 0.75,
        "visualize": 0.8, "report": 0.5, "etl": 0.9,
    },
    TaskCategory.DOCUMENTATION: {
        "document": 0.7, "readme": 0.85, "docs": 0.8,
        "documentation": 0.9, "write docs": 0.9, "api docs": 0.9,
        "changelog": 0.85, "tutorial": 0.8, "guide": 0.6,
    },
    TaskCategory.SECURITY_AUDIT: {
        "security": 0.8, "vulnerability": 0.9, "exploit": 0.9,
        "penetration": 0.9, "owasp": 0.9, "auth": 0.5,
        "encryption": 0.7, "secret": 0.7, "compliance": 0.7,
    },
    TaskCategory.DEVOPS: {
        "deploy": 0.75, "ci/cd": 0.9, "pipeline": 0.8,
        "docker": 0.85, "kubernetes": 0.85, "infrastructure": 0.8,
        "terraform": 0.9, "monitoring": 0.6, "alert": 0.7,
    },
    TaskCategory.SIMPLE_LOOKUP: {
        "find": 0.4, "look up": 0.7, "search": 0.5, "retrieve": 0.7,
        "what is": 0.6, "where is": 0.6, "show me": 0.5,
        "list": 0.3, "get": 0.2,
    },
    TaskCategory.BATCH_PROCESSING: {
        "batch": 0.85, "process all": 0.8, "transform all": 0.8,
        "bulk": 0.85, "migrate data": 0.8, "import": 0.5,
        "export": 0.5, "convert all": 0.8, "regenerate": 0.7,
    },
    TaskCategory.CREATIVE_GENERATION: {
        "generate": 0.5, "create content": 0.8, "write story": 0.9,
        "brainstorm": 0.85, "creative": 0.85, "design ui": 0.7,
        "logo": 0.8, "copywriting": 0.9, "poem": 0.9,
    },
    TaskCategory.CONVERSATION: {
        "hello": 0.7, "thanks": 0.7, "explain": 0.4,
        "what do you think": 0.6, "help": 0.3, "how are you": 0.8,
        "clarify": 0.6, "summarize": 0.5,
    },
}


@dataclass(frozen=True)
class ClassificationResult:
    """Result of task classification.

    Attributes:
        primary: The highest-confidence category.
        confidence: Confidence score 0.0-1.0 for the primary category.
        top_categories: Ordered list of (category, confidence) tuples.
        all_scores: Full mapping of category → confidence.
    """

    primary: TaskCategory
    confidence: float
    top_categories: tuple[tuple[TaskCategory, float], ...] = ()
    all_scores: dict[TaskCategory, float] = field(default_factory=dict)


class TaskClassifier:
    """15-category task classifier with weighted keyword matching.

    Provides multi-label classification with confidence scores, enabling
    the router to make fine-grained decisions about which model tier
    and capabilities are needed.
    """

    def __init__(self) -> None:
        self._classification_counts: dict[TaskCategory, int] = dict.fromkeys(TaskCategory, 0)

    def classify(self, description: str) -> ClassificationResult:
        """Classify a task description into one of 15 categories.

        Returns a ClassificationResult with the primary category and
        confidence-weighted alternatives for fallback routing.
        """
        lower = description.lower()
        scores: dict[TaskCategory, float] = {}

        for category, patterns in _CATEGORY_PATTERNS.items():
            score = 0.0
            matches = 0
            for keyword, weight in patterns.items():
                if keyword in lower:
                    score += weight
                    matches += 1
            # Normalize: cap at 1.0, boost multi-match slightly
            normalized = min(1.0, score * (1.0 + 0.1 * max(0, matches - 1)))
            scores[category] = round(normalized, 4)

        # Sort by confidence descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        primary, confidence = ranked[0]
        top = tuple(ranked[:3])

        self._classification_counts[primary] += 1

        return ClassificationResult(
            primary=primary,
            confidence=confidence,
            top_categories=top,
            all_scores=scores,
        )

    def classify_batch(
        self, descriptions: list[str]
    ) -> list[ClassificationResult]:
        """Classify multiple task descriptions at once."""
        return [self.classify(d) for d in descriptions]

    @property
    def classification_counts(self) -> dict[TaskCategory, int]:
        """Return cumulative classification counts for analysis."""
        return dict(self._classification_counts)

    def reset_counts(self) -> None:
        """Reset the classification counter."""
        self._classification_counts = dict.fromkeys(TaskCategory, 0)
