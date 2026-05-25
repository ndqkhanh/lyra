"""lyra-evolution — Phase 6: Multi-agent self-evolution.

Council Mode, Escher-Loop RSI, GEAR-Evolve search, and closed-loop
self-improvement for the Lyra AGI V4 Ultra Plan.

Phase 3 (Months 7-12): Self-Modification & AGI Capabilities
- Code Analysis: Static analysis and bottleneck detection
- Code Generation: Optimization patches and refactoring
- Sandbox Execution: Safe code execution with rollback
"""

from __future__ import annotations

from .analysis import AnalysisResult, Bottleneck, CodeAnalyzer, ComplexityMetrics
from .council import CouncilMode
from .drift_detector import DriftAlert, DriftReport, DriftSignal, PRISMDriftDetector
from .escher import EscherLoop
from .gear import GEAREvolve
from .generation import CodeGenerator, GeneratedPatch, RefactoringSuggestion
from .gepa_v2 import Candidate, EvolutionConfig, GEPAv2, ParetoFrontier
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
from .sandbox import ExecutionResult, SandboxConfig, SandboxExecutor, Snapshot

__version__ = "0.3.0"

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
    # Phase 3: Code Analysis
    "CodeAnalyzer",
    "AnalysisResult",
    "Bottleneck",
    "ComplexityMetrics",
    # Phase 3: Code Generation
    "CodeGenerator",
    "GeneratedPatch",
    "RefactoringSuggestion",
    # Phase 3: Sandbox Execution
    "SandboxExecutor",
    "ExecutionResult",
    "SandboxConfig",
    "Snapshot",
    # Phase 13.4: PRISM Drift Detection
    "DriftSignal",
    "DriftAlert",
    "DriftReport",
    "PRISMDriftDetector",
    # Phase 13.4: GEPA v2 Prompt Evolution
    "Candidate",
    "ParetoFrontier",
    "EvolutionConfig",
    "GEPAv2",
]
