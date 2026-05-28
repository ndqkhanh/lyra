"""Tests for A-MAC 5-factor admission control gate.

Covers:
  1. Content type priors are within [0, 1]
  2. Utility score clamped to [0, 1]
  3. Confidence score clamped to [0, 1]
  4. Novelty = 1.0 when no existing embeddings
  5. Novelty decreases for similar content
  6. Recency decays exponentially with age
  7. Content prior maps correctly per type
  8. Full composite admits above threshold, rejects below
  9. Stats accumulate correctly
 10. Empty existing embeddings yield novelty = 1.0
"""
from __future__ import annotations

import math
import time

from lyra_memory.amac_admission import (
    AdmissionConfig,
    AmacAdmissionGate,
    ContentType,
    MemoryCandidate,
    _bigram_vector,
    _cosine_similarity,
)

# ------------------------------------------------------------------
# Factor unit tests
# ------------------------------------------------------------------


def test_utility_clamped() -> None:
    gate = AmacAdmissionGate()
    c = MemoryCandidate("x", ContentType.FACT, 0.0, 1.5, 0.9)
    assert gate._score_utility(c) == 1.0
    c2 = MemoryCandidate("x", ContentType.FACT, 0.0, -0.3, 0.9)
    assert gate._score_utility(c2) == 0.0


def test_confidence_clamped() -> None:
    gate = AmacAdmissionGate()
    c = MemoryCandidate("x", ContentType.FACT, 0.0, 0.5, 1.2)
    assert gate._score_confidence(c) == 1.0
    c2 = MemoryCandidate("x", ContentType.FACT, 0.0, 0.5, -0.1)
    assert gate._score_confidence(c2) == 0.0


def test_novelty_empty_embeddings_is_one() -> None:
    gate = AmacAdmissionGate()
    c = MemoryCandidate("hello", ContentType.FACT, 0.0, 0.5, 0.5)
    assert gate._score_novelty(c, []) == 1.0


def test_novelty_identical_content_is_zero() -> None:
    gate = AmacAdmissionGate()
    text = "the quick brown fox"
    emb = _bigram_vector(text)
    c = MemoryCandidate(text, ContentType.FACT, 0.0, 0.5, 0.5)
    score = gate._score_novelty(c, [emb])
    assert score < 0.01, f"Expected ~0 for identical content, got {score}"


def test_novelty_different_content_is_high() -> None:
    gate = AmacAdmissionGate()
    emb = _bigram_vector("python programming language")
    c = MemoryCandidate("javascript frontend framework", ContentType.CODE, 0.0, 0.5, 0.5)
    score = gate._score_novelty(c, [emb])
    assert score > 0.5, f"Expected >0.5 for different content, got {score}"


def test_recency_zero_elapsed_is_one() -> None:
    gate = AmacAdmissionGate()
    c = MemoryCandidate("x", ContentType.FACT, 100.0, 0.5, 0.5)
    assert gate._score_recency(c, now=100.0) == 1.0


def test_recency_at_halflife_is_half() -> None:
    gate = AmacAdmissionGate()
    c = MemoryCandidate("x", ContentType.FACT, 0.0, 0.5, 0.5)
    halflife = gate._config.recency_halflife_seconds
    score = gate._score_recency(c, now=halflife)
    assert abs(score - 0.5) < 1e-9


def test_recency_decays_exponentially() -> None:
    gate = AmacAdmissionGate()
    c = MemoryCandidate("x", ContentType.FACT, 0.0, 0.5, 0.5)
    halflife = gate._config.recency_halflife_seconds
    s1 = gate._score_recency(c, now=halflife)
    s2 = gate._score_recency(c, now=2 * halflife)
    assert abs(s1 - 0.5) < 1e-9
    assert abs(s2 - 0.25) < 1e-9


def test_content_prior_fact() -> None:
    gate = AmacAdmissionGate()
    c = MemoryCandidate("x", ContentType.FACT, 0.0, 0.5, 0.5)
    assert gate._score_content_prior(c) == 0.70


def test_content_prior_skill() -> None:
    gate = AmacAdmissionGate()
    c = MemoryCandidate("x", ContentType.SKILL, 0.0, 0.5, 0.5)
    assert gate._score_content_prior(c) == 0.85


def test_content_prior_conversation() -> None:
    gate = AmacAdmissionGate()
    c = MemoryCandidate("x", ContentType.CONVERSATION, 0.0, 0.5, 0.5)
    assert gate._score_content_prior(c) == 0.40


# ------------------------------------------------------------------
# Composite / integration
# ------------------------------------------------------------------


def test_high_quality_memory_admitted() -> None:
    gate = AmacAdmissionGate()
    c = MemoryCandidate(
        "important security finding",
        ContentType.FACT,
        captured_at=time.monotonic() - 10,
        utility_estimate=0.9,
        confidence=0.95,
    )
    score = gate.evaluate(c)
    assert score.admitted
    assert score.composite > 0.70


def test_low_quality_memory_rejected() -> None:
    gate = AmacAdmissionGate(
        config=AdmissionConfig(threshold=0.80)
    )
    c = MemoryCandidate(
        "chatty conversation filler",
        ContentType.CONVERSATION,
        captured_at=time.monotonic() - 7200,  # 2 hours old
        utility_estimate=0.1,
        confidence=0.2,
    )
    score = gate.evaluate(c)
    assert not score.admitted
    assert score.composite < 0.80


def test_stats_accumulate() -> None:
    gate = AmacAdmissionGate()
    good = MemoryCandidate("good", ContentType.GOAL, 0.0, 1.0, 1.0)
    bad = MemoryCandidate(
        "bad", ContentType.CONVERSATION,
        captured_at=time.monotonic() - 1_000_000,
        utility_estimate=0.0,
        confidence=0.0,
    )
    gate.evaluate(good, now=0.1)
    gate.evaluate(bad, now=1_000_001)
    s = gate.stats
    assert s["admitted"] == 1
    assert s["rejected"] == 1
    assert s["total"] == 2
    assert 0.45 < s["admit_rate"] < 0.55


def test_custom_config_weights_sum_to_composite() -> None:
    cfg = AdmissionConfig(
        w_utility=0.50,
        w_confidence=0.30,
        w_novelty=0.20,
        w_recency=0.0,
        w_content=0.0,
        threshold=0.40,
    )
    gate = AmacAdmissionGate(config=cfg)
    c = MemoryCandidate("x", ContentType.FACT, 0.0, 0.6, 0.8)
    score = gate.evaluate(c, existing_embeddings=[])
    # f1=0.6, f2=0.8, f3=1.0, f4=1.0, f5=0.7
    expected = 0.5 * 0.6 + 0.3 * 0.8 + 0.2 * 1.0
    assert abs(score.composite - expected) < 1e-9


def test_score_as_dict_rounds() -> None:
    gate = AmacAdmissionGate()
    c = MemoryCandidate("x", ContentType.FACT, 0.0, 0.5, 0.5)
    score = gate.evaluate(c, existing_embeddings=[])
    d = score.as_dict()
    for key in ("utility", "confidence", "novelty", "recency", "content_prior", "composite"):
        assert key in d
        assert isinstance(d[key], float)
    assert isinstance(d["admitted"], bool)


# ------------------------------------------------------------------
# Embedding helpers
# ------------------------------------------------------------------


def test_bigram_vector_empty_text() -> None:
    v = _bigram_vector("", dim=64)
    assert all(x == 0.0 for x in v)


def test_bigram_vector_short_text() -> None:
    v = _bigram_vector("a", dim=64)
    assert all(x == 0.0 for x in v)


def test_bigram_vector_unit_norm() -> None:
    v = _bigram_vector("hello world", dim=128)
    norm = math.sqrt(sum(x * x for x in v))
    assert abs(norm - 1.0) < 1e-9


def test_cosine_similarity_identical() -> None:
    a = [1.0, 2.0, 3.0]
    assert abs(_cosine_similarity(a, a) - 1.0) < 1e-9


def test_cosine_similarity_orthogonal() -> None:
    a = [1.0, 0.0, 0.0]
    b = [0.0, 1.0, 0.0]
    assert abs(_cosine_similarity(a, b) - 0.0) < 1e-9


def test_cosine_similarity_zero_vector() -> None:
    assert _cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0
    assert _cosine_similarity([1.0, 2.0], [0.0, 0.0]) == 0.0


def test_cosine_similarity_different_lengths() -> None:
    # Should truncate to min length
    s = _cosine_similarity([1.0, 0.0, 9.0], [1.0, 0.0])
    assert abs(s - 1.0) < 1e-9
