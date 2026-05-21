"""
Lyra AutoResearch - AutoResearchClaw Integration

Complete implementation of AutoResearchClaw features for Lyra:
- 4-layer citation verification system
- Self-healing execution with Pivot/Refine loops
- Multi-agent structured debates
- Cross-run evolution and learning
- 7-mode human-in-the-loop collaboration

Based on: AutoResearchClaw (arXiv:2605.20025)
"""

__version__ = "1.0.0"

from lyra_autoresearch.citations import (
    CitationVerifier,
    VerifyStatus,
    VerificationReport,
    verify_citations,
)
from lyra_autoresearch.debate import (
    DebatePanel,
    Perspective,
    DebateRound,
    run_debate,
)
from lyra_autoresearch.execution import (
    SelfHealingExecutor,
    FailureType,
    ExecutionStrategy,
    execute_with_healing,
)
from lyra_autoresearch.evolution import (
    EvolutionStore,
    LessonEntry,
    LessonCategory,
    SkillSynthesizer,
)
from lyra_autoresearch.hitl import (
    HITLPolicy,
    GatePoint,
    GateOrchestrator,
)

__all__ = [
    # Citations
    "CitationVerifier",
    "VerifyStatus",
    "VerificationReport",
    "verify_citations",
    # Debate
    "DebatePanel",
    "Perspective",
    "DebateRound",
    "run_debate",
    # Execution
    "SelfHealingExecutor",
    "FailureType",
    "ExecutionStrategy",
    "execute_with_healing",
    # Evolution
    "EvolutionStore",
    "LessonEntry",
    "LessonCategory",
    "SkillSynthesizer",
    # HITL
    "HITLPolicy",
    "GatePoint",
    "GateOrchestrator",
]
