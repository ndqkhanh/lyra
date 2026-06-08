"""
Tests for SkillParser — parsing Markdown with YAML frontmatter.

Covers:
  - parse_string with valid/invalid input
  - parse_file with various formats
  - parse_directory (recursive and non-recursive)
  - Frontmatter edge cases (missing fields, bad YAML, string vs list triggers)
  - Category mapping (valid, invalid)
  - Metadata propagation (source_path)
  - Language and framework fields
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from lyra.skills.parser import SkillParser
from lyra.skills.skill import Skill, SkillCategory


class TestSkillParser:
    """Tests for SkillParser class."""

    @pytest.fixture
    def parser(self) -> SkillParser:
        return SkillParser()

    # -- parse_string -----------------------------------------------------

    def test_parse_string_valid(self, parser: SkillParser) -> None:
        content = """---
name: python-testing
description: Python testing patterns
category: tdd-testing
trigger_patterns: [pytest, test]
tags: [python, testing]
language: python
framework: pytest
version: 2.0.0
source: ecc
---

# Python Testing

Use pytest for testing.
"""
        skill = parser.parse_string(content)
        assert skill is not None
        assert skill.name == "python-testing"
        assert skill.description == "Python testing patterns"
        assert skill.category == SkillCategory.TDD_TESTING
        assert skill.trigger_patterns == ["pytest", "test"]
        assert skill.tags == ["python", "testing"]
        assert skill.language == "python"
        assert skill.framework == "pytest"
        assert skill.version == "2.0.0"
        assert skill.source == "ecc"
        assert "# Python Testing" in skill.content
        assert skill.content.endswith("pytest for testing.")

    def test_parse_string_no_frontmatter(self, parser: SkillParser) -> None:
        content = "Just content without frontmatter."
        skill = parser.parse_string(content)
        assert skill is None

    def test_parse_string_invalid_yaml(self, parser: SkillParser) -> None:
        content = """---
invalid: yaml: [
---
Content
"""
        skill = parser.parse_string(content)
        assert skill is None

    def test_parse_string_missing_name(self, parser: SkillParser) -> None:
        content = """---
description: No name
---

Content
"""
        skill = parser.parse_string(content)
        assert skill is None

    def test_parse_string_missing_description(self, parser: SkillParser) -> None:
        content = """---
name: no-description
---

Content
"""
        skill = parser.parse_string(content)
        assert skill is None

    def test_parse_string_empty_name(self, parser: SkillParser) -> None:
        content = """---
name: ""
description: Has empty name
---

Content
"""
        skill = parser.parse_string(content)
        assert skill is None  # Empty name is falsy

    def test_parse_string_no_content(self, parser: SkillParser) -> None:
        content = """---
name: empty
description: No content
---
"""
        skill = parser.parse_string(content)
        assert skill is not None
        assert skill.content == ""  # No markdown content after frontmatter

    def test_parse_string_trigger_patterns_as_string(self, parser: SkillParser) -> None:
        """Trigger patterns can be a single string instead of list."""
        content = """---
name: string-trigger
description: Test
trigger_patterns: pytest
---

Content
"""
        skill = parser.parse_string(content)
        assert skill is not None
        assert skill.trigger_patterns == ["pytest"]

    def test_parse_string_tags_as_string(self, parser: SkillParser) -> None:
        """Tags can be a single string instead of list."""
        content = """---
name: string-tags
description: Test
tags: python
---

Content
"""
        skill = parser.parse_string(content)
        assert skill is not None
        assert skill.tags == ["python"]

    def test_parse_string_invalid_category(self, parser: SkillParser) -> None:
        """Invalid category falls back to GENERAL."""
        content = """---
name: bad-cat
description: Test
category: nonexistent-category
---

Content
"""
        skill = parser.parse_string(content)
        assert skill is not None
        assert skill.category == SkillCategory.GENERAL

    def test_parse_string_missing_category(self, parser: SkillParser) -> None:
        """Missing category defaults to GENERAL."""
        content = """---
name: no-cat
description: Test
---

Content
"""
        skill = parser.parse_string(content)
        assert skill is not None
        assert skill.category == SkillCategory.GENERAL

    def test_parse_string_with_source_path(self, parser: SkillParser) -> None:
        """Source path is stored in metadata when provided."""
        content = """---
name: path-skill
description: Test
---

Content
"""
        skill = parser.parse_string(content, source_path=Path("/tmp/test.md"))
        assert skill is not None
        assert skill.metadata.get("source_path") == "/tmp/test.md"

    def test_parse_string_without_source_path(self, parser: SkillParser) -> None:
        """No source_path means metadata is empty."""
        content = """---
name: no-path
description: Test
---

Content
"""
        skill = parser.parse_string(content)
        assert skill is not None
        assert skill.metadata.get("source_path") is None

    def test_parse_string_all_optional_fields(self, parser: SkillParser) -> None:
        content = """---
name: full
description: Full test
category: coding-standards
trigger_patterns: [lint]
tags: [style]
language: python
framework: black
version: 1.5.0
source: lyra
---

Content
"""
        skill = parser.parse_string(content)
        assert skill is not None
        assert skill.language == "python"
        assert skill.framework == "black"
        assert skill.version == "1.5.0"
        assert skill.source == "lyra"

    def test_parse_string_default_source(self, parser: SkillParser) -> None:
        """Default source is 'ecc'."""
        content = """---
name: default-source
description: Test
---

Content
"""
        skill = parser.parse_string(content)
        assert skill is not None
        assert skill.source == "ecc"

    def test_parse_string_with_metadata(self, parser: SkillParser) -> None:
        content = """---
name: meta-skill
description: Has metadata
metadata:
  custom_key: custom_value
  nested:
    key: val
---

Content
"""
        skill = parser.parse_string(content)
        assert skill is not None
        assert skill.metadata.get("custom_key") == "custom_value"
        assert skill.metadata["nested"]["key"] == "val"

    # -- parse_file -------------------------------------------------------

    def test_parse_file_success(self, parser: SkillParser) -> None:
        content = """---
name: file-skill
description: From file
---

Content
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "skill.md"
            path.write_text(content)
            skill = parser.parse_file(path)
            assert skill is not None
            assert skill.name == "file-skill"

    def test_parse_file_nonexistent(self, parser: SkillParser) -> None:
        skill = parser.parse_file(Path("/nonexistent/file.md"))
        assert skill is None

    def test_parse_file_empty(self, parser: SkillParser) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "empty.md"
            path.write_text("")
            skill = parser.parse_file(path)
            assert skill is None

    def test_parse_file_source_path_stored(self, parser: SkillParser) -> None:
        """Source path from parse_file is stored in metadata."""
        content = """---
name: path-check
description: Check source_path
---

Content
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "path_check.md"
            path.write_text(content)
            skill = parser.parse_file(path)
            assert skill is not None
            stored_path = skill.metadata.get("source_path", "")
            # Both resolved or both original path
            assert Path(stored_path).name == "path_check.md"

    # -- parse_directory --------------------------------------------------

    def test_parse_directory(self, parser: SkillParser) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "skill1.md").write_text("---\nname: skill1\ndescription: S1\n---\n\nContent 1")
            (root / "skill2.md").write_text("---\nname: skill2\ndescription: S2\n---\n\nContent 2")

            skills = parser.parse_directory(root)
            assert len(skills) == 2
            assert "skill1" in skills
            assert "skill2" in skills

    def test_parse_directory_recursive(self, parser: SkillParser) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            sub = root / "subdir"
            sub.mkdir()
            (root / "root.md").write_text("---\nname: root\ndescription: R\n---\n\nRoot")
            (sub / "sub.md").write_text("---\nname: sub\ndescription: S\n---\n\nSub")

            skills_recursive = parser.parse_directory(root, recursive=True)
            assert len(skills_recursive) == 2

            skills_non_recursive = parser.parse_directory(root, recursive=False)
            assert len(skills_non_recursive) == 1

    def test_parse_directory_empty(self, parser: SkillParser) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skills = parser.parse_directory(Path(tmpdir))
            assert skills == {}

    def test_parse_directory_invalid_files(self, parser: SkillParser) -> None:
        """Invalid files in directory are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "valid.md").write_text("---\nname: valid\ndescription: V\n---\n\nContent")
            (root / "invalid.md").write_text("no frontmatter")
            (root / "other.txt").write_text("not a markdown file")

            skills = parser.parse_directory(root)
            assert len(skills) == 1
            assert "valid" in skills

    def test_parse_directory_no_md_files(self, parser: SkillParser) -> None:
        """Directory without .md files returns empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "file.txt").write_text("text")
            (root / "file.yaml").write_text("yaml: true")

            skills = parser.parse_directory(root)
            assert skills == {}
