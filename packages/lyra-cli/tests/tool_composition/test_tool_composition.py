"""Tests for Tool Composition — pipeline and orchestrator."""

from __future__ import annotations

import time

import pytest

from lyra_cli.tool_composition.pipeline import (
    PipelineResult,
    PipelineStepStatus,
    PipelineTemplate,
    StepResult,
    ToolPipeline,
)
from lyra_cli.tool_composition.orchestrator import (
    ExecutionMode,
    OrchestrationResult,
    TaskResult,
    ToolOrchestrator,
    ToolTask,
)


# ── Pipeline Tests ──


class TestToolPipeline:
    @pytest.fixture
    def pipeline(self):
        return ToolPipeline("test-pipe")

    def test_empty_pipeline(self, pipeline):
        result = pipeline.run("hello")
        assert result.success
        assert result.final_output == "hello"
        assert len(result.steps) == 0
        assert result.pipeline_name == "test-pipe"

    def test_single_step(self, pipeline):
        pipeline.add_step("upper", lambda s: s.upper())
        result = pipeline.run("hello")
        assert result.success
        assert result.final_output == "HELLO"
        assert len(result.steps) == 1
        assert result.steps[0].status == PipelineStepStatus.COMPLETED

    def test_multiple_steps_chain(self, pipeline):
        pipeline.add_step("upper", lambda s: s.upper())
        pipeline.add_step("reverse", lambda s: s[::-1])
        pipeline.add_step("add_suffix", lambda s: s + "!")
        result = pipeline.run("hello")
        assert result.success
        assert result.final_output == "OLLEH!"
        assert len(result.steps) == 3

    def test_step_receives_previous_output(self, pipeline):
        received = []

        def capture(x):
            received.append(x)
            return x + "-step"

        pipeline.add_step("s1", capture)
        pipeline.add_step("s2", capture)
        pipeline.run("start")
        assert received == ["start", "start-step"]

    def test_error_strategy_stop(self, pipeline):
        pipeline.add_step("good", lambda s: s)
        pipeline.add_step("bad", lambda _s: (_ for _ in ()).throw(ValueError("boom")))
        pipeline.add_step("should_not_run", lambda s: s + "x")
        result = pipeline.run("input")
        assert not result.success
        assert result.steps[1].status == PipelineStepStatus.FAILED
        assert "boom" in result.steps[1].error
        assert len(result.steps) == 2

    def test_error_strategy_skip(self):
        pipeline = ToolPipeline("skip-pipe", error_strategy="skip")
        pipeline.add_step("good", lambda s: s + "a")
        pipeline.add_step("bad", lambda _s: (_ for _ in ()).throw(RuntimeError("fail")))
        pipeline.add_step("after_bad", lambda s: s + "c")
        result = pipeline.run("x")
        assert result.success
        assert len(result.steps) == 3
        assert result.steps[1].status == PipelineStepStatus.FAILED
        assert result.steps[2].status == PipelineStepStatus.COMPLETED
        # After a failed step that is skipped, current_input remains what it was
        assert result.final_output == "xac"

    def test_error_strategy_continue(self):
        pipeline = ToolPipeline("continue-pipe", error_strategy="continue")
        pipeline.add_step("bad", lambda _s: (_ for _ in ()).throw(ValueError("err")))
        pipeline.add_step("good", lambda s: s + "b")
        result = pipeline.run("x")
        assert result.success
        assert len(result.steps) == 2
        assert result.steps[0].status == PipelineStepStatus.FAILED
        assert result.steps[1].status == PipelineStepStatus.COMPLETED

    def test_initial_input_default(self, pipeline):
        pipeline.add_step("prepend_hello", lambda s: "hello " + s)
        result = pipeline.run()
        assert result.final_output == "hello "

    def test_step_count(self, pipeline):
        assert pipeline.step_count == 0
        pipeline.add_step("a", lambda s: s)
        assert pipeline.step_count == 1
        pipeline.add_step("b", lambda s: s)
        assert pipeline.step_count == 2

    def test_insert_step(self, pipeline):
        pipeline.add_step("s3", lambda s: s + "3")
        pipeline.insert_step(0, "s1", lambda s: s + "1")
        pipeline.insert_step(1, "s2", lambda s: s + "2")
        result = pipeline.run("")
        assert result.final_output == "123"

    def test_remove_step(self, pipeline):
        pipeline.add_step("a", lambda s: s + "a")
        pipeline.add_step("b", lambda s: s + "b")
        pipeline.remove_step("a")
        assert pipeline.step_count == 1
        result = pipeline.run("x")
        assert result.final_output == "xb"

    def test_remove_nonexistent_step(self, pipeline):
        pipeline.add_step("a", lambda s: s)
        pipeline.remove_step("nonexistent")
        assert pipeline.step_count == 1

    def test_step_result_duration_recorded(self, pipeline):
        pipeline.add_step("sleepy", lambda s: (time.sleep(0.01), s)[1])
        result = pipeline.run("x")
        assert result.steps[0].duration_ms > 0

    def test_total_duration_recorded(self, pipeline):
        pipeline.add_step("s1", lambda s: (time.sleep(0.01), s)[1])
        result = pipeline.run("x")
        assert result.total_duration_ms > 0

    def test_step_output_preserved_on_failure(self):
        pipeline = ToolPipeline("test")
        pipeline.add_step("produce", lambda _s: "good-output")
        pipeline.add_step("fail", lambda _s: (_ for _ in ()).throw(ValueError("bad")))
        result = pipeline.run("")
        assert result.steps[1].output == "good-output"


# ── Pipeline Immutability Tests ──


class TestPipelineResultImmutability:
    def test_result_is_frozen(self):
        r = PipelineResult(
            pipeline_name="p", steps=(), final_output="", success=True, total_duration_ms=0.0,
        )
        with pytest.raises(Exception):
            r.final_output = "changed"

    def test_step_result_is_frozen(self):
        r = StepResult(
            step_name="s", status=PipelineStepStatus.COMPLETED, output="o",
        )
        with pytest.raises(Exception):
            r.output = "changed"


class TestPipelineTemplateImmutability:
    def test_template_is_frozen(self):
        t = PipelineTemplate(
            name="tmpl", description="desc", step_names=("a", "b"),
        )
        with pytest.raises(Exception):
            t.name = "other"


# ── Orchestrator Tests ──


class TestToolOrchestrator:
    @pytest.fixture
    def orch(self):
        return ToolOrchestrator(max_parallel=4)

    def test_empty_orchestrator(self, orch):
        result = orch.execute()
        assert result.success_count == 0
        assert result.failure_count == 0
        assert result.total_duration_ms >= 0

    def test_single_task(self, orch):
        orch.add_task(ToolTask("t1", "hello", lambda: "world"))
        result = orch.execute()
        assert result.success_count == 1
        assert result.tasks[0].output == "world"
        assert result.tasks[0].success

    def test_multiple_independent_tasks(self, orch):
        orch.add_task(ToolTask("t1", "a", lambda: "result-a"))
        orch.add_task(ToolTask("t2", "b", lambda: "result-b"))
        orch.add_task(ToolTask("t3", "c", lambda: "result-c"))
        result = orch.execute()
        assert result.success_count == 3
        outputs = {r.output for r in result.tasks}
        assert outputs == {"result-a", "result-b", "result-c"}

    def test_sequential_dependencies(self, orch):
        execution_order = []

        def make_fn(name, order_list):
            def fn():
                order_list.append(name)
                return name
            return fn

        orch.add_task(ToolTask("t1", "first", make_fn("first", execution_order)))
        orch.add_task(ToolTask("t2", "second", make_fn("second", execution_order), depends_on=("t1",)))
        orch.add_task(ToolTask("t3", "third", make_fn("third", execution_order), depends_on=("t2",)))
        result = orch.execute()
        assert result.success_count == 3
        assert execution_order == ["first", "second", "third"]

    def test_dependency_failure_blocks_dependents(self, orch):
        orch.add_task(ToolTask("t1", "fail", lambda: (_ for _ in ()).throw(ValueError("boom"))))
        orch.add_task(ToolTask("t2", "depend", lambda: "should_not_run", depends_on=("t1",)))
        result = orch.execute()
        assert result.failure_count == 1
        t2_result = [r for r in result.tasks if r.task_id == "t2"][0]
        assert t2_result.skipped

    def test_conditional_if_prev_success(self, orch):
        orch.add_task(ToolTask("t1", "ok", lambda: "success"))
        orch.add_task(ToolTask("t2", "conditional", lambda: "ran", condition="if_prev_success", depends_on=("t1",)))
        result = orch.execute()
        t2 = [r for r in result.tasks if r.task_id == "t2"][0]
        assert t2.success
        assert t2.output == "ran"

    def test_conditional_if_prev_success_skips_on_failure(self, orch):
        orch.add_task(ToolTask("t1", "fail", lambda: (_ for _ in ()).throw(ValueError("boom"))))
        orch.add_task(ToolTask("t2", "cond", lambda: "should_not_run", condition="if_prev_success", depends_on=("t1",)))
        result = orch.execute()
        t2 = [r for r in result.tasks if r.task_id == "t2"][0]
        assert t2.skipped

    def test_task_count(self, orch):
        assert orch.task_count == 0
        orch.add_task(ToolTask("t1", "a", lambda: ""))
        orch.add_task(ToolTask("t2", "b", lambda: ""))
        assert orch.task_count == 2

    def test_remove_task(self, orch):
        orch.add_task(ToolTask("t1", "a", lambda: "x"))
        orch.add_task(ToolTask("t2", "b", lambda: "y"))
        orch.remove_task("t1")
        result = orch.execute()
        assert len(result.tasks) == 1
        assert result.tasks[0].task_id == "t2"

    def test_clear_tasks(self, orch):
        orch.add_task(ToolTask("t1", "a", lambda: "x"))
        orch.clear()
        assert orch.task_count == 0

    def test_error_captured_in_result(self, orch):
        def fail():
            raise RuntimeError("something went wrong")

        orch.add_task(ToolTask("t1", "bad", fail))
        result = orch.execute()
        assert result.failure_count == 1
        assert "something went wrong" in result.tasks[0].error
        assert not result.tasks[0].success

    def test_duration_recorded(self, orch):
        orch.add_task(ToolTask("t1", "a", lambda: "x"))
        result = orch.execute()
        assert result.tasks[0].duration_ms > 0
        assert result.total_duration_ms > 0

    def test_max_parallel_respected(self, orch):
        import threading

        running = 0
        max_seen = 0
        lock = threading.Lock()

        def limited_task():
            nonlocal running, max_seen
            with lock:
                running += 1
                max_seen = max(max_seen, running)
            time.sleep(0.02)
            with lock:
                running -= 1
            return "done"

        for i in range(6):
            orch.add_task(ToolTask(f"t{i}", f"task-{i}", limited_task))

        orch._max_parallel = 2
        result = orch.execute()
        assert result.success_count == 6
        assert max_seen <= 2

    def test_parallel_tasks_run_concurrently(self, orch):
        import threading

        seen_threads: set[int] = set()
        lock = threading.Lock()

        def record_thread():
            with lock:
                seen_threads.add(threading.get_ident())
            return "ok"

        for i in range(4):
            orch.add_task(ToolTask(f"t{i}", f"task-{i}", record_thread))

        result = orch.execute()
        assert result.success_count == 4
        assert len(seen_threads) >= 2

    def test_mixed_success_failure_skip_counts(self, orch):
        def fail():
            raise RuntimeError("fail")

        orch.add_task(ToolTask("t1", "good", lambda: "ok"))
        orch.add_task(ToolTask("t2", "bad", fail))
        orch.add_task(ToolTask("t3", "cond", lambda: "nope", condition="if_prev_success", depends_on=("t2",)))
        result = orch.execute()
        assert result.success_count == 1
        assert result.failure_count == 1
        assert result.skipped_count == 1
        assert result.total_duration_ms > 0


# ── Orchestrator Immutability Tests ──


class TestToolTaskImmutability:
    def test_task_is_frozen(self):
        t = ToolTask("t1", "name", lambda: "x")
        with pytest.raises(Exception):
            t.name = "other"

    def test_task_depends_on_default(self):
        t = ToolTask("t1", "name", lambda: "x")
        assert t.depends_on == ()

    def test_task_condition_default(self):
        t = ToolTask("t1", "name", lambda: "x")
        assert t.condition == ""


class TestTaskResultImmutability:
    def test_result_is_frozen(self):
        r = TaskResult(task_id="t1", name="task", output="out")
        with pytest.raises(Exception):
            r.output = "changed"

    def test_result_defaults(self):
        r = TaskResult(task_id="t1", name="task", output="")
        assert r.error == ""
        assert r.success
        assert r.duration_ms == 0.0
        assert not r.skipped


class TestOrchestrationResultImmutability:
    def test_result_is_frozen(self):
        r = OrchestrationResult(
            tasks=(), success_count=0, failure_count=0, skipped_count=0, total_duration_ms=0.0,
        )
        with pytest.raises(Exception):
            r.success_count = 1


# ── ExecutionMode Tests ──


class TestExecutionMode:
    def test_values(self):
        assert ExecutionMode.SEQUENTIAL == "sequential"
        assert ExecutionMode.PARALLEL == "parallel"
        assert ExecutionMode.CONDITIONAL == "conditional"

    def test_is_strenum(self):
        assert isinstance(ExecutionMode.SEQUENTIAL, str)


# ── PipelineStepStatus Tests ──


class TestPipelineStepStatus:
    def test_values(self):
        assert PipelineStepStatus.PENDING == "pending"
        assert PipelineStepStatus.RUNNING == "running"
        assert PipelineStepStatus.COMPLETED == "completed"
        assert PipelineStepStatus.FAILED == "failed"
        assert PipelineStepStatus.SKIPPED == "skipped"
