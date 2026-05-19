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
"""

from lyra_memory.extractor import MemoryExtractor, extract_memories_from_conversation
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
from lyra_memory.obsidian import ObsidianWiki, WikiPage
from lyra_memory.schema import MemoryRecord, MemoryScope, MemoryType, VerifierStatus
from lyra_memory.store import MemoryStore
from lyra_memory.tree import MemoryTree, TreeNode

__version__ = "0.2.0"

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
]
