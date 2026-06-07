"""Dissent Detector — Detects and classifies model disagreement patterns.

Identifies when multiple models disagree on outputs, classifies the type
of dissent, and triggers appropriate escalation strategies.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class DissentType(StrEnum):
    """Types of model disagreement."""

    NONE = "none"                    # All models agree
    FACTUAL = "factual"             # Disagree on facts/answers
    STYLISTIC = "stylistic"         # Agree on content, differ in presentation
    STRUCTURAL = "structural"       # Different code/architecture approaches
    CONFIDENCE_GAP = "confidence_gap"  # Same answer, different confidence
    COMPLETE = "complete"           # Completely different answers


class DissentSeverity(StrEnum):
    """Severity levels for model dissent."""

    NONE = "none"
    LOW = "low"        # Minor stylistic differences
    MEDIUM = "medium"  # Different approaches, both valid
    HIGH = "high"      # Significant factual disagreement
    CRITICAL = "critical"  # Safety/security-relevant disagreement


@dataclass(frozen=True)
class DissentReport:
    """Report on model disagreement analysis."""

    dissent_type: DissentType
    severity: DissentSeverity
    agreement_score: float  # 0.0-1.0
    disagreeing_models: tuple[str, ...]
    agreeing_models: tuple[str, ...]
    areas_of_disagreement: tuple[str, ...]
    recommended_action: str
    needs_human_review: bool = False
    needs_escalation: bool = False
    needs_more_models: bool = False


class DissentDetector:
    """Detects and classifies disagreement across multiple model outputs.

    Analyzes model verdicts to identify when models disagree, classify
    the disagreement type, assess severity, and recommend escalation actions.

    Usage::

        detector = DissentDetector()
        verdicts = [verdict1, verdict2, verdict3]
        report = detector.detect(verdicts)
        if report.severity == DissentSeverity.CRITICAL:
            escalate_for_human_review()
    """

    def __init__(
        self,
        factual_dissent_threshold: float = 0.3,
        structural_dissent_threshold: float = 0.5,
        critical_dissent_threshold: float = 0.2,
    ) -> None:
        self.factual_dissent_threshold = factual_dissent_threshold
        self.structural_dissent_threshold = structural_dissent_threshold
        self.critical_dissent_threshold = critical_dissent_threshold
        self._history: list[DissentReport] = []

    def detect(self, outputs: list[dict[str, Any]]) -> DissentReport:
        """Analyze model outputs for dissent patterns.

        Args:
            outputs: List of dicts with keys: model_name, output, confidence, model_tier

        Returns:
            DissentReport with classification and recommendations
        """
        if len(outputs) < 2:
            report = DissentReport(
                dissent_type=DissentType.NONE,
                severity=DissentSeverity.NONE,
                agreement_score=1.0,
                disagreeing_models=(),
                agreeing_models=tuple(o["model_name"] for o in outputs),
                areas_of_disagreement=(),
                recommended_action="Insufficient models for dissent analysis",
            )
            self._history.append(report)
            return report

        # Compute pairwise similarity
        similarities = self._compute_pairwise_similarity(outputs)
        agreement = sum(similarities) / len(similarities) if similarities else 1.0

        # Classify dissent
        dissent_type = self._classify_dissent(outputs, similarities, agreement)
        severity = self._assess_severity(dissent_type, agreement, outputs)
        areas = self._identify_disagreement_areas(outputs, similarities)

        # Determine disagreeing/agreeing models
        disagreeing, agreeing = self._partition_models(outputs, similarities)

        # Build recommendation
        action, needs_human, needs_escalation, needs_more = self._recommend_action(
            dissent_type, severity, agreement, len(outputs)
        )

        report = DissentReport(
            dissent_type=dissent_type,
            severity=severity,
            agreement_score=agreement,
            disagreeing_models=tuple(disagreeing),
            agreeing_models=tuple(agreeing),
            areas_of_disagreement=tuple(areas),
            recommended_action=action,
            needs_human_review=needs_human,
            needs_escalation=needs_escalation,
            needs_more_models=needs_more,
        )
        self._history.append(report)
        return report

    def detect_from_verdicts(self, verdicts: list[Any]) -> DissentReport:
        """Convenience method accepting ModelVerdict objects."""
        outputs = [
            {
                "model_name": v.model_name,
                "output": v.output,
                "confidence": v.confidence,
                "model_tier": v.model_tier,
            }
            for v in verdicts
        ]
        return self.detect(outputs)

    def get_history(self) -> list[DissentReport]:
        """Return the history of dissent analyses."""
        return list(self._history)

    def get_dissent_rate(self) -> float:
        """Return the fraction of analyses that found significant dissent."""
        if not self._history:
            return 0.0
        significant = sum(
            1 for r in self._history
            if r.severity in (DissentSeverity.HIGH, DissentSeverity.CRITICAL)
        )
        return significant / len(self._history)

    def clear(self) -> None:
        """Clear dissent analysis history."""
        self._history.clear()

    # ── Private ────────────────────────────────────────────────────

    def _compute_pairwise_similarity(
        self, outputs: list[dict[str, Any]]
    ) -> list[float]:
        """Compute pairwise text similarity between all outputs."""
        similarities: list[float] = []
        for i in range(len(outputs)):
            for j in range(i + 1, len(outputs)):
                sim = self._text_similarity(
                    outputs[i].get("output", ""),
                    outputs[j].get("output", ""),
                )
                similarities.append(sim)
        return similarities

    @staticmethod
    def _text_similarity(text_a: str, text_b: str) -> float:
        """Compute a simple token-overlap similarity between two texts."""
        if not text_a and not text_b:
            return 1.0
        if not text_a or not text_b:
            return 0.0

        tokens_a = set(text_a.lower().split())
        tokens_b = set(text_b.lower().split())

        if not tokens_a or not tokens_b:
            return 0.0

        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        return len(intersection) / len(union)

    def _classify_dissent(
        self,
        outputs: list[dict[str, Any]],
        similarities: list[float],
        agreement: float,
    ) -> DissentType:
        """Classify the type of dissent based on similarity patterns."""
        if agreement >= 0.9:
            # Check for confidence gaps
            confidences = [o.get("confidence", 0.0) for o in outputs]
            conf_range = max(confidences) - min(confidences)
            if conf_range > 0.3:
                return DissentType.CONFIDENCE_GAP
            return DissentType.NONE

        if agreement >= 0.7:
            return DissentType.STYLISTIC

        if agreement >= self.structural_dissent_threshold:
            return DissentType.STRUCTURAL

        if agreement >= self.factual_dissent_threshold:
            return DissentType.FACTUAL

        return DissentType.COMPLETE

    def _assess_severity(
        self,
        dissent_type: DissentType,
        agreement: float,
        outputs: list[dict[str, Any]],
    ) -> DissentSeverity:
        """Assess the severity of the dissent."""
        if dissent_type == DissentType.NONE:
            return DissentSeverity.NONE
        if dissent_type == DissentType.CONFIDENCE_GAP:
            return DissentSeverity.LOW
        if dissent_type == DissentType.STYLISTIC:
            return DissentSeverity.LOW
        if dissent_type == DissentType.STRUCTURAL:
            return DissentSeverity.MEDIUM

        # For FACTUAL or COMPLETE, check if safety-relevant
        combined = " ".join(o.get("output", "") for o in outputs).lower()
        safety_keywords = {"security", "auth", "password", "secret", "token",
                          "encrypt", "vulnerability", "exploit", "injection"}
        if any(kw in combined for kw in safety_keywords):
            return DissentSeverity.CRITICAL

        if agreement < self.critical_dissent_threshold:
            return DissentSeverity.CRITICAL

        return DissentSeverity.HIGH

    def _identify_disagreement_areas(
        self,
        outputs: list[dict[str, Any]],
        similarities: list[float],
    ) -> list[str]:
        """Identify specific areas where models disagree."""
        areas: list[str] = []
        min_sim = min(similarities) if similarities else 1.0

        if min_sim < 0.3:
            areas.append("fundamentally different answers produced")

        # Check output length variance as a proxy for detail level
        lengths = [len(o.get("output", "")) for o in outputs]
        if lengths and max(lengths) > 0:
            length_variance = (max(lengths) - min(lengths)) / max(lengths)
            if length_variance > 0.5:
                areas.append("significant variance in response detail/depth")

        # Check for conflicting code patterns
        outputs_text = [o.get("output", "") for o in outputs]
        if any("import " in t for t in outputs_text) and any(
            "import " not in t for t in outputs_text
        ):
            areas.append("code vs non-code response format disagreement")

        return areas

    def _partition_models(
        self,
        outputs: list[dict[str, Any]],
        similarities: list[float],
    ) -> tuple[list[str], list[str]]:
        """Partition models into disagreeing and agreeing groups."""
        disagreeing: list[str] = []
        agreeing: list[str] = []

        avg_sim = sum(similarities) / len(similarities) if similarities else 1.0

        if avg_sim >= 0.7:
            # Most models agree — all are agreeing
            agreeing = [o["model_name"] for o in outputs]
        else:
            # Find the largest cluster
            model_names = [o["model_name"] for o in outputs]
            for i, name in enumerate(model_names):
                # Check if this model agrees with the majority
                sims_for_model = []
                for j in range(len(similarities)):
                    idx = 0
                    for a in range(len(outputs)):
                        for b in range(a + 1, len(outputs)):
                            if (a == i or b == i) and (a != b):
                                sims_for_model.append(similarities[idx])
                            if a < b:
                                idx += 1
                            if a == b:
                                continue

                # Simplified: if a model has low agreement with others
                own_sims = []
                for j, other in enumerate(outputs):
                    if j != i:
                        own_sims.append(
                            self._text_similarity(
                                outputs[i]["output"], other["output"]
                            )
                        )
                avg_own = sum(own_sims) / len(own_sims) if own_sims else 1.0
                if avg_own < 0.5:
                    disagreeing.append(name)
                else:
                    agreeing.append(name)

        return disagreeing, agreeing

    def _recommend_action(
        self,
        dissent_type: DissentType,
        severity: DissentSeverity,
        agreement: float,
        model_count: int,
    ) -> tuple[str, bool, bool, bool]:
        """Recommend action based on dissent analysis."""
        needs_human = False
        needs_escalation = False
        needs_more = False

        if severity == DissentSeverity.NONE:
            action = "Proceed with consensus result"
        elif severity == DissentSeverity.LOW:
            action = "Accept majority result with note about stylistic variance"
        elif severity == DissentSeverity.MEDIUM:
            action = "Present both approaches, let user choose or auto-select highest-confidence"
            if model_count < 3:
                needs_more = True
                action += "; consider adding a tie-breaker model"
        elif severity == DissentSeverity.HIGH:
            action = "Escalate: run additional models and flag for review"
            needs_escalation = True
            needs_more = True
        else:  # CRITICAL
            action = "BLOCK: require human review before proceeding"
            needs_human = True
            needs_escalation = True
            needs_more = True

        return action, needs_human, needs_escalation, needs_more
