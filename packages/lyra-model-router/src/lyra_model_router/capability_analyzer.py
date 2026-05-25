"""Task-to-model capability matching and scoring.

Analyzes task profiles against model capabilities to produce scored,
ranked recommendations for model selection.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence


class ComplexityLevel(Enum):
    """Task complexity levels."""
    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


class DomainType(Enum):
    """Domain categories for task classification."""
    CODING = "coding"
    REASONING = "reasoning"
    ANALYSIS = "analysis"
    CREATIVE = "creative"
    SUMMARIZATION = "summarization"
    EXTRACTION = "extraction"
    CONVERSATION = "conversation"
    CLASSIFICATION = "classification"
    PLANNING = "planning"
    RESEARCH = "research"


class LatencySensitivity(Enum):
    """Latency sensitivity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class TaskProfile:
    """Describes a task to be routed to a model."""
    complexity: ComplexityLevel
    domain: DomainType
    reasoning_depth: float  # 0.0 (none) to 1.0 (deep)
    tool_requirements: tuple[str, ...] = field(default_factory=tuple)
    latency_sensitivity: LatencySensitivity = LatencySensitivity.MEDIUM
    token_budget: int = 4096
    timeout_seconds: float = 60.0

    @property
    def complexity_score(self) -> float:
        """Normalized complexity value 0.0-1.0 for scoring."""
        mapping = {
            ComplexityLevel.TRIVIAL: 0.1,
            ComplexityLevel.SIMPLE: 0.25,
            ComplexityLevel.MODERATE: 0.5,
            ComplexityLevel.COMPLEX: 0.75,
            ComplexityLevel.VERY_COMPLEX: 1.0,
        }
        return mapping.get(self.complexity, 0.5)

    @property
    def estimated_tokens(self) -> int:
        """Estimate tokens needed based on complexity."""
        base = float(self.token_budget)
        return int(base * (1.0 + self.complexity_score * 0.5))


@dataclass(frozen=True)
class ModelCapability:
    """Describes a model's capabilities for routing decisions."""
    model_id: str
    tier: str
    reasoning_score: float  # 0.0-1.0
    coding_score: float  # 0.0-1.0
    speed_score: float  # 0.0-1.0 (higher = faster)
    cost_per_1k_tokens: float  # USD per 1K tokens
    context_limit: int
    strengths: tuple[str, ...] = field(default_factory=tuple)
    weaknesses: tuple[str, ...] = field(default_factory=tuple)

    def cost_for_tokens(self, tokens: int) -> float:
        """Calculate cost for a given number of tokens."""
        return (tokens / 1000.0) * self.cost_per_1k_tokens


@dataclass(frozen=True)
class MatchScore:
    """Scored result of matching a task to a model."""
    model_id: str
    total_score: float  # 0.0-1.0
    reasoning_score: float
    coding_score: float
    speed_score: float
    cost_score: float
    breakdown: dict[str, float] = field(default_factory=dict)

    def __lt__(self, other: MatchScore) -> bool:
        return self.total_score < other.total_score


# Pre-defined model capabilities
PREDEFINED_CAPABILITIES: tuple[ModelCapability, ...] = (
    ModelCapability(
        model_id="claude-opus-4.7",
        tier="premium",
        reasoning_score=0.98,
        coding_score=0.95,
        speed_score=0.45,
        cost_per_1k_tokens=0.075,
        context_limit=200000,
        strengths=("deep_reasoning", "complex_coding", "research", "analysis"),
        weaknesses=("high_cost", "slower_response"),
    ),
    ModelCapability(
        model_id="claude-sonnet-4.6",
        tier="standard",
        reasoning_score=0.85,
        coding_score=0.90,
        speed_score=0.70,
        cost_per_1k_tokens=0.015,
        context_limit=100000,
        strengths=("coding", "analysis", "balanced", "fast_enough"),
        weaknesses=("lower_reasoning_than_opus", "shorter_context"),
    ),
    ModelCapability(
        model_id="claude-haiku-4.5",
        tier="economy",
        reasoning_score=0.60,
        coding_score=0.65,
        speed_score=0.95,
        cost_per_1k_tokens=0.0025,
        context_limit=50000,
        strengths=("speed", "low_cost", "simple_tasks", "high_throughput"),
        weaknesses=("low_reasoning", "limited_coding", "short_context"),
    ),
    ModelCapability(
        model_id="deepseek-v4-pro",
        tier="economy",
        reasoning_score=0.75,
        coding_score=0.80,
        speed_score=0.85,
        cost_per_1k_tokens=0.001,
        context_limit=128000,
        strengths=("low_cost", "good_coding", "speed", "long_context_cheap"),
        weaknesses=("lower_reasoning_than_claude", "less_creative"),
    ),
)


class CapabilityAnalyzer:
    """Analyzes task profiles against model capabilities.

    Produces scored, ranked model recommendations using weighted multi-factor
    matching: reasoning (40%), coding (30%), speed (20%), cost (10%).
    """

    def __init__(
        self,
        capabilities: Sequence[ModelCapability] | None = None,
    ) -> None:
        self._capabilities = list(capabilities or PREDEFINED_CAPABILITIES)
        self._weights = {
            "reasoning": 0.40,
            "coding": 0.30,
            "speed": 0.20,
            "cost": 0.10,
        }

    @property
    def capabilities(self) -> list[ModelCapability]:
        """Return a copy of the registered model capabilities."""
        return list(self._capabilities)

    def register_model(self, capability: ModelCapability) -> None:
        """Register or update a model's capability profile."""
        for i, existing in enumerate(self._capabilities):
            if existing.model_id == capability.model_id:
                self._capabilities[i] = capability
                return
        self._capabilities.append(capability)

    def remove_model(self, model_id: str) -> bool:
        """Remove a model from the registry. Returns True if removed."""
        for i, existing in enumerate(self._capabilities):
            if existing.model_id == model_id:
                self._capabilities.pop(i)
                return True
        return False

    def set_weights(
        self,
        reasoning: float | None = None,
        coding: float | None = None,
        speed: float | None = None,
        cost: float | None = None,
    ) -> None:
        """Update scoring weights. Each must be 0.0-1.0 and sum to 1.0."""
        new_weights = {
            "reasoning": reasoning if reasoning is not None else self._weights["reasoning"],
            "coding": coding if coding is not None else self._weights["coding"],
            "speed": speed if speed is not None else self._weights["speed"],
            "cost": cost if cost is not None else self._weights["cost"],
        }
        total = sum(new_weights.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total:.3f}")
        self._weights = new_weights

    def get_model(self, model_id: str) -> ModelCapability | None:
        """Look up a model by ID."""
        for cap in self._capabilities:
            if cap.model_id == model_id:
                return cap
        return None

    def analyze(self, task: TaskProfile) -> list[MatchScore]:
        """Score all registered models against a task profile.

        Returns models ranked by total_score descending.
        """
        scores: list[MatchScore] = []
        for cap in self._capabilities:
            score = self._score_match(task, cap)
            scores.append(score)
        scores.sort(key=lambda s: s.total_score, reverse=True)
        return scores

    def analyze_top_k(self, task: TaskProfile, k: int = 3) -> list[MatchScore]:
        """Return the top-k scored matches for a task."""
        return self.analyze(task)[:k]

    def _score_match(self, task: TaskProfile, cap: ModelCapability) -> MatchScore:
        """Compute the weighted match score between a task and a model."""
        reasoning_score = self._score_reasoning(task, cap)
        coding_score = self._score_coding(task, cap)
        speed_score = self._score_speed(task, cap)
        cost_score = self._score_cost(task, cap)

        total = (
            reasoning_score * self._weights["reasoning"]
            + coding_score * self._weights["coding"]
            + speed_score * self._weights["speed"]
            + cost_score * self._weights["cost"]
        )

        return MatchScore(
            model_id=cap.model_id,
            total_score=round(total, 4),
            reasoning_score=round(reasoning_score, 4),
            coding_score=round(coding_score, 4),
            speed_score=round(speed_score, 4),
            cost_score=round(cost_score, 4),
            breakdown={
                "reasoning_weight": self._weights["reasoning"],
                "coding_weight": self._weights["coding"],
                "speed_weight": self._weights["speed"],
                "cost_weight": self._weights["cost"],
            },
        )

    def _score_reasoning(self, task: TaskProfile, cap: ModelCapability) -> float:
        """Score reasoning capability match (0.0-1.0)."""
        if task.domain in (DomainType.REASONING, DomainType.RESEARCH, DomainType.ANALYSIS, DomainType.PLANNING):
            return cap.reasoning_score * (0.6 + 0.4 * task.reasoning_depth)
        return cap.reasoning_score * 0.2 + 0.8

    def _score_coding(self, task: TaskProfile, cap: ModelCapability) -> float:
        """Score coding capability match (0.0-1.0)."""
        if task.domain in (DomainType.CODING, DomainType.PLANNING):
            base = cap.coding_score
            if task.complexity in (ComplexityLevel.COMPLEX, ComplexityLevel.VERY_COMPLEX):
                return base * (0.6 + 0.4 * task.reasoning_depth)
            return 0.5 * base + 0.5
        return cap.coding_score * 0.1 + 0.9

    def _score_speed(self, task: TaskProfile, cap: ModelCapability) -> float:
        """Score speed match (0.0-1.0). Higher speed is better for sensitive tasks."""
        if task.latency_sensitivity == LatencySensitivity.HIGH:
            return cap.speed_score
        if task.latency_sensitivity == LatencySensitivity.MEDIUM:
            return 0.3 * cap.speed_score + 0.7
        return 1.0

    def _score_cost(self, task: TaskProfile, cap: ModelCapability) -> float:
        """Score cost efficiency (0.0-1.0). Lower cost = higher score."""
        estimated_cost = cap.cost_for_tokens(task.estimated_tokens)
        max_cost = max(
            c.cost_for_tokens(task.estimated_tokens)
            for c in self._capabilities
        ) or 1.0
        if max_cost == 0:
            return 1.0
        # Invert: lower cost = higher score, moderate penalty to not overwhelm other factors
        return 1.0 - (estimated_cost / max_cost * 0.35)

    def get_tier_for_task(self, task: TaskProfile) -> str:
        """Suggest the appropriate model tier for a task."""
        scores = self.analyze_top_k(task, k=1)
        if not scores:
            return "none"
        best = scores[0]
        cap = self.get_model(best.model_id)
        if cap is None:
            return "standard"
        return cap.tier

    def find_models_for_domain(
        self,
        domain: DomainType,
        min_reasoning: float = 0.0,
        min_coding: float = 0.0,
    ) -> list[ModelCapability]:
        """Find models that meet minimum thresholds for a domain."""
        results: list[ModelCapability] = []
        for cap in self._capabilities:
            if cap.reasoning_score >= min_reasoning and cap.coding_score >= min_coding:
                if domain == DomainType.CODING and cap.coding_score >= 0.5:
                    results.append(cap)
                elif domain != DomainType.CODING:
                    results.append(cap)
        return results

    @staticmethod
    def normalize_score(raw: float, min_val: float, max_val: float) -> float:
        """Linearly normalize a score to 0.0-1.0."""
        if max_val == min_val:
            return 0.5
        return max(0.0, min(1.0, (raw - min_val) / (max_val - min_val)))
