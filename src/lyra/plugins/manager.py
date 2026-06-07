"""
Plugin protocol and manager.

Defines the Plugin Protocol -- any object satisfying ``name``, ``version``,
``tools``, ``hooks``, ``initialize()``, and ``shutdown()`` is a plugin -- and
PluginManager that can load plugins from Python files, enable/disable them,
and enumerate the active set.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Sequence, runtime_checkable

from lyra.hooks.hook import Hook
from lyra.tools.registry import ToolDef

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Plugin protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class Plugin(Protocol):
    """Protocol any Lyra plugin must satisfy.

    Attributes:
        name: Short human-readable identifier (e.g. ``"filesystem"``).
        version: Semver string (e.g. ``"1.0.0"``).
        tools: Tool definitions this plugin contributes.
        hooks: Hook definitions this plugin contributes.

    Methods:
        initialize: Called once after loading to set up resources.
        shutdown: Called once during teardown to release resources.
    """

    name: str
    version: str
    tools: List[ToolDef]
    hooks: List[Hook]

    async def initialize(self) -> None:
        ...

    async def shutdown(self) -> None:
        ...


# ---------------------------------------------------------------------------
# Plugin Manager
# ---------------------------------------------------------------------------


class PluginManager:
    """Manages lifecycle and discovery of plugins.

    Typical usage::

        mgr = PluginManager()
        plugin = mgr.load_plugin("/path/to/my_plugin.py")
        await mgr.initialize("my_plugin")
        # ... use plugin.tools, plugin.hooks ...
        await mgr.shutdown("my_plugin")
    """

    def __init__(self) -> None:
        self._plugins: Dict[str, Plugin] = {}
        self._disabled: set[str] = set()

    # ---- loading -----------------------------------------------------------

    def load_plugin(self, path: str) -> Plugin:
        """Dynamically import a Python file as a plugin.

        The file must define either:
        * a top-level ``create_plugin()`` callable returning a ``Plugin``, or
        * exactly one class satisfying the ``Plugin`` protocol.

        Args:
            path: Absolute or relative filesystem path to a ``.py`` file.

        Returns:
            The loaded ``Plugin`` instance.

        Raises:
            FileNotFoundError: When *path* does not exist.
            ValueError: When the file does not expose a valid plugin.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Plugin file not found: {path}")
        if not p.suffix == ".py":
            raise ValueError(f"Plugin file must be a .py file, got: {p.suffix}")

        module_name = p.stem
        spec = importlib.util.spec_from_file_location(module_name, str(p))
        if spec is None or spec.loader is None:
            raise ValueError(f"Could not load spec from: {path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except SyntaxError as exc:
            raise ValueError(
                f"Syntax error in plugin file {path}: {exc}"
            ) from exc

        # 1. Look for a factory function
        factory = getattr(module, "create_plugin", None)
        if factory is not None and callable(factory):
            plugin: Any = factory()
            if _is_plugin_instance(plugin):
                self._plugins[plugin.name] = plugin
                logger.info("Loaded plugin %r from %s", plugin.name, path)
                return plugin

        # 2. Scan module for a Plugin-compatible class (instantiate it)
        for attr_name in dir(module):
            obj = getattr(module, attr_name)
            if isinstance(obj, type) and _has_plugin_shape(obj):
                # Instantiate the class
                try:
                    instance = obj()
                except Exception:
                    continue
                if _is_plugin_instance(instance):
                    self._plugins[instance.name] = instance
                    logger.info("Loaded plugin %r from %s", instance.name, path)
                    return instance
            elif _is_plugin_instance(obj):
                self._plugins[obj.name] = obj
                logger.info("Loaded plugin %r from %s", obj.name, path)
                return obj

        raise ValueError(
            f"No Plugin-compatible object found in {path}. "
            "The file must expose a `create_plugin()` factory or a top-level "
            "object that satisfies the Plugin protocol."
        )

    def get(self, name: str) -> Optional[Plugin]:
        """Retrieve a loaded plugin by name."""
        return self._plugins.get(name)

    def list_plugins(
        self, include_disabled: bool = False
    ) -> List[Dict[str, Any]]:
        """Return metadata for every loaded plugin.

        Args:
            include_disabled: When ``True`` also return disabled plugins.

        Returns:
            A list of dicts with keys ``name``, ``version``, ``enabled``,
            ``tool_count``, ``hook_count``.
        """
        result: List[Dict[str, Any]] = []
        for name, plugin in self._plugins.items():
            if not include_disabled and name in self._disabled:
                continue
            result.append(
                {
                    "name": plugin.name,
                    "version": plugin.version,
                    "enabled": name not in self._disabled,
                    "tool_count": len(plugin.tools),
                    "hook_count": len(plugin.hooks),
                }
            )
        return result

    # ---- enable / disable --------------------------------------------------

    def enable(self, name: str) -> None:
        """Enable a previously disabled plugin.

        Raises:
            KeyError: When *name* is not a loaded plugin.
        """
        if name not in self._plugins:
            raise KeyError(f"Unknown plugin: {name!r}")
        self._disabled.discard(name)

    def disable(self, name: str) -> None:
        """Disable a loaded plugin (without unloading it).

        Raises:
            KeyError: When *name* is not a loaded plugin.
        """
        if name not in self._plugins:
            raise KeyError(f"Unknown plugin: {name!r}")
        self._disabled.add(name)

    def is_enabled(self, name: str) -> bool:
        """Check whether a plugin is currently enabled."""
        return name not in self._disabled

    # ---- lifecycle ---------------------------------------------------------

    async def initialize(self, name: str) -> None:
        """Call ``initialize()`` on a loaded plugin.

        Raises:
            KeyError: When *name* is not a loaded plugin.
        """
        if name not in self._plugins:
            raise KeyError(f"Unknown plugin: {name!r}")
        await self._plugins[name].initialize()

    async def shutdown(self, name: str) -> None:
        """Call ``shutdown()`` on a loaded plugin.

        Raises:
            KeyError: When *name* is not a loaded plugin.
        """
        if name not in self._plugins:
            raise KeyError(f"Unknown plugin: {name!r}")
        await self._plugins[name].shutdown()

    async def initialize_all(self) -> None:
        """Call ``initialize()`` on every loaded plugin."""
        for name in list(self._plugins):
            if name not in self._disabled:
                await self._plugins[name].initialize()

    async def shutdown_all(self) -> None:
        """Call ``shutdown()`` on every loaded plugin."""
        for name in list(self._plugins):
            if name not in self._disabled:
                await self._plugins[name].shutdown()

    # ---- tools / hooks aggregation -----------------------------------------

    def all_tools(self) -> List[ToolDef]:
        """Aggregate ToolDefs from every enabled plugin."""
        tools: List[ToolDef] = []
        for name, plugin in self._plugins.items():
            if name not in self._disabled:
                tools.extend(plugin.tools)
        return tools

    def all_hooks(self) -> List[Hook]:
        """Aggregate Hooks from every enabled plugin."""
        hooks: List[Hook] = []
        for name, plugin in self._plugins.items():
            if name not in self._disabled:
                hooks.extend(plugin.hooks)
        return hooks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_protocol_class(cls: type) -> bool:
    """Return ``True`` if *cls* is a ``Protocol`` class (not a concrete impl)."""
    return hasattr(cls, "__annotations__") and "_is_protocol" in dir(cls)


def _has_plugin_shape(cls: type) -> bool:
    """Return ``True`` if *cls* has the attributes expected of a Plugin class.

    Checks for the structural shape (class-level attributes) rather than
    using ``isinstance(..., Plugin)`` which can return ``True`` for the
    class object itself when using ``@runtime_checkable``.
    """
    for attr in ("name", "version", "tools", "hooks"):
        if not hasattr(cls, attr):
            return False
    return hasattr(cls, "initialize") and hasattr(cls, "shutdown")


def _is_plugin_instance(obj: Any) -> bool:
    """Check whether *obj* is a concrete Plugin instance (not a class)."""
    if isinstance(obj, type):
        return False
    return isinstance(obj, Plugin)


__all__ = [
    "Plugin",
    "PluginManager",
    "_has_plugin_shape",
    "_is_plugin_instance",
    "_is_protocol_class",
]
