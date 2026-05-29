"""Quality gates and verification system for Lyra Research.

This module provides:
- Quality gates between role transitions
- Quality criteria evaluation
- Gate enforcement (pass/retry/reject/escalate)
- Verification system (completeness, accuracy, consistency)
"""
from lyra_research.quality.analysis_gate import AnalysisGate
from lyra_research.quality.curation_gate import CurationGate
from lyra_research.quality.discovery_gate import DiscoveryGate
from lyra_research.quality.gate_enforcer import (
    EnforcementResult,
    GateEnforcer,
)
from lyra_research.quality.quality_criterion import (
    CriterionResult,
    QualityCriterion,
)
from lyra_research.quality.quality_gate import (
    GateResult,
    QualityGate,
)
from lyra_research.quality.review_gate import ReviewGate
from lyra_research.quality.synthesis_gate import SynthesisGate
from lyra_research.quality.verifier import (
    VerificationResult,
    Verifier,
)

__all__ = [
    "QualityCriterion",
    "CriterionResult",
    "QualityGate",
    "GateResult",
    "DiscoveryGate",
    "AnalysisGate",
    "SynthesisGate",
    "ReviewGate",
    "CurationGate",
    "GateEnforcer",
    "EnforcementResult",
    "Verifier",
    "VerificationResult",
]
