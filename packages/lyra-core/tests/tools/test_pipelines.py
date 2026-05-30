"""Tests for tool composition pipelines."""

from __future__ import annotations

import asyncio
import json
import pytest

from lyra_core.tools.pipeline import (
    PipelineBuilder,
    PipelineContext,
    PipelineExecutor,
    PipelineValidator,
    ToolStep,
    ValidationError,
)
from lyra_core.tools.pipeline.executor import ExecutionStatus


# Mock tools for testing
def mock_read_file(file: str) -> dict[str, str]:
    """Mock file reading tool."""
    return {"content": f"content of {file}", "path": file}


def mock_ast_analyze(source: str) -> dict[str, bool]:
    """Mock AST analysis tool."""
    return {"has_errors": "error" in source.lower(), "line_count": len(source)}


def mock_security_scan(source: str) -> dict[str, list[str]]:
    """Mock security scanner."""
    issues = []
    if "password" in source.lower():
        issues.append("Hardcoded password detected")
    return {"issues": issues, "safe": len(issues) == 0}


def mock_generate_tests(source: str) -> dict[str, str]:
    """Mock test generator."""
    return {"tests": f"test for {source[:20]}"}


def mock_generate_docs(source: str) -> dict[str, str]:
    """Mock documentation generator."""
    return {"docs": f"docs for {source[:20]}"}


def mock_write_file(path: str, content: str) -> dict[str, bool]:
    """Mock file writing tool."""
    return {"success": True, "path": path, "bytes": len(content)}


def mock_rollback_file(path: str) -> dict[str, bool]:
    """Mock file rollback tool."""
    return {"rolled_back": True, "path": path}


def mock_failing_tool(data: str) -> dict[str, str]:
    """Mock tool that always fails."""
    raise RuntimeError("Tool execution failed")


async def mock_async_tool(data: str) -> dict[str, str]:
    """Mock async tool."""
    await asyncio.sleep(0.01)
    return {"result": f"async processed {data}"}


# Tool registry for tests
TOOL_REGISTRY = {
    "read_file": mock_read_file,
    "ast_analyze": mock_ast_analyze,
    "security_scan": mock_security_scan,
    "generate_tests": mock_generate_tests,
    "generate_docs": mock_generate_docs,
    "write_file": mock_write_file,
    "rollback_file": mock_rollback_file,
    "failing_tool": mock_failing_tool,
    "async_tool": mock_async_tool,
}


class TestPipelineBuilder:
    """Tests for PipelineBuilder."""

    def test_create_empty_pipeline(self) -> None:
        """Test creating an empty pipeline."""
        builder = PipelineBuilder("test-pipeline")
        pipeline = builder.build()

        assert pipeline.name == "test-pipeline"
        assert pipeline.step_count == 0
        assert pipeline.error_handler is None

    def test_sequential_steps(self) -> None:
        """Test adding sequential steps."""
        pipeline = (
            PipelineBuilder("seq-test")
            .then("read_file", file="$input.file_path")
            .then("ast_analyze", source="$read_file.content")
            .build()
        )

        assert pipeline.step_count == 2
        assert pipeline.steps[0].tool_step is not None
        assert pipeline.steps[0].tool_step.tool_name == "read_file"
        assert pipeline.steps[1].tool_step is not None
        assert pipeline.steps[1].tool_step.tool_name == "ast_analyze"

    def test_parallel_steps(self) -> None:
        """Test adding parallel steps."""
        pipeline = (
            PipelineBuilder("parallel-test")
            .then("read_file", file="test.py")
            .parallel(
                ToolStep("generate_tests", {"source": "$read_file.content"}),
                ToolStep("generate_docs", {"source": "$read_file.content"}),
            )
            .build()
        )

        assert pipeline.step_count == 2
        assert len(pipeline.steps[1].parallel_steps) == 2

    def test_conditional_step(self) -> None:
        """Test adding conditional steps."""
        pipeline = (
            PipelineBuilder("cond-test")
            .then("ast_analyze", source="$input.source")
            .when(
                "$ast_analyze.has_errors",
                ToolStep("write_file", {"path": "errors.log", "content": "errors"}),
                ToolStep("write_file", {"path": "success.log", "content": "ok"}),
            )
            .build()
        )

        assert pipeline.step_count == 2
        assert pipeline.steps[1].condition == "$ast_analyze.has_errors"
        assert pipeline.steps[1].when_true is not None
        assert pipeline.steps[1].when_false is not None

    def test_retry_step(self) -> None:
        """Test adding retry steps."""
        pipeline = (
            PipelineBuilder("retry-test")
            .retry("failing_tool", count=3, data="test")
            .build()
        )

        assert pipeline.step_count == 1
        assert pipeline.steps[0].retry_count == 3

    def test_timeout_step(self) -> None:
        """Test adding timeout to steps."""
        pipeline = (
            PipelineBuilder("timeout-test")
            .then("read_file", file="test.py")
            .timeout(5.0)
            .build()
        )

        assert pipeline.step_count == 1
        assert pipeline.steps[0].timeout_seconds == 5.0

    def test_error_handler(self) -> None:
        """Test adding error handler."""
        pipeline = (
            PipelineBuilder("error-test")
            .then("failing_tool", data="test")
            .on_error("rollback_file", path="$input.file_path")
            .build()
        )

        assert pipeline.error_handler is not None
        assert pipeline.error_handler.tool_name == "rollback_file"

    def test_metadata(self) -> None:
        """Test adding metadata."""
        pipeline = (
            PipelineBuilder("meta-test")
            .with_metadata(author="test", version="1.0")
            .build()
        )

        assert pipeline.metadata["author"] == "test"
        assert pipeline.metadata["version"] == "1.0"

    def test_serialization_to_dict(self) -> None:
        """Test serializing pipeline to dictionary."""
        builder = (
            PipelineBuilder("serialize-test")
            .then("read_file", file="$input.file_path")
            .then("ast_analyze", source="$read_file.content")
        )

        data = builder.to_dict()

        assert data["name"] == "serialize-test"
        assert len(data["steps"]) == 2
        assert data["steps"][0]["tool_step"]["tool_name"] == "read_file"

    def test_serialization_to_json(self) -> None:
        """Test serializing pipeline to JSON."""
        builder = PipelineBuilder("json-test").then("read_file", file="test.py")

        json_str = builder.to_json()
        data = json.loads(json_str)

        assert data["name"] == "json-test"
        assert len(data["steps"]) == 1

    def test_deserialization_from_dict(self) -> None:
        """Test deserializing pipeline from dictionary."""
        original = (
            PipelineBuilder("deser-test")
            .then("read_file", file="$input.file_path")
            .then("ast_analyze", source="$read_file.content")
        )

        data = original.to_dict()
        restored = PipelineBuilder.from_dict(data)
        pipeline = restored.build()

        assert pipeline.name == "deser-test"
        assert pipeline.step_count == 2

    def test_deserialization_from_json(self) -> None:
        """Test deserializing pipeline from JSON."""
        original = PipelineBuilder("json-deser-test").then("read_file", file="test.py")

        json_str = original.to_json()
        restored = PipelineBuilder.from_json(json_str)
        pipeline = restored.build()

        assert pipeline.name == "json-deser-test"
        assert pipeline.step_count == 1


class TestPipelineContext:
    """Tests for PipelineContext."""

    def test_input_data_access(self) -> None:
        """Test accessing input data."""
        context = PipelineContext(input_data={"file_path": "test.py"})

        assert context.get_variable("$input.file_path") == "test.py"
        assert context.get_variable("$input") == {"file_path": "test.py"}

    def test_step_output_storage(self) -> None:
        """Test storing and accessing step outputs."""
        context = PipelineContext()
        context.set_step_output("read_file", {"content": "test content"})

        assert context.get_variable("$read_file.content") == "test content"
        assert context.get_variable("$read_file") == {"content": "test content"}

    def test_nested_variable_access(self) -> None:
        """Test accessing nested variables."""
        context = PipelineContext()
        context.set_step_output(
            "analyze",
            {"result": {"errors": ["error1", "error2"], "warnings": []}},
        )

        result = context.get_variable("$analyze.result")
        assert result["errors"] == ["error1", "error2"]

    def test_variable_not_found(self) -> None:
        """Test accessing non-existent variable."""
        context = PipelineContext()

        with pytest.raises(KeyError):
            context.get_variable("$nonexistent")

    def test_interpolate_params(self) -> None:
        """Test parameter interpolation."""
        context = PipelineContext(input_data={"file": "test.py"})
        context.set_step_output("read_file", {"content": "test content"})

        params = {
            "file": "$input.file",
            "source": "$read_file.content",
            "static": "value",
        }

        interpolated = context.interpolate_params(params)

        assert interpolated["file"] == "test.py"
        assert interpolated["source"] == "test content"
        assert interpolated["static"] == "value"

    def test_interpolate_nested_params(self) -> None:
        """Test interpolating nested parameters."""
        context = PipelineContext(input_data={"path": "test.py"})

        params = {
            "config": {
                "file": "$input.path",
                "nested": {"value": "$input.path"},
            }
        }

        interpolated = context.interpolate_params(params)

        assert interpolated["config"]["file"] == "test.py"
        assert interpolated["config"]["nested"]["value"] == "test.py"

    def test_interpolate_list_params(self) -> None:
        """Test interpolating list parameters."""
        context = PipelineContext(input_data={"file": "test.py"})

        params = {"files": ["$input.file", "other.py"]}

        interpolated = context.interpolate_params(params)

        assert interpolated["files"] == ["test.py", "other.py"]

    def test_next_step_name(self) -> None:
        """Test generating unique step names."""
        context = PipelineContext()

        name1 = context.next_step_name("read_file")
        name2 = context.next_step_name("read_file")
        name3 = context.next_step_name("analyze")

        assert name1 == "read_file_1"
        assert name2 == "read_file_2"
        assert name3 == "analyze_3"


class TestPipelineExecutor:
    """Tests for PipelineExecutor."""

    def test_execute_simple_pipeline(self) -> None:
        """Test executing a simple sequential pipeline."""
        pipeline = (
            PipelineBuilder("simple")
            .then("read_file", file="$input.file_path")
            .then("ast_analyze", source="$read_file_1.content")
            .build()
        )

        executor = PipelineExecutor(TOOL_REGISTRY)
        result = executor.execute(pipeline, {"file_path": "test.py"})

        assert result.success
        assert result.status == ExecutionStatus.COMPLETED
        assert len(result.step_results) == 2
        assert result.final_output["has_errors"] is False

    def test_execute_parallel_pipeline(self) -> None:
        """Test executing pipeline with parallel steps."""
        pipeline = (
            PipelineBuilder("parallel")
            .then("read_file", file="test.py")
            .parallel(
                ToolStep("generate_tests", {"source": "$read_file_1.content"}),
                ToolStep("generate_docs", {"source": "$read_file_1.content"}),
            )
            .build()
        )

        executor = PipelineExecutor(TOOL_REGISTRY)
        result = executor.execute(pipeline, {})

        assert result.success
        assert len(result.step_results) == 2
        assert "generate_tests" in result.final_output
        assert "generate_docs" in result.final_output

    def test_execute_conditional_true(self) -> None:
        """Test executing conditional step when condition is true."""
        pipeline = (
            PipelineBuilder("cond-true")
            .then("ast_analyze", source="error in code")
            .when(
                "$ast_analyze_1.has_errors",
                ToolStep("write_file", {"path": "errors.log", "content": "errors"}),
            )
            .build()
        )

        executor = PipelineExecutor(TOOL_REGISTRY)
        result = executor.execute(pipeline, {})

        assert result.success
        assert len(result.step_results) == 2
        assert result.step_results[1].tool_name == "write_file"

    def test_execute_conditional_false(self) -> None:
        """Test executing conditional step when condition is false."""
        pipeline = (
            PipelineBuilder("cond-false")
            .then("ast_analyze", source="clean code")
            .when(
                "$ast_analyze_1.has_errors",
                ToolStep("write_file", {"path": "errors.log", "content": "errors"}),
                ToolStep("write_file", {"path": "success.log", "content": "ok"}),
            )
            .build()
        )

        executor = PipelineExecutor(TOOL_REGISTRY)
        result = executor.execute(pipeline, {})

        assert result.success
        assert len(result.step_results) == 2
        assert result.step_results[1].tool_name == "write_file"

    def test_execute_with_error(self) -> None:
        """Test executing pipeline with failing step."""
        pipeline = (
            PipelineBuilder("error")
            .then("read_file", file="test.py")
            .then("failing_tool", data="test")
            .then("ast_analyze", source="should not run")
            .build()
        )

        executor = PipelineExecutor(TOOL_REGISTRY)
        result = executor.execute(pipeline, {})

        assert not result.success
        assert result.status == ExecutionStatus.FAILED
        assert len(result.step_results) == 3
        assert result.step_results[1].status == ExecutionStatus.FAILED
        assert result.step_results[2].status == ExecutionStatus.SKIPPED

    def test_execute_with_error_handler(self) -> None:
        """Test executing pipeline with error handler."""
        pipeline = (
            PipelineBuilder("error-handler")
            .then("failing_tool", data="test")
            .on_error("rollback_file", path="test.py")
            .build()
        )

        executor = PipelineExecutor(TOOL_REGISTRY)
        result = executor.execute(pipeline, )

        assert not result.success
        assert result.error is not None

    def test_execute_async_tool(self) -> None:
        """Test executing pipeline with async tools."""
        pipeline = (
            PipelineBuilder("async")
            .then("async_tool", data="test")
            .build()
        )

        executor = PipelineExecutor(TOOL_REGISTRY)
        result = executor.execute(pipeline, {})

        assert result.success
        assert "async processed test" in result.final_output["result"]

    def test_variable_interpolation(self) -> None:
        """Test variable interpolation in pipeline execution."""
        pipeline = (
            PipelineBuilder("interpolation")
            .then("read_file", file="$input.file_path")
            .then("write_file", path="$input.output_path", content="$read_file_1.content")
            .build()
        )

        executor = PipelineExecutor(TOOL_REGISTRY)
        result = executor.execute(
            pipeline,
            {"file_path": "input.py", "output_path": "output.py"},
        )

        assert result.success
        assert result.final_output["path"] == "output.py"


class TestPipelineValidator:
    """Tests for PipelineValidator."""

    def test_validate_empty_pipeline(self) -> None:
        """Test validating empty pipeline."""
        pipeline = PipelineBuilder("empty").build()

        validator = PipelineValidator(TOOL_REGISTRY)
        result = validator.validate(pipeline)

        assert result.valid
        assert result.has_warnings
        assert "no steps" in result.warnings[0].lower()

    def test_validate_valid_pipeline(self) -> None:
        """Test validating a valid pipeline."""
        pipeline = (
            PipelineBuilder("valid")
            .then("read_file", file="$input.file_path")
            .then("ast_analyze", source="$read_file.content")
            .build()
        )

        validator = PipelineValidator(TOOL_REGISTRY)
        result = validator.validate(pipeline)

        assert result.valid
        assert not result.has_errors

    def test_validate_missing_variable(self) -> None:
        """Test validating pipeline with missing variable."""
        pipeline = (
            PipelineBuilder("invalid")
            .then("ast_analyze", source="$nonexistent.content")
            .build()
        )

        validator = PipelineValidator(TOOL_REGISTRY)
        result = validator.validate(pipeline)

        assert not result.valid
        assert result.has_errors
        assert "nonexistent" in result.errors[0].lower()

    def test_validate_unknown_tool(self) -> None:
        """Test validating pipeline with unknown tool."""
        pipeline = (
            PipelineBuilder("unknown")
            .then("unknown_tool", data="test")
            .build()
        )

        validator = PipelineValidator(TOOL_REGISTRY)
        result = validator.validate(pipeline)

        assert result.valid  # Valid structure
        assert result.has_warnings
        assert "not found" in result.warnings[0].lower()

    def test_validate_empty_tool_name(self) -> None:
        """Test validating pipeline with empty tool name."""
        pipeline = (
            PipelineBuilder("empty-tool")
            .then("", data="test")
            .build()
        )

        validator = PipelineValidator(TOOL_REGISTRY)
        result = validator.validate(pipeline)

        assert not result.valid
        assert "empty" in result.errors[0].lower()

    def test_validate_negative_retry(self) -> None:
        """Test validating pipeline with negative retry count."""
        pipeline = (
            PipelineBuilder("negative-retry")
            .retry("read_file", count=-1, file="test.py")
            .build()
        )

        validator = PipelineValidator(TOOL_REGISTRY)
        result = validator.validate(pipeline)

        assert not result.valid
        assert "negative" in result.errors[0].lower()

    def test_validate_invalid_timeout(self) -> None:
        """Test validating pipeline with invalid timeout."""
        pipeline = (
            PipelineBuilder("invalid-timeout")
            .then("read_file", file="test.py")
            .timeout(0)
            .build()
        )

        validator = PipelineValidator(TOOL_REGISTRY)
        result = validator.validate(pipeline)

        assert not result.valid
        assert "positive" in result.errors[0].lower()

    def test_validate_or_raise_valid(self) -> None:
        """Test validate_or_raise with valid pipeline."""
        pipeline = (
            PipelineBuilder("valid")
            .then("read_file", file="$input.file_path")
            .build()
        )

        validator = PipelineValidator(TOOL_REGISTRY)
        validator.validate_or_raise(pipeline)  # Should not raise

    def test_validate_or_raise_invalid(self) -> None:
        """Test validate_or_raise with invalid pipeline."""
        pipeline = (
            PipelineBuilder("invalid")
            .then("", data="test")
            .build()
        )

        validator = PipelineValidator(TOOL_REGISTRY)

        with pytest.raises(ValidationError) as exc_info:
            validator.validate_or_raise(pipeline)

        assert "empty" in str(exc_info.value).lower()


class TestIntegration:
    """Integration tests for complete pipeline workflows."""

    def test_code_review_pipeline(self) -> None:
        """Test a complete code review pipeline."""
        pipeline = (
            PipelineBuilder("code-review")
            .then("read_file", file="$input.file_path")
            .then("ast_analyze", source="$read_file_1.content")
            .then("security_scan", source="$read_file_1.content")
            .parallel(
                ToolStep("generate_tests", {"source": "$read_file_1.content"}),
                ToolStep("generate_docs", {"source": "$read_file_1.content"}),
            )
            .build()
        )

        # Validate
        validator = PipelineValidator(TOOL_REGISTRY)
        validation = validator.validate(pipeline)
        assert validation.valid

        # Execute
        executor = PipelineExecutor(TOOL_REGISTRY)
        result = executor.execute(pipeline, {"file_path": "app.py"})

        assert result.success
        assert len(result.step_results) == 4
        assert "generate_tests" in result.final_output
        assert "generate_docs" in result.final_output

    def test_pipeline_with_all_features(self) -> None:
        """Test pipeline using all features."""
        pipeline = (
            PipelineBuilder("full-featured")
            .then("read_file", file="$input.file_path")
            .then("ast_analyze", source="$read_file_1.content")
            .when(
                "$ast_analyze_2.has_errors",
                ToolStep("write_file", {"path": "errors.log", "content": "errors"}),
                ToolStep("write_file", {"path": "success.log", "content": "ok"}),
            )
            .parallel(
                ToolStep("generate_tests", {"source": "$read_file_1.content"}),
                ToolStep("generate_docs", {"source": "$read_file_1.content"}),
            )
            .retry("write_file", count=2, path="final.txt", content="done")
            .timeout(10.0)
            .on_error("rollback_file", path="$input.file_path")
            .with_metadata(version="1.0", author="test")
            .build()
        )

        # Validate
        validator = PipelineValidator(TOOL_REGISTRY)
        validation = validator.validate(pipeline)
        assert validation.valid

        # Serialize and deserialize
        json_str = PipelineBuilder("full-featured").to_json()
        restored = PipelineBuilder.from_json(json_str)
        assert restored.name == "full-featured"

        # Execute
        executor = PipelineExecutor(TOOL_REGISTRY)
        result = executor.execute(pipeline, {"file_path": "test.py"})

        assert result.success
        assert len(result.step_results) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
