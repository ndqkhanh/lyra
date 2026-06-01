"""Dependency resolution for plugin hot-reload.

Analyzes plugin dependencies and determines safe reload order to prevent
breaking dependent plugins during hot-reload operations.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PluginDependency:
    """Represents a dependency between plugins."""

    plugin_name: str
    depends_on: str
    import_type: str  # "import", "from_import", "dynamic"


@dataclass
class DependencyGraph:
    """Dependency graph for plugins."""

    _edges: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    _reverse_edges: dict[str, set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )

    def add_dependency(self, plugin: str, depends_on: str) -> None:
        """Add a dependency edge: plugin depends on depends_on."""
        self._edges[plugin].add(depends_on)
        self._reverse_edges[depends_on].add(plugin)

    def get_dependencies(self, plugin: str) -> set[str]:
        """Get direct dependencies of a plugin."""
        return set(self._edges.get(plugin, set()))

    def get_dependents(self, plugin: str) -> set[str]:
        """Get plugins that depend on this plugin."""
        return set(self._reverse_edges.get(plugin, set()))

    def has_circular_dependency(self) -> bool:
        """Check if graph contains circular dependencies."""
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def visit(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in self._edges.get(node, set()):
                if neighbor not in visited:
                    if visit(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node in self._edges:
            if node not in visited:
                if visit(node):
                    return True

        return False

    def topological_sort(self) -> list[str]:
        """Return plugins in dependency order (dependencies first).

        Raises ValueError if circular dependencies exist.
        """
        if self.has_circular_dependency():
            raise ValueError("Circular dependency detected")

        in_degree: dict[str, int] = defaultdict(int)
        all_nodes = set(self._edges.keys()) | set(self._reverse_edges.keys())

        for node in all_nodes:
            in_degree[node] = len(self._edges.get(node, set()))

        queue = [node for node in all_nodes if in_degree[node] == 0]
        result: list[str] = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for dependent in self._reverse_edges.get(node, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        return result


class ImportAnalyzer(ast.NodeVisitor):
    """AST visitor to extract import statements from Python code."""

    def __init__(self) -> None:
        self.imports: list[tuple[str, str]] = []  # (module, type)

    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statement."""
        for alias in node.names:
            self.imports.append((alias.name, "import"))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from...import statement."""
        if node.module:
            self.imports.append((node.module, "from_import"))
        self.generic_visit(node)


class DependencyResolver:
    """Resolves plugin dependencies for safe hot-reload.

    Usage::

        resolver = DependencyResolver()
        resolver.analyze_plugin("/path/to/plugin.py", "my_plugin")
        order = resolver.get_reload_order(["my_plugin", "other_plugin"])
    """

    def __init__(self) -> None:
        self._graph = DependencyGraph()
        self._plugin_paths: dict[str, Path] = {}
        self._plugin_modules: dict[str, str] = {}  # plugin_name -> module_name

    def analyze_plugin(self, path: str | Path, plugin_name: str) -> None:
        """Analyze a plugin file and extract its dependencies."""
        plugin_path = Path(path).resolve()
        if not plugin_path.exists():
            raise FileNotFoundError(f"Plugin file not found: {path}")

        self._plugin_paths[plugin_name] = plugin_path

        # Parse the file to extract imports
        try:
            with open(plugin_path, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(plugin_path))

            analyzer = ImportAnalyzer()
            analyzer.visit(tree)

            # Add dependencies for imports that reference other plugins
            for module_name, import_type in analyzer.imports:
                # Check if this import refers to another known plugin
                if module_name in self._plugin_modules.values():
                    dep_plugin = next(
                        (
                            name
                            for name, mod in self._plugin_modules.items()
                            if mod == module_name
                        ),
                        None,
                    )
                    if dep_plugin and dep_plugin != plugin_name:
                        self._graph.add_dependency(plugin_name, dep_plugin)

        except (OSError, SyntaxError):
            # If we can't parse the file, assume no dependencies
            pass

    def register_plugin_module(self, plugin_name: str, module_name: str) -> None:
        """Register the module name for a plugin."""
        self._plugin_modules[plugin_name] = module_name

    def get_dependencies(self, plugin_name: str) -> set[str]:
        """Get direct dependencies of a plugin."""
        return self._graph.get_dependencies(plugin_name)

    def get_dependents(self, plugin_name: str) -> set[str]:
        """Get plugins that depend on this plugin."""
        return self._graph.get_dependents(plugin_name)

    def get_reload_order(self, plugins: list[str]) -> list[str]:
        """Get the order in which plugins should be reloaded.

        Returns plugins in dependency order (dependencies first).
        Raises ValueError if circular dependencies exist.
        """
        # Build subgraph for requested plugins
        subgraph = DependencyGraph()
        plugin_set = set(plugins)

        for plugin in plugins:
            for dep in self._graph.get_dependencies(plugin):
                if dep in plugin_set:
                    subgraph.add_dependency(plugin, dep)

        return subgraph.topological_sort()

    def validate_reload(self, plugin_name: str) -> tuple[bool, str | None]:
        """Validate if a plugin can be safely reloaded.

        Returns (is_valid, error_message).
        """
        # Check if plugin exists
        if plugin_name not in self._plugin_paths:
            return False, f"Plugin {plugin_name!r} not registered"

        # Check if file still exists
        plugin_path = self._plugin_paths[plugin_name]
        if not plugin_path.exists():
            return False, f"Plugin file not found: {plugin_path}"

        # Check for circular dependencies
        if self._graph.has_circular_dependency():
            return False, "Circular dependency detected in plugin graph"

        return True, None

    def get_affected_plugins(self, plugin_name: str) -> set[str]:
        """Get all plugins that would be affected by reloading this plugin.

        Returns the plugin itself plus all its dependents (recursively).
        """
        affected = {plugin_name}
        to_process = [plugin_name]

        while to_process:
            current = to_process.pop()
            dependents = self._graph.get_dependents(current)
            for dep in dependents:
                if dep not in affected:
                    affected.add(dep)
                    to_process.append(dep)

        return affected

    def clear(self) -> None:
        """Clear all dependency information."""
        self._graph = DependencyGraph()
        self._plugin_paths.clear()
        self._plugin_modules.clear()


__all__ = [
    "DependencyGraph",
    "DependencyResolver",
    "PluginDependency",
]
