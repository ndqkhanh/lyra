"""A-MAC 5-factor memory admission control.

Implements the A-MAC (Agentic Memory Admission Control) gate that scores
incoming memory candidates on five orthogonal factors before committing
them to long-term storage.

Factors (A-MAC paper, 2026):
  F1 — Utility: expected task-relevance of the memory
  F2 — Factual Confidence: verifier-assigned certainty score
  F3 — Semantic Novelty: cosine distance from nearest existing memory
  F4 — Temporal Recency: exponential decay from time of capture
  F5 — Content Type Prior: domain-specific base admission rate

The composite score combines all five factors with configurable weights.
Memories below the admission threshold are discarded or routed to a
low-confidence buffer for later re-evaluation.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Sequence


class ContentType(str, Enum):
    """Domain category for content-type prior (F5)."""

    FACT = "fact"
    SKILL = "skill"
    CONVERSATION = "conversation"
    CODE = "code"
    TOOL_OUTPUT = "tool_output"
    REFLECTION = "reflection"
    ERROR = "error"
    GOAL = "goal"


# Base admission priors per content type (F5 component).
_CONTENT_PRIORS: dict[ContentType, float] = {
    ContentType.FACT: 0.70,
    ContentType.SKILL: 0.85,
    ContentType.CONVERSATION: 0.40,
    ContentType.CODE: 0.55,
    ContentType.TOOL_OUTPUT: 0.35,
    ContentType.REFLECTION: 0.75,
    ContentType.ERROR: 0.60,
    ContentType.GOAL: 0.80,
}


@dataclass(frozen=True)
class AdmissionScore:
    """Composite admission result with per-factor breakdown."""

    utility: float
    confidence: float
    novelty: float
    recency: float
    content_prior: float
    composite: float
    admitted: bool

    def as_dict(self) -> dict:
        return {
            "utility": round(self.utility, 4),
            "confidence": round(self.confidence, 4),
            "novelty": round(self.novelty, 4),
            "recency": round(self.recency, 4),
            "content_prior": round(self.content_prior, 4),
            "composite": round(self.composite, 4),
            "admitted": self.admitted,
        }


@dataclass(frozen=True)
class AdmissionConfig:
    """Tunable weights and thresholds for A-MAC scoring.

    Attributes:
        w_utility: Weight for utility factor (F1).
        w_confidence: Weight for factual confidence (F2).
        w_novelty: Weight for semantic novelty (F3).
        w_recency: Weight for temporal recency (F4).
        w_content: Weight for content-type prior (F5).
        threshold: Composite score below which memories are rejected.
        recency_halflife_seconds: Half-life for exponential recency decay.
    """

    w_utility: float = 0.30
    w_confidence: float = 0.25
    w_novelty: float = 0.20
    w_recency: float = 0.15
    w_content: float = 0.10
    threshold: float = 0.50
    recency_halflife_seconds: float = 3600.0


@dataclass(frozen=True)
class MemoryCandidate:
    """A single memory under admission consideration."""

    content: str
    content_type: ContentType
    captured_at: float  # time.monotonic() timestamp
    utility_estimate: float  # 0.0–1.0, how relevant to active tasks
    confidence: float  # 0.0–1.0, verifier-assigned certainty


class AmacAdmissionGate:
    """5-factor memory admission control gate.

    Scores each candidate on utility, confidence, novelty, recency, and
    content-type prior. The composite is a weighted sum; candidates below
    ``threshold`` are rejected.

    Usage::

        gate = AmacAdmissionGate()
        score = gate.evaluate(candidate, existing_embeddings=[...])
        if score.admitted:
            store.commit(candidate)
    """

    def __init__(self, config: AdmissionConfig | None = None) -> None:
        self._config = config or AdmissionConfig()
        self._admitted_count: int = 0
        self._rejected_count: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        candidate: MemoryCandidate,
        *,
        existing_embeddings: Sequence[Sequence[float]] | None = None,
        now: float | None = None,
    ) -> AdmissionScore:
        """Score a candidate and return the full breakdown."""
        t = now if now is not None else time.monotonic()
        cfg = self._config

        f1 = self._score_utility(candidate)
        f2 = self._score_confidence(candidate)
        f3 = self._score_novelty(candidate, existing_embeddings or [])
        f4 = self._score_recency(candidate, t)
        f5 = self._score_content_prior(candidate)

        composite = (
            cfg.w_utility * f1
            + cfg.w_confidence * f2
            + cfg.w_novelty * f3
            + cfg.w_recency * f4
            + cfg.w_content * f5
        )
        admitted = composite >= cfg.threshold

        if admitted:
            self._admitted_count += 1
        else:
            self._rejected_count += 1

        return AdmissionScore(
            utility=f1,
            confidence=f2,
            novelty=f3,
            recency=f4,
            content_prior=f5,
            composite=composite,
            admitted=admitted,
        )

    @property
    def stats(self) -> dict:
        """Cumulative admission/rejection counts."""
        return {
            "admitted": self._admitted_count,
            "rejected": self._rejected_count,
            "total": self._admitted_count + self._rejected_count,
            "admit_rate": (
                self._admitted_count / max(self._admitted_count + self._rejected_count, 1)
            ),
        }

    # ------------------------------------------------------------------
    # Factor scorers
    # ------------------------------------------------------------------

    @staticmethod
    def _score_utility(candidate: MemoryCandidate) -> float:
        return max(0.0, min(1.0, candidate.utility_estimate))

    @staticmethod
    def _score_confidence(candidate: MemoryCandidate) -> float:
        return max(0.0, min(1.0, candidate.confidence))

    @staticmethod
    def _score_novelty(
        candidate: MemoryCandidate,
        existing_embeddings: Sequence[Sequence[float]],
    ) -> float:
        """1.0 if completely novel, 0.0 if identical to an existing memory."""
        if not existing_embeddings:
            return 1.0
        # Approximate embedding as character-bigram vector when no
        # external embedder is wired. Production deployments supply
        # real embeddings via a provider adapter.
        candidate_vec = _bigram_vector(candidate.content)
        max_sim = max(
            _cosine_similarity(candidate_vec, emb) for emb in existing_embeddings
        )
        return 1.0 - max(0.0, min(1.0, max_sim))

    def _score_recency(
        self, candidate: MemoryCandidate, now: float
    ) -> float:
        """Exponential decay: 1.0 at capture, 0.5 at half-life."""
        elapsed = now - candidate.captured_at
        if elapsed <= 0:
            return 1.0
        halflife = self._config.recency_halflife_seconds
        return 2.0 ** (-elapsed / halflife)

    @staticmethod
    def _score_content_prior(candidate: MemoryCandidate) -> float:
        return _CONTENT_PRIORS.get(candidate.content_type, 0.50)


# ------------------------------------------------------------------
# Embedding helpers (lightweight, no external deps)
# ------------------------------------------------------------------


def _bigram_vector(text: str, dim: int = 256) -> list[float]:
    """Project text to a fixed-dimension bigram-frequency vector."""
    vec = [0.0] * dim
    if len(text) < 2:
        return vec
    for i in range(len(text) - 1):
        idx = (ord(text[i]) * 31 + ord(text[i + 1])) % dim
        vec[idx] += 1.0
    norm = max(sum(v * v for v in vec) ** 0.5, 1e-8)
    return [v / norm for v in vec]


def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        n = min(len(a), len(b))
        a, b = list(a)[:n], list(b)[:n]
    dot = sum(ai * bi for ai, bi in zip(a, b))
    norm_a = sum(ai * ai for ai in a) ** 0.5
    norm_b = sum(bi * bi for bi in b) ** 0.5
    if norm_a < 1e-8 or norm_b < 1e-8:
        return 0.0
    return dot / (norm_a * norm_b)


__all__ = [
    "AdmissionConfig",
    "AdmissionScore",
    "AmacAdmissionGate",
    "ContentType",
    "MemoryCandidate",
]
