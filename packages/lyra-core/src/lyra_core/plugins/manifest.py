"""Declarative plugin manifest loader.

Two manifest systems live side-by-side in :mod:`lyra_core.plugins`:

* The rich **PluginManifest/PluginRegistry** system (see
  :mod:`lyra_core.plugins.registry`) — Python-native, in-process
  plugins that ship as a module with a module-level ``manifest``
  attribute.
* This **declarative** system — filesystem-first: a directory that
  contains a ``plugin.json`` / ``.lyra-plugin`` / ``.claude-plugin``
  header naming a deferred ``entry`` callable by dotted path.
  This is the parity surface for Claude Code / Codex plugins.

This module only parses and validates the manifest; it does NOT
import the ``entry`` module. That's :mod:`lyra_core.plugins.runtime`'s
job, and it's deliberately lazy so manifest discovery can't fail
because of a plugin's optional deps.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


__all__ = [
    "PLUGIN_MANIFEST_FILES",
    "PluginManifestError",
    "PluginManifestSpec",
    "load_manifest",
    "validate_manifest",
]


PLUGIN_MANIFEST_FILES = (".lyra-plugin", ".claude-plugin", "plugin.json")


class PluginManifestError(ValueError):
    """Raised when a declarative plugin manifest is missing, malformed,
    or fails shape validation."""


_REQUIRED = ("name", "version", "entry")


@dataclass(frozen=True)
class PluginManifestSpec:
    """Validated declarative manifest.

    ``kinds`` is a derived set summarising the capability buckets
    this manifest declares (``"hook"``, ``"tool"``, ``"slash_command"``).
    Downstream dispatch code uses it for fast filtering.
    """

    name: str
    version: str
    entry: str
    hooks: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    slash_commands: tuple[str, ...] = ()
    description: str = ""
    kinds: frozenset[str] = field(default_factory=frozenset)


def _as_str_tuple(value: Any, *, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise PluginManifestError(
            f"{field_name!r} must be a list of strings"
        )
    out: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise PluginManifestError(
                f"{field_name!r} must be a list of strings"
            )
        out.append(item)
    return tuple(out)


def validate_manifest(data: Mapping[str, Any]) -> PluginManifestSpec:
    """Validate a declarative manifest dict.

    Raises :class:`PluginManifestError` if any required field is
    missing or any optional field has the wrong shape. Unknown
    fields are tolerated (forward-compat) but ignored.
    """
    if not isinstance(data, Mapping):
        raise PluginManifestError("manifest must be a JSON object")

    missing = [field for field in _REQUIRED if field not in data]
    if missing:
        raise PluginManifestError(
            f"manifest missing required fields: {missing}"
        )

    for field in _REQUIRED:
        value = data[field]
        if not isinstance(value, str) or not value.strip():
            raise PluginManifestError(
                f"manifest field {field!r} must be a non-empty string"
            )

    hooks = _as_str_tuple(data.get("hooks"), field_name="hooks")
    tools = _as_str_tuple(data.get("tools"), field_name="tools")
    slash = _as_str_tuple(
        data.get("slash_commands"), field_name="slash_commands"
    )
    description = data.get("description", "")
    if not isinstance(description, str):
        raise PluginManifestError("'description' must be a string if provided")

    kinds: set[str] = set()
    if hooks:
        kinds.add("hook")
    if tools:
        kinds.add("tool")
    if slash:
        kinds.add("slash_command")

    return PluginManifestSpec(
        name=data["name"],
        version=data["version"],
        entry=data["entry"],
        hooks=hooks,
        tools=tools,
        slash_commands=slash,
        description=description,
        kinds=frozenset(kinds),
    )


def _locate_manifest_file(root: Path) -> Path | None:
    if root.is_file():
        # Caller pointed us directly at a manifest file.
        if root.name in PLUGIN_MANIFEST_FILES:
            return root
        return None
    for name in PLUGIN_MANIFEST_FILES:
        candidate = root / name
        if candidate.is_file():
            return candidate
    return None


def load_manifest(root: Path | str) -> PluginManifestSpec:
    """Load a declarative manifest from *root*.

    ``root`` may be a directory or a manifest file directly. If it
    is a directory we look for ``plugin.json``, ``.lyra-plugin`` and
    ``.claude-plugin`` (first hit wins, in that preference order).
    """
    path = Path(root)
    manifest_path = _locate_manifest_file(path)
    if manifest_path is None:
        raise PluginManifestError(
            f"no plugin manifest found under {path} "
            f"(looked for: {list(PLUGIN_MANIFEST_FILES)})"
        )

    try:
        raw = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PluginManifestError(
            f"cannot read {manifest_path}: {exc}"
        ) from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PluginManifestError(
            f"{manifest_path} is not valid JSON: {exc}"
        ) from exc

    if not isinstance(data, Mapping):
        raise PluginManifestError(
            f"{manifest_path} must contain a JSON object at the top level"
        )

    return validate_manifest(data)
