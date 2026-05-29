"""Tests for Phase 10: Integrated Agent."""

from __future__ import annotations

import time

import pytest
from lyra_core.agent.integrated import (
    AgentConfig,
    AgentSafetyContext,
    AgentStatus,
    HaltReason,
    HaltResumeController,
    IntegratedAgent,
)
from lyra_core.agent.loop import AgentLoop, IterationBudget, TurnResult
from lyra_core.experience.anti_pattern import AntiPattern
from lyra_core.safety.governance import (
    PolicyRule,
    PolicyVerdict,
    SafetyPolicy,
)

# ═══════════════════════════════════════════════════════════════════════════════
# HaltReason & AgentStatus
# ═══════════════════════════════════════════════════════════════════════════════


class TestHaltReason:
    def test_values(self):
        assert HaltReason.SAFETY_DENY.value == "safety_deny"
        assert HaltReason.CRASH_LOOP.value == "crash_loop"
        assert HaltReason.MANUAL.value == "manual"
        assert HaltReason.COOLDOWN.value == "cooldown"
        assert HaltReason.RECOVERY_EXHAUSTED.value == "recovery_exhausted"


class TestAgentStatus:
    def test_values(self):
        assert AgentStatus.RUNNING.value == "running"
        assert AgentStatus.HALTED.value == "halted"
        assert AgentStatus.COOLDOWN.value == "cooldown"
        assert AgentStatus.RECOVERING.value == "recovering"
        assert AgentStatus.DEGRADED.value == "degraded"
        assert AgentStatus.STOPPED.value == "stopped"


# ═══════════════════════════════════════════════════════════════════════════════
# AgentConfig
# ═══════════════════════════════════════════════════════════════════════════════


class TestAgentConfig:
    def test_defaults(self):
        config = AgentConfig()
        assert config.max_turns == 100
        assert config.cooldown_seconds == 5.0
        assert config.max_recovery_attempts == 3
        assert config.crash_loop_threshold == 5
        assert config.learning_cycle_interval == 50
        assert config.auto_eval_after_turns == 20
        assert config.block_on_anti_pattern is True
        assert config.safety_strict is False

    def test_custom_config(self):
        config = AgentConfig(
            max_turns=50, cooldown_seconds=10.0,
            crash_loop_threshold=3,
        )
        assert config.max_turns == 50
        assert config.cooldown_seconds == 10.0
        assert config.crash_loop_threshold == 3

    def test_is_frozen(self):
        config = AgentConfig()
        with pytest.raises(Exception):  # noqa: B017
            config.max_turns = 50  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════════════
# AgentSafetyContext
# ═══════════════════════════════════════════════════════════════════════════════


class TestAgentSafetyContext:
    def test_create(self):
        ctx = AgentSafetyContext(
            policy_verdict=PolicyVerdict.ALLOW,
            blocked_tools=(),
            anti_pattern_matches=(),
            last_check_time=time.time(),
        )
        assert ctx.policy_verdict == PolicyVerdict.ALLOW
        assert ctx.blocked_tools == ()
        assert ctx.anti_pattern_matches == ()

    def test_with_blocked_tools(self):
        ctx = AgentSafetyContext(
            policy_verdict=PolicyVerdict.DENY,
            blocked_tools=("exec", "eval"),
            anti_pattern_matches=("hardcoded_secret",),
            last_check_time=time.time(),
        )
        assert ctx.policy_verdict == PolicyVerdict.DENY
        assert "exec" in ctx.blocked_tools
        assert "hardcoded_secret" in ctx.anti_pattern_matches

    def test_is_frozen(self):
        ctx = AgentSafetyContext(
            policy_verdict=PolicyVerdict.ALLOW,
            blocked_tools=(),
            anti_pattern_matches=(),
            last_check_time=time.time(),
        )
        with pytest.raises(Exception):  # noqa: B017
            ctx.policy_verdict = PolicyVerdict.DENY  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════════════
# HaltResumeController
# ═══════════════════════════════════════════════════════════════════════════════


class TestHaltResumeController:
    @pytest.fixture
    def ctrl(self):
        return HaltResumeController()

    def test_initial_state(self, ctrl):
        assert ctrl.status == AgentStatus.RUNNING
        assert ctrl.halt_reason is None
        assert ctrl.is_running() is True
        assert ctrl.is_halted() is False

    def test_halt(self, ctrl):
        ctrl.halt(HaltReason.SAFETY_DENY)
        assert ctrl.status == AgentStatus.HALTED
        assert ctrl.halt_reason == HaltReason.SAFETY_DENY
        assert ctrl.total_halt_count == 1
        assert ctrl.halted_at is not None
        assert ctrl.is_halted() is True
        assert ctrl.is_running() is False

    def test_begin_recovery(self, ctrl):
        ctrl.halt(HaltReason.MANUAL)
        can_recover = ctrl.begin_recovery()
        assert can_recover is True
        assert ctrl.status == AgentStatus.RECOVERING
        assert ctrl.recovery_attempts == 1

    def test_resume_after_recovery(self, ctrl):
        ctrl.halt(HaltReason.MANUAL)
        ctrl.begin_recovery()
        # Force cooldown bypass by clearing halted_at
        ctrl.halted_at = 0
        resumed = ctrl.resume()
        assert resumed is True
        assert ctrl.status == AgentStatus.RUNNING
        assert ctrl.total_resume_count == 1

    def test_resume_without_recovery(self, ctrl):
        assert ctrl.resume() is False

    def test_recovery_exhausted(self, ctrl):
        ctrl.max_recovery_attempts = 2
        ctrl.halt(HaltReason.SAFETY_DENY)
        ctrl.begin_recovery()
        ctrl.resume()

        ctrl.halt(HaltReason.SAFETY_DENY)
        ctrl.begin_recovery()
        ctrl.resume()

        ctrl.halt(HaltReason.SAFETY_DENY)
        can_recover = ctrl.begin_recovery()
        assert can_recover is False
        assert ctrl.status == AgentStatus.STOPPED
        assert ctrl.halt_reason == HaltReason.RECOVERY_EXHAUSTED

    def test_cooldown_not_expired(self, ctrl):
        ctrl.cooldown_seconds = 3600  # 1 hour
        ctrl.halt(HaltReason.MANUAL)
        ctrl.begin_recovery()
        resumed = ctrl.resume()
        assert resumed is False
        assert ctrl.status == AgentStatus.COOLDOWN

    def test_record_crash_no_loop(self, ctrl):
        loop_detected = ctrl.record_crash()
        assert loop_detected is False
        assert ctrl.crash_count == 1

    def test_record_crash_loop_detected(self, ctrl):
        ctrl.crash_loop_threshold = 3
        for _ in range(3):
            ctrl.record_crash()
        assert ctrl.crash_count == 3
        assert ctrl.is_halted() is True
        assert ctrl.halt_reason == HaltReason.CRASH_LOOP

    def test_record_crash_resets_after_window(self, ctrl):
        ctrl.crash_loop_threshold = 3
        ctrl.record_crash()
        ctrl.last_crash_time = 0  # Force reset window
        ctrl.record_crash()
        assert ctrl.crash_count == 1  # Reset because >60s gap

    def test_reset(self, ctrl):
        ctrl.halt(HaltReason.MANUAL)
        ctrl.record_crash()
        ctrl.reset()
        assert ctrl.status == AgentStatus.RUNNING
        assert ctrl.crash_count == 0
        assert ctrl.halt_reason is None
        assert ctrl.recovery_attempts == 0


# ═══════════════════════════════════════════════════════════════════════════════
# IntegratedAgent
# ═══════════════════════════════════════════════════════════════════════════════


class _MockLLM:
    """Echo LLM that returns a simple text response."""

    def generate(self, messages=None, tools=None):  # noqa: ARG002
        return {"content": "I processed your request.", "tool_calls": []}


class _MockStore:
    """No-op store for testing."""

    def start_session(self, session_id): pass  # noqa: B027
    def append_message(self, session_id, role, content, **kwargs): pass  # noqa: B027


def _mock_tool_fn():
    return "ok"


class TestIntegratedAgent:
    @pytest.fixture
    def agent(self):
        loop = AgentLoop(
            llm=_MockLLM(),
            tools={"echo": _mock_tool_fn},
            store=_MockStore(),
            budget=IterationBudget(max=5),
        )
        return IntegratedAgent(loop=loop)

    def test_create(self, agent):
        assert agent.is_running is True
        assert agent.turn_count == 0

    def test_run_conversation(self, agent):
        result = agent.run_conversation("hello", session_id="s1")
        assert result.final_text == "I processed your request."
        assert result.stopped_by == "end_turn"
        assert agent.turn_count == 1

    def test_run_conversation_generates_session_id(self, agent):
        result = agent.run_conversation("hello")
        assert result.final_text is not None

    def test_pre_turn_safety_allows(self, agent):
        ctx = agent._pre_turn_check("safe text", "s1")
        assert ctx.policy_verdict == PolicyVerdict.ALLOW
        assert ctx.blocked_tools == ()

    def test_pre_turn_safety_blocks_anti_pattern(self, agent):
        agent.anti_pattern_registry.register(AntiPattern(
            id="ap1", name="hardcoded_secret",
            description="Test anti-pattern",
            severity="high",
            pattern_source="test",
            detection_rule="api_key",
        ))
        ctx = agent._pre_turn_check("const api_key = 'sk-123'", "s1")
        assert "hardcoded_secret" in ctx.anti_pattern_matches

    def test_policy_deny_halt(self, agent):
        rule = PolicyRule(
            id="r1", name="Block All", description="Block everything",
            condition="run_conversation", verdict=PolicyVerdict.DENY, priority=1,
        )
        policy = SafetyPolicy(
            id="p1", name="BlockPolicy", version="1.0",
            description="Blocks all", rules=(rule,),
        )
        agent.policy_engine.register_policy(policy)
        result = agent.run_conversation("hello", session_id="s1")
        assert result.stopped_by == "safety_deny"
        assert agent.is_halted is True

    def test_halt_and_manual_resume(self, agent):
        agent.halt(HaltReason.MANUAL)
        assert agent.is_halted is True
        # Reset halted_at to bypass cooldown
        agent.halt_controller.halted_at = 0
        assert agent.resume() is True
        assert agent.is_running is True

    def test_halted_result(self, agent):
        agent.halt(HaltReason.MANUAL)
        result = agent._halted_result()
        assert result.stopped_by == "manual"
        assert "halted" in result.final_text

    def test_health_report(self, agent):
        agent.run_conversation("hello", session_id="s1")
        report = agent.health_report()
        assert report["status"] == "running"
        assert report["turn_count"] == 1
        assert "safety_verdict" in report
        assert "policies_active" in report
        assert "anti_patterns_registered" in report
        assert "learning_records_pending" in report
        assert "eval_runs" in report

    def test_health_report_when_halted(self, agent):
        agent.halt(HaltReason.SAFETY_DENY)
        report = agent.health_report()
        assert report["status"] == "halted"

    def test_config_passed_through(self, agent):
        assert agent.config.max_turns == 100
        assert agent.config.block_on_anti_pattern is True

    def test_reset(self, agent):
        agent.run_conversation("hello", session_id="s1")
        agent.halt(HaltReason.MANUAL)
        agent.reset()
        assert agent.turn_count == 0
        assert agent.is_running is True

    def test_turn_count_property(self, agent):
        assert agent.turn_count == 0
        agent.run_conversation("hello", session_id="s1")
        assert agent.turn_count == 1

    def test_post_turn_capture(self, agent):
        result = TurnResult(
            final_text="Done.", iterations=2,
            tool_calls=[{"name": "read", "arguments": {}}],
            stopped_by="end_turn",
        )
        agent._post_turn_capture("do task", result, "s1")
        pending = agent.learning_loop.get_pending_records()
        assert len(pending) >= 1
        assert pending[-1].task_signature == "do task"

    def test_post_turn_capture_failure(self, agent):
        result = TurnResult(
            final_text="Error", iterations=1, stopped_by="budget",
        )
        agent._post_turn_capture("bad task", result, "s1")
        pending = agent.learning_loop.get_pending_records()
        assert len(pending) >= 1
        assert pending[-1].outcome == "failure"

    def test_post_turn_capture_denied(self, agent):
        result = TurnResult(
            final_text="Action denied by safety policy.",
            iterations=0, stopped_by="safety_deny",
        )
        agent._post_turn_capture("dangerous task", result, "s1")
        pending = agent.learning_loop.get_pending_records()
        assert len(pending) >= 1
        assert pending[-1].outcome == "failure"

    def test_is_running_property(self, agent):
        assert agent.is_running is True
        agent.halt(HaltReason.MANUAL)
        assert agent.is_running is False

    def test_is_halted_property(self, agent):
        assert agent.is_halted is False
        agent.halt(HaltReason.MANUAL)
        assert agent.is_halted is True
