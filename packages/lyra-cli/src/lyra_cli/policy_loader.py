"""Settings-driven loaders for the v3.10 permission grammar + user hooks.

Layered config (highest precedence wins):

1. **Project**  — ``<repo>/.lyra/settings.json``
2. **User**    — ``$LYRA_HOME/settings.json`` (env-var override; defaults to
   ``~/.lyra``)

Each layer contributes ``permissions`` and ``hooks`` blocks; the higher-
precedence layer's lists are merged ahead of (and short-circuit) the lower
layer's. This matches Claude Code's project>user>defaults order — pinning
project policy without forcing the user to drop their personal allowlist.

Why a thin wrapper instead of stuffing this into ``InteractiveSession``:
keeps the loader unit-testable in isolation. Tests build a fake settings
mapping and assert on the produced ``Policy`` / hook list without bringing
up a full session.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from lyra_core.hooks.user_hooks import HookSpec, parse_hooks_config
from lyra_core.permissions.grammar import Policy, policy_from_mapping

from .config_io import load_settings


def _layered_payloads(repo_root: Path) -> list[Mapping[str, Any]]:
    """Return per-layer settings dicts in **decreasing** precedence order.

    Project settings come first so they shadow user settings on
    matching rule lists. Missing files contribute an empty mapping
    rather than being skipped — keeps the merge logic uniform.
    """
    project = repo_root / ".lyra" / "settings.json"
    user_home = Path(os.environ.get("LYRA_HOME") or "~/.lyra").expanduser()
    user_path = user_home / "settings.json"
    return [load_settings(project), load_settings(user_path)]


def _merged_permissions(
    layers: list[Mapping[str, Any]],
) -> dict[str, list[str]]:
    """Concat allow/ask/deny lists across layers, project layer first.

    Concatenation (rather than overwrite) is the right semantic
    because rules combine: a user-level ``deny`` should still apply
    even if the project file declares its own ``deny`` block.
    Order-within-list matters because ``Policy.decide`` returns the
    first match — we keep project rules at the front so they fire
    before user rules.
    """
    merged: dict[str, list[str]] = {"allow": [], "ask": [], "deny": []}
    for layer in layers:
        block = layer.get("permissions") if isinstance(layer, Mapping) else None
        if not isinstance(block, Mapping):
            continue
        for key in ("allow", "ask", "deny"):
            value = block.get(key)
            if isinstance(value, list):
                merged[key].extend(str(v) for v in value)
    return merged


def load_policy(repo_root: Path) -> Policy:
    """Build a :class:`Policy` from the layered settings files.

    A repo with no settings files yields an empty :class:`Policy` —
    callers should treat that as "use defaults" rather than "deny
    everything", which would brick a fresh checkout.
    """
    layers = _layered_payloads(repo_root)
    merged = _merged_permissions(layers)
    if not any(merged.values()):
        return Policy()
    return policy_from_mapping({"permissions": merged})


def load_hooks(repo_root: Path) -> tuple[list[HookSpec], bool]:
    """Build the user-hooks spec list + master enable flag.

    Hooks short-circuit on the *first* layer that declares
    ``enable_hooks: true`` — flipping it on at the project level
    overrides a user-level disable, but a user who explicitly opted
    in stays opted in even if a particular project doesn't mention
    the key. Specs from both layers concat (project first) for the
    same reason as permissions: rules compose, not replace.
    """
    layers = _layered_payloads(repo_root)
    enabled = False
    specs: list[HookSpec] = []
    for layer in layers:
        layer_specs, layer_enabled = parse_hooks_config(layer)
        specs.extend(layer_specs)
        enabled = enabled or layer_enabled
    return specs, enabled


__all__ = ["load_hooks", "load_policy"]
