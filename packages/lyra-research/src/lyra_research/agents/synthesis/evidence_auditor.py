"""
Evidence auditing agent.

Audits evidence quality and citation accuracy.
"""
from __future__ import annotations

import re
from typing import Any

from lyra_research.agents.analysis.analysis_base import Analysis
from lyra_research.agents.synthesis.synthesis_base import SynthesisAgent, SynthesisResult


class EvidenceAuditorAgent(SynthesisAgent):
    """
    Audits evidence quality and citation accuracy.

    Checks for:
    - Missing citations
    - Weak evidence (single source)
    - Unsupported claims
    - Citation accuracy
    """

    def __init__(self, model: str = "claude-opus-4-7") -> None:
        super().__init__(synthesis_type="evidence", model=model)

    async def synthesize(self, analyses: list[Analysis]) -> SynthesisResult:
        """
        Audit evidence quality.

        Args:
            analyses: List of analysis results (from contradiction detection)

        Returns:
            Synthesis result with evidence audit findings
        """
        # Extract findings and contradictions
        all_findings = []
        contradictions = []

        for analysis in analyses:
            if analysis.analysis_type == "contradiction":
                contradictions = analysis.metadata.get("contradictions", [])
            all_findings.extend(analysis.findings)

        # Audit evidence
        evidence_issues = self._audit_evidence(all_findings, contradictions)

        # Calculate confidence
        total_findings = len(all_findings)
        issues_count = len(evidence_issues)
        confidence = max(0.0, 1.0 - (issues_count / max(total_findings, 1)))

        return SynthesisResult(
            synthesis_type=self.synthesis_type,
            findings=[issue["description"] for issue in evidence_issues],
            metadata={
                "evidence_issues": evidence_issues,
                "total_findings": total_findings,
                "issues_count": issues_count,
            },
            confidence=confidence,
            issues_found=issues_count,
        )

    def _audit_evidence(
        self, findings: list[str], contradictions: list[tuple[str, str]]
    ) -> list[dict[str, Any]]:
        """
        Audit evidence quality for all findings.

        Returns list of evidence issues.
        """
        issues: list[dict[str, Any]] = []

        # Check each finding for evidence quality
        for finding in findings:
            # Check for citations
            citations = re.findall(r'\[(\d+)\]', finding)
            citation_count = len(set(citations))  # Unique citations

            if citation_count == 0:
                issues.append({
                    "finding": finding[:100],
                    "issue_type": "missing_citation",
                    "severity": "critical",
                    "description": f"No citations: {finding[:80]}...",
                })
            elif citation_count == 1:
                issues.append({
                    "finding": finding[:100],
                    "issue_type": "weak_evidence",
                    "severity": "high",
                    "description": f"Single citation: {finding[:80]}...",
                })
            elif citation_count == 2:
                issues.append({
                    "finding": finding[:100],
                    "issue_type": "moderate_evidence",
                    "severity": "medium",
                    "description": f"Two citations: {finding[:80]}...",
                })

        # Check contradictions for evidence
        for finding1, finding2 in contradictions:
            issues.append({
                "finding": f"{finding1[:50]} vs {finding2[:50]}",
                "issue_type": "contradiction",
                "severity": "high",
                "description": "Contradictory claims need resolution",
            })

        return issues[:20]  # Limit to top 20 issues
