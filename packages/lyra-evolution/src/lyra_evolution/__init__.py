"""lyra-evolution — Phase 6: Multi-agent self-evolution.

Council Mode, Escher-Loop RSI, GEAR-Evolve search, and closed-loop
self-improvement for the Lyra AGI V4 Ultra Plan.
"""

from __future__ import annotations

from .council import CouncilMode
from .escher import EscherLoop
from .gear import GEAREvolve
from .improvement import SelfImprovement
from .models import (
    CouncilDecision,
    CouncilMember,
    CouncilVote,
    EscherGeneration,
    EscherSolver,
    EvolutionMetrics,
    GEARStrategy,
)

__version__ = "0.2.0"

__all__ = [
    # Council Mode
    "CouncilMember",
    "CouncilVote",
    "CouncilDecision",
    "CouncilMode",
    # Escher-Loop RSI
    "EscherSolver",
    "EscherGeneration",
    "EscherLoop",
    # GEAR-Evolve
    "GEARStrategy",
    "GEAREvolve",
    # Self-Improvement
    "SelfImprovement",
    "EvolutionMetrics",
]
