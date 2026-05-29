"""Layer 4 — Continuous Monitoring.

Implements:
- Rolling mean computation (7-day window)
- Sigma-based drift detection
- PAEF seven failure mode checks
- KG structural difference comparison
- PULSE-style user satisfaction aggregation with confidence intervals
"""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence

from lyra_verification.models import (
    DriftAlert,
    DriftReport,
    PAEFFailure,
)

logger = logging.getLogger(__name__)


class ContinuousMonitor:
    """Layer 4 continuous monitoring.

    Tracks metrics over time, detects drift, checks PAEF failure modes,
    compares knowledge graphs, and aggregates user satisfaction.
    """

    def __init__(self) -> None:
        self._history: dict[str, list[float]] = {}

    def record_metric(self, name: str, value: float) -> None:
        """Record a metric value for later analysis."""
        if name not in self._history:
            self._history[name] = []
        self._history[name].append(value)

    # ------------------------------------------------------------------
    # Rolling mean
    # ------------------------------------------------------------------
    def compute_rolling_mean(
        self,
        metric: str,
        window: int = 7,
    ) -> float | None:
        """Compute a rolling mean over the last *window* data points.

        Returns None if insufficient data is available.
        """
        values = self._history.get(metric, [])
        if len(values) < window:
            return None
        return sum(values[-window:]) / window

    # ------------------------------------------------------------------
    # Drift detection
    # ------------------------------------------------------------------
    def detect_drift(
        self,
        metric: str,
        current_value: float,
        threshold: float = 1.5,
    ) -> DriftAlert | None:
        """Detect drift via z-score (sigma-based) relative to historical data.

        Parameters
        ----------
        metric : str
            The metric name to check.
        current_value : float
            The most recent observation.
        threshold : float
            Number of standard deviations before an alert fires (default 1.5).

        Returns
        -------
        DriftAlert or None
            An alert if |z-score| >= threshold; otherwise None.
        """
        values = self._history.get(metric)
        if not values or len(values) < 3:
            return None

        n = len(values)
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / max(n - 1, 1)
        std = math.sqrt(variance)

        if std == 0.0:
            # No variance — any deviation is significant
            if current_value != mean:
                return DriftAlert(
                    metric=metric,
                    rolling_mean=mean,
                    current_value=current_value,
                    deviation_sigma=float("inf"),
                    threshold=threshold,
                )
            return None

        z = (current_value - mean) / std
        if abs(z) >= threshold:
            return DriftAlert(
                metric=metric,
                rolling_mean=mean,
                current_value=current_value,
                deviation_sigma=abs(z),
                threshold=threshold,
            )
        return None

    # ------------------------------------------------------------------
    # PAEF failure mode checks
    # ------------------------------------------------------------------
    def check_paef_failures(
        self,
        agent_outputs: Sequence[str],
    ) -> dict[PAEFFailure, float]:
        """Score each of the seven PAEF failure modes.

        Each failure mode is scored in [0, 1] where higher = more likely
        that the failure is occurring.

        Returns
        -------
        dict mapping PAEFFailure -> float
        """
        scores: dict[PAEFFailure, float] = {}
        all_text = " ".join(agent_outputs) if agent_outputs else ""
        words = all_text.split() if all_text else []
        n_words = len(words)

        if n_words == 0:
            return dict.fromkeys(PAEFFailure, 0.0)

        # Perplexity: high OOV rate or repetitive tokens
        unique_ratio = len({w.lower() for w in words}) / max(n_words, 1)
        scores[PAEFFailure.PERPLEXITY] = 1.0 - min(unique_ratio * 2, 1.0)

        # Accuracy: contradiction ratio (presence of "however", "but", etc.)
        contradictions = sum(
            1 for w in words
            if w.lower() in ("however", "but", "although", "nevertheless",
                             "conversely", "contrary")
        )
        scores[PAEFFailure.ACCURACY] = min(contradictions / max(n_words, 1) * 10, 1.0)

        # Entity hallucination
        scores[PAEFFailure.ENTITY_HALLUCINATION] = (
            1.0 - unique_ratio * 0.5
        )

        # Faithfulness: hedging ratio
        hedges = {"maybe", "perhaps", "possibly", "might", "could",
                   "seems", "appears", "likely", "probably", "sort of"}
        hedging = sum(1 for w in words if w.lower() in hedges)
        scores[PAEFFailure.FAITHFULNESS] = min(hedging / max(n_words, 1) * 20, 1.0)

        # Consistency: pronoun-switch ratio
        first_person = {"i", "we", "me", "us"}
        third_person = {"he", "she", "it", "they", "them"}
        fp_count = sum(1 for w in words if w.lower() in first_person)
        tp_count = sum(1 for w in words if w.lower() in third_person)
        total = fp_count + tp_count
        if total > 0:
            switch_ratio = min(fp_count, tp_count) / total
        else:
            switch_ratio = 0.0
        scores[PAEFFailure.CONSISTENCY] = switch_ratio

        # Coherence: average sentence length (too short = choppy, too long = run-on)
        sentences = [
            s.strip()
            for out in agent_outputs
            for s in out.replace("!", ".").replace("?", ".").split(".")
            if s.strip()
        ]
        if sentences:
            avg_sent_len = sum(len(s.split()) for s in sentences) / len(sentences)
            coherence_penalty = 0.0
            if avg_sent_len < 5 or avg_sent_len > 40:
                coherence_penalty = min(
                    1.0,
                    abs(avg_sent_len - 15) / 30.0,
                )
            scores[PAEFFailure.COHERENCE] = coherence_penalty
        else:
            scores[PAEFFailure.COHERENCE] = 0.5

        # Safety: toxicity / injection proxy
        toxicity_keywords = {"hate", "kill", "violent", "attack", "dangerous",
                              "illegal", "weapon", "bomb", "hurt", "destroy"}
        toks = sum(1 for w in words if w.lower() in toxicity_keywords)
        scores[PAEFFailure.SAFETY] = min(toks / max(n_words, 1) * 50, 1.0)

        return scores

    # ------------------------------------------------------------------
    # KG structural diff
    # ------------------------------------------------------------------
    def compute_kg_structural_diff(
        self,
        kg_a: dict[str, set[tuple[str, str]]],
        kg_b: dict[str, set[tuple[str, str]]],
    ) -> dict[str, float]:
        """Compare two knowledge graphs structurally.

        Parameters
        ----------
        kg_a : dict
            First KG: entity -> set of (relation, object).
        kg_b : dict
            Second KG: same structure.

        Returns
        -------
        dict with keys:
            jaccard_entities : overlap in entity sets.
            jaccard_triples : overlap in triple sets.
            entity_additions / entity_removals : count differences.
            structural_similarity : combined score (0–1).
        """
        entities_a = set(kg_a.keys())
        entities_b = set(kg_b.keys())

        jaccard_entities = (
            len(entities_a & entities_b) / max(len(entities_a | entities_b), 1)
        )

        triples_a: set[tuple[str, str, str]] = set()
        for entity, rels in kg_a.items():
            for rel, obj in rels:
                triples_a.add((entity, rel, obj))

        triples_b: set[tuple[str, str, str]] = set()
        for entity, rels in kg_b.items():
            for rel, obj in rels:
                triples_b.add((entity, rel, obj))

        jaccard_triples = (
            len(triples_a & triples_b) / max(len(triples_a | triples_b), 1)
        )

        added_entities = len(entities_b - entities_a)
        removed_entities = len(entities_a - entities_b)

        # Structural similarity: harmonic mean of entity + triple Jaccard
        s = jaccard_entities + jaccard_triples
        structural_similarity = s / 2.0 if s > 0 else 1.0

        return {
            "jaccard_entities": jaccard_entities,
            "jaccard_triples": jaccard_triples,
            "entity_additions": float(added_entities),
            "entity_removals": float(removed_entities),
            "structural_similarity": structural_similarity,
        }

    # ------------------------------------------------------------------
    # User satisfaction (PULSE-style)
    # ------------------------------------------------------------------
    def aggregate_user_satisfaction(
        self,
        feedback: Sequence[float],
        confidence_level: float = 0.95,
    ) -> dict[str, float]:
        """PULSE-style user satisfaction aggregation.

        Computes mean, standard deviation, and confidence interval for
        a sequence of user feedback scores.

        Parameters
        ----------
        feedback : sequence of float
            Individual satisfaction ratings (typically 0–1 or 1–5).
        confidence_level : float
            Desired confidence level (default 0.95).

        Returns
        -------
        dict with keys:
            mean, std, n, ci_lower, ci_upper, margin_of_error.
        """
        if not feedback:
            return {
                "mean": 0.0,
                "std": 0.0,
                "n": 0.0,
                "ci_lower": 0.0,
                "ci_upper": 0.0,
                "margin_of_error": 0.0,
            }

        n = len(feedback)
        mean = sum(feedback) / n
        variance = sum((x - mean) ** 2 for x in feedback) / max(n - 1, 1)
        std = math.sqrt(variance)

        # Z-score for confidence level (simplified)
        z_scores = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
        z = z_scores.get(confidence_level, 1.96)

        se = std / math.sqrt(n)
        moe = z * se

        return {
            "mean": mean,
            "std": std,
            "n": float(n),
            "ci_lower": mean - moe,
            "ci_upper": mean + moe,
            "margin_of_error": moe,
        }

    # ------------------------------------------------------------------
    # Aggregated drift report
    # ------------------------------------------------------------------
    def generate_drift_report(
        self,
        current_metrics: dict[str, float],
        drift_threshold: float = 1.5,
    ) -> DriftReport:
        """Generate a comprehensive drift report from current metric values."""
        alerts: list[DriftAlert] = []

        for metric, value in current_metrics.items():
            alert = self.detect_drift(metric, value, threshold=drift_threshold)
            if alert is not None:
                alerts.append(alert)

        total = len(current_metrics)
        triggered = len(alerts)
        return DriftReport(
            alerts=alerts,
            alerts_triggered=triggered,
            total_metrics=total,
            overall_stable=triggered == 0,
        )
