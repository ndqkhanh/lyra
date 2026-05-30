"""Topology subpackage — hierarchical swarms, dynamic reconfiguration, health monitoring."""

from lyra_agent_swarm.topology.hierarchical import (
    HierarchicalTopology,
    SquadRole,
    SquadTemplate,
    TopologyLevel,
    TopologyNode,
)
from lyra_agent_swarm.topology.dynamic_reconfig import (
    BanditMetrics,
    DynamicReconfig,
    ReconfigAction,
    ReconfigPlan,
    ReconfigTrigger,
)
from lyra_agent_swarm.topology.health_monitor import (
    AgentHealth,
    HealthMonitor,
    HealthProbe,
    HealthStatus,
)

__all__ = [
    # Hierarchical Topology
    "HierarchicalTopology",
    "SquadRole",
    "SquadTemplate",
    "TopologyLevel",
    "TopologyNode",
    # Dynamic Reconfiguration
    "BanditMetrics",
    "DynamicReconfig",
    "ReconfigAction",
    "ReconfigPlan",
    "ReconfigTrigger",
    # Health Monitor
    "AgentHealth",
    "HealthMonitor",
    "HealthProbe",
    "HealthStatus",
]
