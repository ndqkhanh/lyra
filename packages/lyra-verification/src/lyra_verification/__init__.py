"""lyra-verification: 4-layer verification architecture for Lyra AGI.

Layer 1 — Inline Guards (<200 ms)
    PII detection, toxicity, NLI entailment, token entropy, prompt injection.

Layer 2 — Online Sampling (~seconds)
    LLM-as-Judge with debiasing (style / position bias), hallucination
    detection via HaMI (token uncertainty + MIL), entity grounding, and
    relation preservation.

Layer 3 — Offline Deep (~minutes)
    Multi-agent D3 debate, cross-reference fact-check, citation audit,
    behavioral fingerprint regression.

Layer 4 — Continuous Monitoring (daily+)
    Drift detection, PAEF failure modes, KG structural diff, user
    satisfaction aggregation.
"""

from __future__ import annotations

from lyra_verification.hallucination import HallucinationDetector
from lyra_verification.inline_guards import InlineGuardResult, InlineGuardSystem
from lyra_verification.judge import DebiasedJudge
from lyra_verification.models import (
    AttributionEigenvalues,
    BehavioralFingerprint,
    CitationAudit,
    DriftAlert,
    DriftReport,
    EntityGrounding,
    HallucinationSignal,
    JudgeEvaluation,
    PAEFFailure,
    RegressionVerdict,
    SecurityCheck,
    Verdict,
    VerificationResult,
)
from lyra_verification.monitoring import ContinuousMonitor
from lyra_verification.regression import AgentRegressionTester

__all__ = [
    "InlineGuardSystem",
    "InlineGuardResult",
    "HallucinationDetector",
    "DebiasedJudge",
    "AgentRegressionTester",
    "ContinuousMonitor",
    "Verdict",
    "PAEFFailure",
    "SecurityCheck",
    "VerificationResult",
    "HallucinationSignal",
    "CitationAudit",
    "DriftAlert",
    "JudgeEvaluation",
    "BehavioralFingerprint",
    "RegressionVerdict",
    "DriftReport",
    "AttributionEigenvalues",
    "EntityGrounding",
]
