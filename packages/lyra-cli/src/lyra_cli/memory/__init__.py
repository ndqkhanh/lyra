"""
Lyra Memory System - TencentDB-inspired 4-tier semantic pyramid.

Architecture:
    L3 Persona (User Profile)          → Always loaded, ~500 tokens
        ↓ distills from
    L2 Scenario (Scene Blocks)         → Loaded on-demand, ~2K tokens
        ↓ aggregates
    L1 Atom (Structured Facts)         → Queried via hybrid search
        ↓ extracts from
    L0 Conversation (Raw Dialogue)     → Archived, retrieved for evidence

Key Features:
- Progressive disclosure (load only relevant layers)
- Heterogeneous storage (JSONL + SQLite + Markdown)
- RRF hybrid search (BM25 + Vector, no weight tuning)
- Warmup scheduling (1→2→4→8→5 turns)
- Cache-friendly injection (user message prefix)
"""

from .l0_conversation import ConversationStore, ConversationLog
from .l1_atom import AtomStore, StructuredFact
from .l2_scenario import ScenarioStore, ScenarioBlock
from .l3_persona import PersonaStore, UserPersona
from .search import rrf_merge, hybrid_search, SearchResult
from .utils import WarmupScheduler

__all__ = [
    "ConversationStore",
    "ConversationLog",
    "AtomStore",
    "StructuredFact",
    "ScenarioStore",
    "ScenarioBlock",
    "PersonaStore",
    "UserPersona",
    "rrf_merge",
    "hybrid_search",
    "SearchResult",
    "WarmupScheduler",
]

__version__ = "0.1.0"
