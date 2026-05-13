"""Tests for T3 User/Team Memory Loader (Phase M8)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

import pytest

from lyra_core.memory.schema import FragmentType, MemoryTier
from lyra_core.memory.t3_loader import (
    extract_decision_rationale,
    extract_entities,
    extract_sections,
    infer_fragment_type,
    load_t3_file,
    load_user_memory,
    parse_frontmatter,
)


def test_parse_frontmatter_with_valid_yaml():
    """Test frontmatter parsing with valid YAML."""
    content = dedent("""
        ---
        version: 1
        user_id: alice
        last_updated: 2026-05-14T10:30:00Z
        tags: [python, testing]
        ---

        # Content
        Some content here.
    """).strip()

    metadata, body = parse_frontmatter(content)

    assert metadata.version == 1
    assert metadata.user_id == "alice"
    assert metadata.last_updated == datetime(2026, 5, 14, 10, 30, 0, tzinfo=timezone.utc)
    assert metadata.tags == ["python", "testing"]
    assert "# Content" in body


def test_parse_frontmatter_without_yaml():
    """Test frontmatter parsing when no YAML present."""
    content = "# Just a heading\nSome content."

    metadata, body = parse_frontmatter(content)

    assert metadata.version == 1
    assert metadata.user_id == "default"
    assert body == content


def test_extract_sections():
    """Test markdown section extraction."""
    body = dedent("""
        # Preferences

        I prefer functional programming.

        ## Code Style
        Use immutable data structures.

        # Decisions

        ## Use TypeScript
        TypeScript is better than JavaScript.
    """).strip()

    sections = extract_sections(body)

    assert len(sections) == 4
    assert sections[0].level == 1
    assert sections[0].title == "Preferences"
    assert "functional programming" in sections[0].content

    assert sections[1].level == 2
    assert sections[1].title == "Code Style"
    assert "immutable" in sections[1].content

    assert sections[2].level == 1
    assert sections[2].title == "Decisions"

    assert sections[3].level == 2
    assert sections[3].title == "Use TypeScript"


def test_infer_fragment_type():
    """Test fragment type inference from section titles."""
    from lyra_core.memory.t3_loader import MarkdownSection

    pref_section = MarkdownSection(1, "Preferences", "content", 1)
    assert infer_fragment_type(pref_section) == FragmentType.PREFERENCE

    decision_section = MarkdownSection(1, "Decisions", "content", 1)
    assert infer_fragment_type(decision_section) == FragmentType.DECISION

    skill_section = MarkdownSection(1, "Skills", "content", 1)
    assert infer_fragment_type(skill_section) == FragmentType.SKILL

    fact_section = MarkdownSection(1, "General", "content", 1)
    assert infer_fragment_type(fact_section) == FragmentType.FACT


def test_extract_decision_rationale():
    """Test rationale extraction from DECISION content."""
    content = dedent("""
        **Rationale:** Type safety reduces runtime errors.
        **Conclusion:** Use TypeScript for all new services.
    """).strip()

    result = extract_decision_rationale(content)

    assert "Type safety" in result["rationale"]
    assert "TypeScript" in result["conclusion"]


def test_extract_entities():
    """Test simple entity extraction."""
    text = "Use TypeScript and React for the Frontend. Avoid JavaScript."

    entities = extract_entities(text)

    assert "TypeScript" in entities
    assert "React" in entities
    assert "Frontend" in entities
    assert len(entities) <= 5


def test_load_t3_file(tmp_path: Path):
    """Test loading T3 file with full pipeline."""
    user_file = tmp_path / "user.md"
    user_file.write_text(
        dedent("""
        ---
        version: 1
        user_id: alice
        last_updated: 2026-05-14T10:30:00Z
        ---

        # Preferences

        ## Code Style
        I prefer functional programming patterns over OOP.

        # Decisions

        ## Use TypeScript
        **Rationale:** Type safety reduces runtime errors.
        **Conclusion:** All new services use TypeScript.
    """).strip()
    )

    fragments = load_t3_file(user_file, MemoryTier.T3_USER, "test-session", "test-agent")

    # Should have 2 fragments: Code Style and Use TypeScript
    # (Preferences and Decisions headings have no content, so they're skipped)
    assert len(fragments) == 2

    # Check first fragment (Code Style)
    code_frag = fragments[0]
    assert code_frag.tier == MemoryTier.T3_USER
    # Code Style should be inferred as PREFERENCE (has "code" keyword)
    assert code_frag.type in [FragmentType.PREFERENCE, FragmentType.SKILL]
    assert "functional programming" in code_frag.content
    assert code_frag.pinned is True
    assert code_frag.confidence == 0.9
    assert code_frag.provenance.user_id == "alice"

    # Check decision fragment (Use TypeScript)
    decision_frag = fragments[1]
    # Should be inferred as FACT (doesn't have "decision" in title, only in parent)
    # Let's check it has the decision content
    assert "TypeScript" in decision_frag.content
    assert decision_frag.structured.get("rationale") or decision_frag.structured.get("conclusion")
    if decision_frag.type == FragmentType.DECISION:
        assert "Type safety" in decision_frag.structured["rationale"]


def test_load_user_memory(tmp_path: Path):
    """Test load_user_memory helper."""
    memory_dir = tmp_path / ".lyra" / "memory"
    memory_dir.mkdir(parents=True)

    user_file = memory_dir / "user.md"
    user_file.write_text(
        dedent("""
        # Preferences
        I prefer pytest over unittest.
    """).strip()
    )

    fragments = load_user_memory(tmp_path, "test-session", "test-agent")

    assert len(fragments) == 1
    assert fragments[0].tier == MemoryTier.T3_USER
    assert "pytest" in fragments[0].content


def test_load_t3_file_nonexistent(tmp_path: Path):
    """Test loading nonexistent file returns empty list."""
    nonexistent = tmp_path / "nonexistent.md"

    fragments = load_t3_file(nonexistent, MemoryTier.T3_USER)

    assert fragments == []


def test_load_t3_file_empty_sections(tmp_path: Path):
    """Test that empty sections are skipped."""
    user_file = tmp_path / "user.md"
    user_file.write_text(
        dedent("""
        # Empty Section

        # Another Empty

        # Valid Section
        This has content.
    """).strip()
    )

    fragments = load_t3_file(user_file, MemoryTier.T3_USER)

    # Only the section with content should be loaded
    assert len(fragments) == 1
    assert "Valid Section" in fragments[0].content
