"""5 Specialized Roles for Lyra Research (Phase 2 Week 5).

Implements autocontext-inspired role-based orchestration:
- Discovery: Multi-source parallel discovery
- Analysis: Quality and relevance analysis
- Synthesis: Cross-source synthesis and report generation
- Review: Adversarial review with heterogeneous model
- Curator: Knowledge curation and quality control
"""

from lyra_research.roles.role_base import Role, RoleResult, RoleStatus
from lyra_research.roles.discovery_role import DiscoveryRole, DiscoveryResult
from lyra_research.roles.analysis_role import AnalysisRole, AnalysisResult
from lyra_research.roles.synthesis_role import SynthesisRole, SynthesisResult
from lyra_research.roles.review_role import ReviewRole, ReviewResult, ReviewIssue
from lyra_research.roles.curator_role import CuratorRole, CurationResult, KnowledgeEntry
from lyra_research.roles.role_orchestrator import RoleOrchestrator, PipelineResult

__all__ = [
    "Role",
    "RoleResult",
    "RoleStatus",
    "DiscoveryRole",
    "DiscoveryResult",
    "AnalysisRole",
    "AnalysisResult",
    "SynthesisRole",
    "SynthesisResult",
    "ReviewRole",
    "ReviewResult",
    "ReviewIssue",
    "CuratorRole",
    "CurationResult",
    "KnowledgeEntry",
    "RoleOrchestrator",
    "PipelineResult",
]
