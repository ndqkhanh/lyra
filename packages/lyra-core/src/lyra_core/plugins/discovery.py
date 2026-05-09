"""Entry-point–based plugin discovery for ``lyra.plugins``.

This module hosts the small "duck-typed" plugin surface used by both
the legacy :class:`lyra_core.agent.AgentLoop` cascade and the new
:class:`lyra_core.hooks.lifecycle.LifecycleBus` (Phase D.4 in
``lyra-cli``). Plugins do not need to subclass anything — they simply
expose hook methods (``on_turn_start``, ``on_tool_call`` …) and Lyra's
runtime invokes whichever methods exist.

Plugins are discovered from the ``lyra.plugins`` entry-point group at
REPL boot. Discovery is best-effort: a plugin that fails to import
or instantiate is skipped silently so one broken third-party plugin
can never block the agent from starting. ``extra`` lets the CLI
register in-process plugins without requiring a distribution install
— useful for tests and demos.

This module was lifted out of the legacy ``lyra_core.plugins`` module
so the ``lyra_core/plugins/`` package — which now coexists with the
older ``plugins.py`` — can re-export ``discover_plugins`` without the
package shadowing making the symbol unreachable.
"""
from __future__ import annotations

from typing import Any, List, Mapping, Protocol, runtime_checkable

__all__ = ["Plugin", "discover_plugins", "fire"]


@runtime_checkable
class Plugin(Protocol):
    """Duck-typed plugin protocol.

    All methods are optional. A plugin contributes a hook simply by
    defining the matching method; missing methods are silently skipped.

    Lifecycle hooks (added in v2.6.0):

    * ``on_session_start(payload: dict)``
    * ``on_turn_start(payload: dict)``
    * ``on_turn_complete(payload: dict)``
    * ``on_turn_rejected(payload: dict)``
    * ``on_tool_call(payload: dict)``
    * ``on_session_end(payload: dict)``

    A plugin can also implement
    ``on_lifecycle_event(event_name: str, payload: dict)`` to receive
    every event without binding to specific names.
    """

    def on_session_start(self, ctx: Any) -> None: ...  # pragma: no cover
    def pre_llm_call(self, ctx: Any) -> None: ...  # pragma: no cover
    def pre_tool_call(self, ctx: Any) -> None: ...  # pragma: no cover
    def on_session_end(self, ctx: Any) -> None: ...  # pragma: no cover


_ENTRY_POINT_GROUP = "lyra.plugins"


def discover_plugins(*, extra: list | None = None) -> List[Any]:
    """Load plugins from the ``lyra.plugins`` entry-point group.

    Returns a list of instantiated plugin objects. ``extra`` is
    appended *after* discovered plugins — the CLI uses this to
    register in-process plugins without requiring a full
    distribution install.

    Discovery is best-effort: any single broken plugin (import error,
    constructor crash, etc.) is silently skipped. The remaining
    plugins still load.
    """
    plugins: List[Any] = []
    try:
        from importlib.metadata import entry_points
    except Exception:  # pragma: no cover - stdlib always present on 3.9+
        return list(extra or [])

    try:
        eps = entry_points()
        # ``entry_points`` returns different shapes across stdlib versions.
        group: list = []
        if hasattr(eps, "select"):
            group = list(eps.select(group=_ENTRY_POINT_GROUP))
        elif isinstance(eps, Mapping):  # type: ignore[unreachable]
            group = list(eps.get(_ENTRY_POINT_GROUP, []))  # type: ignore[call-arg]
        for ep in group:
            try:
                plugin_cls = ep.load()
                plugins.append(
                    plugin_cls() if isinstance(plugin_cls, type) else plugin_cls
                )
            except Exception:
                # One broken plugin must not break the agent.
                continue
    except Exception:
        pass

    if extra:
        plugins.extend(extra)
    return plugins


def fire(plugins: list, hook: str, ctx: Any) -> None:
    """Invoke ``hook`` on every plugin that defines it (duck-typed).

    Errors raised by plugin code are propagated — callers (the chat
    loop, lifecycle bus subscribers) are responsible for wrapping
    invocations they don't trust.
    """
    for plugin in plugins:
        fn = getattr(plugin, hook, None)
        if callable(fn):
            fn(ctx)
