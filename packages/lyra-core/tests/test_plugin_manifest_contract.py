"""Contract tests for :mod:`lyra_core.plugins.manifest`."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_core.plugins import (
    PluginManifestError,
    load_manifest,
    validate_manifest,
)


def _write(p: Path, name: str, body: dict) -> Path:
    target = p / name
    target.write_text(json.dumps(body), encoding="utf-8")
    return target


def test_minimal_valid_manifest() -> None:
    m = validate_manifest(
        {"name": "rust-style", "version": "0.1.0", "entry": "rust_style:plugin"}
    )
    assert m.name == "rust-style"
    assert m.version == "0.1.0"
    assert m.entry == "rust_style:plugin"
    assert m.kinds == set()


def test_kinds_reflects_declared_capabilities() -> None:
    m = validate_manifest(
        {
            "name": "x",
            "version": "1",
            "entry": "x",
            "hooks": ["pre_llm_call"],
            "tools": ["foo"],
            "slash_commands": ["foo"],
        }
    )
    assert m.kinds == {"hook", "tool", "slash_command"}


def test_missing_required_fields_raises() -> None:
    with pytest.raises(PluginManifestError, match="missing required"):
        validate_manifest({"name": "x"})


def test_hooks_must_be_list_of_strings() -> None:
    with pytest.raises(PluginManifestError, match="list of strings"):
        validate_manifest(
            {"name": "x", "version": "1", "entry": "x", "hooks": ["ok", 3]}
        )


def test_load_from_plugin_json(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "plugin.json",
        {"name": "p", "version": "0.1", "entry": "p:plugin"},
    )
    m = load_manifest(tmp_path)
    assert m.name == "p"


def test_load_from_lyra_plugin_suffix(tmp_path: Path) -> None:
    _write(
        tmp_path,
        ".lyra-plugin",
        {"name": "p", "version": "0.1", "entry": "p:plugin"},
    )
    m = load_manifest(tmp_path)
    assert m.name == "p"


def test_load_from_claude_plugin_suffix(tmp_path: Path) -> None:
    _write(
        tmp_path,
        ".claude-plugin",
        {"name": "p", "version": "0.1", "entry": "p:plugin"},
    )
    m = load_manifest(tmp_path)
    assert m.name == "p"


def test_missing_manifest_file_raises(tmp_path: Path) -> None:
    with pytest.raises(PluginManifestError, match="no plugin manifest found"):
        load_manifest(tmp_path)


def test_invalid_json_raises(tmp_path: Path) -> None:
    p = tmp_path / "plugin.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(PluginManifestError, match="not valid JSON"):
        load_manifest(tmp_path)


def test_root_must_be_object(tmp_path: Path) -> None:
    p = tmp_path / "plugin.json"
    p.write_text("[]", encoding="utf-8")
    with pytest.raises(PluginManifestError, match="JSON object"):
        load_manifest(tmp_path)
