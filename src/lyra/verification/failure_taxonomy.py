"""
MUSE-Style Structured Failure Taxonomy for the Verification Panel.

Implements the MUSE paper's finding (arXiv 2606.03005): an externalized
verifier with a STRUCTURED FAILURE TAXONOMY consistently outperforms
self-critique across every difficulty level and model. The taxonomy
guides targeted repair feedback, avoiding the generic "try again" loop.

Key design decisions from MUSE:
- K=3 is the OPTIMAL repair budget (K=5 shows active degradation from
  over-correction — the model starts hallucinating fixes)
- Content-fingerprint loop detection prevents cycling on unfixable errors
- Failure types are actionable: each maps to a specific repair strategy

References
----------
- MUSE: A Unified Agentic Harness for MLLMs (Lu et al., arXiv 2606.03005v1)
- ErrorProbe: Self-Improving Error Diagnosis in MAS (arXiv 2604.17658v1)
- Lyra §4.16 Reliability Plan: plans/4.16-reliability.md
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class FailureType(str, Enum):
    """Structured failure taxonomy from MUSE + ErrorProbe synthesis.

    Each failure type maps to a specific repair strategy rather than
    a generic "try again." This is what makes externalized verification
    beat self-critique.
    """

    # --- MUSE taxonomy (visual/reasoning failures) ---
    HALLUCINATION = "hallucination"         # Claimed fact not in source
    OMISSION = "omission"                   # Missed a required step/fact
    CONTRADICTION = "contradiction"         # Self-contradiction within output
    OVER_GENERALIZATION = "over_generalization"  # Claim broader than evidence
    STRUCTURAL_ERROR = "structural_error"   # Output format/structure wrong

    # --- ErrorProbe taxonomy (agent failures) ---
    TOOL_MISUSE = "tool_misuse"             # Called wrong tool or wrong args
    PREMATURE_TERMINATION = "premature_termination"  # Stopped before done
    INFINITE_LOOP = "infinite_loop"         # Repeated same action without progress
    GOAL_DRIFT = "goal_drift"               # Wandered off-task

    # --- SABER taxonomy (safety failures) ---
    UNAUTHORIZED_MUTATION = "unauthorized_mutation"  # Mutated state without permission
    DATA_LEAK = "data_leak"                 # Exposed sensitive data in output
    INJECTION_VULNERABILITY = "injection_vulnerability"  # Output enables prompt injection

    # --- Generic ---
    UNCERTAIN = "uncertain"                 # Verifier unsure — escalate to human


# Repair strategies mapped to each failure type
REPAIR_STRATEGIES: dict[FailureType, str] = {
    FailureType.HALLUCINATION: (
        "Re-check the claim against the source. If the source does not "
        "confirm it, remove the claim or mark it as [Unverified]."
    ),
    FailureType.OMISSION: (
        "Re-scan the task requirements. Identify which required step was "
        "missed and add it. Do NOT change already-correct parts."
    ),
    FailureType.CONTRADICTION: (
        "Identify the two contradictory statements. Keep the one with "
        "stronger evidence. Remove or correct the other."
    ),
    FailureType.OVER_GENERALIZATION: (
        "Narrow the claim to match exactly what the evidence supports. "
        "Replace absolute statements with qualified ones."
    ),
    FailureType.STRUCTURAL_ERROR: (
        "Fix the output format to match the required schema. Check for "
        "missing fields, wrong types, or malformed syntax."
    ),
    FailureType.TOOL_MISUSE: (
        "Check the tool's documentation. Verify the tool name, required "
        "arguments, and argument types. Retry with correct parameters."
    ),
    FailureType.PREMATURE_TERMINATION: (
        "The task is not complete. List what still needs to be done and "
        "continue from where you stopped."
    ),
    FailureType.INFINITE_LOOP: (
        "You have repeated the same action without progress. STOP. "
        "Try a DIFFERENT approach. If stuck after 3 attempts, ask for help."
    ),
    FailureType.GOAL_DRIFT: (
        "Re-read the original task. Your recent actions have drifted. "
        "Return to the main objective."
    ),
    FailureType.UNAUTHORIZED_MUTATION: (
        "This action modifies state without verification. Route through "
        "the SABER mutation gate before retrying."
    ),
    FailureType.DATA_LEAK: (
        "The output contains sensitive data (API keys, passwords, PII). "
        "Redact it before publishing."
    ),
    FailureType.INJECTION_VULNERABILITY: (
        "The output contains patterns that enable prompt injection. "
        "Sanitize by escaping or removing the vulnerable pattern."
    ),
    FailureType.UNCERTAIN: (
        "The verifier cannot determine if this is correct. Escalate to "
        "human review with the specific concern."
    ),
}


@dataclass(frozen=True)
class FailureDiagnosis:
    """A single diagnosed failure with repair guidance.

    Attributes:
        failure_type: Classified failure category.
        location: Where in the output the failure occurs (line number,
            section name, or tool call index).
        evidence: Specific quote or description proving the failure.
        repair_strategy: Actionable repair instruction.
        severity: How critical this failure is (0-1).
    """

    failure_type: FailureType
    location: str
    evidence: str
    repair_strategy: str
    severity: float = 0.5


@dataclass
class VerificationResult:
    """Result of a MUSE-style structured verification pass.

    Attributes:
        passed: Whether the output passes all checks.
        diagnoses: List of diagnosed failures (empty if passed).
        repair_budget_remaining: How many repair attempts remain (K budget).
        content_fingerprint: Hash of the output for loop detection.
        recommended_action: "accept" | "repair" | "escalate"
    """

    passed: bool
    diagnoses: list[FailureDiagnosis] = field(default_factory=list)
    repair_budget_remaining: int = 3  # K=3 optimal from MUSE
    content_fingerprint: str = ""
    recommended_action: str = "accept"

    @property
    def critical_failures(self) -> list[FailureDiagnosis]:
        """Failures with severity >= 0.7."""
        return [d for d in self.diagnoses if d.severity >= 0.7]

    @property
    def should_repair(self) -> bool:
        return self.recommended_action == "repair" and self.repair_budget_remaining > 0

    @property
    def should_escalate(self) -> bool:
        return self.recommended_action == "escalate"


@dataclass
class FailureTaxonomyVerifier:
    """MUSE-style structured failure classifier for Lyra's verification panel.

    Usage::

        verifier = FailureTaxonomyVerifier()
        result = verifier.verify(
            agent_output=code,
            task_description="Implement a caching layer",
            previous_diagnoses=[],  # Empty on first pass
        )
        if result.should_repair:
            # Send repair_strategy back to agent
            for diagnosis in result.diagnoses:
                agent.retry_with_guidance(diagnosis.repair_strategy)
    """

    # MUSE optimal repair budget (K=3)
    MAX_REPAIR_BUDGET: int = 3

    # Fingerprints of outputs that have been seen before (loop detection)
    _seen_fingerprints: set[str] = field(default_factory=set)
    _repair_count: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def verify(
        self,
        agent_output: str,
        task_description: str,
        previous_diagnoses: list[FailureDiagnosis] | None = None,
        sources: list[str] | None = None,
    ) -> VerificationResult:
        """Verify agent output against the structured failure taxonomy.

        Args:
            agent_output: The agent's output to verify.
            task_description: What the agent was asked to do.
            previous_diagnoses: Diagnoses from prior repair attempts (for
                tracking repair budget).
            sources: Optional list of reference/source texts for
                hallucination detection.

        Returns:
            VerificationResult with pass/fail, diagnoses, and repair guidance.
        """
        fingerprint = self._compute_fingerprint(agent_output)

        # Loop detection: if we've seen this exact output before, stop repairing
        if fingerprint in self._seen_fingerprints:
            return VerificationResult(
                passed=False,
                diagnoses=previous_diagnoses or [],
                repair_budget_remaining=0,
                content_fingerprint=fingerprint,
                recommended_action="escalate",
            )

        self._seen_fingerprints.add(fingerprint)

        # Compute repair budget
        prev_count = len(previous_diagnoses) if previous_diagnoses else 0
        budget = max(0, self.MAX_REPAIR_BUDGET - prev_count)

        # Classify failures
        diagnoses = self._classify_failures(
            agent_output, task_description, sources or []
        )

        if not diagnoses:
            return VerificationResult(
                passed=True,
                diagnoses=[],
                repair_budget_remaining=budget,
                content_fingerprint=fingerprint,
                recommended_action="accept",
            )

        # Determine action
        has_critical = any(d.severity >= 0.7 for d in diagnoses)

        if budget <= 0:
            action = "escalate"
        elif has_critical:
            action = "repair"
        else:
            action = "repair" if budget > 0 else "accept"

        return VerificationResult(
            passed=False,
            diagnoses=diagnoses,
            repair_budget_remaining=budget - 1 if action == "repair" else budget,
            content_fingerprint=fingerprint,
            recommended_action=action,
        )

    def reset(self) -> None:
        """Reset loop detection state between sessions."""
        self._seen_fingerprints.clear()
        self._repair_count = 0

    # ------------------------------------------------------------------
    # Failure classification
    # ------------------------------------------------------------------

    def _classify_failures(
        self,
        output: str,
        task: str,
        sources: list[str],
    ) -> list[FailureDiagnosis]:
        """Classify failures in output using heuristic detection.

        In production, this should be replaced with an LLM call that
        classifies failures according to the taxonomy. The heuristics
        below provide fast pre-filtering for common patterns.
        """
        diagnoses: list[FailureDiagnosis] = []

        # 1. Structural error: check for common format issues
        if self._detect_structural_error(output):
            diagnoses.append(FailureDiagnosis(
                failure_type=FailureType.STRUCTURAL_ERROR,
                location="output",
                evidence="Malformed or incomplete output structure",
                repair_strategy=REPAIR_STRATEGIES[FailureType.STRUCTURAL_ERROR],
                severity=0.6,
            ))

        # 2. Contradiction: check for self-contradicting statements
        contradictions = self._detect_contradictions(output)
        for loc, evidence in contradictions:
            diagnoses.append(FailureDiagnosis(
                failure_type=FailureType.CONTRADICTION,
                location=loc,
                evidence=evidence,
                repair_strategy=REPAIR_STRATEGIES[FailureType.CONTRADICTION],
                severity=0.8,
            ))

        # 3. Hallucination: check claims against sources
        if sources:
            hallucinations = self._detect_hallucinations(output, sources)
            for loc, evidence in hallucinations:
                diagnoses.append(FailureDiagnosis(
                    failure_type=FailureType.HALLUCINATION,
                    location=loc,
                    evidence=evidence,
                    repair_strategy=REPAIR_STRATEGIES[FailureType.HALLUCINATION],
                    severity=0.9,
                ))

        # 4. Omission: check if task requirements are addressed
        omissions = self._detect_omissions(output, task)
        for loc, evidence in omissions:
            diagnoses.append(FailureDiagnosis(
                failure_type=FailureType.OMISSION,
                location=loc,
                evidence=evidence,
                repair_strategy=REPAIR_STRATEGIES[FailureType.OMISSION],
                severity=0.7,
            ))

        # 5. Over-generalization: check for absolute claims without evidence
        if self._detect_over_generalization(output):
            diagnoses.append(FailureDiagnosis(
                failure_type=FailureType.OVER_GENERALIZATION,
                location="output",
                evidence="Contains absolute claims without supporting evidence",
                repair_strategy=REPAIR_STRATEGIES[FailureType.OVER_GENERALIZATION],
                severity=0.4,
            ))

        # 6. Data leak: check for secrets in output
        if self._detect_data_leak(output):
            diagnoses.append(FailureDiagnosis(
                failure_type=FailureType.DATA_LEAK,
                location="output",
                evidence="Output may contain sensitive data",
                repair_strategy=REPAIR_STRATEGIES[FailureType.DATA_LEAK],
                severity=0.95,
            ))

        return diagnoses

    # ------------------------------------------------------------------
    # Heuristic detectors (fast pre-filters)
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_structural_error(output: str) -> bool:
        """Detect common structural errors."""
        # Unclosed code blocks
        if output.count("```") % 2 != 0:
            return True
        # Truncated output (ends mid-sentence without punctuation)
        if len(output) > 100 and output.rstrip()[-1] not in ".!?\n)}]\"'":
            return True
        return False

    @staticmethod
    def _detect_contradictions(output: str) -> list[tuple[str, str]]:
        """Detect self-contradictory statements. Simple heuristic."""
        contradictions = []
        lines = output.split("\n")

        # Check for "X is true" and "X is false" patterns
        positive = set()
        negative = set()
        for i, line in enumerate(lines):
            low = line.lower()
            if " is " in low or " are " in low:
                positive.add(low)
            if "not " in low or "never " in low or "no " in low:
                negative.add(low)

        # Crude check: if same subject appears in both sets
        for p in positive:
            p_terms = set(p.split())
            for n in negative:
                n_terms = set(n.split())
                overlap = p_terms & n_terms
                if len(overlap) > 3:  # Significant overlap = possible contradiction
                    contradictions.append(("output", f"Possible contradiction: '{p[:80]}' vs '{n[:80]}'"))

        return contradictions[:3]  # Limit to top 3

    @staticmethod
    def _detect_hallucinations(
        output: str, sources: list[str]
    ) -> list[tuple[str, str]]:
        """Detect claims not supported by sources. Simple heuristic."""
        hallucinations = []
        source_text = " ".join(sources).lower()

        # Find claims that look like facts (contain numbers, percentages, names)
        import re
        fact_patterns = re.findall(
            r'(\d+(?:\.\d+)?%|\d+ (?:times|seconds|minutes|hours|days|weeks|cases|users|requests)[^.]*\.)',
            output,
        )

        for fact in fact_patterns[:5]:
            # Check if the fact (or its key numbers) appears in sources
            numbers = re.findall(r'\d+(?:\.\d+)?', fact)
            found = any(num in source_text for num in numbers)
            if not found:
                hallucinations.append(("output", f"Claim not found in sources: '{fact[:100]}'"))

        return hallucinations[:3]

    @staticmethod
    def _detect_omissions(
        output: str, task: str
    ) -> list[tuple[str, str]]:
        """Detect task requirements not addressed in output. Simple heuristic."""
        omissions = []
        task_lower = task.lower()
        output_lower = output.lower()

        # Check for key requirement words that appear in task but not output
        key_terms = ["implement", "test", "document", "deploy", "review",
                     "analyze", "fix", "build", "optimize", "migrate"]
        for term in key_terms:
            if term in task_lower and term not in output_lower:
                omissions.append(("task", f"Required action '{term}' not addressed in output"))

        return omissions[:3]

    @staticmethod
    def _detect_over_generalization(output: str) -> bool:
        """Detect over-generalized claims."""
        absolute_phrases = [
            "always", "never", "every time", "all cases",
            "guaranteed", "100%", "completely", "perfectly",
        ]
        return any(phrase in output.lower() for phrase in absolute_phrases)

    @staticmethod
    def _detect_data_leak(output: str) -> bool:
        """Detect potential secret leakage."""
        leak_patterns = [
            "sk-", "api_key", "api_secret", "password",
            "BEGIN RSA PRIVATE KEY", "BEGIN OPENSSH PRIVATE KEY",
            "token =", "secret =",
        ]
        return any(pattern in output for pattern in leak_patterns)

    @staticmethod
    def _compute_fingerprint(content: str) -> str:
        """Compute a content fingerprint for loop detection."""
        # Hash first and last 200 chars (robust to small variations)
        head = content[:200]
        tail = content[-200:] if len(content) > 200 else ""
        return hashlib.sha256((head + tail).encode()).hexdigest()[:16]
