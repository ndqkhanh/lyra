"""
Swarm module for Lyra - Agent Swarm & Fleet Management.

Implements:
- SwarmOrchestrator: task decomposition and parallel work distribution
- FleetManager: agent lifecycle, resource allocation, auto-scaling
- ParallelExecutor: work-stealing concurrent execution with asyncio
- AgentCommunication: message passing with pub/sub and shared state
- SwarmTopology: agent connection patterns (mesh, star, ring, DAG)
- ConsensusProtocol: Raft-like leader election and Byzantine fault detection
"""

from lyra_cli.swarm.communication import (
    AgentCommunication,
    CommunicationConfig,
    Message,
    MessageType,
    SharedStateEntry,
)
from lyra_cli.swarm.consensus import (
    ConsensusConfig,
    ConsensusProtocol,
    ConsensusRole,
    LogEntry,
    NodeState,
)
from lyra_cli.swarm.fleet_manager import (
    AgentInstance,
    AgentStatus,
    FleetConfig,
    FleetManager,
    ResourceProfile,
)
from lyra_cli.swarm.orchestrator import (
    OrchestratorConfig,
    PriorityLevel,
    SwarmOrchestrator,
    SwarmTask,
    TaskResult,
)
from lyra_cli.swarm.parallel_executor import (
    ExecutorConfig,
    ParallelExecutor,
    WorkItem,
    WorkResult,
)
from lyra_cli.swarm.topology import (
    RoutingEntry,
    SwarmTopology,
    TopologyConfig,
    TopologyNode,
    TopologyType,
)

__all__ = [
    # Orchestrator
    "PriorityLevel",
    "SwarmTask",
    "TaskResult",
    "SwarmOrchestrator",
    "OrchestratorConfig",
    # Fleet Manager
    "AgentStatus",
    "AgentInstance",
    "ResourceProfile",
    "FleetConfig",
    "FleetManager",
    # Parallel Executor
    "ExecutorConfig",
    "WorkItem",
    "WorkResult",
    "ParallelExecutor",
    # Communication
    "Message",
    "MessageType",
    "SharedStateEntry",
    "CommunicationConfig",
    "AgentCommunication",
    # Topology
    "TopologyType",
    "TopologyNode",
    "RoutingEntry",
    "TopologyConfig",
    "SwarmTopology",
    # Consensus
    "NodeState",
    "ConsensusRole",
    "LogEntry",
    "ConsensusConfig",
    "ConsensusProtocol",
]
