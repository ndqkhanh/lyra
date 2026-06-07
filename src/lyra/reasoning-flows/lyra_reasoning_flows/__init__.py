"""lyra-reasoning-flows: Three-system reasoning with composable flow engineering.

Implements the SR2AM pattern (System I / System II / System III) with
MCTS-guided planning, ReAct loops, CoT/ToT integration, and full trace capture.
"""

from .cot_integration import CoTIntegrator, ReflexionStep, ThoughtNode, ThoughtStrategy
from .exceptions import (
    FlowCompositionError,
    HorizonEstimationError,
    MCTSSearchError,
    ReActLoopError,
    ReasoningError,
    TraceError,
)
from .flow_engine import FlowDefinition, FlowEngine, FlowPattern, FlowResult, FlowStep
from .mcts_planner import MCTSConfig, MCTSNode, MCTSPlanner, get_best_path, uct_score
from .planning_horizon import (
    HorizonConfig,
    HorizonMetrics,
    PlanningHorizonOptimizer,
)
from .react_loop import AuditResult, EnhancedReActLoop, ReActStep, ReActTrace
from .reasoning_tracer import FullTrace, ReasoningTracer, TraceEvent, TraceEventType
from .system_i import ReasoningTier, SystemIReasoner, TaskAssessment, TaskCategory
from .system_ii import BranchingFactor, CritiqueResult, PlanTree, SimulationResult, SystemIIReasoner
from .system_iii import (
    MetaDecision,
    MetaMetrics,
    RegulationAction,
    RegulationCost,
    SystemIIIMetaRegulator,
)

__version__ = "0.1.0"

__all__ = [
    # Exceptions
    "ReasoningError",
    "FlowCompositionError",
    "MCTSSearchError",
    "HorizonEstimationError",
    "ReActLoopError",
    "TraceError",
    # System I
    "SystemIReasoner",
    "TaskAssessment",
    "ReasoningTier",
    "TaskCategory",
    # System II
    "SystemIIReasoner",
    "BranchingFactor",
    "SimulationResult",
    "PlanTree",
    "CritiqueResult",
    # System III
    "SystemIIIMetaRegulator",
    "MetaDecision",
    "MetaMetrics",
    "RegulationAction",
    "RegulationCost",
    # Flow Engine
    "FlowEngine",
    "FlowDefinition",
    "FlowStep",
    "FlowResult",
    "FlowPattern",
    # MCTS Planner
    "MCTSPlanner",
    "MCTSNode",
    "MCTSConfig",
    "uct_score",
    "get_best_path",
    # Planning Horizon
    "PlanningHorizonOptimizer",
    "HorizonConfig",
    "HorizonMetrics",
    # ReAct Loop
    "EnhancedReActLoop",
    "ReActStep",
    "ReActTrace",
    "AuditResult",
    # CoT Integration
    "CoTIntegrator",
    "ThoughtNode",
    "ThoughtStrategy",
    "ReflexionStep",
    # Tracer
    "ReasoningTracer",
    "TraceEvent",
    "TraceEventType",
    "FullTrace",
]
