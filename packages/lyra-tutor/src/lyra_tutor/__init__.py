"""Intelligent Tutoring Agent — adaptive learning, assessment, personalized education.

Adaptive learning companion that adjusts difficulty, style, and pace
based on learner performance and preferences.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = ["LearnerModel", "TutorAgent"]


@dataclass
class LearnerModel:
    knowledge_level: float = 0.5
    learning_speed: float = 0.5
    preferred_style: str = "visual"
    confidence: float = 0.5


class TutorAgent:
    def __init__(self):
        self.learners: dict[str, LearnerModel] = {}
        self._sessions = 0

    def register_learner(self, learner_id: str, style: str = "visual") -> LearnerModel:
        model = LearnerModel(preferred_style=style)
        self.learners[learner_id] = model
        return model

    def assess(self, learner_id: str, score: float) -> dict[str, Any]:
        model = self.learners.get(learner_id)
        if not model:
            return {"error": "Unknown learner"}
        model.knowledge_level = min(1.0, model.knowledge_level + score * 0.1)
        model.confidence = min(1.0, model.confidence + (score - 0.5) * 0.1)
        self._sessions += 1
        difficulty = "advanced" if model.knowledge_level > 0.7 else "intermediate" if model.knowledge_level > 0.4 else "beginner"
        return {"difficulty": difficulty, "knowledge_level": model.knowledge_level, "next_topic": f"Topic at {difficulty} level"}

    @property
    def stats(self) -> dict[str, Any]:
        return {"learners": len(self.learners), "sessions": self._sessions}
