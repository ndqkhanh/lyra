"""Tests for HookRegistry."""

import pytest
from pathlib import Path
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

    # Create auto-format.md
    format_md = hooks_dir / "auto-format.md"
    format_md.write_text("""---
name: auto-format
description: Auto-format code
type: PostToolUse
script: auto_format.py
enabled: true
---

# Auto-Format Hook
""")

    return hooks_dir


def test_load_hooks(hooks_dir):
    """Test loading hooks from directory."""
    registry = HookRegistry([hooks_dir])
    registry.load_hooks()

    assert len(registry._hooks) == 2
    assert "validate-tool-params" in registry._hooks
    assert "auto-format" in registry._hooks


def test_get_hook(hooks_dir):
    """Test getting a hook by name."""
    registry = HookRegistry([hooks_dir])
    registry.load_hooks()

    hook = registry.get_hook("validate-tool-params")
    assert hook is not None
    assert hook.name == "validate-tool-params"
    assert hook.hook_type == HookType.PRE_TOOL_USE


def test_get_hooks_by_type(hooks_dir):
    """Test getting hooks by type."""
    registry = HookRegistry([hooks_dir])
    registry.load_hooks()

    pre_hooks = registry.get_hooks_by_type(HookType.PRE_TOOL_USE)
    assert len(pre_hooks) == 1
    assert pre_hooks[0].name == "validate-tool-params"

    post_hooks = registry.get_hooks_by_type(HookType.POST_TOOL_USE)
    assert len(post_hooks) == 1
    assert post_hooks[0].name == "auto-format"


def test_search_hooks(hooks_dir):
    """Test searching hooks."""
    registry = HookRegistry([hooks_dir])
    registry.load_hooks()

    results = registry.search_hooks("validate")
    assert len(results) == 1
    assert results[0].name == "validate-tool-params"


def test_list_hooks(hooks_dir):
    """Test listing all hooks."""
    registry = HookRegistry([hooks_dir])
    registry.load_hooks()

    hooks = registry.list_hooks()
    assert len(hooks) == 2
