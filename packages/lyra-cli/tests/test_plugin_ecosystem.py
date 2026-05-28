"""Tests for PluginManifest, PluginManager, PluginRegistry, and related types."""

import json
import tempfile
from pathlib import Path

from lyra_cli.plugin.manager import (
    PluginInstance,
    PluginManager,
    PluginState,
    get_plugin_manager,
)
from lyra_cli.plugin.manifest import (
    PluginDependency,
    PluginKind,
    PluginManifest,
    PluginPermission,
)
from lyra_cli.plugin.marketplace import PluginRegistry, RegistryEntry


class TestPluginKind:
    def test_kind_values(self):
        assert PluginKind.SKILL == "skill"
        assert PluginKind.AGENT == "agent"
        assert PluginKind.HOOK == "hook"
        assert PluginKind.MCP_SERVER == "mcp_server"
        assert PluginKind.THEME == "theme"
        assert PluginKind.SOUND_PACK == "sound_pack"
        assert PluginKind.BUNDLE == "bundle"


class TestPluginPermission:
    def test_defaults(self):
        p = PluginPermission(tool="Read")
        assert p.tool == "Read"
        assert p.level == "read"
        assert p.reason == ""

    def test_custom(self):
        p = PluginPermission(tool="Bash", level="shell", reason="needs shell")
        assert p.level == "shell"


class TestPluginDependency:
    def test_defaults(self):
        d = PluginDependency(name="requests")
        assert d.name == "requests"
        assert d.version == "*"
        assert d.optional is False

    def test_optional(self):
        d = PluginDependency(name="pyyaml", optional=True)
        assert d.optional is True


class TestPluginManifest:
    def test_minimal(self):
        m = PluginManifest(name="test", version="1.0.0", kind=PluginKind.SKILL)
        assert m.name == "test"
        assert m.version == "1.0.0"
        assert m.kind == PluginKind.SKILL
        assert m.is_bundle is False

    def test_bundle_kind(self):
        m = PluginManifest(name="bundle", version="1.0", kind=PluginKind.BUNDLE)
        assert m.is_bundle is True

    def test_multi_kind(self):
        m = PluginManifest(name="full", version="1.0", kind=[PluginKind.SKILL, PluginKind.HOOK])
        assert isinstance(m.kind, list)
        assert PluginKind.SKILL in m.kind

    def test_to_dict_roundtrip(self):
        m = PluginManifest(
            name="my-plugin",
            version="2.0.0",
            kind=PluginKind.SKILL,
            description="A test plugin",
            author="test",
            entry_point="main.py",
            commands=["/test"],
            skills=["test-skill"],
            tags=["test", "example"],
            dependencies=[PluginDependency(name="requests")],
            permissions=[PluginPermission(tool="Read", level="read")],
        )
        data = m.to_dict()
        m2 = PluginManifest.from_dict(data)
        assert m2.name == "my-plugin"
        assert m2.version == "2.0.0"
        assert m2.description == "A test plugin"
        assert m2.tags == ["test", "example"]

    def test_from_dict_minimal(self):
        data = {"name": "minimal", "version": "0.1.0", "kind": "skill"}
        m = PluginManifest.from_dict(data)
        assert m.name == "minimal"

    def test_from_dict_multi_kind(self):
        data = {"name": "multi", "version": "0.1.0", "kind": ["skill", "hook"]}
        m = PluginManifest.from_dict(data)
        assert isinstance(m.kind, list)
        assert len(m.kind) == 2

    def test_default_values(self):
        m = PluginManifest(name="test", version="1.0", kind=PluginKind.SKILL)
        assert m.description == ""
        assert m.author == ""
        assert m.license == "MIT"
        assert m.entry_point == ""
        assert m.commands == []
        assert m.skills == []
        assert m.agents == []
        assert m.dependencies == []
        assert m.permissions == []
        assert m.tags == []
        assert m.requires_python == ">=3.10"


class TestPluginInstance:
    def test_defaults(self):
        m = PluginManifest(name="test", version="1.0", kind=PluginKind.SKILL)
        pi = PluginInstance(manifest=m, path=Path("/tmp/test"))
        assert pi.name == "test"
        assert pi.state == PluginState.DISCOVERED
        assert pi.is_active is False

    def test_active_when_enabled(self):
        m = PluginManifest(name="test", version="1.0", kind=PluginKind.SKILL)
        pi = PluginInstance(manifest=m, path=Path("/tmp/test"), state=PluginState.ENABLED)
        assert pi.is_active is True


class TestPluginManager:
    def _make_plugin_dir(self, name: str, kind: str = "skill") -> str:
        tmp = tempfile.mkdtemp()
        plugin_dir = Path(tmp) / name
        plugin_dir.mkdir()
        manifest = {
            "name": name,
            "version": "1.0.0",
            "kind": kind,
            "description": f"{name} plugin",
        }
        (plugin_dir / "plugin.json").write_text(json.dumps(manifest))
        return str(Path(tmp))

    def test_initial_state(self):
        pm = PluginManager()
        assert pm.plugins == []
        assert pm.active_plugins == []

    def test_discover_finds_plugin(self):
        pm = PluginManager()
        tmp = self._make_plugin_dir("hello-world")
        pm.add_search_path(Path(tmp))
        discovered = pm.discover()
        assert "hello-world" in discovered

    def test_discover_empty_dir(self):
        pm = PluginManager()
        with tempfile.TemporaryDirectory() as tmp:
            pm.add_search_path(Path(tmp))
            discovered = pm.discover()
            assert discovered == []

    def test_discover_invalid_manifest(self):
        pm = PluginManager()
        with tempfile.TemporaryDirectory() as tmp:
            plugin_dir = Path(tmp) / "bad-plugin"
            plugin_dir.mkdir()
            (plugin_dir / "plugin.json").write_text("not json")
            pm.add_search_path(Path(tmp))
            pm.discover()
            assert "bad-plugin" in [p.name for p in pm.errored_plugins]

    def test_get_returns_plugin(self):
        pm = PluginManager()
        tmp = self._make_plugin_dir("found")
        pm.add_search_path(Path(tmp))
        pm.discover()
        assert pm.get("found") is not None

    def test_get_missing_plugin(self):
        pm = PluginManager()
        assert pm.get("nonexistent") is None

    def test_list_by_kind(self):
        pm = PluginManager()
        tmp = self._make_plugin_dir("my-skill", "skill")
        pm.add_search_path(Path(tmp))
        pm.discover()
        skills = pm.list_by_kind(PluginKind.SKILL)
        assert len(skills) == 1
        assert skills[0].name == "my-skill"

    def test_enable_disable(self):
        pm = PluginManager()
        m = PluginManifest(name="test", version="1.0", kind=PluginKind.SKILL)
        pi = PluginInstance(manifest=m, path=Path("/tmp/test"), state=PluginState.LOADED)
        pm._plugins["test"] = pi
        assert pm.enable("test") is True
        assert pi.is_active is True
        assert pm.disable("test") is True
        assert pi.is_active is False

    def test_enable_not_loaded(self):
        pm = PluginManager()
        m = PluginManifest(name="test", version="1.0", kind=PluginKind.SKILL)
        pi = PluginInstance(manifest=m, path=Path("/tmp/test"), state=PluginState.DISCOVERED)
        pm._plugins["test"] = pi
        assert pm.enable("test") is False

    def test_on_lifecycle_hook(self):
        pm = PluginManager()
        events = []

        def hook(instance):
            events.append(instance.name)

        pm.on("on_enable", hook)
        m = PluginManifest(name="test", version="1.0", kind=PluginKind.SKILL)
        pi = PluginInstance(manifest=m, path=Path("/tmp/test"), state=PluginState.LOADED)
        pm._plugins["test"] = pi
        pm.enable("test")
        assert "test" in events

    def test_unload_removes_plugin(self):
        pm = PluginManager()
        m = PluginManifest(name="test", version="1.0", kind=PluginKind.SKILL)
        pi = PluginInstance(manifest=m, path=Path("/tmp/test"))
        pm._plugins["test"] = pi
        assert pm.unload("test") is True
        assert pm.get("test") is None


class TestPluginRegistry:
    def test_initial_state(self):
        reg = PluginRegistry()
        assert reg.entry_count == 0

    def test_add_index(self):
        reg = PluginRegistry()
        reg.add_index("https://example.com/plugins.json")
        assert len(reg._indexes) == 1

    def test_get_missing_entry(self):
        reg = PluginRegistry()
        assert reg.get("nonexistent") is None

    def test_search_by_name(self):
        reg = PluginRegistry()
        entry = RegistryEntry(
            name="dracula-theme",
            version="1.0",
            kind=PluginKind.THEME,
            description="A dark theme",
            tags=["dark", "theme"],
        )
        reg._entries["dracula-theme"] = entry
        results = reg.search("dracula")
        assert len(results) == 1
        assert results[0].name == "dracula-theme"

    def test_search_by_tag(self):
        reg = PluginRegistry()
        entry = RegistryEntry(
            name="retro-sounds",
            version="1.0",
            kind=PluginKind.SOUND_PACK,
            description="Retro game sounds",
            tags=["sound", "retro"],
        )
        reg._entries["retro-sounds"] = entry
        results = reg.search("retro")
        assert len(results) == 1

    def test_search_no_match(self):
        reg = PluginRegistry()
        results = reg.search("nonexistent")
        assert results == []

    def test_list_by_kind(self):
        reg = PluginRegistry()
        reg._entries["theme1"] = RegistryEntry(
            name="theme1", version="1.0", kind=PluginKind.THEME, description="a",
        )
        reg._entries["skill1"] = RegistryEntry(
            name="skill1", version="1.0", kind=PluginKind.SKILL, description="b",
        )
        themes = reg.list_by_kind(PluginKind.THEME)
        assert len(themes) == 1
        assert themes[0].name == "theme1"

    def test_generate_skeleton(self):
        reg = PluginRegistry()
        with tempfile.TemporaryDirectory() as tmp:
            path = reg.generate_skeleton("my-plugin", PluginKind.SKILL, tmp)
            assert path.exists()
            assert (path / "plugin.json").exists()
            manifest = json.loads((path / "plugin.json").read_text())
            assert manifest["name"] == "my-plugin"
            assert manifest["kind"] == "skill"


class TestGetPluginManager:
    def test_returns_singleton(self):
        pm1 = get_plugin_manager()
        pm2 = get_plugin_manager()
        assert pm1 is pm2
