"""Memory storage for persisting memories."""
from pathlib import Path
from typing import List, Optional
import json
from datetime import datetime

from .memory_metadata import MemoryMetadata, MemoryType


class MemoryStorage:
    """Storage for memory entries."""

    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, memory: MemoryMetadata) -> None:
        """Save a memory entry."""
        file_path = self.storage_dir / f"{memory.id}.json"
        data = {
            "id": memory.id,
            "content": memory.content,
            "memory_type": memory.memory_type.value,
            "timestamp": memory.timestamp.isoformat(),
            "tags": memory.tags,
            "metadata": memory.metadata
        }
        file_path.write_text(json.dumps(data, indent=2))

    def load(self, memory_id: str) -> Optional[MemoryMetadata]:
        """Load a memory entry by ID."""
        file_path = self.storage_dir / f"{memory_id}.json"
        if not file_path.exists():
            return None

        data = json.loads(file_path.read_text())
        return MemoryMetadata(
            id=data["id"],
            content=data["content"],
            memory_type=MemoryType(data["memory_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            tags=data["tags"],
            metadata=data.get("metadata")
        )

    def list_all(self) -> List[MemoryMetadata]:
        """List all memory entries."""
        memories = []
        for file_path in self.storage_dir.glob("*.json"):
            memory_id = file_path.stem
            memory = self.load(memory_id)
            if memory:
                memories.append(memory)
        return memories

    def delete(self, memory_id: str) -> bool:
        """Delete a memory entry."""
        file_path = self.storage_dir / f"{memory_id}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False
