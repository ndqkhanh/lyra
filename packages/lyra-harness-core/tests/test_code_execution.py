"""Tests for Code-Execution-as-Tool-Primitive."""
from __future__ import annotations

import pytest

from lyra_harness_core.code_execution import (
    BatchExecutor,
    BatchResult,
    BatchSpec,
    CodeBlock,
    parse_batch_from_json,
)
from lyra_harness_core.messages import ToolCall
from lyra_harness_core.tools import ToolPermissionGate, ToolRegistry
from lyra_harness_core.tools_builtin import CalculatorTool, EchoTool


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def registry():
    r = ToolRegistry()
    r.register(EchoTool())
    r.register(CalculatorTool())
    return r


@pytest.fixture
def executor(registry):
    return BatchExecutor(registry)


# ---------------------------------------------------------------------------
# BatchResult
# ---------------------------------------------------------------------------


class TestBatchResult:
    def test_defaults(self):
        br = BatchResult()
        assert br.total_calls == 0
        assert br.success_count == 0
        assert br.error_count == 0
        assert br.all_succeeded is True
        assert br.tokens_saved == 0

    def test_all_succeeded(self):
        tr = type("TR", (), {"is_error": False, "content": "ok"})()
        br = BatchResult(results=[tr, tr], total_calls=2, success_count=2)
        assert br.all_succeeded is True

    def test_not_all_succeeded(self):
        tr_ok = type("TR", (), {"is_error": False, "content": "ok"})()
        tr_err = type("TR", (), {"is_error": True, "content": "fail"})()
        br = BatchResult(
            results=[tr_ok, tr_err], total_calls=2, success_count=1, error_count=1
        )
        assert br.all_succeeded is False

    def test_combined_output(self):
        tr1 = type("TR", (), {"is_error": False, "content": "hello"})()
        tr2 = type("TR", (), {"is_error": True, "content": "bad"})()
        br = BatchResult(results=[tr1, tr2])
        out = br.combined_output
        assert "[0] OK: hello" in out
        assert "[1] ERROR: bad" in out


# ---------------------------------------------------------------------------
# BatchSpec
# ---------------------------------------------------------------------------


class TestBatchSpec:
    def test_defaults(self):
        spec = BatchSpec(calls=[])
        assert spec.continue_on_error is False
        assert spec.label == ""

    def test_with_calls(self):
        spec = BatchSpec(
            calls=[
                ToolCall(id="c1", name="echo", args={"text": "hi"}),
                ToolCall(id="c2", name="calculator", args={"expression": "1+1"}),
            ],
            continue_on_error=True,
            label="test batch",
        )
        assert len(spec.calls) == 2
        assert spec.continue_on_error is True
        assert spec.label == "test batch"


# ---------------------------------------------------------------------------
# BatchExecutor
# ---------------------------------------------------------------------------


class TestBatchExecutor:
    def test_execute_single_call(self, executor):
        batch = BatchSpec(calls=[ToolCall(id="c1", name="echo", args={"text": "hello"})])
        result = executor.execute(batch)
        assert result.total_calls == 1
        assert result.success_count == 1
        assert result.error_count == 0
        assert result.all_succeeded
        assert "hello" in result.results[0].content

    def test_execute_multiple_calls(self, executor):
        batch = BatchSpec(
            calls=[
                ToolCall(id="c1", name="echo", args={"text": "a"}),
                ToolCall(id="c2", name="echo", args={"text": "b"}),
                ToolCall(id="c3", name="calculator", args={"expression": "3*7"}),
            ]
        )
        result = executor.execute(batch)
        assert result.total_calls == 3
        assert result.success_count == 3
        assert result.results[0].content == "a"
        assert result.results[2].content == "21"

    def test_combined_output_format(self, executor):
        batch = BatchSpec(
            calls=[
                ToolCall(id="c1", name="echo", args={"text": "x"}),
                ToolCall(id="c2", name="echo", args={"text": "y"}),
            ]
        )
        result = executor.execute(batch)
        out = result.combined_output
        assert "[0]" in out
        assert "[1]" in out
        assert "x" in out
        assert "y" in out

    def test_stop_on_first_error_by_default(self, executor):
        batch = BatchSpec(
            calls=[
                ToolCall(id="c1", name="nonexistent", args={}),
                ToolCall(id="c2", name="echo", args={"text": "never runs"}),
            ]
        )
        result = executor.execute(batch)
        assert result.error_count >= 1
        # Only the first call (error) should be in results
        assert result.results[0].is_error
        assert len(result.results) == 1  # stopped after error

    def test_continue_on_error(self, executor):
        batch = BatchSpec(
            calls=[
                ToolCall(id="c1", name="nonexistent", args={}),
                ToolCall(id="c2", name="echo", args={"text": "still runs"}),
            ],
            continue_on_error=True,
        )
        result = executor.execute(batch)
        assert result.error_count == 1
        assert result.success_count == 1
        assert len(result.results) == 2

    def test_with_permission_gate(self, registry):
        gate = ToolPermissionGate(mode="bypass")
        executor = BatchExecutor(registry, permission_gate=gate)
        batch = BatchSpec(calls=[ToolCall(id="c1", name="echo", args={"text": "x"})])
        result = executor.execute(batch)
        assert result.all_succeeded

    def test_tokens_saved_single_call_is_zero(self, executor):
        batch = BatchSpec(calls=[ToolCall(id="c1", name="echo", args={"text": "hi"})])
        result = executor.execute(batch)
        assert result.tokens_saved == 0

    def test_tokens_saved_multiple_calls(self, executor):
        batch = BatchSpec(
            calls=[
                ToolCall(id="c1", name="echo", args={"text": "a"}),
                ToolCall(id="c2", name="echo", args={"text": "b"}),
                ToolCall(id="c3", name="echo", args={"text": "c"}),
            ]
        )
        result = executor.execute(batch)
        # 3 calls → (3-1) * 2000 = 4000 tokens saved
        assert result.tokens_saved == 4000

    def test_empty_batch(self, executor):
        batch = BatchSpec(calls=[])
        result = executor.execute(batch)
        assert result.total_calls == 0
        assert result.success_count == 0
        assert result.elapsed_ms >= 0

    def test_elapsed_time_tracked(self, executor):
        batch = BatchSpec(calls=[ToolCall(id="c1", name="echo", args={"text": "x"})])
        result = executor.execute(batch)
        assert result.elapsed_ms >= 0

    def test_registry_property(self, executor, registry):
        assert executor.registry is registry


# ---------------------------------------------------------------------------
# parse_batch_from_json
# ---------------------------------------------------------------------------


class TestParseBatchFromJson:
    def test_valid_json(self):
        json_text = """
        [
            {"id": "c1", "name": "echo", "args": {"text": "hello"}},
            {"id": "c2", "name": "calculator", "args": {"expression": "1+1"}}
        ]
        """
        spec = parse_batch_from_json(json_text, label="test")
        assert spec.label == "test"
        assert len(spec.calls) == 2
        assert spec.calls[0].name == "echo"
        assert spec.calls[0].args == {"text": "hello"}
        assert spec.calls[1].name == "calculator"

    def test_missing_id_generated(self):
        json_text = """[{"name": "echo", "args": {"text": "x"}}]"""
        spec = parse_batch_from_json(json_text)
        assert len(spec.calls) == 1
        assert spec.calls[0].id.startswith("b")

    def test_missing_args_defaults(self):
        json_text = """[{"name": "echo"}]"""
        spec = parse_batch_from_json(json_text)
        assert spec.calls[0].args == {}

    def test_non_list_raises(self):
        with pytest.raises(ValueError, match="list"):
            parse_batch_from_json('{"name": "echo"}')

    def test_invalid_json_raises(self):
        with pytest.raises(Exception):
            parse_batch_from_json("not json")


# ---------------------------------------------------------------------------
# CodeBlock
# ---------------------------------------------------------------------------


class TestCodeBlock:
    def test_defaults(self):
        cb = CodeBlock(language="lyra-tools", code="[]")
        assert cb.language == "lyra-tools"
        assert cb.source == ""

    def test_with_source(self):
        cb = CodeBlock(language="python", code="print(1)", source="claude-opus")
        assert cb.source == "claude-opus"
