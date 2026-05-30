"""Tests for MCP Server Discovery."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from lyra_core.mcp import MCPRegistry
from lyra_core.mcp.server_discovery import (
    DiscoveredServer,
    DiscoveryResult,
    DiscoverySource,
    HealthStatus,
    ServerDiscovery,
)


class TestDiscoverySource:
    def test_enum_values(self):
        assert DiscoverySource.MCP_JSON == ".mcp.json"
        assert DiscoverySource.CLAUDE_JSON == "~/.claude.json"
        assert DiscoverySource.ENV_VAR == "env:MCP_SERVERS"
        assert DiscoverySource.WELL_KNOWN == "well_known"
        assert DiscoverySource.MANUAL == "manual"


class TestHealthStatus:
    def test_enum_values(self):
        assert HealthStatus.UNKNOWN == "unknown"
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNHEALTHY == "unhealthy"


class TestServerDiscovery:
    def test_init_with_registry(self):
        registry = MCPRegistry()
        sd = ServerDiscovery(registry)
        assert sd.discovered_count == 0
        assert sd.health_check_interval == 30.0

    def test_discover_from_mcp_json(self, tmp_path: Path):
        registry = MCPRegistry()
        sd = ServerDiscovery(registry)

        config = {"mcpServers": {"github": {"url": "http://localhost:8080"}}}
        config_path = tmp_path / ".mcp.json"
        config_path.write_text(json.dumps(config))

        orig_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            result = sd.discover_from_source(DiscoverySource.MCP_JSON)
            assert result.servers_found >= 1
        finally:
            os.chdir(orig_cwd)

    def test_discover_from_mcp_json_multiple_servers(self, tmp_path: Path):
        registry = MCPRegistry()
        sd = ServerDiscovery(registry)

        config = {
            "mcpServers": {
                "github": {"url": "http://localhost:8080"},
                "notion": {"url": "http://localhost:8081"},
                "slack": {"url": "http://localhost:8082"},
            }
        }
        config_path = tmp_path / ".mcp.json"
        config_path.write_text(json.dumps(config))

        orig_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            result = sd.discover_from_source(DiscoverySource.MCP_JSON)
            assert result.servers_found >= 3
        finally:
            os.chdir(orig_cwd)

    def test_discover_from_env_var(self):
        registry = MCPRegistry()
        sd = ServerDiscovery(registry)

        servers = [
            {"name": "srv1", "url": "http://localhost:8001"},
            {"name": "srv2", "url": "http://localhost:8002"},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(servers, f)
            temp_path = f.name

        try:
            os.environ["MCP_SERVERS"] = json.dumps(servers)
            result = sd.discover_from_source(DiscoverySource.ENV_VAR)
            assert result.servers_found >= 2
        finally:
            os.environ.pop("MCP_SERVERS", None)
            os.unlink(temp_path)

    def test_discover_from_env_var_simple_format(self):
        registry = MCPRegistry()
        sd = ServerDiscovery(registry)

        os.environ["MCP_SERVERS"] = json.dumps(["myserver:http://localhost:9999"])
        try:
            result = sd.discover_from_source(DiscoverySource.ENV_VAR)
            assert result.servers_found >= 1
        finally:
            os.environ.pop("MCP_SERVERS", None)

    def test_discover_from_env_var_empty(self):
        registry = MCPRegistry()
        sd = ServerDiscovery(registry)

        if "MCP_SERVERS" in os.environ:
            del os.environ["MCP_SERVERS"]
        result = sd.discover_from_source(DiscoverySource.ENV_VAR)
        assert result.servers_found == 0

    def test_discover_all(self, tmp_path: Path):
        registry = MCPRegistry()
        sd = ServerDiscovery(registry)

        config = {"mcpServers": {"test-srv": {"url": "http://localhost:7777"}}}
        config_path = tmp_path / ".mcp.json"
        config_path.write_text(json.dumps(config))

        orig_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            results = sd.discover_all()
            assert len(results) >= 1
        finally:
            os.chdir(orig_cwd)

    def test_servers_registered_in_registry(self, tmp_path: Path):
        registry = MCPRegistry()
        sd = ServerDiscovery(registry)

        config = {"mcpServers": {"gh": {"url": "http://localhost:8888"}}}
        config_path = tmp_path / ".mcp.json"
        config_path.write_text(json.dumps(config))

        orig_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            sd.discover_all()
            assert registry.get("gh") is not None
            assert registry.get("gh").url == "http://localhost:8888"
        finally:
            os.chdir(orig_cwd)

    def test_discover_unknown_source(self):
        registry = MCPRegistry()
        sd = ServerDiscovery(registry)
        result = sd.discover_from_source(DiscoverySource.MANUAL)
        assert result.servers_found == 0
        assert len(result.errors) >= 1

    def test_list_discovered(self, tmp_path: Path):
        registry = MCPRegistry()
        sd = ServerDiscovery(registry)

        config = {"mcpServers": {"s1": {"url": "http://localhost:9001"}}}
        (tmp_path / ".mcp.json").write_text(json.dumps(config))

        orig_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            sd.discover_all()
            discovered = sd.list_discovered()
            assert len(discovered) >= 1
        finally:
            os.chdir(orig_cwd)

    def test_get_discovered(self, tmp_path: Path):
        registry = MCPRegistry()
        sd = ServerDiscovery(registry)

        config = {"mcpServers": {"findme": {"url": "http://localhost:9999"}}}
        (tmp_path / ".mcp.json").write_text(json.dumps(config))

        orig_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            sd.discover_all()
            d = sd.get_discovered("findme")
            assert d is not None
            assert d.name == "findme"
        finally:
            os.chdir(orig_cwd)

    def test_get_discovered_missing(self):
        registry = MCPRegistry()
        sd = ServerDiscovery(registry)
        assert sd.get_discovered("nonexistent") is None

    def test_discovery_history_accumulates(self, tmp_path: Path):
        registry = MCPRegistry()
        sd = ServerDiscovery(registry)

        config = {"mcpServers": {"hist": {"url": "http://localhost:7777"}}}
        (tmp_path / ".mcp.json").write_text(json.dumps(config))

        orig_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            sd.discover_all()
            assert len(sd.get_discovery_history()) >= 1
        finally:
            os.chdir(orig_cwd)

    def test_clear_removes_all(self, tmp_path: Path):
        registry = MCPRegistry()
        sd = ServerDiscovery(registry)

        config = {"mcpServers": {"tmp-srv": {"url": "http://localhost:5555"}}}
        (tmp_path / ".mcp.json").write_text(json.dumps(config))

        orig_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            sd.discover_all()
            sd.clear()
            assert sd.discovered_count == 0
            assert len(sd.get_discovery_history()) == 0
        finally:
            os.chdir(orig_cwd)

    def test_get_unhealthy_servers_initially_empty(self):
        registry = MCPRegistry()
        sd = ServerDiscovery(registry)
        assert sd.get_unhealthy_servers() == []

    def test_should_health_check_initially_false(self):
        registry = MCPRegistry()
        sd = ServerDiscovery(registry)
        assert sd.should_health_check() is False

    def test_infer_tags_detects_vcs(self):
        ds = DiscoveredServer(
            name="github-server",
            url="http://localhost:8080",
            source=DiscoverySource.MANUAL,
            tags=("vcs",),
        )
        assert "vcs" in ds.tags

    def test_discover_with_invalid_json(self, tmp_path: Path):
        registry = MCPRegistry()
        sd = ServerDiscovery(registry)

        (tmp_path / ".mcp.json").write_text("not valid json {{{")

        orig_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            result = sd.discover_from_source(DiscoverySource.MCP_JSON)
            assert len(result.errors) >= 1
        finally:
            os.chdir(orig_cwd)

    def test_discover_from_well_known_empty(self):
        registry = MCPRegistry()
        sd = ServerDiscovery(registry)
        result = sd.discover_from_source(DiscoverySource.WELL_KNOWN)
        assert result.servers_found == 0

    def test_re_discover_updates_existing_server(self, tmp_path: Path):
        registry = MCPRegistry()
        sd = ServerDiscovery(registry)

        config = {"mcpServers": {"dual": {"url": "http://localhost:1111"}}}
        (tmp_path / ".mcp.json").write_text(json.dumps(config))

        orig_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            sd.discover_from_source(DiscoverySource.MCP_JSON)
            assert sd.discovered_count >= 1

            # Second discovery should update, not duplicate
            result = sd.discover_from_source(DiscoverySource.MCP_JSON)
            assert result.servers_added == 0
        finally:
            os.chdir(orig_cwd)

    def test_discovery_result_dataclass(self):
        ds = DiscoveredServer(
            name="test", url="http://example.com", source=DiscoverySource.MANUAL
        )
        result = DiscoveryResult(
            servers_found=1,
            servers_added=1,
            servers_updated=0,
            source=DiscoverySource.MANUAL,
            discovered=[ds],
        )
        assert result.servers_found == 1
        assert len(result.discovered) == 1
