from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from lyra_adversarial_review.review_config import ReviewConfig


class ClaimStatus(Enum):
    UNVERIFIED = "unverified"
    INTEGRITY_PASS = "integrity_pass"
    INTEGRITY_FAIL = "integrity_fail"
    MAPPING_PASS = "mapping_pass"
    MAPPING_FAIL = "mapping_fail"
    AUDIT_PASS = "audit_pass"
    AUDIT_FAIL = "audit_fail"
    VERIFIED = "verified"
    REJECTED = "rejected"


class VerificationStage(Enum):
    INTEGRITY = "integrity"
    MAPPING = "mapping"
    AUDITING = "auditing"


@dataclass(frozen=True)
class Claim:
    claim_id: str
    text: str
    source: str
    confidence: float = 0.0
    status: ClaimStatus = ClaimStatus.UNVERIFIED


@dataclass(frozen=True)
class StageResult:
    stage: VerificationStage
    passed: bool
    score: float
    evidence: str
    issues: Sequence[str] = field(default_factory=list)


@dataclass(frozen=True)
class VerificationResult:
    claim: Claim
    stages: Sequence[StageResult]
    overall_pass: bool
    confidence: float


@dataclass(frozen=True)
class VerificationReport:
    total_claims: int = 0
    verified: int = 0
    rejected: int = 0
    avg_confidence: float = 0.0
    stage_breakdown: dict[str, dict[str, Any]] = field(default_factory=dict)


class ClaimVerifier:
    """ARIS 3-stage claim verification pipeline following 2605.03042."""

    def __init__(self, config: ReviewConfig | None = None) -> None:
        self._config = config or ReviewConfig()
        self._config.validate()

    async def check_integrity(self, claim: Claim) -> StageResult:
        score, issues = await self._evaluate_integrity(claim)
        passed = score >= self._config.min_confidence_threshold
        return StageResult(
            stage=VerificationStage.INTEGRITY,
            passed=passed,
            score=round(score, 4),
            evidence=f"Integrity score: {score:.4f} (threshold: {self._config.min_confidence_threshold})",
            issues=issues,
        )

    async def map_results(self, claim: Claim, raw_output: str) -> StageResult:
        score, issues = await self._evaluate_mapping(claim, raw_output)
        passed = score >= self._config.min_confidence_threshold
        return StageResult(
            stage=VerificationStage.MAPPING,
            passed=passed,
            score=round(score, 4),
            evidence=f"Mapping score: {score:.4f}",
            issues=issues,
        )

    async def audit_claim(self, claim: Claim, cross_references: Sequence[str]) -> StageResult:
        score, issues = await self._evaluate_audit(claim, cross_references)
        passed = score >= self._config.min_confidence_threshold
        return StageResult(
            stage=VerificationStage.AUDITING,
            passed=passed,
            score=round(score, 4),
            evidence=f"Audit score: {score:.4f} across {len(cross_references)} cross-references",
            issues=issues,
        )

    async def verify(
        self,
        claim: Claim,
        raw_output: str,
        cross_refs: Sequence[str] | None = None,
    ) -> VerificationResult:
        integrity = await self.check_integrity(claim)
        if not integrity.passed:
            return VerificationResult(
                claim=claim,
                stages=[integrity],
                overall_pass=False,
                confidence=integrity.score,
            )

        mapping = await self.map_results(claim, raw_output)
        if not mapping.passed:
            return VerificationResult(
                claim=claim,
                stages=[integrity, mapping],
                overall_pass=False,
                confidence=mapping.score,
            )

        cross_refs_list = list(cross_refs) if cross_refs else []
        auditing = await self.audit_claim(claim, cross_refs_list)
        all_passed = auditing.passed
        overall_confidence = (integrity.score + mapping.score + auditing.score) / 3.0

        return VerificationResult(
            claim=claim,
            stages=[integrity, mapping, auditing],
            overall_pass=all_passed,
            confidence=round(overall_confidence, 4),
        )

    def generate_report(
        self,
        results: Sequence[VerificationResult],
    ) -> VerificationReport:
        total = len(results)
        verified = sum(1 for r in results if r.overall_pass)
        rejected = total - verified
        avg_conf = sum(r.confidence for r in results) / max(total, 1)

        stage_breakdown: dict[str, dict[str, Any]] = {}
        for result in results:
            for stage in result.stages:
                key = stage.stage.value
                if key not in stage_breakdown:
                    stage_breakdown[key] = {"pass": 0, "fail": 0, "avg_score": 0.0}
                if stage.passed:
                    stage_breakdown[key]["pass"] += 1
                else:
                    stage_breakdown[key]["fail"] += 1
                stage_breakdown[key]["avg_score"] += stage.score

        for key in stage_breakdown:
            stage_breakdown[key]["avg_score"] = round(
                stage_breakdown[key]["avg_score"] / total, 4
            )

        return VerificationReport(
            total_claims=total,
            verified=verified,
            rejected=rejected,
            avg_confidence=round(avg_conf, 4),
            stage_breakdown=stage_breakdown,
        )

    def create_claim(self, text: str, source: str, confidence: float = 0.0) -> Claim:
        return Claim(
            claim_id=uuid.uuid4().hex[:12],
            text=text,
            source=source,
            confidence=confidence,
        )

    async def _evaluate_integrity(self, claim: Claim) -> tuple[float, list[str]]:
        issues: list[str] = []
        score = 1.0

        word_count = len(claim.text.split())
        if word_count < 3:
            score -= 0.3
            issues.append("Claim too short (fewer than 3 words)")
        if word_count > 500:
            score -= 0.2
            issues.append("Claim excessively long (over 500 words)")

        hedge_words = ["might", "maybe", "perhaps", "possibly", "could", "seems", "appears"]
        hedge_count = sum(1 for w in hedge_words if w in claim.text.lower())
        if hedge_count > 2:
            score -= 0.1 * min(hedge_count, 5)
            issues.append(f"Excessive hedging ({hedge_count} hedge words detected)")

        if claim.confidence < 0.3:
            score -= 0.2
            issues.append("Low claim confidence score")

        if not claim.source:
            score -= 0.3
            issues.append("Missing source attribution")

        return max(0.0, score), issues

    async def _evaluate_mapping(
        self, claim: Claim, raw_output: str
    ) -> tuple[float, list[str]]:
        issues: list[str] = []
        score = 1.0

        claim_keywords = set(claim.text.lower().split())
        output_keywords = set(raw_output.lower().split())

        overlap = len(claim_keywords & output_keywords)
        total_unique = len(claim_keywords | output_keywords)
        if total_unique > 0:
            jaccard = overlap / total_unique
            score *= jaccard
            if jaccard < 0.1:
                issues.append("Minimal keyword overlap between claim and output")
        else:
            score = 0.0
            issues.append("Empty claim and output")

        for sentence_end in [".", "!", "?"]:
            claim_sentences = claim.text.count(sentence_end)
            output_sentences = raw_output.count(sentence_end)
            if claim_sentences > output_sentences * 2:
                score -= 0.1
                issues.append("Claim has disproportionately more sentences than output")

        return max(0.0, score), issues

    async def _evaluate_audit(
        self, claim: Claim, cross_references: Sequence[str]
    ) -> tuple[float, list[str]]:
        issues: list[str] = []
        score = 1.0

        if not cross_references:
            score *= 0.2
            issues.append("No cross-references provided for audit")
            return max(0.0, score), issues

        total_refs = len(cross_references)
        supporting = 0
        contradictory = 0
        claim_keywords = set(claim.text.lower().split())

        for ref in cross_references:
            ref_lower = ref.lower()
            keyword_hits = sum(1 for kw in claim_keywords if kw in ref_lower)
            if keyword_hits >= 2:
                supporting += 1
            elif keyword_hits == 0:
                contradictory += 1

        if total_refs > 0:
            support_ratio = supporting / total_refs
            contrad_ratio = contradictory / total_refs
            score = support_ratio
            score -= contrad_ratio * 0.5

        if contradictory > supporting:
            issues.append(f"More contradictory refs ({contradictory}) than supporting ({supporting})")
        if supporting == 0:
            issues.append("No supporting cross-references found")

        return max(0.0, score), issues
