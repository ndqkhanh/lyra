"""Breakthrough Integration — wires Plans 6-10 into lyra-core.

Provides one-stop import for all breakthrough packages and a unified
integration facade that connects them.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "BreakthroughIntegration",
    "breakthrough_available",
]


def breakthrough_available() -> dict[str, bool]:
    """Check which breakthrough packages are installed."""
    packages = {
        "instincts": False, "beliefs": False, "memory_token": False,
        "memory_vericache": False, "router": False, "identity": False,
        "resilience": False, "sla": False, "experiment": False,
        "etl_pipeline": False, "command_registry": False,
        "ecology": False, "emergence": False,
    }
    for key in packages:
        try:
            __import__(f"lyra_{key}")
            packages[key] = True
        except ImportError:
            pass
    return packages


class BreakthroughIntegration:
    """Facade connecting all breakthrough packages into the agent loop."""

    def __init__(self):
        self._available = breakthrough_available()
        self._instincts = None
        self._beliefs = None
        self._router = None
        self._identity = None
        self._resilience = None
        self._sla = None
        self._experiment = None
        self._ecology = None

    def initialize(self) -> dict[str, bool]:
        """Lazy-initialize all available breakthrough subsystems."""
        if self._available.get("instincts"):
            from lyra_instincts import InstinctEngine
            self._instincts = InstinctEngine()
        if self._available.get("beliefs"):
            from lyra_beliefs import BeliefSystem
            self._beliefs = BeliefSystem()
        if self._available.get("router"):
            from lyra_router import AgentRouter
            self._router = AgentRouter()
        if self._available.get("identity"):
            from lyra_identity import AgentIdentity
            self._identity = AgentIdentity("lyra")
        if self._available.get("resilience"):
            from lyra_resilience import CircuitBreaker, RecoveryLadder
            self._resilience = {"circuit_breaker": CircuitBreaker("lyra"), "recovery_ladder": RecoveryLadder()}
        if self._available.get("sla"):
            from lyra_sla import SLAManager
            self._sla = SLAManager()
        if self._available.get("experiment"):
            from lyra_experiment import ExperimentRegistry
            self._experiment = ExperimentRegistry()
        if self._available.get("ecology"):
            from lyra_ecology import AgentEcology
            self._ecology = AgentEcology()
        return self._available

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "available_subsystems": [k for k, v in self._available.items() if v],
            "initialized": {
                "instincts": self._instincts is not None,
                "beliefs": self._beliefs is not None,
                "router": self._router is not None,
                "identity": self._identity is not None,
                "resilience": self._resilience is not None,
                "sla": self._sla is not None,
                "experiment": self._experiment is not None,
                "ecology": self._ecology is not None,
            },
        }
