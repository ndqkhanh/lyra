"""Memory metadata models."""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


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
    tags: List[str]
    metadata: Optional[Dict[str, Any]] = None
