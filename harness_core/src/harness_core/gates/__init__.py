"""harness_core.gates — quality gates that fail closed.

Per [docs/199-multi-hop-reasoning-techniques-arc.md](../../../../../../research/harness-engineering/docs/199-multi-hop-reasoning-techniques-arc.md)
Phase 3 (Chain-of-Note), [docs/202-multi-agent-multi-hop-reckoning-2026.md]
(../../../../../../research/harness-engineering/docs/202-multi-agent-multi-hop-reckoning-2026.md) §4 (architectural
value of gates), and [docs/172-polaris-2026-deep-research-roadmap.md]
(../../../../../../research/harness-engineering/docs/172-polaris-2026-deep-research-roadmap.md) §3 Gap 5
(two-axis evidence gates).

A gate is a typed, deterministic predicate run between retrieval and reasoning
(or between reasoning and action). Gates fail *closed* — when a gate cannot
determine, the safer path is to drop the candidate.
"""
from __future__ import annotations

from .chain_of_note import (
    ChainOfNoteGate,
    DocVerdict,
    NoteVerdict,
    ScoredDoc,
)
from .dual_use import (
    DualUseClassifier,
    DualUseGate,
    DualUseVerdict,
    GateAction,
    GateDecision,
    KeywordRiskClassifier,
    RiskLevel,
)
from .kg_fact import (
    FactClaim,
    KGFactGate,
    KGFactVerdict,
    KGSource,
    KGSourceProtocol,
    StaticKGSource,
)
from .retraction import (
    RetractionGate,
    RetractionIndex,
    RetractionRecord,
    RetractionVerdict,
    StaticRetractionIndex,
)

__all__ = [
    "ChainOfNoteGate",
    "DocVerdict",
    "DualUseClassifier",
    "DualUseGate",
    "DualUseVerdict",
    "FactClaim",
    "GateAction",
    "GateDecision",
    "KGFactGate",
    "KGFactVerdict",
    "KGSource",
    "KGSourceProtocol",
    "KeywordRiskClassifier",
    "NoteVerdict",
    "RetractionGate",
    "RetractionIndex",
    "RetractionRecord",
    "RetractionVerdict",
    "RiskLevel",
    "ScoredDoc",
    "StaticKGSource",
    "StaticRetractionIndex",
]
