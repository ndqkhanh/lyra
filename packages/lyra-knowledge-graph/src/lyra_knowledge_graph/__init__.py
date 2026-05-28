"""Lyra Knowledge Graph — Dynamic knowledge graph construction and navigation.

Provides entity extraction, relation labeling, community detection, graph
navigation, codebase pre-indexing, inverse search, RRF fusion, dream cycle
enrichment, and MCP tool access for research-grade knowledge graphs.
"""

from __future__ import annotations

from .community_detector import (
    Community,
    CommunityDetector,
)
from .dream_cycle import (
    DreamCycle,
    KGDreamCycle,
)
from .entity_extractor import (
    EntityExtractor,
    EntityKind,
    ExtractedEntity,
)
from .exceptions import (
    EdgeNotFoundError,
    ExtractionError,
    IndexingError,
    KnowledgeGraphError,
    NavigationError,
    NodeNotFoundError,
)
from .graph_builder import (
    EdgeRelation,
    GraphBuilder,
    KnowledgeEdge,
    KnowledgeGraph,
    KnowledgeNode,
    NodeType,
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
from .inverse_search import (
    HypothesisScore,
    InverseSearch,
    InverseSearchEngine,
)
from .kg_consolidator import (
    ConflictResolution,
    ConsolidationReport,
    KGConsolidator,
    MergeStrategy,
)
from .mcp_server import (
    KnowledgeGraphMCPServer,
)
from .navigation_engine import (
    NavigationEngine,
    TraversalStrategy,
)
from .pre_indexer import (
    DependencyEntry,
    FileIndex,
    PreIndexer,
    SymbolEntry,
)
from .relation_labeler import (
    EdgeLabel,
    LabeledEdge,
    RelationConfidence,
    RelationLabeler,
)
from .rrf_fusion import (
    FusionResult,
    RRFFusion,
    RRFusion,
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
