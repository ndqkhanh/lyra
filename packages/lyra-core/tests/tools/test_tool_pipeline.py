"""Tests for Phase 4.1a — Tool Composition Pipelines."""
from __future__ import annotations

import pytest

from lyra_core.tools.tool_pipeline import (
    PipelineResult,
    PipelineStatus,
    StageResult,
    StageType,
    ToolPipeline,
)


def identity(x):
    return x


def uppercase(x):
    return x.upper() if isinstance(x, str) else x


def append_bang(x):
    return f"{x}!" if isinstance(x, str) else x


def failing_tool(_x):
    raise RuntimeError("deliberate failure")


def safe_tool(x):
    return x


class TestToolPipeline:
    """Unit tests for ToolPipeline composition and execution."""

    def test_empty_pipeline_runs(self):
        p = ToolPipeline("empty")
        result = p.run("hello")
        assert result.status == PipelineStatus.COMPLETED
        assert result.final_output == "hello"
        assert result.stage_results == ()

    def test_add_stage_returns_self(self):
        p = ToolPipeline("fluent")
        assert p.add_stage("s1", identity) is p

    def test_single_stage_executes(self):
        p = ToolPipeline("single")
        p.add_stage("up", uppercase)
        result = p.run("hello")
        assert result.status == PipelineStatus.COMPLETED
        assert result.final_output == "HELLO"
        assert len(result.stage_results) == 1

    def test_sequential_stages_chain(self):
        p = ToolPipeline("chain")
        p.add_stage("up", uppercase)
        p.add_stage("bang", append_bang)
        result = p.run("hello")
        assert result.final_output == "HELLO!"

    def test_parallel_stage_merges_dicts(self):
        p = ToolPipeline("parallel")
        p.add_parallel("multi", [
            lambda x: {"a": 1},
            lambda x: {"b": 2},
            lambda x: {"c": 3},
        ])
        result = p.run(None)
        stage = result.stage_results[0]
        assert stage.status == PipelineStatus.COMPLETED
        assert stage.output == {"a": 1, "b": 2, "c": 3}

    def test_parallel_stage_wraps_non_dicts(self):
        p = ToolPipeline("parallel2")
        p.add_parallel("multi", [lambda x: 10, lambda x: 20])
        result = p.run(None)
        stage = result.stage_results[0]
        assert stage.output == {"results": [10, 20]}

    def test_conditional_then_branch(self):
        p = ToolPipeline("cond")
        p.add_conditional(
            "branch",
            condition=lambda x: isinstance(x, str) and len(x) > 3,
            then_tool=uppercase,
            else_tool=lambda x: "short",
        )
        result = p.run("hello!")
        assert result.final_output == "HELLO!"

    def test_conditional_else_branch(self):
        p = ToolPipeline("cond")
        p.add_conditional(
            "branch",
            condition=lambda x: isinstance(x, str) and len(x) > 10,
            then_tool=uppercase,
            else_tool=lambda x: "short",
        )
        result = p.run("hi")
        assert result.final_output == "short"

    def test_conditional_without_else_passes_through(self):
        p = ToolPipeline("cond")
        p.add_conditional(
            "branch",
            condition=lambda x: False,
            then_tool=uppercase,
        )
        result = p.run("hello")
        assert result.final_output == "hello"

    def test_retry_succeeds_on_first_try(self):
        call_count = {"n": 0}

        def counting_tool(x):
            call_count["n"] += 1
            return f"{x}-{call_count['n']}"

        p = ToolPipeline("retry")
        p.add_retry("try", counting_tool, max_retries=3)
        result = p.run("data")
        assert result.final_output == "data-1"
        sr = result.stage_results[0]
        assert sr.attempt == 1
        assert sr.status == PipelineStatus.COMPLETED

    def test_retry_eventually_fails(self):
        call_count = {"n": 0}

        def always_fails(_x):
            call_count["n"] += 1
            raise RuntimeError(f"fail #{call_count['n']}")

        p = ToolPipeline("retry")
        p.add_retry("bad", always_fails, max_retries=3)
        result = p.run("data")
        assert result.status == PipelineStatus.FAILED
        sr = result.stage_results[0]
        assert sr.status == PipelineStatus.FAILED
        assert sr.attempt == 3

    def test_retry_succeeds_after_failures(self):
        state = {"attempts": 0}

        def flaky(_x):
            state["attempts"] += 1
            if state["attempts"] < 2:
                raise RuntimeError("not yet")
            return "success"

        p = ToolPipeline("retry")
        p.add_retry("flaky", flaky, max_retries=3)
        result = p.run("data")
        assert result.status == PipelineStatus.COMPLETED
        sr = result.stage_results[0]
        assert sr.status == PipelineStatus.COMPLETED
        assert sr.attempt == 2

    def test_dependency_skip_on_failure(self):
        p = ToolPipeline("deps")
        p.add_stage("bad", failing_tool)
        p.add_stage("good", uppercase, depends_on="bad")
        result = p.run("hello")
        assert result.status == PipelineStatus.FAILED
        skipped = result.stage_results[1]
        assert skipped.status == PipelineStatus.SKIPPED
        assert "bad" in skipped.error

    def test_result_summary(self):
        p = ToolPipeline("summary")
        p.add_stage("a", identity)
        p.add_stage("b", uppercase)
        result = p.run("test")
        assert "summary" in result.summary
        assert "2/2" in result.summary
        assert "completed" in result.summary

    def test_stage_count(self):
        p = ToolPipeline("count")
        assert p.stage_count == 0
        p.add_stage("a", identity)
        p.add_stage("b", uppercase)
        p.add_parallel("c", [identity])
        assert p.stage_count == 3

    def test_stage_result_duration(self):
        p = ToolPipeline("timing")
        p.add_stage("a", identity)
        result = p.run("data")
        assert result.stage_results[0].duration_ms >= 0
        assert result.total_duration_ms >= 0

    def test_pipeline_id_is_unique(self):
        p = ToolPipeline("id")
        r1 = p.run("a")
        r2 = p.run("b")
        assert r1.pipeline_id != r2.pipeline_id

    def test_stage_result_has_name_and_type(self):
        p = ToolPipeline("meta")
        p.add_stage("my_stage", identity)
        result = p.run("data")
        sr = result.stage_results[0]
        assert sr.stage_name == "my_stage"
        assert sr.stage_type == StageType.SEQUENTIAL

    def test_parallel_stage_result(self):
        p = ToolPipeline("par")
        p.add_parallel("batch", [identity, uppercase])
        result = p.run("hello")
        sr = result.stage_results[0]
        assert sr.stage_type == StageType.PARALLEL
        assert sr.status == PipelineStatus.COMPLETED

    def test_conditional_stage_result(self):
        p = ToolPipeline("cond")
        p.add_conditional("check", lambda x: True, uppercase)
        result = p.run("hello")
        sr = result.stage_results[0]
        assert sr.stage_type == StageType.CONDITIONAL

    def test_retry_stage_result(self):
        p = ToolPipeline("retry")
        p.add_retry("attempt", safe_tool)
        result = p.run("data")
        sr = result.stage_results[0]
        assert sr.stage_type == StageType.RETRY

    def test_multiple_mixed_stages(self):
        p = ToolPipeline("mixed")
        p.add_stage("parse", identity)
        p.add_parallel("enrich", [identity, lambda x: x])
        p.add_conditional("validate", lambda x: True, identity)
        p.add_retry("submit", safe_tool)
        result = p.run("data")
        assert result.status == PipelineStatus.COMPLETED
        assert len(result.stage_results) == 4

    def test_failure_stops_pipeline(self):
        p = ToolPipeline("failfast")
        p.add_stage("ok", identity)
        p.add_stage("crash", failing_tool)
        p.add_stage("never_runs", uppercase)
        result = p.run("data")
        assert result.status == PipelineStatus.FAILED
        assert len(result.stage_results) == 3
        assert result.stage_results[2].status == PipelineStatus.SKIPPED
