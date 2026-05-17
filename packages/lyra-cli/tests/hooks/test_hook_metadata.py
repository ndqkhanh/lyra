"""Tests for HookMetadata."""

import pytest
from lyra_cli.core.hook_metadata import HookMetadata, HookType


def test_hook_metadata_creation():
    """Test creating a HookMetadata instance."""
    hook = HookMetadata(
        name="test-hook",
        description="Test hook description",
        hook_type=HookType.PRE_TOOL_USE,
        script="test_script.py"
    )
    assert hook.name == "test-hook"
    assert hook.description == "Test hook description"
    assert hook.hook_type == HookType.PRE_TOOL_USE
    assert hook.script == "test_script.py"
    assert hook.enabled is True
    assert hook.file_path is None


def test_hook_metadata_disabled():
    """Test creating a disabled hook."""
    hook = HookMetadata(
        name="disabled-hook",
        description="Disabled hook",
        hook_type=HookType.POST_TOOL_USE,
        script="disabled.py",
        enabled=False
    )
    assert hook.enabled is False


def test_hook_metadata_with_file_path():
    """Test HookMetadata with file path."""
    hook = HookMetadata(
        name="test-hook",
        description="Test description",
        hook_type=HookType.STOP,
        script="test.py",
        file_path="/path/to/hook.md"
    )
    assert hook.file_path == "/path/to/hook.md"
