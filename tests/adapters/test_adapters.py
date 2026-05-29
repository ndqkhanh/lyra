"""
Tests for cross-platform adapters.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from adapters.base import (
    AdapterFactory,
    ClaudeCodeAdapter,
    CursorAdapter,
    HarnessType,
    Hook,
    JetBrainsAdapter,
    Message,
    Response,
    Tool,
    VSCodeAdapter,
)


class TestMessage:
    """Tests for Message class."""

    def test_message_creation(self):
        """Test creating a message."""
        msg = Message(content="Hello", role="user")

        assert msg.content == "Hello"
        assert msg.role == "user"
        assert msg.metadata == {}

    def test_message_with_metadata(self):
        """Test message with metadata."""
        msg = Message(
            content="Test",
            role="assistant",
            metadata={"key": "value"},
        )

        assert msg.metadata["key"] == "value"


class TestResponse:
    """Tests for Response class."""

    def test_response_creation(self):
        """Test creating a response."""
        resp = Response(content="Response", success=True)

        assert resp.content == "Response"
        assert resp.success is True
        assert resp.error is None

    def test_response_with_error(self):
        """Test response with error."""
        resp = Response(
            content="",
            success=False,
            error="Connection failed",
        )

        assert resp.success is False
        assert resp.error == "Connection failed"


class TestTool:
    """Tests for Tool class."""

    def test_tool_creation(self):
        """Test creating a tool."""
        tool = Tool(
            name="test_tool",
            description="A test tool",
            parameters={"param1": "string"},
        )

        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.parameters["param1"] == "string"


class TestHook:
    """Tests for Hook class."""

    def test_hook_creation(self):
        """Test creating a hook."""
        handler = MagicMock()
        hook = Hook(
            event_type="pre_tool_use",
            handler=handler,
            priority=10,
        )

        assert hook.event_type == "pre_tool_use"
        assert hook.handler == handler
        assert hook.priority == 10


class TestClaudeCodeAdapter:
    """Tests for ClaudeCodeAdapter."""

    def test_adapter_creation(self):
        """Test creating Claude Code adapter."""
        adapter = ClaudeCodeAdapter()

        assert adapter.harness_type == HarnessType.CLAUDE_CODE
        assert not adapter.connected

    def test_initialize(self):
        """Test initializing adapter."""
        adapter = ClaudeCodeAdapter()
        result = adapter.initialize()

        assert result is True
        assert adapter.is_connected()

    def test_send_message(self):
        """Test sending message."""
        adapter = ClaudeCodeAdapter()
        adapter.initialize()

        msg = Message(content="Test message")
        response = adapter.send_message(msg)

        assert response.success is True
        assert "Processed" in response.content

    def test_register_tools(self):
        """Test registering tools."""
        adapter = ClaudeCodeAdapter()
        adapter.initialize()

        tools = [
            Tool(name="tool1", description="Tool 1", parameters={}),
            Tool(name="tool2", description="Tool 2", parameters={}),
        ]

        result = adapter.register_tools(tools)

        assert result is True
        assert len(adapter.tools) == 2

    def test_register_hooks(self):
        """Test registering hooks."""
        adapter = ClaudeCodeAdapter()
        adapter.initialize()

        hooks = [
            Hook(event_type="pre_tool", handler=MagicMock()),
            Hook(event_type="post_tool", handler=MagicMock()),
        ]

        result = adapter.register_hooks(hooks)

        assert result is True
        assert len(adapter.hooks) == 2

    def test_capabilities(self):
        """Test getting capabilities."""
        adapter = ClaudeCodeAdapter()
        caps = adapter.get_capabilities()

        assert caps["streaming"] is True
        assert caps["tools"] is True
        assert caps["hooks"] is True
        assert caps["multiline"] is True
        assert caps["autocomplete"] is True

    def test_disconnect(self):
        """Test disconnecting."""
        adapter = ClaudeCodeAdapter()
        adapter.initialize()

        result = adapter.disconnect()

        assert result is True
        assert not adapter.is_connected()


class TestCursorAdapter:
    """Tests for CursorAdapter."""

    def test_adapter_creation(self):
        """Test creating Cursor adapter."""
        adapter = CursorAdapter()

        assert adapter.harness_type == HarnessType.CURSOR
        assert not adapter.connected

    def test_initialize(self):
        """Test initializing adapter."""
        adapter = CursorAdapter()
        result = adapter.initialize()

        assert result is True
        assert adapter.is_connected()

    def test_send_message_not_connected(self):
        """Test sending message when not connected."""
        adapter = CursorAdapter()

        msg = Message(content="Test")
        response = adapter.send_message(msg)

        assert response.success is False
        assert "Not connected" in response.error

    def test_send_message_connected(self):
        """Test sending message when connected."""
        adapter = CursorAdapter()
        adapter.initialize()

        msg = Message(content="Test")
        response = adapter.send_message(msg)

        assert response.success is True
        assert "Cursor processed" in response.content

    def test_register_tools(self):
        """Test registering tools."""
        adapter = CursorAdapter()
        adapter.initialize()

        tools = [Tool(name="tool1", description="Tool 1", parameters={})]
        result = adapter.register_tools(tools)

        assert result is True
        assert len(adapter.tools) == 1

    def test_register_hooks(self):
        """Test registering hooks."""
        adapter = CursorAdapter()
        adapter.initialize()

        hooks = [Hook(event_type="pre_tool", handler=MagicMock())]
        result = adapter.register_hooks(hooks)

        assert result is True
        assert len(adapter.hooks) == 1

    def test_capabilities(self):
        """Test getting capabilities."""
        adapter = CursorAdapter()
        caps = adapter.get_capabilities()

        assert caps["streaming"] is True
        assert caps["tools"] is True
        assert caps["hooks"] is True


class TestVSCodeAdapter:
    """Tests for VSCodeAdapter."""

    def test_adapter_creation(self):
        """Test creating VS Code adapter."""
        adapter = VSCodeAdapter()

        assert adapter.harness_type == HarnessType.VSCODE
        assert not adapter.connected

    def test_initialize(self):
        """Test initializing adapter."""
        adapter = VSCodeAdapter()
        result = adapter.initialize()

        assert result is True
        assert adapter.is_connected()

    def test_send_message(self):
        """Test sending message."""
        adapter = VSCodeAdapter()
        adapter.initialize()

        msg = Message(content="Test")
        response = adapter.send_message(msg)

        assert response.success is True
        assert "VS Code processed" in response.content

    def test_capabilities(self):
        """Test getting capabilities."""
        adapter = VSCodeAdapter()
        caps = adapter.get_capabilities()

        assert caps["streaming"] is True
        assert caps["tools"] is True


class TestJetBrainsAdapter:
    """Tests for JetBrainsAdapter."""

    def test_adapter_creation(self):
        """Test creating JetBrains adapter."""
        adapter = JetBrainsAdapter()

        assert adapter.harness_type == HarnessType.JETBRAINS
        assert not adapter.connected

    def test_initialize(self):
        """Test initializing adapter."""
        adapter = JetBrainsAdapter()
        result = adapter.initialize()

        assert result is True
        assert adapter.is_connected()

    def test_send_message(self):
        """Test sending message."""
        adapter = JetBrainsAdapter()
        adapter.initialize()

        msg = Message(content="Test")
        response = adapter.send_message(msg)

        assert response.success is True
        assert "JetBrains processed" in response.content

    def test_capabilities(self):
        """Test getting capabilities."""
        adapter = JetBrainsAdapter()
        caps = adapter.get_capabilities()

        # JetBrains doesn't support streaming
        assert caps["streaming"] is False
        assert caps["tools"] is True


class TestAdapterFactory:
    """Tests for AdapterFactory."""

    def test_create_claude_code_adapter(self):
        """Test creating Claude Code adapter."""
        adapter = AdapterFactory.create_adapter(HarnessType.CLAUDE_CODE)

        assert isinstance(adapter, ClaudeCodeAdapter)

    def test_create_cursor_adapter(self):
        """Test creating Cursor adapter."""
        adapter = AdapterFactory.create_adapter(HarnessType.CURSOR)

        assert isinstance(adapter, CursorAdapter)

    def test_create_vscode_adapter(self):
        """Test creating VS Code adapter."""
        adapter = AdapterFactory.create_adapter(HarnessType.VSCODE)

        assert isinstance(adapter, VSCodeAdapter)

    def test_create_jetbrains_adapter(self):
        """Test creating JetBrains adapter."""
        adapter = AdapterFactory.create_adapter(HarnessType.JETBRAINS)

        assert isinstance(adapter, JetBrainsAdapter)

    def test_create_unsupported_adapter(self):
        """Test creating unsupported adapter."""
        with pytest.raises(ValueError):
            AdapterFactory.create_adapter(HarnessType.ZED)

    def test_detect_harness_default(self):
        """Test detecting harness (default)."""
        harness = AdapterFactory.detect_harness()

        # Should default to Claude Code
        assert harness == HarnessType.CLAUDE_CODE

    @patch.dict("os.environ", {"CURSOR_IDE": "1"})
    def test_detect_harness_cursor(self):
        """Test detecting Cursor harness."""
        harness = AdapterFactory.detect_harness()

        assert harness == HarnessType.CURSOR

    @patch.dict("os.environ", {"VSCODE_PID": "12345"})
    def test_detect_harness_vscode(self):
        """Test detecting VS Code harness."""
        harness = AdapterFactory.detect_harness()

        assert harness == HarnessType.VSCODE

    @patch.dict("os.environ", {"JETBRAINS_IDE": "1"})
    def test_detect_harness_jetbrains(self):
        """Test detecting JetBrains harness."""
        harness = AdapterFactory.detect_harness()

        assert harness == HarnessType.JETBRAINS


class TestAdapterIntegration:
    """Integration tests for adapters."""

    def test_adapter_lifecycle(self):
        """Test complete adapter lifecycle."""
        adapter = ClaudeCodeAdapter()

        # Initialize
        assert adapter.initialize()
        assert adapter.is_connected()

        # Register tools
        tools = [Tool(name="test", description="Test", parameters={})]
        assert adapter.register_tools(tools)

        # Register hooks
        hooks = [Hook(event_type="test", handler=MagicMock())]
        assert adapter.register_hooks(hooks)

        # Send message
        msg = Message(content="Test")
        response = adapter.send_message(msg)
        assert response.success

        # Disconnect
        assert adapter.disconnect()
        assert not adapter.is_connected()

    def test_multiple_adapters(self):
        """Test using multiple adapters."""
        adapters = [
            ClaudeCodeAdapter(),
            CursorAdapter(),
            VSCodeAdapter(),
            JetBrainsAdapter(),
        ]

        for adapter in adapters:
            assert adapter.initialize()
            assert adapter.is_connected()

            msg = Message(content="Test")
            response = adapter.send_message(msg)
            assert response.success

    def test_adapter_factory_workflow(self):
        """Test adapter factory workflow."""
        # Detect harness
        harness_type = AdapterFactory.detect_harness()

        # Create adapter
        adapter = AdapterFactory.create_adapter(harness_type)

        # Initialize and use
        assert adapter.initialize()
        assert adapter.is_connected()

        # Get capabilities
        caps = adapter.get_capabilities()
        assert isinstance(caps, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
