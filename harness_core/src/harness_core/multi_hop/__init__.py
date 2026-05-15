"""harness_core.multi_hop — multi-hop reasoning substrate.

Per [docs/199-multi-hop-reasoning-techniques-arc.md](../../../../../../research/harness-engineering/docs/199-multi-hop-reasoning-techniques-arc.md),
[docs/200-graph-grounded-multi-hop-retrieval.md](../../../../../../research/harness-engineering/docs/200-graph-grounded-multi-hop-retrieval.md),
and [docs/211-cross-project-power-up-plan-with-tradeoffs.md](../../../../../../research/harness-engineering/docs/211-cross-project-power-up-plan-with-tradeoffs.md)
§9 milestone M3.

Promoted from ``polaris-core/memory/ppr_fusion.py`` (HippoRAG-2 over Polaris's
ProgramGraph) and abstracted via Protocols so it runs on any graph substrate.
Also ships the decomposition cache from the Tier-0 day-by-day checklists.

Modules:
    - ``hipporag`` — Personalized PageRank + dense embedding fusion (single-shot
      multi-hop retrieval; HippoRAG-2 arXiv:2502.14802 ICML 2025).
    - ``types`` — Node/Edge/Graph/Document protocols + simple dataclass impls.
    - ``decomposition_cache`` — sub-question decomposition memo (per [docs/199]
      and Tier-0 of [docs/203]/[docs/208]/[docs/220]).
"""
from __future__ import annotations

from .anchor_predictor import (
    AnchorCandidate,
    AnchorPredictor,
    FixedAnchorPredictor,
    TokenOverlapAnchorPredictor,
    merge_predictors,
)
from .beam_retrieval import (
    BeamCandidate,
    BeamResult,
    BeamRetriever,
    BeamScorer,
    CoverageScorer,
)
from .decomposition_cache import (
    DecompositionCache,
    DecompositionEntry,
    normalize_question,
)
from .hipporag import (
    Embedder,
    EntityExtractor,
    HashEmbedder,
    HippoRAGRetriever,
    PersonalizedPageRank,
    RetrievalResult,
    TitleEntityExtractor,
    cosine,
    graph_to_adjacency,
)
from .operators import (
    IRCoTOperator,
    IRCoTResult,
    IRCoTStep,
    LLMTextGenerator,
    Retriever,
    RetrievedDoc,
    SelfAskOperator,
    SelfAskResult,
    SelfAskStep,
    StubLLM,
    StubRetriever,
    parse_self_ask_response,
)
from .plan_on_graph import (
    NodeStatus,
    PathScore,
    PathScorer,
    PlanOnGraphWalker,
    TargetNodeScorer,
    WalkPath,
    WalkResult,
)
from .reason_in_documents import (
    DenoisedDoc,
    ReasonInDocuments,
    compose_with_chain_of_note,
)
from .types import (
    Document,
    Edge,
    Graph,
    Node,
    SimpleDocument,
    SimpleEdge,
    SimpleGraph,
    SimpleNode,
)

__all__ = [
    "AnchorCandidate",
    "AnchorPredictor",
    "BeamCandidate",
    "BeamResult",
    "BeamRetriever",
    "BeamScorer",
    "CoverageScorer",
    "DecompositionCache",
    "DecompositionEntry",
    "DenoisedDoc",
    "Document",
    "Edge",
    "Embedder",
    "EntityExtractor",
    "FixedAnchorPredictor",
    "Graph",
    "HashEmbedder",
    "HippoRAGRetriever",
    "IRCoTOperator",
    "IRCoTResult",
    "IRCoTStep",
    "LLMTextGenerator",
    "Node",
    "NodeStatus",
    "PathScore",
    "PathScorer",
    "PersonalizedPageRank",
    "PlanOnGraphWalker",
    "ReasonInDocuments",
    "RetrievalResult",
    "Retriever",
    "RetrievedDoc",
    "SelfAskOperator",
    "SelfAskResult",
    "SelfAskStep",
    "SimpleDocument",
    "SimpleEdge",
    "SimpleGraph",
    "SimpleNode",
    "StubLLM",
    "StubRetriever",
    "TargetNodeScorer",
    "TitleEntityExtractor",
    "TokenOverlapAnchorPredictor",
    "WalkPath",
    "WalkResult",
    "compose_with_chain_of_note",
    "cosine",
    "graph_to_adjacency",
    "merge_predictors",
    "normalize_question",
    "parse_self_ask_response",
]
