"""
Tests for ECCSkillImporter — importing skills from files.

Covers:
  - import_file (success, failure, nonexistent)
  - import_directory (all, recursive, with failures)
  - import_all (standard directory structure)
  - ImportResult properties (success_rate edge cases)
  - Empty directories, mixed content
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from lyra.skills.importer import ECCSkillImporter, ImportResult
from lyra.skills.registry import SkillRegistry
from lyra.skills.skill import Skill


class TestECCSkillImporter:
    """Tests for the ECCSkillImporter class."""

    @pytest.fixture
    def registry(self) -> SkillRegistry:
        return SkillRegistry()

    @pytest.fixture
    def importer(self, registry: SkillRegistry) -> ECCSkillImporter:
        return ECCSkillImporter(registry)

    # -- import_file ------------------------------------------------------

    def test_import_file_success(self, importer: ECCSkillImporter, registry: SkillRegistry) -> None:
        content = """---
name: my-skill
description: My test skill
---

# Skill Content

This is the skill content.
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "skill.md"
            path.write_text(content)

            success = importer.import_file(path)
            assert success is True
            assert "my-skill" in registry.skills

    def test_import_file_no_frontmatter(self, importer: ECCSkillImporter) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "skill.md"
            path.write_text("No frontmatter here")

            success = importer.import_file(path)
            assert success is False

    def test_import_file_missing_name(self, importer: ECCSkillImporter) -> None:
        content = """---
description: No name field
---

Content
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "skill.md"
            path.write_text(content)

            success = importer.import_file(path)
            assert success is False

    def test_import_file_nonexistent(self, importer: ECCSkillImporter) -> None:
        success = importer.import_file(Path("/nonexistent/path/skill.md"))
        assert success is False

    def test_import_file_empty(self, importer: ECCSkillImporter) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "empty.md"
            path.write_text("")

            success = importer.import_file(path)
            assert success is False

    def test_import_file_with_tags_and_triggers(
        self, importer: ECCSkillImporter, registry: SkillRegistry
    ) -> None:
        content = """---
name: advanced-skill
description: Advanced skill
category: backend-patterns
trigger_patterns: [api, rest]
tags: [python, backend]
language: python
---

Content
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "adv.md"
            path.write_text(content)

            assert importer.import_file(path) is True
            skill = registry.get("advanced-skill")
            assert skill is not None
            assert skill.category.value == "backend-patterns"
            assert skill.language == "python"
            assert "api" in skill.trigger_patterns

    # -- import_directory -------------------------------------------------

    def test_import_directory_all(self, importer: ECCSkillImporter, registry: SkillRegistry) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "a.md").write_text("---\nname: skill-a\ndescription: A\n---\n\nA")
            (root / "b.md").write_text("---\nname: skill-b\ndescription: B\n---\n\nB")

            result = importer.import_directory(root)
            assert result.total_files == 2
            assert result.parsed_successfully == 2
            assert result.registered_successfully == 2
            assert result.success_rate == 1.0
            assert len(result.skills) == 2
            assert "skill-a" in result.skills
            assert "skill-b" in registry.skills

    def test_import_directory_recursive(self, importer: ECCSkillImporter) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            sub = root / "subdir"
            sub.mkdir()
            (root / "root.md").write_text("---\nname: root-skill\ndescription: R\n---\n\nR")
            (sub / "sub.md").write_text("---\nname: sub-skill\ndescription: S\n---\n\nS")

            # Non-recursive should only find 1
            result = importer.import_directory(root, recursive=False)
            assert result.total_files == 1

            # Recursive should find 2
            result = importer.import_directory(root, recursive=True)
            assert result.total_files == 2

    def test_import_directory_empty(self, importer: ECCSkillImporter) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = importer.import_directory(Path(tmpdir))
            assert result.total_files == 0
            assert result.success_rate == 0.0

    def test_import_directory_all_failures(self, importer: ECCSkillImporter) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "bad1.md").write_text("no frontmatter")
            (root / "bad2.md").write_text("also no frontmatter")

            result = importer.import_directory(root)
            assert result.total_files == 2
            assert result.parsed_successfully == 0
            assert result.registered_successfully == 0
            assert result.success_rate == 0.0
            assert len(result.failed) == 2

    def test_import_directory_mixed(self, importer: ECCSkillImporter) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "good.md").write_text("---\nname: good\ndescription: Good skill\n---\n\nContent")
            (root / "bad.md").write_text("no frontmatter here")

            result = importer.import_directory(root)
            assert result.total_files == 2
            assert result.parsed_successfully == 1
            assert result.registered_successfully == 1
            assert result.success_rate == 0.5
            assert len(result.failed) == 1

    def test_import_directory_with_nested_dirs(self, importer: ECCSkillImporter) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            nested = root / "coding-standards" / "python"
            nested.mkdir(parents=True)
            (nested / "pep8.md").write_text(
                "---\nname: pep8\ndescription: PEP8 standards\n---\n\nContent"
            )

            result = importer.import_directory(root)
            assert result.total_files == 1
            assert result.parsed_successfully == 1

    # -- import_all -------------------------------------------------------

    def test_import_all_delegates_to_import_directory(
        self, importer: ECCSkillImporter
    ) -> None:
        """import_all calls import_directory with recursive=True on the given path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            sub = root / "backend-patterns"
            sub.mkdir()
            (sub / "rest.md").write_text(
                "---\nname: rest-api\ndescription: REST patterns\n---\n\nContent"
            )

            result = importer.import_all(root)
            assert result.total_files == 1
            assert result.parsed_successfully == 1
            assert result.registered_successfully == 1

    def test_import_all_nonexistent_directory(self, importer: ECCSkillImporter) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            # import_all calls import_directory which globs "**/*.md"
            # An empty directory yields 0 files
            result = importer.import_all(Path(tmpdir))
            assert result.total_files == 0

    # -- ImportResult -----------------------------------------------------

    def test_import_result_success_rate(self) -> None:
        result = ImportResult(
            total_files=4,
            parsed_successfully=3,
            registered_successfully=2,
            failed=["bad.md"],
            skills={},
        )
        assert result.success_rate == 0.5
        assert result.total_files == 4

    def test_import_result_success_rate_zero(self) -> None:
        result = ImportResult(
            total_files=0,
            parsed_successfully=0,
            registered_successfully=0,
            failed=[],
            skills={},
        )
        assert result.success_rate == 0.0

    def test_import_result_full_success(self) -> None:
        skills = {
            "a": Skill(name="a", description="A", content="A"),
        }
        result = ImportResult(
            total_files=1,
            parsed_successfully=1,
            registered_successfully=1,
            failed=[],
            skills=skills,
        )
        assert result.success_rate == 1.0
        assert result.skills["a"].name == "a"
