"""
Active context compression for efficient context management.

Implements Focus-style compression:
1. Identify focus regions (important parts)
2. Extract persistent knowledge
3. Prune transient observations
4. Keep knowledge + compressed history
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ContextSegment:
    """A segment of conversation context."""
    turn_number: int
    user_input: str
    assistant_response: str
    tool_results: Optional[List[Dict[str, Any]]] = None
    importance: float = 0.5  # 0.0-1.0


@dataclass
class KnowledgeBlock:
    """Extracted persistent knowledge."""
    content: str
    source_turns: List[int]
    confidence: float


class ContextCompressor:
    """
    Compress conversation context while preserving important information.

    Uses Focus-style compression to keep context under budget.
    """

    def __init__(self, max_tokens: int = 100000):
        """
        Initialize compressor.

        Args:
            max_tokens: Maximum context tokens
        """
        self.max_tokens = max_tokens
        self.knowledge_blocks: List[KnowledgeBlock] = []

    def compress(
        self,
        history: List[ContextSegment],
        current_task: str,
    ) -> tuple[List[KnowledgeBlock], List[ContextSegment]]:
        """
        Compress context history.

        Args:
            history: Full conversation history
            current_task: Current task description

        Returns:
            Tuple of (knowledge_blocks, compressed_history)
        """
        # 1. Identify focus regions
        focus_regions = self._identify_focus_regions(history, current_task)

        # 2. Extract knowledge from focus regions
        new_knowledge = self._extract_knowledge(focus_regions)
        self.knowledge_blocks.extend(new_knowledge)

        # 3. Prune transient observations
        compressed = self._prune_transient(history, focus_regions)

        # 4. Deduplicate knowledge
        self.knowledge_blocks = self._deduplicate_knowledge(self.knowledge_blocks)

        return self.knowledge_blocks, compressed

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        return int(len(text.split()) * 1.3)  # ~1.3 tokens per word

    def _identify_focus_regions(
        self,
        history: List[ContextSegment],
        current_task: str,
    ) -> List[ContextSegment]:
        """
        Identify important regions in history.

        Focus regions are:
        - Recent turns (last 10)
        - Turns with errors
        - Turns with high importance
        - Turns related to current task
        """
        focus = []
        task_keywords = set(current_task.lower().split())

        for segment in history:
            # Always keep recent turns
            if segment.turn_number >= len(history) - 10:
                segment.importance = 1.0
                focus.append(segment)
                continue

            # Keep turns with errors
            if segment.tool_results:
                has_error = any(not r.get("success", True) for r in segment.tool_results)
                if has_error:
                    segment.importance = 0.9
                    focus.append(segment)
                    continue

            # Keep turns related to current task
            segment_text = (segment.user_input + " " + segment.assistant_response).lower()
            overlap = len(task_keywords & set(segment_text.split()))
            if overlap >= 2:
                segment.importance = 0.7
                focus.append(segment)

        return focus

    def _extract_knowledge(self, focus_regions: List[ContextSegment]) -> List[KnowledgeBlock]:
        """Extract persistent knowledge from focus regions."""
        knowledge = []

        for segment in focus_regions:
            # Extract facts from user input
            if any(phrase in segment.user_input.lower() for phrase in ["uses", "is", "has"]):
                knowledge.append(
                    KnowledgeBlock(
                        content=segment.user_input,
                        source_turns=[segment.turn_number],
                        confidence=0.8,
                    )
                )

            # Extract error patterns
            if segment.tool_results:
                for result in segment.tool_results:
                    if not result.get("success", True):
                        error = result.get("error", "Unknown error")
                        knowledge.append(
                            KnowledgeBlock(
                                content=f"Error pattern: {error}",
                                source_turns=[segment.turn_number],
                                confidence=0.9,
                            )
                        )

        return knowledge

    def _prune_transient(
        self,
        history: List[ContextSegment],
        focus_regions: List[ContextSegment],
    ) -> List[ContextSegment]:
        """Prune transient observations, keep only focus regions."""
        focus_turn_numbers = {seg.turn_number for seg in focus_regions}

        # Keep focus regions + recent turns
        compressed = [
            seg for seg in history
            if seg.turn_number in focus_turn_numbers or seg.turn_number >= len(history) - 5
        ]

        return compressed

    def _deduplicate_knowledge(
        self,
        knowledge_blocks: List[KnowledgeBlock],
    ) -> List[KnowledgeBlock]:
        """Remove duplicate knowledge blocks."""
        seen = set()
        unique = []

        for block in knowledge_blocks:
            # Normalize content
            normalized = " ".join(block.content.lower().split())

            if normalized not in seen:
                seen.add(normalized)
                unique.append(block)

        return unique

    def format_compressed_context(
        self,
        knowledge_blocks: List[KnowledgeBlock],
        compressed_history: List[ContextSegment],
    ) -> str:
        """Format compressed context for LLM."""
        lines = []

        # Knowledge section
        if knowledge_blocks:
            lines.append("# Persistent Knowledge\n")
            for block in knowledge_blocks:
                lines.append(f"- {block.content}")
            lines.append("")

        # Compressed history
        lines.append("# Recent Context\n")
        for segment in compressed_history[-10:]:  # Last 10 turns
            lines.append(f"Turn {segment.turn_number}:")
            lines.append(f"User: {segment.user_input}")
            lines.append(f"Assistant: {segment.assistant_response[:200]}...")
            lines.append("")

        return "\n".join(lines)


def checkpoint_and_purge(
    history: List[ContextSegment],
    checkpoint_path: str,
) -> List[ContextSegment]:
    """
    Checkpoint history and purge old turns.

    Args:
        history: Full history
        checkpoint_path: Path to save checkpoint

        Returns:
        Recent history (last 20 turns)
    """
    import json
    from pathlib import Path

    # Save full history
    checkpoint_data = [
        {
            "turn_number": seg.turn_number,
            "user_input": seg.user_input,
            "assistant_response": seg.assistant_response,
            "tool_results": seg.tool_results,
        }
        for seg in history
    ]

    Path(checkpoint_path).parent.mkdir(parents=True, exist_ok=True)
    with open(checkpoint_path, "w") as f:
        json.dump(checkpoint_data, f, indent=2)

    # Keep only recent turns
    return history[-20:]
