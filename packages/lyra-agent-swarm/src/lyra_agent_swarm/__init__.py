"""Lyra Agent Swarm — Multi-agent orchestration framework with discipline roles, Shapley-value team formation, sprint workflows, consensus building, and autonomous operation."""

from __future__ import annotations

from lyra_agent_swarm.discipline_agents import (
    AgentRegistry,
    AgentRole,
    Capability,
    DisciplineAgent,
    HEPHAESTUS,
    HERMES,
    LIBRARIAN,
    ORACLE,
    PROMETHEUS,
    SENTINEL,
    SISYPHUS,
)
from lyra_agent_swarm.dispatcher import (
    DispatchConfig,
    DispatchDecision,
    DispatchStrategy,
    Dispatcher,
    TaskPriority,
    TaskQueue,
    TaskTicket,
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
from lyra_agent_swarm.coalition_former import (
    AgentContribution,
    Coalition,
    CoalitionConfig,
    CoalitionFormer,
)
from lyra_agent_swarm.autopilot import (
    Autopilot,
    AutopilotConfig,
    AutopilotJob,
    AutopilotRun,
    RunStatus,
    Schedule,
)
from lyra_agent_swarm.team_messaging import (
    AgentMessage,
    MessagePriority,
    MessageThread,
    MessagingConfig,
    TeamMessaging,
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
from lyra_agent_swarm.swarm_visualizer import (
    AgentState,
    AgentStatus,
    SwarmMetrics,
    SwarmSnapshot,
    SwarmVisualizer,
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
]
