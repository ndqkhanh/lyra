"""
Valence Vectors — every memory carries a 5-component emotional/cognitive weight
that determines prioritization, retrieval, and consolidation.

Source: Human-Like Lifelong Memory (QufkvHbQs7), ICLR 2026 MemAgent Workshop.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ValenceVector:
    """5-component cognitive weight vector for a memory.

    Components:
        emotional_valence: -1.0 (negative) to +1.0 (positive)
        associative_strength: 0.0 to 1.0 — connectedness to other memories
        contextual_richness: 0.0 to 1.0 — sensory/situational detail level
        density: 0.0 to 1.0 — information per token ratio
        precision: 0.0 to 1.0 — estimated accuracy confidence
    """

    emotional_valence: float = 0.0
    associative_strength: float = 0.5
    contextual_richness: float = 0.5
    density: float = 0.5
    precision: float = 0.5

    def __post_init__(self) -> None:
        for name in ("emotional_valence",):
            val = getattr(self, name)
            if val < -1.0 or val > 1.0:
                object.__setattr__(self, name, max(-1.0, min(1.0, val)))
        for name in ("associative_strength", "contextual_richness", "density", "precision"):
            val = getattr(self, name)
            if val < 0.0 or val > 1.0:
                object.__setattr__(self, name, max(0.0, min(1.0, val)))

    @property
    def salience(self) -> float:
        """Composite salience score for retrieval priority.

        Weighted combination with empirically calibrated weights:
        emotional impact (30%), connectedness (20%), detail richness (15%),
        info density (15%), confidence (20%).
        """
        return (
            0.30 * abs(self.emotional_valence)
            + 0.20 * self.associative_strength
            + 0.15 * self.contextual_richness
            + 0.15 * self.density
            + 0.20 * self.precision
        )

    @property
    def is_significant(self) -> bool:
        """Memories with salience >= 0.6 are prioritized for consolidation."""
        return self.salience >= 0.6

    def to_dict(self) -> dict:
        return {
            "emotional_valence": self.emotional_valence,
            "associative_strength": self.associative_strength,
            "contextual_richness": self.contextual_richness,
            "density": self.density,
            "precision": self.precision,
            "salience": round(self.salience, 4),
        }


class LLMClient(Protocol):
    """Protocol for LLM interaction."""

    async def complete(self, prompt: str) -> str: ...


@dataclass
class ValenceEstimator:
    """Estimates valence vector for new memories using the LLM.

    The LLM analyzes content and context to estimate the 5 cognitive dimensions.
    """

    llm: LLMClient

    async def estimate(self, content: str, context: dict | None = None) -> ValenceVector:
        """Estimate the 5-component valence vector for memory content.

        Args:
            content: The memory content to analyze
            context: Optional dict with keys like 'source', 'goals', 'urgency'

        Returns:
            ValenceVector with estimated cognitive dimensions
        """
        ctx_str = json.dumps(context) if context else "no additional context"
        prompt = f"""Analyze this memory content and estimate its cognitive dimensions:

Content: {content[:2000]}
Context: {ctx_str}

Output JSON only:
{{
    "emotional_valence": <float -1.0 to 1.0>,
    "associative_strength": <float 0.0 to 1.0, how connected to other knowledge>,
    "contextual_richness": <float 0.0 to 1.0, level of sensory/situational detail>,
    "density": <float 0.0 to 1.0, information per token>,
    "precision": <float 0.0 to 1.0, confidence in accuracy>
}}"""

        response = await self.llm.complete(prompt)
        return self._parse_valence(response)

    @staticmethod
    def _parse_valence(response: str) -> ValenceVector:
        try:
            data = json.loads(_extract_json(response))
            return ValenceVector(
                emotional_valence=float(data.get("emotional_valence", 0.0)),
                associative_strength=float(data.get("associative_strength", 0.5)),
                contextual_richness=float(data.get("contextual_richness", 0.5)),
                density=float(data.get("density", 0.5)),
                precision=float(data.get("precision", 0.5)),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return ValenceVector()


def _extract_json(text: str) -> str:
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return text[start:end].strip()
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return text[start:end].strip()
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start >= 0 and brace_end > brace_start:
        return text[brace_start : brace_end + 1]
    return text.strip()
