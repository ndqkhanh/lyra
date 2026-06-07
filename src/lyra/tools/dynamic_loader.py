"""
Dynamic Tool Loader — deferred loading of tool implementations.

Provides ``DynamicToolLoader`` to register tool specifications (``ToolSpec``)
without loading the implementation module.  Implementation is imported on
first use via ``LazyToolProxy``, which transparently delegates to the real
handler after loading.
"""

from __future__ import annotations

import importlib
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from lyra.tools.registry import ToolDef, ToolHandler, ToolResult


# ---------------------------------------------------------------------------
# Tool specification
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolSpec:
    """Declarative specification of a tool, without a loaded handler.

    Attributes:
        name: Unique tool identifier (snake_case).
        description: Human-readable description.
        parameters: JSON Schema dict for parameter validation.
        module_path: Fully-qualified Python module path (e.g. ``lyra.tools.advanced_tools``).
        class_name: Class or function name to import from the module.
        capabilities: Optional list of capability tags.
        sandbox_requirements: Optional sandbox constraints dict.
    """

    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    module_path: str = ""
    class_name: str = ""
    capabilities: List[str] = field(default_factory=list)
    sandbox_requirements: Dict[str, Any] = field(default_factory=dict)

    def to_tool_def(self, handler: ToolHandler) -> ToolDef:
        """Convert this spec to a ``ToolDef`` with the given handler."""
        return ToolDef(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
            handler=handler,
            capabilities=self.capabilities,
            sandbox_requirements=self.sandbox_requirements,
        )


# ---------------------------------------------------------------------------
# Lazy tool proxy
# ---------------------------------------------------------------------------


class LazyToolProxy:
    """Transparent proxy that delays importing a tool's handler.

    The proxy stands in for a real ``ToolHandler`` (async callable).  On
    first invocation it imports the module from ``ToolSpec.module_path``,
    instantiates or retrieves ``ToolSpec.class_name``, and caches the
    result for subsequent calls.

    Parameters
    ----------
    spec:
        ``ToolSpec`` describing where to load the implementation from.
    """

    def __init__(self, spec: ToolSpec) -> None:
        self._spec = spec
        self._handler: Optional[ToolHandler] = None
        self._load_error: Optional[str] = None

    @property
    def spec(self) -> ToolSpec:
        return self._spec

    @property
    def loaded(self) -> bool:
        return self._handler is not None

    def _load(self) -> None:
        """Import the module and resolve the handler."""
        if self._handler is not None or self._load_error is not None:
            return

        try:
            module = importlib.import_module(self._spec.module_path)
        except ImportError as exc:
            self._load_error = (
                f"Failed to load module '{self._spec.module_path}' for "
                f"tool '{self._spec.name}': {exc}"
            )
            return

        if not self._spec.class_name:
            self._load_error = (
                f"ToolSpec for '{self._spec.name}' has no class_name"
            )
            return

        try:
            obj = getattr(module, self._spec.class_name)
        except AttributeError:
            self._load_error = (
                f"'{self._spec.module_path}' has no attribute "
                f"'{self._spec.class_name}'"
            )
            return

        # If it is a class, instantiate it (no-arg constructor)
        if isinstance(obj, type):
            try:
                self._handler = obj()
            except TypeError as exc:
                self._load_error = (
                    f"Could not instantiate '{self._spec.class_name}' "
                    f"from '{self._spec.module_path}': {exc}"
                )
                return
        elif callable(obj):
            # Assume it is an async function / callable
            self._handler = obj  # type: ignore[assignment]
        else:
            self._load_error = (
                f"'{self._spec.class_name}' from '{self._spec.module_path}' "
                f"is {type(obj).__name__}, not a callable handler"
            )

    async def __call__(self, **kwargs: Any) -> Dict[str, Any]:
        """Invoke the real handler, loading it if necessary."""
        self._load()

        if self._load_error:
            return {"success": False, "error": self._load_error}

        if self._handler is None:
            return {"success": False, "error": "Handler not loaded (unknown reason)"}

        return await self._handler(**kwargs)

    def __repr__(self) -> str:
        status = "loaded" if self._handler else "pending"
        return f"LazyToolProxy({self._spec.name}, {status})"


# ---------------------------------------------------------------------------
# Dynamic loader
# ---------------------------------------------------------------------------


class DynamicToolLoader:
    """Registry for deferred-loading tool specs.

    Similar to ``ToolRegistry`` but accepts ``ToolSpec`` objects that are
    not backed by a live handler until first invocation.  The loader
    produces ``ToolDef`` instances wrapped with ``LazyToolProxy``.

    Parameters
    ----------
    auto_register_target:
        Optional ``ToolRegistry`` instance to automatically register
        resolved ``ToolDef`` objects into after first load.
    """

    def __init__(self, auto_register_target: Any = None) -> None:
        self._specs: Dict[str, ToolSpec] = {}
        self._lazy_tools: Dict[str, ToolDef] = {}
        self._registry = auto_register_target

    # ---- lifecycle --------------------------------------------------------

    def register_tool_spec(self, spec: ToolSpec) -> None:
        """Register a tool spec without loading its implementation.

        Raises ``ValueError`` if a spec with the same name already exists.
        """
        if spec.name in self._specs:
            raise ValueError(f"Tool spec '{spec.name}' is already registered")
        self._specs[spec.name] = spec

    def unregister(self, name: str) -> Optional[ToolSpec]:
        """Unregister a tool spec by name.

        Returns the removed ``ToolSpec`` or ``None``.
        """
        spec = self._specs.pop(name, None)
        self._lazy_tools.pop(name, None)
        return spec

    def get_spec(self, name: str) -> Optional[ToolSpec]:
        """Retrieve a registered ``ToolSpec``."""
        return self._specs.get(name)

    def list_specs(self) -> List[ToolSpec]:
        """Return all registered tool specs."""
        return list(self._specs.values())

    def has_spec(self, name: str) -> bool:
        """Check if a spec is registered."""
        return name in self._specs

    # ---- lazy resolution --------------------------------------------------

    def load_on_first_use(self, name: str) -> Optional[ToolDef]:
        """Build (or retrieve) a lazy ``ToolDef`` for the named spec.

        On first call, creates a ``ToolDef`` that wraps the spec with a
        ``LazyToolProxy``.  The proxy will import the real implementation
        when the handler is first called.

        If ``auto_register_target`` was provided at construction, the
        resulting ``ToolDef`` is registered into that registry.
        """
        if name in self._lazy_tools:
            return self._lazy_tools[name]

        spec = self._specs.get(name)
        if spec is None:
            return None

        proxy = LazyToolProxy(spec)
        tool_def = spec.to_tool_def(proxy)
        self._lazy_tools[name] = tool_def

        if self._registry is not None:
            try:
                self._registry.register(tool_def)
            except ValueError:
                pass  # already registered

        return tool_def

    def load_all(self) -> List[ToolDef]:
        """Build lazy ``ToolDef`` for every registered spec.

        Returns the list of newly created ``ToolDef`` objects (already
        cached for subsequent calls).
        """
        loaded: List[ToolDef] = []
        for name in list(self._specs.keys()):
            td = self.load_on_first_use(name)
            if td is not None:
                loaded.append(td)
        return loaded

    def force_load(self, name: str) -> Optional[ToolHandler]:
        """Immediately import and resolve the handler for a spec.

        Returns the real underlying handler (not a ``LazyToolProxy``),
        or ``None`` if the spec does not exist or loading fails.
        """
        td = self.load_on_first_use(name)
        if td is None:
            return None

        handler = td.handler
        if isinstance(handler, LazyToolProxy):
            handler._load()  # type: ignore[attr-defined]
            # Return the real handler now that load has been triggered
            return handler._handler  # type: ignore[return-value]

        return handler

    # ---- stats ------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        """Return loader statistics."""
        loaded_count = sum(1 for td in self._lazy_tools.values() if td.handler and isinstance(td.handler, LazyToolProxy) and td.handler.loaded)
        pending_count = len(self._lazy_tools) - loaded_count
        return {
            "total_specs": len(self._specs),
            "lazy_tools_created": len(self._lazy_tools),
            "handlers_loaded": loaded_count,
            "handlers_pending": pending_count,
        }
