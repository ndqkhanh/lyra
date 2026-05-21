"""
Tests for ECC Lifecycle Integration

Tests for bridging ECC hooks with Lyra's lifecycle system.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from pathlib import Path

from lyra_ecc.lifecycle_integration import ECCLifecycleIntegration, setup_ecc_hooks
from lyra_ecc.hooks import HookType, HookContext, HookResult


class TestECCLifecycleIntegration:
    """Test ECC lifecycle integration."""

    def test_integration_initialization(self):
        """Test integration initializes correctly."""
        lifecycle_bus = Mock()
        integration = ECCLifecycleIntegration(lifecycle_bus)

        assert integration is not None
        assert integration.ecc_engine is not None
        assert lifecycle_bus.subscribe.call_count == 3  # 3 event types (TOOL_CALL, SESSION_START, SESSION_END)

    def test_on_tool_call_event(self):
        """Test handling TOOL_CALL event."""
        lifecycle_bus = Mock()
        integration = ECCLifecycleIntegration(lifecycle_bus)

        context = {
            "tool": "Read",
            "file_path": "test.py",
            "args": {"limit": 100},
        }

        integration._on_tool_call(context)

        # Should have ECC hook fired marker in context
        assert context.get("ecc_hook_fired") is True

    def test_on_session_start_event(self):
        """Test handling SESSION_START event."""
        lifecycle_bus = Mock()
        integration = ECCLifecycleIntegration(lifecycle_bus)

        context = {}

        integration._on_session_start(context)

        assert context.get("ecc_hook_fired") is True

    def test_on_session_end_event(self):
        """Test handling SESSION_END event."""
        lifecycle_bus = Mock()
        integration = ECCLifecycleIntegration(lifecycle_bus)

        context = {}

        integration._on_session_end(context)

        assert context.get("ecc_hook_fired") is True

    def test_build_ecc_context(self):
        """Test building ECC context from lifecycle context."""
        lifecycle_bus = Mock()
        integration = ECCLifecycleIntegration(lifecycle_bus)

        lifecycle_context = {
            "tool": "Edit",  # Changed from "tool_name" to "tool"
            "file_path": "/path/to/file.py",
            "args": {"old_string": "foo", "new_string": "bar"},
        }

        ecc_context = integration._build_ecc_context(HookType.POST_TOOL_USE, lifecycle_context)

        assert ecc_context.event_type == HookType.POST_TOOL_USE
        assert ecc_context.tool_name == "Edit"
        assert ecc_context.file_path == Path("/path/to/file.py")
        assert ecc_context.args == {"old_string": "foo", "new_string": "bar"}

    def test_register_custom_hook(self):
        """Test registering custom hooks."""
        lifecycle_bus = Mock()
        integration = ECCLifecycleIntegration(lifecycle_bus)

        def custom_hook(context: HookContext) -> HookResult:
            return HookResult(success=True)

        initial_count = len(integration.ecc_engine.hooks[HookType.PRE_TOOL_USE])
        integration.register_custom_hook(HookType.PRE_TOOL_USE, custom_hook)

        assert len(integration.ecc_engine.hooks[HookType.PRE_TOOL_USE]) == initial_count + 1

    def test_get_hook_summary(self):
        """Test getting hook summary."""
        lifecycle_bus = Mock()
        integration = ECCLifecycleIntegration(lifecycle_bus)

        summary = integration.get_hook_summary()

        assert "hook_types" in summary
        assert "registered_hooks" in summary
        assert "total_hooks" in summary
        assert len(summary["hook_types"]) == 5  # 5 hook types
        assert summary["total_hooks"] > 0  # Default hooks registered


class TestSetupECCHooks:
    """Test setup_ecc_hooks helper."""

    def test_setup_ecc_hooks(self):
        """Test setup helper creates integration."""
        lifecycle_bus = Mock()

        integration = setup_ecc_hooks(lifecycle_bus)

        assert isinstance(integration, ECCLifecycleIntegration)
        assert integration.lifecycle_bus == lifecycle_bus
        assert lifecycle_bus.subscribe.call_count == 3  # 3 event types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
