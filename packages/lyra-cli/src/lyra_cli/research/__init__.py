"""
Multi-Hop Deep Research System for Lyra (US-011).

A multi-hop research engine inspired by the Code Researcher paper (Microsoft Research 2025).
Orchestrates deep exploration across multiple strategies, tracks exploration trajectories,
evaluates source credibility, builds knowledge graphs, and adaptively selects strategies.

Architecture:
    MultiHopResearchEngine   — Orchestrates exploration with 3 strategies
    ResearchTrajectory       — Records action-result pairs, exploration tree
    SourceCredibility        — Evaluates source trustworthiness
    ResearchKnowledgeGraph   — Semantic graph of findings with PPR
    StrategySelector         — UCB1 bandit for strategy selection
"""

from __future__ import annotations

from .research_engine import MultiHopResearchEngine, ExploreResult, ResearchReport
from .trajectory import (
    ResearchAction,
    ResearchResult,
    ResearchTrajectory,
    TrajectoryNode,
)
from .source_evaluator import (
    SourceCredibility,
    SourceProfile,
    SourceType,
    ContradictionReport,
)
from .knowledge_graph import (
    Finding,
    FindingRelation,
    ResearchKnowledgeGraph,
    KnowledgeGap,
)
from .strategy_selector import (
    StrategyResult,
    StrategySelector,
    StrategyType,
)

__all__ = [
    # Engine
    "MultiHopResearchEngine",
    "ExploreResult",
    "ResearchReport",
    # Trajectory
    "ResearchAction",
    "ResearchResult",
    "ResearchTrajectory",
    "TrajectoryNode",
    # Source evaluator
    "SourceCredibility",
    "SourceProfile",
    "SourceType",
    "ContradictionReport",
    # Knowledge graph
    "Finding",
    "FindingRelation",
    "ResearchKnowledgeGraph",
    "KnowledgeGap",
    # Strategy selector
    "StrategyResult",
    "StrategySelector",
    "StrategyType",
]

__version__ = "0.1.0"
