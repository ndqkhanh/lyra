"""
Lyra Memory System — 5-tier semantic pyramid with hybrid retrieval.

Architecture:
    L5 Persona (Identity & Style)       → Always loaded, ~2K tokens
        ↓ distills from
    L4 Meta (Cross-Session Patterns)    → Loaded on-demand, ~5K tokens
        ↓ synthesizes from
    L3 Procedural (Skills & Workflows)  → Trigger-indexed, ~10K tokens
        ↓ aggregates
    L2 Semantic (Knowledge Graph)       → Entity-relation with PPR
        ↓ populates from
    L1 Episodic + L0 Working            → BM25+Vector+RRF + verbatim cache

Key Features:
- Progressive disclosure (load only relevant layers)
- DCI zero-index grep (Tier 0 retrieval, <1ms)
- RRF hybrid search (BM25 + Vector, no weight tuning)
- RTK + Caveman context compression (80% token reduction)
- Entropy filtering (10-38x low-info removal)
- Dream consolidation with spaced repetition
- Question-driven reflection for memory strengthening
- Cross-session pattern weaving
"""

from .context_optimizer import (
    CavemanCompressor,
    CavemanResult,
    CompressedContent,
    CompressionStrategy,
    ContextItem,
    EntropyFilter,
    EntropyLevel,
    FilteredContext,
    OffloadedContext,
    RTKCompressor,
    SymbolEntry,
    SymbolGraphOffloader,
)
from .dream_reflector import (
    QuestionDrivenReflector,
    QuestionType,
    ReflectionQuestion,
    ReflectionSession,
    ReflectionSignal,
    SignalStrength,
)
from .dream_scheduler import (
    DreamScheduleTrigger,
    DreamScheduler,
    ScheduleEntry,
    SchedulerState,
)
from .l0_conversation import ConversationLog, ConversationStore
from .l1_atom import AtomStore, StructuredFact
from .l2_scenario import ScenarioBlock, ScenarioStore
from .l3_persona import PersonaStore, UserPersona
from .l4_meta import (
    CrossSessionPattern,
    CrossSessionWeaver,
    KnowledgeConfidence,
    KnowledgeType,
    MetaKnowledge,
    MetaKnowledgeStore,
    Strategy,
    StrategyEvolution,
    StrategyStatus,
    StrategyType,
)
from .l5_persona import (
    AccumulatedPreference,
    IdentityModel,
    IdentityTrait,
    PersonaSnapshot,
    PersonaStore as L5PersonaStore,
    PreferenceAccumulator,
    PreferenceSource,
    StyleDimension,
    StyleLearner,
    StylePreference,
    TraitCategory,
)
from .search import (
    DCIZeroIndex,
    DisclosureBatch,
    DisclosureLevel,
    DisclosedMemory,
    GrepResult,
    MatchType,
    ProgressiveDisclosure,
    RankedResult,
    RetrievalContext,
    RetrievalReport,
    RetrievalRouter,
    RetrievalTier,
    SearchResult,
    VerbatimHit,
    VerbatimLayer,
    hybrid_search,
    rrf_merge,
)
from .utils import WarmupScheduler

__all__ = [
    "AccumulatedPreference",
    "AtomStore",
    "CavemanCompressor",
    "CavemanResult",
    "CompressedContent",
    "CompressionStrategy",
    "ContextItem",
    "ConversationLog",
    "ConversationStore",
    "CrossSessionPattern",
    "CrossSessionWeaver",
    "DCIZeroIndex",
    "DisclosureBatch",
    "DisclosureLevel",
    "DisclosedMemory",
    "DreamScheduleTrigger",
    "DreamScheduler",
    "EntropyFilter",
    "EntropyLevel",
    "FilteredContext",
    "GrepResult",
    "IdentityModel",
    "IdentityTrait",
    "KnowledgeConfidence",
    "KnowledgeType",
    "L5PersonaStore",
    "MatchType",
    "MetaKnowledge",
    "MetaKnowledgeStore",
    "OffloadedContext",
    "PersonaSnapshot",
    "PersonaStore",
    "PreferenceAccumulator",
    "PreferenceSource",
    "ProgressiveDisclosure",
    "QuestionDrivenReflector",
    "QuestionType",
    "RTKCompressor",
    "RankedResult",
    "ReflectionQuestion",
    "ReflectionSession",
    "ReflectionSignal",
    "RetrievalContext",
    "RetrievalReport",
    "RetrievalRouter",
    "RetrievalTier",
    "ScenarioBlock",
    "ScenarioStore",
    "ScheduleEntry",
    "SchedulerState",
    "SearchResult",
    "SignalStrength",
    "Strategy",
    "StrategyEvolution",
    "StrategyStatus",
    "StrategyType",
    "StructuredFact",
    "StyleDimension",
    "StyleLearner",
    "StylePreference",
    "SymbolEntry",
    "SymbolGraphOffloader",
    "TraitCategory",
    "UserPersona",
    "VerbatimHit",
    "VerbatimLayer",
    "WarmupScheduler",
    "hybrid_search",
    "rrf_merge",
]

__version__ = "0.2.0"
