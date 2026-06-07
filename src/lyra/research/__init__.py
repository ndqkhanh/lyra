"""
Research subsystem — Deep Research Pipeline (P6) and DeepScientist
Auto-Research Pipeline (P7).

P6 (pipeline.py):     query analysis, parallel search, content extraction,
                      workspace report synthesis (via S4), citation verification.

P7 (deep_research.):  DeepScientist-style 3-stage pipeline with FindingsMemory,
                      quest management, UCB acquisition, and auto-paper generation.
"""

from lyra.research.pipeline import (
    SearchResult,
    Citation,
    ResearchReport,
    DeepResearchPipeline as P6DeepResearchPipeline,
)

from lyra.research.findings_memory import (
    FindingRecord,
    FindingsMemory,
    FindingStage,
    ValuationScores,
)

from lyra.research.deep_research_pipeline import (
    DeepResearchPipeline,
    QuestManager,
    QuestConfig,
    ReviewerScore,
    ReviewerDimension,
)

# v8.2 Research Advanced Features
from lyra.research.evidence_graph import (
    EvidenceGraph,
    EvidenceNode,
    EvidenceEdge,
    EdgeType,
    VerificationResult,
    VerificationStatus,
    GraphQuery,
    ContradictionPair,
)

from lyra.research.adversarial_verification import (
    AdversarialVerificationLoop,
    Verdict,
    PanelVerdict,
    AgentRole,
    ConfidenceBracket,
)

from lyra.research.skill_extractor import (
    SkillExtractor,
    SkillTemplate,
)

__all__ = [
    # P6
    "SearchResult",
    "Citation",
    "ResearchReport",
    "P6DeepResearchPipeline",
    # P7
    "DeepResearchPipeline",
    "QuestManager",
    "QuestConfig",
    "ReviewerScore",
    "ReviewerDimension",
    "FindingRecord",
    "FindingsMemory",
    "FindingStage",
    "ValuationScores",
    # v8.2 Research Advanced Features
    "EvidenceGraph",
    "EvidenceNode",
    "EvidenceEdge",
    "EdgeType",
    "VerificationResult",
    "VerificationStatus",
    "GraphQuery",
    "ContradictionPair",
    "AdversarialVerificationLoop",
    "Verdict",
    "PanelVerdict",
    "AgentRole",
    "ConfidenceBracket",
    "SkillExtractor",
    "SkillTemplate",
]
