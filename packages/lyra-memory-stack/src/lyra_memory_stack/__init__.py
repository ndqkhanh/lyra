"""Lyra Memory Stack — Multi-layered memory system for Lyra agents.

Provides L0-L3 memory layers with progressive disclosure retrieval:
- L0: Working Memory (active context window management)
- L1: Episodic Memory (session events, SQLite+FTS5)
- L2: Semantic Memory (facts, patterns, embeddings)
- L3: Procedural Memory (skills, workflows, KG)

Plus supporting infrastructure: privacy tiers, decay management,
symbolic compression, dual-trace encoding, dream cycle enrichment,
and MCP tool server.
"""

from __future__ import annotations

from .working_memory import (
    ContextItem,
    WorkingMemory,
    estimate_tokens,
)

from .episodic_memory import (
    EpisodeEvent,
    EpisodicMemory,
    SearchResult,
)

from .semantic_memory import (
    Fact,
    FactQueryResult,
    SemanticMemory,
)

from .procedural_memory import (
    KnowledgeEdge,
    ProceduralMemory,
    Skill,
    WorkflowStep,
    WorkflowTemplate,
)

from .retrieval import (
    Layer1Index,
    Layer2Timeline,
    Layer3Detail,
    RetrievalManager,
)

from .dual_trace import (
    DualTraceEntry,
    DualTraceStore,
    SceneTrace,
    SceneType,
)

from .symbolic_compressor import (
    CompressedSymbol,
    SymbolicCompressor,
    ToolCall,
)

from .privacy_tiers import (
    PrivacyManager,
    PrivacyPolicy,
    PrivacyTier,
    cascade_tiers,
)

from .decay_manager import (
    Contradiction,
    DecayManager,
    DecayPolicy,
    MemoryEntry,
    MemoryType,
)

from .dream_cycle import (
    DreamCycle,
    DreamInsight,
)

from .mcp_server import (
    MCPServer,
)

from .exceptions import (
    CompressionError,
    DecayError,
    DreamCycleError,
    MemoryCapacityError,
    MemoryError,
    MemoryNotFoundError,
    PrivacyViolationError,
    RetrievalError,
)

__all__ = [
    # Working Memory
    "ContextItem",
    "WorkingMemory",
    "estimate_tokens",
    # Episodic Memory
    "EpisodeEvent",
    "EpisodicMemory",
    "SearchResult",
    # Semantic Memory
    "Fact",
    "FactQueryResult",
    "SemanticMemory",
    # Procedural Memory
    "KnowledgeEdge",
    "ProceduralMemory",
    "Skill",
    "WorkflowStep",
    "WorkflowTemplate",
    # Retrieval
    "Layer1Index",
    "Layer2Timeline",
    "Layer3Detail",
    "RetrievalManager",
    # Dual Trace
    "DualTraceEntry",
    "DualTraceStore",
    "SceneTrace",
    "SceneType",
    # Symbolic Compression
    "CompressedSymbol",
    "SymbolicCompressor",
    "ToolCall",
    # Privacy Tiers
    "PrivacyManager",
    "PrivacyPolicy",
    "PrivacyTier",
    "cascade_tiers",
    # Decay Manager
    "Contradiction",
    "DecayManager",
    "DecayPolicy",
    "MemoryEntry",
    "MemoryType",
    # Dream Cycle
    "DreamCycle",
    "DreamInsight",
    # MCP Server
    "MCPServer",
    # Exceptions
    "CompressionError",
    "DecayError",
    "DreamCycleError",
    "MemoryCapacityError",
    "MemoryError",
    "MemoryNotFoundError",
    "PrivacyViolationError",
    "RetrievalError",
]
