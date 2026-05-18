"""Safe rendering utilities for TUI widgets.

Provides error handling wrappers that catch widget rendering exceptions
and display error placeholders instead of crashing the entire TUI.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

_log = logging.getLogger(__name__)


def safe_render(
    render_fn: Callable[[], str],
    *,
    widget_name: str = "widget",
    fallback: str | None = None,
) -> str:
    """Safely render a widget, catching exceptions and returning error placeholder.

    Args:
        render_fn: Function that returns rendered widget markup
        widget_name: Name of widget for error message
        fallback: Optional custom fallback text (default: error placeholder)

    Returns:
        Rendered widget markup, or error placeholder if rendering fails

    Example:
        >>> def render_agent_panel():
        ...     return agent_panel.render()
        >>> markup = safe_render(render_agent_panel, widget_name="agent_panel")
    """
    try:
        return render_fn()
    except Exception as e:
        _log.exception("Widget rendering error: %s", widget_name)
        if fallback is not None:
            return fallback
        return f"[red](error loading {widget_name})[/red]"


def safe_update(
    update_fn: Callable[[], None],
    *,
    widget_name: str = "widget",
    silent: bool = False,
) -> bool:
    """Safely update a widget, catching exceptions.

    Args:
        update_fn: Function that updates widget state
        widget_name: Name of widget for error message
        silent: If True, don't log exception (just return False)

    Returns:
        True if update succeeded, False if it failed

    Example:
        >>> def update_agent_list():
        ...     agent_panel.refresh_agents(new_agents)
        >>> success = safe_update(update_agent_list, widget_name="agent_panel")
    """
    try:
        update_fn()
        return True
    except Exception as e:
        if not silent:
            _log.exception("Widget update error: %s", widget_name)
        return False


class SafeWidget:
    """Mixin for widgets that want automatic error handling.

    Usage:
        class MyWidget(SafeWidget, Static):
            def _render_content(self) -> str:
                # Your rendering logic here
                return markup

            def render(self) -> str:
                return self.safe_render(
                    self._render_content,
                    widget_name="MyWidget"
                )
    """

    def safe_render(
        self,
        render_fn: Callable[[], str],
        *,
        widget_name: str | None = None,
        fallback: str | None = None,
    ) -> str:
        """Safe render wrapper for widget methods."""
        name = widget_name or self.__class__.__name__
        return safe_render(render_fn, widget_name=name, fallback=fallback)

    def safe_update(
        self,
        update_fn: Callable[[], None],
        *,
        widget_name: str | None = None,
        silent: bool = False,
    ) -> bool:
        """Safe update wrapper for widget methods."""
        name = widget_name or self.__class__.__name__
        return safe_update(update_fn, widget_name=name, silent=silent)


__all__ = [
    "safe_render",
    "safe_update",
    "SafeWidget",
]
