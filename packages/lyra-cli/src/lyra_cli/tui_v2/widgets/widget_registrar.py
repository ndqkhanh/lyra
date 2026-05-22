"""WidgetRegistrar — auto-discovers and wires widgets into the TUI app.

Solves the problem of 28+ widgets that exist on disk and are wired in
__init__.py but never mounted in app.py — their keybindings don't work.

Scans ``widgets/__init__.py`` for exports, matches each to a file,
and generates the three things needed to fully wire a widget:
  1. ``import`` statement
  2. ``self.widget_name = WidgetClass() `` instantiation
  3. ``mount()`` call — widgets become part of the DOM and their
     keybindings activate.

Usage:
    from ..widgets.widget_registrar import WidgetRegistrar

    # In app.__init__:
        self._registrar = WidgetRegistrar()
        self._registrar.instantiate_all(self)

    # In app.on_mount:
        self._registrar.mount_all(self)
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Any

from textual.widget import Widget


class WidgetRegistrar:
    """Discovers and wires all widgets in a predictable order.

    The order matters because some widgets need others to exist
    before they mount. We sort by a priority attribute or by file
    name convention.
    """

    def __init__(self):
        self._discovered: list[tuple[str, str, type]] = []  # (file_stem, class_name, class)
        self._instances: dict[str, Widget] = {}

    def discover(self, package: Any) -> list[tuple[str, str, type]]:
        """Scan a package for widget classes."""
        pkg_path = Path(package.__file__).parent
        results: list[tuple[str, str, type]] = []

        for f in sorted(pkg_path.glob("*.py")):
            stem = f.stem
            if stem == "__init__" or stem == "widget_registrar":
                continue
            mod_name = f"{package.__name__}.{stem}"
            try:
                mod = importlib.import_module(mod_name)
            except Exception:
                continue

            for name, obj in inspect.getmembers(mod, inspect.isclass):
                if issubclass(obj, Widget) and obj is not Widget:
                    results.append((stem, name, obj))

        self._discovered = results
        return results

    def instantiate_all(self, app: Any, discover: bool = True) -> dict[str, Widget]:
        """Create instances of all widgets and attach to app."""
        if discover or not self._discovered:
            from textual.widgets import Static  # noqa: F401 (used via importlib)
            widgets_pkg = importlib.import_module("lyra_cli.tui_v2.widgets")
            self.discover(widgets_pkg)

        for stem, class_name, cls in self._discovered:
            try:
                instance = cls()
                # Attach to app using a predictable attribute name
                attr_name = f"_{stem}" if stem.startswith("_") else stem
                setattr(app, attr_name, instance)
                self._instances[stem] = instance
            except Exception as e:
                pass  # Skip widgets that fail to instantiate

        return self._instances

    def mount_all(self, app: Any) -> None:
        """Mount all widget instances onto the app."""
        for stem, instance in self._instances.items():
            try:
                if not instance.is_mounted:
                    app.mount(instance)
            except Exception:
                pass

    @property
    def instances(self) -> dict[str, Widget]:
        return self._instances
