"""harness_core.verifier — multi-axis composable safety gates for actions.

Per [docs/221-aegis-ops-multi-hop-collaborative-apply-plan.md](../../../../../../research/harness-engineering/docs/221-aegis-ops-multi-hop-collaborative-apply-plan.md) §3.4
(Aegis-Ops "verifier composing dry-run + diff + policy + permission + HITL"),
[docs/220-orion-code-multi-hop-collaborative-apply-plan.md](../../../../../../research/harness-engineering/docs/220-orion-code-multi-hop-collaborative-apply-plan.md) §3.4
(Orion-Code "verifier composing test + lint + type-check + security-scan + BL-*"),
and [docs/11-verifier-evaluator-loops.md](../../../../../../research/harness-engineering/docs/11-verifier-evaluator-loops.md).

The composer runs N axis-typed verifiers in order, aggregates results into a
:class:`CompositeVerdict`, and reports the maximum severity. Each verifier
exposes its axis (test, lint, dry-run, diff, policy, permission, HITL,
security-scan, etc.) so dashboards and audit logs can group by axis.

Composes with:
    - :mod:`harness_core.gates` — single-doc gates (Chain-of-Note, Retraction,
      Dual-Use). Verifier is for *actions*, not retrieved docs.
    - :mod:`harness_core.orchestration.PureFunctionAgent` — verifiers can be
      wrapped to be replayable.
    - :mod:`harness_core.forensic.ReplayComparator` — failed verifications
      record into the trajectory's side-effect log for later audit.
"""
from __future__ import annotations

from .composer import (
    AxisVerdict,
    CompositeVerdict,
    HITLVerifier,
    Severity,
    StubDiffVerifier,
    StubDryRunVerifier,
    StubPermissionVerifier,
    StubPolicyVerifier,
    Verifier,
    VerifierAxis,
    VerifierComposer,
)

__all__ = [
    "AxisVerdict",
    "CompositeVerdict",
    "HITLVerifier",
    "Severity",
    "StubDiffVerifier",
    "StubDryRunVerifier",
    "StubPermissionVerifier",
    "StubPolicyVerifier",
    "Verifier",
    "VerifierAxis",
    "VerifierComposer",
]
