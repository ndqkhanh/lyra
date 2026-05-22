"""Agent Wellbeing — cognitive load monitoring, burnout prevention, rest scheduling."""
from __future__ import annotations; import logging; from dataclasses import dataclass, field; from typing import Any
logger = logging.getLogger(__name__); __all__ = ["WellbeingReport", "WellbeingMonitor"]

@dataclass
class WellbeingReport: cognitive_load: float = 0.0; stress_level: float = 0.0; tasks_completed: int = 0; burnout_risk: float = 0.0

class WellbeingMonitor:
    def __init__(self): self._reports: list[WellbeingReport] = []; self._current = WellbeingReport()
    def record_task(self, duration_minutes: float, complexity: float = 0.5) -> None:
        self._current.tasks_completed += 1; self._current.cognitive_load = min(1.0, self._current.cognitive_load + complexity * 0.1)
        if self._current.cognitive_load > 0.8: self._current.stress_level = min(1.0, self._current.stress_level + 0.15)
        self._current.burnout_risk = self._current.cognitive_load * self._current.stress_level
    def recommend_rest(self) -> dict:
        if self._current.burnout_risk > 0.5: return {"rest_needed": True, "recommended_minutes": int(self._current.burnout_risk * 60), "reason": "High burnout risk detected"}
        return {"rest_needed": False, "recommended_minutes": 0}
    def reset(self) -> None: self._reports.append(self._current); self._current = WellbeingReport()
    @property
    def stats(self) -> dict: return {"current_load": self._current.cognitive_load, "burnout_risk": self._current.burnout_risk, "tasks_completed": self._current.tasks_completed, "resets": len(self._reports)}
