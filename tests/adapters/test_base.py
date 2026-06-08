"""Tests for the HarnessAdapter base class (lyra.adapters.base).

Tests the abstract base class interface, concrete adapter implementations
(ClaudeCodeAdapter, CursorAdapter, VSCodeAdapter, JetBrainsAdapter),
and the AdapterFactory. These supplement the existing adapter tests in
test_adapters.py.
"""

from __future__ import annotations

from abc import ABC
from unittest.mock import MagicMock, patch

import pytest

from lyra.adapters.base import (
    AdapterFactory,
    ClaudeCodeAdapter,
    CursorAdapter,
    HarnessAdapter,
    HarnessType,
    Hook,
    JetBrainsAdapter,
    Message,
    Response,
    Tool,
    VSCodeAdapter,
)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class TestMessage:
    """Message dataclass."""

    def test_default_role(self) -> None:
        msg = Message(content="Hello")
        assert msg.role == "user"

    def test_mutable(self) -> None:
        """Message is not frozen — mutation is allowed."""
        msg = Message(content="Hi")
        msg.content = "changed"
        assert msg.content == "changed"

    def test_repr(self) -> None:
        msg = Message(content="Hello", role="assistant", metadata={"k": "v"})
        r = repr(msg)
        assert "Hello" in r


class TestResponse:
    """Response dataclass."""

    def test_default_success(self) -> None:
        resp = Response(content="ok")
        assert resp.success is True
        assert resp.error is None

    def test_mutable(self) -> None:
        """Response is not frozen — mutation is allowed."""
        resp = Response(content="ok")
        resp.content = "changed"
        assert resp.content == "changed"


class TestTool:
    """Tool dataclass."""

    def test_optional_handler(self) -> None:
        tool = Tool(name="t", description="d", parameters={})
        assert tool.handler is None


class TestHook:
    """Hook dataclass."""

    def test_default_priority(self) -> None:
        handler = MagicMock()
        hook = Hook(event_type="pre_tool", handler=handler)
        assert hook.priority == 0


# ---------------------------------------------------------------------------
# HarnessAdapter (abstract base)
# ---------------------------------------------------------------------------


class TestHarnessAdapter:
    """Abstract HarnessAdapter base class."""

    def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            HarnessAdapter(HarnessType.CLAUDE_CODE)  # type: ignore[abstract]

    def test_concrete_has_required_methods(self) -> None:
        """Concrete adapters must implement all abstract methods."""
        # All four adapters we have should instantiate without error
        for cls in (
            ClaudeCodeAdapter,
            CursorAdapter,
            VSCodeAdapter,
            JetBrainsAdapter,
        ):
            instance = cls()
            assert isinstance(instance, HarnessAdapter)
            assert isinstance(instance, ABC)

    def test_get_capabilities_defaults(self) -> None:
        """A minimal concrete class returns default capabilities."""
        class MinimalAdapter(HarnessAdapter):
            def initialize(self) -> bool:
                self.connected = True
                return True

            def send_message(self, message: Message) -> Response:
                return Response(content="", success=True)

            def receive_message(self) -> Message | None:
                return None

            def register_tools(self, tools: list[Tool]) -> bool:
                self.tools = tools
                return True

            def register_hooks(self, hooks: list[Hook]) -> bool:
                self.hooks = hooks
                return True

            def provider_name(self) -> str:
                return "minimal"

        adapter = MinimalAdapter(HarnessType.CLAUDE_CODE)
        caps = adapter.get_capabilities()
        assert caps == {
            "streaming": False,
            "tools": False,
            "hooks": False,
            "multiline": False,
            "autocomplete": False,
        }

    def test_disconnect_sets_connected_false(self) -> None:
        adapter = ClaudeCodeAdapter()
        adapter.connected = True
        result = adapter.disconnect()
        assert result is True
        assert adapter.connected is False
        assert adapter.is_connected() is False

    def test_is_connected_initial_false(self) -> None:
        adapter = ClaudeCodeAdapter()
        assert adapter.is_connected() is False
        assert adapter.connected is False


# ---------------------------------------------------------------------------
# HarnessType enum
# ---------------------------------------------------------------------------


class TestHarnessType:
    def test_all_members(self) -> None:
        names = {e.name for e in HarnessType}
        expected = {
            "CLAUDE_CODE",
            "CURSOR",
            "CODEX",
            "VSCODE",
            "JETBRAINS",
            "ZED",
            "GITHUB_COPILOT",
            "OPENCODE",
        }
        assert names == expected


# ---------------------------------------------------------------------------
# ClaudeCodeAdapter
# ---------------------------------------------------------------------------


class TestClaudeCodeAdapter:
    def test_harness_type(self) -> None:
        adapter = ClaudeCodeAdapter()
        assert adapter.harness_type == HarnessType.CLAUDE_CODE

    def test_initialize(self) -> None:
        adapter = ClaudeCodeAdapter()
        assert adapter.initialize() is True
        assert adapter.is_connected()

    def test_send_message(self) -> None:
        adapter = ClaudeCodeAdapter()
        adapter.initialize()

        resp = adapter.send_message(Message(content="Hi"))
        assert resp.success is True
        assert "Processed" in resp.content

    def test_receive_message_returns_none(self) -> None:
        adapter = ClaudeCodeAdapter()
        result = adapter.receive_message()
        assert result is None

    def test_register_tools(self) -> None:
        adapter = ClaudeCodeAdapter()
        tools = [Tool(name="t", description="d", parameters={})]
        assert adapter.register_tools(tools) is True
        assert adapter.tools == tools

    def test_register_hooks(self) -> None:
        adapter = ClaudeCodeAdapter()
        hooks = [Hook(event_type="e", handler=MagicMock())]
        assert adapter.register_hooks(hooks) is True
        assert adapter.hooks == hooks

    def test_capabilities_all_true(self) -> None:
        adapter = ClaudeCodeAdapter()
        caps = adapter.get_capabilities()
        assert all(caps.values())  # all True


# ---------------------------------------------------------------------------
# CursorAdapter
# ---------------------------------------------------------------------------


class TestCursorAdapter:
    def test_harness_type(self) -> None:
        adapter = CursorAdapter()
        assert adapter.harness_type == HarnessType.CURSOR

    def test_initialize(self) -> None:
        adapter = CursorAdapter()
        assert adapter.initialize() is True
        assert adapter.is_connected()

    def test_send_message_not_connected(self) -> None:
        adapter = CursorAdapter()
        resp = adapter.send_message(Message(content="Hi"))
        assert resp.success is False
        assert "Not connected" in resp.error

    def test_send_message_connected(self) -> None:
        adapter = CursorAdapter()
        adapter.initialize()
        resp = adapter.send_message(Message(content="Hi"))
        assert resp.success is True
        assert "Cursor processed" in resp.content

    def test_receive_message_not_connected(self) -> None:
        adapter = CursorAdapter()
        assert adapter.receive_message() is None

    def test_register_tools_not_connected(self) -> None:
        adapter = CursorAdapter()
        assert adapter.register_tools([]) is False

    def test_register_tools_connected(self) -> None:
        adapter = CursorAdapter()
        adapter.initialize()
        tools = [Tool(name="t", description="d", parameters={})]
        assert adapter.register_tools(tools) is True
        assert len(adapter.tools) == 1

    def test_register_hooks_not_connected(self) -> None:
        adapter = CursorAdapter()
        assert adapter.register_hooks([]) is False

    def test_register_hooks_connected(self) -> None:
        adapter = CursorAdapter()
        adapter.initialize()
        hooks = [Hook(event_type="e", handler=MagicMock())]
        assert adapter.register_hooks(hooks) is True
        assert len(adapter.hooks) == 1

    def test_capabilities(self) -> None:
        adapter = CursorAdapter()
        caps = adapter.get_capabilities()
        assert caps["streaming"] is True
        assert caps["tools"] is True

    def test_transform_message(self) -> None:
        adapter = CursorAdapter()
        result = adapter._transform_message(Message(content="Hello"))
        assert result == "Hello"

    def test_transform_tool(self) -> None:
        adapter = CursorAdapter()
        tool = Tool(name="my_tool", description="Does stuff", parameters={"x": "int"})
        result = adapter._transform_tool(tool)
        assert result["name"] == "my_tool"
        assert result["description"] == "Does stuff"
        assert result["parameters"] == {"x": "int"}

    def test_transform_hook(self) -> None:
        adapter = CursorAdapter()
        hook = Hook(event_type="post_tool", handler=MagicMock(), priority=5)
        result = adapter._transform_hook(hook)
        assert result["event"] == "post_tool"
        assert result["priority"] == 5


# ---------------------------------------------------------------------------
# VSCodeAdapter
# ---------------------------------------------------------------------------


class TestVSCodeAdapter:
    def test_harness_type(self) -> None:
        adapter = VSCodeAdapter()
        assert adapter.harness_type == HarnessType.VSCODE

    def test_initialize(self) -> None:
        adapter = VSCodeAdapter()
        assert adapter.initialize() is True
        assert adapter.is_connected()

    def test_send_message_not_connected(self) -> None:
        adapter = VSCodeAdapter()
        resp = adapter.send_message(Message(content="Hi"))
        assert resp.success is False

    def test_send_message_connected(self) -> None:
        adapter = VSCodeAdapter()
        adapter.initialize()
        resp = adapter.send_message(Message(content="Hi"))
        assert resp.success is True
        assert "VS Code processed" in resp.content

    def test_receive_message(self) -> None:
        adapter = VSCodeAdapter()
        assert adapter.receive_message() is None

    def test_register_tools(self) -> None:
        adapter = VSCodeAdapter()
        tools = [Tool(name="t", description="d", parameters={})]
        assert adapter.register_tools(tools) is True
        assert adapter.tools == tools

    def test_register_hooks(self) -> None:
        adapter = VSCodeAdapter()
        hooks = [Hook(event_type="e", handler=MagicMock())]
        assert adapter.register_hooks(hooks) is True
        assert adapter.hooks == hooks

    def test_capabilities(self) -> None:
        adapter = VSCodeAdapter()
        caps = adapter.get_capabilities()
        assert caps["streaming"] is True


# ---------------------------------------------------------------------------
# JetBrainsAdapter
# ---------------------------------------------------------------------------


class TestJetBrainsAdapter:
    def test_harness_type(self) -> None:
        adapter = JetBrainsAdapter()
        assert adapter.harness_type == HarnessType.JETBRAINS

    def test_initialize(self) -> None:
        adapter = JetBrainsAdapter()
        assert adapter.initialize() is True
        assert adapter.is_connected()

    def test_send_message_not_connected(self) -> None:
        adapter = JetBrainsAdapter()
        resp = adapter.send_message(Message(content="Hi"))
        assert resp.success is False
        assert "Not connected" in resp.error

    def test_send_message_connected(self) -> None:
        adapter = JetBrainsAdapter()
        adapter.initialize()
        resp = adapter.send_message(Message(content="Hi"))
        assert resp.success is True
        assert "JetBrains processed" in resp.content

    def test_capabilities_no_streaming(self) -> None:
        """JetBrains adapter explicitly disables streaming."""
        adapter = JetBrainsAdapter()
        caps = adapter.get_capabilities()
        assert caps["streaming"] is False
        assert caps["tools"] is True
        assert caps["hooks"] is True


# ---------------------------------------------------------------------------
# AdapterFactory
# ---------------------------------------------------------------------------


class TestAdapterFactory:
    """Factory pattern for creating harness adapters."""

    def test_create_claude_code(self) -> None:
        adapter = AdapterFactory.create_adapter(HarnessType.CLAUDE_CODE)
        assert isinstance(adapter, ClaudeCodeAdapter)

    def test_create_cursor(self) -> None:
        adapter = AdapterFactory.create_adapter(HarnessType.CURSOR)
        assert isinstance(adapter, CursorAdapter)

    def test_create_vscode(self) -> None:
        adapter = AdapterFactory.create_adapter(HarnessType.VSCODE)
        assert isinstance(adapter, VSCodeAdapter)

    def test_create_jetbrains(self) -> None:
        adapter = AdapterFactory.create_adapter(HarnessType.JETBRAINS)
        assert isinstance(adapter, JetBrainsAdapter)

    def test_unsupported_harness(self) -> None:
        with pytest.raises(ValueError, match="Unsupported harness type"):
            AdapterFactory.create_adapter(HarnessType.ZED)

    def test_unsupported_cod(self) -> None:
        with pytest.raises(ValueError, match="Unsupported harness type"):
            AdapterFactory.create_adapter(HarnessType.GITHUB_COPILOT)

    def test_detect_harness_default(self) -> None:
        harness = AdapterFactory.detect_harness()
        assert harness == HarnessType.CLAUDE_CODE

    @patch.dict("os.environ", {"CURSOR_IDE": "1"}, clear=True)
    def test_detect_harness_cursor(self) -> None:
        harness = AdapterFactory.detect_harness()
        assert harness == HarnessType.CURSOR

    @patch.dict("os.environ", {"VSCODE_PID": "12345"}, clear=True)
    def test_detect_harness_vscode(self) -> None:
        harness = AdapterFactory.detect_harness()
        assert harness == HarnessType.VSCODE

    @patch.dict("os.environ", {"JETBRAINS_IDE": "1"}, clear=True)
    def test_detect_harness_jetbrains(self) -> None:
        harness = AdapterFactory.detect_harness()
        assert harness == HarnessType.JETBRAINS

    def test_detect_precedence(self) -> None:
        """When multiple env vars are set, first match wins (Cursor)."""
        with patch.dict(
            "os.environ",
            {"CURSOR_IDE": "1", "VSCODE_PID": "999"},
            clear=True,
        ):
            harness = AdapterFactory.detect_harness()
            assert harness == HarnessType.CURSOR
