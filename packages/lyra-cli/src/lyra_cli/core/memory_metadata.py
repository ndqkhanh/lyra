"""Memory metadata models."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class MemoryType(Enum):
    """Memory types."""
    CONVERSATION = "conversation"
    PROJECT = "project"
    PREFERENCE = "preference"


@dataclass
class MemoryMetadata:
    """Metadata for a memory entry."""

    id: str
    content: str
    memory_type: MemoryType
    timestamp: datetime
    tags: list[str]
    metadata: dict[str, Any] | None = None
