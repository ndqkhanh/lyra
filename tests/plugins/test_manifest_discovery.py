"""Tests for src/plugins/manifest_discovery.py and marketplace.py."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from lyra.plugins.manifest_discovery import (
    ManifestDiscovery,
    ManifestPlugin,
    HotReloader,
    DeferredLoader,
)
from lyra.plugins.marketplace import PluginMarketplace, MarketPlugin
from lyra.plugins.manager import PluginManager


# ---------------------------------------------------------------------------
# ManifestDiscovery
# ---------------------------------------------------------------------------


class TestManifestDiscovery:
    def test_discover_no_plugins_dir(self, tmp_path):
        discovery = ManifestDiscovery(search_paths=[str(tmp_path / "nonexistent")])
        plugins = discovery.discover()
        assert plugins == []

    def test_discover_from_yaml(self, tmp_path):
        plugin_dir = tmp_path / "my_plugin"
        plugin_dir.mkdir()
        manifest = plugin_dir / "plugin.yaml"
        manifest.write_text(
            "name: my_plugin\nversion: 1.0.0\nentry: my_plugin.py\n"
            "capabilities:\n  - search\n  - format\n",
            encoding="utf-8",
        )
        plugin_file = plugin_dir / "my_plugin.py"
        plugin_file.write_text("# plugin stub", encoding="utf-8")

        discovery = ManifestDiscovery(search_paths=[str(tmp_path)])
        discovered = discovery.discover()
        assert len(discovered) == 1
        assert discovered[0].name == "my_plugin"
        assert discovered[0].version == "1.0.0"
        assert "search" in discovered[0].capabilities

    def test_discover_from_json(self, tmp_path):
        plugin_dir = tmp_path / "json_plugin"
        plugin_dir.mkdir()
        manifest = plugin_dir / "plugin.json"
        manifest.write_text(
            json.dumps({"name": "json_plugin", "version": "2.0.0", "entry": "main.py"}),
            encoding="utf-8",
        )
        (plugin_dir / "main.py").write_text("# stub", encoding="utf-8")

        discovery = ManifestDiscovery(search_paths=[str(tmp_path)])
        discovered = discovery.discover()
        assert len(discovered) == 1
        assert discovered[0].name == "json_plugin"

    def test_discover_from_file(self, tmp_path):
        manifest_path = tmp_path / "plugin.yaml"
        manifest_path.write_text(
            "name: test_pkg\nversion: 0.5.0\nentry: pkg.py\n",
            encoding="utf-8",
        )
        (tmp_path / "pkg.py").write_text("# stub", encoding="utf-8")

        discovery = ManifestDiscovery()
        plugin = discovery.discover_from_file(str(manifest_path))
        assert plugin is not None
        assert plugin.name == "test_pkg"

    def test_discover_from_file_nonexistent(self):
        discovery = ManifestDiscovery()
        assert discovery.discover_from_file("/nonexistent/plugin.yaml") is None

    def test_get_plugin(self, tmp_path):
        plugin_dir = tmp_path / "gp"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.yaml").write_text(
            "name: gp\nversion: 1.0.0\nentry: gp.py\n", encoding="utf-8",
        )
        (plugin_dir / "gp.py").write_text("# stub", encoding="utf-8")

        discovery = ManifestDiscovery(search_paths=[str(tmp_path)])
        discovery.discover()
        plugin = discovery.get_plugin("gp")
        assert plugin is not None
        assert plugin.name == "gp"
        assert discovery.get_plugin("nonexistent") is None

    def test_list_plugins(self, tmp_path):
        discovery = ManifestDiscovery(search_paths=[str(tmp_path / "empty")])
        assert discovery.list_plugins() == []


# ---------------------------------------------------------------------------
# HotReloader
# ---------------------------------------------------------------------------


class TestHotReloader:
    def test_watch_unknown_plugin(self):
        pm = PluginManager()
        hr = HotReloader(pm)
        assert hr.watch("nonexistent") is False

    def test_list_watched_empty(self):
        pm = PluginManager()
        hr = HotReloader(pm)
        assert hr.list_watched() == []

    def test_unwatch_unknown(self):
        pm = PluginManager()
        hr = HotReloader(pm)
        assert hr.unwatch("nonexistent") is False

    def test_poll_idempotent(self):
        pm = PluginManager()
        hr = HotReloader(pm, poll_interval=0.0)
        result = hr.poll()
        assert result == []


# ---------------------------------------------------------------------------
# DeferredLoader
# ---------------------------------------------------------------------------


class TestDeferredLoader:
    def test_register_and_get(self):
        pm = PluginManager()
        dl = DeferredLoader(pm)

        def make_plugin():
            class FakePlugin:
                name = "deferred"
                version = "1.0.0"
                tools = []
                hooks = []
                async def initialize(self): pass
                async def shutdown(self): pass
            return FakePlugin()

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

    def test_register_no_loader_error(self):
        pm = PluginManager()
        dl = DeferredLoader(pm)
        assert dl.get("missing") is None

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


# ---------------------------------------------------------------------------
# PluginMarketplace
# ---------------------------------------------------------------------------


class TestPluginMarketplace:
    def test_load_registry(self, tmp_path):
        pm = PluginManager()
        mp = PluginMarketplace(pm, install_dir=str(tmp_path / "plugins"))
        reg_file = tmp_path / "registry.json"
        reg_file.write_text(
            json.dumps([
                {"name": "search", "version": "1.0.0", "description": "Search plugin", "author": "lyra"},
                {"name": "format", "version": "2.0.0", "description": "Format plugin", "rating": 4.5},
            ]),
            encoding="utf-8",
        )
        count = mp.load_registry(str(reg_file))
        assert count == 2

    def test_load_registry_nonexistent(self):
        pm = PluginManager()
        mp = PluginMarketplace(pm)
        assert mp.load_registry("/nonexistent/reg.json") == 0

    def test_search(self, tmp_path):
        pm = PluginManager()
        mp = PluginMarketplace(pm, install_dir=str(tmp_path / "plugins"))
        reg_file = tmp_path / "registry.json"
        reg_file.write_text(
            json.dumps([
                {"name": "search", "version": "1.0.0", "description": "Search tool", "tags": ["search", "utility"]},
                {"name": "viz", "version": "1.0.0", "description": "Visualization tool", "tags": ["viz"]},
            ]),
            encoding="utf-8",
        )
        mp.load_registry(str(reg_file))
        results = mp.search("search")
        assert len(results) == 1
        assert results[0].name == "search"

    def test_search_empty_query(self, tmp_path):
        pm = PluginManager()
        mp = PluginMarketplace(pm, install_dir=str(tmp_path / "plugins"))
        reg_file = tmp_path / "registry.json"
        reg_file.write_text(
            json.dumps([{"name": "a", "version": "1.0"}, {"name": "b", "version": "1.0"}]),
            encoding="utf-8",
        )
        mp.load_registry(str(reg_file))
        assert len(mp.search("")) == 2

    def test_get_details(self, tmp_path):
        pm = PluginManager()
        mp = PluginMarketplace(pm, install_dir=str(tmp_path / "plugins"))
        reg_file = tmp_path / "registry.json"
        reg_file.write_text(
            json.dumps([{"name": "test_plugin", "version": "1.0.0", "author": "test"}]),
            encoding="utf-8",
        )
        mp.load_registry(str(reg_file))
        details = mp.get_details("test_plugin")
        assert details is not None
        assert details.author == "test"
        assert mp.get_details("unknown") is None

    def test_install_and_uninstall(self, tmp_path):
        pm = PluginManager()
        install_dir = tmp_path / "installed"
        mp = PluginMarketplace(pm, install_dir=str(install_dir))
        reg_file = tmp_path / "registry.json"
        reg_file.write_text(
            json.dumps([{"name": "my_plugin", "version": "1.0.0", "description": "Test"}]),
            encoding="utf-8",
        )
        mp.load_registry(str(reg_file))

        # Install
        manifest = mp.install("my_plugin")
        assert manifest is not None
        assert manifest.name == "my_plugin"
        assert mp.is_installed("my_plugin")

        # Uninstall
        assert mp.uninstall("my_plugin") is True
        assert not mp.is_installed("my_plugin")

    def test_install_unknown_plugin(self, tmp_path):
        pm = PluginManager()
        mp = PluginMarketplace(pm, install_dir=str(tmp_path / "plugins"))
        assert mp.install("nonexistent") is None

    def test_uninstall_not_installed(self, tmp_path):
        pm = PluginManager()
        mp = PluginMarketplace(pm, install_dir=str(tmp_path / "plugins"))
        assert mp.uninstall("nonexistent") is False

    def test_list_installed_empty(self, tmp_path):
        pm = PluginManager()
        mp = PluginMarketplace(pm, install_dir=str(tmp_path / "plugins"))
        assert mp.list_installed() == []
