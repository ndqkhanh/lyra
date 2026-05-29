"""
Cross-source synthesis agent.

Synthesizes findings across multiple sources into a coherent taxonomy.
"""
from __future__ import annotations

from typing import Any

from lyra_research.agents.analysis.analysis_base import Analysis
from lyra_research.agents.synthesis.synthesis_base import SynthesisAgent, SynthesisResult


class CrossSourceSynthesizerAgent(SynthesisAgent):
    """
    Synthesizes findings across sources into coherent taxonomy.

    Groups findings by theme, identifies patterns, builds hierarchical structure.
    """

    def __init__(self, model: str = "claude-opus-4-7") -> None:
        super().__init__(synthesis_type="cross_source", model=model)

    async def synthesize(self, analyses: list[Analysis]) -> SynthesisResult:
        """
        Synthesize findings across sources.

        Args:
            analyses: List of analysis results

        Returns:
            Synthesis result with taxonomy and grouped findings
        """
        # Extract all findings
        all_findings = []
        for analysis in analyses:
            all_findings.extend(analysis.findings)

        # Group findings by theme
        themes = self._extract_themes(all_findings)
        grouped_findings = self._group_by_theme(all_findings, themes)

        # Build taxonomy
        taxonomy = self._build_taxonomy(grouped_findings)

        # Calculate confidence based on source diversity
        source_types = {a.analysis_type for a in analyses}
        confidence = min(len(source_types) / 4.0, 1.0)  # 4 analysis types

        return SynthesisResult(
            synthesis_type=self.synthesis_type,
            findings=all_findings,
            metadata={
                "themes": themes,
                "grouped_findings": grouped_findings,
                "taxonomy": taxonomy,
                "source_count": len(analyses),
            },
            confidence=confidence,
        )

    def _extract_themes(self, findings: list[str]) -> list[str]:
        """Extract recurring themes from findings."""
        # Simple keyword extraction
        word_counts: dict[str, int] = {}
        stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
            "been", "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "should", "could", "may", "might", "must", "can", "this",
            "that", "these", "those", "it", "its", "they", "their", "them",
        }

        for finding in findings:
            words = finding.lower().split()
            for word in words:
                # Clean word
                word = word.strip(".,!?;:()[]{}\"'")
                if len(word) >= 4 and word not in stopwords:
                    word_counts[word] = word_counts.get(word, 0) + 1

        # Get top themes (words appearing 2+ times)
        themes = [
            word for word, count in sorted(
                word_counts.items(), key=lambda x: -x[1]
            )
            if count >= 2
        ][:10]

        return themes

    def _group_by_theme(
        self, findings: list[str], themes: list[str]
    ) -> dict[str, list[str]]:
        """Group findings by theme."""
        grouped: dict[str, list[str]] = {theme: [] for theme in themes}
        grouped["other"] = []

        for finding in findings:
            finding_lower = finding.lower()
            assigned = False

            for theme in themes:
                if theme in finding_lower:
                    grouped[theme].append(finding)
                    assigned = True
                    break

            if not assigned:
                grouped["other"].append(finding)

        # Remove empty groups
        return {k: v for k, v in grouped.items() if v}

    def _build_taxonomy(self, grouped_findings: dict[str, list[str]]) -> dict[str, Any]:
        """Build hierarchical taxonomy from grouped findings."""
        taxonomy = {
            "categories": list(grouped_findings.keys()),
            "hierarchy": {},
        }

        # Build simple 2-level hierarchy
        for category, findings in grouped_findings.items():
            taxonomy["hierarchy"][category] = {
                "finding_count": len(findings),
                "sample_findings": findings[:3],  # Top 3 findings
            }

        return taxonomy
