"""Tests for plugin dependency resolution."""
from __future__ import annotations

import pytest
from lyra_core.plugins.dependency_resolver import (
    DependencyGraph,
    DependencyResolver,
)


class TestDependencyGraph:
    """Tests for DependencyGraph."""

    def test_add_dependency(self):
        graph = DependencyGraph()
        graph.add_dependency("plugin_a", "plugin_b")

        assert "plugin_b" in graph.get_dependencies("plugin_a")
        assert "plugin_a" in graph.get_dependents("plugin_b")

    def test_get_dependencies_empty(self):
        graph = DependencyGraph()
        assert graph.get_dependencies("unknown") == set()

    def test_get_dependents_empty(self):
        graph = DependencyGraph()
        assert graph.get_dependents("unknown") == set()

    def test_has_circular_dependency_simple(self):
        graph = DependencyGraph()
        graph.add_dependency("a", "b")
        graph.add_dependency("b", "a")

        assert graph.has_circular_dependency()

    def test_has_circular_dependency_complex(self):
        graph = DependencyGraph()
        graph.add_dependency("a", "b")
        graph.add_dependency("b", "c")
        graph.add_dependency("c", "a")

        assert graph.has_circular_dependency()

    def test_no_circular_dependency(self):
        graph = DependencyGraph()
        graph.add_dependency("a", "b")
        graph.add_dependency("b", "c")
        graph.add_dependency("a", "c")

        assert not graph.has_circular_dependency()

    def test_topological_sort_simple(self):
        graph = DependencyGraph()
        graph.add_dependency("a", "b")
        graph.add_dependency("b", "c")

        result = graph.topological_sort()
        # c should come before b, b before a
        assert result.index("c") < result.index("b")
        assert result.index("b") < result.index("a")

    def test_topological_sort_with_circular_raises(self):
        graph = DependencyGraph()
        graph.add_dependency("a", "b")
        graph.add_dependency("b", "a")

        with pytest.raises(ValueError, match="Circular dependency"):
            graph.topological_sort()

    def test_topological_sort_complex(self):
        graph = DependencyGraph()
        graph.add_dependency("app", "db")
        graph.add_dependency("app", "cache")
        graph.add_dependency("db", "config")
        graph.add_dependency("cache", "config")

        result = graph.topological_sort()
        # config should come first
        assert result.index("config") < result.index("db")
        assert result.index("config") < result.index("cache")
        assert result.index("db") < result.index("app")
        assert result.index("cache") < result.index("app")


class TestDependencyResolver:
    """Tests for DependencyResolver."""

    @pytest.fixture
    def resolver(self):
        return DependencyResolver()

    @pytest.fixture
    def plugin_file(self, tmp_path):
        plugin = tmp_path / "test_plugin.py"
        plugin.write_text(
            """
from lyra_core.plugins.registry import PluginManifest

manifest = PluginManifest(...)
"""
        )
        return plugin

    def test_analyze_plugin(self, resolver, plugin_file):
        resolver.analyze_plugin(plugin_file, "test_plugin")
        # Should not raise

    def test_analyze_nonexistent_plugin_raises(self, resolver):
        with pytest.raises(FileNotFoundError):
            resolver.analyze_plugin("/nonexistent/plugin.py", "test")

    def test_register_plugin_module(self, resolver):
        resolver.register_plugin_module("my_plugin", "my_plugin_module")
        # Should not raise

    def test_get_dependencies(self, resolver, tmp_path):
        # Create plugin A that imports plugin B
        plugin_a = tmp_path / "plugin_a.py"
        plugin_a.write_text("import plugin_b_module\n")

        plugin_b = tmp_path / "plugin_b.py"
        plugin_b.write_text("# plugin b\n")

        resolver.register_plugin_module("plugin_b", "plugin_b_module")
        resolver.analyze_plugin(plugin_a, "plugin_a")
        resolver.analyze_plugin(plugin_b, "plugin_b")

        deps = resolver.get_dependencies("plugin_a")
        assert "plugin_b" in deps

    def test_get_dependents(self, resolver, tmp_path):
        plugin_a = tmp_path / "plugin_a.py"
        plugin_a.write_text("import plugin_b_module\n")

        plugin_b = tmp_path / "plugin_b.py"
        plugin_b.write_text("# plugin b\n")

        resolver.register_plugin_module("plugin_b", "plugin_b_module")
        resolver.analyze_plugin(plugin_a, "plugin_a")
        resolver.analyze_plugin(plugin_b, "plugin_b")

        dependents = resolver.get_dependents("plugin_b")
        assert "plugin_a" in dependents

    def test_get_reload_order(self, resolver, tmp_path):
        # Create dependency chain: c <- b <- a
        plugin_a = tmp_path / "plugin_a.py"
        plugin_a.write_text("import plugin_b_module\n")

        plugin_b = tmp_path / "plugin_b.py"
        plugin_b.write_text("import plugin_c_module\n")

        plugin_c = tmp_path / "plugin_c.py"
        plugin_c.write_text("# plugin c\n")

        resolver.register_plugin_module("plugin_b", "plugin_b_module")
        resolver.register_plugin_module("plugin_c", "plugin_c_module")
        resolver.analyze_plugin(plugin_a, "plugin_a")
        resolver.analyze_plugin(plugin_b, "plugin_b")
        resolver.analyze_plugin(plugin_c, "plugin_c")

        order = resolver.get_reload_order(["plugin_a", "plugin_b", "plugin_c"])
        # c should come before b, b before a
        assert order.index("plugin_c") < order.index("plugin_b")
        assert order.index("plugin_b") < order.index("plugin_a")

    def test_get_reload_order_with_circular_raises(self, resolver, tmp_path):
        plugin_a = tmp_path / "plugin_a.py"
        plugin_a.write_text("import plugin_b_module\n")

        plugin_b = tmp_path / "plugin_b.py"
        plugin_b.write_text("import plugin_a_module\n")

        resolver.register_plugin_module("plugin_a", "plugin_a_module")
        resolver.register_plugin_module("plugin_b", "plugin_b_module")
        resolver.analyze_plugin(plugin_a, "plugin_a")
        resolver.analyze_plugin(plugin_b, "plugin_b")

        with pytest.raises(ValueError, match="Circular dependency"):
            resolver.get_reload_order(["plugin_a", "plugin_b"])

    def test_validate_reload_success(self, resolver, plugin_file):
        resolver.analyze_plugin(plugin_file, "test_plugin")
        is_valid, error = resolver.validate_reload("test_plugin")
        assert is_valid
        assert error is None

    def test_validate_reload_not_registered(self, resolver):
        is_valid, error = resolver.validate_reload("unknown_plugin")
        assert not is_valid
        assert "not registered" in error

    def test_validate_reload_file_not_found(self, resolver, tmp_path):
        plugin = tmp_path / "plugin.py"
        plugin.write_text("# test")
        resolver.analyze_plugin(plugin, "test_plugin")

        # Delete the file
        plugin.unlink()

        is_valid, error = resolver.validate_reload("test_plugin")
        assert not is_valid
        assert "not found" in error

    def test_validate_reload_circular_dependency(self, resolver, tmp_path):
        plugin_a = tmp_path / "plugin_a.py"
        plugin_a.write_text("import plugin_b_module\n")

        plugin_b = tmp_path / "plugin_b.py"
        plugin_b.write_text("import plugin_a_module\n")

        resolver.register_plugin_module("plugin_a", "plugin_a_module")
        resolver.register_plugin_module("plugin_b", "plugin_b_module")
        resolver.analyze_plugin(plugin_a, "plugin_a")
        resolver.analyze_plugin(plugin_b, "plugin_b")

        is_valid, error = resolver.validate_reload("plugin_a")
        assert not is_valid
        assert "Circular dependency" in error

    def test_get_affected_plugins(self, resolver, tmp_path):
        # Create dependency chain: d <- c <- b <- a
        plugin_a = tmp_path / "plugin_a.py"
        plugin_a.write_text("import plugin_b_module\n")

        plugin_b = tmp_path / "plugin_b.py"
        plugin_b.write_text("import plugin_c_module\n")

        plugin_c = tmp_path / "plugin_c.py"
        plugin_c.write_text("import plugin_d_module\n")

        plugin_d = tmp_path / "plugin_d.py"
        plugin_d.write_text("# plugin d\n")

        resolver.register_plugin_module("plugin_b", "plugin_b_module")
        resolver.register_plugin_module("plugin_c", "plugin_c_module")
        resolver.register_plugin_module("plugin_d", "plugin_d_module")
        resolver.analyze_plugin(plugin_a, "plugin_a")
        resolver.analyze_plugin(plugin_b, "plugin_b")
        resolver.analyze_plugin(plugin_c, "plugin_c")
        resolver.analyze_plugin(plugin_d, "plugin_d")

        # Reloading d should affect c, b, and a
        affected = resolver.get_affected_plugins("plugin_d")
        assert affected == {"plugin_d", "plugin_c", "plugin_b", "plugin_a"}

    def test_clear(self, resolver, plugin_file):
        resolver.analyze_plugin(plugin_file, "test_plugin")
        resolver.clear()

        is_valid, _ = resolver.validate_reload("test_plugin")
        assert not is_valid

    def test_analyze_plugin_with_syntax_error(self, resolver, tmp_path):
        plugin = tmp_path / "bad_plugin.py"
        plugin.write_text("def broken(\n")  # Syntax error

        # Should not raise, just skip dependency extraction
        resolver.analyze_plugin(plugin, "bad_plugin")

    def test_from_import_detection(self, resolver, tmp_path):
        plugin_a = tmp_path / "plugin_a.py"
        plugin_a.write_text("from plugin_b_module import something\n")

        plugin_b = tmp_path / "plugin_b.py"
        plugin_b.write_text("# plugin b\n")

        resolver.register_plugin_module("plugin_b", "plugin_b_module")
        resolver.analyze_plugin(plugin_a, "plugin_a")
        resolver.analyze_plugin(plugin_b, "plugin_b")

        deps = resolver.get_dependencies("plugin_a")
        assert "plugin_b" in deps
