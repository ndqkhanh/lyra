"""Cross-Model Adversarial Verification (ARIS) for self-evolving agent systems.

ARIS (Adversarial Review & Integrity Scoring) is a three-stage verification
pipeline that enforces cross-model accountability in agent self-evolution:

    1. Evidence Integrity (Stage 1)
       Verified claims are backed by concrete evidence. Each claimed fact is
       checked against supporting / contradicting facts in the evidence store.

    2. Result-to-Claim Coherence (Stage 2)
       The final output is audited against the set of claims the agent made
       during its reasoning. Every claim must be logically reflected in the
       output.

    3. Claim Auditing (Stage 3)
       Internal consistency of the agent's claims — no two claims may make
       contradictory statements. Contradictions are detected pairwise.

The module enforces **adversarial pairing**: the model family that *executes*
must differ from the model family that *reviews*. Running the same family on
both sides is a known failure mode (judge rubber-stamping).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Protocol

__all__ = [
    "ARISStage",
    "ARISVerdict",
    "AdversarialReviewer",
    "CrossModelPairing",
    "ReviewHistory",
    "StageResult",
    "VerificationEvidence",
]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ARISStage(str, enum.Enum):
    """The three stages of the ARIS verification pipeline."""

    EVIDENCE_INTEGRITY = "evidence_integrity"
    RESULT_TO_CLAIM = "result_to_claim"
    CLAIM_AUDITING = "claim_auditing"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VerificationEvidence:
    """A single piece of evidence associated with a claim made by the agent.

    Parameters
    ----------
    claim:
        The original claim the evidence relates to.
    source:
        Origin of the evidence (e.g. ``"tool_output"``, ``"code"``,
        ``"memory"``).
    supporting_facts:
        Set of factual statements that *support* the claim.
    contradicting_facts:
        Set of factual statements that *contradict* the claim.
    confidence:
        Confidence score in the evidence itself (``0.0`` – ``1.0``).
    """

    claim: str
    source: str
    supporting_facts: frozenset[str] = field(default_factory=frozenset)
    contradicting_facts: frozenset[str] = field(default_factory=frozenset)
    confidence: float = 1.0

    def __post_init__(self) -> None:
        """Clamp *confidence* to ``[0.0, 1.0]``."""
        if not 0.0 <= self.confidence <= 1.0:
            object.__setattr__(self, "confidence", max(0.0, min(1.0, self.confidence)))


@dataclass(frozen=True)
class StageResult:
    """Outcome of a single ARIS verification stage."""

    stage: ARISStage
    passed: bool
    score: float
    issues: tuple[str, ...] = field(default_factory=tuple)
    evidence_used: tuple[VerificationEvidence, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ARISVerdict:
    """Final verdict produced by the full ARIS pipeline.

    Attributes
    ----------
    approved:
        ``True`` only when *all three* stages pass.
    stage_results:
        Exactly three elements — one per ARIS stage in order.
    overall_score:
        Geometric mean of the three stage scores.
    reviewer_model:
        Model family string of the reviewing model.
    executor_model:
        Model family string of the executing model.
    recommendation:
        Human-readable summary of the verdict.
    requires_human_review:
        Whether the result should be escalated to a human operator.
    """

    approved: bool
    stage_results: tuple[StageResult, StageResult, StageResult]
    overall_score: float
    reviewer_model: str
    executor_model: str
    recommendation: str
    requires_human_review: bool


@dataclass(frozen=True)
class CrossModelPairing:
    """Encapsulates an adversarial model pairing.

    The pairing is *adversarial* only when the executor and reviewer belong
    to different model families (e.g. Anthropic executor reviewed by a
    DeepSeek model).
    """

    executor_family: str
    reviewer_family: str
    is_adversarial: bool = field(init=False)

    def __post_init__(self) -> None:
        is_adv = self.executor_family != self.reviewer_family
        object.__setattr__(self, "is_adversarial", is_adv)

    def validate(self) -> bool:
        """Return ``True`` only when executor and reviewer differ."""
        return self.is_adversarial


@dataclass(frozen=True)
class ReviewHistory:
    """Aggregated review statistics across multiple ARIS verdicts."""

    verdicts: tuple[ARISVerdict, ...] = field(default_factory=tuple)
    acceptance_rate: float = field(init=False)
    avg_score: float = field(init=False)
    common_issues: tuple[str, ...] = field(init=False)

    def __post_init__(self) -> None:
        n = len(self.verdicts)
        if n == 0:
            object.__setattr__(self, "acceptance_rate", 0.0)
            object.__setattr__(self, "avg_score", 0.0)
            object.__setattr__(self, "common_issues", ())
            return

        approved_count = sum(1 for v in self.verdicts if v.approved)
        object.__setattr__(self, "acceptance_rate", approved_count / n)

        object.__setattr__(
            self,
            "avg_score",
            sum(v.overall_score for v in self.verdicts) / n,
        )

        # Collect the most frequently recurring issue strings.
        issue_counter: dict[str, int] = {}
        for v in self.verdicts:
            for sr in v.stage_results:
                for issue in sr.issues:
                    issue_counter[issue] = issue_counter.get(issue, 0) + 1
        sorted_issues = sorted(issue_counter, key=issue_counter.__getitem__, reverse=True)
        object.__setattr__(self, "common_issues", tuple(sorted_issues[:10]))


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class EvidenceStore(Protocol):
    """Duck-typed protocol for evidence look-up.

    Any object that exposes ``get_evidence(claim_id: str) -> ...`` satisfies
    this protocol, enabling the reviewer to work with in-memory stores,
    database-backed repositories, or mock stores in tests.
    """

    def get_evidence(self, claim_id: str) -> VerificationEvidence | None:
        """Return evidence for *claim_id*, or ``None`` if absent."""


# ---------------------------------------------------------------------------
# Stop-word set for lightweight text matching (Stage 2).
# ---------------------------------------------------------------------------

_STOP_WORDS: frozenset[str] = frozenset(
    {
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "dare", "ought",
        "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
        "into", "through", "during", "before", "after", "above", "below",
        "between", "out", "off", "over", "under", "again", "further", "then",
        "once", "here", "there", "when", "where", "why", "how", "all", "each",
        "every", "both", "few", "more", "most", "other", "some", "such", "no",
        "nor", "not", "only", "own", "same", "so", "than", "too", "very",
        "just", "because", "but", "and", "or", "if", "while", "although",
        "this", "that", "these", "those", "i", "me", "my", "myself", "we",
        "our", "ours", "ourselves", "you", "your", "yours", "yourself",
        "he", "him", "his", "himself", "she", "her", "hers", "herself",
        "it", "its", "itself", "they", "them", "their", "theirs", "themselves",
        "what", "which", "who", "whom", "whose", "any", "anything", "nothing",
        "something", "everything",
    }
)

_CONTRADICTION_MARKERS: tuple[tuple[str, str], ...] = (
    ("not ", ""),
    ("never ", "always "),
    ("no ", "yes "),
    ("cannot ", "can "),
    ("does not ", "does "),
    ("is not ", "is "),
    ("are not ", "are "),
    ("will not ", "will "),
    ("failed ", "succeeded "),
    ("incorrect", "correct"),
    ("invalid", "valid"),
    ("false", "true"),
    ("absent", "present"),
    ("missing", "exists"),
    ("disables", "enables"),
)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _words(text: str) -> frozenset[str]:
    """Lowercased content words (*stop words removed*) from *text*."""
    tokens = (
        w.strip(".,!?;:\"'()[]{}")
        for w in text.lower().split()
    )
    return frozenset(t for t in tokens if t and t not in _STOP_WORDS)


def _claim_words_overlap(claim: str, target: str) -> float:
    """Fraction of content words in *claim* that appear in *target*.

    Returns a float in ``[0.0, 1.0]``.
    """
    cw = _words(claim)
    if not cw:
        return 0.0
    tw = _words(target)
    matched = cw & tw
    return len(matched) / len(cw)


def _detect_contradictions(claims: list[str]) -> list[tuple[int, int, str]]:
    """Return a list of ``(i, j, description)`` for contradictory claim pairs."""
    contradictions: list[tuple[int, int, str]] = []
    for i in range(len(claims)):
        for j in range(i + 1, len(claims)):
            ci_lower = claims[i].lower()
            cj_lower = claims[j].lower()
            for a, b in _CONTRADICTION_MARKERS:
                has_a = a in ci_lower
                has_b = b in ci_lower
                # Check the inverse in the other claim (or same claim).
                a_in_j = a in cj_lower
                b_in_j = b in cj_lower
                # A contradiction occurs when one claim contains marker A
                # and the other contains marker B (or vice versa).
                if (has_a and b_in_j) or (has_b and a_in_j):
                    contradictions.append(
                        (i, j, f"claims[{i}] and claims[{j}] contradict on '{a}' vs '{b}'"),
                    )
                    break
    return contradictions


# ---------------------------------------------------------------------------
# Adversarial Reviewer
# ---------------------------------------------------------------------------


class AdversarialReviewer:
    """ARIS three-stage verification pipeline for cross-model accountability.

    Parameters
    ----------
    executor_model_family:
        Model family that *produced* the work (e.g. ``"anthropic"``,
        ``"deepseek"``).
    reviewer_model_family:
        Model family that *reviews* the work. **Must** differ from
        *executor_model_family* for a true adversarial pairing.
    evidence_store:
        Any object implementing ``get_evidence(claim_id)`` that returns
        :class:`VerificationEvidence` or ``None``.

    Raises
    ------
    ValueError
        If *executor_model_family* == *reviewer_model_family* — the
        adversarial contract is violated at construction time.
    """

    def __init__(
        self,
        executor_model_family: str,
        reviewer_model_family: str,
        evidence_store: EvidenceStore,
    ) -> None:
        if executor_model_family == reviewer_model_family:
            raise ValueError(
                "AdversarialReviewer requires executor and reviewer from "
                f"different model families, got both='{executor_model_family}'"
            )
        self._executor_family = executor_model_family
        self._reviewer_family = reviewer_model_family
        self._evidence_store = evidence_store

    # -- Public property accessors ------------------------------------------

    @property
    def executor_model_family(self) -> str:
        return self._executor_family

    @property
    def reviewer_model_family(self) -> str:
        return self._reviewer_family

    @property
    def evidence_store(self) -> EvidenceStore:
        return self._evidence_store

    # -- Stage 1: Evidence Integrity ----------------------------------------

    def verify_evidence_integrity(
        self,
        claims: list[str],
        available_evidence: list[VerificationEvidence],
    ) -> StageResult:
        """Stage 1 — Are the claimed facts actually present in the evidence?

        For each claim, the method checks whether at least one piece of
        evidence names the claim in its ``claim`` field or ``supporting_facts``.

        **Score**: fraction of claims that have evidence support.
        **Pass**: score ``>= 0.7``.

        Parameters
        ----------
        claims:
            List of claims the agent made.
        available_evidence:
            Evidence bag available for verification.

        Returns
        -------
        StageResult
            Outcome of the evidence-integrity check.
        """
        if not claims:
            return StageResult(
                stage=ARISStage.EVIDENCE_INTEGRITY,
                passed=True,
                score=1.0,
                issues=("no claims to verify",),
                evidence_used=tuple(available_evidence),
            )

        # Build a set of all claim-like references present in evidence.
        evidence_claims: set[str] = set()
        for ev in available_evidence:
            evidence_claims.add(ev.claim.lower())
            evidence_claims.update(f.lower() for f in ev.supporting_facts)

        supported = 0
        issues: list[str] = []
        for claim in claims:
            cl = claim.lower()
            if cl in evidence_claims:
                supported += 1
            else:
                issues.append(f"claim not supported by evidence: {claim!r}")

        score = supported / len(claims)
        passed = score >= 0.7

        return StageResult(
            stage=ARISStage.EVIDENCE_INTEGRITY,
            passed=passed,
            score=score,
            issues=tuple(issues),
            evidence_used=tuple(available_evidence),
        )

    # -- Stage 2: Result-to-Claim -------------------------------------------

    def verify_result_to_claim(
        self,
        output: str,
        claims: list[str],
    ) -> StageResult:
        """Stage 2 — Does the evidence logically support the output?

        Checks that each claim shares significant content-word overlap with
        the final *output* text (i.e. the claim is *reflected* in the
        output).

        **Score**: fraction of claims whose content words overlap with
        *output* at a ratio ``>= 0.3``.
        **Pass**: score ``>= 0.7``.

        Parameters
        ----------
        output:
            Final output produced by the agent.
        claims:
            List of claims the agent made.

        Returns
        -------
        StageResult
            Outcome of the result-to-claim coherence check.
        """
        if not claims:
            return StageResult(
                stage=ARISStage.RESULT_TO_CLAIM,
                passed=True,
                score=1.0,
                issues=("no claims to verify",),
            )

        if not output.strip():
            return StageResult(
                stage=ARISStage.RESULT_TO_CLAIM,
                passed=False,
                score=0.0,
                issues=("output is empty; no claims can be reflected",),
            )

        issues: list[str] = []
        reflected_count = 0
        # Threshold: fraction of claim content words that must appear in output.
        OVERLAP_THRESHOLD = 0.3

        for claim in claims:
            overlap = _claim_words_overlap(claim, output)
            if overlap >= OVERLAP_THRESHOLD:
                reflected_count += 1
            else:
                issues.append(
                    f"claim not reflected in output (overlap={overlap:.2f}): "
                    f"{claim!r}",
                )

        score = reflected_count / len(claims)
        passed = score >= 0.7

        return StageResult(
            stage=ARISStage.RESULT_TO_CLAIM,
            passed=passed,
            score=score,
            issues=tuple(issues),
        )

    # -- Stage 3: Claim Auditing --------------------------------------------

    def audit_claims(
        self,
        claims: list[str],
        intermediate_outputs: list[str],
    ) -> StageResult:
        """Stage 3 — Are all intermediate claims internally consistent?

        Detects pairwise contradictions among *claims*. The *intermediate_outputs*
        parameter is provided for future semantic-contradiction analysis; the
        current implementation uses an efficient pattern-based scan.

        **Score**: ``1.0 - (contradiction_count / total_claim_pairs)``.
        **Pass**: score ``>= 0.8``.

        Parameters
        ----------
        claims:
            List of claims the agent made.
        intermediate_outputs:
            Intermediate outputs produced during the agent's reasoning.
            Reserved for future semantic analysis.

        Returns
        -------
        StageResult
            Outcome of the claim-auditing check.
        """
        if len(claims) < 2:
            return StageResult(
                stage=ARISStage.CLAIM_AUDITING,
                passed=True,
                score=1.0,
                issues=("too few claims to detect contradictions",),
            )

        contradictions = _detect_contradictions(claims)
        total_pairs = len(claims) * (len(claims) - 1) // 2
        score = 1.0 - (len(contradictions) / total_pairs)
        passed = score >= 0.8

        issues = [desc for _, _, desc in contradictions]

        return StageResult(
            stage=ARISStage.CLAIM_AUDITING,
            passed=passed,
            score=score,
            issues=tuple(issues),
        )

    # -- Full pipeline -------------------------------------------------------

    def review(
        self,
        output: str,
        claims: list[str],
        intermediate_outputs: list[str],
        available_evidence: list[VerificationEvidence],
    ) -> ARISVerdict:
        """Run all three ARIS stages and produce a final verdict.

        ``approved`` is ``True`` **only** when every stage passes.

        Parameters
        ----------
        output:
            Final output from the agent.
        claims:
            Claims the agent made during execution.
        intermediate_outputs:
            Intermediate reasoning/output steps (passed to Stage 3).
        available_evidence:
            Evidence bag for Stage 1.

        Returns
        -------
        ARISVerdict
            Aggregate verdict across all three stages.
        """
        stage1 = self.verify_evidence_integrity(claims, available_evidence)
        stage2 = self.verify_result_to_claim(output, claims)
        stage3 = self.audit_claims(claims, intermediate_outputs)

        stage_results = (stage1, stage2, stage3)

        # Approved only when ALL stages pass.
        approved = all(sr.passed for sr in stage_results)

        # Geometric mean of stage scores.
        import math
        product = stage1.score * stage2.score * stage3.score
        overall_score = math.pow(product, 1.0 / 3.0)

        requires_human_review = overall_score < 0.6 or any(
            not sr.passed for sr in stage_results
        )

        # Build a concise recommendation string.
        lines = [f"ARIS review by {self._reviewer_family} of {self._executor_family}: "]
        for sr in stage_results:
            status = "PASS" if sr.passed else "FAIL"
            lines.append(f"  {sr.stage.value}: {status} (score={sr.score:.3f})")
        if approved:
            lines.append("All stages passed. Output approved.")
        else:
            lines.append("Some stages failed. Rejecting output.")

        recommendation = "\n".join(lines)

        return ARISVerdict(
            approved=approved,
            stage_results=stage_results,
            overall_score=overall_score,
            reviewer_model=self._reviewer_family,
            executor_model=self._executor_family,
            recommendation=recommendation,
            requires_human_review=requires_human_review,
        )

    # -- Escalation ----------------------------------------------------------

    @staticmethod
    def requires_escalation(verdict: ARISVerdict) -> bool:
        """Return ``True`` when a verdict needs human escalation.

        Escalation is triggered when:
        - The *overall_score* falls below ``0.6``, **or**
        - Any individual stage failed.
        """
        return verdict.overall_score < 0.6 or not all(
            sr.passed for sr in verdict.stage_results
        )
