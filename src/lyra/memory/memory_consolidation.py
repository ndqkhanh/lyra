"""
Memory Consolidation - Move memories from short-term to long-term.
"""

import time
from dataclasses import dataclass
from enum import Enum

from lyra.memory.long_term_memory import LongTermMemory
from lyra.memory.memory_store import Memory, MemoryType
from lyra.memory.short_term_memory import ConversationTurn, ShortTermMemory


class ConsolidationPolicy(Enum):
    """When to trigger consolidation."""
    IMMEDIATE = "immediate"        # After every turn
    THRESHOLD = "threshold"        # When buffer reaches threshold
    PERIODIC = "periodic"          # At regular intervals
    MANUAL = "manual"              # Only when explicitly called


@dataclass
class ConsolidationResult:
    """
    Result of a consolidation operation.

    Attributes:
        memories_created: Number of new long-term memories
        memories_merged: Number of memories merged
        patterns_extracted: Number of patterns found
        duration: Time taken (seconds)
    """
    memories_created: int
    memories_merged: int
    patterns_extracted: int
    duration: float


class MemoryConsolidator:
    """
    Consolidate memories from short-term to long-term.

    Responsibilities:
    - Move important short-term memories to long-term
    - Merge similar memories
    - Extract patterns and knowledge
    - Apply consolidation policies
    """

    def __init__(
        self,
        short_term: ShortTermMemory,
        long_term: LongTermMemory,
        policy: ConsolidationPolicy = ConsolidationPolicy.THRESHOLD,
        importance_threshold: float = 0.5,
    ):
        """
        Initialize memory consolidator.

        Args:
            short_term: Short-term memory
            long_term: Long-term memory
            policy: Consolidation policy
            importance_threshold: Minimum importance to consolidate
        """
        self.short_term = short_term
        self.long_term = long_term
        self.policy = policy
        self.importance_threshold = importance_threshold
        self.last_consolidation = time.time()

    def should_consolidate(self) -> bool:
        """
        Check if consolidation should occur.

        Returns:
            True if should consolidate
        """
        if self.policy == ConsolidationPolicy.IMMEDIATE:
            return True

        elif self.policy == ConsolidationPolicy.THRESHOLD:
            return self.short_term.should_consolidate()

        elif self.policy == ConsolidationPolicy.PERIODIC:
            # Consolidate every 5 minutes
            time_since_last = time.time() - self.last_consolidation
            return time_since_last >= 300

        elif self.policy == ConsolidationPolicy.MANUAL:
            return False

        return False

    def consolidate(self) -> ConsolidationResult:
        """
        Perform memory consolidation.

        Returns:
            Consolidation result
        """
        start_time = time.time()

        # Consolidate conversation turns
        memories_created = self.short_term.consolidate_to_long_term(
            self.long_term.store,
            self.importance_threshold,
        )

        # Extract patterns
        patterns_extracted = self._extract_patterns()

        # Merge similar memories
        memories_merged = self.long_term.merge_similar()

        # Update last consolidation time
        self.last_consolidation = time.time()

        duration = time.time() - start_time

        return ConsolidationResult(
            memories_created=memories_created,
            memories_merged=memories_merged,
            patterns_extracted=patterns_extracted,
            duration=duration,
        )

    def _extract_patterns(self) -> int:
        """
        Extract patterns from recent memories.

        Returns:
            Number of patterns extracted
        """
        # Get recent episodic memories
        recent = self.long_term.get_recent(limit=20)
        episodic = [m for m in recent if m.memory_type == MemoryType.EPISODIC]

        if len(episodic) < 3:
            return 0

        # Look for repeated patterns
        patterns = self._find_repeated_patterns(episodic)

        # Create semantic memories from patterns
        patterns_created = 0
        for pattern in patterns:
            self.long_term.add(
                content=pattern["description"],
                memory_type=MemoryType.SEMANTIC,
                importance=pattern["importance"],
                tags=["pattern", "learned"],
                context={"occurrences": pattern["count"]},
            )
            patterns_created += 1

        return patterns_created

    def _find_repeated_patterns(self, memories: list[Memory]) -> list[dict]:
        """
        Find repeated patterns in memories.

        Args:
            memories: List of memories to analyze

        Returns:
            List of patterns found
        """
        patterns = []

        # Simple pattern detection: look for repeated keywords
        keyword_counts = {}

        for memory in memories:
            words = memory.content.lower().split()
            for word in words:
                if len(word) > 4:  # Only meaningful words
                    keyword_counts[word] = keyword_counts.get(word, 0) + 1

        # Find frequently occurring keywords
        for keyword, count in keyword_counts.items():
            if count >= 3:  # Appears at least 3 times
                patterns.append({
                    "description": f"Frequently discussed: {keyword}",
                    "importance": min(1.0, 0.5 + (count * 0.1)),
                    "count": count,
                })

        return patterns

    def consolidate_specific(
        self,
        turns: list[ConversationTurn],
        memory_type: MemoryType = MemoryType.EPISODIC,
    ) -> int:
        """
        Consolidate specific conversation turns.

        Args:
            turns: Turns to consolidate
            memory_type: Type of memory to create

        Returns:
            Number of memories created
        """
        created = 0

        for turn in turns:
            # Calculate importance
            importance = self._calculate_turn_importance(turn)

            if importance >= self.importance_threshold:
                self.long_term.add(
                    content=f"{turn.role}: {turn.content}",
                    memory_type=memory_type,
                    importance=importance,
                    tags=[turn.role, "conversation"],
                    context={
                        "timestamp": turn.timestamp,
                        "metadata": turn.metadata,
                    },
                )
                created += 1

        return created

    def _calculate_turn_importance(self, turn: ConversationTurn) -> float:
        """
        Calculate importance of a conversation turn.

        Args:
            turn: Conversation turn

        Returns:
            Importance score (0.0 - 1.0)
        """
        importance = 0.5

        # User turns are more important
        if turn.role == "user":
            importance += 0.2

        # Longer content is more important
        content_length = len(turn.content)
        if content_length > 100:
            importance += 0.1
        if content_length > 500:
            importance += 0.1

        # Metadata can indicate importance
        if turn.metadata.get("important"):
            importance += 0.2

        return min(1.0, importance)

    def extract_knowledge(self, topic: str) -> Memory | None:
        """
        Extract knowledge about a topic from recent memories.

        Args:
            topic: Topic to extract knowledge about

        Returns:
            Semantic memory with extracted knowledge
        """
        # Search for relevant memories
        relevant = self.long_term.search_by_content(topic, limit=10)

        if not relevant:
            return None

        # Combine information
        knowledge_points = []
        for memory in relevant:
            if topic.lower() in memory.content.lower():
                knowledge_points.append(memory.content)

        if not knowledge_points:
            return None

        # Create semantic memory
        knowledge = self.long_term.add(
            content=f"Knowledge about {topic}: " + "; ".join(knowledge_points[:3]),
            memory_type=MemoryType.SEMANTIC,
            importance=0.7,
            tags=[topic, "knowledge", "extracted"],
            context={"source_count": len(knowledge_points)},
        )

        return knowledge

    def create_procedure(
        self,
        name: str,
        steps: list[str],
        importance: float = 0.6,
    ) -> Memory:
        """
        Create a procedural memory.

        Args:
            name: Procedure name
            steps: List of steps
            importance: Importance score

        Returns:
            Created procedural memory
        """
        content = f"Procedure: {name}\n"
        for i, step in enumerate(steps, 1):
            content += f"{i}. {step}\n"

        return self.long_term.add(
            content=content,
            memory_type=MemoryType.PROCEDURAL,
            importance=importance,
            tags=[name, "procedure"],
            context={"step_count": len(steps)},
        )

    def auto_consolidate(self) -> ConsolidationResult | None:
        """
        Automatically consolidate if policy allows.

        Returns:
            Consolidation result if consolidation occurred
        """
        if self.should_consolidate():
            return self.consolidate()
        return None

    def get_statistics(self) -> dict:
        """
        Get consolidation statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "policy": self.policy.value,
            "importance_threshold": self.importance_threshold,
            "last_consolidation": self.last_consolidation,
            "time_since_last": time.time() - self.last_consolidation,
            "should_consolidate": self.should_consolidate(),
        }
