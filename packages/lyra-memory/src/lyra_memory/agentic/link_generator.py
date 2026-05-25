"""
Autonomous link generation between memory notes.

After storing a new note, the LLM analyzes its relationship to existing notes
and creates bidirectional typed links — forming an emergent associative graph.

Source: A-Mem (FiM0M8gcct), ICLR 2026 MemAgent Workshop.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class LinkType(str, Enum):
    """Semantic relationship types between memory notes."""

    CAUSES = "causes"           # new note explains why another happened
    CONTRADICTS = "contradicts" # new note conflicts with another
    EXTENDS = "extends"         # new note adds detail to another
    SUMMARIZES = "summarizes"   # new note abstracts over another
    RELATES = "relates"         # general thematic connection
    PREREQUISITE = "prerequisite"  # new note depends on another


@dataclass(frozen=True)
class Link:
    """A typed, directional link between two memory notes."""

    source_id: str
    target_id: str
    link_type: LinkType
    confidence: float = 1.0
    rationale: str = ""


class LLMClient(Protocol):
    """Protocol for LLM interaction."""

    async def complete(self, prompt: str) -> str: ...


@dataclass
class LinkGenerator:
    """Autonomous link generation — LLM discovers relationships between notes.

    After a new note is stored, the generator finds semantically nearby notes
    and asks the LLM to determine meaningful typed connections.
    """

    llm: LLMClient
    max_candidates: int = 20
    min_confidence: float = 0.6

    async def generate_links(
        self, new_note_id: str, new_note_content: str,
        new_note_keywords: list[str], candidates: list[dict],
    ) -> list[Link]:
        """Generate typed links between a new note and existing candidates.

        Args:
            new_note_id: ID of the newly created note
            new_note_content: Content of the new note
            new_note_keywords: Extracted keywords of the new note
            candidates: Top-k similar existing notes (with id, content, keywords)

        Returns:
            List of directional Links from new_note to relevant candidates
        """
        if not candidates:
            return []

        limited = candidates[: self.max_candidates]
        prompt = self._build_link_prompt(
            new_note_content, new_note_keywords, limited
        )
        response = await self.llm.complete(prompt)
        return self._parse_links(response, new_note_id, limited)

    def _build_link_prompt(
        self, content: str, keywords: list[str], candidates: list[dict]
    ) -> str:
        candidate_fmt = []
        for c in candidates:
            candidate_fmt.append(
                f"  [{c['id']}] keywords={c.get('keywords', [])}\n"
                f"      {c.get('content', '')[:200]}"
            )

        return f"""Analyze the relationship between a new memory note and existing notes.

NEW NOTE:
  keywords: {keywords}
  content: {content[:500]}

EXISTING NOTES:
{chr(10).join(candidate_fmt)}

For each existing note that has a meaningful connection, classify the relationship:
- CAUSES: the new note explains why the existing note's event happened
- CONTRADICTS: the new note conflicts with or corrects the existing note
- EXTENDS: the new note adds detail, examples, or nuance to the existing note
- SUMMARIZES: the new note abstracts or generalizes over the existing note
- RELATES: general thematic or topical connection
- PREREQUISITE: the new note depends on the existing note's knowledge

Only include connections with confidence >= {self.min_confidence}.

Respond with JSON array:
[
    {{
        "target_id": "id of existing note",
        "link_type": "one of: causes, contradicts, extends, summarizes, relates, prerequisite",
        "confidence": 0.0-1.0,
        "rationale": "one-line reason"
    }}
]

If no meaningful connections exist, return an empty array []."""

    def _parse_links(
        self, response: str, source_id: str, candidates: list[dict]
    ) -> list[Link]:
        try:
            data = json.loads(self._extract_json(response))
        except (json.JSONDecodeError, TypeError):
            return []

        valid_ids = {c["id"] for c in candidates}
        links = []
        for item in data:
            if not isinstance(item, dict):
                continue
            target = item.get("target_id", "")
            if target not in valid_ids:
                continue
            confidence = float(item.get("confidence", 0.5))
            if confidence < self.min_confidence:
                continue
            try:
                link_type = LinkType(item.get("link_type", "relates"))
            except ValueError:
                link_type = LinkType.RELATES

            links.append(Link(
                source_id=source_id,
                target_id=target,
                link_type=link_type,
                confidence=confidence,
                rationale=item.get("rationale", ""),
            ))
        return links

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
        bracket_start = text.find("[")
        bracket_end = text.rfind("]")
        if bracket_start >= 0 and bracket_end > bracket_start:
            return text[bracket_start : bracket_end + 1]
        return text.strip()
