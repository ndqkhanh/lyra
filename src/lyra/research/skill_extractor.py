"""
Skill Extractor — auto-create reusable skills from research findings.

Extracts knowledge patterns from ``FindingRecord`` objects and research
papers, distills them into structured ``Skill`` instances with proper
frontmatter (``SkillTemplate``), and integrates with the Lyra skill
registry for automatic registration.

A quality gate ensures only findings that passed adversarial verification
are eligible for skill extraction.

Key features
------------
- **Extract from finding**: distill a ``FindingRecord`` into a ``Skill``.
- **Extract from paper**: scan a paper path for reusable patterns and
  generate one or more ``Skill`` objects.
- **SkillTemplate**: fills SKILL.md frontmatter (name, description,
  trigger_patterns, tags, category) from finding structure.
- **Quality gate**: only extract if the finding passed adversarial
  verification (``VerificationStatus.CONFIRMED`` or ``VERIFIED``).
- **SkillNet integration**: auto-registers extracted skills into the
  Phase 1 skill network.

References
----------
- Lyra skill system: ``src/lyra/skills/``
- SkillNet: ``src/lyra/skills/skillnet.py``
- DeepScientist: arXiv 2505.22954
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from lyra.research.evidence_graph import VerificationStatus
from lyra.research.findings_memory import FindingRecord, FindingStage
from lyra.skills.skill import Skill, SkillCategory
from lyra.skills.skillnet import SkillNet, SkillGraphLink
from lyra.skills.registry import SkillRegistry


# =============================================================================
# Constants
# =============================================================================

DEFAULT_SKILL_CATEGORY: SkillCategory = SkillCategory.GENERAL
"""Default skill category for extracted skills."""

SKILL_FILE_EXTENSION: str = ".md"
"""File extension for generated SKILL.md files."""

MIN_CONFIDENCE_FOR_EXTRACTION: float = 0.5
"""Minimum confidence threshold for extraction quality gate."""


# =============================================================================
# SkillTemplate — fills SKILL.md frontmatter
# =============================================================================


@dataclass
class SkillTemplate:
    """Fills SKILL.md frontmatter from finding structure.

    The template generates a Markdown file with YAML-style frontmatter
    compatible with the Lyra skill loader:

    .. code-block:: markdown

        ---
        name: skill-name
        description: Short description
        category: backend-patterns
        trigger_patterns: [pattern1, pattern2]
        tags: [tag1, tag2]
        language: python
        ---

        # Skill Content

        ...
    """

    name: str = ""
    description: str = ""
    category: SkillCategory = DEFAULT_SKILL_CATEGORY
    trigger_patterns: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    language: str | None = None
    content: str = ""
    source_ref: str = ""

    @classmethod
    def from_finding(
        cls,
        finding: FindingRecord,
        content: str = "",
    ) -> SkillTemplate:
        """Build a template from a ``FindingRecord``.

        Derives:
        - **name**: from the hypothesis (first ~6 words, slugified).
        - **description**: first 200 chars of the hypothesis.
        - **category**: inferred from tags or default.
        - **trigger_patterns**: key terms from the hypothesis.
        - **tags**: from finding tags and stage.
        - **language**: from source (if it looks like code).
        - **content**: the provided content or auto-generated.
        """
        # Name: slugify first 6 words of hypothesis
        words = finding.hypothesis.split()
        name = cls._slugify(" ".join(words[:6])) or "extracted-finding"

        # Description: first 200 chars of hypothesis
        description = finding.hypothesis[:200]

        # Trigger patterns: significant words from the hypothesis
        trigger_patterns = list(
            set(
                w.lower()
                for w in words
                if len(w) > 3 and w.lower() not in _STOP_WORDS
            )
        )[:5]

        # Tags: from finding metadata tags plus stage
        tags = list(finding.metadata.get("tags", []))
        if finding.stage == FindingStage.PROGRESS:
            tags.append("verified")
        tags.append(finding.stage.value)
        tags = list(set(tags))[:10]

        # Language hint
        language = finding.metadata.get("language") or None

        # Content
        if not content:
            content = cls._auto_content(finding)

        return cls(
            name=name,
            description=description,
            category=DEFAULT_SKILL_CATEGORY,
            trigger_patterns=trigger_patterns,
            tags=tags,
            language=language,
            content=content,
            source_ref=finding.finding_id,
        )

    def render(self) -> str:
        """Render the template as a Markdown file with frontmatter.

        Returns:
            Full Markdown string suitable for writing to a ``.md`` file.
        """
        lines: list[str] = [
            "---",
            f"name: {self.name}",
            f"description: {self.description}",
            f"category: {self.category.value}",
            f"trigger_patterns: {json.dumps(self.trigger_patterns)}",
            f"tags: {json.dumps(self.tags)}",
        ]
        if self.language:
            lines.append(f"language: {self.language}")
        if self.source_ref:
            lines.append(f"source: finding-{self.source_ref}")
        lines.append("---")
        lines.append("")
        lines.append(self.content)
        lines.append("")

        return "\n".join(lines)

    def to_skill(self) -> Skill:
        """Convert the template to a ``Skill`` object."""
        return Skill(
            name=self.name,
            description=self.description,
            content=self.content,
            category=self.category,
            trigger_patterns=self.trigger_patterns,
            tags=self.tags,
            language=self.language,
            source="lyra",
            metadata={
                "source_type": "research_finding",
                "source_ref": self.source_ref,
            },
        )

    @classmethod
    def _auto_content(cls, finding: FindingRecord) -> str:
        """Auto-generate skill content from a finding record."""
        parts: list[str] = [
            f"# {finding.hypothesis}",
            "",
            f"**Stage**: {finding.stage.value}",
            f"**Source**: finding `{finding.finding_id}`" if finding.finding_id else "",
            "",
            "## Description",
            "",
            finding.analysis or "Extracted from research finding.",
            "",
            "## Usage",
            "",
            "This skill was automatically extracted from a research finding.",
            "Apply it when the context matches the trigger patterns above.",
            "",
        ]
        if finding.experiment_logs:
            parts.extend([
                "## Evidence",
                "",
                f"- {len(finding.experiment_logs)} experiment(s) conducted.",
                f"- Implementation: {finding.implementation_ref or 'N/A'}",
                "",
            ])
        return "\n".join(parts)

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to a URL-safe slug."""
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[-\s]+", "-", text)
        return text[:80].strip("-")


# Common stop words for trigger generation
_STOP_WORDS: frozenset[str] = frozenset({
    "the", "and", "for", "with", "that", "this", "from", "which",
    "what", "when", "where", "how", "why", "about", "into", "through",
    "during", "before", "after", "above", "below", "between", "under",
    "again", "further", "then", "once", "here", "there", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such",
    "than", "also", "very", "just", "should", "could", "would",
})


# =============================================================================
# SkillExtractor
# =============================================================================


class SkillExtractor:
    """Auto-create reusable skills from research findings.

    The extractor takes ``FindingRecord`` objects or paper paths, distils
    them into structured ``Skill`` instances via ``SkillTemplate``, and
    optionally registers them in a ``SkillRegistry`` or ``SkillNet``.

    A quality gate ensures only findings that passed adversarial
    verification (``VerificationStatus.CONFIRMED`` or ``VERIFIED``) are
    eligible for extraction.

    Usage::

        extractor = SkillExtractor()

        # Extract from a single finding
        skill = extractor.extract_from_finding(finding_record)

        # Extract from a paper
        skills = extractor.extract_from_paper("/path/to/paper.md")

        # Extract with quality gate
        skill = extractor.extract_from_finding(
            finding, verification_status=VerificationStatus.CONFIRMED
        )
    """

    def __init__(
        self,
        registry: SkillRegistry | None = None,
        skill_net: SkillNet | None = None,
        output_dir: str | Path | None = None,
    ) -> None:
        """
        Args:
            registry: Optional ``SkillRegistry`` for auto-registration.
            skill_net: Optional ``SkillNet`` for integration with the
                Phase 1 skill network.
            output_dir: Optional directory to write SKILL.md files to.
        """
        self._registry = registry
        self._skill_net = skill_net
        self._output_dir = Path(output_dir) if output_dir else None

    # ------------------------------------------------------------------
    # Extraction from FindingRecord
    # ------------------------------------------------------------------

    def extract_from_finding(
        self,
        finding: FindingRecord,
        verification_status: VerificationStatus | None = None,
        auto_register: bool = True,
        write_file: bool = True,
    ) -> Skill | None:
        """Extract a reusable skill from a research finding.

        Applies the quality gate: extraction is skipped if the finding
        does not meet minimum confidence or the verification status is
        not CONFIRMED or VERIFIED.

        Args:
            finding: The ``FindingRecord`` to extract from.
            verification_status: Optional verification status from the
                ``EvidenceGraph``. If ``None``, the quality gate is
                relaxed (extracts from IDEA stage findings as well).
            auto_register: If True and a ``SkillRegistry`` is configured,
                the extracted skill is registered.
            write_file: If True and ``output_dir`` is configured, the
                skill is written as a ``.md`` file.

        Returns:
            A ``Skill`` object, or ``None`` if the quality gate rejected
            the finding.
        """
        if not self._passes_quality_gate(finding, verification_status):
            return None

        # Build the template
        template = SkillTemplate.from_finding(finding)

        # Convert to Skill
        skill = template.to_skill()

        # Auto-register
        if auto_register and self._registry is not None:
            self._registry.register(skill)

        # Integrate into skill net
        if self._skill_net is not None:
            self._skill_net.add_skill(skill)

        # Write file
        if write_file and self._output_dir is not None:
            self._write_skill_file(skill, template)

        return skill

    def extract_multiple(
        self,
        findings: list[FindingRecord],
        verification_statuses: dict[str, VerificationStatus] | None = None,
        auto_register: bool = True,
        write_file: bool = True,
    ) -> list[Skill]:
        """Extract skills from multiple findings.

        Args:
            findings: List of ``FindingRecord`` to process.
            verification_statuses: Optional dict mapping ``finding_id``
                to ``VerificationStatus`` for the quality gate.
            auto_register: If True, register extracted skills.
            write_file: If True, write extracted skills to files.

        Returns:
            List of successfully extracted ``Skill`` objects (findings
            that failed the quality gate are omitted).
        """
        skills: list[Skill] = []
        for finding in findings:
            vs = None
            if verification_statuses is not None:
                vs = verification_statuses.get(finding.finding_id)
            skill = self.extract_from_finding(
                finding,
                verification_status=vs,
                auto_register=auto_register,
                write_file=write_file,
            )
            if skill is not None:
                skills.append(skill)
        return skills

    # ------------------------------------------------------------------
    # Extraction from paper
    # ------------------------------------------------------------------

    def extract_from_paper(
        self,
        paper_path: str | Path,
        auto_register: bool = True,
        write_file: bool = True,
    ) -> list[Skill]:
        """Scan a research paper for reusable patterns and distill skills.

        The method reads the paper, identifies key sections (abstract,
        methodology, results, conclusions), and extracts actionable
        patterns as ``Skill`` objects.

        Args:
            paper_path: Path to the paper file (``.md``, ``.txt``,
                or ``.pdf``).
            auto_register: If True, register extracted skills.
            write_file: If True, write extracted skills to files.

        Returns:
            List of extracted ``Skill`` objects.
        """
        path = Path(paper_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Paper not found: {path}")

        text = self._read_paper(path)

        # Parse sections from the paper
        sections = self._parse_sections(text)

        skills: list[Skill] = []
        for section in sections:
            template = SkillTemplate(
                name=self._slugify_section(section["heading"]),
                description=section["heading"][:200],
                category=self._detect_category_from_section(section),
                trigger_patterns=self._extract_trigger_words(section),
                tags=self._extract_tags_from_section(section),
                language=self._detect_language_from_text(section["body"]),
                content=section["body"],
                source_ref=path.name,
            )

            skill = template.to_skill()

            if auto_register and self._registry is not None:
                self._registry.register(skill)

            if self._skill_net is not None:
                self._skill_net.add_skill(skill)

            if write_file and self._output_dir is not None:
                self._write_skill_file(skill, template)

            skills.append(skill)

        return skills

    # ------------------------------------------------------------------
    # Quality gate
    # ------------------------------------------------------------------

    @staticmethod
    def _passes_quality_gate(
        finding: FindingRecord,
        verification_status: VerificationStatus | None,
    ) -> bool:
        """Check if a finding meets the quality threshold for extraction.

        A finding passes if:
        1. The finding has a non-empty hypothesis.
        2. The valuation combined score is >= MIN_CONFIDENCE_FOR_EXTRACTION.
        3. If ``verification_status`` is provided, it must be CONFIRMED
           or VERIFIED.

        Args:
            finding: The finding record to check.
            verification_status: Optional verification status from
                ``EvidenceGraph``.

        Returns:
            ``True`` if the finding should be extracted.
        """
        if not finding.hypothesis or not finding.hypothesis.strip():
            return False

        if finding.valuation.combined() < MIN_CONFIDENCE_FOR_EXTRACTION:
            return False

        if verification_status is not None:
            if verification_status not in (
                VerificationStatus.CONFIRMED,
                VerificationStatus.VERIFIED,
            ):
                return False

        return True

    # ------------------------------------------------------------------
    # Paper parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _read_paper(path: Path) -> str:
        """Read paper text from a file.

        Supports ``.md``, ``.txt``, and basic ``.pdf`` (via raw text
        extraction if PyMuPDF is not available).

        Args:
            path: Path to the paper file.

        Returns:
            UTF-8 decoded text content.
        """
        suffix = path.suffix.lower()

        if suffix in (".md", ".txt"):
            return path.read_text(encoding="utf-8", errors="ignore")

        if suffix == ".pdf":
            try:
                import fitz  # PyMuPDF

                doc = fitz.open(str(path))
                lines: list[str] = []
                for page in doc:
                    lines.append(page.get_text())
                doc.close()
                return "\n".join(lines)[:10000]
            except ImportError:
                # Raw fallback
                raw = path.read_bytes()
                text: list[str] = []
                for match in re.finditer(rb"\((.*?)\)", raw):
                    decoded = match.group(1).decode("latin-1", errors="ignore")
                    if len(decoded) > 3 and all(
                        c.isprintable() or c in "\n\r\t " for c in decoded
                    ):
                        text.append(decoded)
                return " ".join(text)[:10000]

        # Fallback: try reading as-is
        return path.read_text(encoding="utf-8", errors="ignore")[:10000]

    @staticmethod
    def _parse_sections(text: str) -> list[dict[str, Any]]:
        """Parse a paper into heading-anchored sections.

        Splits on Markdown headings (``## ...``, ``### ...``) and
        returns each section as a dict with ``heading`` and ``body``.

        Args:
            text: Raw paper text.

        Returns:
            List of section dicts.
        """
        sections: list[dict[str, Any]] = []
        current_heading = "Abstract"
        current_body: list[str] = []

        for line in text.split("\n"):
            heading_match = re.match(r"^(#{1,3})\s+(.+)", line)
            if heading_match:
                # Save previous section
                body = "\n".join(current_body).strip()
                if body:
                    sections.append({
                        "heading": current_heading,
                        "body": body,
                    })
                current_heading = heading_match.group(2).strip()
                current_body = []
            else:
                current_body.append(line)

        # Last section
        body = "\n".join(current_body).strip()
        if body:
            sections.append({
                "heading": current_heading,
                "body": body,
            })

        return sections

    # ------------------------------------------------------------------
    # SkillNet integration
    # ------------------------------------------------------------------

    def link_to_skillnet(
        self,
        skills: list[Skill],
        similarity_threshold: float = 0.3,
    ) -> SkillNet:
        """Link extracted skills into the existing ``SkillNet``.

        Creates similarity and dependency links between extracted skills
        and skills already in the network.

        Args:
            skills: Extracted skills to link.
            similarity_threshold: Minimum Jaccard similarity for a link.

        Returns:
            The updated ``SkillNet`` (or a new one if none was configured).
        """
        net = self._skill_net or SkillNet()

        for skill in skills:
            net.add_skill(skill)

        # Create similarity links between all pairs of newly extracted skills
        for i, a in enumerate(skills):
            for b in skills[i + 1:]:
                sim = self._jaccard(a, b)
                if sim >= similarity_threshold:
                    net.add_link(SkillGraphLink(
                        source=a.name,
                        target=b.name,
                        weight=round(sim, 3),
                        metadata={"jaccard": sim},
                    ))
                    net.add_link(SkillGraphLink(
                        source=b.name,
                        target=a.name,
                        weight=round(sim, 3),
                        metadata={"jaccard": sim},
                    ))

        return net

    # ------------------------------------------------------------------
    # File writing
    # ------------------------------------------------------------------

    def _write_skill_file(
        self,
        skill: Skill,
        template: SkillTemplate,
    ) -> Path:
        """Write the extracted skill to a ``.md`` file.

        Args:
            skill: The skill to write.
            template: The template that produced the skill.

        Returns:
            Path to the written file.
        """
        if self._output_dir is None:
            # If no output dir — just skip
            return Path()

        self._output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{template.name}{SKILL_FILE_EXTENSION}"
        filepath = self._output_dir / filename

        rendered = template.render()
        filepath.write_text(rendered, encoding="utf-8")

        return filepath

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_category_from_section(
        section: dict[str, Any],
    ) -> SkillCategory:
        """Detect the skill category from a paper section."""
        heading_lower = section.get("heading", "").lower()
        body_lower = section.get("body", "").lower()

        if any(kw in heading_lower for kw in ("method", "algorithm", "implementation")):
            return SkillCategory.BACKEND_PATTERNS
        if any(kw in heading_lower for kw in ("result", "evaluation", "experiment")):
            return SkillCategory.TDD_TESTING
        if any(kw in heading_lower for kw in ("security", "safety", "privacy")):
            return SkillCategory.SECURITY_REVIEW
        if any(kw in heading_lower for kw in ("api", "interface", "endpoint")):
            return SkillCategory.API_DESIGN
        if any(kw in heading_lower for kw in ("frontend", "ui", "interface")):
            return SkillCategory.FRONTEND_PATTERNS
        if any(kw in body_lower for kw in ("docker", "deploy", "ci/cd", "pipeline")):
            return SkillCategory.DEPLOYMENT

        return DEFAULT_SKILL_CATEGORY

    @staticmethod
    def _extract_trigger_words(section: dict[str, Any]) -> list[str]:
        """Extract trigger keywords from a paper section.

        Returns up to 8 significant words from the heading and first 200
        chars of the body.
        """
        heading = section.get("heading", "")
        body = section.get("body", "")[:200]

        combined = f"{heading} {body}"
        words = re.findall(r"\b[a-zA-Z]{4,}\b", combined.lower())
        unique = list(dict.fromkeys(words))  # Preserve order, deduplicate
        return unique[:8]

    @staticmethod
    def _extract_tags_from_section(section: dict[str, Any]) -> list[str]:
        """Extract tags from a paper section."""
        tags: set[str] = set()
        heading = section.get("heading", "").lower()

        # Map common section headings to tags
        tag_map: dict[str, list[str]] = {
            "abstract": ["overview"],
            "introduction": ["overview", "motivation"],
            "method": ["methodology", "algorithm"],
            "methodology": ["methodology"],
            "implementation": ["implementation", "code"],
            "experiment": ["experiment", "evaluation"],
            "result": ["result", "evaluation"],
            "conclusion": ["conclusion", "summary"],
            "discussion": ["discussion", "analysis"],
        }

        for key, mapped_tags in tag_map.items():
            if key in heading:
                tags.update(mapped_tags)

        return list(tags)[:10]

    @staticmethod
    def _detect_language_from_text(text: str) -> str | None:
        """Detect programming language from code blocks in the text."""
        code_block_match = re.search(
            r"```(\w+)", text, re.MULTILINE
        )
        if code_block_match:
            return code_block_match.group(1)

        # Heuristic: look for language-specific keywords
        if re.search(r"\b(def |class |import |from \w+ import)", text):
            return "python"
        if re.search(r"\bfunction\b|\bconst\b|\blet\b|\bvar\b", text):
            return "javascript"
        if re.search(r"\bfunc\b|\bpackage\b|\bimport\s+\"", text):
            return "go"
        if re.search(r"\buse\s+\w+::", text):
            return "rust"

        return None

    @staticmethod
    def _jaccard(a: Skill, b: Skill) -> float:
        """Jaccard similarity between two skills based on tags and content."""
        set_a = set(t.lower() for t in a.tags) | set(
            w.lower()
            for w in re.findall(r"\b[a-z]{4,}\b", a.content.lower())
        )
        set_b = set(t.lower() for t in b.tags) | set(
            w.lower()
            for w in re.findall(r"\b[a-z]{4,}\b", b.content.lower())
        )
        if not set_a or not set_b:
            return 0.0
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / max(len(union), 1)

    @staticmethod
    def _slugify_section(heading: str) -> str:
        """Convert a section heading to a skill-name slug."""
        slug = heading.lower().strip()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[-\s]+", "-", slug)
        return slug[:60].strip("-")
