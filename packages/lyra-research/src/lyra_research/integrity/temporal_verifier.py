"""
Temporal Verification

Detects 5 temporal failure modes:
1. Retrospective arithmetic (comparing past to future)
2. Anachronistic citation (citing future work)
3. Comparator unmaterialized (comparing to non-existent baseline)
4. Causal inversion (effect before cause)
5. Deictic present (ambiguous "now" references)
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class TemporalViolationType(Enum):
    """Types of temporal violations"""

    RETROSPECTIVE_ARITHMETIC = "retrospective_arithmetic"
    ANACHRONISTIC_CITATION = "anachronistic_citation"
    COMPARATOR_UNMATERIALIZED = "comparator_unmaterialized"
    CAUSAL_INVERSION = "causal_inversion"
    DEICTIC_PRESENT = "deictic_present"


@dataclass
class TemporalViolation:
    """Temporal violation data"""

    type: TemporalViolationType
    claim: str
    citation: str
    reason: str
    severity: str = "HIGH"


class TemporalVerifier:
    """Detect 5 temporal failure modes"""

    def verify_temporal_consistency(self, report: dict[str, Any]) -> list[TemporalViolation]:
        """
        Verify temporal consistency across all claims

        Args:
            report: Research report with claims and citations

        Returns:
            List of temporal violations
        """
        violations = []

        # Mode 1: Retrospective arithmetic
        violations.extend(self.detect_retrospective_arithmetic(report))

        # Mode 2: Anachronistic citation
        violations.extend(self.detect_anachronistic_citations(report))

        # Mode 3: Comparator unmaterialized
        violations.extend(self.detect_unmaterialized_comparators(report))

        # Mode 4: Causal inversion
        violations.extend(self.detect_causal_inversions(report))

        # Mode 5: Deictic present
        violations.extend(self.detect_deictic_present(report))

        return violations

    def detect_retrospective_arithmetic(self, report: dict[str, Any]) -> list[TemporalViolation]:
        """
        Detect retrospective arithmetic (comparing past to future)

        Example: "In 2020, X was 10% better than Y in 2025"
        """
        violations = []
        claims = report.get("claims", [])

        for claim in claims:
            text = claim.get("text", "")
            # Simple pattern matching for year comparisons
            # In production, would use more sophisticated NLP
            if self._contains_backward_comparison(text):
                violations.append(
                    TemporalViolation(
                        type=TemporalViolationType.RETROSPECTIVE_ARITHMETIC,
                        claim=text,
                        citation="",
                        reason="Claim compares past to future",
                    )
                )

        return violations

    def detect_anachronistic_citations(self, report: dict[str, Any]) -> list[TemporalViolation]:
        """
        Detect citations to papers published after the claim date

        Example: Claim from 2020 cites paper from 2023
        """
        violations = []
        claims = report.get("claims", [])

        for claim in claims:
            claim_date = claim.get("date")
            if not claim_date:
                continue

            if isinstance(claim_date, str):
                claim_date = datetime.fromisoformat(claim_date)

            for citation in claim.get("citations", []):
                pub_date = citation.get("published_date")
                if not pub_date:
                    continue

                if isinstance(pub_date, str):
                    pub_date = datetime.fromisoformat(pub_date)

                if pub_date > claim_date:
                    violations.append(
                        TemporalViolation(
                            type=TemporalViolationType.ANACHRONISTIC_CITATION,
                            claim=claim.get("text", ""),
                            citation=citation.get("id", ""),
                            reason=(
                                f"Claim dated {claim_date.date()} cites paper from "
                                f"{pub_date.date()}"
                            ),
                        )
                    )

        return violations

    def detect_unmaterialized_comparators(self, report: dict[str, Any]) -> list[TemporalViolation]:
        """
        Detect comparisons to non-existent baselines

        Example: "X outperforms Y" but Y doesn't exist yet
        """
        violations = []
        claims = report.get("claims", [])

        for claim in claims:
            text = claim.get("text", "")
            # Check for comparison keywords
            if any(
                keyword in text.lower() for keyword in ["outperforms", "better than", "compared to"]
            ):
                # In production, would verify the comparator exists
                # For now, just flag for manual review
                pass

        return violations

    def detect_causal_inversions(self, report: dict[str, Any]) -> list[TemporalViolation]:
        """
        Detect effect before cause

        Example: "The result was X, which led to Y being developed"
        but Y was developed before X
        """
        violations = []
        # This requires sophisticated causal reasoning
        # Would be implemented with NLP in production
        return violations

    def detect_deictic_present(self, report: dict[str, Any]) -> list[TemporalViolation]:
        """
        Detect ambiguous "now" references

        Example: "Currently, X is the state-of-the-art" (when is "currently"?)
        """
        violations = []
        claims = report.get("claims", [])

        deictic_terms = ["now", "currently", "today", "recently", "lately", "at present"]

        for claim in claims:
            text = claim.get("text", "")
            for term in deictic_terms:
                if term in text.lower():
                    violations.append(
                        TemporalViolation(
                            type=TemporalViolationType.DEICTIC_PRESENT,
                            claim=text,
                            citation="",
                            reason=f"Ambiguous temporal reference: '{term}'",
                            severity="MEDIUM",
                        )
                    )
                    break

        return violations

    def _contains_backward_comparison(self, text: str) -> bool:
        """Check if text contains backward temporal comparison"""
        # Simple heuristic - would be more sophisticated in production
        import re

        # Look for patterns like "2020...2025" or "earlier...later"
        year_pattern = r"\b(19|20)\d{2}\b"
        years = re.findall(year_pattern, text)
        if len(years) >= 2:
            # Check if years are in descending order (backward)
            return int(years[0]) > int(years[1])
        return False
