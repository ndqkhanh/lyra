"""
Lyra Orchestration - Multi-agent orchestration system.

This package provides:
- Event bus for cross-module communication
- Agent coordinator for parallel execution
- Domain events for agent coordination
- Consensus protocol for agent decision-making
- Task queue for distributed work distribution
"""

from lyra_orchestration.coalition_coordinator import BidBasedScheduler, CoalitionAwareCoordinator
from lyra_orchestration.consensus import (
    ConsensusProtocol,
    Proposal,
    Vote,
    VoteChoice,
    VotingStrategy,
)
from lyra_orchestration.coordinator import AgentCoordinator, AgentStatus, AgentTask
from lyra_orchestration.event_bus import (
    AgentCompleted,
    AgentFailed,
    AgentStarted,
    Event,
    EventBus,
    EventPriority,
    ExploitAttempted,
    IntegrationSynced,
    MemoryIngested,
    ScanCompleted,
    Subscription,
    VulnerabilityDiscovered,
)
from lyra_orchestration.task_queue import Task, TaskPriority, TaskQueue, TaskStatus

__version__ = "0.1.0"

__all__ = [
    # Event Bus
    "EventBus",
    "Event",
    "EventPriority",
    "Subscription",
    # Domain Events
    "AgentStarted",
    "AgentCompleted",
    "AgentFailed",
    "ScanCompleted",
    "VulnerabilityDiscovered",
    "ExploitAttempted",
    "MemoryIngested",
    "IntegrationSynced",
    # Coordinator
    "AgentCoordinator",
    "AgentTask",
    "AgentStatus",
    # Consensus Protocol
    "ConsensusProtocol",
    "Proposal",
    "Vote",
    "VoteChoice",
    "VotingStrategy",
    # Task Queue
    "TaskQueue",
    "Task",
    "TaskPriority",
    "TaskStatus",
    # Coalition-aware coordination (Superorganism Plan)
    "CoalitionAwareCoordinator",
    "BidBasedScheduler",
]
