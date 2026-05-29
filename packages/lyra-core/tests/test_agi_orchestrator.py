"""Dedicated tests for agi_orchestrator.py."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from lyra_core.agi_orchestrator import AGIOrchestrator, AGIPhase, PlanStatus


class TestAGIPhase:
    def test_values(self):
        assert AGIPhase.CITADEL.value != AGIPhase.ORACLE.value
        assert AGIPhase.SINGULARITY.value != AGIPhase.SUPERORGANISM.value

    def test_all_five_phases(self):
        phases = list(AGIPhase)
        assert len(phases) == 5
        names = {p.name for p in phases}
        assert names == {"CITADEL", "ORACLE", "CHAMELEON", "SINGULARITY", "SUPERORGANISM"}


class TestPlanStatus:
    def test_create(self):
        ps = PlanStatus(name="Test", phase=AGIPhase.CITADEL, packages=["pkg-a"])
        assert ps.name == "Test"
        assert ps.phase == AGIPhase.CITADEL
        assert ps.packages == ["pkg-a"]
        assert ps.is_ready is False
        assert ps.health_score == 0.0
        assert ps.last_check == 0.0

    def test_mutable(self):
        ps = PlanStatus(name="X", phase=AGIPhase.ORACLE, packages=[])
        ps.is_ready = True
        ps.health_score = 0.9
        assert ps.is_ready is True
        assert ps.health_score == 0.9


class TestAGIOrchestrator:
    @pytest.fixture
    def orch(self):
        return AGIOrchestrator()

    def test_init_registers_five_plans(self, orch):
        assert len(orch.plans) == 5
        for phase in AGIPhase:
            assert phase in orch.plans
            assert isinstance(orch.plans[phase], PlanStatus)

    def test_init_each_plan_has_packages(self, orch):
        for phase, status in orch.plans.items():
            assert len(status.packages) > 0, f"{phase.name} has no packages"

    def test_citadel_packages(self, orch):
        pkgs = orch.plans[AGIPhase.CITADEL].packages
        assert "lyra-verification-mesh" in pkgs
        assert "lyra-hbhc" in pkgs

    def test_oracle_packages(self, orch):
        pkgs = orch.plans[AGIPhase.ORACLE].packages
        assert "lyra-causal-graph" in pkgs
        assert "lyra-science-pipeline" in pkgs

    def test_health_check_missing_packages_score_low(self, orch):
        """When packages don't exist, health_score should be 0.3 per package."""
        with patch("importlib.import_module", side_effect=ImportError):
            result = asyncio.run(orch.health_check())
        for status in result.values():
            assert status.health_score == pytest.approx(0.3, abs=0.01)
            assert status.is_ready is False

    def test_health_check_all_packages_exist_score_high(self):
        orch = AGIOrchestrator()
        # All 19 packages return True → score = 1.0
        with patch("importlib.import_module", return_value=True):
            result = asyncio.run(orch.health_check())
        for status in result.values():
            assert status.health_score == pytest.approx(1.0, abs=0.01)
            assert status.is_ready is True

    def test_health_check_records_history(self, orch):
        assert len(orch._health_history) == 0
        asyncio.run(orch.health_check())
        assert len(orch._health_history) == 1
        asyncio.run(orch.health_check())
        assert len(orch._health_history) == 2

    def test_health_check_updates_last_check(self, orch):
        asyncio.run(orch.health_check())
        for status in orch.plans.values():
            assert status.last_check > 0

    def test_get_overview_before_health_check(self, orch):
        overview = orch.get_overview()
        assert overview["overall_health"] == 0.0
        assert overview["ready_phases"] == 0
        assert overview["agi_readiness"] is False

    def test_get_overview_after_health_check(self, orch):
        with patch("importlib.import_module", return_value=True):
            asyncio.run(orch.health_check())
        overview = orch.get_overview()
        assert overview["overall_health"] == pytest.approx(1.0)
        assert overview["ready_phases"] == 5
        assert overview["agi_readiness"] is True

    def test_get_overview_agi_readiness_requires_three_ready(self, orch):
        """agi_readiness requires >0.6 overall health AND >=3 ready phases."""
        high_pkgs = {
            "lyra_verification_mesh", "lyra_hbhc", "lyra_viper_mcp", "lyra_attestor",
            "lyra_causal_graph", "lyra_counterfactual", "lyra_science_pipeline", "lyra_claim_verification",
            "lyra_drift_detector", "lyra_skill_weaver", "lyra_context_profiler", "lyra_competence_map",
        }

        def mock_import(name, *args, **__):
            if name in high_pkgs:
                return object()
            raise ImportError(f"No module named '{name}'")

        with patch("importlib.import_module", side_effect=mock_import):
            asyncio.run(orch.health_check())
        overview = orch.get_overview()
        assert overview["ready_phases"] == 3
        assert overview["agi_readiness"] is True

    def test_get_overview_agi_readiness_fails_below_three_ready(self, orch):
        """agi_readiness fails when <3 phases are ready."""
        high_pkgs = {
            "lyra_verification_mesh", "lyra_hbhc", "lyra_viper_mcp", "lyra_attestor",
        }

        def mock_import(name, *args, **__):
            if name in high_pkgs:
                return object()
            raise ImportError(f"No module named '{name}'")

        with patch("importlib.import_module", side_effect=mock_import):
            asyncio.run(orch.health_check())
        overview = orch.get_overview()
        assert overview["ready_phases"] == 1
        assert overview["agi_readiness"] is False

    def test_emergency_shield(self, orch):
        with patch("importlib.import_module", return_value=True):
            asyncio.run(orch.health_check())
        result = asyncio.run(orch.emergency_shield())
        assert result["status"] == "emergency_shield_active"
        assert result["citadel_health"] > 0
        assert len(result["phases_paused"]) == 4

    def test_background_health_starts_and_stops(self, orch):
        asyncio.run(orch.start_background_health(interval=0.01))
        assert orch._running is True
        assert orch._task is not None
        asyncio.run(orch.stop())
        assert orch._running is False

    def test_background_health_runs_checks(self, orch):
        async def _run():
            await orch.start_background_health(interval=0.02)
            await asyncio.sleep(0.06)
            await orch.stop()

        asyncio.run(_run())
        assert len(orch._health_history) >= 1

    def test_stop_when_not_running(self, orch):
        """Stop should be a no-op when not running."""
        asyncio.run(orch.stop())
        assert orch._running is False

    def test_health_check_is_idempotent(self, orch):
        r1 = asyncio.run(orch.health_check())
        r2 = asyncio.run(orch.health_check())
        for phase in AGIPhase:
            assert r1[phase].health_score == r2[phase].health_score

    def test_plan_status_str_repr(self, orch):
        ps = orch.plans[AGIPhase.CITADEL]
        assert "Citadel" in str(ps) or "Citadel" in ps.name
