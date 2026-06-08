"""Deep tests for src/lyra/plugins/manifest_discovery.py — 85%+ coverage target.

Tests ManifestPlugin, ManifestDiscovery, HotReloader, and DeferredLoader
with thorough error path and edge case coverage.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from lyra.plugins.manifest_discovery import (
    DeferredLoader,
    HotReloader,
    ManifestDiscovery,
    ManifestPlugin,
)
from lyra.plugins.manager import PluginManager


# =========================================================================
# ManifestPlugin
# =========================================================================


class TestManifestPlugin:
    def test_defaults(self):
        mp = ManifestPlugin(name="p1", version="1.0", path="/p/p1.py", manifest_path="/p/plugin.yaml")
        assert mp.capabilities == []
        assert mp.metadata == {}

    def test_with_capabilities_and_metadata(self):
        mp = ManifestPlugin(
            name="p1",
            version="1.0",
            path="/p/p1.py",
            manifest_path="/p/plugin.yaml",
            capabilities=["search", "format"],
            metadata={"author": "test"},
        )
        assert "search" in mp.capabilities
        assert mp.metadata["author"] == "test"


# =========================================================================
# ManifestDiscovery
# =========================================================================


class TestManifestDiscovery:
    @patch("lyra.plugins.manifest_discovery.Path.cwd")
    def test_default_paths_cwd_has_plugins(self, mock_cwd):
        mock_cwd.return_value = Path("/fake/cwd")
        with patch("pathlib.Path.is_dir") as mock_is_dir:
            mock_is_dir.return_value = True
            paths = ManifestDiscovery._default_paths()
            assert len(paths) >= 1
            assert "/fake/cwd/plugins" in paths

    @patch("lyra.plugins.manifest_discovery.Path.cwd")
    def test_default_paths_no_plugins_dir(self, mock_cwd):
        mock_cwd.return_value = Path("/tmp/nonexistent_cwd")
        paths = ManifestDiscovery._default_paths()
        # Falls back to cwd/plugins
        assert len(paths) == 1
        assert "/tmp/nonexistent_cwd/plugins" in paths[0]

    def test_discover_skips_non_directories(self, tmp_path):
        """Files in the search path that are not directories are skipped."""
        search_dir = tmp_path / "skippable"
        search_dir.mkdir()
        # A file, not a directory
        (search_dir / "not_a_dir.txt").write_text("hello")
        discovery = ManifestDiscovery(search_paths=[str(search_dir)])
        # This should not crash — child is a file, iterdir yields it, _scan_directory skips
        plugins = discovery.discover()
        assert plugins == []

    def test_discover_from_yaml(self, tmp_path):
        plugin_dir = tmp_path / "my_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.yaml").write_text(
            "name: my_plugin\nversion: 1.0.0\nentry: my_plugin.py\n"
            "capabilities:\n  - search\n  - format\n",
            encoding="utf-8",
        )
        (plugin_dir / "my_plugin.py").write_text("# stub", encoding="utf-8")
        discovery = ManifestDiscovery(search_paths=[str(tmp_path)])
        discovered = discovery.discover()
        assert len(discovered) == 1
        assert discovered[0].name == "my_plugin"

    def test_discover_from_yml(self, tmp_path):
        plugin_dir = tmp_path / "yml_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.yml").write_text(
            "name: yml_plugin\nversion: 0.5.0\nentry: main.py\n",
            encoding="utf-8",
        )
        (plugin_dir / "main.py").write_text("# stub", encoding="utf-8")
        discovery = ManifestDiscovery(search_paths=[str(tmp_path)])
        discovered = discovery.discover()
        assert len(discovered) == 1
        assert discovered[0].name == "yml_plugin"

    def test_discover_from_json(self, tmp_path):
        plugin_dir = tmp_path / "json_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(
            json.dumps({"name": "json_plugin", "version": "2.0.0", "entry": "main.py"}),
            encoding="utf-8",
        )
        (plugin_dir / "main.py").write_text("# stub", encoding="utf-8")
        discovery = ManifestDiscovery(search_paths=[str(tmp_path)])
        discovered = discovery.discover()
        assert len(discovered) == 1

    def test_discover_from_pyproject_toml(self, tmp_path):
        plugin_dir = tmp_path / "toml_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "pyproject.toml").write_text(
            '[tool.lyra.plugins.my_tool]\nversion = "3.0.0"\nentry = "tool.py"\n',
            encoding="utf-8",
        )
        (plugin_dir / "tool.py").write_text("# stub", encoding="utf-8")
        discovery = ManifestDiscovery(search_paths=[str(tmp_path)])
        discovered = discovery.discover()
        assert len(discovered) == 1
        assert discovered[0].name == "my_tool"

    def test_discover_scan_base_dir_directly(self, tmp_path):
        """discover() also scans the search dir itself for standalone manifests."""
        manifest = tmp_path / "plugin.yaml"
        manifest.write_text("name: standalone\nversion: 1.0\nentry: plugin.py\n", encoding="utf-8")
        (tmp_path / "plugin.py").write_text("# stub", encoding="utf-8")
        discovery = ManifestDiscovery(search_paths=[str(tmp_path)])
        discovered = discovery.discover()
        assert any(p.name == "standalone" for p in discovered)

    def test_discover_from_file(self, tmp_path):
        p = tmp_path / "plugin.yaml"
        p.write_text("name: file_pkg\nversion: 0.5.0\nentry: pkg.py\n", encoding="utf-8")
        (tmp_path / "pkg.py").write_text("# stub", encoding="utf-8")
        discovery = ManifestDiscovery()
        plugin = discovery.discover_from_file(str(p))
        assert plugin is not None
        assert plugin.name == "file_pkg"

    def test_discover_from_file_nonexistent(self):
        discovery = ManifestDiscovery()
        assert discovery.discover_from_file("/nonexistent/plugin.yaml") is None

    def test_discover_from_file_uses_parent_stem_as_name(self, tmp_path):
        """When manifest lacks a 'name' key, parent dir name is used."""
        p = tmp_path / "my_plugin" / "plugin.yaml"
        p.parent.mkdir(parents=True)
        p.write_text("version: 1.0\nentry: run.py\n", encoding="utf-8")
        (p.parent / "run.py").write_text("# stub", encoding="utf-8")
        discovery = ManifestDiscovery()
        plugin = discovery.discover_from_file(str(p))
        assert plugin is not None
        assert plugin.name == "my_plugin"

    def test_get_plugin(self, tmp_path):
        plugin_dir = tmp_path / "gp"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.yaml").write_text("name: gp\nversion: 1.0\nentry: gp.py\n", encoding="utf-8")
        (plugin_dir / "gp.py").write_text("# stub", encoding="utf-8")
        discovery = ManifestDiscovery(search_paths=[str(tmp_path)])
        discovery.discover()
        assert discovery.get_plugin("gp") is not None
        assert discovery.get_plugin("nonexistent") is None

    def test_list_plugins(self):
        discovery = ManifestDiscovery(search_paths=["/nonexistent"])
        assert discovery.list_plugins() == []

    # -- _read_manifest edge cases --

    def test_read_manifest_unsupported_format(self, tmp_path):
        p = tmp_path / "plugin.ini"
        p.write_text("[plugin]\nname=test\n", encoding="utf-8")
        discovery = ManifestDiscovery()
        result = discovery._read_manifest(p)
        assert result is None

    def test_read_manifest_yaml_parse_error(self, tmp_path):
        p = tmp_path / "plugin.yaml"
        p.write_text("name: valid", encoding="utf-8")
        discovery = ManifestDiscovery()
        # yaml is imported locally; path.read_text succeeds but yaml.safe_load fails
        with patch("pathlib.Path.read_text", return_value="name: valid"):
            with patch("yaml.safe_load", side_effect=Exception("parse failure")):
                result = discovery._read_manifest(p)
                assert result is None

    def test_read_manifest_yaml_nested_plugin_key(self, tmp_path):
        """YAML with a top-level 'plugin' key extracts that sub-dict."""
        p = tmp_path / "plugin.yaml"
        p.write_text("plugin:\n  name: nested\n  version: 1.0\n", encoding="utf-8")
        discovery = ManifestDiscovery()
        result = discovery._read_manifest(p)
        assert result is not None
        assert result.get("name") == "nested"

    def test_read_manifest_toml_no_tool_section(self, tmp_path):
        p = tmp_path / "pyproject.toml"
        p.write_text("[build-system]\nrequires = []\n", encoding="utf-8")
        discovery = ManifestDiscovery()
        result = discovery._read_manifest(p)
        assert result is None

    def test_read_manifest_toml_invalid_syntax(self, tmp_path):
        p = tmp_path / "pyproject.toml"
        p.write_text("[[[", encoding="utf-8")
        discovery = ManifestDiscovery()
        result = discovery._read_manifest(p)
        assert result is None

    def test_read_manifest_toml_missing_tomllib(self, tmp_path):
        p = tmp_path / "pyproject.toml"
        p.write_text("[tool.lyra.plugins.x]\nname=x\n", encoding="utf-8")
        with patch.dict("sys.modules", {"tomllib": None}):
            # Force import error by patching the import path
            import builtins
            real_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name in ("tomllib", "tomli"):
                    raise ImportError("No TOML parser")
                return real_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                discovery = ManifestDiscovery()
                result = discovery._read_manifest(p)
                assert result is None

    def test_read_manifest_pyproject_returns_first_plugin(self, tmp_path):
        p = tmp_path / "pyproject.toml"
        p.write_text(
            '[tool.lyra.plugins.first]\nversion="1.0"\n'
            '[tool.lyra.plugins.second]\nversion="2.0"\n',
            encoding="utf-8",
        )
        discovery = ManifestDiscovery()
        result = discovery._read_manifest(p)
        assert result is not None
        assert result["name"] == "first"

    def test_read_manifest_json_parse_error(self, tmp_path):
        p = tmp_path / "plugin.json"
        p.write_text("{bad json}", encoding="utf-8")
        discovery = ManifestDiscovery()
        result = discovery._read_manifest(p)
        assert result is None

    # -- discover() edge cases: search_path not a dir --

    def test_discover_skips_nonexistent_base(self):
        discovery = ManifestDiscovery(search_paths=["/definitely/nonexistent/path"])
        plugins = discovery.discover()
        assert plugins == []

    # -- _parse_pyproject_toml edge cases --

    def test_parse_pyproject_toml_empty_plugins(self, tmp_path):
        p = tmp_path / "pyproject.toml"
        p.write_text("[tool.lyra]\nother=1\n", encoding="utf-8")
        discovery = ManifestDiscovery()
        result = discovery._parse_pyproject_toml(p)
        assert result is None

    def test_parse_pyproject_toml_non_dict_plugin(self, tmp_path):
        p = tmp_path / "pyproject.toml"
        p.write_text('[tool.lyra.plugins]\nfoo="string_value"\n', encoding="utf-8")
        discovery = ManifestDiscovery()
        result = discovery._parse_pyproject_toml(p)
        assert result is None

    def test_parse_pyproject_toml_read_error(self, tmp_path):
        p = tmp_path / "pyproject.toml"
        p.write_text("", encoding="utf-8")
        discovery = ManifestDiscovery()
        result = discovery._parse_pyproject_toml(p)
        assert result is None


# =========================================================================
# HotReloader
# =========================================================================


class TestHotReloader:
    def test_watch_unknown_plugin(self):
        pm = PluginManager()
        hr = HotReloader(pm)
        assert hr.watch("nonexistent") is False

    def test_watch_known_plugin(self):
        """Watch a plugin that exists via a real file path."""
        pm = PluginManager()
        # Create a minimal plugin and load it
        class FakePlugin:
            name = "fakey"
            version = "1.0"
            tools = []
            hooks = []
            async def initialize(self): pass
            async def shutdown(self): pass

        pm._plugins["fakey"] = FakePlugin()

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(b"# test plugin")
            fname = f.name

        try:
            hr = HotReloader(pm)
            with patch("lyra.plugins.manifest_discovery.Path.exists", return_value=True):
                with patch("lyra.plugins.manifest_discovery.Path.stat") as mock_stat:
                    mock_stat.return_value.st_mtime = 100.0
                    result = hr.watch("fakey")
                    assert result is True
                    assert "fakey" in hr._watched
        finally:
            Path(fname).unlink(missing_ok=True)

    def test_watch_plugin_no_module_file(self):
        """When inspect.getmodule returns None, fallback path is used."""
        pm = PluginManager()
        class FakePlugin:
            name = "modless"
            version = "1.0"
            tools = []
            hooks = []
            async def initialize(self): pass
            async def shutdown(self): pass
        pm._plugins["modless"] = FakePlugin()

        hr = HotReloader(pm)
        with patch("inspect.getmodule", return_value=None):
            with patch("lyra.plugins.manifest_discovery.Path.stat") as mock_stat:
                mock_stat.return_value.st_mtime = 100.0
                result = hr.watch("modless")
                assert result is True
                assert "modless" in hr._watched

    def test_watch_plugin_inspect_raises(self):
        pm = PluginManager()
        class FakePlugin:
            name = "bad_inspect"
            version = "1.0"
            tools = []
            hooks = []
            async def initialize(self): pass
            async def shutdown(self): pass
        pm._plugins["bad_inspect"] = FakePlugin()

        hr = HotReloader(pm)
        with patch("inspect.getmodule", side_effect=Exception("boom")):
            with patch("lyra.plugins.manifest_discovery.Path.stat") as mock_stat:
                mock_stat.return_value.st_mtime = 100.0
                result = hr.watch("bad_inspect")
                assert result is True
                assert "bad_inspect" in hr._watched

    def test_list_watched_empty(self):
        pm = PluginManager()
        hr = HotReloader(pm)
        assert hr.list_watched() == []

    def test_unwatch_unknown(self):
        pm = PluginManager()
        hr = HotReloader(pm)
        assert hr.unwatch("nonexistent") is False

    def test_unwatch_known(self):
        pm = PluginManager()
        hr = HotReloader(pm)
        wp = ManifestPlugin(name="test", version="1.0", path="/p.py", manifest_path="/p.yaml")
        hr._watched["test"] = type("WatchedPlugin", (), {"name": "test", "path": "/p.py", "mtime": 0.0, "manifest_path": None})()  # type: ignore[arg-type]
        assert hr.unwatch("test") is True
        assert hr.list_watched() == []

    def test_poll_returns_empty_before_interval(self):
        pm = PluginManager()
        hr = HotReloader(pm, poll_interval=10.0)
        hr._last_poll = 0.0
        result = hr.poll()
        assert result == []

    def test_poll_detects_change_and_reloads(self):
        pm = PluginManager()
        hr = HotReloader(pm, poll_interval=0.0)

        # Seed a watched plugin with a past mtime
        import time
        hr._last_poll = 0.0
        hr._watched["test_plugin"] = type("_", (), {
            "name": "test_plugin",
            "path": "/fake/path.py",
            "mtime": 100.0,
            "manifest_path": None,
        })()

        with patch.object(hr, "_file_mtime", return_value=200.0):
            with patch.object(hr, "reload", return_value=True):
                result = hr.poll()
                assert "test_plugin" in result

    def test_poll_skips_when_mtime_unchanged(self):
        pm = PluginManager()
        hr = HotReloader(pm, poll_interval=0.0)
        hr._last_poll = 0.0
        hr._watched["stable"] = type("_", (), {
            "name": "stable",
            "path": "/fake/stable.py",
            "mtime": 100.0,
            "manifest_path": None,
        })()

        with patch.object(hr, "_file_mtime", return_value=100.0):
            result = hr.poll()
            assert result == []

    def test_poll_skips_when_mtime_none(self):
        pm = PluginManager()
        hr = HotReloader(pm, poll_interval=0.0)
        hr._last_poll = 0.0
        hr._watched["gone"] = type("_", (), {
            "name": "gone",
            "path": "/nonexistent/file.py",
            "mtime": 100.0,
            "manifest_path": None,
        })()

        with patch.object(hr, "_file_mtime", return_value=None):
            result = hr.poll()
            assert result == []

    def test_reload_unwatched_plugin(self):
        pm = PluginManager()
        hr = HotReloader(pm)
        assert hr.reload("unwatched") is False

    def test_reload_with_discovery_and_load(self):
        """reload uses ManifestDiscovery to re-discover and load."""
        pm = PluginManager()
        hr = HotReloader(pm)

        hr._watched["test"] = type("_", (), {
            "name": "test",
            "path": str(Path(tempfile.mkdtemp())),
            "mtime": 100.0,
            "manifest_path": None,
        })()

        with patch("lyra.plugins.manifest_discovery.ManifestDiscovery.discover_from_file") as mock_disc:
            mock_manifest = ManifestPlugin(
                name="test", version="1.0", path="/fake/plugin.py",
                manifest_path="/fake/plugin.yaml",
            )
            mock_disc.return_value = mock_manifest
            with patch.object(pm, "load_plugin") as mock_load:
                result = hr.reload("test")
                assert result is True
                mock_load.assert_called_once_with("/fake/plugin.py")

    def test_reload_discovery_returns_none(self):
        pm = PluginManager()
        hr = HotReloader(pm)
        hr._watched["test"] = type("_", (), {
            "name": "test",
            "path": str(Path(tempfile.mkdtemp())),
            "mtime": 100.0,
            "manifest_path": None,
        })()

        with patch("lyra.plugins.manifest_discovery.ManifestDiscovery.discover_from_file", return_value=None):
            result = hr.reload("test")
            assert result is False

    def test_reload_load_plugin_raises(self):
        pm = PluginManager()
        hr = HotReloader(pm)
        hr._watched["test"] = type("_", (), {
            "name": "test",
            "path": str(Path(tempfile.mkdtemp())),
            "mtime": 100.0,
            "manifest_path": None,
        })()

        with patch("lyra.plugins.manifest_discovery.ManifestDiscovery.discover_from_file") as mock_disc:
            mock_manifest = ManifestPlugin(
                name="test", version="1.0", path="/fake/plugin.py",
                manifest_path="/fake/plugin.yaml",
            )
            mock_disc.return_value = mock_manifest
            with patch.object(pm, "load_plugin", side_effect=Exception("load failed")):
                result = hr.reload("test")
                assert result is False

    def test_reload_shutdown_raises_still_continues(self):
        pm = PluginManager()
        hr = HotReloader(pm)
        hr._watched["test"] = type("_", (), {
            "name": "test",
            "path": str(Path(tempfile.mkdtemp())),
            "mtime": 100.0,
            "manifest_path": None,
        })()

        with patch("lyra.plugins.manifest_discovery.ManifestDiscovery.discover_from_file") as mock_disc:
            mock_manifest = ManifestPlugin(
                name="test", version="1.0", path="/fake/plugin.py",
                manifest_path="/fake/plugin.yaml",
            )
            mock_disc.return_value = mock_manifest
            with patch.object(pm, "load_plugin") as mock_load:
                with patch("asyncio.get_event_loop") as mock_loop:
                    mock_loop.return_value.run_until_complete.side_effect = Exception("shutdown failed")
                    result = hr.reload("test")
                    assert result is True
                    mock_load.assert_called_once()

    def test_file_mtime_os_error(self):
        with patch("pathlib.Path.stat", side_effect=OSError("no such file")):
            mtime = HotReloader._file_mtime("/nonexistent")
            assert mtime is None

    def test_file_mtime_success(self, tmp_path):
        f = tmp_path / "temp.py"
        f.write_text("# test")
        mtime = HotReloader._file_mtime(str(f))
        assert mtime is not None
        assert mtime > 0

    def test_watch_plugin_includes_manifest_path(self):
        pm = PluginManager()
        class FakePlugin:
            name = "with_manifest"
            version = "1.0"
            tools = []
            hooks = []
            async def initialize(self): pass
            async def shutdown(self): pass
        pm._plugins["with_manifest"] = FakePlugin()
        hr = HotReloader(pm)
        with patch("inspect.getmodule") as mock_getmod:
            mock_mod = MagicMock()
            mock_mod.__file__ = "/fake/path.py"
            mock_getmod.return_value = mock_mod
            with patch("lyra.plugins.manifest_discovery.Path.stat") as mock_stat:
                mock_stat.return_value.st_mtime = 100.0
                hr.watch("with_manifest")
                assert hr._watched["with_manifest"].path == "/fake/path.py"


# =========================================================================
# DeferredLoader
# =========================================================================


class TestDeferredLoader:
    def test_register_and_get(self):
        pm = PluginManager()
        dl = DeferredLoader(pm)

        def make_plugin():
            class FP:
                name = "deferred"
                version = "1.0.0"
                tools = []
                hooks = []
                async def initialize(self): pass
                async def shutdown(self): pass
            return FP()

        dl.register("deferred", make_plugin)
        plugin = dl.get("deferred")
        assert plugin is not None
        assert plugin.name == "deferred"

    def test_get_unknown(self):
        pm = PluginManager()
        dl = DeferredLoader(pm)
        assert dl.get("unknown") is None

    def test_is_loaded(self):
        pm = PluginManager()
        dl = DeferredLoader(pm)
        assert not dl.is_loaded("test")

    def test_is_loaded_via_manager(self):
        """is_loaded returns True if the plugin exists in manager already."""
        pm = PluginManager()
        class FP:
            name = "preloaded"
            version = "1.0"
            tools = []
            hooks = []
            async def initialize(self): pass
            async def shutdown(self): pass
        pm._plugins["preloaded"] = FP()

        dl = DeferredLoader(pm)
        assert dl.is_loaded("preloaded")
        assert dl.get("preloaded") is not None

    def test_registered_names(self):
        pm = PluginManager()
        dl = DeferredLoader(pm)
        dl.register("a", lambda: None)
        dl.register("b", lambda: None)
        assert "a" in dl.registered_names()
        assert "b" in dl.registered_names()

    def test_load_all(self):
        pm = PluginManager()
        dl = DeferredLoader(pm)
        count = [0]

        def make():
            count[0] += 1
            class FP:
                name = f"p{count[0]}"
                version = "1.0"
                tools = []
                hooks = []
                async def initialize(self): pass
                async def shutdown(self): pass
            return FP()

        dl.register("p1", make)
        dl.register("p2", make)
        n = dl.load_all()
        assert n == 2

    def test_load_all_already_loaded(self):
        """load_all should not re-load already-loaded plugins."""
        pm = PluginManager()
        dl = DeferredLoader(pm)
        dl.register("p1", lambda: type("FP", (), {
            "name": "p1", "version": "1.0", "tools": [], "hooks": [],
            "initialize": lambda self: None, "shutdown": lambda self: None,
        })())
        dl.load_all()
        # Second load_all should not increase the count
        n = dl.load_all()
        assert n == 0

    def test_get_loader_raises(self):
        """If the loader callable raises, get() returns None."""
        pm = PluginManager()
        dl = DeferredLoader(pm)

        def failing_loader():
            raise RuntimeError("loader failure")

        dl.register("broken", failing_loader)
        result = dl.get("broken")
        assert result is None
