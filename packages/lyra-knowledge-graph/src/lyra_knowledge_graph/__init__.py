"""Lyra Knowledge Graph — Dynamic knowledge graph construction and navigation.

Provides entity extraction, relation labeling, community detection, graph
navigation, codebase pre-indexing, inverse search, RRF fusion, dream cycle
enrichment, and MCP tool access for research-grade knowledge graphs.
"""

from __future__ import annotations

from .graph_builder import (
    NodeType,
    EdgeRelation,
    KnowledgeNode,
    KnowledgeEdge,
    KnowledgeGraph,
    GraphBuilder,
)

from .entity_extractor import (
    EntityKind,
    ExtractedEntity,
    EntityExtractor,
)

from .relation_labeler import (
    EdgeLabel,
    RelationConfidence,
    LabeledEdge,
    RelationLabeler,
)

from .community_detector import (
    Community,
    CommunityDetector,
)

from .navigation_engine import (
    TraversalStrategy,
    NavigationEngine,
)

from .pre_indexer import (
    FileIndex,
    SymbolEntry,
    DependencyEntry,
    PreIndexer,
)

from .inverse_search import (
    InverseSearchEngine,
    HypothesisScore,
    InverseSearch,
)

from .rrf_fusion import (
    RRFusion,
    FusionResult,
    RRFFusion,
)

from .dream_cycle import (
    DreamCycle,
    KGDreamCycle,
)

from .mcp_server import (
    KnowledgeGraphMCPServer,
)

from .exceptions import (
    KnowledgeGraphError,
    NodeNotFoundError,
    EdgeNotFoundError,
    ExtractionError,
    IndexingError,
    NavigationError,
)

from .graph_querier import (
    GraphQuerier,
    PathResult,
    QueryResult,
    QueryStrategy,
    SortOrder,
    SubgraphResult,
)

from .graph_visualizer import (
    ExportFormat,
    GraphVisualizer,
    VisualStyle,
)

from .kg_consolidator import (
    ConflictResolution,
    ConsolidationReport,
    KGConsolidator,
    MergeStrategy,
)

__all__ = [
    # Graph builder
    "NodeType",
    "EdgeRelation",
    "KnowledgeNode",
    "KnowledgeEdge",
    "KnowledgeGraph",
    "GraphBuilder",
    # Entity extractor
    "EntityKind",
    "ExtractedEntity",
    "EntityExtractor",
    # Relation labeler
    "EdgeLabel",
    "RelationConfidence",
    "LabeledEdge",
    "RelationLabeler",
    # Community detector
    "Community",
    "CommunityDetector",
    # Navigation engine
    "TraversalStrategy",
    "NavigationEngine",
    # Pre-indexer
    "FileIndex",
    "SymbolEntry",
    "DependencyEntry",
    "PreIndexer",
    # Inverse search
    "InverseSearchEngine",
    "HypothesisScore",
    "InverseSearch",
    # RRF fusion
    "RRFusion",
    "FusionResult",
    "RRFFusion",
    # Dream cycle
    "DreamCycle",
    "KGDreamCycle",
    # MCP server
    "KnowledgeGraphMCPServer",
    # Graph querier (Plan 32)
    "GraphQuerier",
    "PathResult",
    "QueryResult",
    "QueryStrategy",
    "SortOrder",
    "SubgraphResult",
    # Graph visualizer (Plan 32)
    "ExportFormat",
    "GraphVisualizer",
    "VisualStyle",
    # KG consolidator (Plan 32)
    "ConflictResolution",
    "ConsolidationReport",
    "KGConsolidator",
    "MergeStrategy",
    # Exceptions
    "KnowledgeGraphError",
    "NodeNotFoundError",
    "EdgeNotFoundError",
    "ExtractionError",
    "IndexingError",
    "NavigationError",
]
