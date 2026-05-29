"""Frozen dataclasses for the 4-layer verification architecture."""

from __future__ import annotations

import enum
from collections.abc import Sequence
from dataclasses import dataclass, field


class Verdict(enum.Enum):
    """Three-valued verdicts per AgentAssay: PASS, FAIL, INCONCLUSIVE."""

    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"

    @classmethod
    def from_float(cls, score: float, threshold: float = 0.5) -> Verdict:
        """Map a score in [0, 1] to a three-valued verdict.

        Parameters
        ----------
        score : float
            Continuous score, typically 0 (worst) to 1 (best).
        threshold : float, optional
            Decision boundary (default 0.5).

        Returns
        -------
        Verdict
            FAIL if score < threshold - 0.15, PASS if score >= threshold + 0.15,
            INCONCLUSIVE otherwise.
        """
        if score < threshold - 0.15:
            return cls.FAIL
        if score >= threshold + 0.15:
            return cls.PASS
        return cls.INCONCLUSIVE


class PAEFFailure(enum.Enum):
    """Seven production failure modes from PAEF taxon omy."""

    PERPLEXITY = "perplexity"
    ACCURACY = "accuracy"
    ENTITY_HALLUCINATION = "entity_hallucination"
    FAITHFULNESS = "faithfulness"
    CONSISTENCY = "consistency"
    COHERENCE = "coherence"
    SAFETY = "safety"


@dataclass(frozen=True)
class SecurityCheck:
    """Result of a single security / inline guard check."""

    check_type: str
    passed: bool
    details: str


@dataclass(frozen=True)
class VerificationResult:
    """Single verification outcome at any layer.

    Attributes
    ----------
    layer : int
        Verification layer (1–4).
    verdict : Verdict
        Three-valued result.
    confidence : float
        Model confidence in the verdict (0–1).
    evidence : str
        Human-readable justification.
    latency_ms : float
        Wall-clock time spent in verification, in milliseconds.
    checks : Sequence[SecurityCheck], optional
        Per-check details from inline guards.
    """

    layer: int
    verdict: Verdict
    confidence: float
    evidence: str
    latency_ms: float = 0.0
    checks: Sequence[SecurityCheck] = field(default_factory=list)


@dataclass(frozen=True)
class AttributionEigenvalues:
    """Spectral decomposition of attention for interpretability."""

    eigenvalues: Sequence[float]
    spectral_gap: float
    effective_rank: int


@dataclass(frozen=True)
class EntityGrounding:
    """Result of verifying a named entity against a knowledge graph."""

    entity: str
    present_in_kg: bool
    supporting_triples: Sequence[tuple[str, str, str]] = field(default_factory=list)
    confidence: float = 0.0


@dataclass(frozen=True)
class HallucinationSignal:
    """Multi-signal hallucination detection output.

    Attributes
    ----------
    token_uncertainty : float
        Normalised mean token entropy (HaMI signal).
    attention_eigenvalues : AttributionEigenvalues, optional
        Spectral decomposition of attention matrix (LapEigvals).
    entity_groundings : Sequence[EntityGrounding]
        Per-entity grounding against KG.
    relation_preservation : float
        BERTscore / relation overlap between output and reference.
    hybrid_score : float
        Combined multi-signal score in [0, 1]; higher = more likely hallucinated.
    """

    token_uncertainty: float = 0.0
    attention_eigenvalues: AttributionEigenvalues | None = None
    entity_groundings: Sequence[EntityGrounding] = field(default_factory=list)
    relation_preservation: float = 0.0
    hybrid_score: float = 0.0


@dataclass(frozen=True)
class CitationAudit:
    """Single citation check — the three-score model.

    57 % of citations can fail faithfulness while passing correctness,
    so both axes are reported independently.
    """

    claim: str
    citation_url: str
    correctness_score: float  # 0–1; does the claim match the source?
    faithfulness_score: float  # 0–1; does the source support the claim?
    coverage_score: float = 0.0  # 0–1; how much of the claim is covered?


@dataclass(frozen=True)
class DriftAlert:
    """Statistical drift detection alert."""

    metric: str
    rolling_mean: float
    current_value: float
    deviation_sigma: float
    threshold: float


@dataclass(frozen=True)
class JudgeEvaluation:
    """Output from a single judge evaluation pass."""

    score: float
    rationale: str
    criteria: str
    is_debiased: bool = False


@dataclass(frozen=True)
class BehavioralFingerprint:
    """Behavioural profile for regression testing."""

    metrics: dict[str, float] = field(default_factory=dict)
    sample_size: int = 0

    def cosine_similarity(self, other: BehavioralFingerprint) -> float:
        """Compute cosine similarity between two fingerprints."""
        common_keys = set(self.metrics) & set(other.metrics)
        if not common_keys:
            return 0.0
        dot = sum(self.metrics[k] * other.metrics[k] for k in common_keys)
        norm_a = sum(v * v for v in self.metrics.values()) ** 0.5
        norm_b = sum(v * v for v in other.metrics.values()) ** 0.5
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)


@dataclass(frozen=True)
class RegressionVerdict:
    """Outcome of a single regression test."""

    test_name: str
    passed: bool
    similarity: float
    details: str


@dataclass(frozen=True)
class DriftReport:
    """Aggregated drift report for a window."""

    alerts: Sequence[DriftAlert] = field(default_factory=list)
    alerts_triggered: int = 0
    total_metrics: int = 0
    overall_stable: bool = True
