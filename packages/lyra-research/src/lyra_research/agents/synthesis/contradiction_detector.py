"""
Contradiction detection agent.

Detects contradictions between sources.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from lyra_research.agents.analysis.analysis_base import Analysis
from lyra_research.agents.synthesis.synthesis_base import SynthesisAgent, SynthesisResult


class ContradictionDetectorAgent(SynthesisAgent):
    """
    Detects contradictions between sources.

    Identifies conflicting claims, opposing findings, and inconsistent results.
    """

    def __init__(self, model: str = "claude-opus-4-7") -> None:
        super().__init__(synthesis_type="contradiction", model=model)

    async def synthesize(self, analyses: List[Analysis]) -> SynthesisResult:
        """
        Detect contradictions in analyses.

        Args:
            analyses: List of analysis results (from cross-source synthesis)

        Returns:
            Synthesis result with detected contradictions
        """
        # Extract findings from metadata if available
        all_findings = []
        for analysis in analyses:
            if "grouped_findings" in analysis.metadata:
                # From cross-source synthesis
                for theme_findings in analysis.metadata["grouped_findings"].values():
                    all_findings.extend(theme_findings)
            else:
                all_findings.extend(analysis.findings)

        # Detect contradictions
        contradictions = self._detect_contradictions(all_findings)

        # Calculate confidence based on contradiction detection
        confidence = 0.9 if contradictions else 1.0

        return SynthesisResult(
            synthesis_type=self.synthesis_type,
            findings=[f"{c[0]} contradicts {c[1]}" for c in contradictions],
            metadata={
                "contradictions": contradictions,
                "contradiction_count": len(contradictions),
            },
            confidence=confidence,
            issues_found=len(contradictions),
        )

    def _detect_contradictions(
        self, findings: List[str]
    ) -> List[Tuple[str, str]]:
        """
        Detect contradictions between findings.

        Uses pattern matching to find opposing claims.
        """
        contradictions: List[Tuple[str, str]] = []

        # Patterns for contradictory statements
        positive_patterns = [
            r"(improves?|increases?|enhances?|boosts?|better)",
            r"(outperforms?|superior|exceeds?)",
            r"(achieves?|reaches?|attains?) (?:high|good|excellent)",
        ]

        negative_patterns = [
            r"(degrades?|decreases?|reduces?|worsens?|worse)",
            r"(underperforms?|inferior|fails? to)",
            r"(achieves?|reaches?|attains?) (?:low|poor|bad)",
        ]

        # Check each pair of findings
        for i, finding1 in enumerate(findings):
            for finding2 in findings[i + 1:]:
                if self._are_contradictory(
                    finding1, finding2, positive_patterns, negative_patterns
                ):
                    contradictions.append((finding1, finding2))

        return contradictions[:10]  # Limit to top 10

    def _are_contradictory(
        self,
        finding1: str,
        finding2: str,
        positive_patterns: List[str],
        negative_patterns: List[str],
    ) -> bool:
        """Check if two findings are contradictory."""
        finding1_lower = finding1.lower()
        finding2_lower = finding2.lower()

        # Check if they discuss the same topic (share 3+ words)
        words1 = set(re.findall(r'\b[a-z]{4,}\b', finding1_lower))
        words2 = set(re.findall(r'\b[a-z]{4,}\b', finding2_lower))
        shared_words = words1 & words2

        if len(shared_words) < 3:
            return False  # Different topics

        # Check if one is positive and other is negative
        finding1_positive = any(
            re.search(pattern, finding1_lower) for pattern in positive_patterns
        )
        finding1_negative = any(
            re.search(pattern, finding1_lower) for pattern in negative_patterns
        )

        finding2_positive = any(
            re.search(pattern, finding2_lower) for pattern in positive_patterns
        )
        finding2_negative = any(
            re.search(pattern, finding2_lower) for pattern in negative_patterns
        )

        # Contradiction if one is positive and other is negative
        return (finding1_positive and finding2_negative) or (
            finding1_negative and finding2_positive
        )
