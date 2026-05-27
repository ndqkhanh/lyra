"""Tests for Two-Circuit Architecture Bridge (Plan 33)."""

import pytest

from lyra_core.two_circuit import (
    CircuitMode,
    ColdPathResult,
    HotPathConfig,
    ImprovementStatus,
    TwoCircuitBridge,
)


class TestTwoCircuitBridge:
    def _make_result(self, imp_id: str = "imp-001", score_delta: float = 0.15) -> ColdPathResult:
        return ColdPathResult(
            improvement_id=imp_id,
            skill_name="test_skill",
            original_text="original prompt",
            improved_text="improved prompt",
            score_delta=score_delta,
            review_rounds=0,
        )

    def test_submit_cold_path_result(self):
        bridge = TwoCircuitBridge()
        result = self._make_result()
        bridge.submit_cold_path_result(result)

        assert bridge.pending_count == 1
        assert result.status == ImprovementStatus.PENDING

    @pytest.mark.asyncio
    async def test_review_approves_improvement(self):
        bridge = TwoCircuitBridge()

        async def approve_fn(_result):
            return True, "Looks good"

        result = self._make_result()
        bridge.submit_cold_path_result(result)
        status = await bridge.review("imp-001", approve_fn)

        assert status == ImprovementStatus.APPROVED
        assert bridge.approved_count == 1
        assert bridge.pending_count == 0

    @pytest.mark.asyncio
    async def test_review_rejects_after_max_rounds(self):
        bridge = TwoCircuitBridge(max_review_rounds=2)

        async def reject_fn(_result):
            return False, "Needs work"

        result = self._make_result()
        bridge.submit_cold_path_result(result)
        status = await bridge.review("imp-001", reject_fn)

        assert status == ImprovementStatus.REJECTED
        assert bridge.rejected_count == 1

    @pytest.mark.asyncio
    async def test_review_without_requirement_auto_approves(self):
        bridge = TwoCircuitBridge(review_required=False)
        result = self._make_result()
        bridge.submit_cold_path_result(result)
        status = await bridge.review("imp-001", async_noop)

        assert status == ImprovementStatus.APPROVED

    @pytest.mark.asyncio
    async def test_review_partial_approval(self):
        bridge = TwoCircuitBridge(max_review_rounds=3)
        call_count = 0

        async def approve_on_second(_result):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                return True, "Fixed on second pass"
            return False, "Try again"

        result = self._make_result()
        bridge.submit_cold_path_result(result)
        status = await bridge.review("imp-001", approve_on_second)

        assert status == ImprovementStatus.APPROVED
        assert result.review_rounds == 2

    def test_review_unknown_id_raises(self):
        bridge = TwoCircuitBridge()

        with pytest.raises(KeyError):
            import asyncio

            asyncio.get_event_loop().run_until_complete(bridge.review("nonexistent", async_noop))

    def test_get_hot_path_config(self):
        bridge = TwoCircuitBridge(review_required=False)

        result = self._make_result()
        bridge.submit_cold_path_result(result)

        import asyncio

        asyncio.get_event_loop().run_until_complete(bridge.review("imp-001", async_noop))

        config = bridge.get_hot_path_config()
        assert "test_skill" in config.skill_overrides
        assert config.skill_overrides["test_skill"] == "improved prompt"
        assert "imp-001" in config.approved_improvements

    def test_deploy_approved(self):
        bridge = TwoCircuitBridge(review_required=False)
        result = self._make_result()
        bridge.submit_cold_path_result(result)

        import asyncio

        asyncio.get_event_loop().run_until_complete(bridge.review("imp-001", async_noop))

        deployed = bridge.deploy_approved()
        assert deployed == ["imp-001"]
        assert bridge.deployed_count == 1
        assert bridge.approved_count == 0

    def test_summary_counts(self):
        bridge = TwoCircuitBridge()
        s = bridge.summary()
        assert s == {"pending": 0, "approved": 0, "rejected": 0, "deployed": 0}

    def test_hot_path_config_defaults(self):
        config = HotPathConfig()
        assert config.skill_overrides == {}
        assert config.approved_improvements == []
        assert config.stagnation_threshold == 3
        assert config.fanout_max == 5

    def test_circuit_mode_enum(self):
        assert CircuitMode.HOT != CircuitMode.COLD
        assert CircuitMode.BRIDGE is not None

    def test_improvement_status_enum(self):
        assert ImprovementStatus.PENDING.value == "pending"
        assert ImprovementStatus.DEPLOYED.value == "deployed"

    @pytest.mark.asyncio
    async def test_multiple_improvements(self):
        bridge = TwoCircuitBridge(review_required=False)

        for i in range(3):
            result = self._make_result(f"imp-{i:03d}", score_delta=0.1 * i)
            bridge.submit_cold_path_result(result)
            await bridge.review(f"imp-{i:03d}", async_noop)

        config = bridge.get_hot_path_config()
        assert len(config.approved_improvements) == 3

    @pytest.mark.asyncio
    async def test_deploy_only_approved(self):
        bridge = TwoCircuitBridge()

        async def reject(_result):
            return False, "bad"

        r1 = self._make_result("good")
        r2 = self._make_result("bad")
        bridge.submit_cold_path_result(r1)
        bridge.submit_cold_path_result(r2)

        await bridge.review("good", async_noop)
        await bridge.review("bad", reject)

        deployed = bridge.deploy_approved()
        assert deployed == ["good"]
        assert bridge.rejected_count == 1


async def async_noop(_result=None):
    return True, "ok"
