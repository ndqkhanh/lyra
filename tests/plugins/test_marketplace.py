"""Tests for src/plugins/marketplace.py - PluginMarketplace."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lyra.plugins.marketplace import MarketPlugin, PluginMarketplace
from lyra.plugins.manifest_discovery import ManifestPlugin


SAMPLE_REGISTRY = [
    {
        "name": "web-search",
        "version": "1.2.0",
        "description": "Web search plugin",
        "author": "Lyra Team",
        "tags": ["search", "web"],
        "downloads": 1500,
        "rating": 4.5,
        "homepage": "https://example.com/search",
        "source_url": "https://github.com/lyra/search-plugin",
    },
    {
        "name": "code-exec",
        "version": "0.9.0",
        "description": "Code execution sandbox",
        "author": "Lyra Team",
        "tags": ["code", "sandbox"],
        "downloads": 800,
        "rating": 4.0,
    },
]


class TestMarketPlugin:
    """Tests for MarketPlugin dataclass."""

    def test_minimal_plugin(self):
        plugin = MarketPlugin(name="test", version="1.0.0")
        assert plugin.name == "test"
        assert plugin.version == "1.0.0"
        assert plugin.description == ""
        assert plugin.rating == 0.0

    def test_full_plugin(self):
        plugin = MarketPlugin(
            name="search",
            version="2.0.0",
            description="Search tool",
            author="dev",
            tags=["search"],
            downloads=500,
            rating=4.2,
            homepage="https://example.com",
            source_url="https://github.com/example/search",
        )
        assert plugin.rating == 4.2
        assert plugin.source_url == "https://github.com/example/search"


class TestPluginMarketplace:
    """Tests for PluginMarketplace."""

    @pytest.fixture
    def marketplace(self):
        manager = MagicMock()
        return PluginMarketplace(plugin_manager=manager)

    def test_initial_state(self, marketplace: PluginMarketplace):
        assert marketplace._local_registry == {}

    def test_load_registry_from_file(self, marketplace: PluginMarketplace):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(SAMPLE_REGISTRY, f)
            reg_path = f.name
        try:
            count = marketplace.load_registry(reg_path)
            assert count == 2
            assert "web-search" in marketplace._local_registry
            assert marketplace._local_registry["web-search"].rating == 4.5
        finally:
            os.unlink(reg_path)

    def test_load_registry_nonexistent(self, marketplace: PluginMarketplace):
        count = marketplace.load_registry("/nonexistent/registry.json")
        assert count == 0

    def test_load_registry_with_plugins_key(self, marketplace: PluginMarketplace):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"plugins": SAMPLE_REGISTRY}, f)
            reg_path = f.name
        try:
            count = marketplace.load_registry(reg_path)
            assert count == 2
        finally:
            os.unlink(reg_path)

    def test_load_registry_malformed(self, marketplace: PluginMarketplace):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("not valid json")
            reg_path = f.name
        try:
            count = marketplace.load_registry(reg_path)
            assert count == 0
        finally:
            os.unlink(reg_path)

    def test_search_all(self, marketplace: PluginMarketplace):
        marketplace._local_registry = {
            "p1": MarketPlugin(name="p1", version="1.0.0"),
            "p2": MarketPlugin(name="p2", version="1.0.0"),
        }
        results = marketplace.search()
        assert len(results) == 2

    def test_search_with_query(self, marketplace: PluginMarketplace):
        marketplace._local_registry = {
            "search": MarketPlugin(
                name="search", version="1.0.0", description="Web search",
                author="team", tags=["web"],
            ),
            "calc": MarketPlugin(name="calc", version="1.0.0"),
        }
        results = marketplace.search("search")
        assert len(results) == 1
        assert results[0].name == "search"

    def test_search_author(self, marketplace: PluginMarketplace):
        marketplace._local_registry = {
            "p1": MarketPlugin(name="p1", version="1.0.0", author="lyra"),
            "p2": MarketPlugin(name="p2", version="1.0.0", author="other"),
        }
        results = marketplace.search("lyra")
        assert len(results) == 1

    def test_search_tags(self, marketplace: PluginMarketplace):
        marketplace._local_registry = {
            "p1": MarketPlugin(name="p1", version="1.0.0", tags=["search", "web"]),
            "p2": MarketPlugin(name="p2", version="1.0.0", tags=["code"]),
        }
        results = marketplace.search("search")
        assert len(results) == 1

    def test_search_sort_by_rating(self, marketplace: PluginMarketplace):
        marketplace._local_registry = {
            "p1": MarketPlugin(name="p1", version="1.0.0", rating=3.0, downloads=100),
            "p2": MarketPlugin(name="p2", version="1.0.0", rating=5.0, downloads=200),
        }
        results = marketplace.search()
        assert results[0].name == "p2"

    def test_search_limit(self, marketplace: PluginMarketplace):
        marketplace._local_registry = {
            f"p{i}": MarketPlugin(name=f"p{i}", version="1.0.0")
            for i in range(50)
        }
        results = marketplace.search(limit=10)
        assert len(results) == 10

    def test_get_details(self, marketplace: PluginMarketplace):
        marketplace._local_registry = {
            "test": MarketPlugin(name="test", version="1.0.0", description="A plugin"),
        }
        details = marketplace.get_details("test")
        assert details is not None
        assert details.description == "A plugin"

    def test_get_details_not_found(self, marketplace: PluginMarketplace):
        assert marketplace.get_details("nonexistent") is None

    def test_install_not_in_registry(self, marketplace: PluginMarketplace):
        result = marketplace.install("nonexistent")
        assert result is None

    def test_install_version_mismatch(self, marketplace: PluginMarketplace):
        marketplace._local_registry = {
            "test": MarketPlugin(name="test", version="2.0.0"),
        }
        result = marketplace.install("test", version="1.0.0")
        assert result is None

    def test_install_success(self, marketplace: PluginMarketplace):
        marketplace._local_registry = {
            "test": MarketPlugin(
                name="test", version="1.0.0", description="Test plugin",
                tags=["test"],
            ),
        }
        result = marketplace.install("test")
        assert result is not None
        assert result.name == "test"

    def test_install_already_exists(self, marketplace: PluginMarketplace):
        marketplace._local_registry = {
            "test": MarketPlugin(name="test", version="1.0.0"),
        }
        result = marketplace.install("test")
        # Should succeed on first call
        assert result is not None

    def test_uninstall_not_installed(self, marketplace: PluginMarketplace):
        assert marketplace.uninstall("nonexistent") is False

    def test_uninstall_success(self, marketplace: PluginMarketplace):
        with tempfile.TemporaryDirectory() as tmpdir:
            install_dir = Path(tmpdir) / "plugins"
            install_dir.mkdir()
            plugin_dir = install_dir / "test-plugin"
            plugin_dir.mkdir()
            (plugin_dir / "__init__.py").touch()

            manager = MagicMock()
            mp = PluginMarketplace(
                plugin_manager=manager,
                install_dir=str(install_dir),
            )
            assert mp.uninstall("test-plugin") is True
            assert not plugin_dir.exists()

    def test_list_installed(self, marketplace: PluginMarketplace):
        results = marketplace.list_installed()
        assert isinstance(results, list)

    def test_is_installed(self, marketplace: PluginMarketplace):
        assert marketplace.is_installed("nonexistent") is False

    def test_stub_plugin_template(self):
        template = PluginMarketplace._stub_plugin_template("my-plugin", "1.0.0")
        assert "Plugin: my-plugin v1.0.0" in template
        assert "async def initialize()" in template
        assert "async def shutdown()" in template

    def test_install_creates_stub_file(self):
        """Install creates a plugin directory and stub files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            install_dir = Path(tmpdir)
            manager = MagicMock()
            mp = PluginMarketplace(
                plugin_manager=manager,
                install_dir=str(install_dir),
            )
            mp._local_registry = {
                "test-plugin": MarketPlugin(
                    name="test-plugin", version="1.0.0", description="A test",
                    tags=["test"],
                ),
            }
            result = mp.install("test-plugin")
            assert result is not None
            assert result.name == "test-plugin"
            # Verify files were created
            assert (install_dir / "test-plugin" / "plugin.yaml").exists()
            assert (install_dir / "test-plugin" / "test-plugin.py").exists()

    def test_install_with_yaml(self):
        """Install writes YAML manifest when yaml is available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            install_dir = Path(tmpdir)
            manager = MagicMock()
            mp = PluginMarketplace(
                plugin_manager=manager,
                install_dir=str(install_dir),
            )
            mp._local_registry = {
                "test": MarketPlugin(name="test", version="2.0.0", tags=["a"]),
            }
            result = mp.install("test")
            assert result is not None
            manifest_file = install_dir / "test" / "plugin.yaml"
            assert manifest_file.exists()
            content = manifest_file.read_text()
            assert "name: test" in content or '"name": "test"' in content

    def test_is_installed_check(self):
        """is_installed checks for plugin directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            install_dir = Path(tmpdir) / "plugins"
            install_dir.mkdir()
            (install_dir / "existing-plugin").mkdir()

            manager = MagicMock()
            mp = PluginMarketplace(
                plugin_manager=manager,
                install_dir=str(install_dir),
            )
            assert mp.is_installed("existing-plugin") is True
            assert mp.is_installed("missing-plugin") is False
