"""Named toolsets — composable tool bundles, hermes-agent parity.

hermes-agent ships a ``TOOLSETS`` map (see
``hermes-agent/toolsets.py``) so users can swap in / out groups of
tools by name (e.g. ``--tools=safe`` excludes destructive shells;
``--tools=research`` strips writes; ``--tools=full`` is everything).
v3.0.0 closes that gap.

Lyra's tool registry has historically been flat — every default tool
is registered on the kernel at startup, every MCP tool gets merged in
at autoload, and per-session enable/disable is done through the
permission stack rather than the tool list. The hermes pattern adds a
**named-bundle** layer on top of that: each toolset is an ordered
list of tool names that maps to "the canonical mix for this kind of
work". The ``TOOLSETS`` dict here is the SSOT; ``apply_toolset()`` is
how the REPL / `/toolsets` slash applies one to a session.

Built-in bundles:

* ``default`` — every tool the agent kernel knows about.
* ``safe`` — read-only + plan-only tools (``Read``, ``Glob``, ``Grep``,
  ``WebSearch``, ``WebFetch``, ``codesearch``, ``LSP``, ``Brief``,
  ``AskUserQuestion``); excludes ``Bash``, ``ExecuteCode``,
  ``Write``, ``Edit``, ``Patch``, ``apply_patch``, ``Browser``,
  ``send_message``.
* ``research`` — same as ``safe`` plus ``pdf_extract`` and
  ``image_describe``.
* ``coding`` — ``safe`` ∪ ``Write`` / ``Edit`` / ``Patch`` /
  ``apply_patch`` / ``NotebookEdit`` / ``TodoWrite``; excludes
  ``Bash``, ``ExecuteCode``, ``Browser``, ``send_message``.
* ``ops`` — ``coding`` ∪ ``Bash`` / ``ExecuteCode`` / ``Browser`` /
  ``send_message`` (everything available, equivalent to ``default``).

Custom bundles are added at runtime via ``register_toolset(name,
tools)``; they round-trip through ``~/.lyra/config.yaml`` under
``toolsets:``.

The names listed in each bundle are *advisory* — the actual tool
catalogue depends on what the kernel + MCP autoloader registered. If
a toolset references a tool that isn't available, ``apply_toolset``
silently drops it and reports the diff via ``applied`` / ``skipped``.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Iterable

_DEFAULT_TOOLSETS: dict[str, tuple[str, ...]] = {
    "default": (
        "Read",
        "Glob",
        "Grep",
        "Edit",
        "Write",
        "Bash",
        "Patch",
        "apply_patch",
        "NotebookEdit",
        "WebSearch",
        "WebFetch",
        "TodoWrite",
        "codesearch",
        "LSP",
        "ExecuteCode",
        "Browser",
        "AskUserQuestion",
        "send_message",
        "pdf_extract",
        "image_describe",
        "image_ocr",
        "Task",
    ),
    "safe": (
        "Read",
        "Glob",
        "Grep",
        "WebSearch",
        "WebFetch",
        "codesearch",
        "LSP",
        "AskUserQuestion",
    ),
    "research": (
        "Read",
        "Glob",
        "Grep",
        "WebSearch",
        "WebFetch",
        "codesearch",
        "LSP",
        "AskUserQuestion",
        "pdf_extract",
        "image_describe",
        "image_ocr",
    ),
    "coding": (
        "Read",
        "Glob",
        "Grep",
        "Edit",
        "Write",
        "Patch",
        "apply_patch",
        "NotebookEdit",
        "WebSearch",
        "WebFetch",
        "TodoWrite",
        "codesearch",
        "LSP",
        "AskUserQuestion",
    ),
    "ops": (
        "Read",
        "Glob",
        "Grep",
        "Edit",
        "Write",
        "Bash",
        "Patch",
        "apply_patch",
        "NotebookEdit",
        "WebSearch",
        "WebFetch",
        "TodoWrite",
        "codesearch",
        "LSP",
        "ExecuteCode",
        "Browser",
        "AskUserQuestion",
        "send_message",
        "Task",
    ),
}


@dataclass(frozen=True)
class ToolsetApplication:
    """Result of applying a toolset to a tool catalogue."""

    name: str
    requested: tuple[str, ...]
    available: tuple[str, ...]
    applied: tuple[str, ...]
    skipped: tuple[str, ...]
    enabled_now: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "requested": list(self.requested),
            "available": list(self.available),
            "applied": list(self.applied),
            "skipped": list(self.skipped),
            "enabled_now": list(self.enabled_now),
        }


@dataclass
class ToolsetRegistry:
    """Mutable registry of named tool bundles (hermes-agent parity).

    The defaults are seeded once at construction; custom bundles are
    layered on top via :meth:`register`. ``ToolsetRegistry`` is a
    plain dataclass so tests can subclass / patch / round-trip
    through YAML without surprises.
    """

    bundles: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: deepcopy(_DEFAULT_TOOLSETS)
    )

    def names(self) -> tuple[str, ...]:
        return tuple(self.bundles.keys())

    def get(self, name: str) -> tuple[str, ...]:
        if name not in self.bundles:
            raise KeyError(f"unknown toolset: {name!r}; known: {self.names()!r}")
        return self.bundles[name]

    def register(self, name: str, tools: Iterable[str]) -> None:
        if not name or not name.strip():
            raise ValueError("toolset name must be non-empty")
        ordered = tuple(dict.fromkeys(tools))
        if not ordered:
            raise ValueError(f"toolset {name!r} cannot be empty")
        self.bundles[name] = ordered

    def remove(self, name: str) -> None:
        if name in _DEFAULT_TOOLSETS:
            raise ValueError(f"cannot remove built-in toolset {name!r}")
        self.bundles.pop(name, None)

    def apply(
        self,
        name: str,
        *,
        available: Iterable[str],
    ) -> ToolsetApplication:
        """Return the diff between ``self.get(name)`` and ``available``.

        ``available`` is the catalogue the kernel actually has at this
        moment; tools requested by the bundle that aren't available
        land in ``skipped`` (with no error so the registry survives
        plugin / MCP availability changes).
        """
        requested = self.get(name)
        avail_tuple = tuple(dict.fromkeys(available))
        avail_set = set(avail_tuple)
        applied = tuple(t for t in requested if t in avail_set)
        skipped = tuple(t for t in requested if t not in avail_set)
        return ToolsetApplication(
            name=name,
            requested=requested,
            available=avail_tuple,
            applied=applied,
            skipped=skipped,
            enabled_now=applied,
        )


_REGISTRY = ToolsetRegistry()


def default_toolsets() -> dict[str, tuple[str, ...]]:
    """Return a copy of the built-in toolset map."""
    return deepcopy(_DEFAULT_TOOLSETS)


def get_registry() -> ToolsetRegistry:
    """Return the module-level registry (singleton convenience)."""
    return _REGISTRY


def list_toolsets() -> tuple[str, ...]:
    return _REGISTRY.names()


def get_toolset(name: str) -> tuple[str, ...]:
    return _REGISTRY.get(name)


def register_toolset(name: str, tools: Iterable[str]) -> None:
    _REGISTRY.register(name, tools)


def apply_toolset(name: str, *, available: Iterable[str]) -> ToolsetApplication:
    return _REGISTRY.apply(name, available=available)


__all__ = [
    "ToolsetApplication",
    "ToolsetRegistry",
    "apply_toolset",
    "default_toolsets",
    "get_registry",
    "get_toolset",
    "list_toolsets",
    "register_toolset",
]
