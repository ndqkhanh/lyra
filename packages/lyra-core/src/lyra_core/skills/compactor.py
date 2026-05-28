"""Skill Compactor — auto-compaction of skill documents to reduce token usage.

Part of the 6-phase skill lifecycle (Plan 31): Curate → Load → Invoke → Learn → Evolve → **COMPACT**.

When a skill document exceeds the token budget, the compactor preserves the
essential instruction structure while removing redundant examples and verbose
explanations. Uses a simple priority-based compaction strategy:

1. Preserve: name, description, purpose, procedure steps
2. Compact: examples (keep best 2-3), verbose notes, historical changelogs
3. Remove: duplicate paragraphs, empty sections, old version blocks
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar


@dataclass
class CompactionReport:
    """Report from a compaction run."""

    skill_id: str
    original_tokens: int
    compacted_tokens: int
    sections_preserved: int
    sections_compacted: int
    sections_removed: int
    savings_pct: float

    @property
    def token_savings(self) -> int:
        return self.original_tokens - self.compacted_tokens


class SkillCompactor:
    """Auto-compacts skill documents to stay within token budgets.

    Usage::

        compactor = SkillCompactor(max_tokens=2000)
        report = compactor.compact("my-skill", skill_content)
        if report.savings_pct > 0.2:
            save(report.compacted_text)
    """

    _SECTION_RE: ClassVar[re.Pattern] = re.compile(
        r"^#{1,3}\s+(.+)$", re.MULTILINE
    )
    _PRESERVE_SECTIONS: ClassVar[set[str]] = {
        "purpose", "overview", "description", "procedure", "steps",
        "allowed-tools", "allowed-context", "prerequisites",
    }
    _COMPACT_SECTIONS: ClassVar[set[str]] = {
        "examples", "example", "notes", "background", "details",
        "appendix", "faq", "troubleshooting",
    }
    _SKIP_SECTIONS: ClassVar[set[str]] = {
        "changelog", "history", "version-history", "deprecated",
    }

    def __init__(self, max_tokens: int = 2000):
        self.max_tokens = max_tokens

    def compact(self, skill_id: str, content: str) -> tuple[str, CompactionReport]:
        """Compact skill content to fit within max_tokens."""
        original_tokens = _estimate_tokens(content)
        sections = self._parse_sections(content)

        preserved: list[tuple[str, str]] = []
        compacted: list[tuple[str, str]] = []
        removed: list[str] = []

        for heading, body in sections:
            norm = heading.strip("# ").lower()
            if any(s in norm for s in self._SKIP_SECTIONS):
                removed.append(heading)
            elif any(s in norm for s in self._COMPACT_SECTIONS):
                compacted.append((heading, self._compact_body(body)))
            else:
                preserved.append((heading, body))

        result_parts: list[str] = []
        for h, b in preserved:
            result_parts.append(f"{h}\n{b}")
        for h, b in compacted:
            result_parts.append(f"{h}\n{b}")

        compacted_text = "\n\n".join(result_parts)
        compacted_tokens = _estimate_tokens(compacted_text)

        if compacted_tokens > self.max_tokens:
            compacted_text = self._truncate_to_budget(compacted_text, preserved, compacted)

        report = CompactionReport(
            skill_id=skill_id,
            original_tokens=original_tokens,
            compacted_tokens=_estimate_tokens(compacted_text),
            sections_preserved=len(preserved),
            sections_compacted=len(compacted),
            sections_removed=len(removed),
            savings_pct=1.0 - (_estimate_tokens(compacted_text) / max(1, original_tokens)),
        )
        return compacted_text, report

    def _parse_sections(self, content: str) -> list[tuple[str, str]]:
        """Split content into (heading, body) pairs."""
        parts = self._SECTION_RE.split(content)
        sections: list[tuple[str, str]] = []

        if parts and not parts[0].startswith("#"):
            sections.append(("## Preamble", parts[0].strip()))
            parts = parts[1:]

        i = 0
        while i + 1 < len(parts):
            heading = parts[i].strip() if i < len(parts) else ""
            body = parts[i + 1].strip() if i + 1 < len(parts) else ""
            if heading:
                sections.append((f"## {heading}", body))
            i += 2

        return sections

    def _compact_body(self, body: str) -> str:
        """Compact a non-critical section body."""
        lines = body.strip().split("\n")
        if len(lines) <= 5:
            return body

        paras = _split_paragraphs(lines)
        if len(paras) <= 2:
            return body

        return "\n\n".join(paras[:3]) + f"\n\n_(compacted: {len(paras) - 3} paragraphs removed)_"

    def _truncate_to_budget(
        self,
        text: str,
        preserved: list[tuple[str, str]],
        compacted: list[tuple[str, str]],
    ) -> str:
        """Truncate to fit within token budget, keeping highest-priority sections."""
        budget_tokens = self.max_tokens
        result: list[str] = []
        used = 0

        for h, b in preserved:
            section_text = f"{h}\n{b}"
            st = _estimate_tokens(section_text)
            if used + st <= budget_tokens:
                result.append(section_text)
                used += st
            else:
                break

        for h, b in compacted:
            section_text = f"{h}\n{b}"
            st = _estimate_tokens(section_text)
            if used + st <= budget_tokens:
                result.append(section_text)
                used += st

        return "\n\n".join(result)


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _split_paragraphs(lines: list[str]) -> list[str]:
    """Split lines into paragraph blocks."""
    paragraphs: list[str] = []
    current: list[str] = []
    for line in lines:
        if line.strip():
            current.append(line)
        elif current:
            paragraphs.append("\n".join(current))
            current = []
    if current:
        paragraphs.append("\n".join(current))
    return paragraphs
