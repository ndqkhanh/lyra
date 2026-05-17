"""Tests for HookExecutor."""

import pytest
from pathlib import Path
from lyra_cli.core.hook_executor import HookExecutor, HookResult
from lyra_cli.core.hook_registry import HookRegistry
from lyra_cli.core.hook_metadata import HookType


@pytest.fixture
def hooks_dir(tmp_path):
    """Create a temporary hooks directory with test hooks."""
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()

    # Create validate-tool-params.md
    validate_md = hooks_dir / "validate-tool-params.md"
    validate_md.write_text("""---
name: validate-tool-params
description: Validate tool parameters
type: PreToolUse
script: validate_params.py
enabled: true
---

# Validate Tool Parameters Hook
""")

    return hooks_dir


@pytest.fixture
def executor(hooks_dir):
    """Create a HookExecutor with loaded hooks."""
    registry = HookRegistry([hooks_dir])
    registry.load_hooks()
    return HookExecutor(registry)


def test_execute_hooks(executor):
    """Test executing hooks of a specific type."""
    results = executor.execute_hooks(HookType.PRE_TOOL_USE)

    assert len(results) == 1
    assert isinstance(results[0], HookResult)


def test_execute_hooks_empty_type(executor):
    """Test executing hooks when no hooks of that type exist."""
    results = executor.execute_hooks(HookType.STOP)

    assert len(results) == 0


def test_hook_result_success(executor):
    """Test successful hook execution result."""
    results = executor.execute_hooks(HookType.PRE_TOOL_USE)

    assert results[0].success is True
    assert "validate-tool-params" in results[0].output
