"""Tests for BreakthroughIntegration — the unified AGI upgrade facade."""
from __future__ import annotations

import pytest
from lyra_core.breakthrough import (
    BreakthroughIntegration,
    CapabilityDomain,
    SystemHealth,
    UpgradeStatus,
    breakthrough_available,
)


class TestBreakthroughIntegration:
    """Core integration tests for the breakthrough facade."""

    def test_registry_has_all_20_upgrades(self):
        bi = BreakthroughIntegration()
        assert len(bi.UPGRADE_REGISTRY) >= 20, f"Expected 20+ upgrades, got {len(bi.UPGRADE_REGISTRY)}"

    def test_all_upgrades_have_domain_and_phase(self):
        bi = BreakthroughIntegration()
        for name, (domain, phase, pkgs) in bi.UPGRADE_REGISTRY.items():
            assert isinstance(domain, CapabilityDomain), f"{name}: domain must be CapabilityDomain"
            assert 1 <= phase <= 5, f"{name}: phase must be 1-5, got {phase}"
            assert len(pkgs) >= 1, f"{name}: must have at least 1 package"

    def test_scan_availability_returns_dict(self):
        bi = BreakthroughIntegration()
        result = bi.scan_availability()
        assert isinstance(result, dict)
        assert len(result) >= 20

    def test_health_check_returns_system_health(self):
        bi = BreakthroughIntegration()
        health = bi.health_check()
        assert isinstance(health, SystemHealth)
        assert 0.0 <= health.overall <= 1.0
        assert 0.0 <= health.agi_readiness <= 1.0
        assert health.total_upgrades >= 20

    def test_health_check_stores_history(self):
        bi = BreakthroughIntegration()
        bi.health_check()
        bi.health_check()
        assert len(bi._health_history) == 2

    def test_health_history_capped_at_1000(self):
        bi = BreakthroughIntegration()
        bi._health_history = [bi.health_check()] * 1001
        bi.health_check()
        assert len(bi._health_history) <= 1001

    def test_summary_includes_all_sections(self):
        bi = BreakthroughIntegration()
        s = bi.summary
        assert "system_health" in s
        assert "domain_health" in s
        assert "phase_health" in s
        assert "upgrades" in s

    def test_get_upgrade_by_name(self):
        bi = BreakthroughIntegration()
        aer = bi.get_upgrade("aer")
        assert aer is not None
        assert aer.name == "aer"
        assert aer.domain == CapabilityDomain.REASONING
        assert aer.phase == 1

    def test_get_upgrade_missing_returns_none(self):
        bi = BreakthroughIntegration()
        assert bi.get_upgrade("nonexistent") is None

    def test_get_domain_upgrades(self):
        bi = BreakthroughIntegration()
        reasoning = bi.get_domain_upgrades(CapabilityDomain.REASONING)
        assert len(reasoning) >= 4
        assert all(s.domain == CapabilityDomain.REASONING for s in reasoning)

    def test_get_phase_upgrades(self):
        bi = BreakthroughIntegration()
        phase1 = bi.get_phase_upgrades(1)
        assert len(phase1) >= 3
        assert all(s.phase == 1 for s in phase1)

    def test_upgrade_names_returns_list(self):
        bi = BreakthroughIntegration()
        names = bi.upgrade_names
        assert isinstance(names, list)
        assert "aer" in names
        assert "hierarchical_memory" in names

    def test_breakthrough_available_utility(self):
        result = breakthrough_available()
        assert isinstance(result, dict)
        assert len(result) >= 20


class TestCrossPlanCoordination:
    """Tests for cross-plan coordination events."""

    @pytest.fixture
    def bi(self):
        return BreakthroughIntegration()

    @pytest.mark.asyncio
    async def test_coordinate_safety_breach(self, bi):
        result = await bi.coordinate("safety_breach", {"source": "test"})
        assert result["action"] == "activate_shield"

    @pytest.mark.asyncio
    async def test_coordinate_drift_detected(self, bi):
        result = await bi.coordinate("drift_detected", {"domain": "reasoning", "severity": "high"})
        assert result["action"] == "reverify"

    @pytest.mark.asyncio
    async def test_coordinate_performance_drop(self, bi):
        result = await bi.coordinate("performance_drop", {"component": "router", "fallback": "opus"})
        assert result["action"] == "reroute"

    @pytest.mark.asyncio
    async def test_coordinate_new_capability(self, bi):
        result = await bi.coordinate("new_capability", {"name": "code_review"})
        assert result["action"] == "register"

    @pytest.mark.asyncio
    async def test_coordinate_agent_failure(self, bi):
        result = await bi.coordinate("agent_failure", {"agent_id": "agent-1"})
        assert result["action"] == "respawn"

    @pytest.mark.asyncio
    async def test_coordinate_knowledge_update(self, bi):
        result = await bi.coordinate("knowledge_update", {"source": "wiki", "entities": ["E1", "E2"]})
        assert result["action"] == "propagate"

    @pytest.mark.asyncio
    async def test_coordinate_unknown_event_noop(self, bi):
        result = await bi.coordinate("unknown_event")
        assert result["action"] == "noop"


class TestHooks:
    @pytest.fixture
    def bi(self):
        return BreakthroughIntegration()

    @pytest.mark.asyncio
    async def test_emit_calls_registered_hooks(self, bi):
        called_with = []

        def hook(data):
            called_with.append(data)

        bi.on("test_event", hook)
        await bi.emit("test_event", {"key": "val"})
        assert len(called_with) == 1
        assert called_with[0] == {"key": "val"}

    @pytest.mark.asyncio
    async def test_emit_async_hook(self, bi):
        called = []

        async def async_hook(data):
            called.append(data)

        bi.on("async_event", async_hook)
        await bi.emit("async_event", {"x": 1})
        assert len(called) == 1

    @pytest.mark.asyncio
    async def test_emit_handles_hook_error_gracefully(self, bi):
        def bad_hook(data):
            raise RuntimeError("hook error")

        bi.on("bad", bad_hook)
        await bi.emit("bad", {})  # Should not raise

    @pytest.mark.asyncio
    async def test_emit_no_hooks_no_error(self, bi):
        await bi.emit("nonexistent")  # Should not raise


class TestSystemHealth:
    def test_system_health_dataclass(self):
        h = SystemHealth(
            overall=0.8, by_domain={"REASONING": 0.9}, by_phase={1: 0.85},
            ready_upgrades=15, total_upgrades=20, agi_readiness=0.78,
        )
        assert h.overall == 0.8
        assert h.ready_upgrades == 15
        assert h.agi_readiness == 0.78


class TestUpgradeStatus:
    def test_upgrade_status_defaults(self):
        s = UpgradeStatus(name="test", domain=CapabilityDomain.REASONING, phase=1)
        assert s.is_available is False
        assert s.is_initialized is False
        assert s.health_score == 0.0
        assert s.instance is None
        assert s.metrics == {}
