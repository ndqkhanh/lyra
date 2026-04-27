"""Plugin runtime — discover declarative manifests and dispatch events.

The runtime walks a root directory, finds every declarative plugin
manifest (see :mod:`lyra_core.plugins.manifest`), and holds each one
as a :class:`LoadedPlugin`. Entry modules are **not** imported during
discovery — only on the first :meth:`PluginRuntime.dispatch` call
for an event the plugin subscribes to. This keeps manifest
exploration cheap and isolates heavy optional deps.

Dispatch semantics:

* Each plugin whose manifest ``hooks`` list contains the event is
  invoked with ``(event, ctx)``.
* Successful return values become ``{"plugin": name, "value": ...}``.
* Exceptions are caught and reported as
  ``{"plugin": name, "error": "<ExcClass>: <msg>"}`` without aborting
  the rest of the dispatch — one broken plugin must not take the
  whole loop down.
* Plugins not subscribed to the event are silently skipped.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

from .manifest import (
    PLUGIN_MANIFEST_FILES,
    PluginManifestError,
    PluginManifestSpec,
    load_manifest,
)


__all__ = [
    "LoadedPlugin",
    "PluginRuntime",
]


@dataclass
class LoadedPlugin:
    """A manifest plus its source path and (lazy) resolved callable."""

    manifest: PluginManifestSpec
    source: Path
    _callable: Callable[..., Any] | None = field(default=None, repr=False)

    @property
    def is_imported(self) -> bool:
        return self._callable is not None


def _resolve_entry(entry: str) -> Callable[..., Any]:
    """Split ``"module.submod:attr"`` into an importable callable."""
    if ":" in entry:
        module_name, attr = entry.split(":", 1)
    else:
        # Support dotted form ``module.submod.attr`` for convenience.
        module_name, _, attr = entry.rpartition(".")
    if not module_name or not attr:
        raise RuntimeError(
            f"entry {entry!r} must be 'module:callable' or 'module.callable'"
        )
    mod = importlib.import_module(module_name)
    target: Any = mod
    for part in attr.split("."):
        target = getattr(target, part)
    if not callable(target):
        raise RuntimeError(f"entry {entry!r} is not callable")
    return target


@dataclass
class PluginRuntime:
    """Discover + dispatch declarative plugins.

    One instance per agent session is typical. Not thread-safe —
    dispatch is sequential (plugin ordering matters for repeatability).
    """

    _loaded: list[LoadedPlugin] = field(default_factory=list)

    def discover(self, root: Path | str) -> list[LoadedPlugin]:
        """Recursively walk *root* for manifests.

        Returns (and stores) one :class:`LoadedPlugin` per discovered
        manifest. Imports nothing — the entry modules stay untouched
        until the first :meth:`dispatch`.
        """
        root = Path(root)
        if not root.exists():
            raise PluginManifestError(
                f"plugin root {root} does not exist"
            )

        found: list[LoadedPlugin] = []
        seen_dirs: set[Path] = set()

        for dirpath in [root, *sorted(p for p in root.rglob("*") if p.is_dir())]:
            if dirpath in seen_dirs:
                continue
            # Pick the first manifest name present in this directory
            # (in declared preference order).
            for name in PLUGIN_MANIFEST_FILES:
                candidate = dirpath / name
                if candidate.is_file():
                    # Surface manifest errors at discovery time.
                    spec = load_manifest(dirpath)
                    found.append(LoadedPlugin(manifest=spec, source=candidate))
                    seen_dirs.add(dirpath)
                    break

        # Stable ordering by plugin name so dispatch is deterministic.
        found.sort(key=lambda p: p.manifest.name)
        self._loaded = found
        return list(found)

    def loaded(self) -> tuple[LoadedPlugin, ...]:
        return tuple(self._loaded)

    def dispatch(
        self,
        event: str,
        ctx: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        """Fire *event* at every plugin subscribed to it."""
        results: list[dict[str, Any]] = []
        for loaded in self._loaded:
            if event not in loaded.manifest.hooks:
                continue
            try:
                if loaded._callable is None:
                    loaded._callable = _resolve_entry(loaded.manifest.entry)
                value = loaded._callable(event, dict(ctx))
                results.append(
                    {"plugin": loaded.manifest.name, "value": value}
                )
            except Exception as exc:  # noqa: BLE001 — per-plugin isolation
                results.append(
                    {
                        "plugin": loaded.manifest.name,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
        return results
