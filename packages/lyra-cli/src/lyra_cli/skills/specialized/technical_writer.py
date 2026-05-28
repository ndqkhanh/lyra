"""Technical Writer Skill — documentation quality and completeness analysis.

Validates technical documentation for:
- Structure and navigation
- API reference completeness
- Code example quality
- Readability and clarity
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DocQuality(StrEnum):
    EXCELLENT = "excellent"
    GOOD = "good"
    NEEDS_IMPROVEMENT = "needs_improvement"
    MISSING = "missing"


@dataclass(frozen=True)
class DocIssue:
    section: str
    quality: DocQuality
    issue: str
    fix: str


class TechnicalWriterSkill:
    """Analyzes technical documentation for quality and completeness."""

    _REQUIRED_SECTIONS = frozenset({
        "overview", "installation", "quickstart", "api_reference", "configuration", "troubleshooting"
    })

    def run(self, input_data: dict) -> dict:
        content = input_data.get("content", "")
        sections = input_data.get("sections", [])
        issues: list[DocIssue] = []

        section_names = {s.get("name", "").lower().replace(" ", "_") for s in sections}
        for required in self._REQUIRED_SECTIONS:
            if required not in section_names:
                readable = required.replace("_", " ").title()
                issues.append(DocIssue(required, DocQuality.MISSING,
                    f"'{readable}' section is missing.",
                    f"Add a '{readable}' section to the documentation."))

        has_code_examples = "```" in content or "`" in content
        if not has_code_examples and len(sections) > 2:
            issues.append(DocIssue("examples", DocQuality.NEEDS_IMPROVEMENT,
                "No code examples found in documentation.",
                "Add practical code examples for key use cases."))

        word_count = len(content.split()) if content else 0
        if word_count < 100 and sections:
            issues.append(DocIssue("content", DocQuality.NEEDS_IMPROVEMENT,
                f"Documentation is very brief ({word_count} words).",
                "Expand documentation with more detailed explanations."))

        return {
            "issues": [i.__dict__ for i in issues],
            "word_count": word_count,
            "sections_covered": len(section_names & self._REQUIRED_SECTIONS),
            "total_required": len(self._REQUIRED_SECTIONS),
            "score": max(0, 100
                - len([i for i in issues if i.quality == DocQuality.MISSING]) * 20
                - len([i for i in issues if i.quality == DocQuality.NEEDS_IMPROVEMENT]) * 10),
        }
