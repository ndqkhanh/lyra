"""Tests for the Effort-Orchestration Bridge — Tier 1 integration."""

import pytest
from lyra_core.orchestration.effort_bridge import EffortBridge
from lyra_effort.models import EffortLevel
from lyra_workflow.orchestrator import TaskComplexity


class TestEffortBridge:
    """EffortBridge — wires effort level to auto-orchestration trigger."""

    def test_ultracode_triggers_orchestration_for_complex_task(self):
        """ULTRACODE + complex task → orchestration triggered."""
        bridge = EffortBridge(effort_level=EffortLevel.ULTRACODE)
        decision = bridge.evaluate(
            "Audit all auth endpoints for PCI compliance across the codebase"
        )
        assert decision.should_orchestrate
        assert decision.complexity == TaskComplexity.HIGH
        assert decision.estimated_agents >= 8  # Complex tasks need many agents

    def test_high_effort_does_not_trigger(self):
        """HIGH effort should NOT auto-orchestrate."""
        bridge = EffortBridge(effort_level=EffortLevel.HIGH)
        decision = bridge.evaluate(
            "Audit all auth endpoints for PCI compliance"
        )
        assert not decision.should_orchestrate

    def test_simple_task_no_orchestration_even_with_ultracode(self):
        """Simple questions don't trigger orchestration even in ultracode."""
        bridge = EffortBridge(effort_level=EffortLevel.ULTRACODE)
        decision = bridge.evaluate("What is 2+2?")
        assert not decision.should_orchestrate
        assert decision.complexity in (TaskComplexity.TRIVIAL, TaskComplexity.LOW)

    def test_plan_workflow_creates_correct_phases(self):
        """Workflow plan from orchestration decision has correct phases."""
        bridge = EffortBridge(effort_level=EffortLevel.ULTRACODE)
        decision = bridge.evaluate(
            "Audit the entire payment module for PCI compliance across the codebase"
        )
        assert decision.complexity == TaskComplexity.HIGH  # 4 complex keyword matches
        script = bridge.plan_workflow(decision)
        assert len(script.phases) == 3  # HIGH → 3 phases (Discover/Verify/Report)
        assert script.phases[0].name == "Discover"
        assert script.phases[1].name == "Verify"
        assert script.phases[2].name == "Report"

    def test_from_config_factory(self):
        """EffortBridge.from_config() resolves string effort levels."""
        bridge = EffortBridge.from_config("ultracode")
        assert bridge.effort_level == EffortLevel.ULTRACODE
        assert bridge.should_orchestrate(
            "Audit the entire codebase for security vulnerabilities across all endpoints"
        )

        bridge2 = EffortBridge.from_config("low")
        assert not bridge2.should_orchestrate("Audit the entire codebase")

    def test_invalid_effort_falls_back_to_high(self):
        """Invalid effort strings fall back to HIGH (safe default)."""
        bridge = EffortBridge.from_config("nonsense")
        assert bridge.effort_level == EffortLevel.HIGH
        assert not bridge.should_orchestrate("Audit everything")

    def test_medium_task_with_medium_threshold_triggers(self):
        """MEDIUM complexity task triggers orchestration (threshold=M)."""
        bridge = EffortBridge(effort_level=EffortLevel.ULTRACODE)
        # "review, multiple, analyze, several" = 4 medium keyword matches → MEDIUM
        decision = bridge.evaluate(
            "Review and analyze multiple configuration files for several errors"
        )
        assert decision.complexity == TaskComplexity.MEDIUM
        assert decision.should_orchestrate  # MEDIUM >= MEDIUM threshold

    def test_orchestration_disabled_when_not_ultracode(self):
        """XHIGH effort should NOT enable orchestration (only ULTRACODE does)."""
        bridge = EffortBridge(effort_level=EffortLevel.XHIGH)
        decision = bridge.evaluate(
            "Audit all auth endpoints for PCI compliance across the codebase"
        )
        assert not decision.should_orchestrate
