"""Tests for DynamicWorkflowEngine — runtime workflow generation and execution."""

import pytest
from lyra_core.orchestration.dynamic_workflow import (
    DynamicWorkflowEngine,
    StepKind,
    StepStatus,
    WorkflowContext,
    WorkflowStep,
)


class TestWorkflowStep:
    """Unit tests for WorkflowStep model."""

    def test_step_creation(self):
        step = WorkflowStep(id="analyze", kind=StepKind.TASK,
                           description="Analyze requirements")
        assert step.id == "analyze"
        assert step.kind == StepKind.TASK
        assert step.status == StepStatus.PENDING

    def test_lifecycle_transitions(self):
        step = WorkflowStep(id="test", kind=StepKind.TASK)
        step.mark_running()
        assert step.status == StepStatus.RUNNING
        assert step.started_at is not None

        step.mark_completed("output")
        assert step.status == StepStatus.COMPLETED
        assert step.output == "output"

    def test_failure_transition(self):
        step = WorkflowStep(id="test", kind=StepKind.TASK)
        step.mark_failed("error message")
        assert step.status == StepStatus.FAILED
        assert step.error == "error message"

    def test_skip_transition(self):
        step = WorkflowStep(id="test", kind=StepKind.TASK)
        step.mark_skipped()
        assert step.status == StepStatus.SKIPPED

    def test_elapsed_returns_zero_before_start(self):
        step = WorkflowStep(id="test", kind=StepKind.TASK)
        assert step.elapsed_s == 0.0

    def test_dependencies_list(self):
        step = WorkflowStep(id="test", kind=StepKind.TASK,
                           depends_on=["analyze", "implement"])
        assert "analyze" in step.depends_on
        assert "implement" in step.depends_on


class TestWorkflowContext:
    """Unit tests for WorkflowContext."""

    def test_context_creation(self):
        ctx = WorkflowContext(workflow_id="wf1", task="Build API")
        assert ctx.workflow_id == "wf1"
        assert ctx.task == "Build API"
        assert ctx.all_complete is True  # No steps = all complete

    def test_get_step(self):
        ctx = WorkflowContext(workflow_id="wf1", task="test",
                             steps=[WorkflowStep(id="s1", kind=StepKind.TASK)])
        assert ctx.get_step("s1") is not None
        assert ctx.get_step("nonexistent") is None

    def test_pending_steps(self):
        ctx = WorkflowContext(workflow_id="wf1", task="test", steps=[
            WorkflowStep(id="s1", kind=StepKind.TASK),
            WorkflowStep(id="s2", kind=StepKind.TASK,
                        status=StepStatus.COMPLETED),
        ])
        pending = ctx.pending_steps()
        assert len(pending) == 1
        assert pending[0].id == "s1"

    def test_all_complete_with_mixed_status(self):
        ctx = WorkflowContext(workflow_id="wf1", task="test", steps=[
            WorkflowStep(id="s1", kind=StepKind.TASK),
            WorkflowStep(id="s2", kind=StepKind.TASK,
                        status=StepStatus.COMPLETED),
        ])
        assert ctx.all_complete is False

    def test_variables_store_outputs(self):
        ctx = WorkflowContext(workflow_id="wf1", task="test")
        ctx.variables["analyze"] = "analysis result"
        assert ctx.variables["analyze"] == "analysis result"


class TestDynamicWorkflowEngine:
    """Tests for DynamicWorkflowEngine."""

    def test_create_workflow_generates_steps(self):
        engine = DynamicWorkflowEngine()
        ctx = engine.create_workflow("Build a REST API")
        assert ctx.workflow_id.startswith("wf_")
        assert len(ctx.steps) >= 3
        step_ids = {s.id for s in ctx.steps}
        assert "analyze" in step_ids
        assert "implement" in step_ids
        assert "test" in step_ids

    def test_dependencies_met(self):
        engine = DynamicWorkflowEngine()
        ctx = WorkflowContext(workflow_id="wf1", task="test", steps=[
            WorkflowStep(id="dep", kind=StepKind.TASK, status=StepStatus.COMPLETED),
            WorkflowStep(id="target", kind=StepKind.TASK, depends_on=["dep"]),
        ])
        target = ctx.get_step("target")
        assert engine._dependencies_met(target, ctx) is True

    def test_dependencies_not_met(self):
        engine = DynamicWorkflowEngine()
        ctx = WorkflowContext(workflow_id="wf1", task="test", steps=[
            WorkflowStep(id="dep", kind=StepKind.TASK, status=StepStatus.PENDING),
            WorkflowStep(id="target", kind=StepKind.TASK, depends_on=["dep"]),
        ])
        target = ctx.get_step("target")
        assert engine._dependencies_met(target, ctx) is False

    def test_dependency_failed_blocks(self):
        engine = DynamicWorkflowEngine()
        ctx = WorkflowContext(workflow_id="wf1", task="test", steps=[
            WorkflowStep(id="dep", kind=StepKind.TASK, status=StepStatus.FAILED),
            WorkflowStep(id="target", kind=StepKind.TASK, depends_on=["dep"]),
        ])
        target = ctx.get_step("target")
        assert engine._dependencies_met(target, ctx) is False

    @pytest.mark.asyncio
    async def test_execute_runs_steps_in_order(self):
        engine = DynamicWorkflowEngine()
        ctx = engine.create_workflow("Test task")

        executed = []
        async def executor(step, ctx):
            executed.append(step.id)
            return f"result_{step.id}"

        events = []
        async for event in engine.execute(ctx, executor):
            events.append(event)

        assert len(executed) >= 3
        assert executed[0] == "analyze"
        assert events[-1]["event"] == "workflow_complete"

    @pytest.mark.asyncio
    async def test_execute_handles_retry(self):
        engine = DynamicWorkflowEngine()
        ctx = WorkflowContext(workflow_id="wf1", task="test", steps=[
            WorkflowStep(id="flaky", kind=StepKind.TASK, max_retries=1),
        ])

        call_count = [0]
        async def executor(step, ctx):
            call_count[0] += 1
            if call_count[0] < 2:
                raise RuntimeError("transient failure")
            return "success"

        events = []
        async for event in engine.execute(ctx, executor):
            events.append(event)

        retries = [e for e in events if e["event"] == "step_retry"]
        assert len(retries) == 1
        assert ctx.get_step("flaky").status == StepStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_marks_failed_after_max_retries(self):
        engine = DynamicWorkflowEngine()
        ctx = WorkflowContext(workflow_id="wf1", task="test", steps=[
            WorkflowStep(id="broken", kind=StepKind.TASK, max_retries=1),
        ])

        async def executor(step, ctx):
            raise RuntimeError("persistent failure")

        events = []
        async for event in engine.execute(ctx, executor):
            events.append(event)

        assert ctx.get_step("broken").status == StepStatus.FAILED

    def test_checkpoint_creates_marker(self):
        engine = DynamicWorkflowEngine()
        ctx = engine.create_workflow("Test")

        step_id = engine.checkpoint(ctx)
        assert step_id.startswith("checkpoint_")
        assert ctx.checkpoint_step_id == step_id

    def test_resume_from_checkpoint(self):
        engine = DynamicWorkflowEngine()
        ctx = engine.create_workflow("Test")

        # Mark analyze as completed
        ctx.get_step("analyze").mark_completed("done")
        engine.checkpoint(ctx)

        pending = engine.resume_from_checkpoint(ctx)
        pending_ids = {s.id for s in pending}
        assert "analyze" not in pending_ids
        assert "implement" in pending_ids

    def test_get_workflow_retrieves_by_id(self):
        engine = DynamicWorkflowEngine()
        ctx = engine.create_workflow("Test")
        assert engine.get_workflow(ctx.workflow_id) is ctx
        assert engine.get_workflow("nonexistent") is None
