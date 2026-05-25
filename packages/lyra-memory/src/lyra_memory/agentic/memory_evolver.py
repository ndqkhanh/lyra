"""
Memory evolution — existing memories update when new, related information arrives.

When a new note is close to existing memories, the agent can update those
memories (content, keywords, tags) rather than just linking. This prevents
accumulation of stale/contradictory information.

Source: A-Mem (FiM0M8gcct), ICLR 2026 MemAgent Workshop.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EvolutionResult:
    """Result of attempting to evolve an existing memory."""

    note_id: str
    was_updated: bool
    new_content: str | None = None
    new_keywords: list[str] | None = None
    new_tags: list[str] | None = None
    reason: str = ""


class LLMClient(Protocol):
    """Protocol for LLM interaction."""

    async def complete(self, prompt: str) -> str: ...


@dataclass
class MemoryEvolver:
    """Evolves existing memories when new information arrives.

    When a new note is semantically close to existing notes, the evolver
    checks whether the new information changes, refines, or contradicts
    the existing memory. If so, it produces an updated version.
    """

    llm: LLMClient
    similarity_threshold: float = 0.7
    max_evolutions_per_write: int = 5

    async def evolve(
        self, new_content: str, nearby_notes: list[dict],
    ) -> list[EvolutionResult]:
        """Check and evolve existing notes based on new information.

        Args:
            new_content: The newly stored content
            nearby_notes: Existing notes that are semantically close

        Returns:
            List of EvolutionResults for notes that should be updated
        """
        results = []
        for note in nearby_notes[: self.max_evolutions_per_write]:
            result = await self._try_evolve_one(new_content, note)
            if result.was_updated:
                results.append(result)
        return results

    async def _try_evolve_one(
        self, new_content: str, existing_note: dict
    ) -> EvolutionResult:
        """Attempt to evolve a single existing note."""
        prompt = f"""Evaluate whether new information should update an existing memory note.

EXISTING MEMORY:
  content: {existing_note.get('content', '')[:500]}
  keywords: {existing_note.get('keywords', [])}
  tags: {existing_note.get('tags', [])}

NEW INFORMATION:
  {new_content[:500]}

Does the new information:
- CHANGE a fact in the existing memory? (correction)
- ADD significant detail the existing memory is missing? (refinement)
- CONTRADICT the existing memory? (the existing is now wrong)
- SUPERSEDE the existing memory entirely? (the new is a better version)

If the new info is redundant or irrelevant, respond with NO_UPDATE.

Respond with JSON:
{{
    "should_update": true/false,
    "reason": "brief explanation",
    "new_content": "updated full content (if should_update)",
    "new_keywords": ["updated", "keywords"],
    "new_tags": ["updated", "tags"]
}}"""

        response = await self.llm.complete(prompt)
        try:
            data = json.loads(self._extract_json(response))
        except (json.JSONDecodeError, KeyError):
            return EvolutionResult(
                note_id=existing_note.get("id", ""),
                was_updated=False,
                reason="failed to parse LLM response",
            )

        if not data.get("should_update", False):
            return EvolutionResult(
                note_id=existing_note.get("id", ""),
                was_updated=False,
                reason=data.get("reason", "no update needed"),
            )

        return EvolutionResult(
            note_id=existing_note.get("id", ""),
            was_updated=True,
            new_content=data.get("new_content"),
            new_keywords=data.get("new_keywords"),
            new_tags=data.get("new_tags"),
            reason=data.get("reason", ""),
        )

    @staticmethod
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
