"""
Supervisor — Persistent background daemon for managing agent sessions.

Tracks session state, enforces idle timeouts, persists state to SQLite,
and provides a fleet-view of all sessions. Includes health dashboard
metrics, cheap model summaries, auto-restart with exponential backoff,
confidence circuit breaker, interactive fleet TUI, shell commands,
and MCTS-driven topology search.
"""

from lyra.supervisor.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitState,
    ConfidenceCircuitBreaker,
    LoopHealth,
    TripAction,
)
from lyra.supervisor.daemon import DaemonHealth, SessionSummary, SupervisorDaemon
from lyra.supervisor.fleet_tui import FleetTUI, FleetTUIConfig
from lyra.supervisor.shell_commands import (
    cmd_fleet_kill,
    cmd_fleet_list,
    cmd_fleet_logs,
    cmd_fleet_start,
    cmd_fleet_status,
    cmd_fleet_stop,
    cmd_fleet_top,
)
from lyra.supervisor.state import ProcessState, SessionInfo, SessionState
from lyra.supervisor.topology_search import (
    AgentRole,
    MCTSConfig,
    Topology,
    TopologyNode,
    TopologySearcher,
    TopologyTemplate,
)

__all__ = [
    "DaemonHealth",
    "SessionSummary",
    "SupervisorDaemon",
    "ProcessState",
    "SessionState",
    "SessionInfo",
    # Circuit breaker
    "CircuitBreakerConfig",
    "CircuitState",
    "ConfidenceCircuitBreaker",
    "LoopHealth",
    "TripAction",
    # Fleet TUI
    "FleetTUI",
    "FleetTUIConfig",
    # Shell commands
    "cmd_fleet_start",
    "cmd_fleet_stop",
    "cmd_fleet_status",
    "cmd_fleet_kill",
    "cmd_fleet_logs",
    "cmd_fleet_top",
    "cmd_fleet_list",
    # Topology search
    "AgentRole",
    "MCTSConfig",
    "Topology",
    "TopologyNode",
    "TopologySearcher",
    "TopologyTemplate",
]
