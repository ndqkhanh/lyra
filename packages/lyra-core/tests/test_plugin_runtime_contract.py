"""Contract tests for :class:`PluginRuntime` (v1.7.3).

The v1.7.2 pass shipped a :class:`PluginManifest` loader; this pass
wires the manifest to a runtime that actually invokes entry-point
callables when the agent fires events. Deliberately lazy: a manifest
can be discovered and inspected without importing its ``entry`` module
(important because entry-point modules may have heavy optional deps
of their own).

Invariants tested:

- ``discover(root)`` walks a directory recursively and returns one
  :class:`LoadedPlugin` per manifest found (``.lyra-plugin`` AND
  ``.claude-plugin`` AND ``plugin.json``).
- ``discover`` does NOT import any ``entry`` modules — imports are
  deferred until the first :meth:`dispatch`.
- ``dispatch(event, ctx)`` calls each plugin's ``entry`` with
  ``event=<name>`` + ``ctx=<dict>`` and collects results.
- A plugin whose ``entry`` raises during dispatch is isolated — the
  exception is surfaced as a ``{"error": ...}`` result for that plugin
  and other plugins continue to run.
- Malformed manifests surface as :class:`PluginManifestError` at
  discovery time (not dispatch time).
- Both ``.lyra-plugin`` and ``.claude-plugin`` are recognised (parity).
"""
from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import pytest

from lyra_core.plugins import PluginManifestError
from lyra_core.plugins.runtime import LoadedPlugin, PluginRuntime


# --- helpers -------------------------------------------------------- #


def _write_manifest(dir: Path, *, name: str, entry: str, hooks: list[str]) -> None:
    (dir / ".lyra-plugin").write_text(
        json.dumps(
            {
                "name": name,
                "version": "0.1.0",
                "entry": entry,
                "hooks": hooks,
            }
        )
    )


def _write_entry_module(
    tmp_path: Path, *, module_name: str, body: str
) -> None:
    """Drop a throwaway module on sys.path so importlib can find it.

    Uses a tmp_path-unique package name to avoid ``sys.modules`` cache
    collisions across tests.
    """
    mod_dir = tmp_path / "_pkg"
    mod_dir.mkdir(exist_ok=True)
    (mod_dir / "__init__.py").write_text("")
    (mod_dir / f"{module_name}.py").write_text(textwrap.dedent(body))
    if str(tmp_path) not in sys.path:
        sys.path.insert(0, str(tmp_path))


@pytest.fixture(autouse=True)
def _flush_pkg_cache() -> None:
    """Flush any leaked ``_pkg`` entries so tests start from a clean import state."""
    doomed = [m for m in sys.modules if m == "_pkg" or m.startswith("_pkg.")]
    for m in doomed:
        sys.modules.pop(m, None)
    yield
    doomed = [m for m in sys.modules if m == "_pkg" or m.startswith("_pkg.")]
    for m in doomed:
        sys.modules.pop(m, None)


# --- discovery ------------------------------------------------------ #


def test_discover_returns_loaded_plugin_per_manifest(tmp_path: Path) -> None:
    plugin_a = tmp_path / "plugin_a"
    plugin_a.mkdir()
    _write_manifest(plugin_a, name="alpha", entry="_pkg.alpha:handler", hooks=["on_turn"])

    plugin_b = tmp_path / "plugin_b"
    plugin_b.mkdir()
    (plugin_b / ".claude-plugin").write_text(
        json.dumps(
            {
                "name": "beta",
                "version": "0.1.0",
                "entry": "_pkg.beta:handler",
                "hooks": ["on_turn"],
            }
        )
    )

    runtime = PluginRuntime()
    loaded = runtime.discover(tmp_path)

    assert {p.manifest.name for p in loaded} == {"alpha", "beta"}
    for p in loaded:
        assert isinstance(p, LoadedPlugin)
        # Imports are DEFERRED — the resolved callable must still be None.
        assert p.is_imported is False


def test_discover_does_not_import_entry_modules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib

    calls: list[str] = []
    real_import = importlib.import_module

    def _spy(name: str, *args, **kwargs):
        calls.append(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", _spy)

    plugin_dir = tmp_path / "lazy"
    plugin_dir.mkdir()
    _write_manifest(plugin_dir, name="lazy", entry="fake.mod:fn", hooks=["on_turn"])

    runtime = PluginRuntime()
    runtime.discover(tmp_path)

    assert "fake.mod" not in calls


# --- dispatch ------------------------------------------------------- #


def test_dispatch_invokes_entry_callable(tmp_path: Path) -> None:
    _write_entry_module(
        tmp_path,
        module_name="good",
        body="""
        def handler(event, ctx):
            return {'echoed': (event, dict(ctx))}
        """,
    )
    plugin_dir = tmp_path / "plugin_good"
    plugin_dir.mkdir()
    _write_manifest(plugin_dir, name="good", entry="_pkg.good:handler", hooks=["on_turn"])

    runtime = PluginRuntime()
    runtime.discover(tmp_path)

    results = runtime.dispatch("on_turn", {"user": "hi"})

    assert len(results) == 1
    assert results[0]["plugin"] == "good"
    assert results[0]["value"] == {"echoed": ("on_turn", {"user": "hi"})}


def test_dispatch_isolates_plugin_exceptions(tmp_path: Path) -> None:
    _write_entry_module(
        tmp_path,
        module_name="crash",
        body="""
        def handler(event, ctx):
            raise RuntimeError('plugin go boom')
        """,
    )
    _write_entry_module(
        tmp_path,
        module_name="calm",
        body="""
        def handler(event, ctx):
            return 'i am fine'
        """,
    )
    for mod, name in (("crash", "c1"), ("calm", "c2")):
        d = tmp_path / name
        d.mkdir()
        _write_manifest(d, name=name, entry=f"_pkg.{mod}:handler", hooks=["on_turn"])

    runtime = PluginRuntime()
    runtime.discover(tmp_path)
    results = runtime.dispatch("on_turn", {})

    by_plugin = {r["plugin"]: r for r in results}
    assert by_plugin["c1"]["error"].startswith("RuntimeError")
    assert by_plugin["c2"]["value"] == "i am fine"


def test_dispatch_only_fires_plugins_subscribed_to_the_event(tmp_path: Path) -> None:
    _write_entry_module(
        tmp_path,
        module_name="onturn_only",
        body="""
        def handler(event, ctx):
            return 'turn'
        """,
    )
    _write_entry_module(
        tmp_path,
        module_name="startup_only",
        body="""
        def handler(event, ctx):
            return 'start'
        """,
    )
    d1 = tmp_path / "a"
    d1.mkdir()
    _write_manifest(d1, name="a", entry="_pkg.onturn_only:handler", hooks=["on_turn"])

    d2 = tmp_path / "b"
    d2.mkdir()
    _write_manifest(d2, name="b", entry="_pkg.startup_only:handler", hooks=["on_startup"])

    runtime = PluginRuntime()
    runtime.discover(tmp_path)
    turn_results = runtime.dispatch("on_turn", {})
    startup_results = runtime.dispatch("on_startup", {})

    assert {r["plugin"] for r in turn_results} == {"a"}
    assert {r["plugin"] for r in startup_results} == {"b"}


# --- bad manifests -------------------------------------------------- #


def test_discover_surfaces_bad_manifest(tmp_path: Path) -> None:
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / ".lyra-plugin").write_text("{broken json")

    runtime = PluginRuntime()
    with pytest.raises(PluginManifestError):
        runtime.discover(tmp_path)


# --- claude-plugin parity ------------------------------------------- #


def test_claude_plugin_file_is_recognised(tmp_path: Path) -> None:
    _write_entry_module(
        tmp_path,
        module_name="cp",
        body="""
        def handler(event, ctx):
            return 42
        """,
    )
    d = tmp_path / "compat"
    d.mkdir()
    (d / ".claude-plugin").write_text(
        json.dumps(
            {
                "name": "compat",
                "version": "0.1.0",
                "entry": "_pkg.cp:handler",
                "hooks": ["on_turn"],
            }
        )
    )

    runtime = PluginRuntime()
    runtime.discover(tmp_path)
    results = runtime.dispatch("on_turn", {})

    assert results[0]["value"] == 42
