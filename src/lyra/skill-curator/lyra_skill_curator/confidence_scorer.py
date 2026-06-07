"""Reliability Scoring — score extracted skills with Bayesian updates and decay."""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum


class EvidenceType(Enum):
    """The category of evidence for a confidence score."""

    SUCCESSFUL_USE = "successful_use"
    FAILED_USE = "failed_use"
    EXPERT_REVIEW = "expert_review"
    CROSS_VALIDATION = "cross_validation"
    BENCHMARK = "benchmark"


@dataclass(frozen=True)
class EvidenceItem:
    """A single piece of evidence supporting or refuting a skill."""

    type: EvidenceType
    strength: float  # 0.0 to 1.0
    source: str


@dataclass(frozen=True)
class ConfidenceScore:
    """A scored confidence level for a skill with supporting evidence."""

    skill_id: str
    score: float  # 0.0 to 1.0
    evidence_items: tuple[EvidenceItem, ...]
    uncertainty: float  # 0.0 (certain) to 1.0 (uncertain)


class ConfidenceScorer:
    """Scores and updates confidence for skills based on evidence."""

    def score(
        self, skill_id: str, evidence: Sequence[EvidenceItem]
    ) -> ConfidenceScore:
        """Compute a confidence score from evidence items."""
        return score(skill_id, evidence)

    def update_score(
        self,
        current: ConfidenceScore,
        new_evidence: Sequence[EvidenceItem],
    ) -> ConfidenceScore:
        """Bayesian update of a confidence score with new evidence."""
        return update_score(current, new_evidence)

    def decay_confidence(
        self, score: ConfidenceScore, time_elapsed: float
    ) -> ConfidenceScore:
        """Apply time-based decay to a confidence score."""
        return decay_confidence(score, time_elapsed)

    def get_reliability_tier(self, score: ConfidenceScore) -> str:
        """Return the reliability tier string for a confidence score."""
        return get_reliability_tier(score)


def _evidence_weight(etype: EvidenceType) -> float:
    """Return the relative weight of an evidence type."""
    weights = {
        EvidenceType.SUCCESSFUL_USE: 0.25,
        EvidenceType.FAILED_USE: -0.4,
        EvidenceType.EXPERT_REVIEW: 0.3,
        EvidenceType.CROSS_VALIDATION: 0.2,
        EvidenceType.BENCHMARK: 0.35,
    }
    return weights.get(etype, 0.0)


def score(
    skill_id: str, evidence: Sequence[EvidenceItem]
) -> ConfidenceScore:
    """Compute a confidence score from a list of evidence items.

    Uses a weighted sum of evidence strengths with type-specific weights.
    Positive types increase score; negative types (FAILED_USE) decrease it.

    Args:
        skill_id: identifier for the skill being scored.
        evidence: sequence of evidence items.

    Returns:
        A ConfidenceScore with computed score and uncertainty.

    Raises:
        ValueError: if skill_id is empty.
    """
    if not skill_id.strip():
        raise ValueError("skill_id cannot be empty.")

    if not evidence:
        return ConfidenceScore(
            skill_id=skill_id,
            score=0.5,
            evidence_items=(),
            uncertainty=1.0,
        )

    weighted_sum = sum(
        e.strength * _evidence_weight(e.type) for e in evidence
    )
    raw_score = 0.5 + weighted_sum
    final_score = max(0.0, min(1.0, raw_score))

    n = len(evidence)
    uncertainty = round(
        max(0.0, min(1.0, 1.0 / (1.0 + math.log(n + 1)) * 1.5)), 4
    )

    return ConfidenceScore(
        skill_id=skill_id,
        score=round(final_score, 4),
        evidence_items=tuple(evidence),
        uncertainty=uncertainty,
    )


def update_score(
    current: ConfidenceScore,
    new_evidence: Sequence[EvidenceItem],
) -> ConfidenceScore:
    """Bayesian-inspired update of a confidence score with new evidence.

    Merges existing evidence with new evidence and recomputes the score.

    Args:
        current: the existing confidence score.
        new_evidence: new evidence items to incorporate.

    Returns:
        An updated ConfidenceScore reflecting the combined evidence.
    """
    combined = list(current.evidence_items) + list(new_evidence)
    result = score(current.skill_id, combined)

    blended_score = round(
        (current.score + result.score) / 2.0, 4
    )
    blended_uncertainty = round(
        (current.uncertainty + result.uncertainty) / 2.0, 4
    )

    return ConfidenceScore(
        skill_id=current.skill_id,
        score=blended_score,
        evidence_items=tuple(combined),
        uncertainty=blended_uncertainty,
    )


def decay_confidence(
    current: ConfidenceScore, time_elapsed: float
) -> ConfidenceScore:
    """Apply time-based decay to a confidence score.

    Confidence decays toward 0.5 (uncertain) as time passes.
    The decay follows an exponential approach to 0.5.

    Args:
        current: the existing confidence score.
        time_elapsed: time elapsed in arbitrary units (e.g. days).

    Returns:
        A ConfidenceScore with decay applied; uncertainty increases.
    """
    if time_elapsed <= 0:
        return current

    decay_factor = math.exp(-0.1 * time_elapsed)
    new_raw = decay_factor * (current.score - 0.5) + 0.5
    new_score = round(max(0.0, min(1.0, new_raw)), 4)

    new_uncertainty = round(
        max(0.0, min(1.0, current.uncertainty + 0.05 * time_elapsed)), 4
    )

    return ConfidenceScore(
        skill_id=current.skill_id,
        score=new_score,
        evidence_items=current.evidence_items,
        uncertainty=new_uncertainty,
    )


def get_reliability_tier(confidence_score: ConfidenceScore) -> str:
    """Determine the reliability tier of a confidence score.

    Tiers:
        - HIGH: score >= 0.8 and uncertainty < 0.4
        - MEDIUM: score >= 0.6
        - LOW: score >= 0.3
        - UNTRUSTED: score < 0.3

    Args:
        confidence_score: the score to tier.

    Returns:
        One of "HIGH", "MEDIUM", "LOW", "UNTRUSTED".
    """
    if (
        confidence_score.score >= 0.8
        and confidence_score.uncertainty < 0.4
    ):
        return "HIGH"
    if confidence_score.score >= 0.6:
        return "MEDIUM"
    if confidence_score.score >= 0.3:
        return "LOW"
    return "UNTRUSTED"
