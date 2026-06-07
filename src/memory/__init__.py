"""
Memory System - Comprehensive memory management for agents.

This module provides:
- Memory storage (episodic, semantic, procedural)
- Short-term memory (recent context)
- Long-term memory (persistent knowledge)
- Memory retrieval (intelligent search)
- Memory consolidation (STM -> LTM)
- Vector search (embedding-based semantic search)
- SQLite-backed persistence
"""

from src.memory.long_term_memory import LongTermMemory, MemoryIndex, SQLiteLongTermMemory
from src.memory.memory_consolidation import (
    ConsolidationPolicy,
    ConsolidationResult,
    MemoryConsolidator,
)
from src.memory.memory_retrieval import (
    MemoryRetriever,
    RelevanceScorer,
    RetrievalResult,
    RetrievalStrategy,
)
from src.memory.memory_store import (
    ConversationRecord,
    LongTermRecord,
    Memory,
    MemoryStore,
    MemoryType,
    SQLiteStore,
)
from src.memory.short_term_memory import (
    ConversationTurn,
    ShortTermMemory,
    SQLiteShortTermMemory,
)
from src.memory.vector_search import (
    Encoder,
    SentenceTransformerEncoder,
    TfidfEncoder,
    VectorSearcher,
)

__all__ = [
    # Core
    "Memory",
    "MemoryType",
    "MemoryStore",
    # SQLite persistence
    "SQLiteStore",
    "ConversationRecord",
    "LongTermRecord",
    # Short-term
    "ShortTermMemory",
    "ConversationTurn",
    "SQLiteShortTermMemory",
    # Long-term
    "LongTermMemory",
    "MemoryIndex",
    "SQLiteLongTermMemory",
    # Retrieval
    "MemoryRetriever",
    "RetrievalStrategy",
    "RetrievalResult",
    "RelevanceScorer",
    # Consolidation
    "MemoryConsolidator",
    "ConsolidationPolicy",
    "ConsolidationResult",
    # Vector search
    "Encoder",
    "SentenceTransformerEncoder",
    "TfidfEncoder",
    "VectorSearcher",
]
