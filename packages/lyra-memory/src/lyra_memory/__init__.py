"""
Lyra Memory System - Persistent, temporal, multi-tier memory for AI agents.

This package implements a production-grade memory system with:
- Multi-tier storage (hot/warm/cold/graph)
- Temporal validity tracking
- Hybrid BM25 + vector retrieval
- Contradiction detection
- Verifier-gated writes
- Automatic memory extraction from conversations
- Memory Tree for hierarchical summarization (OpenHuman-inspired)
- Obsidian Wiki integration (Karpathy-style)
- Entity and relation extraction from pentest results

Ultra Memory System (v0.3.0):
- Importance scoring (multi-dimensional)
- ACT-R activation & decay
- Multi-graph knowledge store (MAGMA-inspired)
- Offline consolidation (Auto-Dreamer-inspired)
- Autonomous budget management
"""

from lyra_memory.activation_manager import ActivationManager, ActivationRecord
from lyra_memory.budget_controller import (
    BudgetStatus,
    BudgetTier,
    MemoryBudgetController,
    PruneCandidate,
)
from lyra_memory.consolidation_engine import (
    ConsolidationEngine,
    ConsolidationPattern,
    ConsolidationResult,
)
from lyra_memory.extractor import MemoryExtractor, extract_memories_from_conversation
from lyra_memory.importance_scorer import (
    ImportanceCategory,
    ImportanceScore,
    ImportanceScorer,
)
from lyra_memory.ingestion import (
    Entity,
    EntityExtractor,
    EntityType,
    IngestionJob,
    IngestionQueue,
    Relation,
    RelationExtractor,
    RelationType,
)
from lyra_memory.multi_graph import (
    CausalRelation,
    EntityRelation,
    GraphEdge,
    GraphType,
    MultiGraphStore,
    SemanticRelation,
    TemporalRelation,
)
from lyra_memory.obsidian import ObsidianWiki, WikiPage
from lyra_memory.schema import MemoryRecord, MemoryScope, MemoryType, VerifierStatus
from lyra_memory.store import MemoryStore
from lyra_memory.tree import MemoryTree, TreeNode
from lyra_memory.ultra_system import MemoryStats, UltraMemoryConfig, UltraMemorySystem
from lyra_memory.graph_tier import (
    KnowledgeGraph,
    KnowledgeGraphNode,
    KnowledgeGraphEdge,
    MMRReranker,
    ACTRMemoryModel,
    AutoDreamer,
    FederatedRetriever,
    GraphMemoryStore,
)
from lyra_memory.pgvector_store import (
    InMemoryVectorStore,
    PgVectorConfig,
    PgVectorEmbedding,
    PgVectorStore,
)
from lyra_memory.world_graph import (
    CrossWorldEdge,
    World,
    WorldGraph,
    WorldGraphMemory,
    WorldNode,
    WorldNodeType,
    WorldRelation,
    WorldRelationType,
    WorldSnapshot,
)

__version__ = "0.3.0"

__all__ = [
    # Core
    "MemoryRecord",
    "MemoryScope",
    "MemoryType",
    "VerifierStatus",
    "MemoryStore",
    "MemoryExtractor",
    "extract_memories_from_conversation",
    # Tree
    "MemoryTree",
    "TreeNode",
    # Obsidian
    "ObsidianWiki",
    "WikiPage",
    # Ingestion
    "Entity",
    "EntityType",
    "EntityExtractor",
    "Relation",
    "RelationType",
    "RelationExtractor",
    "IngestionJob",
    "IngestionQueue",
    # Ultra Memory System
    "UltraMemorySystem",
    "UltraMemoryConfig",
    "MemoryStats",
    # Importance Scoring
    "ImportanceScorer",
    "ImportanceScore",
    "ImportanceCategory",
    # Activation & Decay
    "ActivationManager",
    "ActivationRecord",
    # Multi-Graph
    "MultiGraphStore",
    "GraphType",
    "GraphEdge",
    "SemanticRelation",
    "TemporalRelation",
    "CausalRelation",
    "EntityRelation",
    # Consolidation
    "ConsolidationEngine",
    "ConsolidationResult",
    "ConsolidationPattern",
    # Budget Management
    "MemoryBudgetController",
    "BudgetStatus",
    "BudgetTier",
    "PruneCandidate",
    # Graph Tier (Agent Loop 2.0)
    "KnowledgeGraph",
    "KnowledgeGraphNode",
    "KnowledgeGraphEdge",
    "MMRReranker",
    "ACTRMemoryModel",
    "AutoDreamer",
    "FederatedRetriever",
    "GraphMemoryStore",
    # World Graph (WorldDB-style)
    "WorldGraphMemory",
    "WorldGraph",
    "World",
    "WorldNode",
    "WorldNodeType",
    "WorldRelation",
    "WorldRelationType",
    "CrossWorldEdge",
    "WorldSnapshot",
    # PgVector Store
    "PgVectorConfig",
    "PgVectorStore",
    "PgVectorEmbedding",
    "InMemoryVectorStore",
]
