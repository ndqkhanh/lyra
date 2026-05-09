"""Wave-F Task 10 — harness plugins first-class contract."""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_core.plugins import (
    PluginManifest,
    PluginMetadata,
    PluginRegistry,
    PluginValidationError,
    load_plugin,
)


# ---- registration validation ---------------------------------------


def test_metadata_rejects_bad_name() -> None:
    with pytest.raises(PluginValidationError):
        PluginMetadata(name="Bad Name!", version="1.0").validate()


def test_metadata_requires_version() -> None:
    with pytest.raises(PluginValidationError):
        PluginMetadata(name="ok", version="").validate()


def test_register_rejects_hook_mismatch() -> None:
    registry = PluginRegistry()
    manifest = PluginManifest(
        metadata=PluginMetadata(
            name="x",
            version="1.0",
            hooks=("on_turn_start",),
        ),
        hook_callables={"on_turn_start": lambda ctx: None, "extra": lambda ctx: None},
    )
    with pytest.raises(PluginValidationError):
        registry.register(manifest)


def test_register_rejects_duplicates() -> None:
    registry = PluginRegistry()
    manifest = PluginManifest(
        metadata=PluginMetadata(name="x", version="1.0"),
    )
    registry.register(manifest)
    with pytest.raises(PluginValidationError):
        registry.register(manifest)


# ---- hook dispatch -------------------------------------------------


def test_hooks_run_in_registration_order() -> None:
    order: list[str] = []

    def make_hook(name: str):
        def hook(ctx):
            order.append(name)
        return hook

    registry = PluginRegistry()
    registry.register(
        PluginManifest(
            metadata=PluginMetadata(
                name="a", version="1.0", hooks=("on_turn_start",)
            ),
            hook_callables={"on_turn_start": make_hook("a")},
        )
    )
    registry.register(
        PluginManifest(
            metadata=PluginMetadata(
                name="b", version="1.0", hooks=("on_turn_start",)
            ),
            hook_callables={"on_turn_start": make_hook("b")},
        )
    )
    registry.dispatch("on_turn_start", context={})
    assert order == ["a", "b"]


def test_dispatch_captures_hook_exception() -> None:
    def bad(ctx):
        raise RuntimeError("kaboom")

    registry = PluginRegistry()
    registry.register(
        PluginManifest(
            metadata=PluginMetadata(
                name="bad", version="1.0", hooks=("on_turn_start",)
            ),
            hook_callables={"on_turn_start": bad},
        )
    )
    results = registry.dispatch("on_turn_start", context={})
    assert len(results) == 1
    assert results[0].ok is False
    assert "kaboom" in (results[0].error or "")


def test_dispatch_rejects_non_mapping_return() -> None:
    def bad(ctx):
        return [1, 2, 3]

    registry = PluginRegistry()
    registry.register(
        PluginManifest(
            metadata=PluginMetadata(
                name="weird", version="1.0", hooks=("on_turn_end",)
            ),
            hook_callables={"on_turn_end": bad},
        )
    )
    results = registry.dispatch("on_turn_end", context={})
    assert results[0].ok is False
    assert "expected Mapping" in (results[0].error or "")


def test_dispatch_skips_plugins_without_hook() -> None:
    called: list[str] = []
    registry = PluginRegistry()
    registry.register(
        PluginManifest(
            metadata=PluginMetadata(
                name="has-start", version="1.0", hooks=("on_turn_start",)
            ),
            hook_callables={"on_turn_start": lambda ctx: called.append("start")},
        )
    )
    registry.register(
        PluginManifest(
            metadata=PluginMetadata(
                name="has-end", version="1.0", hooks=("on_turn_end",)
            ),
            hook_callables={"on_turn_end": lambda ctx: called.append("end")},
        )
    )
    registry.dispatch("on_turn_start", context={})
    assert called == ["start"]


# ---- tool contributions --------------------------------------------


def test_tool_factory_lookup_walks_load_order() -> None:
    def make_echo():
        return lambda s: s

    registry = PluginRegistry()
    registry.register(
        PluginManifest(
            metadata=PluginMetadata(
                name="echoer", version="1.0", tools=("echo",)
            ),
            tool_factories={"echo": make_echo},
        )
    )
    factory = registry.tool_factory("echo")
    assert factory is not None
    assert factory()("hi") == "hi"
    assert registry.tool_names() == ("echo",)


def test_tool_factory_missing_returns_none() -> None:
    registry = PluginRegistry()
    assert registry.tool_factory("anything") is None


# ---- filesystem loader ---------------------------------------------


def test_load_plugin_from_file(tmp_path: Path) -> None:
    plugin = tmp_path / "plug.py"
    plugin.write_text(
        "from lyra_core.plugins import PluginManifest, PluginMetadata\n"
        "def _hook(ctx):\n"
        "    return {'seen': True}\n"
        "manifest = PluginManifest(\n"
        "    metadata=PluginMetadata(name='fs-plug', version='0.1', hooks=('on_turn_start',)),\n"
        "    hook_callables={'on_turn_start': _hook},\n"
        ")\n"
    )
    manifest = load_plugin(plugin)
    assert manifest.metadata.name == "fs-plug"
    assert "on_turn_start" in manifest.hook_callables


def test_load_plugin_missing_manifest_attribute(tmp_path: Path) -> None:
    plugin = tmp_path / "plug.py"
    plugin.write_text("x = 1\n")
    with pytest.raises(PluginValidationError):
        load_plugin(plugin)


def test_load_plugin_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(PluginValidationError):
        load_plugin(tmp_path / "ghost.py")
