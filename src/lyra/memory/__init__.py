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
- Field-theoretic memory (PDE-governed continuous fields)
- Dream engine (idle-time background consolidation)
- Population broadcast (FORGE-style cross-agent memory)
- Latent memory tokens (MemGen-style generative tokens)
"""

from lyra.memory.long_term_memory import LongTermMemory, MemoryIndex, SQLiteLongTermMemory
from lyra.memory.memory_consolidation import (
    ConsolidationPolicy,
    ConsolidationResult,
    MemoryConsolidator,
)
from lyra.memory.memory_retrieval import (
    MemoryRetriever,
    RelevanceScorer,
    RetrievalResult,
    RetrievalStrategy,
)
from lyra.memory.memory_store import (
    ConversationRecord,
    LongTermRecord,
    Memory,
    MemoryStore,
    MemoryType,
    SQLiteStore,
)
from lyra.memory.short_term_memory import (
    ConversationTurn,
    ShortTermMemory,
    SQLiteShortTermMemory,
)
from lyra.memory.vector_search import (
    Encoder,
    SentenceTransformerEncoder,
    TfidfEncoder,
    VectorSearcher,
)

# --- New in 7.3.0: Field-Theoretic Memory ---
from lyra.memory.field_theoretic import (
    FieldMemory,
    FieldPoint,
    FieldState,
    free_energy,
    couple_agent_fields,
    create_field_memory,
)

# --- New in 7.3.0: Dream Engine ---
from lyra.memory.dream_engine import (
    DreamEngine,
    DreamBank,
    DreamEntry,
    DreamAction,
)

# --- New in 7.3.0: Population Broadcast ---
from lyra.memory.population_broadcast import (
    PopulationBroadcast,
    ReflectionAgent,
    SynthesizedMemory,
    MemoryTypeCategory,
    AgentProfile,
    BroadcastEvent,
)

# --- New in 7.3.0: Latent Memory Tokens ---
from lyra.memory.latent_tokens import (
    LatentMemory,
    LatentToken,
    MemSequence,
    MemoryWeaver,
    MemoryTrigger,
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
    # Field-theoretic memory
    "FieldMemory",
    "FieldPoint",
    "FieldState",
    "free_energy",
    "couple_agent_fields",
    "create_field_memory",
    # Dream engine
    "DreamEngine",
    "DreamBank",
    "DreamEntry",
    "DreamAction",
    # Population broadcast
    "PopulationBroadcast",
    "ReflectionAgent",
    "SynthesizedMemory",
    "MemoryTypeCategory",
    "AgentProfile",
    "BroadcastEvent",
    # Latent memory tokens
    "LatentMemory",
    "LatentToken",
    "MemSequence",
    "MemoryWeaver",
    "MemoryTrigger",
]
