"""Lyra Agent Swarm — Multi-agent orchestration framework with discipline roles, Shapley-value team
formation, sprint workflows, consensus building, and autonomous operation."""

from __future__ import annotations

from lyra_agent_swarm.autopilot import (
    Autopilot,
    AutopilotConfig,
    AutopilotJob,
    AutopilotRun,
    RunStatus,
    Schedule,
)
from lyra_agent_swarm.coalition_former import (
    AgentContribution,
    Coalition,
    CoalitionConfig,
    CoalitionFormer,
)

# ── Compound Agent (Plan 33) ────────────────────────────────────
from lyra_agent_swarm.compound_agent import (
    CompoundAgent,
    CompoundConfig,
    CompoundResult,
    SlotConfig,
    SlotOutput,
    SlotRole,
)

# ── Consensus (Raft) ─────────────────────────────────────────────
from lyra_agent_swarm.consensus.raft_consensus import (
    LogEntry,
    NodeState,
    RaftConfig,
    RaftNode,
)
from lyra_agent_swarm.consensus_builder import (
    AggregationMethod,
    ConsensusBuilder,
    ConsensusConfig,
    ConsensusResult,
    Proposal,
    Vote,
    VoteChoice,
)
from lyra_agent_swarm.continuous_guard import (
    DESTRUCTIVE_PATTERNS,
    MAX_CONSECUTIVE_FAILURES,
    MAX_COST_PER_HOUR_USD,
    MAX_FILES_PER_HOUR,
    MAX_OPERATIONS_PER_MINUTE,
    SAFETY_RULES,
    ContinuousGuard,
    GuardAction,
    GuardReason,
    GuardState,
    GuardVerdict,
    OperationRecord,
    create_default_guard,
    create_lenient_guard,
    create_strict_guard,
)
from lyra_agent_swarm.discipline_agents import (
    HEPHAESTUS,
    HERMES,
    LIBRARIAN,
    ORACLE,
    PROMETHEUS,
    SENTINEL,
    SISYPHUS,
    AgentRegistry,
    AgentRole,
    Capability,
    DisciplineAgent,
)
from lyra_agent_swarm.dispatcher import (
    DispatchConfig,
    DispatchDecision,
    Dispatcher,
    DispatchStrategy,
    TaskPriority,
    TaskQueue,
    TaskTicket,
)
from lyra_agent_swarm.fleet_orchestrator import (
    ExecutionPattern,
    FanOutBatch,
    Fleet,
    FleetMetrics,
    FleetOrchestrator,
    FleetStatus,
    MapReduceResult,
    TaskItem,
    TaskItemStatus,
    chunk_items,
    estimate_fleet_cost,
)
from lyra_agent_swarm.goal_system import (
    GOAL_TEMPLATES,
    Goal,
    GoalAgentType,
    GoalCriteria,
    GoalEvent,
    GoalManager,
    GoalMetrics,
    GoalPriority,
    GoalStatus,
)

# ── RecursiveLink Latent Communication (Plan 13) ───────────────
from lyra_agent_swarm.recursive_link import (
    LatentMessage,
    LatentState,
    LinkContext,
    LinkMode,
    LinkStatus,
    RecursiveLink,
)
from lyra_agent_swarm.sprint_model import (
    Sprint,
    SprintConfig,
    SprintModel,
    SprintPhase,
    SprintResult,
    SprintStatus,
    SprintTask,
)
from lyra_agent_swarm.squad_manager import (
    Squad,
    SquadDomain,
    SquadManager,
    SquadMetrics,
)
from lyra_agent_swarm.swarm_visualizer import (
    AgentState,
    AgentStatus,
    SwarmMetrics,
    SwarmSnapshot,
    SwarmVisualizer,
)
from lyra_agent_swarm.team_messaging import (
    AgentMessage,
    MessagePriority,
    MessageThread,
    MessagingConfig,
    TeamMessaging,
)

# ── Zero-Trust Federation (Plan 33) ─────────────────────────────
from lyra_agent_swarm.zero_trust_federation import (
    AuthDecision,
    AuthStatus,
    FederationConfig,
    FederationIdentity,
    FederationLevel,
    FederationRegistry,
    ZeroTrustFederation,
)
from lyra_agent_swarm.zero_trust_federation import (
    Capability as FederationCapability,
)

__all__ = [
    # discipline_agents
    "AgentRole",
    "Capability",
    "DisciplineAgent",
    "AgentRegistry",
    "SISYPHUS",
    "HEPHAESTUS",
    "PROMETHEUS",
    "ORACLE",
    "LIBRARIAN",
    "SENTINEL",
    "HERMES",
    # dispatcher
    "TaskPriority",
    "DispatchStrategy",
    "TaskTicket",
    "DispatchConfig",
    "DispatchDecision",
    "TaskQueue",
    "Dispatcher",
    # sprint_model
    "SprintPhase",
    "SprintStatus",
    "Sprint",
    "SprintTask",
    "SprintResult",
    "SprintConfig",
    "SprintModel",
    # squad_manager
    "SquadDomain",
    "Squad",
    "SquadMetrics",
    "SquadManager",
    # coalition_former
    "AgentContribution",
    "Coalition",
    "CoalitionConfig",
    "CoalitionFormer",
    # autopilot
    "Schedule",
    "RunStatus",
    "AutopilotJob",
    "AutopilotConfig",
    "AutopilotRun",
    "Autopilot",
    # team_messaging
    "MessagePriority",
    "AgentMessage",
    "MessageThread",
    "MessagingConfig",
    "TeamMessaging",
    # consensus_builder
    "VoteChoice",
    "AggregationMethod",
    "Proposal",
    "Vote",
    "ConsensusResult",
    "ConsensusConfig",
    "ConsensusBuilder",
    # swarm_visualizer
    "AgentState",
    "AgentStatus",
    "SwarmSnapshot",
    "SwarmMetrics",
    "SwarmVisualizer",
    # goal_system
    "GOAL_TEMPLATES",
    "Goal",
    "GoalAgentType",
    "GoalCriteria",
    "GoalEvent",
    "GoalManager",
    "GoalMetrics",
    "GoalPriority",
    "GoalStatus",
    # continuous_guard
    "DESTRUCTIVE_PATTERNS",
    "MAX_CONSECUTIVE_FAILURES",
    "MAX_COST_PER_HOUR_USD",
    "MAX_FILES_PER_HOUR",
    "MAX_OPERATIONS_PER_MINUTE",
    "SAFETY_RULES",
    "ContinuousGuard",
    "GuardAction",
    "GuardReason",
    "GuardState",
    "GuardVerdict",
    "OperationRecord",
    "create_default_guard",
    "create_lenient_guard",
    "create_strict_guard",
    # fleet_orchestrator
    "ExecutionPattern",
    "FanOutBatch",
    "Fleet",
    "FleetMetrics",
    "FleetOrchestrator",
    "FleetStatus",
    "MapReduceResult",
    "TaskItem",
    "TaskItemStatus",
    "chunk_items",
    "estimate_fleet_cost",
    # compound_agent (Plan 33)
    "CompoundAgent",
    "CompoundConfig",
    "CompoundResult",
    "SlotConfig",
    "SlotOutput",
    "SlotRole",
    # zero_trust_federation (Plan 33)
    "AuthDecision",
    "AuthStatus",
    "FederationCapability",
    "FederationConfig",
    "FederationIdentity",
    "FederationLevel",
    "FederationRegistry",
    "ZeroTrustFederation",
    # recursive_link (Plan 13)
    "LatentMessage",
    "LatentState",
    "LinkContext",
    "LinkMode",
    "LinkStatus",
    "RecursiveLink",
    # consensus (raft)
    "LogEntry",
    "NodeState",
    "RaftConfig",
    "RaftNode",
]
