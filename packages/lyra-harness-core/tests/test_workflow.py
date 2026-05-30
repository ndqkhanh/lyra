"""Tests for workflow.py — Workflow.js Spec (P4-B1 CRITICAL)."""
from __future__ import annotations

import pytest
from lyra_harness_core.workflow import (
    CheckpointConfig,
    DecompositionResult,
    FanOutConfig,
    IsolationMode,
    ResumeStrategy,
    SubTask,
    SubTaskResult,
    SubTaskStatus,
    VerifyConfig,
    WorkflowDAG,
    WorkflowEngine,
    WorkflowResult,
    WorkflowSpec,
    WorkflowStatus,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestSubTaskStatus:
    def test_values(self):
        assert SubTaskStatus.PENDING.value == "pending"
        assert SubTaskStatus.COMPLETED.value == "completed"
        assert SubTaskStatus.FAILED.value == "failed"

class TestIsolationMode:
    def test_values(self):
        assert IsolationMode.WORKTREE.value == "worktree"
        assert IsolationMode.NONE.value == "none"

class TestResumeStrategy:
    def test_values(self):
        assert ResumeStrategy.SKIP_COMPLETED.value == "skip_completed"
        assert ResumeStrategy.RETRY_FAILED.value == "retry_failed"

class TestWorkflowStatus:
    def test_values(self):
        assert WorkflowStatus.COMPLETED.value == "completed"
        assert WorkflowStatus.FAILED.value == "failed"


# ---------------------------------------------------------------------------
# SubTask
# ---------------------------------------------------------------------------

class TestSubTask:
    def test_creation(self):
        st = SubTask(id="t1", agent_type="research", query="Find papers on RLHF")
        assert st.id == "t1"
        assert st.agent_type == "research"
        assert st.query == "Find papers on RLHF"

    def test_defaults(self):
        st = SubTask(id="t2", agent_type="code")
        assert st.query == ""
        assert st.repo == ""
        assert st.system == ""
        assert st.metadata == {}

    def test_with_metadata(self):
        st = SubTask(id="t3", agent_type="architect", metadata={"priority": "high"})
        assert st.metadata["priority"] == "high"

    def test_frozen(self):
        st = SubTask(id="t1", agent_type="code")
        with pytest.raises(Exception):
            st.id = "new"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DecompositionResult
# ---------------------------------------------------------------------------

class TestDecompositionResult:
    def test_creation(self):
        t1 = SubTask(id="a", agent_type="research")
        t2 = SubTask(id="b", agent_type="code")
        dr = DecompositionResult(
            sub_tasks=(t1, t2),
            dependencies={"b": ("a",)},
            description="Two-phase workflow",
        )
        assert dr.subtask_count == 2
        assert dr.dependencies == {"b": ("a",)}

    def test_defaults(self):
        dr = DecompositionResult(sub_tasks=())
        assert dr.subtask_count == 0
        assert dr.dependencies == {}
        assert dr.description == ""

    def test_frozen(self):
        dr = DecompositionResult(sub_tasks=())
        with pytest.raises(Exception):
            dr.description = "new"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# FanOutConfig
# ---------------------------------------------------------------------------

class TestFanOutConfig:
    def test_defaults(self):
        fc = FanOutConfig()
        assert fc.max_concurrency == 12
        assert "research" in fc.agent_types

    def test_custom(self):
        fc = FanOutConfig(
            max_concurrency=4,
            agent_types=("code", "security"),
            isolation=IsolationMode.PROCESS,
        )
        assert fc.max_concurrency == 4
        assert fc.agent_types == ("code", "security")

    def test_frozen(self):
        fc = FanOutConfig()
        with pytest.raises(Exception):
            fc.max_concurrency = 8  # type: ignore[misc]


# ---------------------------------------------------------------------------
# VerifyConfig
# ---------------------------------------------------------------------------

class TestVerifyConfig:
    def test_defaults(self):
        vc = VerifyConfig()
        assert vc.attack_agents == 2
        assert vc.convergence_threshold == 0.9
        assert vc.enabled

    def test_frozen(self):
        vc = VerifyConfig()
        with pytest.raises(Exception):
            vc.max_rounds = 5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CheckpointConfig
# ---------------------------------------------------------------------------

class TestCheckpointConfig:
    def test_defaults(self):
        cc = CheckpointConfig()
        assert cc.after_each == "sub_task"
        assert cc.retention == "30d"
        assert cc.resume_strategy == ResumeStrategy.SKIP_COMPLETED


# ---------------------------------------------------------------------------
# WorkflowSpec
# ---------------------------------------------------------------------------

class TestWorkflowSpec:
    def test_creation(self):
        spec = WorkflowSpec(name="deep-research", description="Multi-agent research")
        assert spec.name == "deep-research"
        assert spec.fan_out.max_concurrency == 12

    def test_with_decomposition(self):
        spec = WorkflowSpec(name="test")
        t1 = SubTask(id="a", agent_type="code")
        dr = DecompositionResult(sub_tasks=(t1,))
        updated = spec.with_decomposition(dr)
        assert updated.decompose_config is not None
        assert updated.decompose_config.subtask_count == 1

    def test_frozen(self):
        spec = WorkflowSpec(name="x")
        with pytest.raises(Exception):
            spec.name = "y"  # type: ignore[misc]

    def test_default_verify_config(self):
        spec = WorkflowSpec(name="x")
        assert spec.verify.enabled
        assert spec.verify.convergence_threshold == 0.9


# ---------------------------------------------------------------------------
# SubTaskResult
# ---------------------------------------------------------------------------

class TestSubTaskResult:
    def test_completed(self):
        r = SubTaskResult(
            subtask_id="t1",
            status=SubTaskStatus.COMPLETED,
            output="done",
            agent_id="research-0",
            duration_ms=123.0,
        )
        assert r.status == SubTaskStatus.COMPLETED
        assert r.output == "done"

    def test_failed(self):
        r = SubTaskResult(
            subtask_id="t2",
            status=SubTaskStatus.FAILED,
            error="timeout",
        )
        assert r.status == SubTaskStatus.FAILED
        assert r.error == "timeout"

    def test_frozen(self):
        r = SubTaskResult(subtask_id="x", status=SubTaskStatus.PENDING)
        with pytest.raises(Exception):
            r.output = "new"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# WorkflowDAG
# ---------------------------------------------------------------------------

class TestWorkflowDAG:
    def test_empty(self):
        dag = WorkflowDAG()
        assert dag.task_count == 0
        assert dag.edge_count == 0

    def test_add_task(self):
        dag = WorkflowDAG()
        dag.add_task(SubTask(id="a", agent_type="code"))
        assert dag.task_count == 1

    def test_add_dependency(self):
        dag = WorkflowDAG()
        dag.add_task(SubTask(id="a", agent_type="code"))
        dag.add_task(SubTask(id="b", agent_type="review"))
        dag.add_dependency("b", "a")
        assert dag.edge_count == 1

    def test_no_cycles(self):
        dag = WorkflowDAG()
        dag.add_task(SubTask(id="a", agent_type="code"))
        dag.add_task(SubTask(id="b", agent_type="review"))
        dag.add_task(SubTask(id="c", agent_type="deploy"))
        dag.add_dependency("b", "a")
        dag.add_dependency("c", "b")
        assert not dag.has_cycles()

    def test_has_cycles(self):
        dag = WorkflowDAG()
        dag.add_task(SubTask(id="a", agent_type="code"))
        dag.add_task(SubTask(id="b", agent_type="review"))
        dag.add_dependency("a", "b")
        dag.add_dependency("b", "a")
        assert dag.has_cycles()

    def test_self_cycle(self):
        dag = WorkflowDAG()
        dag.add_task(SubTask(id="a", agent_type="code"))
        dag.add_dependency("a", "a")
        assert dag.has_cycles()

    def test_topological_order_linear(self):
        dag = WorkflowDAG()
        dag.add_task(SubTask(id="a", agent_type="code"))
        dag.add_task(SubTask(id="b", agent_type="review"))
        dag.add_task(SubTask(id="c", agent_type="deploy"))
        dag.add_dependency("b", "a")
        dag.add_dependency("c", "b")
        waves = dag.topological_order()
        assert len(waves) == 3  # each task in its own wave

    def test_topological_order_parallel(self):
        dag = WorkflowDAG()
        dag.add_task(SubTask(id="a", agent_type="research"))
        dag.add_task(SubTask(id="b", agent_type="code"))
        dag.add_task(SubTask(id="c", agent_type="merge"))
        dag.add_dependency("c", "a")
        dag.add_dependency("c", "b")
        waves = dag.topological_order()
        assert len(waves) == 2  # a,b in wave 0, c in wave 1
        assert len(waves[0]) == 2

    def test_ready_tasks(self):
        dag = WorkflowDAG()
        dag.add_task(SubTask(id="a", agent_type="code"))
        dag.add_task(SubTask(id="b", agent_type="review"))
        dag.add_dependency("b", "a")
        ready = dag.ready_tasks(completed=set())
        assert ready == ("a",)  # only a has no deps

    def test_ready_after_completion(self):
        dag = WorkflowDAG()
        dag.add_task(SubTask(id="a", agent_type="code"))
        dag.add_task(SubTask(id="b", agent_type="review"))
        dag.add_dependency("b", "a")
        ready = dag.ready_tasks(completed={"a"})
        assert ready == ("b",)

    def test_from_decomposition(self):
        t1 = SubTask(id="a", agent_type="code")
        t2 = SubTask(id="b", agent_type="review")
        dr = DecompositionResult(sub_tasks=(t1, t2), dependencies={"b": ("a",)})
        dag = WorkflowDAG.from_decomposition(dr)
        assert dag.task_count == 2
        assert dag.edge_count == 1

    def test_topological_order_independent(self):
        """Three independent tasks → single wave."""
        dag = WorkflowDAG()
        dag.add_task(SubTask(id="a", agent_type="code"))
        dag.add_task(SubTask(id="b", agent_type="code"))
        dag.add_task(SubTask(id="c", agent_type="code"))
        waves = dag.topological_order()
        assert len(waves) == 1
        assert len(waves[0]) == 3


# ---------------------------------------------------------------------------
# WorkflowResult
# ---------------------------------------------------------------------------

class TestWorkflowResult:
    def test_completed(self):
        r = WorkflowResult(
            workflow_name="test",
            status=WorkflowStatus.COMPLETED,
            subtask_results=(),
            total_subtasks=3,
            completed_count=3,
            failed_count=0,
            duration_ms=100.0,
        )
        assert r.success_rate == 1.0

    def test_partial(self):
        r = WorkflowResult(
            workflow_name="test",
            status=WorkflowStatus.PARTIAL,
            subtask_results=(),
            total_subtasks=4,
            completed_count=3,
            failed_count=1,
            duration_ms=200.0,
        )
        assert r.success_rate == 0.75

    def test_success_rate_zero_tasks(self):
        r = WorkflowResult(
            workflow_name="test",
            status=WorkflowStatus.COMPLETED,
            subtask_results=(),
            total_subtasks=0,
            completed_count=0,
            failed_count=0,
            duration_ms=0.0,
        )
        assert r.success_rate == 1.0

    def test_subtask_ids(self):
        sr1 = SubTaskResult(subtask_id="a", status=SubTaskStatus.COMPLETED)
        sr2 = SubTaskResult(subtask_id="b", status=SubTaskStatus.COMPLETED)
        r = WorkflowResult(
            workflow_name="test",
            status=WorkflowStatus.COMPLETED,
            subtask_results=(sr1, sr2),
            total_subtasks=2,
            completed_count=2,
            failed_count=0,
            duration_ms=0.0,
        )
        assert r.subtask_ids == ("a", "b")

    def test_frozen(self):
        r = WorkflowResult(
            workflow_name="x", status=WorkflowStatus.COMPLETED,
            subtask_results=(), total_subtasks=0, completed_count=0,
            failed_count=0, duration_ms=0.0,
        )
        with pytest.raises(Exception):
            r.status = WorkflowStatus.FAILED  # type: ignore[misc]


# ---------------------------------------------------------------------------
# WorkflowEngine
# ---------------------------------------------------------------------------

class TestWorkflowEngine:
    def test_execute_empty_decomposition(self):
        spec = WorkflowSpec(name="empty-test")
        engine = WorkflowEngine()
        result = engine.execute(spec)
        assert result.status == WorkflowStatus.FAILED
        assert "No decomposition config" in result.verification_summary

    def test_execute_single_task_dry_run(self):
        t1 = SubTask(id="search", agent_type="research", query="Find papers")
        dr = DecompositionResult(sub_tasks=(t1,))
        spec = WorkflowSpec(name="single").with_decomposition(dr)
        engine = WorkflowEngine()
        result = engine.execute(spec)
        assert result.status == WorkflowStatus.PENDING  # dry run, no runner
        assert result.total_subtasks == 1

    def test_execute_multiple_independent(self):
        t1 = SubTask(id="a", agent_type="research")
        t2 = SubTask(id="b", agent_type="code")
        t3 = SubTask(id="c", agent_type="review")
        dr = DecompositionResult(sub_tasks=(t1, t2, t3))
        spec = WorkflowSpec(name="parallel").with_decomposition(dr)
        engine = WorkflowEngine(max_concurrency=2)
        result = engine.execute(spec)
        assert result.total_subtasks == 3
        assert result.status == WorkflowStatus.PENDING  # dry run

    def test_execute_with_runner(self):
        t1 = SubTask(id="a", agent_type="research")
        t2 = SubTask(id="b", agent_type="code")
        dr = DecompositionResult(sub_tasks=(t1, t2))
        spec = WorkflowSpec(name="runner-test").with_decomposition(dr)
        engine = WorkflowEngine()

        def runner(task, ctx):
            return f"result-{task.id}"

        result = engine.execute(spec, agent_runner=runner)
        assert result.status == WorkflowStatus.COMPLETED
        assert result.completed_count == 2
        assert result.failed_count == 0

    def test_execute_with_dependencies(self):
        t1 = SubTask(id="research", agent_type="research")
        t2 = SubTask(id="code", agent_type="code")
        t3 = SubTask(id="review", agent_type="review")
        dr = DecompositionResult(
            sub_tasks=(t1, t2, t3),
            dependencies={"code": ("research",), "review": ("code",)},
        )
        spec = WorkflowSpec(name="sequential").with_decomposition(dr)
        engine = WorkflowEngine()

        order = []
        def runner(task, ctx):
            order.append(task.id)
            return f"done-{task.id}"

        result = engine.execute(spec, agent_runner=runner)
        assert result.completed_count == 3
        assert order == ["research", "code", "review"]

    def test_execute_parallel_wave_respects_order(self):
        t1 = SubTask(id="a", agent_type="research")
        t2 = SubTask(id="b", agent_type="research")
        t3 = SubTask(id="c", agent_type="review")
        dr = DecompositionResult(
            sub_tasks=(t1, t2, t3),
            dependencies={"c": ("a", "b")},
        )
        spec = WorkflowSpec(name="diamond").with_decomposition(dr)
        engine = WorkflowEngine()

        order = []
        def runner(task, ctx):
            order.append(task.id)
            return f"done-{task.id}"

        result = engine.execute(spec, agent_runner=runner)
        assert result.completed_count == 3
        # a,b before c
        a_idx = order.index("a")
        b_idx = order.index("b")
        c_idx = order.index("c")
        assert a_idx < c_idx
        assert b_idx < c_idx

    def test_execute_runner_exception(self):
        t1 = SubTask(id="failing", agent_type="code")
        dr = DecompositionResult(sub_tasks=(t1,))
        spec = WorkflowSpec(name="fail-test").with_decomposition(dr)
        engine = WorkflowEngine()

        def runner(task, ctx):
            raise RuntimeError("boom")

        result = engine.execute(spec, agent_runner=runner)
        assert result.status == WorkflowStatus.FAILED
        assert result.failed_count == 1
        assert result.subtask_results[0].error == "boom"

    def test_execute_partial_failure(self):
        t1 = SubTask(id="ok", agent_type="research")
        t2 = SubTask(id="fail", agent_type="code")
        dr = DecompositionResult(sub_tasks=(t1, t2))
        spec = WorkflowSpec(name="partial").with_decomposition(dr)
        engine = WorkflowEngine()

        def runner(task, ctx):
            if task.id == "fail":
                raise RuntimeError("failed")
            return "ok"

        result = engine.execute(spec, agent_runner=runner)
        assert result.status == WorkflowStatus.PARTIAL
        assert result.completed_count == 1
        assert result.failed_count == 1

    def test_execute_cycle_detection(self):
        t1 = SubTask(id="a", agent_type="code")
        t2 = SubTask(id="b", agent_type="review")
        dr = DecompositionResult(
            sub_tasks=(t1, t2),
            dependencies={"a": ("b",), "b": ("a",)},
        )
        spec = WorkflowSpec(name="cycle").with_decomposition(dr)
        engine = WorkflowEngine()
        result = engine.execute(spec)
        assert result.status == WorkflowStatus.FAILED
        assert "Cycle" in result.verification_summary

    def test_execute_context_passed(self):
        t1 = SubTask(id="ctx-test", agent_type="research")
        dr = DecompositionResult(sub_tasks=(t1,))
        spec = WorkflowSpec(name="ctx").with_decomposition(dr)
        engine = WorkflowEngine()

        ctx_seen = []
        def runner(task, ctx):
            ctx_seen.append(ctx.get("custom_key"))
            return "ok"

        engine.execute(spec, initial_context={"custom_key": "hello"}, agent_runner=runner)
        assert "hello" in ctx_seen

    def test_reset(self):
        t1 = SubTask(id="a", agent_type="code")
        dr = DecompositionResult(sub_tasks=(t1,))
        spec = WorkflowSpec(name="reset").with_decomposition(dr)
        engine = WorkflowEngine()

        def runner(task, ctx):
            return "ok"

        engine.execute(spec, agent_runner=runner)
        assert len(engine.results) == 1
        engine.reset()
        assert len(engine.results) == 0


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_full_workflow_pipeline(self):
        """End-to-end: deep-research workflow with DAG and fan-out."""
        tasks = (
            SubTask(id="lit-review", agent_type="research", query="RLHF papers"),
            SubTask(id="code-audit", agent_type="code", repo="open/rlhf"),
            SubTask(id="arch-review", agent_type="architect", system="RLHF pipeline"),
            SubTask(id="merge-report", agent_type="review", query="synthesize findings"),
        )
        decomposition = DecompositionResult(
            sub_tasks=tasks,
            dependencies={
                "merge-report": ("lit-review", "code-audit", "arch-review"),
            },
            description="Deep research on RLHF",
        )
        spec = WorkflowSpec(
            name="deep-research",
            description="Multi-agent deep research with adversarial verification",
            fan_out=FanOutConfig(max_concurrency=3),
        ).with_decomposition(decomposition)

        engine = WorkflowEngine(max_concurrency=3)
        outputs = []

        def runner(task, ctx):
            output = f"[{task.agent_type}] analyzed {task.query or task.repo or task.system}"
            outputs.append(output)
            return output

        result = engine.execute(spec, agent_runner=runner)

        assert result.status == WorkflowStatus.COMPLETED
        assert result.completed_count == 4
        assert result.total_subtasks == 4
        assert result.success_rate == 1.0
        assert len(outputs) == 4
        # merge-report should run last
        merge_idx = next(i for i, o in enumerate(outputs) if "merge-report" not in o and o.startswith("[review]"))
        assert merge_idx == 3  # last position after all dependencies

    def test_spec_matches_workflow_js_pattern(self):
        """Verify the WorkflowSpec mirrors the workflow.js pattern from the plan."""
        spec = WorkflowSpec(
            name="deep-research-workflow",
            description="Multi-agent deep research with adversarial verification",
            fan_out=FanOutConfig(
                max_concurrency=12,
                agent_types=("research", "code", "architect", "security", "performance"),
                isolation=IsolationMode.WORKTREE,
            ),
            verify=VerifyConfig(
                attack_agents=2,
                convergence_threshold=0.9,
                max_rounds=3,
            ),
            checkpoint=CheckpointConfig(
                after_each="sub_task",
                retention="30d",
                resume_strategy=ResumeStrategy.SKIP_COMPLETED,
            ),
        )
        assert spec.fan_out.max_concurrency == 12
        assert spec.verify.attack_agents == 2
        assert spec.verify.convergence_threshold == 0.9
        assert spec.checkpoint.resume_strategy == ResumeStrategy.SKIP_COMPLETED
        assert "research" in spec.fan_out.agent_types
