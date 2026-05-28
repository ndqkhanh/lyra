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

from lyra_cli.swarm.orchestrator import (
    PriorityLevel,
    SwarmTask,
    TaskResult,
    SwarmOrchestrator,
    OrchestratorConfig,
)

from lyra_cli.swarm.fleet_manager import (
    AgentStatus,
    AgentInstance,
    ResourceProfile,
    FleetConfig,
    FleetManager,
)

from lyra_cli.swarm.parallel_executor import (
    ExecutorConfig,
    WorkItem,
    WorkResult,
    ParallelExecutor,
)

from lyra_cli.swarm.communication import (
    Message,
    MessageType,
    SharedStateEntry,
    CommunicationConfig,
    AgentCommunication,
)

from lyra_cli.swarm.topology import (
    TopologyType,
    TopologyNode,
    RoutingEntry,
    TopologyConfig,
    SwarmTopology,
)

from lyra_cli.swarm.consensus import (
    NodeState,
    ConsensusRole,
    LogEntry,
    ConsensusConfig,
    ConsensusProtocol,
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
