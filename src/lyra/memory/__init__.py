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

# --- New in 7.4.0: Trust Scoring ---
from lyra.memory.trust import (
    TrustScore,
    TrustWeightedBroadcast,
)

# --- New in 7.4.0: Quarantine ---
from lyra.memory.quarantine import (
    QuarantineItem,
    QuarantinePool,
)

# --- New in 7.5.0: Cascade Memory ---
from lyra.memory.cascade_memory import (
    CascadeMemory,
    CascadeRetrievalResult,
    MemoryItem,
    MemoryTier,
    TierAccessStats,
)

# --- New in 8.1.0: Behavioral Clustering ---
from lyra.memory.behavioral_clustering import (
    BehavioralClusterEngine,
    BehavioralClusteringResult,
    BehavioralFeatureExtractor,
    ClusterLabel,
    ClusterLabelGenerator,
    cluster_memory_items,
)

# --- New in 8.1.0: Fusion Retrieval ---
from lyra.memory.memory_retrieval import (
    FusionRetriever,
    FusionWeights,
)

# --- New in 8.1.0: R-KV Pruning ---
from lyra.memory.rkv_pruning import (
    RKVPruner,
    PrunedCache,
    RedundancyAssessor,
    RedundancyScore,
    prune_redundant_keys,
)

# --- New in 8.1.0: Auto-Consolidation ---
from lyra.memory.memory_consolidation import (
    AutoConsolidationScheduler,
    BackgroundConsolidationDaemon,
    ConsolidationStats,
)

# --- New in 8.2.0: Deep Dream Engine ---
from lyra.memory.deep_dream import (
    ConwayCycle,
    ConwayMemory,
    ConwayState,
    DeepDreamObserver,
    DreamObservation,
    DreamQuality,
    MemoryFilesIntegration,
    WarmUpScheduler,
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
    # Trust scoring
    "TrustScore",
    "TrustWeightedBroadcast",
    # Quarantine
    "QuarantineItem",
    "QuarantinePool",
    # Cascade Memory
    "CascadeMemory",
    "CascadeRetrievalResult",
    "MemoryItem",
    "MemoryTier",
    "TierAccessStats",
    # Behavioral Clustering (8.1)
    "BehavioralClusterEngine",
    "BehavioralClusteringResult",
    "BehavioralFeatureExtractor",
    "ClusterLabel",
    "ClusterLabelGenerator",
    "cluster_memory_items",
    # Fusion Retrieval (8.1)
    "FusionRetriever",
    "FusionWeights",
    # R-KV Pruning (8.1)
    "RKVPruner",
    "PrunedCache",
    "RedundancyAssessor",
    "RedundancyScore",
    "prune_redundant_keys",
    # Auto-Consolidation (8.1)
    "AutoConsolidationScheduler",
    "BackgroundConsolidationDaemon",
    "ConsolidationStats",
    # Deep Dream (8.2)
    "ConwayCycle",
    "ConwayMemory",
    "ConwayState",
    "DeepDreamObserver",
    "DreamObservation",
    "DreamQuality",
    "MemoryFilesIntegration",
    "WarmUpScheduler",
]
