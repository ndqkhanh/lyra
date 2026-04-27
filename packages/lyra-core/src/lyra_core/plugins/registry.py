"""Plugin registry.

A plugin is a Python object that:

1. Supplies a :class:`PluginMetadata` block (name, version,
   author, declared hooks, declared tools).
2. Registers one or more :class:`PluginHook` callables against
   named extension points (``on_turn_start``, ``on_turn_end``,
   ``on_safety_flag``, …).
3. Optionally contributes tool factories and slash commands.

``PluginRegistry`` owns dispatch. Hooks run in **declaration
order**; exceptions are captured per hook so one misbehaving
plugin can't take the whole loop down. The registry returns a
:class:`HookResult` per invocation so callers can surface errors
without swallowing them.
"""
from __future__ import annotations

import importlib
import importlib.util
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Protocol


__all__ = [
    "HarnessPlugin",
    "HookResult",
    "PluginHook",
    "PluginManifest",
    "PluginMetadata",
    "PluginRegistry",
    "PluginValidationError",
    "load_plugin",
]


_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*$")


class PluginValidationError(ValueError):
    pass


# ---- manifests + metadata ------------------------------------------


@dataclass(frozen=True)
class PluginMetadata:
    """The minimal declarative header every plugin must supply."""

    name: str
    version: str
    author: str = ""
    description: str = ""
    hooks: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()

    def validate(self) -> None:
        if not _NAME_RE.match(self.name):
            raise PluginValidationError(
                f"plugin name {self.name!r} must match [a-z][a-z0-9_-]*"
            )
        if not self.version.strip():
            raise PluginValidationError("plugin version must be non-empty")


@dataclass(frozen=True)
class PluginManifest:
    """Full declarative block (metadata + hook/tool registrations)."""

    metadata: PluginMetadata
    hook_callables: Mapping[str, "PluginHook"] = field(default_factory=dict)
    tool_factories: Mapping[str, Callable[..., Any]] = field(default_factory=dict)


# ---- runtime types -------------------------------------------------


class PluginHook(Protocol):
    """One hook callable.

    Hooks take a single ``context`` dict so plugins don't pin to a
    specific hook's kwargs. Returning ``None`` is fine; returning
    a dict gets merged into the session's side-channel.
    """

    def __call__(self, context: Mapping[str, Any]) -> Mapping[str, Any] | None: ...


@dataclass(frozen=True)
class HookResult:
    plugin: str
    hook: str
    ok: bool
    output: Mapping[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "plugin": self.plugin,
            "hook": self.hook,
            "ok": self.ok,
            "output": dict(self.output) if self.output else None,
            "error": self.error,
        }


class HarnessPlugin(Protocol):
    """Minimal protocol a plugin module must expose.

    Concretely: a module-level ``manifest`` attribute of type
    :class:`PluginManifest`.
    """

    manifest: PluginManifest


# ---- registry ------------------------------------------------------


@dataclass
class PluginRegistry:
    _manifests: dict[str, PluginManifest] = field(default_factory=dict)
    _load_order: list[str] = field(default_factory=list)

    def register(self, manifest: PluginManifest) -> None:
        manifest.metadata.validate()
        name = manifest.metadata.name
        if name in self._manifests:
            raise PluginValidationError(
                f"plugin {name!r} already registered"
            )
        # Every declared hook must have a callable, and vice versa.
        declared = set(manifest.metadata.hooks)
        implemented = set(manifest.hook_callables.keys())
        if declared != implemented:
            missing = declared - implemented
            extra = implemented - declared
            raise PluginValidationError(
                f"plugin {name!r} hook mismatch — "
                f"missing impls: {sorted(missing)}, "
                f"undeclared impls: {sorted(extra)}"
            )
        self._manifests[name] = manifest
        self._load_order.append(name)

    def unregister(self, name: str) -> None:
        if name not in self._manifests:
            raise PluginValidationError(f"plugin {name!r} not registered")
        del self._manifests[name]
        self._load_order.remove(name)

    def names(self) -> tuple[str, ...]:
        return tuple(self._load_order)

    def metadata(self, name: str) -> PluginMetadata:
        try:
            return self._manifests[name].metadata
        except KeyError as exc:
            raise PluginValidationError(f"plugin {name!r} not registered") from exc

    def tool_factory(self, tool_name: str) -> Callable[..., Any] | None:
        for name in self._load_order:
            factories = self._manifests[name].tool_factories
            if tool_name in factories:
                return factories[tool_name]
        return None

    def tool_names(self) -> tuple[str, ...]:
        names: list[str] = []
        for name in self._load_order:
            for tool in self._manifests[name].tool_factories:
                if tool not in names:
                    names.append(tool)
        return tuple(names)

    def dispatch(
        self,
        hook: str,
        *,
        context: Mapping[str, Any],
    ) -> tuple[HookResult, ...]:
        results: list[HookResult] = []
        for name in self._load_order:
            manifest = self._manifests[name]
            fn = manifest.hook_callables.get(hook)
            if fn is None:
                continue
            try:
                output = fn(context)
                if output is not None and not isinstance(output, Mapping):
                    raise TypeError(
                        f"hook {hook!r} returned {type(output).__name__}, "
                        f"expected Mapping or None"
                    )
                results.append(
                    HookResult(plugin=name, hook=hook, ok=True, output=output)
                )
            except Exception as exc:  # noqa: BLE001
                results.append(
                    HookResult(
                        plugin=name,
                        hook=hook,
                        ok=False,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
        return tuple(results)


# ---- loader --------------------------------------------------------


def load_plugin(path: Path | str) -> PluginManifest:
    """Load a single-file plugin module from *path*.

    The file must expose a module-level ``manifest`` attribute.
    No sandboxing beyond that — the caller is expected to audit
    third-party plugins before installing them.
    """
    p = Path(path).resolve()
    if not p.exists() or not p.is_file():
        raise PluginValidationError(f"plugin file not found: {path}")
    spec = importlib.util.spec_from_file_location(
        f"_lyra_plugin_{p.stem}", p
    )
    if spec is None or spec.loader is None:
        raise PluginValidationError(f"cannot import plugin from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    manifest = getattr(module, "manifest", None)
    if not isinstance(manifest, PluginManifest):
        raise PluginValidationError(
            f"plugin at {path} does not expose a PluginManifest `manifest`"
        )
    return manifest
