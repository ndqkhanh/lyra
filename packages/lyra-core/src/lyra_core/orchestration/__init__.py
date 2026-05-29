"""Lyra autonomous multi-agent team orchestration system.

This package provides the foundation for spawning and coordinating
specialized agent teams that collaborate through the complete SDLC.
"""

from lyra_core.orchestration.agent_base import (
    AgentMetadata,
    AgentRole,
    AgentStatus,
    BaseAgent,
)

# Phase C — Adversarial Convergence
from lyra_core.orchestration.convergence import (
    ConvergenceAttempt,
    ConvergenceConfig,
    ConvergenceLoop,
    ConvergencePhase,
    ConvergenceReport,
    GateResult,
)

# Phase C — Dynamic Workflow Engine
from lyra_core.orchestration.dynamic_workflow import (
    DynamicWorkflowEngine,
    StepKind,
    StepStatus,
    WorkflowContext,
    WorkflowStep,
)
from lyra_core.orchestration.hash_editor import (
    ContentAnchor,
    EditResult,
    EditStatus,
    HashAnchoredEdit,
    HashAnchoredEditor,
)
from lyra_core.orchestration.latent_bridge import (
    BridgeMetrics,
    ConsensusMethod,
    ConsensusResult,
    ConsensusSynthesizer,
    KnowledgeExchangeBus,
    KnowledgeFragment,
    LatentStateType,
    LatentVector,
    SharedLatentState,
)
from lyra_core.orchestration.message_bus import InMemoryMessageBus, MessageBus
from lyra_core.orchestration.model_router import (
    ModelRouter,
    ModelSlot,
    RoutingDecision,
    SlotConfig,
    SlotHealth,
    SlotHealthStatus,
)
from lyra_core.orchestration.orchestrator import TeamOrchestrator
from lyra_core.orchestration.protocol import Message, MessageType
from lyra_core.orchestration.quality_arbiter import (
    QualityArbiter,
    QualityDimension,
    QualityReport,
    QualityScore,
    QualityStatus,
)
from lyra_core.orchestration.state_store import InMemoryStateStore, StateStore
from lyra_core.orchestration.task_decomposer import (
    CoordinationStrategy,
    DecompositionResult,
    DependencyGraph,
    Subtask,
    SubtaskStatus,
    TaskDecomposer,
    TaskPriority,
)

__all__ = [
    # Protocol
    "Message",
    "MessageType",
    # Message Bus
    "MessageBus",
    "InMemoryMessageBus",
    # Agent Base
    "BaseAgent",
    "AgentRole",
    "AgentStatus",
    "AgentMetadata",
    # Orchestrator
    "TeamOrchestrator",
    # State Store
    "StateStore",
    "InMemoryStateStore",
    # Phase 2.1 — Task Decomposer
    "CoordinationStrategy",
    "DecompositionResult",
    "DependencyGraph",
    "Subtask",
    "SubtaskStatus",
    "TaskDecomposer",
    "TaskPriority",
    # Phase 2.2 — Model Router
    "ModelRouter",
    "ModelSlot",
    "RoutingDecision",
    "SlotConfig",
    "SlotHealth",
    "SlotHealthStatus",
    # Phase 2.3 — Latent Bridge
    "BridgeMetrics",
    "ConsensusMethod",
    "ConsensusResult",
    "ConsensusSynthesizer",
    "KnowledgeExchangeBus",
    "KnowledgeFragment",
    "LatentStateType",
    "LatentVector",
    "SharedLatentState",
    # Phase 2.4a — Hash Editor
    "ContentAnchor",
    "EditResult",
    "EditStatus",
    "HashAnchoredEdit",
    "HashAnchoredEditor",
    # Phase 2.4b — Quality Arbiter
    "QualityArbiter",
    "QualityDimension",
    "QualityReport",
    "QualityScore",
    "QualityStatus",
    # Phase C — Adversarial Convergence
    "ConvergenceAttempt",
    "ConvergenceConfig",
    "ConvergenceLoop",
    "ConvergencePhase",
    "ConvergenceReport",
    "GateResult",
    # Phase C — Dynamic Workflow Engine
    "DynamicWorkflowEngine",
    "StepKind",
    "StepStatus",
    "WorkflowContext",
    "WorkflowStep",
]
