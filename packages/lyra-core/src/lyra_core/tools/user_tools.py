"""Wave-D Task 10: load user-defined tools from ``~/.lyra/tools/``.

Drop a Python file there, decorate one-or-more callables with
:func:`tool`, and the loader returns a :class:`UserToolBundle` the
agent loop can register alongside the built-ins.

Why a marker decorator + import scan?

* The marker (``__lyra_tool__`` set by :func:`tool`) makes the
  loader **explicit**: a helper module that happens to live next to
  a tool file isn't accidentally promoted into the registry.
* The loader uses :mod:`importlib.util.spec_from_file_location` so
  files don't need to be on ``sys.path`` and module names don't
  collide across user tool files.
* Imports run inside ``try / except``; a broken file is recorded in
  ``errors`` instead of taking down the whole REPL boot.

The decorator's ``risk`` field flows into the permission stack and
the ``/tools`` table — ``"destructive"`` and ``"network"`` get
extra confirmation steps under ``strict`` mode.
"""
from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Literal


ToolRisk = Literal["safe", "network", "filesystem", "destructive"]
_VALID_RISKS: frozenset[str] = frozenset({"safe", "network", "filesystem", "destructive"})


@dataclass
class ToolDescriptor:
    """Single registry entry."""

    name: str
    fn: Callable[..., Any]
    description: str = ""
    risk: ToolRisk = "safe"
    source: str = ""  # absolute path of the file the tool came from


@dataclass
class UserToolBundle:
    """What :func:`load_user_tools` returns."""

    tools: dict[str, ToolDescriptor] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def names(self) -> list[str]:
        return sorted(self.tools.keys())


# ---------------------------------------------------------------------------
# Public decorator
# ---------------------------------------------------------------------------


def tool(
    *,
    name: str | None = None,
    description: str = "",
    risk: ToolRisk = "safe",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Mark a callable as a Lyra user tool.

    Usage::

        from lyra_core.tools.user_tools import tool

        @tool(description="echo the text", risk="safe")
        def echo(text: str = "") -> dict:
            return {"echoed": text}

    The decorator sets four attributes on the wrapped callable so
    :func:`load_user_tools` can find it without re-running the file.
    """
    if risk not in _VALID_RISKS:
        risk = "safe"

    def _wrap(fn: Callable[..., Any]) -> Callable[..., Any]:
        fn.__lyra_tool__ = True  # type: ignore[attr-defined]
        fn.__lyra_tool_name__ = name or fn.__name__  # type: ignore[attr-defined]
        fn.__lyra_tool_description__ = description  # type: ignore[attr-defined]
        fn.__lyra_tool_risk__ = risk  # type: ignore[attr-defined]
        return fn

    return _wrap


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def _scan_module(module: Any, *, source: Path) -> Iterable[ToolDescriptor]:
    """Yield every ``@tool``-marked callable, regardless of attr name.

    The marker ``__lyra_tool__`` is what makes a function a tool —
    walking by attr name would silently skip leading-underscore
    helpers (which is exactly the pattern users adopt when they
    want to hide a tool's wrapped target from ``import *``).
    """
    seen: set[int] = set()
    for attr in dir(module):
        obj = getattr(module, attr, None)
        if not callable(obj):
            continue
        if not getattr(obj, "__lyra_tool__", False):
            continue
        if id(obj) in seen:
            continue
        seen.add(id(obj))
        yield ToolDescriptor(
            name=getattr(obj, "__lyra_tool_name__", attr),
            fn=obj,
            description=getattr(obj, "__lyra_tool_description__", ""),
            risk=getattr(obj, "__lyra_tool_risk__", "safe"),
            source=str(source),
        )


def _import_user_file(path: Path) -> Any:
    """Return a module object for ``path``; raises on import failure."""
    mod_name = f"_lyra_user_tool_{path.stem}_{abs(hash(path)) & 0xFFFFFF:06x}"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"could not load spec for {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(mod_name, None)
        raise
    return module


def load_user_tools(*, user_dir: Path | str) -> UserToolBundle:
    """Scan ``user_dir`` for ``*.py`` files exporting :func:`tool`-decorated callables.

    Hidden files (``.foo.py``) and non-Python files are skipped.
    Import-time errors are recorded in :attr:`UserToolBundle.errors`
    instead of raised so a single bad file doesn't break boot.
    """
    bundle = UserToolBundle()
    root = Path(user_dir)
    if not root.exists() or not root.is_dir():
        return bundle

    for child in sorted(root.iterdir()):
        if not child.is_file():
            continue
        if child.suffix.lower() != ".py":
            continue
        if child.name.startswith("."):
            continue
        try:
            module = _import_user_file(child)
        except Exception as exc:
            bundle.errors.append(f"{child.name}: {type(exc).__name__}: {exc}")
            continue
        for desc in _scan_module(module, source=child):
            bundle.tools[desc.name] = desc
    return bundle


__all__ = [
    "ToolDescriptor",
    "ToolRisk",
    "UserToolBundle",
    "load_user_tools",
    "tool",
]
