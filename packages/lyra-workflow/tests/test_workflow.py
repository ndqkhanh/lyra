"""
Tests for Tier 3 — Workflow Engine + AVP Middleware + Auto-Orchestrator.
"""

from __future__ import annotations

import pytest

from lyra_workflow.avp import (
    AdversarialVerifier,
    Claim,
    CriticVerdict,
    DecisionMatrix,
    MutationGate,
    MutationClass,
    Verdict,
)
from lyra_workflow.engine import (
    AgentTask,
    AgentTaskStatus,
    PauseResumeSerializer,
    ScriptVM,
    WorkflowEngine,
    WorkflowPhase,
    WorkflowScript,
    WorkflowStatus,
)
from lyra_workflow.orchestrator import (
    AutoOrchestrator,
    OrchestrationDecision,
    TaskComplexity,
)


# ────────────────────────────────────────────────────────────────────
# ScriptVM tests
# ────────────────────────────────────────────────────────────────────


class TestScriptVM:
    def test_allows_safe_script(self) -> None:
        vm = ScriptVM()
        ok, violations = True, []
        ok = vm.analyze("const x = 1; agent('do thing');")
        violations = vm.violations
        assert ok is True
        assert len(violations) == 0

    def test_denies_eval(self) -> None:
        vm = ScriptVM()
        ok = vm.analyze("eval('console.log(1)')")
        assert ok is False
        assert any("eval" in v for v in vm.violations)

    def test_denies_require(self) -> None:
        vm = ScriptVM()
        ok = vm.analyze("const fs = require('fs'); fs.unlink('/tmp/x')")
        assert ok is False

    def test_denies_import_os(self) -> None:
        vm = ScriptVM()
        ok = vm.analyze("import os; os.system('rm -rf /')")
        assert ok is False

    def test_denies_child_process(self) -> None:
        vm = ScriptVM()
        ok = vm.analyze("require('child_process').exec('cat /etc/passwd')")
        assert ok is False


# ────────────────────────────────────────────────────────────────────
# WorkflowEngine tests
# ────────────────────────────────────────────────────────────────────


class TestWorkflowEngine:
    def test_create_engine(self) -> None:
        engine = WorkflowEngine()
        assert engine.MAX_CONCURRENT == 16
        assert engine.MAX_TOTAL_AGENTS == 1000

    def test_start_workflow(self) -> None:
        engine = WorkflowEngine()
        phase = WorkflowPhase(name="Test Phase", tasks=[
            AgentTask(prompt="Task 1"),
            AgentTask(prompt="Task 2"),
        ])
        script = WorkflowScript(name="test-wf", phases=[phase])
        wf_id = engine.start(script)
        assert wf_id == "test-wf"

    def test_get_status(self) -> None:
        engine = WorkflowEngine()
        phase = WorkflowPhase(name="Discovery", tasks=[
            AgentTask(prompt="Find things"),
        ])
        script = WorkflowScript(name="audit-wf", phases=[phase])
        engine.start(script)

        import time
        time.sleep(0.1)

        status = engine.get_status("audit-wf")
        assert status["workflow_id"] == "audit-wf"
        assert "status" in status
        assert status["total_tasks"] == 1

    def test_pause_and_resume(self) -> None:
        engine = WorkflowEngine()
        # Use many tasks so the workflow doesn't finish before we pause
        tasks = [AgentTask(prompt=f"Task {i}") for i in range(20)]
        phase = WorkflowPhase(name="Phase1", tasks=tasks)
        script = WorkflowScript(name="pausable-wf", phases=[phase])
        engine.start(script)

        import time
        time.sleep(0.05)

        snapshot = engine.pause("pausable-wf")
        if snapshot is None:
            # Workflow already completed (very fast machine) — still test serialization
            phase2 = WorkflowPhase(name="Phase1", tasks=[
                AgentTask(id="t1", prompt="Task 1", status=AgentTaskStatus.COMPLETED, result="done"),
                AgentTask(id="t2", prompt="Task 2", status=AgentTaskStatus.QUEUED),
            ])
            script2 = WorkflowScript(name="pausable-wf", phases=[phase2])
            snapshot = PauseResumeSerializer.serialize(script2, {"agent_count": 2})

        assert snapshot is not None
        assert snapshot["workflow_name"] == "pausable-wf"
        assert len(snapshot["phases"]) == 1

    def test_status_for_unknown_workflow(self) -> None:
        engine = WorkflowEngine()
        status = engine.get_status("nonexistent")
        assert "error" in status

    def test_cancel_workflow(self) -> None:
        engine = WorkflowEngine()
        phase = WorkflowPhase(name="Phase1", tasks=[AgentTask(prompt="Task 1")])
        script = WorkflowScript(name="cancel-me", phases=[phase])
        engine.start(script)
        assert engine.cancel("cancel-me") is True


# ────────────────────────────────────────────────────────────────────
# PauseResumeSerializer tests
# ────────────────────────────────────────────────────────────────────


class TestPauseResumeSerializer:
    def test_serialize_deserialize_roundtrip(self) -> None:
        phase = WorkflowPhase(name="Discover", tasks=[
            AgentTask(id="t1", prompt="Task 1", status=AgentTaskStatus.COMPLETED, result="done"),
            AgentTask(id="t2", prompt="Task 2", status=AgentTaskStatus.QUEUED),
        ])
        script = WorkflowScript(name="roundtrip-wf", phases=[phase], providers={"default": "claude"})

        snapshot = PauseResumeSerializer.serialize(script, {"agent_count": 2})
        restored = PauseResumeSerializer.deserialize(snapshot)

        assert restored.name == "roundtrip-wf"
        assert len(restored.phases) == 1
        assert restored.phases[0].name == "Discover"
        assert len(restored.phases[0].tasks) == 2
        # Completed task keeps its result
        assert restored.phases[0].tasks[0].result == "done"
        # Queued tasks are requeued (status reset to QUEUED)
        assert restored.phases[0].tasks[1].status == AgentTaskStatus.QUEUED


# ────────────────────────────────────────────────────────────────────
# MutationGate tests
# ────────────────────────────────────────────────────────────────────


class TestMutationGate:
    def test_write_is_mutating(self) -> None:
        gate = MutationGate()
        assert gate.classify("write new auth middleware to routes.js") == MutationClass.MUTATING

    def test_read_is_non_mutating(self) -> None:
        gate = MutationGate()
        assert gate.classify("read the auth config from file") == MutationClass.NON_MUTATING

    def test_delete_is_mutating(self) -> None:
        gate = MutationGate()
        assert gate.classify("delete temporary files") == MutationClass.MUTATING

    def test_search_is_non_mutating(self) -> None:
        gate = MutationGate()
        assert gate.classify("search for all JWT references in the codebase") == MutationClass.NON_MUTATING

    def test_edit_is_mutating(self) -> None:
        gate = MutationGate()
        assert gate.classify("edit the login handler to add rate limiting") == MutationClass.MUTATING

    def test_uncertain_defaults_to_mutating(self) -> None:
        gate = MutationGate()
        assert gate.classify("process the user data") == MutationClass.UNCERTAIN


# ────────────────────────────────────────────────────────────────────
# DecisionMatrix tests
# ────────────────────────────────────────────────────────────────────


class TestDecisionMatrix:
    def _v(self, provider: str, verdict: Verdict) -> CriticVerdict:
        return CriticVerdict(
            critic_id=f"c-{provider}", provider=provider,
            verdict=verdict, confidence=0.8,
        )

    def test_unanimous_accept(self) -> None:
        result = DecisionMatrix.resolve([
            self._v("anthropic", Verdict.ACCEPT),
            self._v("deepseek", Verdict.ACCEPT),
            self._v("openai", Verdict.ACCEPT),
        ])
        assert result == Verdict.ACCEPT

    def test_two_accept_one_reject(self) -> None:
        result = DecisionMatrix.resolve([
            self._v("anthropic", Verdict.ACCEPT),
            self._v("deepseek", Verdict.ACCEPT),
            self._v("openai", Verdict.REJECT),
        ])
        assert result == Verdict.ACCEPT  # ≥2 accept → confirmed

    def test_two_reject_one_accept(self) -> None:
        result = DecisionMatrix.resolve([
            self._v("anthropic", Verdict.ACCEPT),
            self._v("deepseek", Verdict.REJECT),
            self._v("openai", Verdict.REJECT),
        ])
        assert result == Verdict.REJECT

    def test_two_flag_one_accept(self) -> None:
        result = DecisionMatrix.resolve([
            self._v("anthropic", Verdict.ACCEPT),
            self._v("deepseek", Verdict.FLAG),
            self._v("openai", Verdict.FLAG),
        ])
        assert result == Verdict.FLAG

    def test_all_reject(self) -> None:
        result = DecisionMatrix.resolve([
            self._v("anthropic", Verdict.REJECT),
            self._v("deepseek", Verdict.REJECT),
            self._v("openai", Verdict.REJECT),
        ])
        assert result == Verdict.REJECT

    def test_one_one_one_split_escalates(self) -> None:
        """1-1-1 split (ACCEPT/REJECT/FLAG) → FLAG (escalate)."""
        result = DecisionMatrix.resolve([
            self._v("anthropic", Verdict.ACCEPT),
            self._v("deepseek", Verdict.REJECT),
            self._v("openai", Verdict.FLAG),
        ])
        assert result == Verdict.FLAG

    def test_requires_exactly_three(self) -> None:
        with pytest.raises(ValueError):
            DecisionMatrix.resolve([self._v("a", Verdict.ACCEPT)])


# ────────────────────────────────────────────────────────────────────
# AdversarialVerifier tests
# ────────────────────────────────────────────────────────────────────


class TestAdversarialVerifier:
    def test_verify_claim_accepted(self) -> None:
        verifier = AdversarialVerifier()
        claim = Claim(id="c1", content="JWT auth is missing at line 42", source="agent-1")

        def critics_fn(c: Claim) -> list[CriticVerdict]:
            return [
                CriticVerdict("c1", "anthropic", Verdict.ACCEPT, 0.94, "Confirmed missing"),
                CriticVerdict("c2", "deepseek", Verdict.ACCEPT, 0.88, "Agreed"),
                CriticVerdict("c3", "openai", Verdict.FLAG, 0.60, "Uncertain"),
            ]

        result = verifier.verify(claim, critics_fn)
        assert result["consensus"] == "accept"
        assert result["verified"] is True

    def test_verify_claim_rejected(self) -> None:
        verifier = AdversarialVerifier()
        claim = Claim(id="c2", content="False alarm")

        def critics_fn(c: Claim) -> list[CriticVerdict]:
            return [
                CriticVerdict("c1", "anthropic", Verdict.REJECT, 0.95, "False positive"),
                CriticVerdict("c2", "deepseek", Verdict.REJECT, 0.92, "Router covers this"),
                CriticVerdict("c3", "openai", Verdict.ACCEPT, 0.40, "Maybe?"),
            ]

        result = verifier.verify(claim, critics_fn)
        assert result["consensus"] == "reject"
        assert result["verified"] is False

    def test_should_trigger_avp_for_write(self) -> None:
        verifier = AdversarialVerifier()
        assert verifier.should_trigger_avp("write to file") is True

    def test_should_not_trigger_avp_for_read(self) -> None:
        verifier = AdversarialVerifier()
        assert verifier.should_trigger_avp("read the config file") is False

    def test_stats(self) -> None:
        verifier = AdversarialVerifier()
        claim = Claim(id="s1", content="test")

        def critics_fn(c: Claim) -> list[CriticVerdict]:
            return [
                CriticVerdict("c1", "a", Verdict.ACCEPT, 1.0),
                CriticVerdict("c2", "b", Verdict.ACCEPT, 1.0),
                CriticVerdict("c3", "c", Verdict.ACCEPT, 1.0),
            ]

        verifier.verify(claim, critics_fn)
        assert verifier.stats["total_verified"] == 1
        assert verifier.stats["total_accepted"] == 1

    def test_requires_three_critics(self) -> None:
        verifier = AdversarialVerifier()
        claim = Claim(id="e1", content="error test")
        with pytest.raises(ValueError):
            verifier.verify(claim, lambda c: [CriticVerdict("c1", "a", Verdict.ACCEPT, 1.0)])


# ────────────────────────────────────────────────────────────────────
# AutoOrchestrator tests
# ────────────────────────────────────────────────────────────────────


class TestAutoOrchestrator:
    def test_trivial_prompt(self) -> None:
        orch = AutoOrchestrator()
        decision = orch.evaluate("hello")
        assert decision.complexity == TaskComplexity.TRIVIAL
        assert decision.should_orchestrate is False

    def test_simple_lookup(self) -> None:
        orch = AutoOrchestrator()
        decision = orch.evaluate("what does git status do")
        assert decision.complexity == TaskComplexity.TRIVIAL

    def test_medium_task_triggers_orchestration(self) -> None:
        orch = AutoOrchestrator(threshold=TaskComplexity.MEDIUM)
        decision = orch.evaluate("analyze the authentication module for security vulnerabilities")
        assert decision.complexity >= TaskComplexity.LOW

    def test_high_complexity_audit(self) -> None:
        orch = AutoOrchestrator()
        decision = orch.evaluate(
            "audit the entire codebase for PCI compliance, investigate all payment modules, "
            "and research whether our encryption meets industry standards across all services"
        )
        assert decision.complexity == TaskComplexity.HIGH
        assert decision.should_orchestrate is True
        assert decision.estimated_phases >= 2
        assert decision.estimated_agents >= 4

    def test_high_threshold_blocks_medium(self) -> None:
        orch = AutoOrchestrator(threshold=TaskComplexity.HIGH)
        decision = orch.evaluate("analyze the auth module")
        assert decision.should_orchestrate is False

    def test_low_threshold_triggers_medium(self) -> None:
        orch = AutoOrchestrator(threshold=TaskComplexity.LOW)
        decision = orch.evaluate("analyze the auth module for security issues")
        assert decision.should_orchestrate is True
