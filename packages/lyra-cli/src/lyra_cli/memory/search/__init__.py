"""Search utilities for Lyra memory system — hybrid retrieval, DCI grep, progressive disclosure."""

from .dci_zero_index import DCIZeroIndex, GrepResult, MatchType
from .progressive_disclosure import DisclosureBatch, DisclosureLevel, DisclosedMemory, ProgressiveDisclosure
from .retrieval_router import RankedResult, RetrievalContext, RetrievalReport, RetrievalRouter, RetrievalTier
from .rrf import SearchResult, hybrid_search, rrf_merge
from .verbatim_layer import VerbatimHit, VerbatimLayer

__all__ = [
    "DCIZeroIndex",
    "DisclosureBatch",
    "DisclosureLevel",
    "DisclosedMemory",
    "GrepResult",
    "MatchType",
    "ProgressiveDisclosure",
    "RankedResult",
    "RetrievalContext",
    "RetrievalReport",
    "RetrievalRouter",
    "RetrievalTier",
    "SearchResult",
    "VerbatimHit",
    "VerbatimLayer",
    "hybrid_search",
    "rrf_merge",
]
