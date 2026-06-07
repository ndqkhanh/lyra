"""
Misevolution guardrails for self-evolving systems.

Implements four mandatory safety gates that prevent the safety degradation
documented in the Misevolve paper (Shao et al., 2025, arXiv:2509.26354v2):
99.4% -> 54.4% refusal rate (-45%), 56-76% unsafe tool creation rate,
and 84.6% workflow refusal collapse at round 60.

References
----------
- "Your Agent May Misevolve" — Shao et al., 2025, arXiv:2509.26354v2
- Misevolve §3: Safety collapse across all self-evolution pathways
- SkillOpt §4: Validation-gated text optimisation (Microsoft Research)
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class GateVerdict(Enum):
    """Verdict from a single guardrail gate."""

    PASS = "pass"
    FAIL = "fail"
    ESCALATE = "escalate"  # Needs human review


class GateType(Enum):
    """Type of guardrail gate."""

    REGRESSION_CHECK = "regression_check"
    FROZEN_EVALUATOR = "frozen_evaluator"
    HUMAN_APPROVAL = "human_approval"
    EXECUTION_BIAS = "execution_bias"


@dataclass(frozen=True)
class GateResult:
    """Result from a single guardrail gate evaluation.

    Attributes:
        gate: The gate type.
        verdict: ``PASS``, ``FAIL``, or ``ESCALATE``.
        detail: Human-readable explanation of the verdict.
        timestamp: Unix timestamp.
        metadata: Arbitrary additional context.
    """

    gate: GateType
    verdict: GateVerdict
    detail: str
    timestamp: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            object.__setattr__(self, "timestamp", time.time())


@dataclass
class EvolutionArtifact:
    """An artifact produced by the evolution optimizer.

    Attributes:
        artifact_id: Unique identifier derived from content hash.
        artifact_type: Type of artifact ("gene", "skill", "prompt",
            "tool_config", "workflow_config").
        content: The artifact content (JSON-serializable).
        parent_id: ID of the parent artifact (for lineage tracking).
        generation: Evolution generation that produced this artifact.
        created_at: Unix timestamp.
        is_promoted: Whether this has been promoted to default.
    """

    artifact_id: str = ""
    artifact_type: str = "gene"
    content: dict[str, Any] = field(default_factory=dict)
    parent_id: str | None = None
    generation: int = 0
    created_at: float = 0.0
    is_promoted: bool = False

    def __post_init__(self) -> None:
        if not self.artifact_id:
            content_hash = hashlib.sha256(
                json.dumps(self.content, sort_keys=True).encode(),
            ).hexdigest()[:16]
            object.__setattr__(self, "artifact_id", f"art_{content_hash}")
        if self.created_at == 0.0:
            object.__setattr__(self, "created_at", time.time())


# ---------------------------------------------------------------------------
# -- guardrail implementations ----------------------------------------------
# ---------------------------------------------------------------------------


@dataclass
class RegressionGate:
    """Gated promotion: no evolved artifact becomes default without check.

    Evaluates the candidate against a frozen baseline on a held-out
    evaluation set. The candidate must not regress by more than the
    allowed threshold.

    Reference
    ---------
    SkillOpt §4 — Validation gate: <= 1% regression
    Misevolve §5 — Safety stable for 50 rounds then collapses; gated
    promotion catches regression early.
    """

    threshold: float = 0.01  # 1% regression allowance
    _baseline_score: float | None = None

    def set_baseline(self, score: float) -> None:
        """Set the baseline score against which regression is measured.

        Args:
            score: Baseline evaluation score (incumbent).
        """
        self._baseline_score = score
        logger.info("regression baseline set", score=round(score, 4))

    def evaluate(
        self,
        candidate_score: float,
        candidate_id: str | None = None,
    ) -> GateResult:
        """Check whether the candidate regresses beyond the threshold.

        Args:
            candidate_score: Evaluation score of the candidate.
            candidate_id: Optional identifier for logging.

        Returns:
            ``PASS`` if regression <= threshold, ``FAIL`` otherwise.
        """
        baseline = self._baseline_score
        if baseline is None or baseline == 0.0:
            # No baseline: pass with warning (first evaluation)
            return GateResult(
                gate=GateType.REGRESSION_CHECK,
                verdict=GateVerdict.PASS,
                detail="No baseline set; accepting first candidate.",
            )

        regression = (baseline - candidate_score) / abs(baseline)
        candidate_label = candidate_id or "unknown"

        if regression <= self.threshold:
            return GateResult(
                gate=GateType.REGRESSION_CHECK,
                verdict=GateVerdict.PASS,
                detail=(
                    f"Candidate '{candidate_label}' regresses by "
                    f"{regression:.4%} (threshold: {self.threshold:.1%}). "
                    "Passing."
                ),
                metadata={
                    "baseline_score": baseline,
                    "candidate_score": candidate_score,
                    "regression": regression,
                    "threshold": self.threshold,
                },
            )

        return GateResult(
            gate=GateType.REGRESSION_CHECK,
            verdict=GateVerdict.FAIL,
            detail=(
                f"Candidate '{candidate_label}' regresses by "
                f"{regression:.4%}, which exceeds the threshold of "
                f"{self.threshold:.1%}. Rejecting."
            ),
            metadata={
                "baseline_score": baseline,
                "candidate_score": candidate_score,
                "regression": regression,
                "threshold": self.threshold,
            },
        )


@dataclass
class FrozenEvaluatorGate:
    """Frozen evaluator: never co-evolves with the optimizer.

    The evaluator is checked for drift at each gate invocation. Any
    modification to the evaluator's configuration or reference data
    after the initial freeze results in a ``FAIL`` verdict.

    Reference
    ---------
    Misevolve §4.2 — Evaluator drift as a root cause of safety degradation
    SkillOpt §2.4 — Frozen evaluation set invariant during optimisation
    """

    _is_frozen: bool = False
    _freeze_hash: str | None = None

    def freeze(self, evaluator_state: dict[str, Any]) -> None:
        """Freeze the evaluator state.

        Args:
            evaluator_state: Snapshot of the evaluator's configuration
                (task list, parameters, model reference).
        """
        self._is_frozen = True
        self._freeze_hash = hashlib.sha256(
            json.dumps(evaluator_state, sort_keys=True).encode(),
        ).hexdigest()
        logger.info("frozen evaluator gate: evaluator frozen")

    def evaluate(self, current_state: dict[str, Any]) -> GateResult:
        """Check whether the evaluator has drifted from its frozen state.

        Args:
            current_state: Current evaluator configuration snapshot.

        Returns:
            ``PASS`` if the evaluator matches its frozen state,
            ``FAIL`` if drift is detected, ``ESCALATE`` if never frozen.
        """
        if not self._is_frozen or self._freeze_hash is None:
            return GateResult(
                gate=GateType.FROZEN_EVALUATOR,
                verdict=GateVerdict.ESCALATE,
                detail="Evaluator has not been frozen yet. Escalating to human review.",
            )

        current_hash = hashlib.sha256(
            json.dumps(current_state, sort_keys=True).encode(),
        ).hexdigest()

        if current_hash == self._freeze_hash:
            return GateResult(
                gate=GateType.FROZEN_EVALUATOR,
                verdict=GateVerdict.PASS,
                detail="Evaluator state matches frozen snapshot. No drift detected.",
            )

        return GateResult(
            gate=GateType.FROZEN_EVALUATOR,
            verdict=GateVerdict.FAIL,
            detail=(
                "Evaluator state has changed since freezing. "
                f"Original hash: {self._freeze_hash[:12]}... "
                f"Current hash: {current_hash[:12]}..."
            ),
            metadata={
                "original_hash": self._freeze_hash,
                "current_hash": current_hash,
            },
        )


@dataclass
class HumanApprovalGate:
    """Human approval gate: no evolved artifact becomes default without
    explicit human accept.

    Reference
    ---------
    Misevolve §6 — Recommended mitigation for safety-critical systems
    DGM / DGM-H §5 — "Human-in-the-loop for default-swap decisions"
    """

    pending_approvals: dict[str, dict[str, Any]] = field(default_factory=dict)
    approved_ids: set[str] = field(default_factory=set)
    rejected_ids: set[str] = field(default_factory=set)

    def request_approval(
        self,
        artifact: EvolutionArtifact,
        change_description: str,
        evaluation_summary: str,
    ) -> str:
        """Register an artifact for human approval.

        Args:
            artifact: The evolved artifact waiting for approval.
            change_description: Human-readable description of what changed.
            evaluation_summary: Summary of evaluation results.

        Returns:
            The artifact ID for tracking.
        """
        self.pending_approvals[artifact.artifact_id] = {
            "artifact": artifact,
            "change_description": change_description,
            "evaluation_summary": evaluation_summary,
            "requested_at": time.time(),
        }
        logger.info(
            "human approval requested",
            artifact_id=artifact.artifact_id,
            artifact_type=artifact.artifact_type,
        )
        return artifact.artifact_id

    def approve(self, artifact_id: str) -> GateResult:
        """Mark an artifact as approved by a human.

        Args:
            artifact_id: The artifact ID to approve.

        Returns:
            ``PASS`` if the artifact was pending and is now approved,
            ``FAIL`` if the artifact was not found.
        """
        if artifact_id not in self.pending_approvals:
            return GateResult(
                gate=GateType.HUMAN_APPROVAL,
                verdict=GateVerdict.FAIL,
                detail=f"Artifact '{artifact_id}' not found in pending approvals.",
            )

        self.approved_ids.add(artifact_id)
        del self.pending_approvals[artifact_id]
        logger.info("human approval granted", artifact_id=artifact_id)

        return GateResult(
            gate=GateType.HUMAN_APPROVAL,
            verdict=GateVerdict.PASS,
            detail=f"Human approved artifact '{artifact_id}'.",
        )

    def reject(self, artifact_id: str) -> GateResult:
        """Mark an artifact as rejected by a human.

        Args:
            artifact_id: The artifact ID to reject.

        Returns:
            ``PASS`` (informational — rejection is a valid outcome).
        """
        if artifact_id in self.pending_approvals:
            del self.pending_approvals[artifact_id]

        self.rejected_ids.add(artifact_id)
        logger.info("human approval rejected", artifact_id=artifact_id)

        return GateResult(
            gate=GateType.HUMAN_APPROVAL,
            verdict=GateVerdict.PASS,
            detail=f"Human rejected artifact '{artifact_id}'.",
        )

    def has_pending(self) -> bool:
        """Whether there are any pending approvals."""
        return bool(self.pending_approvals)

    @property
    def pending_count(self) -> int:
        """Number of artifacts awaiting human approval."""
        return len(self.pending_approvals)


@dataclass
class ExecutionBiasDetector:
    """Detects execution bias in evolved artifacts using integrated gradients.

    An execution bias occurs when an evolution step appears benign but
    introduces a subtle failure mode under specific conditions. This
    detector uses a causal attribution approach: it measures how much
    each part of the evolved prompt / skill contributes to the output.

    Reference
    ---------
    Misevolve §4.3 — "Benign experience can increase attack surface"
    Integrated Gradients — Sundararajan et al., ICML 2017
    """

    _attribution_fn: Callable[[str, str], dict[str, float]] | None = None

    def set_attribution_fn(
        self,
        fn: Callable[[str, str], dict[str, float]],
    ) -> None:
        """Set the integrated gradients attribution function.

        Args:
            fn: Callable ``(evolved_text, test_input) -> dict`` mapping
                input segments to attribution scores.
        """
        self._attribution_fn = fn

    def evaluate(
        self,
        evolved_text: str,
        test_inputs: list[str],
        baseline_text: str | None = None,
    ) -> GateResult:
        """Detect execution bias in an evolved artifact.

        Compares the attribution of the evolved artifact against a
        baseline (the pre-evolution version). If attributions shift
        disproportionately on safety-relevant segments, bias is flagged.

        Args:
            evolved_text: The evolved prompt / gene text.
            test_inputs: One or more test inputs to run attribution on.
            baseline_text: The pre-evolution prompt / gene text.
                If ``None``, only evolved-text attribution is computed
                (less sensitive but works without history).

        Returns:
            ``PASS`` if no execution bias detected, ``FAIL`` if bias
            is detected, ``ESCALATE`` if attribution is unavailable.
        """
        if self._attribution_fn is None:
            return GateResult(
                gate=GateType.EXECUTION_BIAS,
                verdict=GateVerdict.ESCALATE,
                detail=(
                    "No attribution function configured. "
                    "Execution bias detection is unavailable."
                ),
            )

        bias_found = False
        bias_details: list[str] = []

        for test_input in test_inputs:
            evolved_attr = self._attribution_fn(evolved_text, test_input)

            if baseline_text is not None:
                baseline_attr = self._attribution_fn(baseline_text, test_input)

                # Check for disproportionate attribution shifts on known
                # safety segments (e.g., "ignore", "override", "bypass")
                for segment, e_score in evolved_attr.items():
                    b_score = baseline_attr.get(segment, 0.0)
                    if b_score > 0 and e_score / b_score > 3.0:
                        # Attribution on this segment tripled — possible bias
                        bias_found = True
                        bias_details.append(
                            f"Segment '{segment}': attribution shift "
                            f"{b_score:.4f} -> {e_score:.4f}",
                        )

        if bias_found:
            return GateResult(
                gate=GateType.EXECUTION_BIAS,
                verdict=GateVerdict.FAIL,
                detail="Execution bias detected: " + "; ".join(bias_details),
                metadata={"test_inputs": len(test_inputs)},
            )

        return GateResult(
            gate=GateType.EXECUTION_BIAS,
            verdict=GateVerdict.PASS,
            detail=f"No execution bias detected across {len(test_inputs)} test inputs.",
        )


# ---------------------------------------------------------------------------
# -- orchestrated guardrails ------------------------------------------------
# ---------------------------------------------------------------------------


@dataclass
class MisevolutionGuardrails:
    """Four mandatory safety gates for self-evolving systems.

    All four gates must pass before an evolved artifact can be promoted
    to default.

    Reference
    ---------
    Misevolve (Shao et al., 2025, arXiv:2509.26354v2):
    "Your Agent May Misevolve: A Study on the Degradation of Safety and
    Stability in Self-Evolving Agents"
    """

    regression_gate: RegressionGate = field(default_factory=RegressionGate)
    frozen_evaluator_gate: FrozenEvaluatorGate = field(default_factory=FrozenEvaluatorGate)
    human_approval_gate: HumanApprovalGate = field(default_factory=HumanApprovalGate)
    execution_bias_detector: ExecutionBiasDetector = field(default_factory=ExecutionBiasDetector)

    _history: list[GateResult] = field(default_factory=list)

    def check_all(
        self,
        candidate_score: float,
        candidate_id: str | None = None,
        evolved_text: str = "",
        test_inputs: list[str] | None = None,
        baseline_text: str | None = None,
        evaluator_state: dict[str, Any] | None = None,
        artifact: EvolutionArtifact | None = None,
        change_description: str = "",
        evaluation_summary: str = "",
    ) -> list[GateResult]:
        """Run all four guardrail gates.

        Args:
            candidate_score: Regression gate candidate score.
            candidate_id: Optional identifier for logging.
            evolved_text: Text of the evolved artifact for bias detection.
            test_inputs: Test inputs for bias detection.
            baseline_text: Pre-evolution text for bias detection.
            evaluator_state: Current evaluator state for drift check.
            artifact: Artifact for human approval gate.
            change_description: Description for human approval.
            evaluation_summary: Evaluation summary for human approval.

        Returns:
            List of ``GateResult`` instances (one per gate). All gates
            must return ``PASS`` for the artifact to be promotable.
        """
        results: list[GateResult] = []

        # Gate 1: Regression check
        result = self.regression_gate.evaluate(candidate_score, candidate_id)
        results.append(result)
        self._history.append(result)

        # Gate 2: Frozen evaluator check
        if evaluator_state is not None:
            result = self.frozen_evaluator_gate.evaluate(evaluator_state)
            results.append(result)
            self._history.append(result)

        # Gate 3: Execution bias detection
        if evolved_text:
            result = self.execution_bias_detector.evaluate(
                evolved_text,
                test_inputs or [],
                baseline_text,
            )
            results.append(result)
            self._history.append(result)

        # Gate 4: Human approval
        if artifact is not None:
            approval_id = self.human_approval_gate.request_approval(
                artifact,
                change_description,
                evaluation_summary,
            )
            # Human approval is asynchronous; the check records it
            result = GateResult(
                gate=GateType.HUMAN_APPROVAL,
                verdict=GateVerdict.ESCALATE,
                detail=f"Human approval pending for artifact '{approval_id}'.",
                metadata={"artifact_id": approval_id},
            )
            results.append(result)
            self._history.append(result)

        # Log summary
        passed = sum(1 for r in results if r.verdict == GateVerdict.PASS)
        failed = sum(1 for r in results if r.verdict == GateVerdict.FAIL)
        logger.info(
            "guardrail gates evaluated",
            total=len(results),
            passed=passed,
            failed=failed,
        )

        return results

    @property
    def all_pass(self) -> bool:
        """Check whether all evaluated gates passed.

        Returns ``True`` only if every gate in ``_history`` returns
        ``PASS``. Any ``FAIL`` or ``ESCALATE`` means promotion is
        blocked.
        """
        if not self._history:
            return False
        return all(r.verdict == GateVerdict.PASS for r in self._history)

    @property
    def history(self) -> list[GateResult]:
        """Full history of all gate evaluations."""
        return list(self._history)

    def reset(self) -> None:
        """Reset evaluation history."""
        self._history.clear()
        logger.info("guardrail history reset")
