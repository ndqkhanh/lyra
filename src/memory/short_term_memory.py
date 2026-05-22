"""
Short-Term Memory - Recent conversation context.
"""

import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from collections import deque

from src.memory.memory_store import Memory, MemoryType, MemoryStore


@dataclass
class ConversationTurn:
    """
    A single conversation turn.
    
    Attributes:
        role: Speaker role (user, agent, system)
        content: Turn content
        timestamp: When turn occurred
        metadata: Additional metadata
    """
    role: str
    content: str
    timestamp: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ShortTermMemory:
    """
    Short-term memory for recent context.
    
    Responsibilities:
    - Store recent conversation turns
    - Maintain fixed-size buffer
    - Provide quick access to recent context
    - Consolidate to long-term memory
    """

    def __init__(
        self,
        capacity: int = 10,
        consolidation_threshold: int = 5,
    ):
        """
        Initialize short-term memory.
        
        Args:
            capacity: Maximum number of turns to keep
            consolidation_threshold: When to trigger consolidation
        """
        self.capacity = capacity
        self.consolidation_threshold = consolidation_threshold
        self.turns: deque = deque(maxlen=capacity)
        self.working_memory: Dict[str, Any] = {}

    def add_turn(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationTurn:
        """
        Add a conversation turn.
        
        Args:
            role: Speaker role
            content: Turn content
            metadata: Additional metadata
            
        Returns:
            Created turn
        """
        turn = ConversationTurn(
            role=role,
            content=content,
            timestamp=time.time(),
            metadata=metadata or {},
        )
        
        self.turns.append(turn)
        return turn

    def get_recent(self, limit: Optional[int] = None) -> List[ConversationTurn]:
        """
        Get recent turns.
        
        Args:
            limit: Maximum number to return (None = all)
            
        Returns:
            List of recent turns
        """
        if limit is None:
            return list(self.turns)
        return list(self.turns)[-limit:]

    def get_context(self, max_turns: Optional[int] = None) -> str:
        """
        Get conversation context as string.
        
        Args:
            max_turns: Maximum turns to include
            
        Returns:
            Formatted context string
        """
        turns = self.get_recent(max_turns)
        
        lines = []
        for turn in turns:
            lines.append(f"{turn.role}: {turn.content}")
        
        return "\n".join(lines)

    def get_by_role(self, role: str) -> List[ConversationTurn]:
        """
        Get turns by role.
        
        Args:
            role: Role to filter by
            
        Returns:
            List of turns from specified role
        """
        return [turn for turn in self.turns if turn.role == role]

    def set_working_memory(self, key: str, value: Any):
        """
        Set working memory value.
        
        Args:
            key: Memory key
            value: Memory value
        """
        self.working_memory[key] = value

    def get_working_memory(self, key: str, default: Any = None) -> Any:
        """
        Get working memory value.
        
        Args:
            key: Memory key
            default: Default value if not found
            
        Returns:
            Memory value or default
        """
        return self.working_memory.get(key, default)

    def clear_working_memory(self):
        """Clear working memory."""
        self.working_memory.clear()

    def should_consolidate(self) -> bool:
        """
        Check if consolidation should occur.
        
        Returns:
            True if should consolidate
        """
        return len(self.turns) >= self.consolidation_threshold

    def prepare_for_consolidation(self) -> List[ConversationTurn]:
        """
        Get turns ready for consolidation.
        
        Returns:
            List of turns to consolidate
        """
        # Return oldest half of turns
        consolidate_count = len(self.turns) // 2
        return list(self.turns)[:consolidate_count]

    def consolidate_to_long_term(
        self,
        long_term_store: MemoryStore,
        importance_threshold: float = 0.5,
    ) -> int:
        """
        Consolidate turns to long-term memory.
        
        Args:
            long_term_store: Long-term memory store
            importance_threshold: Minimum importance to consolidate
            
        Returns:
            Number of memories consolidated
        """
        if not self.should_consolidate():
            return 0
        
        turns_to_consolidate = self.prepare_for_consolidation()
        consolidated = 0
        
        for turn in turns_to_consolidate:
            # Calculate importance based on role and content length
            importance = self._calculate_importance(turn)
            
            if importance >= importance_threshold:
                # Create episodic memory from turn
                long_term_store.add(
                    content=f"{turn.role}: {turn.content}",
                    memory_type=MemoryType.EPISODIC,
                    importance=importance,
                    tags=[turn.role, "conversation"],
                    context={
                        "timestamp": turn.timestamp,
                        "metadata": turn.metadata,
                    },
                )
                consolidated += 1
        
        return consolidated

    def _calculate_importance(self, turn: ConversationTurn) -> float:
        """
        Calculate importance of a turn.
        
        Args:
            turn: Conversation turn
            
        Returns:
            Importance score (0.0 - 1.0)
        """
        # Base importance
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

    def clear(self):
        """Clear all turns."""
        self.turns.clear()
        self.working_memory.clear()

    def get_statistics(self) -> Dict:
        """
        Get short-term memory statistics.
        
        Returns:
            Statistics dictionary
        """
        if not self.turns:
            return {
                "total_turns": 0,
                "capacity": self.capacity,
                "utilization": 0.0,
                "by_role": {},
            }
        
        by_role = {}
        for turn in self.turns:
            by_role[turn.role] = by_role.get(turn.role, 0) + 1
        
        return {
            "total_turns": len(self.turns),
            "capacity": self.capacity,
            "utilization": len(self.turns) / self.capacity,
            "by_role": by_role,
            "working_memory_keys": len(self.working_memory),
            "should_consolidate": self.should_consolidate(),
        }
