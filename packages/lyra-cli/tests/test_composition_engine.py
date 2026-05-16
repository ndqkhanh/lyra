"""Tests for CompositionEngine (Phase 4)."""

from __future__ import annotations

import pytest

from lyra_cli.cli.composition_engine import CompositionEngine, StageResult


class MockSkillManager:
    """Mock skill manager for testing."""

    def __init__(self):
        self.skills = {
            "skill-a": {
                "name": "skill-a",
                "description": "Test skill A",
                "execution": {"type": "prompt"},
            },
            "skill-b": {
                "name": "skill-b",
                "description": "Test skill B",
                "execution": {"type": "prompt"},
            },
            "skill-c": {
                "name": "skill-c",
                "description": "Test skill C",
                "execution": {"type": "prompt"},
            },
        }
        self.execution_log = []

    def execute_skill(self, skill_name: str, args: str) -> str:
        """Mock skill execution."""
        self.execution_log.append((skill_name, args))
        return f"Output from {skill_name} with args: {args}"


@pytest.fixture
def skill_manager():
    """Create a mock skill manager."""
    return MockSkillManager()


@pytest.fixture
def engine(skill_manager):
    """Create a composition engine."""
    return CompositionEngine(skill_manager)


def test_simple_composition(engine, skill_manager):
    """Test executing a simple composition."""
    composition = {
        "stages": [
            {
                "name": "stage1",
                "skill": "skill-a",
                "args": "${input}",
                "output": "result1",
            }
        ],
        "return": "${result1}",
    }

    result = engine.execute(composition, "test input")

    assert result.success
    assert result.output is not None
    assert len(skill_manager.execution_log) == 1


def test_multi_stage_composition(engine, skill_manager):
    """Test executing a multi-stage composition."""
    composition = {
        "stages": [
            {
                "name": "search",
                "skill": "skill-a",
                "args": "${input}",
                "output": "search_results",
            },
            {
                "name": "analyze",
                "skill": "skill-b",
                "args": "${search_results}",
                "output": "analysis",
            },
            {
                "name": "synthesize",
                "skill": "skill-c",
                "args": "${analysis}",
                "output": "final_report",
            },
        ],
        "return": "${final_report}",
    }

    result = engine.execute(composition, "research topic")

    assert result.success
    assert result.output is not None
    assert len(skill_manager.execution_log) == 3


def test_variable_interpolation(engine):
    """Test variable interpolation in arguments."""
    engine.context = {"input": "test", "var1": "value1", "var2": "value2"}

    # Simple variable
    assert engine._interpolate("${input}") == "test"

    # Multiple variables
    assert engine._interpolate("${var1} and ${var2}") == "value1 and value2"

    # No variables
    assert engine._interpolate("plain text") == "plain text"


def test_dotted_path_resolution(engine):
    """Test resolving dotted paths in context."""
    engine.context = {
        "data": {"nested": {"value": "found"}},
        "simple": "value",
    }

    assert engine._resolve_path("simple") == "value"
    assert engine._resolve_path("data.nested.value") == "found"
    assert engine._resolve_path("nonexistent") is None


def test_dict_args_interpolation(engine, skill_manager):
    """Test interpolation with dict arguments."""
    composition = {
        "stages": [
            {
                "name": "stage1",
                "skill": "skill-a",
                "args": {"key1": "${input}", "key2": "static"},
                "output": "result",
            }
        ],
        "return": "${result}",
    }

    result = engine.execute(composition, "test")

    assert result.success
    # Check that dict args were passed
    assert len(skill_manager.execution_log) == 1


def test_missing_skill_error(engine):
    """Test error handling for missing skill."""
    composition = {
        "stages": [
            {
                "name": "stage1",
                "skill": "nonexistent-skill",
                "args": "${input}",
                "output": "result",
            }
        ],
        "return": "${result}",
    }

    result = engine.execute(composition, "test")

    assert not result.success
    assert result.error is not None
    assert "not found" in result.error


def test_stage_failure_stops_execution(engine, skill_manager):
    """Test that stage failure stops execution."""
    composition = {
        "stages": [
            {
                "name": "stage1",
                "skill": "skill-a",
                "args": "${input}",
                "output": "result1",
            },
            {
                "name": "stage2",
                "skill": "nonexistent-skill",
                "args": "${result1}",
                "output": "result2",
            },
            {
                "name": "stage3",
                "skill": "skill-c",
                "args": "${result2}",
                "output": "result3",
            },
        ],
        "return": "${result3}",
    }

    result = engine.execute(composition, "test")

    assert not result.success
    # Only first stage should execute
    assert len(skill_manager.execution_log) == 1


def test_context_accumulation(engine, skill_manager):
    """Test that context accumulates across stages."""
    composition = {
        "stages": [
            {
                "name": "stage1",
                "skill": "skill-a",
                "args": "${input}",
                "output": "result1",
            },
            {
                "name": "stage2",
                "skill": "skill-b",
                "args": "${result1}",
                "output": "result2",
            },
        ],
        "return": "${result1} and ${result2}",
    }

    result = engine.execute(composition, "test")

    assert result.success
    # Both results should be in context
    assert "result1" in engine.context
    assert "result2" in engine.context


def test_empty_composition(engine):
    """Test executing an empty composition."""
    composition = {"stages": [], "return": "${input}"}

    result = engine.execute(composition, "test")

    assert result.success
    assert result.output == "test"


def test_stage_without_output_var(engine, skill_manager):
    """Test stage without output variable."""
    composition = {
        "stages": [
            {
                "name": "stage1",
                "skill": "skill-a",
                "args": "${input}",
                # No output variable
            }
        ],
        "return": "${input}",
    }

    result = engine.execute(composition, "test")

    assert result.success
    assert len(skill_manager.execution_log) == 1
