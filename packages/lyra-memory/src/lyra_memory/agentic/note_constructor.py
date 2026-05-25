"""
Agentic note construction — LLM decides what to store, how to keyword/tag it,
and whether to merge with existing notes.

Source: A-Mem (FiM0M8gcct), ICLR 2026 MemAgent Workshop.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ConstructionDecision:
    """Result of the LLM's decision about storing new information."""

    should_store: bool
    keywords: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    contextual_description: str = ""
    merge_target_id: str | None = None
    merged_content: str | None = None
    reason: str = ""


class LLMClient(Protocol):
    """Protocol for LLM interaction — enables testing with stubs."""

    async def complete(self, prompt: str) -> str: ...


class EmbeddingModel(Protocol):
    """Protocol for embedding generation."""

    async def embed(self, text: str) -> list[float]: ...


@dataclass
class NoteConstructor:
    """Agent-driven note construction — the LLM decides what and how to store.

    When new content arrives, the constructor asks the LLM to decide:
    1. Is this worth storing? (non-trivial, non-duplicate)
    2. What keywords and tags best capture it?
    3. What contextual description helps future retrieval?
    4. Should it merge with or supersede an existing note?
    """

    llm: LLMClient
    embedder: EmbeddingModel
    min_content_length: int = 20
    max_keywords: int = 8
    max_tags: int = 5

    async def construct(
        self, content: str, nearby_notes: list[dict] | None = None
    ) -> ConstructionDecision:
        """Analyze content and decide how to store it.

        Args:
            content: The raw content to potentially store
            nearby_notes: Existing notes that are semantically similar (top-k)

        Returns:
            ConstructionDecision with the LLM's storage strategy
        """
        if not content or len(content.strip()) < self.min_content_length:
            return ConstructionDecision(should_store=False, reason="content too short")

        prompt = self._build_construction_prompt(content, nearby_notes or [])
        response = await self.llm.complete(prompt)
        return self._parse_decision(response)

    def _build_construction_prompt(
        self, content: str, nearby_notes: list[dict]
    ) -> str:
        nearby_fmt = ""
        if nearby_notes:
            entries = []
            for i, note in enumerate(nearby_notes[:5], 1):
                entries.append(
                    f"  [{i}] {note.get('content', '')[:200]}\n"
                    f"      keywords: {note.get('keywords', [])}\n"
                    f"      tags: {note.get('tags', [])}"
                )
            nearby_fmt = "\n".join(entries)

        return f"""Analyze this content and decide how to store it in a Zettelkasten memory.

Content to evaluate:
{content[:2000]}

Existing related notes:
{nearby_fmt if nearby_fmt else "(no related notes found)"}

Decide:
1. STORE: Is this non-trivial, non-duplicate information worth remembering? (true/false)
2. KEYWORDS: Extract up to {self.max_keywords} specific keywords for retrieval
3. TAGS: Assign up to {self.max_tags} semantic tags (e.g., "bug-fix", "architecture", "python", "api-design")
4. CONTEXT: Write a one-line contextual description for when/why this memory matters
5. MERGE: Should this merge into an existing note? If yes, provide the note index and merged content

Respond with JSON only:
{{
    "should_store": true/false,
    "keywords": ["kw1", "kw2", ...],
    "tags": ["tag1", ...],
    "contextual_description": "one-line context",
    "merge_target_index": null or note-index-number,
    "merged_content": null or "combined content",
    "reason": "brief explanation of decision"
}}"""

    def _parse_decision(self, response: str) -> ConstructionDecision:
        try:
            data = json.loads(self._extract_json(response))
        except (json.JSONDecodeError, KeyError):
            return ConstructionDecision(
                should_store=False, reason="failed to parse LLM response"
            )

        return ConstructionDecision(
            should_store=bool(data.get("should_store", False)),
            keywords=data.get("keywords", [])[: self.max_keywords],
            tags=data.get("tags", [])[: self.max_tags],
            contextual_description=data.get("contextual_description", ""),
            merge_target_id=(
                str(data["merge_target_index"])
                if data.get("merge_target_index") is not None
                else None
            ),
            merged_content=data.get("merged_content"),
            reason=data.get("reason", ""),
        )

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract JSON block from LLM response, handling markdown fences."""
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            return text[start:end].strip()
        if "```" in text:
            start = text.index("```") + 3
            end = text.index("```", start)
            return text[start:end].strip()
        # Try to find JSON object boundaries
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start >= 0 and brace_end > brace_start:
            return text[brace_start : brace_end + 1]
        return text.strip()
