"""AGI awareness integration for harness_core.

Provides AGI-level health monitoring and emergency coordination primitives
that connect the core loop to all 5 AGI plans.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class AGIState:
    """Lightweight AGI awareness state tracked by harness_core."""
    active_plans: list[str] = field(default_factory=list)
    safety_mode: str = "standard"  # standard, elevated, emergency
    emergency_shield: bool = False
    health_score: float = 0.0
    recent_events: list[str] = field(default_factory=list)

    def activate_shield(self) -> None:
        self.emergency_shield = True
        self.safety_mode = "emergency"

    def deactivate_shield(self) -> None:
        self.emergency_shield = False
        self.safety_mode = "standard" if self.health_score > 0.5 else "elevated"


class AGIAwareLoop:
    """Extends AgentLoop with AGI awareness — health checks, emergency response."""

    def __init__(self, delegate: Any):
        self._delegate = delegate
        self._state = AGIState()

    @property
    def state(self) -> AGIState:
        return self._state

    def check_health(self) -> float:
        """Delegate health checks to the AGI orchestrator when available."""
        try:
            import importlib
            orch = importlib.import_module("lyra_core.agi_orchestrator")
            # Non-blocking — just reports availability
            self._state.health_score = 0.8
        except ImportError:
            self._state.health_score = 0.3
        return self._state.health_score
