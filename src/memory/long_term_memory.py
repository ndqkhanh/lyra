"""
Long-Term Memory - Persistent knowledge base.
"""

import time
from typing import List, Dict, Optional, Set
from collections import defaultdict

from src.memory.memory_store import Memory, MemoryType, MemoryStore


class MemoryIndex:
    """
    Fast retrieval index for memories.
    
    Maintains indices for:
    - Tags
    - Memory types
    - Time ranges
    """

    def __init__(self):
        """Initialize memory index."""
        self.tag_index: Dict[str, Set[str]] = defaultdict(set)
        self.type_index: Dict[MemoryType, Set[str]] = defaultdict(set)
        self.time_index: List[tuple] = []  # (timestamp, memory_id)

    def add_memory(self, memory: Memory):
        """
        Add memory to index.
        
        Args:
            memory: Memory to index
        """
        # Index by tags
        for tag in memory.tags:
            self.tag_index[tag].add(memory.memory_id)
        
        # Index by type
        self.type_index[memory.memory_type].add(memory.memory_id)
        
        # Index by time
        self.time_index.append((memory.timestamp, memory.memory_id))
        self.time_index.sort(reverse=True)  # Most recent first

    def remove_memory(self, memory: Memory):
        """
        Remove memory from index.
        
        Args:
            memory: Memory to remove
        """
        # Remove from tag index
        for tag in memory.tags:
            self.tag_index[tag].discard(memory.memory_id)
        
        # Remove from type index
        self.type_index[memory.memory_type].discard(memory.memory_id)
        
        # Remove from time index
        self.time_index = [
            (ts, mid) for ts, mid in self.time_index
            if mid != memory.memory_id
        ]

    def find_by_tags(self, tags: List[str], match_all: bool = False) -> Set[str]:
        """
        Find memory IDs by tags.
        
        Args:
            tags: Tags to search for
            match_all: If True, must have all tags
            
        Returns:
            Set of memory IDs
        """
        if not tags:
            return set()
        
        if match_all:
            # Intersection of all tag sets
            result = self.tag_index[tags[0]].copy()
            for tag in tags[1:]:
                result &= self.tag_index[tag]
            return result
        else:
            # Union of all tag sets
            result = set()
            for tag in tags:
                result |= self.tag_index[tag]
            return result

    def find_by_type(self, memory_type: MemoryType) -> Set[str]:
        """
        Find memory IDs by type.
        
        Args:
            memory_type: Type to search for
            
        Returns:
            Set of memory IDs
        """
        return self.type_index[memory_type].copy()

    def find_by_time_range(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> List[str]:
        """
        Find memory IDs in time range.
        
        Args:
            start_time: Start timestamp (inclusive)
            end_time: End timestamp (inclusive)
            
        Returns:
            List of memory IDs (sorted by time, most recent first)
        """
        result = []
        
        for timestamp, memory_id in self.time_index:
            if start_time and timestamp < start_time:
                continue
            if end_time and timestamp > end_time:
                continue
            result.append(memory_id)
        
        return result

    def clear(self):
        """Clear all indices."""
        self.tag_index.clear()
        self.type_index.clear()
        self.time_index.clear()


class LongTermMemory:
    """
    Long-term persistent memory.
    
    Responsibilities:
    - Store unlimited memories
    - Fast indexed retrieval
    - Importance-based management
    - Knowledge consolidation
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize long-term memory.
        
        Args:
            storage_path: Path to persist memories
        """
        self.store = MemoryStore(storage_path)
        self.index = MemoryIndex()
        
        # Build index from loaded memories
        self._rebuild_index()

    def add(
        self,
        content: str,
        memory_type: MemoryType,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        context: Optional[Dict] = None,
    ) -> Memory:
        """
        Add a memory to long-term storage.
        
        Args:
            content: Memory content
            memory_type: Type of memory
            importance: Importance score
            tags: Associated tags
            context: Additional context
            
        Returns:
            Created memory
        """
        memory = self.store.add(
            content=content,
            memory_type=memory_type,
            importance=importance,
            tags=tags,
            context=context,
        )
        
        self.index.add_memory(memory)
        return memory

    def get(self, memory_id: str) -> Optional[Memory]:
        """
        Get a memory by ID.
        
        Args:
            memory_id: Memory identifier
            
        Returns:
            Memory if found
        """
        return self.store.get(memory_id)

    def search_by_tags(
        self,
        tags: List[str],
        match_all: bool = False,
        limit: Optional[int] = None,
    ) -> List[Memory]:
        """
        Search memories by tags.
        
        Args:
            tags: Tags to search for
            match_all: If True, must have all tags
            limit: Maximum results to return
            
        Returns:
            List of matching memories
        """
        memory_ids = self.index.find_by_tags(tags, match_all)
        
        memories = []
        for mid in memory_ids:
            memory = self.store.get(mid)
            if memory:
                memories.append(memory)
        
        # Sort by importance
        memories.sort(key=lambda m: m.importance, reverse=True)
        
        if limit:
            memories = memories[:limit]
        
        return memories

    def search_by_type(
        self,
        memory_type: MemoryType,
        limit: Optional[int] = None,
    ) -> List[Memory]:
        """
        Search memories by type.
        
        Args:
            memory_type: Type to search for
            limit: Maximum results to return
            
        Returns:
            List of matching memories
        """
        memory_ids = self.index.find_by_type(memory_type)
        
        memories = []
        for mid in memory_ids:
            memory = self.store.get(mid)
            if memory:
                memories.append(memory)
        
        # Sort by importance
        memories.sort(key=lambda m: m.importance, reverse=True)
        
        if limit:
            memories = memories[:limit]
        
        return memories

    def search_by_time_range(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> List[Memory]:
        """
        Search memories by time range.
        
        Args:
            start_time: Start timestamp
            end_time: End timestamp
            limit: Maximum results to return
            
        Returns:
            List of matching memories
        """
        memory_ids = self.index.find_by_time_range(start_time, end_time)
        
        memories = []
        for mid in memory_ids:
            memory = self.store.get(mid)
            if memory:
                memories.append(memory)
        
        if limit:
            memories = memories[:limit]
        
        return memories

    def search_by_content(
        self,
        query: str,
        limit: Optional[int] = None,
    ) -> List[Memory]:
        """
        Search memories by content (simple keyword search).
        
        Args:
            query: Search query
            limit: Maximum results to return
            
        Returns:
            List of matching memories
        """
        query_lower = query.lower()
        
        matches = []
        for memory in self.store.get_all():
            if query_lower in memory.content.lower():
                matches.append(memory)
        
        # Sort by importance
        matches.sort(key=lambda m: m.importance, reverse=True)
        
        if limit:
            matches = matches[:limit]
        
        return matches

    def get_recent(self, limit: int = 10) -> List[Memory]:
        """
        Get most recent memories.
        
        Args:
            limit: Maximum number to return
            
        Returns:
            List of recent memories
        """
        return self.store.get_recent(limit)

    def get_important(
        self,
        threshold: float = 0.7,
        limit: int = 10,
    ) -> List[Memory]:
        """
        Get most important memories.
        
        Args:
            threshold: Minimum importance
            limit: Maximum number to return
            
        Returns:
            List of important memories
        """
        return self.store.get_important(threshold, limit)

    def merge_similar(
        self,
        similarity_threshold: float = 0.8,
    ) -> int:
        """
        Merge similar memories.
        
        Args:
            similarity_threshold: Minimum similarity to merge
            
        Returns:
            Number of memories merged
        """
        # Simple implementation: merge memories with same content
        content_map: Dict[str, List[Memory]] = defaultdict(list)
        
        for memory in self.store.get_all():
            content_map[memory.content].append(memory)
        
        merged = 0
        for content, memories in content_map.items():
            if len(memories) > 1:
                # Keep most important, merge others
                memories.sort(key=lambda m: m.importance, reverse=True)
                primary = memories[0]
                
                for other in memories[1:]:
                    # Merge tags and context
                    primary.tags = list(set(primary.tags + other.tags))
                    primary.context.update(other.context)
                    
                    # Boost importance
                    primary.importance = min(1.0, primary.importance + 0.1)
                    
                    # Remove duplicate
                    self.store.delete(other.memory_id)
                    self.index.remove_memory(other)
                    
                    merged += 1
        
        return merged

    def apply_decay(self, decay_rate: float = 0.01):
        """
        Apply importance decay to all memories.
        
        Args:
            decay_rate: Rate of decay per day
        """
        self.store.apply_decay(decay_rate)

    def prune(self, min_importance: float = 0.1) -> int:
        """
        Remove low-importance memories.
        
        Args:
            min_importance: Minimum importance to keep
            
        Returns:
            Number of memories pruned
        """
        to_remove = []
        for memory in self.store.get_all():
            if memory.importance < min_importance:
                to_remove.append(memory)
        
        for memory in to_remove:
            self.store.delete(memory.memory_id)
            self.index.remove_memory(memory)
        
        return len(to_remove)

    def save(self):
        """Save memories to disk."""
        self.store.save()

    def load(self):
        """Load memories from disk."""
        self.store.load()
        self._rebuild_index()

    def _rebuild_index(self):
        """Rebuild index from current memories."""
        self.index.clear()
        for memory in self.store.get_all():
            self.index.add_memory(memory)

    def clear(self):
        """Clear all memories."""
        self.store.clear()
        self.index.clear()

    def get_statistics(self) -> Dict:
        """
        Get long-term memory statistics.
        
        Returns:
            Statistics dictionary
        """
        stats = self.store.get_statistics()
        
        # Add index statistics
        stats["indexed_tags"] = len(self.index.tag_index)
        stats["indexed_types"] = len(self.index.type_index)
        
        return stats
