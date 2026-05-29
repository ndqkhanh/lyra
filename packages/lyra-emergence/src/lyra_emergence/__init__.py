"""Emergence Detector — scans agent ecologies for emergent behaviors and phase transitions.

Detects when agent collectives spontaneously develop new capabilities,
coordination patterns, or specializations not explicitly programmed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "EmergenceSignal",
    "PhaseTransition",
    "EmergenceDetector",
]


class EmergenceSignal(Enum):
    SPECIALIZATION = auto()
    COORDINATION = auto()
    INNOVATION = auto()
    SYMBIOSIS = auto()
    COMPETITION = auto()


@dataclass
class PhaseTransition:
    generation: int
    signal_type: EmergenceSignal
    description: str
    magnitude: float


class EmergenceDetector:
    """Detects emergent behaviors in agent collectives over time."""

    def __init__(self):
        self.transitions: list[PhaseTransition] = []
        self.history: dict[str, list[float]] = {
            "specialization_depth": [],
            "avg_fitness": [],
            "population": [],
            "diversity": [],
            "resources": [],
        }
        self._gen = 0

    def record_generation(self, stats: dict[str, Any]) -> dict[str, Any]:
        """Record a generation's stats and check for emergence."""
        self._gen += 1
        for key in self.history:
            if key in stats:
                self.history[key].append(stats[key])

        signals = []
        signal = self._check_specialization()
        if signal:
            signals.append(signal)
        signal = self._check_coordination()
        if signal:
            signals.append(signal)
        signal = self._check_innovation()
        if signal:
            signals.append(signal)
        signal = self._check_symbiosis()
        if signal:
            signals.append(signal)

        return {
            "generation": self._gen,
            "signals_detected": len(signals),
            "signals": [{"type": s.signal_type.name, "magnitude": s.magnitude} for s in signals],
            "total_transitions": len(self.transitions),
        }

    def _check_specialization(self) -> PhaseTransition | None:
        """Detect when agents develop distinct specializations."""
        depths = self.history["diversity"]
        if len(depths) < 5:
            return None
        recent = depths[-3:]
        older = depths[:3]
        if len(recent) < 3 or len(older) < 3:
            return None
        if sum(recent) > sum(older) * 1.5:
            transition = PhaseTransition(
                generation=self._gen,
                signal_type=EmergenceSignal.SPECIALIZATION,
                description=f"Diversity increased from {sum(older)/3:.1f} to {sum(recent)/3:.1f}",
                magnitude=(sum(recent) - sum(older)) / max(sum(older), 0.001),
            )
            self.transitions.append(transition)
            return transition
        return None

    def _check_coordination(self) -> PhaseTransition | None:
        """Detect when agents start coordinating (population vs resources)."""
        pops = self.history["population"]
        if len(pops) < 5:
            return None
        recent = pops[-3:]
        older = pops[:3]
        if len(recent) < 3 or len(older) < 3:
            return None
        recent_avg = sum(recent) / 3
        older_avg = sum(older) / 3
        if recent_avg > older_avg * 1.3:
            transition = PhaseTransition(
                generation=self._gen,
                signal_type=EmergenceSignal.COORDINATION,
                description=f"Population grew from {older_avg:.0f} to {recent_avg:.0f}",
                magnitude=(recent_avg - older_avg) / max(older_avg, 1),
            )
            self.transitions.append(transition)
            return transition
        return None

    def _check_innovation(self) -> PhaseTransition | None:
        """Detect unexpected fitness jumps (innovation)."""
        fits = self.history["avg_fitness"]
        if len(fits) < 5:
            return None
        recent = fits[-3:]
        older = fits[:3]
        if len(recent) < 3 or len(older) < 3:
            return None
        recent_avg = sum(recent) / 3
        older_avg = sum(older) / 3
        if recent_avg > older_avg * 1.5 and older_avg > 0.01:
            transition = PhaseTransition(
                generation=self._gen,
                signal_type=EmergenceSignal.INNOVATION,
                description=f"Fitness jumped from {older_avg:.2f} to {recent_avg:.2f}",
                magnitude=(recent_avg - older_avg) / older_avg,
            )
            self.transitions.append(transition)
            return transition
        return None

    def _check_symbiosis(self) -> PhaseTransition | None:
        """Detect when resource efficiency improves (agents work together)."""
        if "resources" not in self.history or len(self.history["resources"]) < 5:
            return None
        recent = self.history["resources"][-3:]
        older = self.history["resources"][:3]
        if len(recent) < 3 or len(older) < 3:
            return None
        recent_avg = sum(recent) / 3
        older_avg = sum(older) / 3
        if older_avg > 0 and recent_avg < older_avg * 0.7:
            transition = PhaseTransition(
                generation=self._gen,
                signal_type=EmergenceSignal.SYMBIOSIS,
                description=f"Resource consumption dropped by {(1 - recent_avg/older_avg)*100:.0f}%",
                magnitude=(older_avg - recent_avg) / older_avg,
            )
            self.transitions.append(transition)
            return transition
        return None

    def get_report(self) -> dict[str, Any]:
        return {
            "generations_tracked": self._gen,
            "transitions_detected": len(self.transitions),
            "transitions": [
                {"type": t.signal_type.name, "generation": t.generation, "magnitude": t.magnitude}
                for t in self.transitions
            ],
        }
