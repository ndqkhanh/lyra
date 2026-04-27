"""Harness plugin boundary: pluggable orchestration strategies."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HarnessPlugin:
    name: str
    description: str = ""


_REGISTRY: dict[str, HarnessPlugin] = {}


def register_harness(plugin: HarnessPlugin) -> None:
    _REGISTRY[plugin.name] = plugin


def get_harness(name: str) -> HarnessPlugin:
    if name not in _REGISTRY:
        raise KeyError(f"no harness plugin registered with name {name!r}")
    return _REGISTRY[name]


# ---------------------------------------------------------------------------
# Seed the default plugins so ``get_harness("three-agent")`` works out of box.
# ---------------------------------------------------------------------------
register_harness(HarnessPlugin(name="single-agent", description="one agent, one loop"))
register_harness(HarnessPlugin(name="three-agent", description="planner / executor / verifier"))
register_harness(HarnessPlugin(name="dag-teams", description="dynamic DAG + deterministic scheduler"))
