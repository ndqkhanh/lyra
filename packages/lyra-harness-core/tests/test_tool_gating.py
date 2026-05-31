"""Tests for State-Machine Tool Gating per Workflow Phase (P1-X)."""
from __future__ import annotations

import pytest

from lyra_harness_core.tool_gating import (
    PhaseDef,
    PhaseStateMachine,
    Transition,
    WorkflowPhase,
    build_readonly_workflow,
    build_standard_workflow,
)


# ---------------------------------------------------------------------------
# WorkflowPhase
# ---------------------------------------------------------------------------


class TestWorkflowPhase:
    def test_values(self):
        assert WorkflowPhase.INIT.value == "init"
        assert WorkflowPhase.PLANNING.value == "planning"
        assert WorkflowPhase.RESEARCH.value == "research"
        assert WorkflowPhase.EXECUTION.value == "execution"
        assert WorkflowPhase.VERIFICATION.value == "verification"
        assert WorkflowPhase.REVIEW.value == "review"
        assert WorkflowPhase.COMPLETE.value == "complete"
        assert WorkflowPhase.ERROR.value == "error"

    def test_count(self):
        assert len(WorkflowPhase) == 8


# ---------------------------------------------------------------------------
# Transition
# ---------------------------------------------------------------------------


class TestTransition:
    def test_basic(self):
        t = Transition(
            name="begin_planning",
            from_phase=WorkflowPhase.INIT,
            to_phase=WorkflowPhase.PLANNING,
        )
        assert t.name == "begin_planning"
        assert t.from_phase == WorkflowPhase.INIT
        assert t.to_phase == WorkflowPhase.PLANNING
        assert t.description == ""

    def test_with_description(self):
        t = Transition(
            name="recover",
            from_phase=WorkflowPhase.ERROR,
            to_phase=WorkflowPhase.PLANNING,
            description="Recover from error",
        )
        assert t.description == "Recover from error"

    def test_frozen(self):
        t = Transition(name="x", from_phase=WorkflowPhase.INIT, to_phase=WorkflowPhase.PLANNING)
        with pytest.raises(Exception):
            t.name = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PhaseDef
# ---------------------------------------------------------------------------


class TestPhaseDef:
    def test_minimal(self):
        pd = PhaseDef(phase=WorkflowPhase.INIT)
        assert pd.phase == WorkflowPhase.INIT
        assert pd.allowed_tools is None  # None = all tools allowed
        assert pd.required_tools == frozenset()
        assert pd.max_tool_calls == 0
        assert pd.description == ""

    def test_with_tools(self):
        pd = PhaseDef(
            phase=WorkflowPhase.PLANNING,
            allowed_tools=frozenset(["read", "search"]),
            required_tools=frozenset(["read"]),
            max_tool_calls=10,
            description="Planning phase",
        )
        assert "read" in pd.allowed_tools
        assert "search" in pd.allowed_tools
        assert "read" in pd.required_tools
        assert pd.max_tool_calls == 10
        assert pd.description == "Planning phase"

    def test_frozen(self):
        pd = PhaseDef(phase=WorkflowPhase.INIT)
        with pytest.raises(Exception):
            pd.phase = WorkflowPhase.PLANNING  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PhaseStateMachine — Phase Management
# ---------------------------------------------------------------------------


class TestPhaseStateMachinePhaseManagement:
    @pytest.fixture
    def sm(self):
        return PhaseStateMachine()

    def test_initial_phase(self, sm):
        assert sm.current_phase == WorkflowPhase.INIT

    def test_add_phase(self, sm):
        sm.add_phase(WorkflowPhase.PLANNING, allowed_tools={"read", "search"})
        pd = sm.get_phase_def(WorkflowPhase.PLANNING)
        assert pd is not None
        assert "read" in pd.allowed_tools

    def test_add_phase_all_params(self, sm):
        sm.add_phase(
            WorkflowPhase.EXECUTION,
            allowed_tools={"write", "bash"},
            required_tools={"read"},
            max_tool_calls=5,
            description="Run stuff",
        )
        pd = sm.get_phase_def(WorkflowPhase.EXECUTION)
        assert pd.required_tools == frozenset(["read"])
        assert pd.max_tool_calls == 5
        assert pd.description == "Run stuff"

    def test_get_phase_def_none(self, sm):
        assert sm.get_phase_def(WorkflowPhase.PLANNING) is None

    def test_phase_count(self, sm):
        assert sm.phase_count == 0
        sm.add_phase(WorkflowPhase.INIT)
        sm.add_phase(WorkflowPhase.PLANNING)
        assert sm.phase_count == 2


# ---------------------------------------------------------------------------
# PhaseStateMachine — Transitions
# ---------------------------------------------------------------------------


class TestPhaseStateMachineTransitions:
    @pytest.fixture
    def sm(self):
        sm = PhaseStateMachine()
        sm.add_phase(WorkflowPhase.INIT)
        sm.add_phase(WorkflowPhase.PLANNING, allowed_tools={"read"})
        sm.add_phase(WorkflowPhase.EXECUTION, allowed_tools={"read", "write"})
        sm.add_transition("begin_planning", WorkflowPhase.INIT, WorkflowPhase.PLANNING)
        sm.add_transition("begin_execution", WorkflowPhase.PLANNING, WorkflowPhase.EXECUTION)
        sm.add_transition("back_to_planning", WorkflowPhase.EXECUTION, WorkflowPhase.PLANNING)
        sm.start(WorkflowPhase.INIT)
        return sm

    def test_transition_success(self, sm):
        assert sm.transition("begin_planning")
        assert sm.current_phase == WorkflowPhase.PLANNING

    def test_transition_invalid_name(self, sm):
        assert not sm.transition("nonexistent")
        assert sm.current_phase == WorkflowPhase.INIT

    def test_transition_wrong_phase(self, sm):
        assert not sm.transition("begin_execution")  # needs PLANNING, currently INIT
        assert sm.current_phase == WorkflowPhase.INIT

    def test_phase_history(self, sm):
        sm.transition("begin_planning")
        sm.transition("begin_execution")
        assert sm.phase_history == [WorkflowPhase.INIT, WorkflowPhase.PLANNING]

    def test_available_transitions(self, sm):
        transitions = sm.available_transitions()
        assert len(transitions) == 1
        assert transitions[0].name == "begin_planning"

    def test_transition_names(self, sm):
        assert sm.transition_names() == ["begin_planning"]

    def test_can_transition(self, sm):
        assert sm.can_transition("begin_planning")
        assert not sm.can_transition("nonexistent")
        assert not sm.can_transition("begin_execution")

    def test_reset_tool_count_on_transition(self, sm):
        sm.add_phase(WorkflowPhase.PLANNING, max_tool_calls=3)
        sm.transition("begin_planning")
        sm.record_tool_call("read")
        sm.record_tool_call("read")
        assert sm.tool_calls_this_phase == 2
        sm.transition("begin_execution")
        assert sm.tool_calls_this_phase == 0

    def test_start(self, sm):
        sm.start(WorkflowPhase.EXECUTION)
        assert sm.current_phase == WorkflowPhase.EXECUTION
        assert sm.phase_history == []
        assert sm.tool_calls_this_phase == 0

    def test_reset(self, sm):
        sm.transition("begin_planning")
        sm.reset()
        assert sm.current_phase == WorkflowPhase.INIT
        assert sm.phase_history == []

    def test_transition_count(self, sm):
        assert sm.transition_count == 3


# ---------------------------------------------------------------------------
# PhaseStateMachine — Guards
# ---------------------------------------------------------------------------


class TestPhaseStateMachineGuards:
    @pytest.fixture
    def sm(self):
        sm = PhaseStateMachine()
        sm.add_phase(WorkflowPhase.PLANNING)
        sm.add_phase(WorkflowPhase.EXECUTION)

        def require_approval(_sm, ctx):
            return ctx.get("approved", False)

        sm.add_transition(
            "begin_execution",
            WorkflowPhase.PLANNING,
            WorkflowPhase.EXECUTION,
            guard=require_approval,
        )
        sm.start(WorkflowPhase.PLANNING)
        return sm

    def test_guard_blocks(self, sm):
        assert not sm.transition("begin_execution", {"approved": False})
        assert sm.current_phase == WorkflowPhase.PLANNING

    def test_guard_allows(self, sm):
        assert sm.transition("begin_execution", {"approved": True})
        assert sm.current_phase == WorkflowPhase.EXECUTION

    def test_can_transition_with_guard(self, sm):
        assert not sm.can_transition("begin_execution", {"approved": False})
        assert sm.can_transition("begin_execution", {"approved": True})

    def test_guard_receives_state_machine(self, sm):
        captured = {}

        def guard(machine, _ctx):
            captured["phase"] = machine.current_phase
            return True

        sm.add_transition("x", WorkflowPhase.EXECUTION, WorkflowPhase.PLANNING, guard=guard)
        sm.transition("begin_execution", {"approved": True})
        sm.transition("x")
        assert captured["phase"] == WorkflowPhase.EXECUTION

    def test_guard_receives_context(self, sm):
        captured = {}

        def guard(_machine, ctx):
            captured["ctx"] = ctx
            return True

        sm.add_transition("x", WorkflowPhase.EXECUTION, WorkflowPhase.PLANNING, guard=guard)
        sm.transition("begin_execution", {"approved": True})
        sm.transition("x", {"key": "value", "num": 42})
        assert captured["ctx"] == {"key": "value", "num": 42}


# ---------------------------------------------------------------------------
# PhaseStateMachine — Tool Gating
# ---------------------------------------------------------------------------


class TestPhaseStateMachineToolGating:
    @pytest.fixture
    def sm(self):
        sm = PhaseStateMachine()
        sm.add_phase(WorkflowPhase.INIT, allowed_tools={"read", "list_files"})
        sm.add_phase(WorkflowPhase.PLANNING, allowed_tools={"read", "search"})
        sm.add_phase(WorkflowPhase.EXECUTION, allowed_tools={"read", "write", "bash"})
        sm.add_phase(WorkflowPhase.COMPLETE, allowed_tools=set())
        sm.add_transition("plan", WorkflowPhase.INIT, WorkflowPhase.PLANNING)
        sm.add_transition("exec", WorkflowPhase.PLANNING, WorkflowPhase.EXECUTION)
        sm.add_transition("done", WorkflowPhase.EXECUTION, WorkflowPhase.COMPLETE)
        sm.start(WorkflowPhase.INIT)
        return sm

    def test_can_use_allowed_tool(self, sm):
        assert sm.can_use_tool("read")
        assert sm.can_use_tool("list_files")

    def test_cannot_use_disallowed_tool(self, sm):
        assert not sm.can_use_tool("write")
        assert not sm.can_use_tool("bash")

    def test_can_use_changes_with_phase(self, sm):
        assert not sm.can_use_tool("write")
        sm.transition("plan")
        assert not sm.can_use_tool("write")
        sm.transition("exec")
        assert sm.can_use_tool("write")

    def test_record_tool_call(self, sm):
        assert sm.record_tool_call("read")
        assert sm.tool_calls_this_phase == 1
        assert sm.total_tool_calls == 1

    def test_record_disallowed_tool(self, sm):
        assert not sm.record_tool_call("write")
        assert sm.tool_calls_this_phase == 0

    def test_max_tool_calls(self, sm):
        sm.add_phase(WorkflowPhase.INIT, allowed_tools={"read"}, max_tool_calls=2)
        sm.start(WorkflowPhase.INIT)
        assert sm.record_tool_call("read")
        assert sm.record_tool_call("read")
        assert not sm.record_tool_call("read")  # limit reached

    def test_max_tool_calls_unlimited(self, sm):
        for _ in range(100):
            assert sm.record_tool_call("read")
        assert sm.tool_calls_this_phase == 100

    def test_allowed_tools_list(self, sm):
        tools = sm.allowed_tools()
        assert "read" in tools
        assert "list_files" in tools
        assert "write" not in tools

    def test_allowed_tools_at_max_calls(self, sm):
        sm.add_phase(WorkflowPhase.INIT, allowed_tools={"read"}, max_tool_calls=1)
        sm.start(WorkflowPhase.INIT)
        assert sm.allowed_tools() == ["read"]
        sm.record_tool_call("read")
        assert sm.allowed_tools() == []

    def test_required_tools(self, sm):
        sm.add_phase(WorkflowPhase.PLANNING, required_tools={"read"})
        sm.transition("plan")
        assert "read" in sm.required_tools()
        assert "search" not in sm.required_tools()

    def test_missing_required_tools(self, sm):
        sm.add_phase(WorkflowPhase.PLANNING, required_tools={"read", "approve"})
        sm.transition("plan")
        missing = sm.missing_required_tools()
        assert "read" in missing
        assert "approve" in missing

    def test_no_explicit_allow_list_allows_all(self, sm):
        sm.add_phase(WorkflowPhase.RESEARCH)  # no allow-list
        sm.add_transition("research", WorkflowPhase.INIT, WorkflowPhase.RESEARCH)
        sm.transition("research")
        assert sm.can_use_tool("any_tool")

    def test_complete_phase_no_tools(self, sm):
        sm.transition("plan")
        sm.transition("exec")
        sm.transition("done")
        assert sm.current_phase == WorkflowPhase.COMPLETE
        assert not sm.can_use_tool("read")
        assert sm.allowed_tools() == []

    def test_no_phase_def_blocks_all(self, sm):
        sm.add_transition("research", WorkflowPhase.INIT, WorkflowPhase.RESEARCH)
        sm.transition("research")
        assert not sm.can_use_tool("anything")


# ---------------------------------------------------------------------------
# PhaseStateMachine — Introspection
# ---------------------------------------------------------------------------


class TestPhaseStateMachineIntrospection:
    @pytest.fixture
    def sm(self):
        sm = PhaseStateMachine()
        sm.add_phase(WorkflowPhase.INIT, allowed_tools={"read"})
        sm.add_phase(WorkflowPhase.PLANNING, allowed_tools={"read", "search"})
        sm.add_transition("plan", WorkflowPhase.INIT, WorkflowPhase.PLANNING)
        sm.start(WorkflowPhase.INIT)
        return sm

    def test_phase_tool_summary(self, sm):
        summary = sm.phase_tool_summary()
        assert summary["current_phase"] == "init"
        assert "read" in summary["allowed_tools"]
        assert summary["tool_calls_this_phase"] == 0
        assert "plan" in summary["available_transitions"]

    def test_phase_tool_summary_after_transition(self, sm):
        sm.transition("plan")
        sm.record_tool_call("read")
        summary = sm.phase_tool_summary()
        assert summary["current_phase"] == "planning"
        assert summary["tool_calls_this_phase"] == 1

    def test_to_dict(self, sm):
        d = sm.to_dict()
        assert d["current_phase"] == "init"
        assert "init" in d["phases"]
        assert d["phases"]["init"]["allowed_tools"] == ["read"]
        assert len(d["transitions"]["init"]) == 1

    def test_to_dict_includes_transition_target(self, sm):
        d = sm.to_dict()
        init_transitions = d["transitions"]["init"]
        assert init_transitions[0]["name"] == "plan"
        assert init_transitions[0]["to"] == "planning"

    def test_phase_history_in_to_dict(self, sm):
        sm.transition("plan")
        d = sm.to_dict()
        assert d["phase_history"] == ["init"]

    def test_empty_allowed_tools(self, sm):
        sm.add_phase(WorkflowPhase.COMPLETE)
        sm.add_transition("done", WorkflowPhase.PLANNING, WorkflowPhase.COMPLETE)
        sm.transition("plan")
        sm.transition("done")
        summary = sm.phase_tool_summary()
        assert summary["allowed_tools"] == []


# ---------------------------------------------------------------------------
# PhaseStateMachine — Edge Cases
# ---------------------------------------------------------------------------


class TestPhaseStateMachineEdgeCases:
    def test_multiple_transitions_from_same_phase(self):
        sm = PhaseStateMachine()
        sm.add_phase(WorkflowPhase.INIT)
        sm.add_phase(WorkflowPhase.PLANNING)
        sm.add_phase(WorkflowPhase.RESEARCH)
        sm.add_transition("to_plan", WorkflowPhase.INIT, WorkflowPhase.PLANNING)
        sm.add_transition("to_research", WorkflowPhase.INIT, WorkflowPhase.RESEARCH)
        sm.start(WorkflowPhase.INIT)

        assert len(sm.transition_names()) == 2
        assert "to_plan" in sm.transition_names()
        assert "to_research" in sm.transition_names()

    def test_transition_to_same_phase(self):
        sm = PhaseStateMachine()
        sm.add_phase(WorkflowPhase.PLANNING)
        sm.add_transition("replan", WorkflowPhase.PLANNING, WorkflowPhase.PLANNING)
        sm.start(WorkflowPhase.PLANNING)
        assert sm.transition("replan")
        assert sm.current_phase == WorkflowPhase.PLANNING
        assert len(sm.phase_history) == 1

    def test_duplicate_transition_names(self):
        sm = PhaseStateMachine()
        sm.add_phase(WorkflowPhase.INIT)
        sm.add_phase(WorkflowPhase.PLANNING)
        sm.add_phase(WorkflowPhase.RESEARCH)
        sm.add_transition("go", WorkflowPhase.INIT, WorkflowPhase.PLANNING)
        sm.add_transition("go", WorkflowPhase.PLANNING, WorkflowPhase.RESEARCH)
        sm.start(WorkflowPhase.INIT)

        assert sm.transition("go")
        assert sm.current_phase == WorkflowPhase.PLANNING
        assert sm.transition("go")
        assert sm.current_phase == WorkflowPhase.RESEARCH

    def test_total_tool_calls_persists_across_phases(self):
        sm = PhaseStateMachine()
        sm.add_phase(WorkflowPhase.INIT, allowed_tools={"read"})
        sm.add_phase(WorkflowPhase.PLANNING, allowed_tools={"read"})
        sm.add_transition("plan", WorkflowPhase.INIT, WorkflowPhase.PLANNING)
        sm.start(WorkflowPhase.INIT)
        sm.record_tool_call("read")
        sm.record_tool_call("read")
        sm.transition("plan")
        sm.record_tool_call("read")
        assert sm.tool_calls_this_phase == 1
        assert sm.total_tool_calls == 3

    def test_can_use_unknown_phase_defaults_false(self):
        sm = PhaseStateMachine()
        assert not sm.can_use_tool("anything")


# ---------------------------------------------------------------------------
# Pre-built: build_standard_workflow
# ---------------------------------------------------------------------------


class TestBuildStandardWorkflow:
    @pytest.fixture
    def sm(self):
        return build_standard_workflow()

    def test_all_phases_registered(self, sm):
        assert sm.phase_count == 8
        for phase in WorkflowPhase:
            assert sm.get_phase_def(phase) is not None

    def test_init_phase_tools(self, sm):
        sm.start(WorkflowPhase.INIT)
        assert sm.can_use_tool("read")
        assert sm.can_use_tool("list_files")
        assert not sm.can_use_tool("write")

    def test_planning_phase_tools(self, sm):
        sm.start(WorkflowPhase.PLANNING)
        assert sm.can_use_tool("read")
        assert sm.can_use_tool("search")
        assert sm.can_use_tool("grep")
        assert not sm.can_use_tool("write")

    def test_execution_phase_tools(self, sm):
        sm.start(WorkflowPhase.EXECUTION)
        assert sm.can_use_tool("write")
        assert sm.can_use_tool("edit")
        assert sm.can_use_tool("bash")

    def test_verification_phase_tools(self, sm):
        sm.start(WorkflowPhase.VERIFICATION)
        assert sm.can_use_tool("read")
        assert sm.can_use_tool("bash")
        assert not sm.can_use_tool("write")

    def test_verification_required_tools(self, sm):
        sm.start(WorkflowPhase.VERIFICATION)
        assert "read" in sm.required_tools()

    def test_complete_phase_no_tools(self, sm):
        sm.start(WorkflowPhase.COMPLETE)
        assert not sm.can_use_tool("read")
        assert not sm.can_use_tool("write")

    def test_error_phase_tools(self, sm):
        sm.start(WorkflowPhase.ERROR)
        assert sm.can_use_tool("read")
        assert sm.can_use_tool("list_files")
        assert not sm.can_use_tool("write")

    def test_full_happy_path(self, sm):
        sm.start(WorkflowPhase.INIT)
        assert sm.transition("begin_planning")
        assert sm.current_phase == WorkflowPhase.PLANNING
        assert sm.transition("begin_research")
        assert sm.current_phase == WorkflowPhase.RESEARCH
        assert sm.transition("begin_execution")
        assert sm.current_phase == WorkflowPhase.EXECUTION
        assert sm.transition("begin_verification")
        assert sm.current_phase == WorkflowPhase.VERIFICATION
        assert sm.transition("begin_review")
        assert sm.current_phase == WorkflowPhase.REVIEW
        assert sm.transition("complete")
        assert sm.current_phase == WorkflowPhase.COMPLETE

    def test_skip_research(self, sm):
        sm.start(WorkflowPhase.PLANNING)
        assert sm.transition("begin_execution")
        assert sm.current_phase == WorkflowPhase.EXECUTION

    def test_skip_review(self, sm):
        sm.start(WorkflowPhase.VERIFICATION)
        assert sm.transition("complete")
        assert sm.current_phase == WorkflowPhase.COMPLETE

    def test_error_recovery(self, sm):
        sm.start(WorkflowPhase.EXECUTION)
        assert sm.transition("to_error")
        assert sm.current_phase == WorkflowPhase.ERROR
        assert sm.transition("recover")
        assert sm.current_phase == WorkflowPhase.PLANNING

    def test_back_to_planning_from_research(self, sm):
        sm.start(WorkflowPhase.RESEARCH)
        assert sm.transition("back_to_planning")
        assert sm.current_phase == WorkflowPhase.PLANNING

    def test_back_to_execution_from_verification(self, sm):
        sm.start(WorkflowPhase.VERIFICATION)
        assert sm.transition("back_to_execution")
        assert sm.current_phase == WorkflowPhase.EXECUTION

    def test_error_from_verification(self, sm):
        sm.start(WorkflowPhase.VERIFICATION)
        assert sm.transition("to_error")
        assert sm.current_phase == WorkflowPhase.ERROR

    def test_transition_count(self, sm):
        assert sm.transition_count == 13

    def test_tools_per_phase_by_phase(self, sm):
        """Verify tools don't leak between phases."""
        sm.start(WorkflowPhase.PLANNING)
        assert not sm.can_use_tool("write")
        sm.transition("begin_execution")
        assert sm.can_use_tool("write")


# ---------------------------------------------------------------------------
# Pre-built: build_readonly_workflow
# ---------------------------------------------------------------------------


class TestBuildReadonlyWorkflow:
    @pytest.fixture
    def sm(self):
        return build_readonly_workflow()

    def test_phase_count(self, sm):
        assert sm.phase_count == 3

    def test_no_write_tools_ever(self, sm):
        for phase in [WorkflowPhase.PLANNING, WorkflowPhase.EXECUTION, WorkflowPhase.VERIFICATION]:
            sm.start(phase)
            assert not sm.can_use_tool("write")
            assert not sm.can_use_tool("edit")
            assert not sm.can_use_tool("bash")

    def test_planning_tools(self, sm):
        sm.start(WorkflowPhase.PLANNING)
        assert sm.can_use_tool("read")
        assert sm.can_use_tool("search")
        assert sm.can_use_tool("grep")

    def test_execution_tools(self, sm):
        sm.start(WorkflowPhase.EXECUTION)
        assert sm.can_use_tool("web_search")
        assert sm.can_use_tool("web_fetch")

    def test_verification_tools(self, sm):
        sm.start(WorkflowPhase.VERIFICATION)
        assert sm.can_use_tool("read")
        assert sm.can_use_tool("grep")
        assert not sm.can_use_tool("web_search")

    def test_transitions(self, sm):
        sm.start(WorkflowPhase.PLANNING)
        assert sm.transition("plan")
        assert sm.current_phase == WorkflowPhase.EXECUTION
        assert sm.transition("verify")
        assert sm.current_phase == WorkflowPhase.VERIFICATION

    def test_replan(self, sm):
        sm.start(WorkflowPhase.VERIFICATION)
        assert sm.transition("replan")
        assert sm.current_phase == WorkflowPhase.PLANNING

    def test_complete(self, sm):
        sm.start(WorkflowPhase.VERIFICATION)
        assert sm.transition("complete")
        assert sm.current_phase == WorkflowPhase.COMPLETE


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------


class TestToolGatingIntegration:
    def test_workflow_with_tool_enforcement(self):
        sm = build_standard_workflow()
        sm.start(WorkflowPhase.INIT)

        # Phase: INIT — only read/list_files
        assert sm.record_tool_call("read")
        assert sm.record_tool_call("list_files")
        assert not sm.record_tool_call("write")

        # Transition to PLANNING
        sm.transition("begin_planning")
        assert sm.record_tool_call("read")
        assert sm.record_tool_call("search")
        assert not sm.record_tool_call("bash")

        # Transition to EXECUTION
        sm.transition("begin_execution")
        assert sm.record_tool_call("write")
        assert sm.record_tool_call("bash")
        assert sm.record_tool_call("edit")

        # Transition to VERIFICATION
        sm.transition("begin_verification")
        assert sm.record_tool_call("read")
        assert not sm.record_tool_call("write")
        assert sm.record_tool_call("bash")  # allowed for testing

        # Complete
        sm.transition("begin_review")
        sm.transition("complete")
        assert not sm.record_tool_call("read")

    def test_custom_workflow_with_guard(self):
        sm = PhaseStateMachine()
        sm.add_phase(WorkflowPhase.PLANNING)
        sm.add_phase(WorkflowPhase.EXECUTION, allowed_tools={"write"})

        plan_approved = False

        def approval_guard(_sm, ctx):
            return ctx.get("approved", False)

        sm.add_transition(
            "execute",
            WorkflowPhase.PLANNING,
            WorkflowPhase.EXECUTION,
            guard=approval_guard,
        )
        sm.start(WorkflowPhase.PLANNING)

        # Guard blocks
        assert not sm.transition("execute")
        assert sm.current_phase == WorkflowPhase.PLANNING

        # Approve and retry
        assert sm.transition("execute", {"approved": True})
        assert sm.current_phase == WorkflowPhase.EXECUTION
        assert sm.can_use_tool("write")

    def test_error_recovery_preserves_phase_history(self):
        sm = build_standard_workflow()
        sm.start(WorkflowPhase.INIT)
        sm.transition("begin_planning")
        sm.transition("begin_execution")
        sm.transition("to_error")
        sm.transition("recover")

        assert sm.phase_history == [
            WorkflowPhase.INIT,
            WorkflowPhase.PLANNING,
            WorkflowPhase.EXECUTION,
            WorkflowPhase.ERROR,
        ]
        assert sm.current_phase == WorkflowPhase.PLANNING

    def test_max_tool_calls_per_phase(self):
        sm = PhaseStateMachine()
        sm.add_phase(WorkflowPhase.EXECUTION, allowed_tools={"bash"}, max_tool_calls=3)
        sm.start(WorkflowPhase.EXECUTION)

        assert sm.record_tool_call("bash")
        assert sm.record_tool_call("bash")
        assert sm.record_tool_call("bash")
        assert not sm.record_tool_call("bash")  # exceeded
        assert sm.tool_calls_this_phase == 3
