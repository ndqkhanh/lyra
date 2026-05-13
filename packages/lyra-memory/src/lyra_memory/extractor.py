"""
Memory extraction from conversations.

Extracts memory candidates from observations, actions, and outcomes.
Implements deduplication, contradiction checking, and verification.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from lyra_memory.schema import MemoryRecord, MemoryScope, MemoryType, VerifierStatus
from lyra_memory.store import MemoryStore


class MemoryExtractor:
    """
    Extract memories from conversation turns.

    Implements the write path:
    1. Extract candidates from observation/action/outcome
    2. Deduplicate against existing memories
    3. Check for contradictions
    4. Verify before storing
    """

    def __init__(self, store: MemoryStore):
        """
        Initialize extractor.

        Args:
            store: Memory store to write to
        """
        self.store = store

    def extract_from_turn(
        self,
        user_input: str,
        assistant_response: str,
        tool_results: Optional[List[Dict[str, Any]]] = None,
        turn_number: Optional[int] = None,
    ) -> List[MemoryRecord]:
        """
        Extract memories from a conversation turn.

        Args:
            user_input: User's message
            assistant_response: Assistant's response
            tool_results: Tool execution results
            turn_number: Turn number for source tracking

        Returns:
            List of extracted and stored memories
        """
        candidates = []

        # Extract from user input
        candidates.extend(self._extract_from_user_input(user_input, turn_number))

        # Extract from assistant response
        candidates.extend(self._extract_from_response(assistant_response, turn_number))

        # Extract from tool results
        if tool_results:
            candidates.extend(self._extract_from_tools(tool_results, turn_number))

        # Deduplicate
        candidates = self._deduplicate(candidates)

        # Check contradictions and store
        stored = []
        for candidate in candidates:
            # Check for contradictions
            contradictions = self._find_contradictions(candidate)

            if contradictions:
                # Supersede old memories
                for old_memory in contradictions:
                    self.store.supersede(old_memory.id, candidate)

            # Store the new memory
            memory = self.store.write(
                content=candidate.content,
                scope=candidate.scope,
                type=candidate.type,
                source_span=candidate.source_span,
                confidence=candidate.confidence,
                metadata=candidate.metadata,
                verify=True,
            )
            stored.append(memory)

        return stored

    def _extract_from_user_input(
        self,
        user_input: str,
        turn_number: Optional[int],
    ) -> List[MemoryRecord]:
        """Extract memories from user input."""
        candidates = []
        source = f"turn {turn_number}" if turn_number else "user input"

        # Pattern 1: Explicit preferences ("I prefer X", "I like Y")
        if any(phrase in user_input.lower() for phrase in ["i prefer", "i like", "i want"]):
            candidates.append(
                MemoryRecord(
                    content=user_input,
                    scope=MemoryScope.USER,
                    type=MemoryType.PREFERENCE,
                    source_span=source,
                    confidence=0.9,
                )
            )

        # Pattern 2: Project facts ("This project uses X", "We use Y")
        if any(phrase in user_input.lower() for phrase in ["project uses", "we use", "this uses"]):
            candidates.append(
                MemoryRecord(
                    content=user_input,
                    scope=MemoryScope.PROJECT,
                    type=MemoryType.SEMANTIC,
                    source_span=source,
                    confidence=0.8,
                )
            )

        # Pattern 3: Corrections ("Actually, X", "No, Y", "That's wrong")
        if any(phrase in user_input.lower() for phrase in ["actually", "no,", "that's wrong", "incorrect"]):
            candidates.append(
                MemoryRecord(
                    content=user_input,
                    scope=MemoryScope.SESSION,
                    type=MemoryType.SEMANTIC,
                    source_span=source,
                    confidence=0.95,  # High confidence for corrections
                    metadata={"is_correction": True},
                )
            )

        return candidates

    def _extract_from_response(
        self,
        response: str,
        turn_number: Optional[int],
    ) -> List[MemoryRecord]:
        """Extract memories from assistant response."""
        candidates = []
        source = f"turn {turn_number}" if turn_number else "assistant response"

        # Pattern 1: Discovered facts (lower confidence)
        # These are inferred, not explicitly stated by user
        if any(phrase in response.lower() for phrase in ["i found", "i discovered", "it appears"]):
            candidates.append(
                MemoryRecord(
                    content=response,
                    scope=MemoryScope.SESSION,
                    type=MemoryType.SEMANTIC,
                    source_span=source,
                    confidence=0.6,  # Lower confidence for inferred facts
                )
            )

        return candidates

    def _extract_from_tools(
        self,
        tool_results: List[Dict[str, Any]],
        turn_number: Optional[int],
    ) -> List[MemoryRecord]:
        """Extract memories from tool execution results."""
        candidates = []
        source = f"turn {turn_number}" if turn_number else "tool execution"

        for result in tool_results:
            tool_name = result.get("tool", "unknown")
            success = result.get("success", False)

            # Pattern 1: Failed tool executions (failure memory)
            if not success:
                error = result.get("error", "Unknown error")
                candidates.append(
                    MemoryRecord(
                        content=f"Tool {tool_name} failed: {error}",
                        scope=MemoryScope.SESSION,
                        type=MemoryType.FAILURE,
                        source_span=source,
                        confidence=1.0,
                        metadata={"tool": tool_name, "error": error},
                    )
                )

            # Pattern 2: File operations (episodic memory)
            if tool_name in ["read_file", "write_file", "edit_file"]:
                file_path = result.get("file_path", "unknown")
                candidates.append(
                    MemoryRecord(
                        content=f"Operated on file: {file_path}",
                        scope=MemoryScope.SESSION,
                        type=MemoryType.EPISODIC,
                        source_span=source,
                        confidence=1.0,
                        metadata={"tool": tool_name, "file": file_path},
                    )
                )

        return candidates

    def _deduplicate(self, candidates: List[MemoryRecord]) -> List[MemoryRecord]:
        """
        Remove duplicate candidates.

        Two memories are duplicates if they have:
        - Same content (case-insensitive, normalized whitespace)
        - Same type
        - Same scope
        """
        seen = set()
        unique = []

        for candidate in candidates:
            # Normalize content for comparison
            normalized = " ".join(candidate.content.lower().split())
            key = (normalized, candidate.type, candidate.scope)

            if key not in seen:
                seen.add(key)
                unique.append(candidate)

        return unique

    def _find_contradictions(self, candidate: MemoryRecord) -> List[MemoryRecord]:
        """
        Find existing memories that contradict the candidate.

        A contradiction occurs when:
        - Same scope and type
        - Content is semantically similar but factually different
        - Existing memory is not already superseded

        Returns:
            List of contradicting memories to supersede
        """
        # Search for similar memories
        similar = self.store.retrieve(
            query=candidate.content,
            scope=candidate.scope,
            type=candidate.type,
            limit=5,
        )

        contradictions = []

        for memory in similar:
            # Skip if already superseded
            if memory.is_superseded():
                continue

            # Check for contradiction patterns
            if self._is_contradiction(candidate.content, memory.content):
                contradictions.append(memory)

        return contradictions

    def _is_contradiction(self, new_content: str, old_content: str) -> bool:
        """
        Check if two statements contradict each other.

        Simple heuristic-based approach. Can be enhanced with:
        - NLI (Natural Language Inference) models
        - Semantic similarity + negation detection
        - Knowledge graph reasoning
        """
        new_lower = new_content.lower()
        old_lower = old_content.lower()

        # Pattern 1: Explicit negation
        negation_phrases = ["no,", "actually,", "incorrect", "wrong", "not"]
        if any(phrase in new_lower for phrase in negation_phrases):
            return True

        # Pattern 2: Version changes
        # "Python 3.9" vs "Python 3.10"
        if "python" in new_lower and "python" in old_lower:
            # Extract version numbers
            import re
            new_versions = re.findall(r'\d+\.\d+', new_lower)
            old_versions = re.findall(r'\d+\.\d+', old_lower)
            if new_versions and old_versions and new_versions != old_versions:
                return True

        # Pattern 3: Opposite preferences
        # "I prefer X" vs "I prefer Y"
        if "prefer" in new_lower and "prefer" in old_lower:
            # Simple check: different content after "prefer"
            new_after = new_lower.split("prefer", 1)[-1].strip()
            old_after = old_lower.split("prefer", 1)[-1].strip()
            if new_after != old_after:
                return True

        return False


def extract_memories_from_conversation(
    store: MemoryStore,
    conversation_history: List[Tuple[str, str]],
) -> List[MemoryRecord]:
    """
    Extract memories from a full conversation history.

    Args:
        store: Memory store
        conversation_history: List of (user_input, assistant_response) tuples

    Returns:
        List of all extracted memories
    """
    extractor = MemoryExtractor(store)
    all_memories = []

    for turn_number, (user_input, assistant_response) in enumerate(conversation_history, 1):
        memories = extractor.extract_from_turn(
            user_input=user_input,
            assistant_response=assistant_response,
            turn_number=turn_number,
        )
        all_memories.extend(memories)

    return all_memories
