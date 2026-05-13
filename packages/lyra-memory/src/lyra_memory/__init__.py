"""
Lyra Memory System - Persistent, temporal, multi-tier memory for AI agents.

This package implements a production-grade memory system with:
- Multi-tier storage (hot/warm/cold/graph)
- Temporal validity tracking
- Hybrid BM25 + vector retrieval
- Contradiction detection
- Verifier-gated writes
- Automatic memory extraction from conversations
"""

from lyra_memory.extractor import MemoryExtractor, extract_memories_from_conversation
from lyra_memory.schema import MemoryRecord, MemoryScope, MemoryType, VerifierStatus
from lyra_memory.store import MemoryStore

__version__ = "0.1.0"

__all__ = [
    "MemoryRecord",
    "MemoryScope",
    "MemoryType",
    "VerifierStatus",
    "MemoryStore",
    "MemoryExtractor",
    "extract_memories_from_conversation",
]
