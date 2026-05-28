"""Tests for the Phase 2.2 5-Slot Model Router."""
from __future__ import annotations

import pytest
from lyra_core.orchestration.model_router import (
    ModelRouter,
    ModelSlot,
    SlotHealth,
    SlotHealthStatus,
)


class TestModelSlot:
    def test_five_slots_exist(self):
        slots = list(ModelSlot)
        assert len(slots) == 5
        assert ModelSlot.NORMAL in slots
        assert ModelSlot.THINKING in slots
        assert ModelSlot.COMPACT in slots
        assert ModelSlot.CRITIQUE in slots
        assert ModelSlot.VLM in slots


class TestSlotConfig:
    def test_default_configs_have_valid_multipliers(self):
        router = ModelRouter()
        for slot in ModelSlot:
            config = router.slot_configs[slot]
            assert config.cost_multiplier > 0


class TestModelRouter:
    def test_route_implement_task_to_normal(self):
        router = ModelRouter()
        decision = router.route("Implement a login page")
        assert decision.primary_slot == ModelSlot.NORMAL

    def test_route_architect_task_to_thinking(self):
        router = ModelRouter()
        decision = router.route("Design the system architecture")
        assert decision.primary_slot == ModelSlot.THINKING

    def test_route_research_task_to_thinking(self):
        router = ModelRouter()
        decision = router.route("Research best practices for API design")
        assert decision.primary_slot == ModelSlot.THINKING

    def test_route_quick_task_to_compact(self):
        router = ModelRouter()
        decision = router.route("Quick typo fix in README")
        assert decision.primary_slot == ModelSlot.COMPACT

    def test_route_review_task_to_critique(self):
        router = ModelRouter()
        decision = router.route("Review the authentication module")
        assert decision.primary_slot == ModelSlot.CRITIQUE

    def test_route_test_task_to_critique(self):
        router = ModelRouter()
        decision = router.route("Test the login flow")
        assert decision.primary_slot == ModelSlot.CRITIQUE

    def test_route_image_task_to_vlm(self):
        router = ModelRouter()
        decision = router.route("Review this screenshot of the UI")
        assert decision.primary_slot == ModelSlot.VLM

    def test_route_diagram_task_to_vlm(self):
        router = ModelRouter()
        decision = router.route("Analyze this architecture diagram")
        assert decision.primary_slot == ModelSlot.VLM

    def test_require_vision_overrides_task_type(self):
        router = ModelRouter()
        decision = router.route("Implement a login page", require_vision=True)
        assert decision.primary_slot == ModelSlot.VLM

    def test_require_thinking_overrides_task_type(self):
        router = ModelRouter()
        decision = router.route("Quick fix", require_thinking=True)
        assert decision.primary_slot == ModelSlot.THINKING

    def test_preferred_slot_overrides_classification(self):
        router = ModelRouter()
        decision = router.route(
            "Implement a login page", preferred_slot=ModelSlot.THINKING
        )
        assert decision.primary_slot == ModelSlot.THINKING

    def test_budget_constraint_downgrades_expensive_slot(self):
        router = ModelRouter()
        decision = router.route(
            "Design the system architecture", budget_multiplier=1.0
        )
        assert decision.primary_slot != ModelSlot.THINKING

    def test_budget_constraint_respected_for_normal(self):
        router = ModelRouter()
        decision = router.route(
            "Implement a login page", budget_multiplier=1.0
        )
        assert decision.estimated_cost_multiplier <= 1.0

    def test_decision_id_is_unique(self):
        router = ModelRouter()
        d1 = router.route("task a")
        d2 = router.route("task b")
        assert d1.decision_id != d2.decision_id

    def test_decision_includes_reasoning(self):
        router = ModelRouter()
        decision = router.route("Implement auth")
        assert len(decision.reasoning) > 0

    def test_record_success_maintains_health(self):
        router = ModelRouter()
        router.record_slot_result(ModelSlot.NORMAL, success=True, latency_ms=100)
        hs = router.health_status[ModelSlot.NORMAL]
        assert hs.health == SlotHealth.HEALTHY

    def test_record_errors_degrades_slot(self):
        router = ModelRouter()
        for _ in range(3):
            router.record_slot_result(
                ModelSlot.NORMAL, success=False, error="timeout"
            )
        hs = router.health_status[ModelSlot.NORMAL]
        assert hs.health == SlotHealth.DEGRADED

    def test_repeated_errors_make_slot_unavailable(self):
        router = ModelRouter()
        for _ in range(6):
            router.record_slot_result(
                ModelSlot.NORMAL, success=False, error="crash"
            )
        hs = router.health_status[ModelSlot.NORMAL]
        assert hs.health == SlotHealth.UNAVAILABLE

    def test_error_recovery_after_successes(self):
        router = ModelRouter()
        for _ in range(6):
            router.record_slot_result(
                ModelSlot.NORMAL, success=False, error="crash"
            )
        for _ in range(10):
            router.record_slot_result(ModelSlot.NORMAL, success=True, latency_ms=50)
        hs = router.health_status[ModelSlot.NORMAL]
        assert hs.health == SlotHealth.HEALTHY

    def test_unavailable_slot_falls_back(self):
        router = ModelRouter()
        for _ in range(6):
            router.record_slot_result(
                ModelSlot.NORMAL, success=False, error="crash"
            )
        decision = router.route("Implement a login page")
        assert decision.primary_slot != ModelSlot.NORMAL

    def test_all_slots_unavailable_raises(self):
        router = ModelRouter()
        for slot in ModelSlot:
            for _ in range(6):
                router.record_slot_result(slot, success=False, error="down")
        with pytest.raises(RuntimeError):
            router.route("Implement a login page")

    def test_get_healthy_slots(self):
        router = ModelRouter()
        healthy = router.get_healthy_slots()
        assert len(healthy) == 5

    def test_get_cost_estimate(self):
        router = ModelRouter()
        cost = router.get_cost_estimate("Design architecture")
        assert cost > 1.0

    def test_history_accumulates(self):
        router = ModelRouter()
        router.route("task a")
        router.route("task b")
        assert len(router.history) == 2

    def test_reset_health_restores_all(self):
        router = ModelRouter()
        for _ in range(6):
            router.record_slot_result(
                ModelSlot.NORMAL, success=False, error="crash"
            )
        router.reset_health()
        hs = router.health_status[ModelSlot.NORMAL]
        assert hs.health == SlotHealth.HEALTHY


class TestSlotHealthStatus:
    def test_initial_health_is_healthy(self):
        hs = SlotHealthStatus(slot=ModelSlot.NORMAL)
        assert hs.health == SlotHealth.HEALTHY

    def test_single_error_keeps_healthy(self):
        hs = SlotHealthStatus(slot=ModelSlot.NORMAL)
        hs.record_error("timeout")
        assert hs.health == SlotHealth.HEALTHY

    def test_latency_tracking(self):
        hs = SlotHealthStatus(slot=ModelSlot.NORMAL)
        hs.record_success(100)
        hs.record_success(200)
        assert hs.avg_latency_ms > 50
        assert hs.avg_latency_ms < 200
