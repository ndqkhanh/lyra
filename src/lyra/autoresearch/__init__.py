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

from lyra.autoresearch.citations import (
    CitationVerifier,
    VerificationReport,
    VerifyStatus,
    verify_citations,
)
from lyra.autoresearch.debate import (
    DebatePanel,
    DebateRound,
    Perspective,
    run_debate,
)
from lyra.autoresearch.evolution import (
    EvolutionEngine,
    EvolutionStore,
    LessonCategory,
    LessonEntry,
    LessonSeverity,
    SkillSynthesizer,
)
from lyra.autoresearch.execution import (
    ExecutionStrategy,
    FailureType,
    SelfHealingExecutor,
    execute_with_healing,
)
from lyra.autoresearch.hitl import (
    GateOrchestrator,
    GatePoint,
    HITLMode,
    HITLPolicy,
    create_gate_config,
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
    "EvolutionEngine",
    "EvolutionStore",
    "LessonEntry",
    "LessonCategory",
    "LessonSeverity",
    "SkillSynthesizer",
    # HITL
    "HITLMode",
    "HITLPolicy",
    "GatePoint",
    "GateOrchestrator",
    "create_gate_config",
]
