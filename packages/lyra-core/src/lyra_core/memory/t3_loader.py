"""T3 User/Team Memory Loader (Phase M8).

Loads T3 memory from markdown-first user.md and team.md files with:
  - YAML frontmatter parsing for metadata
  - Fragment extraction from markdown sections
  - Tier assignment (t3_user vs t3_team)
  - Automatic provenance tracking
  - Filesystem watcher integration

File format:
```markdown
---
version: 1
user_id: alice
last_updated: 2026-05-14T10:30:00Z
---

# Preferences

## Code Style
I prefer functional programming patterns over OOP when possible.

## Testing
Always write tests first (TDD). Minimum 80% coverage.

# Decisions

## Use TypeScript for new services
**Rationale:** Type safety reduces runtime errors, better IDE support.
**Conclusion:** All new backend services use TypeScript, not JavaScript.
```

Research grounding:
  - CoALA T3 procedural memory (markdown-first, git-synced)
  - Graphiti bi-temporal validity (valid_from / invalid_at)
  - Collaborative Memory provenance tracking
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .schema import Fragment, FragmentType, MemoryTier, Provenance


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------


@dataclass
class T3Metadata:
    """Metadata extracted from YAML frontmatter."""

    version: int = 1
    user_id: str = "default"
    team_id: str | None = None
    last_updated: datetime | None = None
    tags: list[str] | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "T3Metadata":
        last_updated = d.get("last_updated")
        if isinstance(last_updated, str):
            last_updated = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
        elif last_updated is None:
            last_updated = datetime.now(timezone.utc)

        return cls(
            version=d.get("version", 1),
            user_id=d.get("user_id", "default"),
            team_id=d.get("team_id"),
            last_updated=last_updated,
            tags=d.get("tags"),
        )


def parse_frontmatter(content: str) -> tuple[T3Metadata, str]:
    """Extract YAML frontmatter and return metadata + body.

    Args:
        content: Full markdown file content

    Returns:
        (metadata, body) where body has frontmatter stripped
    """
    # Match YAML frontmatter: ---\n...\n---
    pattern = r"^---\s*\n(.*?)\n---\s*\n"
    match = re.match(pattern, content, re.DOTALL)

    if not match:
        # No frontmatter, use defaults
        return T3Metadata(), content

    yaml_text = match.group(1)
    body = content[match.end() :]

    try:
        data = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError:
        # Invalid YAML, treat as no frontmatter
        return T3Metadata(), content

    return T3Metadata.from_dict(data), body


# Fragment extraction from markdown sections
# ---------------------------------------------------------------------------


@dataclass
class MarkdownSection:
    """A section extracted from markdown (heading + content)."""

    level: int  # 1 for #, 2 for ##, etc.
    title: str
    content: str
    line_start: int


def extract_sections(body: str) -> list[MarkdownSection]:
    """Parse markdown body into sections based on headings.

    Args:
        body: Markdown content (frontmatter already stripped)

    Returns:
        List of sections with heading level, title, and content
    """
    sections: list[MarkdownSection] = []
    lines = body.split("\n")

    current_section: MarkdownSection | None = None
    current_content: list[str] = []

    for i, line in enumerate(lines):
        # Match markdown heading: # Title or ## Title
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)

        if heading_match:
            # Save previous section if exists (even if empty content)
            if current_section is not None:
                current_section.content = "\n".join(current_content).strip()
                # Always append, we'll filter empty sections later in load_t3_file
                sections.append(current_section)

            # Start new section
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            current_section = MarkdownSection(
                level=level, title=title, content="", line_start=i + 1
            )
            current_content = []
        elif current_section is not None:
            current_content.append(line)

    # Save final section
    if current_section is not None:
        current_section.content = "\n".join(current_content).strip()
        sections.append(current_section)

    return sections


# ---------------------------------------------------------------------------
# Fragment type inference
# ---------------------------------------------------------------------------


def infer_fragment_type(section: MarkdownSection) -> FragmentType:
    """Infer fragment type from section title and content.

    Rules:
      - "Preferences" / "Settings" → PREFERENCE
      - "Decisions" / "ADR" → DECISION
      - "Skills" / "Code" → SKILL
      - Default → FACT
    """
    title_lower = section.title.lower()

    if any(kw in title_lower for kw in ["preference", "setting", "config"]):
        return FragmentType.PREFERENCE
    elif any(kw in title_lower for kw in ["decision", "adr", "rationale"]):
        return FragmentType.DECISION
    elif any(kw in title_lower for kw in ["skill", "code", "snippet"]):
        return FragmentType.SKILL
    else:
        return FragmentType.FACT


def extract_decision_rationale(content: str) -> dict[str, str]:
    """Extract rationale and conclusion from DECISION content.

    Expected format:
      **Rationale:** ...
      **Conclusion:** ...

    Returns:
        {"rationale": "...", "conclusion": "..."}
    """
    rationale_match = re.search(
        r"\*\*Rationale:\*\*\s*(.+?)(?=\*\*|$)", content, re.DOTALL | re.IGNORECASE
    )
    conclusion_match = re.search(
        r"\*\*Conclusion:\*\*\s*(.+?)(?=\*\*|$)", content, re.DOTALL | re.IGNORECASE
    )

    return {
        "rationale": rationale_match.group(1).strip() if rationale_match else "",
        "conclusion": conclusion_match.group(1).strip() if conclusion_match else "",
    }


# ---------------------------------------------------------------------------
# T3 Loader
# ---------------------------------------------------------------------------


def load_t3_file(
    file_path: Path,
    tier: MemoryTier,
    session_id: str = "t3-loader",
    agent_id: str = "system",
) -> list[Fragment]:
    """Load T3 memory fragments from user.md or team.md.

    Args:
        file_path: Path to user.md or team.md
        tier: MemoryTier.T3_USER or MemoryTier.T3_TEAM
        session_id: Session ID for provenance
        agent_id: Agent ID for provenance

    Returns:
        List of Fragment objects extracted from the file
    """
    if not file_path.exists():
        return []

    content = file_path.read_text(encoding="utf-8")
    metadata, body = parse_frontmatter(content)
    sections = extract_sections(body)

    fragments: list[Fragment] = []

    for section in sections:
        # Skip empty sections
        if not section.content:
            continue

        fragment_type = infer_fragment_type(section)

        # Build structured payload
        structured: dict[str, Any] = {}

        # Extract rationale/conclusion if present (regardless of inferred type)
        # This handles cases where decision content is under a non-decision heading
        decision_data = extract_decision_rationale(section.content)
        if decision_data["rationale"] or decision_data["conclusion"]:
            # Only upgrade to DECISION if we have rationale (required by schema)
            if decision_data["rationale"]:
                structured = decision_data
                # If we found decision structure, upgrade type to DECISION
                if fragment_type == FragmentType.FACT:
                    fragment_type = FragmentType.DECISION

        # Create fragment ID: tier:type:uuid
        fragment_id = f"{tier.value}:{fragment_type.value}:{uuid.uuid4().hex[:8]}"

        # Extract entities (simple noun-phrase extraction)
        entities = extract_entities(section.content)

        # Build provenance
        provenance = Provenance(
            agent_id=agent_id,
            session_id=session_id,
            user_id=metadata.user_id,
            resources=[str(file_path)],
        )

        # Create fragment
        fragment = Fragment(
            id=fragment_id,
            tier=tier,
            type=fragment_type,
            content=f"{section.title}: {section.content[:150]}",  # Truncate to 200 chars
            provenance=provenance,
            structured=structured,
            entities=entities,
            confidence=0.9,  # High confidence for user-authored content
            pinned=True,  # T3 fragments are never evicted
            valid_from=metadata.last_updated or datetime.now(timezone.utc),
        )

        fragments.append(fragment)

    return fragments


def extract_entities(text: str) -> list[str]:
    """Simple entity extraction (noun phrases, capitalized words).

    Args:
        text: Content to extract entities from

    Returns:
        List of entity strings (max 5)
    """
    # Extract capitalized words including compound words like TypeScript, JavaScript
    # Pattern: Capital letter followed by letters (including more capitals)
    words = re.findall(r"\b[A-Z][a-zA-Z]+\b", text)

    # Deduplicate and limit to 5
    entities = list(dict.fromkeys(words))[:5]

    return entities


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_user_memory(
    repo_root: Path, session_id: str = "t3-loader", agent_id: str = "system"
) -> list[Fragment]:
    """Load user memory from <repo>/.lyra/memory/user.md.

    Args:
        repo_root: Repository root directory
        session_id: Session ID for provenance
        agent_id: Agent ID for provenance

    Returns:
        List of Fragment objects from user.md
    """
    user_file = repo_root / ".lyra" / "memory" / "user.md"
    return load_t3_file(user_file, MemoryTier.T3_USER, session_id, agent_id)


def load_team_memory(
    repo_root: Path, session_id: str = "t3-loader", agent_id: str = "system"
) -> list[Fragment]:
    """Load team memory from <repo>/.lyra/memory/team.md.

    Args:
        repo_root: Repository root directory
        session_id: Session ID for provenance
        agent_id: Agent ID for provenance

    Returns:
        List of Fragment objects from team.md
    """
    team_file = repo_root / ".lyra" / "memory" / "team.md"
    return load_t3_file(team_file, MemoryTier.T3_TEAM, session_id, agent_id)


__all__ = [
    "T3Metadata",
    "MarkdownSection",
    "parse_frontmatter",
    "extract_sections",
    "infer_fragment_type",
    "extract_decision_rationale",
    "load_t3_file",
    "load_user_memory",
    "load_team_memory",
    "extract_entities",
]

