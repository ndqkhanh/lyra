"""
Falsification checking agent.

Checks for falsification attempts and verifies claims.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from lyra_research.agents.analysis.analysis_base import Analysis
from lyra_research.agents.synthesis.synthesis_base import SynthesisAgent, SynthesisResult


class FalsificationCheckerAgent(SynthesisAgent):
    """
    Checks for falsification attempts and verifies claims.

    Identifies:
    - Overstated claims
    - Cherry-picked results
    - Missing counter-evidence
    - Unverifiable statements
    """

    def __init__(self, model: str = "claude-opus-4-7") -> None:
        super().__init__(synthesis_type="falsification", model=model)

    async def synthesize(self, analyses: List[Analysis]) -> SynthesisResult:
        """
        Check for falsification attempts.

        Args:
            analyses: List of analysis results (from evidence audit)

        Returns:
            Synthesis result with falsification check findings
        """
        # Extract findings and evidence issues
        all_findings = []
        evidence_issues = []

        for analysis in analyses:
            if analysis.analysis_type == "evidence":
                evidence_issues = analysis.metadata.get("evidence_issues", [])
            all_findings.extend(analysis.findings)

        # Check for falsification
        falsification_risks = self._check_falsification(all_findings, evidence_issues)

        # Calculate confidence
        confidence = 1.0 if not falsification_risks else 0.8

        return SynthesisResult(
            synthesis_type=self.synthesis_type,
            findings=[risk["description"] for risk in falsification_risks],
            metadata={
                "falsification_risks": falsification_risks,
                "risk_count": len(falsification_risks),
            },
            confidence=confidence,
            issues_found=len(falsification_risks),
        )

    def _check_falsification(
        self, findings: List[str], evidence_issues: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Check for falsification risks.

        Returns list of falsification risks.
        """
        risks: List[Dict[str, Any]] = []

        # Patterns for overstated claims
        overstatement_patterns = [
            r"\b(always|never|all|none|every|impossible|guaranteed)\b",
            r"\b(best|worst|perfect|flawless|ultimate|definitive)\b",
            r"\b(proves?|confirms?|establishes?) (?:beyond|without) (?:doubt|question)\b",
        ]

        # Check each finding for overstatements
        for finding in findings:
            finding_lower = finding.lower()

            # Check for overstatements
            for pattern in overstatement_patterns:
                if re.search(pattern, finding_lower):
                    risks.append({
                        "finding": finding[:100],
                        "risk_type": "overstatement",
                        "severity": "medium",
                        "description": f"Overstated claim: {finding[:80]}...",
                        "pattern": pattern,
                    })
                    break

            # Check for numerical claims without citations
            if re.search(r'\d+(?:\.\d+)?%', finding):
                citations = re.findall(r'\[(\d+)\]', finding)
                if not citations:
                    risks.append({
                        "finding": finding[:100],
                        "risk_type": "unverified_numerical",
                        "severity": "high",
                        "description": f"Numerical claim without citation: {finding[:80]}...",
                    })

        # Promote critical evidence issues to falsification risks
        for issue in evidence_issues:
            if issue.get("severity") == "critical":
                risks.append({
                    "finding": issue["finding"],
                    "risk_type": "missing_evidence",
                    "severity": "critical",
                    "description": f"Critical evidence gap: {issue['description']}",
                })

        return risks[:15]  # Limit to top 15 risks
