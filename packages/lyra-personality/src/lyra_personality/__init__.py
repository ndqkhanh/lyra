"""Agent Personality — Big Five trait model for consistent behavioral traits.

Makes Lyra agents coherent characters, not just action generators.
An agent with high conscientiousness should be thorough everywhere,
not just when explicitly instructed.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "BigFiveTraits",
    "AgentPersonality",
]


@dataclass
class BigFiveTraits:
    openness: float = 0.5
    conscientiousness: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5
    neuroticism: float = 0.3


class AgentPersonality:
    """Big Five personality model with experience-driven adaptation."""

    def __init__(self, traits: Optional[BigFiveTraits] = None):
        self.traits = traits or BigFiveTraits()
        self._experience_log: list[dict[str, Any]] = []

    def express(self, context: dict[str, Any]) -> dict[str, float]:
        """Generate behavioral modifiers based on personality."""
        modifiers = {
            "thoroughness": 0.5 + self.traits.conscientiousness * 0.5,
            "creativity": 0.5 + self.traits.openness * 0.5,
            "social_engagement": 0.5 + self.traits.extraversion * 0.5,
            "cooperation": 0.5 + self.traits.agreeableness * 0.5,
            "sensitivity": self.traits.neuroticism,
            "risk_taking": 0.5 + self.traits.openness * 0.3 - self.traits.neuroticism * 0.2,
        }
        self._experience_log.append({"type": "express", "context": str(context)[:50]})
        return modifiers

    def learn_from_feedback(self, feedback: float, context: str) -> None:
        """Personality shifts gradually based on experience."""
        self._experience_log.append({"type": "feedback", "value": feedback, "context": context[:50]})
        if feedback > 0.8:
            self.traits.conscientiousness = min(1.0, self.traits.conscientiousness + 0.02)
            self.traits.agreeableness = min(1.0, self.traits.agreeableness + 0.01)
        elif feedback < 0.3:
            self.traits.neuroticism = min(1.0, self.traits.neuroticism + 0.02)

    def describe(self) -> str:
        """Generate a natural language personality description."""
        desc = []
        if self.traits.openness > 0.7:
            desc.append("curious and imaginative")
        elif self.traits.openness < 0.3:
            desc.append("conventional and practical")
        if self.traits.conscientiousness > 0.7:
            desc.append("organized and diligent")
        elif self.traits.conscientiousness < 0.3:
            desc.append("flexible and spontaneous")
        if self.traits.extraversion > 0.7:
            desc.append("social and energetic")
        elif self.traits.extraversion < 0.3:
            desc.append("reserved and independent")
        if self.traits.agreeableness > 0.7:
            desc.append("cooperative and compassionate")
        elif self.traits.agreeableness < 0.3:
            desc.append("analytical and direct")
        return f"An agent who is {' and '.join(desc) if desc else 'balanced'}."

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "openness": self.traits.openness,
            "conscientiousness": self.traits.conscientiousness,
            "extraversion": self.traits.extraversion,
            "agreeableness": self.traits.agreeableness,
            "neuroticism": self.traits.neuroticism,
            "experiences": len(self._experience_log),
        }
