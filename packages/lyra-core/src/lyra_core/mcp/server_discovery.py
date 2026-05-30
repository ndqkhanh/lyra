"""MCP Server Discovery — Auto-discovers MCP servers from config files and env.

Scans standard config locations (.mcp.json, ~/.claude.json, env vars)
and registers discovered servers with the MCP registry. Includes periodic
health checking to mark unhealthy servers.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lyra_core.mcp import MCPRegistry


class DiscoverySource(StrEnum):
    """Where a server was discovered from."""

    MCP_JSON = ".mcp.json"
    CLAUDE_JSON = "~/.claude.json"
    ENV_VAR = "env:MCP_SERVERS"
    WELL_KNOWN = "well_known"
    MANUAL = "manual"


class HealthStatus(StrEnum):
    """Health status of a discovered server."""

    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True)
class DiscoveredServer:
    """Metadata about a discovered MCP server."""

    name: str
    url: str
    source: DiscoverySource
    source_path: str = ""
    health: HealthStatus = HealthStatus.UNKNOWN
    last_health_check: float = 0.0
    health_failures: int = 0
    tools_available: int = 0
    tags: tuple[str, ...] = ()


@dataclass
class DiscoveryResult:
    """Result of a discovery scan."""

    servers_found: int
    servers_added: int
    servers_updated: int
    source: DiscoverySource
    errors: list[str] = field(default_factory=list)
    discovered: list[DiscoveredServer] = field(default_factory=list)


class ServerDiscovery:
    """Auto-discovers MCP servers from config files and environment.

    Scans standard locations for MCP server definitions and registers
    them with the central MCP registry. Runs periodic health checks
    to detect unhealthy servers.

    Config formats supported:
    - ``.mcp.json`` — project-local MCP config
    - ``~/.claude.json`` — user-level Claude config (``mcpServers`` key)
    - ``MCP_SERVERS`` env var — JSON array of server definitions
    - Well-known paths in ``~/.lyra/mcp/``
    """

    def __init__(
        self,
        registry: MCPRegistry,
        health_check_interval: float = 30.0,
        health_check_timeout: float = 5.0,
        max_health_failures: int = 3,
    ) -> None:
        self._registry = registry
        self.health_check_interval = health_check_interval
        self.health_check_timeout = health_check_timeout
        self.max_health_failures = max_health_failures
        self._discovered: dict[str, DiscoveredServer] = {}
        self._discovery_history: list[DiscoveryResult] = []

    # ── Discovery ─────────────────────────────────────────────────

    def discover_all(self) -> list[DiscoveryResult]:
        """Run all discovery sources and register servers.

        Returns a list of DiscoveryResult, one per source scanned.
        """
        results: list[DiscoveryResult] = []

        for source, discover_fn in [
            (DiscoverySource.MCP_JSON, self._discover_from_mcp_json),
            (DiscoverySource.CLAUDE_JSON, self._discover_from_claude_json),
            (DiscoverySource.ENV_VAR, self._discover_from_env),
            (DiscoverySource.WELL_KNOWN, self._discover_from_well_known),
        ]:
            result = discover_fn()
            results.append(result)
            self._discovery_history.append(result)

        return results

    def discover_from_source(self, source: DiscoverySource) -> DiscoveryResult:
        """Run discovery from a single source."""
        discover_fns = {
            DiscoverySource.MCP_JSON: self._discover_from_mcp_json,
            DiscoverySource.CLAUDE_JSON: self._discover_from_claude_json,
            DiscoverySource.ENV_VAR: self._discover_from_env,
            DiscoverySource.WELL_KNOWN: self._discover_from_well_known,
        }
        fn = discover_fns.get(source)
        if fn is None:
            result = DiscoveryResult(
                servers_found=0,
                servers_added=0,
                servers_updated=0,
                source=source,
                errors=[f"Unknown discovery source: {source}"],
            )
            self._discovery_history.append(result)
            return result

        result = fn()
        self._discovery_history.append(result)
        return result

    # ── Health Checks ─────────────────────────────────────────────

    def run_health_checks(self) -> dict[str, HealthStatus]:
        """Run health checks on all discovered servers.

        Returns a dict of server name -> HealthStatus.
        """
        results: dict[str, HealthStatus] = {}
        for name, discovered in list(self._discovered.items()):
            status = self._check_health(discovered)
            results[name] = status

            updated = DiscoveredServer(
                name=discovered.name,
                url=discovered.url,
                source=discovered.source,
                source_path=discovered.source_path,
                health=status,
                last_health_check=time.monotonic(),
                health_failures=(
                    discovered.health_failures + 1
                    if status == HealthStatus.UNHEALTHY
                    else 0
                ),
                tools_available=discovered.tools_available,
                tags=discovered.tags,
            )
            self._discovered[name] = updated
        return results

    def should_health_check(self) -> bool:
        """Check if enough time has elapsed since the last health check cycle."""
        if not self._discovered:
            return False
        oldest = min(
            d.last_health_check for d in self._discovered.values()
        )
        return (time.monotonic() - oldest) >= self.health_check_interval

    def get_unhealthy_servers(self) -> list[DiscoveredServer]:
        """Return all servers currently marked unhealthy."""
        return [
            d for d in self._discovered.values()
            if d.health == HealthStatus.UNHEALTHY
        ]

    # ── Accessors ─────────────────────────────────────────────────

    def get_discovered(self, name: str) -> DiscoveredServer | None:
        """Get discovery metadata for a server by name."""
        return self._discovered.get(name)

    def list_discovered(self) -> list[DiscoveredServer]:
        """List all discovered servers with their metadata."""
        return list(self._discovered.values())

    def get_discovery_history(self) -> list[DiscoveryResult]:
        """Return the history of discovery scans."""
        return list(self._discovery_history)

    @property
    def discovered_count(self) -> int:
        return len(self._discovered)

    def clear(self) -> None:
        """Clear all discovery state."""
        self._discovered.clear()
        self._discovery_history.clear()

    # ── Private: Source-specific discovery ─────────────────────────

    def _discover_from_mcp_json(self) -> DiscoveryResult:
        """Discover servers from .mcp.json in current and parent directories."""
        source = DiscoverySource.MCP_JSON
        errors: list[str] = []
        found: list[DiscoveredServer] = []
        added = 0
        updated = 0

        for config_path in self._find_config_files(".mcp.json"):
            try:
                with open(config_path) as f:
                    config = json.load(f)
                servers = config.get("mcpServers", {})
                for name, server_def in servers.items():
                    url = self._extract_url(server_def)
                    if url:
                        ds = self._register_discovered(
                            name, url, source, str(config_path)
                        )
                        found.append(ds)
                        action = self._upsert_registry(name, url)
                        if action == "added":
                            added += 1
                        elif action == "updated":
                            updated += 1
            except (json.JSONDecodeError, OSError) as e:
                errors.append(f"{config_path}: {e}")

        return DiscoveryResult(
            servers_found=len(found),
            servers_added=added,
            servers_updated=updated,
            source=source,
            errors=errors,
            discovered=found,
        )

    def _discover_from_claude_json(self) -> DiscoveryResult:
        """Discover servers from ~/.claude.json mcpServers key."""
        source = DiscoverySource.CLAUDE_JSON
        errors: list[str] = []
        found: list[DiscoveredServer] = []
        added = 0
        updated = 0

        claude_config = Path.home() / ".claude.json"
        if not claude_config.exists():
            return DiscoveryResult(0, 0, 0, source, discovered=[])

        try:
            with open(claude_config) as f:
                config = json.load(f)
            servers = config.get("mcpServers", {})
            for name, server_def in servers.items():
                url = self._extract_url(server_def)
                if url:
                    ds = self._register_discovered(
                        name, url, source, str(claude_config)
                    )
                    found.append(ds)
                    action = self._upsert_registry(name, url)
                    if action == "added":
                        added += 1
                    elif action == "updated":
                        updated += 1
        except (json.JSONDecodeError, OSError) as e:
            errors.append(f"~/.claude.json: {e}")

        return DiscoveryResult(
            servers_found=len(found),
            servers_added=added,
            servers_updated=updated,
            source=source,
            errors=errors,
            discovered=found,
        )

    def _discover_from_env(self) -> DiscoveryResult:
        """Discover servers from MCP_SERVERS environment variable."""
        source = DiscoverySource.ENV_VAR
        errors: list[str] = []
        found: list[DiscoveredServer] = []
        added = 0
        updated = 0

        env_val = os.environ.get("MCP_SERVERS", "")
        if not env_val:
            return DiscoveryResult(0, 0, 0, source, discovered=[])

        try:
            servers = json.loads(env_val)
            if not isinstance(servers, list):
                servers = [servers]

            for item in servers:
                if isinstance(item, str):
                    # Simple URL format: "server-name:url"
                    if ":" in item:
                        name, url = item.split(":", 1)
                    else:
                        name = item
                        url = item
                elif isinstance(item, dict):
                    name = item.get("name", item.get("url", "unknown"))
                    url = item.get("url", item.get("command", ""))
                else:
                    continue

                ds = self._register_discovered(name, url, source, "env:MCP_SERVERS")
                found.append(ds)
                action = self._upsert_registry(name, url)
                if action == "added":
                    added += 1
                elif action == "updated":
                    updated += 1
        except (json.JSONDecodeError, ValueError) as e:
            errors.append(f"MCP_SERVERS env: {e}")

        return DiscoveryResult(
            servers_found=len(found),
            servers_added=added,
            servers_updated=updated,
            source=source,
            errors=errors,
            discovered=found,
        )

    def _discover_from_well_known(self) -> DiscoveryResult:
        """Discover servers from ~/.lyra/mcp/ well-known directory."""
        source = DiscoverySource.WELL_KNOWN
        errors: list[str] = []
        found: list[DiscoveredServer] = []
        added = 0
        updated = 0

        well_known = Path.home() / ".lyra" / "mcp"
        if not well_known.is_dir():
            return DiscoveryResult(0, 0, 0, source, discovered=[])

        for config_file in sorted(well_known.glob("*.json")):
            try:
                with open(config_file) as f:
                    config = json.load(f)

                name = config.get("name", config_file.stem)
                url = self._extract_url(config)
                if url:
                    ds = self._register_discovered(
                        name, url, source, str(config_file)
                    )
                    found.append(ds)
                    action = self._upsert_registry(name, url)
                    if action == "added":
                        added += 1
                    elif action == "updated":
                        updated += 1
            except (json.JSONDecodeError, OSError) as e:
                errors.append(f"{config_file}: {e}")

        return DiscoveryResult(
            servers_found=len(found),
            servers_added=added,
            servers_updated=updated,
            source=source,
            errors=errors,
            discovered=found,
        )

    # ── Private: Helpers ───────────────────────────────────────────

    @staticmethod
    def _find_config_files(filename: str) -> list[Path]:
        """Walk up from CWD to find all instances of a config file."""
        paths: list[Path] = []
        current = Path.cwd()
        while True:
            candidate = current / filename
            if candidate.exists():
                paths.append(candidate)
            parent = current.parent
            if parent == current:
                break
            current = parent
        return paths

    @staticmethod
    def _extract_url(server_def: dict | str) -> str:
        """Extract a URL from various server definition formats."""
        if isinstance(server_def, str):
            return server_def
        if isinstance(server_def, dict):
            return server_def.get("url", server_def.get("command", ""))
        return ""

    def _register_discovered(
        self, name: str, url: str, source: DiscoverySource, source_path: str
    ) -> DiscoveredServer:
        """Record a discovered server in the internal map."""
        tags = self._infer_tags(name, url)
        existing = self._discovered.get(name)
        health = existing.health if existing else HealthStatus.UNKNOWN
        failures = existing.health_failures if existing else 0

        ds = DiscoveredServer(
            name=name,
            url=url,
            source=source,
            source_path=source_path,
            health=health,
            health_failures=failures,
            tags=tags,
        )
        self._discovered[name] = ds
        return ds

    def _upsert_registry(self, name: str, url: str) -> str:
        """Add or update a server in the central registry. Returns 'added' or 'updated'."""
        existing = self._registry.get(name)
        if existing:
            existing.url = url
            return "updated"
        self._registry.register(name=name, url=url)
        return "added"

    @staticmethod
    def _infer_tags(name: str, url: str) -> tuple[str, ...]:
        """Infer capability tags from server name and URL."""
        tags: set[str] = set()
        combined = f"{name} {url}".lower()

        if any(kw in combined for kw in ("github", "gh")):
            tags.add("vcs")
        if any(kw in combined for kw in ("notion", "docs", "confluence")):
            tags.add("docs")
        if any(kw in combined for kw in ("slack", "discord", "teams")):
            tags.add("chat")
        if any(kw in combined for kw in ("linear", "jira", "asana")):
            tags.add("project-management")
        if any(kw in combined for kw in ("postgres", "mysql", "sqlite", "database")):
            tags.add("database")
        if any(kw in combined for kw in ("docker", "kubernetes", "k8s")):
            tags.add("infra")
        if any(kw in combined for kw in ("file", "filesystem", "fs")):
            tags.add("filesystem")
        if any(kw in combined for kw in ("memory", "memgraph")):
            tags.add("memory")

        return tuple(sorted(tags))

    def _check_health(self, discovered: DiscoveredServer) -> HealthStatus:
        """Check health of a single server (lightweight connectivity probe)."""
        if discovered.health_failures >= self.max_health_failures:
            return HealthStatus.UNHEALTHY

        # If URL is a local command (stdio transport), skip connectivity check
        if discovered.url and not discovered.url.startswith(("http://", "https://", "ws://", "wss://")):
            return HealthStatus.HEALTHY

        # For HTTP-based servers, try a quick connectivity check
        try:
            import urllib.request
            req = urllib.request.Request(
                discovered.url, method="HEAD"
            )
            urllib.request.urlopen(req, timeout=self.health_check_timeout)
            return HealthStatus.HEALTHY
        except Exception:
            return HealthStatus.UNHEALTHY
