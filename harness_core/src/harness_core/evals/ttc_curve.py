"""Test-time-compute curve: accuracy vs thinking-token budget.

SealQA (arXiv:2506.01062) and the broader test-time-compute line show that
under noisy retrieval, the accuracy-vs-budget curve can *plateau or decline*
past an inflection point. The TTC curve is the diagnostic that surfaces this:
plot accuracy at multiple budget points, find the inflection, set production
budget cap there.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(order=True)
class TTCPoint:
    """One (budget, accuracy) sample on the TTC curve."""

    budget_tokens: int
    accuracy: float
    label: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.accuracy <= 1.0:
            raise ValueError(f"accuracy must be in [0, 1], got {self.accuracy}")
        if self.budget_tokens < 0:
            raise ValueError(f"budget_tokens must be >= 0, got {self.budget_tokens}")


@dataclass
class TTCCurve:
    """Accumulate (budget, accuracy) points; compute inflection.

    The inflection heuristic: the smallest budget at which the accuracy gain
    over the next ``window`` points falls below ``epsilon``. That's the
    "no useful return on more compute" point.
    """

    points: list[TTCPoint] = field(default_factory=list)

    def add(self, *, budget_tokens: int, accuracy: float, label: str = "") -> TTCPoint:
        point = TTCPoint(budget_tokens=budget_tokens, accuracy=accuracy, label=label)
        self.points.append(point)
        self.points.sort()
        return point

    def sorted_points(self) -> list[TTCPoint]:
        return sorted(self.points)

    def find_inflection(self, *, epsilon: float = 0.01, window: int = 2) -> Optional[TTCPoint]:
        """First point where the next ``window`` points add < epsilon accuracy.

        Returns None if the curve is still rising at the last sample (no
        inflection observed in the data).
        """
        pts = self.sorted_points()
        if len(pts) < window + 1:
            return None
        for i, pt in enumerate(pts):
            future = pts[i + 1 : i + 1 + window]
            if len(future) < window:
                return None
            future_max = max(f.accuracy for f in future)
            if future_max - pt.accuracy < epsilon:
                return pt
        return None

    def find_decline(self) -> Optional[TTCPoint]:
        """First point where any subsequent sample has lower accuracy.

        SealQA-style "more compute makes it worse" detector.
        """
        pts = self.sorted_points()
        for i, pt in enumerate(pts):
            for f in pts[i + 1 :]:
                if f.accuracy < pt.accuracy:
                    return pt
        return None

    def to_csv(self) -> str:
        lines = ["budget_tokens,accuracy,label"]
        for p in self.sorted_points():
            lines.append(f"{p.budget_tokens},{p.accuracy:.6f},{p.label}")
        return "\n".join(lines)
