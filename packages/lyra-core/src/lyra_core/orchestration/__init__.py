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
from lyra_core.orchestration.message_bus import InMemoryMessageBus, MessageBus
from lyra_core.orchestration.orchestrator import TeamOrchestrator
from lyra_core.orchestration.protocol import Message, MessageType
from lyra_core.orchestration.state_store import InMemoryStateStore, StateStore

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
]
