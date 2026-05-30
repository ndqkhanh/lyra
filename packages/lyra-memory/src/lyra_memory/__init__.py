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

from lyra_memory.abstraction.concept_abstractor import (
    AbstractConcept,
    AbstractionLevel,
    ConceptAbstractor,
)
from lyra_memory.abstraction.pattern_recognizer import (
    CrossEpisodePattern,
    PatternRecognizer,
)
from lyra_memory.activation_manager import ActivationManager, ActivationRecord
from lyra_memory.amac_admission import (
    AdmissionConfig,
    AdmissionScore,
    AmacAdmissionGate,
    ContentType,
    MemoryCandidate,
)
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
from lyra_memory.cranimem_gate import (
    CraniMemAdmissionGate,
    CraniMemCandidate,
    CraniMemConfig,
    GateAction,
    GateDecision,
)
from lyra_memory.curriculum.difficulty_scheduler import (
    DifficultyLevel,
    DifficultyScheduler,
    SkillGap,
    TaskCurriculum,
)
from lyra_memory.curriculum.progress_tracker import (
    CompetencyMap,
    CurriculumPhase,
    ProgressTracker,
)
from lyra_memory.dream_consolidator import (
    ConsolidationCandidate,
    ConsolidationStats,
    DreamConsolidator,
    DreamPhase,
    EbbinghausCurve,
    MemoryFragment,
    MemorySignal,
)
from lyra_memory.entropic_consolidation import (
    ConsolidatedMemory,
    ConsolidationPhase,
    EntropicConfig,
    EntropicConsolidator,
)
from lyra_memory.entropic_consolidation import (
    MemoryFragment as EntropicMemoryFragment,
)
from lyra_memory.extractor import MemoryExtractor, extract_memories_from_conversation
from lyra_memory.gossip.consensus_protocol import (
    ConsensusConfig,
    GossipMessage,
    GossipNode,
    MemoryUpdate,
    MergeResult,
    VectorClock,
)
from lyra_memory.graph_tier import (
    ACTRMemoryModel,
    AutoDreamer,
    FederatedRetriever,
    GraphMemoryStore,
    KnowledgeGraph,
    KnowledgeGraphEdge,
    KnowledgeGraphNode,
    MMRReranker,
)
from lyra_memory.health_monitor import (
    HealthConfig,
    HealthSnapshot,
    MemoryHealthMonitor,
)
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
from lyra_memory.mragent.cue_tag_episode import (
    CueTagEpisodeEncoder,
    EpisodeEncoding,
)
from lyra_memory.mragent.cue_tag_semantic import (
    CueTagSemanticEncoder,
    SemanticEncoding,
)
from lyra_memory.mragent.dual_encoder import (
    DenseVector,
    DualEncodedMemory,
    DualEncoder,
    EncoderConfig,
    MRAgentDualEncoder,
    SparseVector,
)
from lyra_memory.routing_fabric import (
    MemoryResult,
    RoutingConfig,
    RoutingFabric,
)
from lyra_memory.context_prioritizer import ContextPrioritizer
from lyra_memory.progressive_disclosure import (
    DisclosureConfig,
    DisclosureLevel,
    ProgressiveDisclosureManager,
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
from lyra_memory.operations.batch_processor import (
    BatchOpResult,
    BatchProcessor,
    OperationType,
)
from lyra_memory.operations.integrity_checker import (
    IntegrityChecker,
    IntegrityReport,
    IntegrityStatus,
)
from lyra_memory.pgvector_store import (
    InMemoryVectorStore,
    PgVectorConfig,
    PgVectorEmbedding,
    PgVectorStore,
)
from lyra_memory.schema import MemoryRecord, MemoryScope, MemoryType, VerifierStatus
from lyra_memory.search import (
    InMemorySearchBackend,
    Observation,
    SearchBackend,
    SearchHit,
    SearchResult,
    ThreeLayerSearch,
    ThreeLayerSearchConfig,
    TimelineEntry,
)
from lyra_memory.store import MemoryStore
from lyra_memory.symbolic_ssm import (
    CraniMemGate,
    EntityNode,
    SymbolicRepresentation,
    SymbolicShortTermMemory,
)
from lyra_memory.symbolic_ssm import (
    Relation as SSMRelation,
)
from lyra_memory.tree import MemoryTree, TreeNode
from lyra_memory.ultra_system import MemoryStats, UltraMemoryConfig, UltraMemorySystem
from lyra_memory.verbatim_cache import (
    CachePriority,
    VerbatimCache,
    VerbatimEntry,
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

__version__ = "0.4.0"

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
    # Dream Consolidation
    "MemorySignal",
    "DreamPhase",
    "MemoryFragment",
    "ConsolidationCandidate",
    "EbbinghausCurve",
    "ConsolidationStats",
    "DreamConsolidator",
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
    # 3-Layer Memory Search
    "InMemorySearchBackend",
    "Observation",
    "SearchBackend",
    "SearchHit",
    "SearchResult",
    "ThreeLayerSearch",
    "ThreeLayerSearchConfig",
    "TimelineEntry",
    # A-MAC Admission Control
    "AdmissionConfig",
    "AdmissionScore",
    "AmacAdmissionGate",
    "ContentType",
    "MemoryCandidate",
    # Health Monitor
    "HealthConfig",
    "HealthSnapshot",
    "MemoryHealthMonitor",
    # Symbolic SSM (Phoenix Memory — Plan 30)
    "SymbolicShortTermMemory",
    "SymbolicRepresentation",
    "CraniMemGate",
    "EntityNode",
    "SSMRelation",
    # MRAgent Dual Encoding
    "CueTagEpisodeEncoder",
    "CueTagSemanticEncoder",
    "DenseVector",
    "DualEncodedMemory",
    "DualEncoder",
    "EncoderConfig",
    "EpisodeEncoding",
    "MRAgentDualEncoder",
    "SemanticEncoding",
    "SparseVector",
    # Routing Fabric
    "MemoryResult",
    "RoutingConfig",
    "RoutingFabric",
    # Progressive Disclosure
    "ContextPrioritizer",
    "DisclosureConfig",
    "DisclosureLevel",
    "ProgressiveDisclosureManager",
    # Entropic Consolidation (Plan 30)
    "ConsolidatedMemory",
    "ConsolidationPhase",
    "EntropicConfig",
    "EntropicConsolidator",
    "EntropicMemoryFragment",
    # CraniMem Admission Gate (Plan 30)
    "CraniMemAdmissionGate",
    "CraniMemCandidate",
    "CraniMemConfig",
    "GateAction",
    "GateDecision",
    # Gossip Consensus Protocol
    "ConsensusConfig",
    "GossipMessage",
    "GossipNode",
    "MemoryUpdate",
    "MergeResult",
    "VectorClock",
    # Verbatim Cache
    "CachePriority",
    "VerbatimCache",
    "VerbatimEntry",
    # Curriculum Learning (Plan 27)
    "CompetencyMap",
    "CurriculumPhase",
    "DifficultyLevel",
    "DifficultyScheduler",
    "ProgressTracker",
    "SkillGap",
    "TaskCurriculum",
    # Abstraction Layer (Plan 27)
    "AbstractConcept",
    "AbstractionLevel",
    "ConceptAbstractor",
    "CrossEpisodePattern",
    "PatternRecognizer",
    # Batch Operations (Plan 27)
    "BatchOpResult",
    "BatchProcessor",
    "IntegrityChecker",
    "IntegrityReport",
    "IntegrityStatus",
    "OperationType",
]
