"""
Memory Store - Core storage for agent memories.
"""

import json
import time
import uuid
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path


class MemoryType(Enum):
    """Types of memories."""
    EPISODIC = "episodic"      # Specific events and experiences
    SEMANTIC = "semantic"      # General knowledge and facts
    PROCEDURAL = "procedural"  # How to perform tasks


@dataclass
class Memory:
    """
    A single memory entry.
    
    Attributes:
        memory_id: Unique identifier
        content: Memory content
        memory_type: Type of memory
        timestamp: When memory was created
        importance: Importance score (0.0 - 1.0)
        tags: Associated tags
        context: Additional context
        access_count: Number of times accessed
        last_accessed: Last access timestamp
    """
    memory_id: str
    content: str
    memory_type: MemoryType
    timestamp: float
    importance: float = 0.5
    tags: List[str] = None
    context: Dict[str, Any] = None
    access_count: int = 0
    last_accessed: float = 0.0

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.context is None:
            self.context = {}
        if self.last_accessed == 0.0:
            self.last_accessed = self.timestamp

    def to_dict(self) -> Dict:
        """Convert memory to dictionary."""
        data = asdict(self)
        data["memory_type"] = self.memory_type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "Memory":
        """Create memory from dictionary."""
        data = data.copy()
        data["memory_type"] = MemoryType(data["memory_type"])
        return cls(**data)

    def access(self):
        """Record memory access."""
        self.access_count += 1
        self.last_accessed = time.time()

    def decay_importance(self, decay_rate: float = 0.01):
        """
        Decay importance over time.
        
        Args:
            decay_rate: Rate of decay per day
        """
        days_since_access = (time.time() - self.last_accessed) / 86400
        decay = decay_rate * days_since_access
        self.importance = max(0.0, self.importance - decay)


class MemoryStore:
    """
    Core storage for memories.
    
    Responsibilities:
    - Store and retrieve memories
    - Manage memory lifecycle
    - Persist memories to disk
    - Apply importance decay
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize memory store.
        
        Args:
            storage_path: Path to persist memories (optional)
        """
        self.memories: Dict[str, Memory] = {}
        self.storage_path = storage_path

        if storage_path:
            self.load()

    def add(
        self,
        content: str,
        memory_type: MemoryType,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Memory:
        """
        Add a new memory.
        
        Args:
            content: Memory content
            memory_type: Type of memory
            importance: Importance score (0.0 - 1.0)
            tags: Associated tags
            context: Additional context
            
        Returns:
            Created memory
        """
        memory = Memory(
            memory_id=str(uuid.uuid4()),
            content=content,
            memory_type=memory_type,
            timestamp=time.time(),
            importance=importance,
            tags=tags or [],
            context=context or {},
        )

        self.memories[memory.memory_id] = memory
        return memory

    def get(self, memory_id: str) -> Optional[Memory]:
        """
        Get a memory by ID.
        
        Args:
            memory_id: Memory identifier
            
        Returns:
            Memory if found, None otherwise
        """
        memory = self.memories.get(memory_id)
        if memory:
            memory.access()
        return memory

    def update(self, memory_id: str, **kwargs) -> bool:
        """
        Update a memory.
        
        Args:
            memory_id: Memory identifier
            **kwargs: Fields to update
            
        Returns:
            True if updated, False if not found
        """
        memory = self.memories.get(memory_id)
        if not memory:
            return False

        for key, value in kwargs.items():
            if hasattr(memory, key):
                setattr(memory, key, value)

        return True

    def delete(self, memory_id: str) -> bool:
        """
        Delete a memory.
        
        Args:
            memory_id: Memory identifier
            
        Returns:
            True if deleted, False if not found
        """
        if memory_id in self.memories:
            del self.memories[memory_id]
            return True
        return False

    def get_all(self) -> List[Memory]:
        """
        Get all memories.
        
        Returns:
            List of all memories
        """
        return list(self.memories.values())

    def get_by_type(self, memory_type: MemoryType) -> List[Memory]:
        """
        Get memories by type.
        
        Args:
            memory_type: Type to filter by
            
        Returns:
            List of memories of specified type
        """
        return [
            m for m in self.memories.values()
            if m.memory_type == memory_type
        ]

    def get_by_tags(self, tags: List[str], match_all: bool = False) -> List[Memory]:
        """
        Get memories by tags.
        
        Args:
            tags: Tags to search for
            match_all: If True, memory must have all tags
            
        Returns:
            List of matching memories
        """
        if match_all:
            return [
                m for m in self.memories.values()
                if all(tag in m.tags for tag in tags)
            ]
        else:
            return [
                m for m in self.memories.values()
                if any(tag in m.tags for tag in tags)
            ]

    def get_recent(self, limit: int = 10) -> List[Memory]:
        """
        Get most recent memories.
        
        Args:
            limit: Maximum number to return
            
        Returns:
            List of recent memories
        """
        sorted_memories = sorted(
            self.memories.values(),
            key=lambda m: m.timestamp,
            reverse=True
        )
        return sorted_memories[:limit]

    def get_important(self, threshold: float = 0.7, limit: int = 10) -> List[Memory]:
        """
        Get most important memories.
        
        Args:
            threshold: Minimum importance score
            limit: Maximum number to return
            
        Returns:
            List of important memories
        """
        important = [
            m for m in self.memories.values()
            if m.importance >= threshold
        ]
        sorted_important = sorted(
            important,
            key=lambda m: m.importance,
            reverse=True
        )
        return sorted_important[:limit]

    def apply_decay(self, decay_rate: float = 0.01):
        """
        Apply importance decay to all memories.
        
        Args:
            decay_rate: Rate of decay per day
        """
        for memory in self.memories.values():
            memory.decay_importance(decay_rate)

    def prune(self, min_importance: float = 0.1):
        """
        Remove memories below importance threshold.
        
        Args:
            min_importance: Minimum importance to keep
            
        Returns:
            Number of memories pruned
        """
        to_remove = [
            mid for mid, m in self.memories.items()
            if m.importance < min_importance
        ]

        for mid in to_remove:
            del self.memories[mid]

        return len(to_remove)

    def save(self):
        """Save memories to disk."""
        if not self.storage_path:
            return

        path = Path(self.storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "memories": [m.to_dict() for m in self.memories.values()]
        }

        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def load(self):
        """Load memories from disk."""
        if not self.storage_path:
            return

        path = Path(self.storage_path)
        if not path.exists():
            return

        with open(path, 'r') as f:
            data = json.load(f)

        self.memories = {}
        for mem_data in data.get("memories", []):
            memory = Memory.from_dict(mem_data)
            self.memories[memory.memory_id] = memory

    def clear(self):
        """Clear all memories."""
        self.memories.clear()

    def get_statistics(self) -> Dict:
        """
        Get memory statistics.
        
        Returns:
            Statistics dictionary
        """
        if not self.memories:
            return {
                "total_memories": 0,
                "by_type": {},
                "average_importance": 0.0,
                "total_accesses": 0,
            }

        by_type = {}
        for memory in self.memories.values():
            mtype = memory.memory_type.value
            by_type[mtype] = by_type.get(mtype, 0) + 1

        total_importance = sum(m.importance for m in self.memories.values())
        total_accesses = sum(m.access_count for m in self.memories.values())

        return {
            "total_memories": len(self.memories),
            "by_type": by_type,
            "average_importance": total_importance / len(self.memories),
            "total_accesses": total_accesses,
            "average_accesses": total_accesses / len(self.memories),
        }
