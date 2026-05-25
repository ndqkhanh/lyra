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
)

from .entity_extractor import (
    EntityKind,
    ExtractedEntity,
    EntityExtractor,
)

from .relation_labeler import (
    EdgeLabel,
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
)

from .rrf_fusion import (
    RRFusion,
    FusionResult,
)

from .dream_cycle import (
    DreamCycle,
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

__all__ = [
    # Graph builder
    "NodeType",
    "EdgeRelation",
    "KnowledgeNode",
    "KnowledgeEdge",
    "KnowledgeGraph",
    # Entity extractor
    "EntityKind",
    "ExtractedEntity",
    "EntityExtractor",
    # Relation labeler
    "EdgeLabel",
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
    # RRF fusion
    "RRFusion",
    "FusionResult",
    # Dream cycle
    "DreamCycle",
    # MCP server
    "KnowledgeGraphMCPServer",
    # Exceptions
    "KnowledgeGraphError",
    "NodeNotFoundError",
    "EdgeNotFoundError",
    "ExtractionError",
    "IndexingError",
    "NavigationError",
]
