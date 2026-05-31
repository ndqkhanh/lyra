"""Tests for Tiered MCP Server Bundling (P1-B3)."""
from __future__ import annotations

import pytest

from lyra_harness_core.mcp_bundling import (
    MCPLifecycleManager,
    MCPServerHealth,
    MCPServerInstance,
    MCPServerManifest,
    MCPServerState,
    MCPTier,
    TieredBundle,
    build_default_bundle,
    build_default_tier1_manifests,
    build_default_tier2_manifests,
)


# ---------------------------------------------------------------------------
# MCPTier, MCPServerState, MCPServerHealth
# ---------------------------------------------------------------------------


class TestMCPTier:
    def test_values(self):
        assert MCPTier.TIER_1.value == "tier_1"
        assert MCPTier.TIER_2.value == "tier_2"


class TestMCPServerState:
    def test_values(self):
        assert MCPServerState.STOPPED.value == "stopped"
        assert MCPServerState.RUNNING.value == "running"


class TestMCPServerHealth:
    def test_values(self):
        assert MCPServerHealth.HEALTHY.value == "healthy"
        assert MCPServerHealth.UNKNOWN.value == "unknown"


# ---------------------------------------------------------------------------
# MCPServerManifest
# ---------------------------------------------------------------------------


class TestMCPServerManifest:
    def test_minimal(self):
        m = MCPServerManifest(name="test", command="npx")
        assert m.name == "test"
        assert m.command == "npx"
        assert m.args == []
        assert m.tier == MCPTier.TIER_2
        assert m.tools == []

    def test_with_args(self):
        m = MCPServerManifest(
            name="fs",
            command="npx",
            args=["-y", "@mcp/filesystem"],
            tier=MCPTier.TIER_1,
            tools=["read", "write"],
        )
        assert m.args == ["-y", "@mcp/filesystem"]
        assert m.tier == MCPTier.TIER_1
        assert m.tools == ["read", "write"]

    def test_frozen(self):
        m = MCPServerManifest(name="x", command="cmd")
        with pytest.raises(Exception):
            m.name = "y"  # type: ignore[misc]

    def test_to_dict(self):
        m = MCPServerManifest(
            name="fs",
            command="npx",
            tier=MCPTier.TIER_1,
            description="filesystem",
            version="1.2.3",
        )
        d = m.to_dict()
        assert d["name"] == "fs"
        assert d["tier"] == "tier_1"
        assert d["version"] == "1.2.3"


# ---------------------------------------------------------------------------
# MCPServerInstance
# ---------------------------------------------------------------------------


class TestMCPServerInstance:
    @pytest.fixture
    def manifest(self):
        return MCPServerManifest(name="test", command="cmd", tools=["t1", "t2"])

    def test_initial_state(self, manifest):
        instance = MCPServerInstance(manifest=manifest)
        assert instance.state == MCPServerState.STOPPED
        assert instance.health == MCPServerHealth.UNKNOWN
        assert instance.pid is None
        assert instance.uptime_seconds == 0

    def test_is_running(self, manifest):
        instance = MCPServerInstance(manifest=manifest)
        assert not instance.is_running
        instance.state = MCPServerState.RUNNING
        assert instance.is_running

    def test_is_degraded(self, manifest):
        instance = MCPServerInstance(manifest=manifest)
        assert not instance.is_degraded
        instance.health = MCPServerHealth.DEGRADED
        assert instance.is_degraded

    def test_tool_count(self, manifest):
        instance = MCPServerInstance(manifest=manifest)
        assert instance.tool_count == 2

    def test_to_dict(self, manifest):
        instance = MCPServerInstance(manifest=manifest)
        d = instance.to_dict()
        assert d["name"] == "test"
        assert d["state"] == "stopped"


# ---------------------------------------------------------------------------
# TieredBundle
# ---------------------------------------------------------------------------


class TestTieredBundle:
    @pytest.fixture
    def bundle(self):
        b = TieredBundle()
        b.tier_1.append(MCPServerInstance(
            manifest=MCPServerManifest(
                name="fs", command="npx", tier=MCPTier.TIER_1, tools=["read", "write"],
            ),
        ))
        b.tier_2.append(MCPServerInstance(
            manifest=MCPServerManifest(
                name="db", command="npx", tier=MCPTier.TIER_2, tools=["query"],
            ),
        ))
        return b

    def test_all_servers(self, bundle):
        assert len(bundle.all_servers) == 2

    def test_servers_by_tier(self, bundle):
        assert len(bundle.servers_by_tier(MCPTier.TIER_1)) == 1
        assert len(bundle.servers_by_tier(MCPTier.TIER_2)) == 1

    def test_get_server(self, bundle):
        assert bundle.get_server("fs") is not None
        assert bundle.get_server("nope") is None

    def test_tools_by_tier(self, bundle):
        tier1_tools = bundle.tools_by_tier(MCPTier.TIER_1)
        assert "read" in tier1_tools
        assert "write" in tier1_tools

    def test_all_tools(self, bundle):
        tools = bundle.all_tools()
        assert "fs" in tools
        assert "db" in tools
        assert tools["fs"] == ["read", "write"]

    def test_is_tier_healthy(self, bundle):
        assert not bundle.is_tier_healthy(MCPTier.TIER_1)
        bundle.tier_1[0].health = MCPServerHealth.HEALTHY
        assert bundle.is_tier_healthy(MCPTier.TIER_1)

    def test_server_count(self, bundle):
        assert bundle.server_count == 2

    def test_total_tool_count(self, bundle):
        assert bundle.total_tool_count == 3  # 2 from fs + 1 from db

    def test_running_servers(self, bundle):
        assert len(bundle.running_servers) == 0
        bundle.tier_1[0].state = MCPServerState.RUNNING
        assert len(bundle.running_servers) == 1

    def test_degraded_servers(self, bundle):
        assert len(bundle.degraded_servers) == 0
        bundle.tier_1[0].health = MCPServerHealth.UNHEALTHY
        assert len(bundle.degraded_servers) == 1

    def test_to_dict(self, bundle):
        d = bundle.to_dict()
        assert "tier_1" in d
        assert "tier_2" in d
        assert len(d["tier_1"]) == 1


# ---------------------------------------------------------------------------
# MCPLifecycleManager
# ---------------------------------------------------------------------------


class TestMCPLifecycleManager:
    @pytest.fixture
    def manager(self):
        mgr = MCPLifecycleManager()
        mgr.register(MCPServerManifest(
            name="fs", command="npx", tier=MCPTier.TIER_1, tools=["read"],
        ))
        mgr.register(MCPServerManifest(
            name="db", command="npx", tier=MCPTier.TIER_2, tools=["query"],
        ))
        return mgr

    def test_register(self, manager):
        assert manager.bundle.server_count == 2
        assert manager.bundle.get_server("fs") is not None

    def test_unregister(self, manager):
        assert manager.unregister("fs")
        assert manager.bundle.server_count == 1
        assert manager.bundle.get_server("fs") is None

    def test_unregister_nonexistent(self, manager):
        assert not manager.unregister("nope")

    def test_start(self, manager):
        assert manager.start("fs")
        instance = manager.bundle.get_server("fs")
        assert instance.state == MCPServerState.RUNNING
        assert instance.health == MCPServerHealth.HEALTHY

    def test_start_nonexistent(self, manager):
        assert not manager.start("nope")

    def test_stop(self, manager):
        manager.start("fs")
        assert manager.stop("fs")
        instance = manager.bundle.get_server("fs")
        assert instance.state == MCPServerState.STOPPED

    def test_restart(self, manager):
        manager.start("fs")
        assert manager.restart("fs")
        instance = manager.bundle.get_server("fs")
        assert instance.state == MCPServerState.RUNNING
        assert instance.restart_count == 1

    def test_start_tier(self, manager):
        started = manager.start_tier(MCPTier.TIER_1)
        assert "fs" in started
        assert manager.bundle.get_server("fs").is_running

    def test_stop_tier(self, manager):
        manager.start_all()
        stopped = manager.stop_tier(MCPTier.TIER_1)
        assert "fs" in stopped

    def test_start_all_tier1_healthy(self, manager):
        result = manager.start_all()
        assert "fs" in result["tier_1"]
        # Tier-1 starts first, then Tier-2 if Tier-1 healthy
        assert "db" in result["tier_2"]

    def test_start_all_tier1_unhealthy_blocks_tier2(self, manager):
        # Start only Tier-1 but mark it unhealthy
        manager.start("fs")
        manager.mark_unhealthy("fs", "test failure")
        # start_all should still start tier-2 since we're only checking tier health
        manager.bundle.tier_1[0].health = MCPServerHealth.UNHEALTHY
        assert not manager.bundle.is_tier_healthy(MCPTier.TIER_1)
        result = manager.start_all()
        assert "fs" in result["tier_1"]
        # Tier-2 should NOT start when Tier-1 is unhealthy
        assert result["tier_2"] == []

    def test_stop_all(self, manager):
        manager.start_all()
        count = manager.stop_all()
        assert count == 2

    def test_health_check(self, manager):
        manager.start("fs")
        health = manager.health_check("fs")
        assert health == MCPServerHealth.HEALTHY

    def test_health_check_nonexistent(self, manager):
        assert manager.health_check("nope") == MCPServerHealth.UNKNOWN

    def test_health_check_not_running(self, manager):
        health = manager.health_check("fs")
        assert health == MCPServerHealth.UNHEALTHY

    def test_health_check_all(self, manager):
        manager.start("fs")
        results = manager.health_check_all()
        assert "fs" in results
        assert "db" in results

    def test_mark_degraded(self, manager):
        manager.start("fs")
        manager.mark_degraded("fs", "high latency")
        instance = manager.bundle.get_server("fs")
        assert instance.health == MCPServerHealth.DEGRADED
        assert instance.error_message == "high latency"

    def test_mark_unhealthy(self, manager):
        manager.start("fs")
        manager.mark_unhealthy("fs", "connection lost")
        instance = manager.bundle.get_server("fs")
        assert instance.health == MCPServerHealth.UNHEALTHY
        assert instance.error_message == "connection lost"
        # State should remain RUNNING (health is degraded, not crashed)

    def test_get_server_info(self, manager):
        manager.start("fs")
        info = manager.get_server_info("fs")
        assert info is not None
        assert info["name"] == "fs"
        assert info["state"] == "running"

    def test_get_server_info_nonexistent(self, manager):
        assert manager.get_server_info("nope") is None

    def test_get_tool_providers(self, manager):
        providers = manager.get_tool_providers("read")
        assert "fs" in providers
        assert "db" not in providers

    def test_get_tool_providers_none(self, manager):
        assert manager.get_tool_providers("nonexistent") == []

    def test_stats(self, manager):
        manager.start("fs")
        stats = manager.stats()
        assert stats["total_servers"] == 2
        assert stats["tier_1_count"] == 1
        assert stats["tier_2_count"] == 1
        assert stats["running"] == 1
        assert stats["total_tools"] == 2

    def test_restart_rate_limit(self, manager):
        manager._max_restarts = 2
        manager.start("fs")
        assert manager.restart("fs")  # 1
        assert manager.restart("fs")  # 2
        assert not manager.restart("fs")  # exceeds limit
        instance = manager.bundle.get_server("fs")
        assert instance.state == MCPServerState.ERROR
        assert "rate limit" in instance.error_message


# ---------------------------------------------------------------------------
# Pre-built Bundles
# ---------------------------------------------------------------------------


class TestBuildDefaultTier1Manifests:
    def test_count(self):
        manifests = build_default_tier1_manifests()
        assert len(manifests) == 4

    def test_all_tier1(self):
        for m in build_default_tier1_manifests():
            assert m.tier == MCPTier.TIER_1

    def test_names(self):
        names = {m.name for m in build_default_tier1_manifests()}
        assert names == {"filesystem", "git", "search", "context"}


class TestBuildDefaultTier2Manifests:
    def test_count(self):
        manifests = build_default_tier2_manifests()
        assert len(manifests) == 4

    def test_all_tier2(self):
        for m in build_default_tier2_manifests():
            assert m.tier == MCPTier.TIER_2

    def test_names(self):
        names = {m.name for m in build_default_tier2_manifests()}
        assert names == {"database", "browser", "slack", "memory"}


class TestBuildDefaultBundle:
    def test_server_count(self):
        bundle, manager = build_default_bundle()
        assert bundle.server_count == 8
        assert len(bundle.tier_1) == 4
        assert len(bundle.tier_2) == 4

    def test_start_all(self):
        bundle, manager = build_default_bundle()
        result = manager.start_all()
        assert len(result["tier_1"]) == 4
        assert len(result["tier_2"]) == 4

    def test_tools_available(self):
        bundle, manager = build_default_bundle()
        providers = manager.get_tool_providers("read_file")
        assert "filesystem" in providers


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------


class TestMCPBundlingIntegration:
    def test_full_lifecycle(self):
        manager = MCPLifecycleManager()

        # Register Tier-1 servers
        manager.register(MCPServerManifest(
            name="fs", command="npx", tier=MCPTier.TIER_1,
            tools=["read", "write"],
        ))
        manager.register(MCPServerManifest(
            name="search", command="npx", tier=MCPTier.TIER_1,
            tools=["grep"],
        ))

        # Register Tier-2 servers
        manager.register(MCPServerManifest(
            name="db", command="npx", tier=MCPTier.TIER_2,
            tools=["query"],
        ))

        # Start all (Tier-1 first)
        result = manager.start_all()
        assert len(result["tier_1"]) == 2
        assert len(result["tier_2"]) == 1

        # Verify Tier-1 healthy -> Tier-2 started
        assert manager.bundle.is_tier_healthy(MCPTier.TIER_1)

        # Check tool providers
        assert manager.get_tool_providers("read") == ["fs"]
        assert manager.get_tool_providers("grep") == ["search"]
        assert manager.get_tool_providers("query") == ["db"]

        # Health check all
        results = manager.health_check_all()
        assert all(h == MCPServerHealth.HEALTHY for h in results.values())

        # Mark one degraded
        manager.mark_degraded("db", "slow query")
        assert manager.bundle.get_server("db").is_degraded

        # Stats
        stats = manager.stats()
        assert stats["running"] == 3
        assert stats["degraded"] == 1

        # Stop all
        assert manager.stop_all() == 3
        assert manager.stats()["running"] == 0

    def test_tiered_tool_discovery(self):
        """Tools should be discoverable per tier."""
        bundle, manager = build_default_bundle()
        manager.start_all()

        tier1_tools = bundle.tools_by_tier(MCPTier.TIER_1)
        tier2_tools = bundle.tools_by_tier(MCPTier.TIER_2)

        assert len(tier1_tools) > 0
        assert len(tier2_tools) > 0
        # Core tools only in tier 1
        assert "read_file" in tier1_tools
        # Specialized tools only in tier 2
        assert "db_query" in tier2_tools
