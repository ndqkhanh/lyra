"""
Lyra Orchestration - Multi-agent orchestration system.

This package provides:
- Event bus for cross-module communication
- Agent coordinator for parallel execution
- Domain events for agent coordination
"""

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
]
