"""Competence Map — Context→Skill mapping with regression protection."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "CompetenceEntry",
    "RegressionDetector",
    "CompetenceMap",
]




@dataclass
class CompetenceEntry:
    context_signature: str
    skill_name: str
    success_rate: float
    total_attempts: int
    recent_attempts: int = 0
    last_used: float = 0.0


class RegressionDetector:
    """Detects catastrophic forgetting — when new learning degrades old performance."""

    def __init__(self, threshold: float = 0.1):
        self.threshold = threshold
        self.baselines: dict[str, float] = {}
        self.regressions: list[dict[str, Any]] = []

    def set_baseline(self, skill_name: str, success_rate: float) -> None:
        self.baselines[skill_name] = success_rate

    def check_regression(self, skill_name: str, current_rate: float) -> bool:
        baseline = self.baselines.get(skill_name)
        if baseline is None:
            return False
        drop = baseline - current_rate
        if drop > self.threshold:
            self.regressions.append({
                "skill": skill_name,
                "baseline": baseline,
                "current": current_rate,
                "drop": drop,
                "is_regression": True,
            })
            return True
        return False


class CompetenceMap:
    """Maintains which skills work in which contexts with regression protection."""

    def __init__(self):
        self.entries: list[CompetenceEntry] = []
        self.contexts: dict[str, int] = defaultdict(int)  # signature -> count
        self.regression_detector = RegressionDetector()

    def record_attempt(
        self, context_signature: str, skill_name: str, success: bool
    ) -> CompetenceEntry:
        existing = self._find_entry(context_signature, skill_name)
        if existing:
            existing.total_attempts += 1
            existing.recent_attempts += 1
            existing.success_rate = (
                (existing.success_rate * (existing.total_attempts - 1) + (1.0 if success else 0.0))
                / existing.total_attempts
            )
            existing.last_used = __import__("time").time()
            self.regression_detector.check_regression(skill_name, existing.success_rate)
            return existing
        else:
            entry = CompetenceEntry(
                context_signature=context_signature,
                skill_name=skill_name,
                success_rate=1.0 if success else 0.0,
                total_attempts=1,
                recent_attempts=1,
                last_used=__import__("time").time(),
            )
            self.entries.append(entry)
            self.contexts[context_signature] += 1
            return entry

    def _find_entry(self, context: str, skill: str) -> Optional[CompetenceEntry]:
        for e in self.entries:
            if e.context_signature == context and e.skill_name == skill:
                return e
        return None

    def best_skill_for_context(self, context_signature: str) -> Optional[str]:
        candidates = [
            e for e in self.entries
            if e.context_signature == context_signature and e.total_attempts >= 3
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda e: e.success_rate).skill_name

    def skills_for_context(self, context_signature: str) -> list[CompetenceEntry]:
        return sorted(
            [e for e in self.entries if e.context_signature == context_signature],
            key=lambda e: e.success_rate,
            reverse=True,
        )

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_entries": len(self.entries),
            "unique_contexts": len(self.contexts),
            "unique_skills": len(set(e.skill_name for e in self.entries)),
            "regression_events": len(self.regression_detector.regressions),
        }
