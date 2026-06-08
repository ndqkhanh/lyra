"""
Tests for SkillExport — SkillPackage and SkillRegistryExport.

Covers:
  - SkillPackage creation, hashing, signing, verification
  - Serialization (to_dict, from_dict)
  - Conversion to/from Skill (from_skill, to_skill)
  - File I/O (save, load) with integrity verification
  - SkillRegistryExport creation, Wasla format, save, load
  - Edge cases: verification failure, missing fields, category mapping
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from lyra.skills.export import SkillPackage, SkillRegistryExport
from lyra.skills.skill import Skill, SkillCategory


class TestSkillPackage:
    """Tests for SkillPackage — individual skill export/import."""

    # -- Creation and defaults -------------------------------------------

    def test_create_minimal(self) -> None:
        pkg = SkillPackage(
            name="test-skill",
            version="1.0.0",
            description="A test skill",
            content="Test content",
            category="general",
        )
        assert pkg.name == "test-skill"
        assert pkg.version == "1.0.0"
        assert pkg.description == "A test skill"
        assert pkg.content == "Test content"
        assert pkg.category == "general"
        assert pkg.trigger_patterns == []
        assert pkg.tags == []
        assert pkg.dependencies == []
        assert pkg.compatible_agents == ["lyra"]
        assert pkg.author == ""
        assert pkg.license == "MIT"
        assert pkg.source == "lyra"
        assert pkg.integrity_sha256 == ""

    def test_create_full(self) -> None:
        pkg = SkillPackage(
            name="full-skill",
            version="2.0.0",
            description="Full skill",
            content="Full content",
            category="coding-standards",
            trigger_patterns=["lint", "format"],
            tags=["python", "style"],
            dependencies=["base-skill"],
            compatible_agents=["lyra", "claude"],
            author="Test Author",
            license="Apache-2.0",
            source="ecc",
        )
        assert pkg.trigger_patterns == ["lint", "format"]
        assert pkg.tags == ["python", "style"]
        assert pkg.dependencies == ["base-skill"]
        assert pkg.compatible_agents == ["lyra", "claude"]
        assert pkg.author == "Test Author"
        assert pkg.license == "Apache-2.0"
        assert pkg.source == "ecc"

    def test_created_at_auto_set(self) -> None:
        pkg = SkillPackage(
            name="test", version="1", description="d", content="c", category="g"
        )
        assert "T" in pkg.created_at  # ISO format

    # -- Integrity hash ---------------------------------------------------

    def test_compute_hash_deterministic(self) -> None:
        pkg_a = SkillPackage(
            name="test", version="1", description="d", content="c", category="g"
        )
        pkg_b = SkillPackage(
            name="test", version="1", description="d", content="c", category="g"
        )
        assert pkg_a.compute_hash() == pkg_b.compute_hash()

    def test_compute_hash_changes_with_content(self) -> None:
        pkg_a = SkillPackage(
            name="test", version="1", description="d", content="c", category="g"
        )
        pkg_b = SkillPackage(
            name="test", version="1", description="d", content="different", category="g"
        )
        assert pkg_a.compute_hash() != pkg_b.compute_hash()

    def test_compute_hash_sorts_lists(self) -> None:
        """Hash is computed over sorted lists for determinism."""
        pkg_a = SkillPackage(
            name="test", version="1", description="d", content="c", category="g",
            trigger_patterns=["b", "a"],
        )
        pkg_b = SkillPackage(
            name="test", version="1", description="d", content="c", category="g",
            trigger_patterns=["a", "b"],
        )
        assert pkg_a.compute_hash() == pkg_b.compute_hash()

    # -- Sign and verify --------------------------------------------------

    def test_sign_sets_integrity(self) -> None:
        pkg = SkillPackage(
            name="test", version="1", description="d", content="c", category="g"
        )
        assert pkg.integrity_sha256 == ""
        pkg.sign()
        assert pkg.integrity_sha256 != ""

    def test_verify_passes_after_sign(self) -> None:
        pkg = SkillPackage(
            name="test", version="1", description="d", content="c", category="g"
        )
        pkg.sign()
        assert pkg.verify() is True

    def test_verify_fails_on_content_tamper(self) -> None:
        pkg = SkillPackage(
            name="test", version="1", description="d", content="original", category="g"
        )
        pkg.sign()
        pkg.content = "tampered"
        assert pkg.verify() is False

    def test_verify_fails_on_name_tamper(self) -> None:
        pkg = SkillPackage(
            name="test", version="1", description="d", content="c", category="g"
        )
        pkg.sign()
        pkg.name = "tampered"
        assert pkg.verify() is False

    def test_verify_no_hash(self) -> None:
        """Unsigned package has empty hash, so verification compares '' to hash."""
        pkg = SkillPackage(
            name="test", version="1", description="d", content="c", category="g"
        )
        assert pkg.integrity_sha256 == ""
        assert pkg.verify() is False  # '' != actual_hash

    # -- Serialization ----------------------------------------------------

    def test_to_dict(self) -> None:
        pkg = SkillPackage(
            name="test", version="1.0.0", description="d", content="c", category="g",
            trigger_patterns=["t"], tags=["tag"],
        )
        pkg.sign()
        d = pkg.to_dict()
        assert d["name"] == "test"
        assert d["version"] == "1.0.0"
        assert d["description"] == "d"
        assert d["content"] == "c"
        assert d["category"] == "g"
        assert d["trigger_patterns"] == ["t"]
        assert d["tags"] == ["tag"]
        assert d["integrity_sha256"] == pkg.integrity_sha256
        assert d["source"] == "lyra"
        assert d["author"] == ""

    def test_from_dict(self) -> None:
        data = {
            "name": "imported",
            "version": "2.0.0",
            "description": "Imported skill",
            "content": "Imported content",
            "category": "tdd-testing",
            "trigger_patterns": ["test"],
            "tags": ["testing"],
            "dependencies": [],
            "compatible_agents": ["lyra"],
            "author": "Someone",
            "license": "MIT",
            "created_at": "2025-01-01T00:00:00",
            "integrity_sha256": "",
            "source": "ecc",
        }
        pkg = SkillPackage.from_dict(data)
        assert pkg.name == "imported"
        assert pkg.version == "2.0.0"
        assert pkg.description == "Imported skill"
        assert pkg.category == "tdd-testing"
        assert pkg.source == "ecc"
        assert pkg.author == "Someone"

    def test_from_dict_minimal(self) -> None:
        """from_dict works with only required fields."""
        data = {
            "name": "minimal",
            "version": "1",
            "description": "",
            "content": "content",
        }
        pkg = SkillPackage.from_dict(data)
        assert pkg.name == "minimal"
        assert pkg.category == "general"
        assert pkg.trigger_patterns == []
        assert pkg.author == ""
        assert pkg.source == "unknown"

    def test_roundtrip_to_from_dict(self) -> None:
        pkg = SkillPackage(
            name="rt", version="1", description="d", content="c", category="api-design",
            trigger_patterns=["api"], tags=["api"],
        )
        pkg.sign()
        reconstructed = SkillPackage.from_dict(pkg.to_dict())
        assert reconstructed.name == pkg.name
        assert reconstructed.category == pkg.category
        assert reconstructed.verify() is True

    # -- Conversion to/from Skill ----------------------------------------

    def test_from_skill(self) -> None:
        skill = Skill(
            name="python-testing",
            description="Python testing patterns",
            content="Use pytest",
            category=SkillCategory.TDD_TESTING,
            trigger_patterns=["test", "pytest"],
            tags=["python", "testing"],
            version="2.0.0",
            dependencies=["base"],
        )
        pkg = SkillPackage.from_skill(skill)
        assert pkg.name == "python-testing"
        assert pkg.version == "2.0.0"
        assert pkg.description == "Python testing patterns"
        assert pkg.content == "Use pytest"
        assert pkg.category == "tdd-testing"
        assert pkg.trigger_patterns == ["test", "pytest"]
        assert pkg.tags == ["python", "testing"]
        assert pkg.dependencies == ["base"]
        assert pkg.source == "lyra"
        # from_skill calls sign automatically
        assert pkg.integrity_sha256 != ""

    def test_from_skill_general_category(self) -> None:
        skill = Skill(
            name="generic", description="d", content="c",
        )
        pkg = SkillPackage.from_skill(skill)
        assert pkg.category == "general"

    def test_to_skill(self) -> None:
        pkg = SkillPackage(
            name="from-pkg", version="3.0.0", description="From package",
            content="Package content", category="coding-standards",
            trigger_patterns=["lint"], tags=["style"],
            dependencies=["dep1"],
            source="ecc",
        )
        skill = pkg.to_skill()
        assert skill.name == "from-pkg"
        assert skill.version == "3.0.0"
        assert skill.description == "From package"
        assert skill.content == "Package content"
        assert skill.category == SkillCategory.CODING_STANDARDS
        assert skill.trigger_patterns == ["lint"]
        assert skill.tags == ["style"]
        assert skill.dependencies == ["dep1"]
        assert skill.source == "ecc"

    def test_to_skill_unknown_category(self) -> None:
        """Unknown category falls back to GENERAL."""
        pkg = SkillPackage(
            name="s", version="1", description="d", content="c", category="nonexistent",
        )
        skill = pkg.to_skill()
        assert skill.category == SkillCategory.GENERAL

    def test_to_skill_default_version(self) -> None:
        pkg = SkillPackage(
            name="s", version="1", description="d", content="c", category="g",
        )
        skill = pkg.to_skill()
        assert skill.version == "1"

    # -- File I/O ---------------------------------------------------------

    def test_save_and_load(self) -> None:
        pkg = SkillPackage(
            name="saved", version="1", description="Test save",
            content="Content to save", category="general",
        )
        pkg.sign()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "skill.json"
            pkg.save(path)

            # Verify file exists and contains JSON
            assert path.exists()
            raw = json.loads(path.read_text())
            assert raw["name"] == "saved"

            # Load and verify
            loaded = SkillPackage.load(path)
            assert loaded.name == "saved"
            assert loaded.content == "Content to save"
            assert loaded.verify() is True

    def test_load_integrity_failure(self) -> None:
        pkg = SkillPackage(
            name="tampered", version="1", description="d", content="c", category="g",
        )
        pkg.sign()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "skill.json"
            pkg.save(path)

            # Tamper with the file
            raw = json.loads(path.read_text())
            raw["content"] = "tampered"
            path.write_text(json.dumps(raw))

            # Load should fail integrity check
            with pytest.raises(ValueError, match="Integrity check failed"):
                SkillPackage.load(path)

    def test_save_calls_sign(self) -> None:
        """save() calls sign() to ensure integrity hash is set."""
        pkg = SkillPackage(
            name="unsigned", version="1", description="d", content="c", category="g",
        )
        assert pkg.integrity_sha256 == ""

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "skill.json"
            pkg.save(path)

            loaded = SkillPackage.load(path)
            assert loaded.verify() is True


class TestSkillRegistryExport:
    """Tests for SkillRegistryExport — bulk export/import."""

    def test_create_empty(self) -> None:
        reg = SkillRegistryExport()
        assert reg.name == "lyra-skills"
        assert reg.version == "1.0.0"
        assert reg.skills == []

    def test_add_and_to_wasla_format(self) -> None:
        reg = SkillRegistryExport()
        pkg = SkillPackage(
            name="test", version="1", description="d", content="c", category="g",
        )
        reg.add(pkg)
        data = reg.to_wasla_format()

        assert data["format"] == "wasla/v1"
        assert data["registry"] == "lyra-skills"
        assert len(data["skills"]) == 1
        assert data["skills"][0]["name"] == "test"

    def test_save_and_load(self) -> None:
        reg = SkillRegistryExport(name="test-reg")
        reg.add(
            SkillPackage(
                name="skill-a", version="1", description="A", content="Content A",
                category="general",
            )
        )
        reg.add(
            SkillPackage(
                name="skill-b", version="2", description="B", content="Content B",
                category="tdd-testing",
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "registry.json"
            reg.save(path)

            loaded = SkillRegistryExport.load(path)
            assert loaded.name == "test-reg"
            assert len(loaded.skills) == 2
            loaded_names = {s.name for s in loaded.skills}
            assert "skill-a" in loaded_names
            assert "skill-b" in loaded_names

    def test_load_defaults(self) -> None:
        """Load uses sensible defaults for missing fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "minimal.json"
            path.write_text(
                json.dumps({
                    "format": "wasla/v1",
                    "skills": [
                        {
                            "name": "s",
                            "version": "1",
                            "description": "d",
                            "content": "c",
                        }
                    ],
                })
            )
            loaded = SkillRegistryExport.load(path)
            assert loaded.name == "imported"
            assert loaded.version == "1.0.0"

    def test_custom_name_version(self) -> None:
        reg = SkillRegistryExport(name="custom", version="2.0.0")
        assert reg.name == "custom"
        assert reg.version == "2.0.0"

    def test_to_wasla_with_multiple_skills(self) -> None:
        reg = SkillRegistryExport(name="multi")
        for i in range(5):
            pkg = SkillPackage(
                name=f"skill-{i}", version="1.0.0",
                description=f"Skill {i}", content=f"Content {i}",
                category="general",
            )
            reg.add(pkg)
        data = reg.to_wasla_format()
        assert len(data["skills"]) == 5
        assert data["skills"][0]["name"] == "skill-0"
        assert data["skills"][4]["name"] == "skill-4"
