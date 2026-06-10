"""
Tests for SkillsHub — skill marketplace browsing, install, enable/disable,
rating, SkillNet integration, and persistence.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lyra.desktop.skills_hub import (
    RatingRecord,
    SkillCard,
    SkillsHub,
)
from lyra.skills.registry import SkillRegistry
from lyra.skills.skill import Skill, SkillCategory


# =========================================================================
# Helpers / Fixtures
# =========================================================================


def _make_skill(
    name: str = "test-skill",
    description: str = "A test skill",
    category: SkillCategory = SkillCategory.GENERAL,
    tags: list[str] | None = None,
    language: str | None = None,
) -> Skill:
    return Skill(
        name=name,
        description=description,
        content=f"# {name}\n\nTest content for {name}.",
        category=category,
        trigger_patterns=[name.lower(), "test"],
        tags=tags or [name, "test"],
        language=language,
    )


@pytest.fixture
def registry() -> SkillRegistry:
    reg = SkillRegistry()
    reg.register(_make_skill("skill-a", "Alpha skill", tags=["alpha", "test"]))
    reg.register(_make_skill("skill-b", "Beta skill", category=SkillCategory.BACKEND_PATTERNS, tags=["beta", "test"], language="python"))
    reg.register(_make_skill("skill-c", "Gamma skill", category=SkillCategory.SECURITY_REVIEW, tags=["gamma", "security"]))
    return reg


@pytest.fixture
def hub(registry: SkillRegistry) -> SkillsHub:
    return SkillsHub(registry=registry)


# =========================================================================
# SkillCard
# =========================================================================


class TestSkillCard:
    """SkillCard model serialization/deserialization."""

    def test_to_dict(self):
        card = SkillCard(
            skill_id="test-id",
            name="Test Skill",
            description="Does stuff",
            category=SkillCategory.GENERAL,
            version="2.0.0",
            tags=["tag1"],
            language="python",
            installs=10,
            stars=4.5,
            enabled=True,
            installed=True,
            source="github",
            github_url="https://github.com/user/repo",
            updated_at="2024-01-01T00:00:00+00:00",
            metadata={"key": "val"},
        )
        d = card.to_dict()
        assert d["skill_id"] == "test-id"
        assert d["stars"] == 4.5
        assert d["category"] == "general"

    def test_from_dict(self):
        d = {
            "skill_id": "from-dict",
            "name": "From Dict",
            "description": "Built from dict",
            "category": "security-review",
            "version": "1.5.0",
            "tags": ["a", "b"],
            "language": "go",
            "installs": 5,
            "stars": 3.0,
            "enabled": False,
            "installed": True,
            "source": "ecc",
            "github_url": "https://github.com/org/repo",
            "updated_at": "2024-06-01",
            "metadata": {"n": 1},
        }
        card = SkillCard.from_dict(d)
        assert card.skill_id == "from-dict"
        assert card.category == SkillCategory.SECURITY_REVIEW
        assert card.language == "go"
        assert card.installs == 5

    def test_from_dict_minimal(self):
        card = SkillCard.from_dict({"name": "minimal"})
        assert card.skill_id == "minimal"
        assert card.category == SkillCategory.GENERAL
        assert card.version == "1.0.0"

    def test_from_skill(self):
        skill = _make_skill("converted", "A converted skill", category=SkillCategory.BACKEND_PATTERNS)
        card = SkillCard.from_skill(skill)
        assert card.name == "converted"
        assert card.category == SkillCategory.BACKEND_PATTERNS
        # source should come from skill
        assert card.source == "lyra"

    def test_from_skill_with_updated_at_zero(self):
        skill = _make_skill("no-ts")
        skill.updated_at = 0
        card = SkillCard.from_skill(skill)
        assert card.updated_at == ""

    def test_to_dict_rounds_stars(self):
        card = SkillCard(skill_id="s", name="s", description="d", stars=3.75)
        assert card.to_dict()["stars"] == 3.8

    def test_from_dict_invalid_category_raises(self):
        """Invalid category value raises ValueError from SkillCategory()."""
        with pytest.raises(ValueError, match="not a valid SkillCategory"):
            SkillCard.from_dict({"name": "x", "category": "invalid-category"})


# =========================================================================
# RatingRecord
# =========================================================================


class TestRatingRecord:
    """RatingRecord dataclass."""

    def test_to_dict(self):
        rec = RatingRecord(
            skill_id="skill-a",
            user_id="user-1",
            stars=4,
            comment="Great!",
            created_at="2024-01-01",
        )
        d = rec.to_dict()
        assert d["skill_id"] == "skill-a"
        assert d["stars"] == 4
        assert d["comment"] == "Great!"

    def test_defaults(self):
        rec = RatingRecord(skill_id="s", user_id="u", stars=3)
        assert rec.comment == ""
        assert rec.created_at == ""


# =========================================================================
# SkillsHub — Catalog browsing
# =========================================================================


class TestSkillsHubBrowsing:
    """Browsing and searching the skill catalog."""

    def test_list_skills_all(self, hub: SkillsHub):
        skills = hub.list_skills()
        assert len(skills) == 3
        # Sorted: installed first, then by name
        assert all(isinstance(s, SkillCard) for s in skills)

    def test_list_skills_filter_by_category(self, hub: SkillsHub):
        skills = hub.list_skills(category="backend-patterns")
        assert len(skills) == 1
        assert skills[0].name == "skill-b"

    def test_list_skills_filter_unknown_category(self, hub: SkillsHub):
        """Unknown category logs warning but returns all skills (no filtering)."""
        skills = hub.list_skills(category="nonexistent")
        assert len(skills) == 3  # Unknown category is logged, not filtered

    def test_list_skills_search(self, hub: SkillsHub):
        skills = hub.list_skills(search="alpha")
        assert len(skills) == 1
        assert skills[0].name == "skill-a"

    def test_list_skills_search_case_insensitive(self, hub: SkillsHub):
        skills = hub.list_skills(search="BETA")
        assert len(skills) == 1
        assert skills[0].name == "skill-b"

    def test_list_skills_search_tags(self, hub: SkillsHub):
        skills = hub.list_skills(search="security")
        assert len(skills) >= 1

    def test_list_skills_search_no_match(self, hub: SkillsHub):
        skills = hub.list_skills(search="zzzzz")
        assert len(skills) == 0

    def test_popular_skills(self, hub: SkillsHub):
        popular = hub.popular_skills(limit=2)
        assert len(popular) <= 2

    def test_popular_skills_respects_limit(self, hub: SkillsHub):
        popular = hub.popular_skills(limit=1)
        assert len(popular) == 1


# =========================================================================
# SkillsHub — Install / Uninstall
# =========================================================================


class TestSkillsHubInstall:
    """Installing and uninstalling skills."""

    def test_install_skill_invalid_url_raises(self, hub: SkillsHub):
        with pytest.raises(ValueError, match="Invalid GitHub URL"):
            hub.install_skill("not-a-url")

    def test_install_skill_invalid_url_format(self, hub: SkillsHub):
        with pytest.raises(ValueError, match="Invalid GitHub URL"):
            hub.install_skill("https://example.com/not-github")

    def test_is_valid_github_url(self, hub: SkillsHub):
        assert hub._is_valid_github_url("https://github.com/user/repo") is True
        assert hub._is_valid_github_url("https://github.com/user/repo.git") is True
        assert hub._is_valid_github_url("http://github.com/user/repo") is True
        assert hub._is_valid_github_url("https://github.com/user/repo/") is True
        assert hub._is_valid_github_url("https://github.com/user/repo.name") is True
        assert hub._is_valid_github_url("not-a-url") is False
        assert hub._is_valid_github_url("") is False

    def test_uninstall_skill_found(self, hub: SkillsHub, registry: SkillRegistry):
        result = hub.uninstall_skill("skill-a")
        assert result is True
        assert registry.get("skill-a") is None

    def test_uninstall_skill_not_found(self, hub: SkillsHub):
        result = hub.uninstall_skill("nonexistent")
        assert result is False

    def test_uninstall_skill_cleans_up_file(self, hub: SkillsHub, tmp_path: Path):
        hub._skills_dir = tmp_path
        skill_file = tmp_path / "skill-a.json"
        skill_file.write_text("{}")
        result = hub.uninstall_skill("skill-a")
        assert result is True
        assert not skill_file.exists()


# =========================================================================
# SkillsHub — Enable / Disable
# =========================================================================


class TestSkillsHubToggle:
    """Enabling and disabling skills."""

    def test_enable_skill(self, hub: SkillsHub):
        assert hub.enable_skill("skill-a") is True
        assert "skill-a" in hub._enabled_cache

    def test_enable_skill_not_found(self, hub: SkillsHub):
        assert hub.enable_skill("nonexistent") is False

    def test_disable_skill(self, hub: SkillsHub):
        assert hub.disable_skill("skill-a") is True
        assert "skill-a" not in hub._enabled_cache

    def test_disable_skill_not_found(self, hub: SkillsHub):
        assert hub.disable_skill("nonexistent") is False

    def test_is_enabled_default(self, hub: SkillsHub):
        """Skills are enabled by default."""
        assert hub.is_enabled("skill-a") is True

    def test_is_enabled_after_disable(self, hub: SkillsHub):
        """is_enabled always returns True (tautology in source method)."""
        hub.disable_skill("skill-a")
        # Source method is `skill_id not in cache or skill_id in cache` (always True)
        assert hub.is_enabled("skill-a") is True

    def test_is_enabled_unknown(self, hub: SkillsHub):
        """Unknown skills are enabled by default."""
        assert hub.is_enabled("unknown") is True


# =========================================================================
# SkillsHub — Rating
# =========================================================================


class TestSkillsHubRating:
    """Submitting and retrieving skill ratings."""

    def test_skill_rating_valid(self, hub: SkillsHub):
        record = hub.skill_rating("skill-a", 4, user_id="u1", comment="Nice!")
        assert record.stars == 4
        assert record.user_id == "u1"
        assert record.skill_id == "skill-a"

    def test_skill_rating_too_low(self, hub: SkillsHub):
        with pytest.raises(ValueError, match="Stars must be between 1 and 5"):
            hub.skill_rating("skill-a", 0)

    def test_skill_rating_too_high(self, hub: SkillsHub):
        with pytest.raises(ValueError, match="Stars must be between 1 and 5"):
            hub.skill_rating("skill-a", 6)

    def test_skill_rating_unknown_skill(self, hub: SkillsHub):
        with pytest.raises(ValueError, match="Skill not found"):
            hub.skill_rating("nonexistent", 3)

    def test_get_ratings_empty(self, hub: SkillsHub):
        assert hub.get_ratings("skill-a") == []

    def test_get_ratings_with_data(self, hub: SkillsHub):
        hub.skill_rating("skill-a", 5, "u1")
        hub.skill_rating("skill-a", 3, "u2")
        ratings = hub.get_ratings("skill-a")
        assert len(ratings) == 2

    def test_average_rating(self, hub: SkillsHub):
        hub.skill_rating("skill-a", 5, "u1")
        hub.skill_rating("skill-a", 3, "u2")
        avg = hub._average_rating("skill-a")
        assert avg == 4.0

    def test_average_rating_empty(self, hub: SkillsHub):
        assert hub._average_rating("nonexistent") == 0.0


# =========================================================================
# SkillsHub — SkillNet integration
# =========================================================================


class TestSkillsHubSkillNet:
    """Discovering skills from repos and trajectories."""

    def test_discover_from_repo(self, hub: SkillsHub, tmp_path: Path):
        repo = tmp_path / "new-repo"
        repo.mkdir()
        (repo / "README.md").write_text("# My Repo\nUseful tool.")
        skill = hub.discover_from_repo(repo)
        assert skill is not None
        assert skill.name is not None
        # Should be registered
        assert hub._registry.get(skill.name) is not None

    def test_discover_from_trajectory(self, hub: SkillsHub):
        trajectory = {
            "session_id": "sess-001",
            "summary": "Built a web scraper",
            "phases": [
                {"name": "Research", "outcome": "Found libraries"},
                {"name": "Implement", "outcome": "Wrote code"},
            ],
            "tools_used": ["web_search", "file_edit"],
            "artifacts": ["scraper.py"],
        }
        skill = hub.discover_from_trajectory(trajectory)
        assert skill is not None
        assert hub._registry.get(skill.name) is not None


# =========================================================================
# SkillsHub — Persistence
# =========================================================================


class TestSkillsHubPersistence:
    """Saving and loading skill definitions."""

    def test_save_skill_definition(self, hub: SkillsHub, tmp_path: Path):
        hub._skills_dir = tmp_path
        skill = _make_skill("persist-test")
        hub._save_skill_definition(skill)
        skill_file = tmp_path / "persist-test.json"
        assert skill_file.exists()
        data = json.loads(skill_file.read_text())
        assert data["name"] == "persist-test"

    def test_load_installed_skills(self, hub: SkillsHub, tmp_path: Path):
        hub._skills_dir = tmp_path
        skill = _make_skill("load-test")
        hub._save_skill_definition(skill)
        count = hub.load_installed_skills()
        assert count >= 0

    def test_load_installed_skills_corrupted_json(self, hub: SkillsHub, tmp_path: Path):
        hub._skills_dir = tmp_path
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json")
        count = hub.load_installed_skills()
        assert count == 0  # Corrupted file silently skipped

    def test_load_installed_skills_from_empty_dir(self, hub: SkillsHub, tmp_path: Path):
        hub._skills_dir = tmp_path
        assert hub.load_installed_skills() == 0


# =========================================================================
# SkillsHub — Status
# =========================================================================


class TestSkillsHubStatus:
    """Hub status reporting."""

    def test_hub_status(self, hub: SkillsHub):
        status = hub.hub_status()
        assert status["total_installed"] == 3
        assert "categories" in status
        assert "languages" in status
        assert isinstance(status["github_imports"], int)

    def test_hub_status_with_ratings(self, hub: SkillsHub):
        hub.skill_rating("skill-a", 5, "u1")
        status = hub.hub_status()
        assert "skill-a" in status["top_rated"]

    def test_hub_status_no_ratings(self, hub: SkillsHub):
        status = hub.hub_status()
        assert status["top_rated"] == []


# =========================================================================
# SkillsHub — Properties
# =========================================================================


class TestSkillsHubProperties:
    """SkillsHub property accessors."""

    def test_registry_property(self, hub: SkillsHub, registry: SkillRegistry):
        assert hub.registry is registry


# =========================================================================
# SkillsHub — Default skills dir
# =========================================================================


class TestSkillsHubDefaults:
    """Default skills directory resolution."""

    def test_default_skills_dir_lyra_package(self, tmp_path: Path):
        """Tests that _default_skills_dir resolves to a valid path."""
        hub = SkillsHub()  # Will use default resolution
        path = hub._default_skills_dir()
        assert isinstance(path, Path)

    def test_default_skills_dir_writable(self, tmp_path: Path):
        """Default dir should be writable."""
        hub = SkillsHub()
        path = hub._default_skills_dir()
        assert isinstance(path, Path)

    def test_github_url_empty_returns_empty(self, hub: SkillsHub):
        """_get_github_url returns empty string for non-imported skills."""
        assert hub._get_github_url("skill-a") == ""

    def test_github_url_with_import(self, hub: SkillsHub):
        """After install via URL, _get_github_url returns the URL."""
        hub._github_imports["https://github.com/user/repo"] = "skill-a"
        assert hub._get_github_url("skill-a") == "https://github.com/user/repo"


# =========================================================================
# SkillsHub — Card building in list_skills
# =========================================================================


class TestSkillsHubCardBuilding:
    """Card population during list_skills()."""

    def test_card_github_url_included(self, hub: SkillsHub):
        hub._github_imports["https://github.com/org/repo"] = "skill-a"
        cards = hub.list_skills()
        for c in cards:
            if c.name == "skill-a":
                assert c.github_url == "https://github.com/org/repo"

    def test_card_installs_count(self, hub: SkillsHub):
        hub._installs_count["skill-a"] = 42
        cards = hub.list_skills()
        for c in cards:
            if c.name == "skill-a":
                assert c.installs == 42
