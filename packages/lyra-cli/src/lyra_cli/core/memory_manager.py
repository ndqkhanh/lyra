"""Memory manager for managing memory entries."""
from typing import List, Optional
from datetime import datetime
import uuid

from .memory_storage import MemoryStorage
from .memory_metadata import MemoryMetadata, MemoryType


class MemoryManager:
    """Manager for memory entries."""

    def __init__(self, storage: MemoryStorage):
        self.storage = storage

    def add(self, content: str, memory_type: MemoryType, tags: List[str]) -> MemoryMetadata:
        """Add a new memory entry."""
        memory = MemoryMetadata(
            id=str(uuid.uuid4()),
            content=content,
            memory_type=memory_type,
            timestamp=datetime.now(),
            tags=tags
        )
        self.storage.save(memory)
        return memory

    def get(self, memory_id: str) -> Optional[MemoryMetadata]:
        """Get a memory by ID."""
        return self.storage.load(memory_id)

    def search(self, query: str) -> List[MemoryMetadata]:
        """Search memories by content or tags."""
        query_lower = query.lower()
        return [
            m for m in self.storage.list_all()
            if query_lower in m.content.lower() or any(query_lower in tag.lower() for tag in m.tags)
        ]

    def filter_by_type(self, memory_type: MemoryType) -> List[MemoryMetadata]:
        """Filter memories by type."""
        return [m for m in self.storage.list_all() if m.memory_type == memory_type]

    def delete(self, memory_id: str) -> bool:
        """Delete a memory."""
        return self.storage.delete(memory_id)

    def list_all(self) -> List[MemoryMetadata]:
        """List all memories."""
        return self.storage.list_all()
