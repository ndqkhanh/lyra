"""Uncertainty Quantification — calibrated confidence estimates, probabilistic reasoning."""
from __future__ import annotations
import logging, math
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)
__all__ = ["ConfidenceEstimate", "UncertaintyEngine"]

@dataclass
class ConfidenceEstimate:
    value: float; uncertainty: float; calibration_score: float = 0.0

class UncertaintyEngine:
    def __init__(self):
        self.estimates: list[ConfidenceEstimate] = []
        self._history: list[tuple[float, bool]] = []

    def predict(self, value: float, evidence_count: int = 10) -> ConfidenceEstimate:
        uncertainty = 1.0 / math.sqrt(max(evidence_count, 1))
        est = ConfidenceEstimate(value=value, uncertainty=uncertainty)
        self.estimates.append(est)
        return est

    def update_calibration(self, predicted: float, actual: bool) -> None:
        self._history.append((predicted, actual))
        if len(self._history) >= 10:
            recent = self._history[-10:]
            accuracy = sum(1 for p, a in recent if (p > 0.5) == a) / len(recent)
            if self.estimates:
                self.estimates[-1].calibration_score = accuracy

    @property
    def stats(self) -> dict: return {"estimates": len(self.estimates), "calibration_samples": len(self._history)}
