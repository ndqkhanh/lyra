"""Integration tests for the plugins system."""

import tempfile
from pathlib import Path

from lyra_plugins.discovery import discover_plugins
from lyra_plugins.loader import load_plugin
from lyra_plugins.manifest import PluginManifest, validate_manifest


class TestPluginDiscovery:
    """Plugin discovery from filesystem."""

    def test_discovers_plugins_in_directory(self):
        """Plugins with valid manifests are discovered."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin_dir = Path(tmp) / "my-plugin"
            plugin_dir.mkdir()
            (plugin_dir / "manifest.json").write_text(
                '{"name": "my-plugin", "version": "1.0", "entry_point": "main.py"}'
            )

            plugins = discover_plugins(Path(tmp))
            assert len(plugins) >= 1
            assert any(p["name"] == "my-plugin" for p in plugins)

    def test_ignores_directories_without_manifest(self):
        """Directories without manifest.json are skipped."""
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "not-a-plugin").mkdir()

            plugins = discover_plugins(Path(tmp))
            names = [p["name"] for p in plugins]
            assert "not-a-plugin" not in names


class TestPluginManifest:
    """Plugin manifest validation."""

    def test_valid_manifest_passes_validation(self):
        manifest = PluginManifest(
            name="test-plugin",
            version="1.0.0",
            description="A test plugin",
            author="test",
            entry_point="main.py",
        )
        errors = validate_manifest(manifest)
        assert len(errors) == 0

    def test_empty_name_fails_validation(self):
        manifest = PluginManifest(
            name="",
            version="1.0.0",
            description="",
            author="",
            entry_point="main.py",
        )
        errors = validate_manifest(manifest)
        assert len(errors) > 0

    def test_invalid_version_fails_validation(self):
        manifest = PluginManifest(
            name="test",
            version="not-a-version",
            description="",
            author="",
            entry_point="main.py",
        )
        errors = validate_manifest(manifest)
        assert len(errors) > 0


class TestPluginLoading:
    """Plugin loading and sandboxing."""

    def test_load_plugin_returns_module(self):
        """Loading a plugin returns a module with metadata."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin_dir = Path(tmp) / "test-plugin"
            plugin_dir.mkdir()
            (plugin_dir / "main.py").write_text(
                "PLUGIN_NAME = 'test-plugin'\ndef run(): return 'ok'\n"
            )
            (plugin_dir / "manifest.json").write_text(
                '{"name": "test-plugin", "version": "1.0", "entry_point": "main.py"}'
            )

            result = load_plugin(plugin_dir)
            assert result is not None
