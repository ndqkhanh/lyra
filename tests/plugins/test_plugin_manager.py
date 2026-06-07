"""
Tests for PluginManager and the Plugin protocol.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pytest

from src.hooks.hook import Hook, HookType
from src.plugins.manager import Plugin, PluginManager, _is_protocol_class
from src.tools.registry import ToolDef

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def manager() -> PluginManager:
    return PluginManager()


@pytest.fixture
def sample_plugin_file() -> str:
    """Write a minimal plugin .py file to a temp location and return its path."""
    code = """
from __future__ import annotations

from typing import Any, Dict, List

from src.hooks.hook import Hook, HookType
from src.plugins.manager import Plugin
from src.tools.registry import ToolDef


class MyTestPlugin:
    name = "test_plugin"
    version = "1.0.0"
    tools: List[ToolDef] = [
        ToolDef(name="greet", description="Say hello"),
    ]
    hooks: List[Hook] = [
        Hook(
            hook_id="greet_logger",
            hook_type=HookType.PRE_TOOL_USE,
            handler=lambda ctx: None,
            description="Log greet calls",
        ),
    ]

    async def initialize(self) -> None:
        self._initialized = True

    async def shutdown(self) -> None:
        self._shutdown = True
"""
    path = Path(tempfile.mkdtemp()) / "my_test_plugin.py"
    path.write_text(code)
    return str(path)


@pytest.fixture
def factory_plugin_file() -> str:
    """A plugin file exposing a ``create_plugin()`` factory."""
    code = """
from __future__ import annotations

from typing import Any, Dict, List

from src.hooks.hook import Hook, HookType
from src.plugins.manager import Plugin
from src.tools.registry import ToolDef


class _FactoryPlugin:
    name = "factory_plugin"
    version = "2.0.0"
    tools: List[ToolDef] = [
        ToolDef(name="ping", description="Ping tool"),
    ]
    hooks: List[Hook] = []

    async def initialize(self) -> None:
        self._initialized = True

    async def shutdown(self) -> None:
        self._shutdown = True


def create_plugin() -> Plugin:
    return _FactoryPlugin()
"""
    path = Path(tempfile.mkdtemp()) / "factory_plugin.py"
    path.write_text(code)
    return str(path)


@pytest.fixture
def invalid_plugin_file() -> str:
    """A .py file with no Plugin-compatible content."""
    code = "x = 42\n"
    path = Path(tempfile.mkdtemp()) / "invalid.py"
    path.write_text(code)
    return str(path)


# ---------------------------------------------------------------------------
# _is_protocol_class
# ---------------------------------------------------------------------------


class TestIsProtocolClass:
    def test_detects_protocol_class(self) -> None:
        assert _is_protocol_class(Plugin)

    def test_concrete_class_is_not_protocol(self) -> None:
        class Concrete:
            pass

        assert not _is_protocol_class(Concrete)


# ---------------------------------------------------------------------------
# PluginManager — load_plugin
# ---------------------------------------------------------------------------


class TestLoadPlugin:
    def test_load_from_class(self, manager: PluginManager, sample_plugin_file: str) -> None:
        plugin = manager.load_plugin(sample_plugin_file)
        assert plugin.name == "test_plugin"
        assert plugin.version == "1.0.0"
        assert len(plugin.tools) == 1
        assert plugin.tools[0].name == "greet"
        assert len(plugin.hooks) == 1
        assert plugin.hooks[0].hook_id == "greet_logger"

    def test_load_from_factory(self, manager: PluginManager, factory_plugin_file: str) -> None:
        plugin = manager.load_plugin(factory_plugin_file)
        assert plugin.name == "factory_plugin"
        assert plugin.version == "2.0.0"
        assert len(plugin.tools) == 1
        assert plugin.tools[0].name == "ping"

    def test_load_file_not_found(self, manager: PluginManager) -> None:
        with pytest.raises(FileNotFoundError):
            manager.load_plugin("/nonexistent/path.py")

    def test_load_not_a_py_file(self, manager: PluginManager) -> None:
        txt_file = Path(tempfile.mkdtemp()) / "plugin.txt"
        txt_file.write_text("content")
        with pytest.raises(ValueError, match=".py"):
            manager.load_plugin(str(txt_file))

    def test_load_invalid_content(self, manager: PluginManager, invalid_plugin_file: str) -> None:
        with pytest.raises(ValueError, match="No Plugin-compatible"):
            manager.load_plugin(invalid_plugin_file)

    def test_get_plugin(self, manager: PluginManager, sample_plugin_file: str) -> None:
        manager.load_plugin(sample_plugin_file)
        assert manager.get("test_plugin") is not None
        assert manager.get("nonexistent") is None


# ---------------------------------------------------------------------------
# PluginManager — enable / disable
# ---------------------------------------------------------------------------


class TestEnableDisable:
    def test_enable_disable_roundtrip(self, manager: PluginManager, sample_plugin_file: str) -> None:
        manager.load_plugin(sample_plugin_file)
        assert manager.is_enabled("test_plugin")

        manager.disable("test_plugin")
        assert not manager.is_enabled("test_plugin")

        manager.enable("test_plugin")
        assert manager.is_enabled("test_plugin")

    def test_disable_unknown_raises(self, manager: PluginManager) -> None:
        with pytest.raises(KeyError, match="Unknown"):
            manager.disable("unknown")

    def test_enable_unknown_raises(self, manager: PluginManager) -> None:
        with pytest.raises(KeyError, match="Unknown"):
            manager.enable("unknown")


# ---------------------------------------------------------------------------
# PluginManager — list_plugins
# ---------------------------------------------------------------------------


class TestListPlugins:
    def test_list_all(self, manager: PluginManager) -> None:
        assert manager.list_plugins() == []

    def test_list_with_plugins(self, manager: PluginManager, sample_plugin_file: str) -> None:
        manager.load_plugin(sample_plugin_file)
        entries = manager.list_plugins()
        assert len(entries) == 1
        assert entries[0]["name"] == "test_plugin"
        assert entries[0]["version"] == "1.0.0"
        assert entries[0]["enabled"] is True
        assert entries[0]["tool_count"] == 1
        assert entries[0]["hook_count"] == 1

    def test_list_disabled_excluded_by_default(
        self, manager: PluginManager, sample_plugin_file: str
    ) -> None:
        manager.load_plugin(sample_plugin_file)
        manager.disable("test_plugin")
        assert len(manager.list_plugins()) == 0

    def test_list_disabled_included(self, manager: PluginManager, sample_plugin_file: str) -> None:
        manager.load_plugin(sample_plugin_file)
        manager.disable("test_plugin")
        entries = manager.list_plugins(include_disabled=True)
        assert len(entries) == 1
        assert entries[0]["enabled"] is False


# ---------------------------------------------------------------------------
# PluginManager — lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    async def test_initialize_and_shutdown(self, manager: PluginManager, sample_plugin_file: str) -> None:
        plugin_obj = manager.load_plugin(sample_plugin_file)
        assert not hasattr(plugin_obj, "_initialized")

        await manager.initialize("test_plugin")
        assert plugin_obj._initialized is True

        await manager.shutdown("test_plugin")
        assert plugin_obj._shutdown is True

    async def test_initialize_unknown_raises(self, manager: PluginManager) -> None:
        with pytest.raises(KeyError):
            await manager.initialize("unknown")

    async def test_shutdown_unknown_raises(self, manager: PluginManager) -> None:
        with pytest.raises(KeyError):
            await manager.shutdown("unknown")

    async def test_initialize_all(
        self, manager: PluginManager, sample_plugin_file: str, factory_plugin_file: str
    ) -> None:
        p1 = manager.load_plugin(sample_plugin_file)
        p2 = manager.load_plugin(factory_plugin_file)
        await manager.initialize_all()
        assert p1._initialized is True
        assert p2._initialized is True

    async def test_shutdown_all(
        self, manager: PluginManager, sample_plugin_file: str, factory_plugin_file: str
    ) -> None:
        p1 = manager.load_plugin(sample_plugin_file)
        p2 = manager.load_plugin(factory_plugin_file)
        await manager.initialize_all()
        await manager.shutdown_all()
        assert p1._shutdown is True
        assert p2._shutdown is True

    async def test_disabled_skipped_during_initialize_all(
        self, manager: PluginManager, sample_plugin_file: str
    ) -> None:
        p = manager.load_plugin(sample_plugin_file)
        manager.disable("test_plugin")
        await manager.initialize_all()

        # For a disabled plugin, initialize_all skips it
        # The protocol check -> isinstance -> it is a Plugin, but _initialized
        # attribute is not set because initialize was not called
        assert not hasattr(p, "_initialized")


# ---------------------------------------------------------------------------
# PluginManager — tools / hooks aggregation
# ---------------------------------------------------------------------------


class TestAggregation:
    def test_all_tools(self, manager: PluginManager, sample_plugin_file: str) -> None:
        manager.load_plugin(sample_plugin_file)
        tools = manager.all_tools()
        assert len(tools) == 1
        assert tools[0].name == "greet"

    def test_all_tools_disabled_plugin_excluded(
        self, manager: PluginManager, sample_plugin_file: str
    ) -> None:
        manager.load_plugin(sample_plugin_file)
        manager.disable("test_plugin")
        assert manager.all_tools() == []

    def test_all_hooks(self, manager: PluginManager, sample_plugin_file: str) -> None:
        manager.load_plugin(sample_plugin_file)
        hooks = manager.all_hooks()
        assert len(hooks) == 1
        assert hooks[0].hook_id == "greet_logger"

    def test_all_hooks_disabled_plugin_excluded(
        self, manager: PluginManager, sample_plugin_file: str
    ) -> None:
        manager.load_plugin(sample_plugin_file)
        manager.disable("test_plugin")
        assert manager.all_hooks() == []
