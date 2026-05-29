"""Importance Scoring System — Multi-factor element importance computation.

Provides TF-IDF, recency-weighted, task-relevance, dependency-based, and
ML-based importance scoring with configurable weight blending.
"""

from __future__ import annotations

import logging
import math
import re
import time
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)


# ── Exceptions ──────────────────────────────────────────────────────────────────


class ImportanceError(Exception):
    """Base exception for importance scoring errors."""


class InsufficientDataError(ImportanceError):
    """Raised when there is insufficient data to compute scores."""


# ── Types ───────────────────────────────────────────────────────────────────────


class ContextElementProtocol(Protocol):
    """Protocol for objects that can be importance-scored."""

    id: str
    content: str
    token_count: int
    recency: float
    access_count: int
    dependencies: list[str]
    created_at: float
    last_accessed_at: float


# ── Scoring Components ──────────────────────────────────────────────────────────


@dataclass
class ScoreWeights:
    """Configurable weights for combining importance score components.

    All weights should sum to approximately 1.0 for normalized output.
    """

    tfidf_weight: float = 0.25
    recency_weight: float = 0.20
    task_relevance_weight: float = 0.25
    dependency_weight: float = 0.15
    usage_weight: float = 0.10
    ml_weight: float = 0.05

    def __post_init__(self) -> None:
        total = (
            self.tfidf_weight
            + self.recency_weight
            + self.task_relevance_weight
            + self.dependency_weight
            + self.usage_weight
            + self.ml_weight
        )
        if abs(total - 1.0) > 0.01:
            logger.warning("ScoreWeights sum to %.3f, not 1.0 (will normalize)", total)

    def normalize(self) -> ScoreWeights:
        """Return a copy with weights normalized to sum to 1.0."""
        total = (
            self.tfidf_weight
            + self.recency_weight
            + self.task_relevance_weight
            + self.dependency_weight
            + self.usage_weight
            + self.ml_weight
        )
        if total == 0:
            return ScoreWeights()
        return ScoreWeights(
            tfidf_weight=self.tfidf_weight / total,
            recency_weight=self.recency_weight / total,
            task_relevance_weight=self.task_relevance_weight / total,
            dependency_weight=self.dependency_weight / total,
            usage_weight=self.usage_weight / total,
            ml_weight=self.ml_weight / total,
        )


# ── TF-IDF Calculator ───────────────────────────────────────────────────────────


class TfidfCalculator:
    """TF-IDF based importance scoring for text elements.

    Treats each context element as a document in a corpus of all elements.
    Higher TF-IDF scores indicate more distinctive (important) content.
    """

    def __init__(self):
        self._idf_cache: dict[str, float] = {}
        self._corpus_size: int = 0

    @staticmethod
    def tokenize(text: str) -> list[str]:
        """Tokenize text into lowercase word tokens."""
        return re.findall(r"\b[a-z]{3,}\b", text.lower())

    def fit(self, documents: list[str]) -> None:
        """Compute IDF values across the document corpus."""
        self._corpus_size = len(documents)
        doc_freq: dict[str, int] = defaultdict(int)

        for doc in documents:
            tokens = set(self.tokenize(doc))
            for token in tokens:
                doc_freq[token] += 1

        self._idf_cache = {
            token: math.log((self._corpus_size + 1) / (freq + 1)) + 1.0
            for token, freq in doc_freq.items()
        }

    def score(self, document: str) -> float:
        """Compute TF-IDF score for a single document against the corpus."""
        if self._corpus_size == 0:
            return 0.0

        tokens = self.tokenize(document)
        if not tokens:
            return 0.0

        tf = Counter(tokens)
        total = sum(tf.values())

        score = sum(
            (count / total) * self._idf_cache.get(token, 0.0) for token, count in tf.items()
        )

        return min(score, 1.0)  # Cap at 1.0


# ── Recency Scorer ──────────────────────────────────────────────────────────────


class RecencyScorer:
    """Recency-weighted scoring with configurable decay.

    Recent elements score higher; old elements decay exponentially.
    """

    def __init__(
        self,
        half_life_seconds: float = 300.0,  # 5 minutes
        boost_recent: bool = True,
    ):
        self._half_life = half_life_seconds
        self._decay_constant = math.log(2) / half_life_seconds
        self._boost_recent = boost_recent

    def score(self, element: ContextElementProtocol) -> float:
        """Compute recency score for an element."""
        now = time.time()
        age = now - element.last_accessed_at
        score = math.exp(-self._decay_constant * max(age, 0))

        if self._boost_recent and age < 60.0:  # Boost within first minute
            score = min(score * 1.2, 1.0)

        return score

    def score_batch(self, elements: list[ContextElementProtocol]) -> list[float]:
        """Compute recency scores for a batch of elements."""
        return [self.score(el) for el in elements]


# ── Task Relevance Scorer ───────────────────────────────────────────────────────


class TaskRelevanceScorer:
    """Scores elements by their relevance to the current task.

    Uses keyword overlap and semantic similarity heuristics.
    """

    def __init__(self):
        self._current_task_keywords: set[str] = set()
        self._keyword_weights: dict[str, float] = {}

    def set_task(self, task_description: str) -> None:
        """Set the current task and extract weighted keywords."""
        tokens = re.findall(r"\b[a-z]{3,}\b", task_description.lower())
        tf = Counter(tokens)
        max_freq = max(tf.values(), default=1)
        self._keyword_weights = {token: count / max_freq for token, count in tf.items()}
        self._current_task_keywords = set(tf.keys())

    def score(self, content: str) -> float:
        """Score content relevance to the current task."""
        if not self._current_task_keywords:
            return 0.5  # Neutral when no task is set

        content_tokens = set(re.findall(r"\b[a-z]{3,}\b", content.lower()))
        if not content_tokens:
            return 0.0

        overlap = content_tokens & self._current_task_keywords
        if not overlap:
            return 0.0

        weighted_score = sum(self._keyword_weights.get(token, 0.0) for token in overlap)
        # Normalize by content size and max possible score
        max_possible = len(content_tokens)
        return min(weighted_score / max(max_possible, 1), 1.0)


# ── Dependency Scorer ───────────────────────────────────────────────────────────


class DependencyScorer:
    """Scores elements based on their position in the dependency graph.

    Elements referenced by many others (high in-degree) are more important.
    Elements that reference many others (high out-degree) may be integrative.
    """

    def __init__(self):
        self._dependency_graph: dict[str, set[str]] = {}
        self._reverse_graph: dict[str, set[str]] = {}

    def build_graph(
        self,
        elements: Sequence[ContextElementProtocol],
    ) -> None:
        """Build the dependency graph from element dependency lists."""
        element_ids = {el.id for el in elements}
        self._dependency_graph = {}
        self._reverse_graph = defaultdict(set)

        for element in elements:
            self._dependency_graph[element.id] = {
                dep for dep in element.dependencies if dep in element_ids
            }
            for dep in self._dependency_graph[element.id]:
                self._reverse_graph[dep].add(element.id)

    def score(self, element_id: str) -> float:
        """Compute dependency-based importance score."""
        # In-degree: how many elements depend on this one
        in_degree = len(self._reverse_graph.get(element_id, set()))

        # Compute total element count for normalization
        set(self._dependency_graph.keys()) | set(self._reverse_graph.keys())
        max_in_degree = max(
            (len(v) for v in self._reverse_graph.values()),
            default=1,
        )

        if max_in_degree == 0:
            return 0.0

        return min(in_degree / max_in_degree, 1.0)

    def score_batch(self, element_ids: list[str]) -> dict[str, float]:
        """Score multiple elements at once."""
        return {eid: self.score(eid) for eid in element_ids}


# ── ML Importance Predictor ─────────────────────────────────────────────────────


class MLImportancePredictor:
    """Lightweight ML-based importance prediction using heuristics.

    This is a simple linear model that can be replaced with a full ML
    pipeline (e.g., scikit-learn, ONNX) for production deployments.
    """

    def __init__(self):
        self._weights: dict[str, float] = {
            "token_count": 0.1,
            "access_count": 0.2,
            "recency": 0.15,
            "dependency_count": 0.2,
            "content_length": 0.05,
            "unique_word_ratio": 0.15,
            "keyword_density": 0.15,
        }
        self._fitted: bool = False

    def fit(
        self,
        features: list[dict[str, float]],
        labels: list[float],
    ) -> None:
        """Fit the linear model using simple gradient descent.

        In production, replace with scikit-learn or pytorch.
        """
        if len(features) != len(labels) or len(features) == 0:
            raise InsufficientDataError("Features and labels must be non-empty and equal length")

        learning_rate = 0.01
        epochs = 100

        for _ in range(epochs):
            for feat_vec, label in zip(features, labels, strict=False):
                prediction = self._predict_raw(feat_vec)
                error = label - prediction

                for key in self._weights:
                    if key in feat_vec:
                        self._weights[key] += learning_rate * error * feat_vec[key]

        self._fitted = True
        logger.info("ML predictor fitted on %d samples", len(features))

    def predict(self, features: dict[str, float]) -> float:
        """Predict importance score from features."""
        raw = self._predict_raw(features)
        return max(0.0, min(raw, 1.0))  # Clamp to [0, 1]

    def _predict_raw(self, features: dict[str, float]) -> float:
        return sum(self._weights.get(key, 0.0) * value for key, value in features.items())

    @staticmethod
    def extract_features(element: ContextElementProtocol) -> dict[str, float]:
        """Extract feature vector from a context element."""
        words = len(re.findall(r"\b[a-z]+\b", element.content.lower()))
        unique_words = len(set(re.findall(r"\b[a-z]+\b", element.content.lower())))

        return {
            "token_count": float(element.token_count),
            "access_count": float(element.access_count),
            "recency": element.recency,
            "dependency_count": float(len(element.dependencies)),
            "content_length": float(len(element.content)),
            "unique_word_ratio": unique_words / max(words, 1),
            "keyword_density": words / max(len(element.content), 1),
        }


# ── Importance Calculator ───────────────────────────────────────────────────────


class ImportanceCalculator:
    """Orchestrates multi-factor importance scoring for context elements.

    Combines TF-IDF, recency, task relevance, dependency, usage, and ML
    scores using configurable weights. This is the primary API for
    computing element importance.

    Usage::

        calc = ImportanceCalculator(weights=ScoreWeights())
        calc.set_task("Implement user authentication module")
        scores = await calc.score_batch(elements)
    """

    def __init__(self, weights: ScoreWeights | None = None):
        self._weights = (weights or ScoreWeights()).normalize()
        self._tfidf = TfidfCalculator()
        self._recency = RecencyScorer()
        self._task = TaskRelevanceScorer()
        self._dependency = DependencyScorer()
        self._ml = MLImportancePredictor()

        self._score_history: list[dict[str, float]] = []
        self._compute_count: int = 0

    def set_task(self, task_description: str) -> None:
        """Set the current task for relevance scoring."""
        self._task.set_task(task_description)

    def set_weights(self, weights: ScoreWeights) -> None:
        """Update scoring weights."""
        self._weights = weights.normalize()

    async def score_batch(
        self,
        elements: Sequence[ContextElementProtocol],
    ) -> dict[str, float]:
        """Score a batch of context elements.

        Returns a mapping of element_id to importance_score (0.0 to 1.0).
        """
        if not elements:
            return {}

        elements_list = list(elements)
        self._compute_count += 1

        # 1. TF-IDF scores
        documents = [el.content for el in elements_list]
        self._tfidf.fit(documents)
        tfidf_scores = {el.id: self._tfidf.score(el.content) for el in elements_list}

        # 2. Recency scores
        recency_scores = {el.id: self._recency.score(el) for el in elements_list}

        # 3. Task relevance scores
        task_scores = {el.id: self._task.score(el.content) for el in elements_list}

        # 4. Dependency scores
        self._dependency.build_graph(elements_list)
        dep_scores = self._dependency.score_batch([el.id for el in elements_list])

        # 5. Usage scores (based on access count)
        max_access = max(max((el.access_count for el in elements_list), default=1), 1)
        usage_scores = {el.id: min(el.access_count / max_access, 1.0) for el in elements_list}

        # 6. ML scores
        ml_scores = {el.id: self._ml.predict(self._ml.extract_features(el)) for el in elements_list}

        # Combine using configured weights
        final_scores: dict[str, float] = {}
        for el in elements_list:
            score = (
                self._weights.tfidf_weight * tfidf_scores.get(el.id, 0.0)
                + self._weights.recency_weight * recency_scores.get(el.id, 0.0)
                + self._weights.task_relevance_weight * task_scores.get(el.id, 0.0)
                + self._weights.dependency_weight * dep_scores.get(el.id, 0.0)
                + self._weights.usage_weight * usage_scores.get(el.id, 0.0)
                + self._weights.ml_weight * ml_scores.get(el.id, 0.0)
            )
            final_scores[el.id] = max(0.0, min(score, 1.0))

        # Record component scores for analysis
        if len(elements_list) <= 100:  # Don't bloat history with huge batches
            self._score_history.append(
                {
                    "batch": self._compute_count,
                    "avg_tfidf": sum(tfidf_scores.values()) / max(len(tfidf_scores), 1),
                    "avg_recency": sum(recency_scores.values()) / max(len(recency_scores), 1),
                    "avg_task": sum(task_scores.values()) / max(len(task_scores), 1),
                    "avg_combined": sum(final_scores.values()) / max(len(final_scores), 1),
                }
            )

        return final_scores

    async def score_single(
        self,
        element: ContextElementProtocol,
        corpus: list[ContextElementProtocol] | None = None,
    ) -> float:
        """Score a single element, optionally against a corpus."""
        if corpus:
            batch = list(corpus) + [element]
        else:
            batch = [element]
        scores = await self.score_batch(batch)
        return scores.get(element.id, 0.0)

    def get_score_breakdown(
        self,
        element: ContextElementProtocol,
    ) -> dict[str, float]:
        """Get the component-wise score breakdown for a single element."""
        documents = [element.content]
        self._tfidf.fit(documents)

        return {
            "tfidf": self._tfidf.score(element.content),
            "recency": self._recency.score(element),
            "task_relevance": self._task.score(element.content),
            "dependency": self._dependency.score(element.id),
            "usage": min(element.access_count / max(element.access_count, 1), 1.0),
            "ml": self._ml.predict(self._ml.extract_features(element)),
        }

    # ── Weight Management ───────────────────────────────────────────────────

    def calibrate_weights_from_history(self) -> ScoreWeights:
        """Auto-calibrate weights based on score variance in history.

        Higher variance components get lower weights (they are less stable).
        """
        if len(self._score_history) < 3:
            return self._weights

        variances: dict[str, float] = {}
        for key in ["avg_tfidf", "avg_recency", "avg_task"]:
            values = [h[key] for h in self._score_history if key in h]
            if len(values) > 1:
                mean = sum(values) / len(values)
                var = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
                variances[key] = var

        if not variances:
            return self._weights

        # Inverse variance weighting
        total_inv_var = sum(1.0 / max(v, 1e-6) for v in variances.values())
        if total_inv_var == 0:
            return self._weights

        new_weights = ScoreWeights(
            tfidf_weight=(1.0 / max(variances.get("avg_tfidf", 1.0), 1e-6)) / total_inv_var * 0.6,
            recency_weight=(1.0 / max(variances.get("avg_recency", 1.0), 1e-6))
            / total_inv_var
            * 0.4,
            task_relevance_weight=(1.0 / max(variances.get("avg_task", 1.0), 1e-6))
            / total_inv_var
            * 0.5,
            dependency_weight=0.15,
            usage_weight=0.10,
            ml_weight=0.05,
        )
        self.set_weights(new_weights)
        return new_weights

    @property
    def compute_count(self) -> int:
        return self._compute_count

    @property
    def current_weights(self) -> ScoreWeights:
        return self._weights
