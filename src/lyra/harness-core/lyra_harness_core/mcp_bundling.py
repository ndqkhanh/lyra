"""Tiered MCP Server Bundling — P1-B3 (HIGH, MED).

Lifecycle-managed MCP server bundling with Tier-1 (always-on) and
Tier-2 (on-demand) classification. Servers are described by manifests,
grouped into bundles, and monitored for health.

See: plan-phase1-harness.md §4.3, awesome-mcp-servers
"""
from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Server Tier
# ---------------------------------------------------------------------------


class MCPTier(str, enum.Enum):
    """MCP server tier classification."""

    TIER_1 = "tier_1"  # Always loaded — core tools (filesystem, git, search)
    TIER_2 = "tier_2"  # On-demand — specialized tools (database, browser, etc.)


class MCPServerState(str, enum.Enum):
    """Runtime state of an MCP server."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    ERROR = "error"


class MCPServerHealth(str, enum.Enum):
    """Health status of an MCP server."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# MCP Server Manifest
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MCPServerManifest:
    """Static description of an MCP server."""

    name: str
    command: str              # executable or entry point
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    tier: MCPTier = MCPTier.TIER_2
    description: str = ""
    tools: list[str] = field(default_factory=list)  # tool names provided
    version: str = "0.0.0"
    startup_timeout_seconds: float = 30.0
    health_check_interval_seconds: float = 60.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "command": self.command,
            "args": self.args,
            "env": self.env,
            "tier": self.tier.value,
            "description": self.description,
            "tools": self.tools,
            "version": self.version,
            "startup_timeout_seconds": self.startup_timeout_seconds,
            "health_check_interval_seconds": self.health_check_interval_seconds,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Server Instance State
# ---------------------------------------------------------------------------


@dataclass
class MCPServerInstance:
    """Runtime state for a single MCP server."""

    manifest: MCPServerManifest
    state: MCPServerState = MCPServerState.STOPPED
    health: MCPServerHealth = MCPServerHealth.UNKNOWN
    pid: int | None = None
    started_at: float = 0.0
    last_health_check: float = 0.0
    error_message: str = ""
    restart_count: int = 0
    _process: Any = field(default=None, repr=False, init=False)

    @property
    def uptime_seconds(self) -> float:
        if self.state == MCPServerState.RUNNING and self.started_at > 0:
            return time.time() - self.started_at
        return 0.0

    @property
    def is_running(self) -> bool:
        return self.state == MCPServerState.RUNNING

    @property
    def is_degraded(self) -> bool:
        return self.health in (MCPServerHealth.DEGRADED, MCPServerHealth.UNHEALTHY)

    @property
    def tool_count(self) -> int:
        return len(self.manifest.tools)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.manifest.name,
            "state": self.state.value,
            "health": self.health.value,
            "pid": self.pid,
            "uptime_seconds": self.uptime_seconds,
            "restart_count": self.restart_count,
            "error": self.error_message,
        }


# ---------------------------------------------------------------------------
# Tiered Bundle
# ---------------------------------------------------------------------------


@dataclass
class TieredBundle:
    """A collection of MCP servers grouped by tier.

    Tier-1 servers are started first and must be healthy before
    Tier-2 servers are started.
    """

    tier_1: list[MCPServerInstance] = field(default_factory=list)
    tier_2: list[MCPServerInstance] = field(default_factory=list)

    @property
    def all_servers(self) -> list[MCPServerInstance]:
        return self.tier_1 + self.tier_2

    @property
    def running_servers(self) -> list[MCPServerInstance]:
        return [s for s in self.all_servers if s.is_running]

    @property
    def degraded_servers(self) -> list[MCPServerInstance]:
        return [s for s in self.all_servers if s.is_degraded]

    @property
    def total_tool_count(self) -> int:
        return sum(s.tool_count for s in self.all_servers)

    def servers_by_tier(self, tier: MCPTier) -> list[MCPServerInstance]:
        if tier == MCPTier.TIER_1:
            return list(self.tier_1)
        return list(self.tier_2)

    def get_server(self, name: str) -> MCPServerInstance | None:
        for s in self.all_servers:
            if s.manifest.name == name:
                return s
        return None

    def tools_by_tier(self, tier: MCPTier) -> list[str]:
        """List all tool names provided by servers in a given tier."""
        tools: list[str] = []
        for s in self.servers_by_tier(tier):
            tools.extend(s.manifest.tools)
        return tools

    def all_tools(self) -> dict[str, list[str]]:
        """Map server name → tools provided."""
        return {s.manifest.name: list(s.manifest.tools) for s in self.all_servers}

    def is_tier_healthy(self, tier: MCPTier) -> bool:
        """Check if all servers in a tier are healthy."""
        for s in self.servers_by_tier(tier):
            if s.health != MCPServerHealth.HEALTHY:
                return False
        return len(self.servers_by_tier(tier)) > 0

    @property
    def server_count(self) -> int:
        return len(self.all_servers)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier_1": [s.to_dict() for s in self.tier_1],
            "tier_2": [s.to_dict() for s in self.tier_2],
        }


# ---------------------------------------------------------------------------
# Lifecycle Manager
# ---------------------------------------------------------------------------


@dataclass
class MCPLifecycleManager:
    """Manages the lifecycle of MCP servers in a tiered bundle.

    Provides start/stop/restart with health monitoring and
    tier-dependent ordering (Tier-1 must be healthy before Tier-2 starts).
    """

    bundle: TieredBundle = field(default_factory=TieredBundle)
    _max_restarts: int = 3
    _restart_window_seconds: float = 300.0  # 5 minutes
    _restart_timestamps: dict[str, list[float]] = field(default_factory=dict)

    def register(self, manifest: MCPServerManifest) -> MCPServerInstance:
        """Register a new server manifest and create its instance."""
        instance = MCPServerInstance(manifest=manifest)
        if manifest.tier == MCPTier.TIER_1:
            self.bundle.tier_1.append(instance)
        else:
            self.bundle.tier_2.append(instance)
        return instance

    def unregister(self, name: str) -> bool:
        """Remove a server by name. Returns True if found and removed."""
        for tier_list in (self.bundle.tier_1, self.bundle.tier_2):
            for i, s in enumerate(tier_list):
                if s.manifest.name == name:
                    tier_list.pop(i)
                    return True
        return False

    def start(self, name: str) -> bool:
        """Mark a server as started (caller handles actual process launch).

        If already running, this is a no-op — health is preserved.
        """
        instance = self.bundle.get_server(name)
        if instance is None:
            return False
        if instance.state == MCPServerState.RUNNING:
            return True
        instance.state = MCPServerState.STARTING
        # Simulated start — real impl would launch the process
        instance.state = MCPServerState.RUNNING
        instance.health = MCPServerHealth.HEALTHY
        instance.started_at = time.time()
        instance.last_health_check = time.time()
        return True

    def stop(self, name: str) -> bool:
        """Mark a server as stopped."""
        instance = self.bundle.get_server(name)
        if instance is None:
            return False
        instance.state = MCPServerState.STOPPING
        instance.state = MCPServerState.STOPPED
        instance.health = MCPServerHealth.UNKNOWN
        return True

    def restart(self, name: str) -> bool:
        """Stop then start a server."""
        instance = self.bundle.get_server(name)
        if instance is None:
            return False

        # Check restart rate limit
        if not self._can_restart(name):
            instance.error_message = f"restart rate limit exceeded ({self._max_restarts} per {self._restart_window_seconds}s)"
            instance.state = MCPServerState.ERROR
            return False

        self._record_restart(name)
        self.stop(name)
        instance.restart_count += 1
        return self.start(name)

    def start_tier(self, tier: MCPTier) -> list[str]:
        """Start all servers in a tier. Returns names of successfully started servers."""
        started: list[str] = []
        for s in self.bundle.servers_by_tier(tier):
            if self.start(s.manifest.name):
                started.append(s.manifest.name)
        return started

    def stop_tier(self, tier: MCPTier) -> list[str]:
        """Stop all servers in a tier."""
        stopped: list[str] = []
        for s in self.bundle.servers_by_tier(tier):
            if self.stop(s.manifest.name):
                stopped.append(s.manifest.name)
        return stopped

    def start_all(self) -> dict[str, list[str]]:
        """Start all servers: Tier-1 first, then Tier-2 if Tier-1 is healthy.

        Returns {tier: [started server names]}.
        """
        result: dict[str, list[str]] = {"tier_1": [], "tier_2": []}

        result["tier_1"] = self.start_tier(MCPTier.TIER_1)

        if self.bundle.is_tier_healthy(MCPTier.TIER_1):
            result["tier_2"] = self.start_tier(MCPTier.TIER_2)

        return result

    def stop_all(self) -> int:
        """Stop all servers. Returns count of stopped servers."""
        count = 0
        for s in self.bundle.all_servers:
            if self.stop(s.manifest.name):
                count += 1
        return count

    def health_check(self, name: str) -> MCPServerHealth:
        """Run a health check on a server. Returns current health status.

        In a real implementation, this would ping the server's health endpoint.
        Here we assume running == healthy unless marked otherwise.
        """
        instance = self.bundle.get_server(name)
        if instance is None:
            return MCPServerHealth.UNKNOWN

        instance.last_health_check = time.time()

        if instance.state != MCPServerState.RUNNING:
            instance.health = MCPServerHealth.UNHEALTHY
        elif instance.error_message:
            instance.health = MCPServerHealth.DEGRADED
        else:
            instance.health = MCPServerHealth.HEALTHY

        return instance.health

    def health_check_all(self) -> dict[str, MCPServerHealth]:
        """Run health checks on all servers."""
        return {s.manifest.name: self.health_check(s.manifest.name) for s in self.bundle.all_servers}

    def mark_degraded(self, name: str, reason: str = "") -> None:
        """Mark a server as degraded (e.g., after a health check failure)."""
        instance = self.bundle.get_server(name)
        if instance:
            instance.health = MCPServerHealth.DEGRADED
            instance.error_message = reason

    def mark_unhealthy(self, name: str, reason: str = "") -> None:
        """Mark a server as unhealthy (without changing its runtime state)."""
        instance = self.bundle.get_server(name)
        if instance:
            instance.health = MCPServerHealth.UNHEALTHY
            instance.error_message = reason

    def get_server_info(self, name: str) -> dict[str, Any] | None:
        """Get combined manifest + runtime info for a server."""
        instance = self.bundle.get_server(name)
        if instance is None:
            return None
        return {
            **instance.manifest.to_dict(),
            **instance.to_dict(),
        }

    def get_tool_providers(self, tool_name: str) -> list[str]:
        """Find which servers provide a given tool."""
        providers: list[str] = []
        for s in self.bundle.all_servers:
            if tool_name in s.manifest.tools:
                providers.append(s.manifest.name)
        return providers

    def stats(self) -> dict[str, Any]:
        """Aggregate statistics for all managed servers."""
        total = len(self.bundle.all_servers)
        running = len(self.bundle.running_servers)
        degraded = len(self.bundle.degraded_servers)
        return {
            "total_servers": total,
            "tier_1_count": len(self.bundle.tier_1),
            "tier_2_count": len(self.bundle.tier_2),
            "running": running,
            "stopped": total - running,
            "degraded": degraded,
            "total_tools": self.bundle.total_tool_count,
            "tier_1_healthy": self.bundle.is_tier_healthy(MCPTier.TIER_1),
            "tier_2_healthy": self.bundle.is_tier_healthy(MCPTier.TIER_2),
        }

    # --- Internal -------------------------------------------------------------

    def _can_restart(self, name: str) -> bool:
        """Check if a server is within its restart rate limit."""
        timestamps = self._restart_timestamps.get(name, [])
        cutoff = time.time() - self._restart_window_seconds
        recent = [t for t in timestamps if t > cutoff]
        return len(recent) < self._max_restarts

    def _record_restart(self, name: str) -> None:
        """Record a restart event for rate limiting."""
        if name not in self._restart_timestamps:
            self._restart_timestamps[name] = []
        self._restart_timestamps[name].append(time.time())


# ---------------------------------------------------------------------------
# Pre-built Bundles
# ---------------------------------------------------------------------------


def build_default_tier1_manifests() -> list[MCPServerManifest]:
    """Default Tier-1 MCP servers (always loaded, core tools)."""
    return [
        MCPServerManifest(
            name="filesystem",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem"],
            tier=MCPTier.TIER_1,
            description="Filesystem access (read/write within allowed paths)",
            tools=["read_file", "write_file", "list_directory", "move_file", "search_files"],
            version="1.0.0",
        ),
        MCPServerManifest(
            name="git",
            command="npx",
            args=["-y", "@anthropic/mcp-server-git"],
            tier=MCPTier.TIER_1,
            description="Git operations (status, diff, log, commit)",
            tools=["git_status", "git_diff", "git_log", "git_commit", "git_branch"],
            version="1.0.0",
        ),
        MCPServerManifest(
            name="search",
            command="npx",
            args=["-y", "@anthropic/mcp-server-search"],
            tier=MCPTier.TIER_1,
            description="Code search and grep",
            tools=["grep", "glob", "find_files", "search_content"],
            version="1.0.0",
        ),
        MCPServerManifest(
            name="context",
            command="python",
            args=["-m", "lyra.mcp.context_server"],
            tier=MCPTier.TIER_1,
            description="Context window management (compaction, summarization)",
            tools=["compact_context", "summarize_context", "context_stats"],
            version="1.0.0",
        ),
    ]


def build_default_tier2_manifests() -> list[MCPServerManifest]:
    """Default Tier-2 MCP servers (on-demand, specialized)."""
    return [
        MCPServerManifest(
            name="database",
            command="npx",
            args=["-y", "@anthropic/mcp-server-postgres"],
            tier=MCPTier.TIER_2,
            description="Database query and schema inspection",
            tools=["db_query", "db_schema", "db_explain", "db_list_tables"],
            version="1.0.0",
        ),
        MCPServerManifest(
            name="browser",
            command="npx",
            args=["-y", "@anthropic/mcp-server-puppeteer"],
            tier=MCPTier.TIER_2,
            description="Headless browser for web interaction",
            tools=["browser_navigate", "browser_screenshot", "browser_click", "browser_fill"],
            version="1.0.0",
        ),
        MCPServerManifest(
            name="slack",
            command="npx",
            args=["-y", "@anthropic/mcp-server-slack"],
            tier=MCPTier.TIER_2,
            description="Slack messaging and channel management",
            tools=["slack_send", "slack_list_channels", "slack_search"],
            version="1.0.0",
        ),
        MCPServerManifest(
            name="memory",
            command="python",
            args=["-m", "lyra.mcp.memory_server"],
            tier=MCPTier.TIER_2,
            description="Long-term memory store (vector + graph)",
            tools=["memory_store", "memory_search", "memory_delete", "memory_summarize"],
            version="1.0.0",
        ),
    ]


def build_default_bundle() -> tuple[TieredBundle, MCPLifecycleManager]:
    """Build a default MCP bundle with all servers registered."""
    manager = MCPLifecycleManager()
    for manifest in build_default_tier1_manifests():
        manager.register(manifest)
    for manifest in build_default_tier2_manifests():
        manager.register(manifest)
    return manager.bundle, manager


__all__ = [
    "MCPLifecycleManager",
    "MCPServerHealth",
    "MCPServerInstance",
    "MCPServerManifest",
    "MCPServerState",
    "MCPTier",
    "TieredBundle",
    "build_default_bundle",
    "build_default_tier1_manifests",
    "build_default_tier2_manifests",
]
