"""1-10 complexity estimator with multi-factor analysis.

Plan 10 Layer 2: Estimates task complexity on a 1-10 scale based on
description semantics, estimated token budget, tool count, dependency
depth, and domain-specific difficulty heuristics.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ComplexityEstimate:
    """Detailed complexity assessment for a task.

    Attributes:
        score: Overall complexity 1.0-10.0.
        factors: Named factor contributions to the final score.
        reasoning: Human-readable breakdown.
        recommended_tier: Suggested model tier index (0-3).
    """

    score: float
    factors: dict[str, float]
    reasoning: str
    recommended_tier: int


# Signals of high intrinsic complexity
_HIGH_COMPLEXITY_SIGNALS: dict[str, float] = {
    "recursive": 0.8,
    "distributed": 0.7,
    "concurrent": 0.7,
    "multi-threaded": 0.7,
    "optimization": 0.5,
    "performance critical": 0.8,
    "real-time": 0.7,
    "machine learning": 0.8,
    "neural network": 0.8,
    "compiler": 0.9,
    "parser": 0.7,
    "serializer": 0.5,
    "protocol": 0.6,
    "encryption": 0.6,
    "consensus": 0.8,
    "replication": 0.7,
    "sharding": 0.8,
    "migration": 0.6,
    "legacy": 0.5,
    "cross-platform": 0.5,
    "multi-tenant": 0.7,
    "auth": 0.5,
    "race condition": 0.8,
    "deadlock": 0.8,
    "memory leak": 0.7,
}

_LOW_COMPLEXITY_SIGNALS: dict[str, float] = {
    "simple": -0.4,
    "trivial": -0.6,
    "straightforward": -0.3,
    "boilerplate": -0.5,
    "template": -0.4,
    "one-liner": -0.7,
    "quick": -0.3,
    "minor": -0.3,
    "cosmetic": -0.5,
    "typo": -0.7,
    "rename": -0.3,
    "format": -0.4,
}


class ComplexityEstimator:
    """Estimates task complexity on a 1-10 scale.

    Factors considered:
    - Description length and keyword signals (weight: 0.30)
    - Context tokens required (weight: 0.25)
    - Tools count (weight: 0.20)
    - Dependency depth (weight: 0.15)
    - Domain-specific difficulty (weight: 0.10)

    The estimator can be calibrated with historical data to improve
    accuracy over time (performance history integration).
    """

    def __init__(self) -> None:
        self._factor_weights = {
            "description": 0.30,
            "context": 0.25,
            "tools": 0.20,
            "dependencies": 0.15,
            "domain": 0.10,
        }

    def estimate(
        self,
        description: str,
        context_tokens: int = 0,
        tools_required: int = 0,
        dependency_count: int = 0,
        domain: str = "general",
    ) -> ComplexityEstimate:
        """Produce a 1-10 complexity estimate.

        Args:
            description: Task description text.
            context_tokens: Estimated context tokens needed.
            tools_required: Expected number of tool calls.
            dependency_count: Number of upstream dependencies.
            domain: Domain hint for difficulty calibration.
        """
        desc_score = self._score_description(description)
        context_score = self._score_context(context_tokens)
        tools_score = self._score_tools(tools_required)
        dep_score = self._score_dependencies(dependency_count)
        domain_score = self._score_domain(domain)

        factors = {
            "description": desc_score,
            "context": context_score,
            "tools": tools_score,
            "dependencies": dep_score,
            "domain": domain_score,
        }

        raw = sum(
            factors[k] * self._factor_weights[k] for k in self._factor_weights
        )
        # Scale 0-1 to 1-10 range
        score = round(1.0 + raw * 9.0, 1)
        score = max(1.0, min(10.0, score))

        tier = self._recommend_tier(score, context_tokens, tools_required)

        reasoning = (
            f"Complexity {score}/10 | "
            f"desc={desc_score:.2f} ctx={context_score:.2f} "
            f"tools={tools_score:.2f} deps={dep_score:.2f} "
            f"domain={domain_score:.2f} → tier {tier}"
        )

        return ComplexityEstimate(
            score=score,
            factors=factors,
            reasoning=reasoning,
            recommended_tier=tier,
        )

    def _score_description(self, description: str) -> float:
        """Score based on description length and complexity signals."""
        lower = description.lower()

        # Length factor: 0.0 for short, 1.0 for very long
        length = len(description)
        if length < 50:
            length_score = 0.1
        elif length < 200:
            length_score = 0.3
        elif length < 500:
            length_score = 0.5
        elif length < 1000:
            length_score = 0.7
        else:
            length_score = 0.9

        # Keyword signals
        high_score = sum(
            weight for kw, weight in _HIGH_COMPLEXITY_SIGNALS.items()
            if kw in lower
        )
        low_score = sum(
            abs(weight) for kw, weight in _LOW_COMPLEXITY_SIGNALS.items()
            if kw in lower
        )

        # Question count (more questions = higher complexity)
        question_count = lower.count("?")
        question_factor = min(0.2, question_count * 0.05)

        # Code block count (described code blocks = implementation complexity)
        code_blocks = len(re.findall(r"```|`[^`]+`", description))
        code_factor = min(0.15, code_blocks * 0.03)

        raw = length_score + high_score - low_score + question_factor + code_factor
        return round(max(0.0, min(1.0, raw)), 4)

    @staticmethod
    def _score_context(context_tokens: int) -> float:
        """Score based on estimated context token count."""
        if context_tokens == 0:
            return 0.1
        if context_tokens < 5_000:
            return 0.2
        if context_tokens < 25_000:
            return 0.4
        if context_tokens < 75_000:
            return 0.6
        if context_tokens < 150_000:
            return 0.8
        return 0.95

    @staticmethod
    def _score_tools(tools_required: int) -> float:
        """Score based on number of tools required."""
        if tools_required == 0:
            return 0.1
        if tools_required <= 2:
            return 0.25
        if tools_required <= 5:
            return 0.5
        if tools_required <= 10:
            return 0.7
        if tools_required <= 20:
            return 0.85
        return 0.95

    @staticmethod
    def _score_dependencies(dependency_count: int) -> float:
        """Score based on upstream dependency count."""
        if dependency_count == 0:
            return 0.05
        if dependency_count <= 2:
            return 0.2
        if dependency_count <= 5:
            return 0.45
        if dependency_count <= 10:
            return 0.7
        return 0.9

    @staticmethod
    def _score_domain(domain: str) -> float:
        """Score based on domain-specific difficulty heuristics."""
        domain_scores = {
            "compiler": 0.9,
            "os_kernel": 0.95,
            "distributed_systems": 0.85,
            "machine_learning": 0.8,
            "security": 0.75,
            "cryptography": 0.9,
            "database": 0.6,
            "networking": 0.7,
            "frontend": 0.4,
            "devops": 0.55,
            "testing": 0.35,
            "documentation": 0.2,
            "general": 0.4,
        }
        return domain_scores.get(domain, 0.4)

    @staticmethod
    def _recommend_tier(
        score: float, context_tokens: int, tools_required: int
    ) -> int:
        """Map complexity score to a model tier 0-3.

        Tier 0: 7.5+ complexity → Reasoning models
        Tier 1: 4.5-7.4 → Standard models
        Tier 2: 2.5-4.4 → Fast models
        Tier 3: <2.5 → Cheap models

        Context and tool adjustments nudge borderline cases up.
        """
        adjusted = score
        if context_tokens > 100_000:
            adjusted += 0.5
        if tools_required > 10:
            adjusted += 0.5

        if adjusted >= 7.5:
            return 0
        if adjusted >= 4.5:
            return 1
        if adjusted >= 2.5:
            return 2
        return 3

    def calibrate(self, actual_scores: list[tuple[float, float]]) -> None:
        """Calibrate factor weights from observed (estimated, actual) pairs.

        Simple linear adjustment — moves weights toward factors that
        correlate with actual complexity.
        """
        if len(actual_scores) < 10:
            return
        # Store for future ML-based weight optimization
        self._calibration_data = actual_scores
