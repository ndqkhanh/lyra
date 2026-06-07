"""
Skills Hub — browsable skill marketplace for the Lyra desktop.

Provides catalog browsing, search, one-click GitHub install, enable/disable
toggling, user ratings, and popularity ranking. Integrates with the Phase 1
SkillNet auto-creator for discovering and importing new skills.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lyra.skills.registry import SkillRegistry
from lyra.skills.skill import Skill, SkillCategory
from lyra.skills.skillnet import SkillNetAutoCreator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class SkillCard:
    """A browsable skill listing for the skills hub marketplace.

    Attributes:
        skill_id: Unique identifier for the skill.
        name: Human-readable skill name.
        description: Short description of what the skill does.
        category: Skill category.
        version: Semantic version string.
        tags: Searchable tags.
        language: Primary programming language (or None).
        installs: Number of times this skill has been installed.
        stars: Average user rating (0.0 — 5.0).
        enabled: Whether the skill is currently enabled.
        installed: Whether the skill is installed locally.
        source: Origin ("lyra", "ecc", "github").
        github_url: GitHub repository URL (if applicable).
        updated_at: ISO-formatted last-updated timestamp.
        metadata: Arbitrary additional metadata.
    """

    skill_id: str
    name: str
    description: str
    category: SkillCategory = SkillCategory.GENERAL
    version: str = "1.0.0"
    tags: list[str] = field(default_factory=list)
    language: str | None = None
    installs: int = 0
    stars: float = 0.0
    enabled: bool = True
    installed: bool = False
    source: str = "lyra"
    github_url: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize card to dictionary."""
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "version": self.version,
            "tags": self.tags,
            "language": self.language,
            "installs": self.installs,
            "stars": round(self.stars, 1),
            "enabled": self.enabled,
            "installed": self.installed,
            "source": self.source,
            "github_url": self.github_url,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillCard:
        """Create card from dictionary."""
        cat_val = data.get("category", "general")
        return cls(
            skill_id=data.get("skill_id", data.get("name", "unknown")),
            name=data.get("name", "unknown"),
            description=data.get("description", ""),
            category=SkillCategory(cat_val) if isinstance(cat_val, str) else cat_val,
            version=data.get("version", "1.0.0"),
            tags=data.get("tags", []),
            language=data.get("language"),
            installs=data.get("installs", 0),
            stars=data.get("stars", 0.0),
            enabled=data.get("enabled", True),
            installed=data.get("installed", False),
            source=data.get("source", "lyra"),
            github_url=data.get("github_url", ""),
            updated_at=data.get("updated_at", ""),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_skill(cls, skill: Skill) -> SkillCard:
        """Build a SkillCard from a ``lyra.skills.skill.Skill`` instance."""
        return cls(
            skill_id=skill.name,
            name=skill.name,
            description=skill.description,
            category=skill.category,
            version=skill.version,
            tags=list(skill.tags),
            language=skill.language,
            source=skill.source,
            metadata=skill.metadata,
            updated_at=datetime.fromtimestamp(skill.updated_at, tz=timezone.utc).isoformat()
            if skill.updated_at
            else "",
        )


@dataclass
class RatingRecord:
    """A single user rating for a skill.

    Attributes:
        skill_id: The skill being rated.
        user_id: The user who submitted the rating.
        stars: Rating value (1 — 5).
        comment: Optional review comment.
        created_at: ISO-formatted timestamp.
    """

    skill_id: str
    user_id: str
    stars: int
    comment: str = ""
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "user_id": self.user_id,
            "stars": self.stars,
            "comment": self.comment,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# SkillsHub
# ---------------------------------------------------------------------------


class SkillsHub:
    """Browsable skill marketplace for discovering, installing, enabling, and
    rating skills.

    Integrates with:
    - ``SkillRegistry`` for managing the installed skill set.
    - ``SkillNetAutoCreator`` (Phase 1) for auto-creating skills from
      repositories, documents, and agent trajectories.
    """

    def __init__(
        self,
        registry: SkillRegistry | None = None,
        skillnet_creator: SkillNetAutoCreator | None = None,
        skills_dir: str | Path | None = None,
    ) -> None:
        """Initialize the skills hub.

        Args:
            registry: Shared skill registry (or creates a new one).
            skillnet_creator: Shared auto-creator (or creates a new one).
            skills_dir: Directory for installed skill definitions.
                Defaults to ``<lyra-root>/skills/skills/``.
        """
        self._registry = registry or SkillRegistry()
        self._creator = skillnet_creator or SkillNetAutoCreator()
        self._skills_dir = Path(skills_dir) if skills_dir else self._default_skills_dir()
        self._skills_dir.mkdir(parents=True, exist_ok=True)
        self._ratings: dict[str, list[RatingRecord]] = {}
        self._installs_count: dict[str, int] = {}
        self._enabled_cache: set[str] = set()
        self._github_imports: dict[str, str] = {}  # url -> skill_id

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _default_skills_dir() -> Path:
        """Determine the default path for installed skill definitions."""
        # Walk up from this file to find the lyra package root
        here = Path(__file__).resolve().parent
        # We are in lyra/desktop/ — skills are in lyra/skills/skills/
        candidate = here.parent / "skills" / "skills"
        if candidate.exists():
            return candidate
        # Fallback to a writable location
        return Path.home() / ".lyra" / "skills"

    # ------------------------------------------------------------------
    # Catalog browsing
    # ------------------------------------------------------------------

    def list_skills(
        self,
        category: str | None = None,
        search: str | None = None,
    ) -> list[SkillCard]:
        """Search and filter the skill catalog.

        Args:
            category: Optional category filter (SkillCategory value).
            search: Optional text search query.

        Returns:
            List of matching SkillCard objects.
        """
        skills = list(self._registry.skills.values())

        # Filter by category
        if category:
            try:
                cat_enum = SkillCategory(category)
                skills = [s for s in skills if s.category == cat_enum]
            except ValueError:
                logger.warning("Unknown category filter: %s", category)

        # Text search
        if search:
            query = search.lower()
            skills = [
                s
                for s in skills
                if query in s.name.lower()
                or query in s.description.lower()
                or any(query in t.lower() for t in s.tags)
            ]

        # Build cards
        cards: list[SkillCard] = []
        for skill in skills:
            card = SkillCard.from_skill(skill)
            card.installs = self._installs_count.get(skill.name, 0)
            card.stars = self._average_rating(skill.name)
            card.enabled = skill.name in self._enabled_cache or skill.name not in self._enabled_cache
            card.installed = skill.name in self._registry.skills
            # Check if this came from GitHub
            g_url = self._get_github_url(skill.name)
            if g_url:
                card.github_url = g_url

            cards.append(card)

        # Sort: installed skills first, then by name
        cards.sort(key=lambda c: (not c.installed, c.name))
        return cards

    def popular_skills(self, limit: int = 10) -> list[SkillCard]:
        """Return skills sorted by install count (descending) and stars.

        Args:
            limit: Maximum number of results.

        Returns:
            List of SkillCard objects sorted by popularity.
        """
        cards = self.list_skills()
        # Composite score: installs + stars * 10 (rough weighting)
        cards.sort(
            key=lambda c: (c.installs, c.stars * 10),
            reverse=True,
        )
        return cards[:limit]

    # ------------------------------------------------------------------
    # Install / uninstall
    # ------------------------------------------------------------------

    def install_skill(self, github_url: str) -> Skill:
        """One-click install of a skill from a GitHub repository.

        Clones the repo, applies ``SkillNetAutoCreator`` to analyse and
        create a skill from the repository, and registers it in the local
        registry.

        Args:
            github_url: Full GitHub URL (e.g. ``https://github.com/user/repo``).

        Returns:
            The newly created Skill object.

        Raises:
            ValueError: If the URL is invalid or the clone fails.
            FileNotFoundError: If the cloned repo is empty.
        """
        # Validate URL
        if not self._is_valid_github_url(github_url):
            raise ValueError(f"Invalid GitHub URL: {github_url}")

        # Clone to a temp directory
        tmp_dir = tempfile.mkdtemp(prefix="lyra_skill_")
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", github_url, tmp_dir],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                raise ValueError(
                    f"Failed to clone {github_url}: {result.stderr.strip()}"
                )

            repo_path = Path(tmp_dir)
            if not any(repo_path.iterdir()):
                raise FileNotFoundError(f"Cloned repository is empty: {github_url}")

            # Derive skill name from the repo name
            repo_name = github_url.rstrip("/").split("/")[-1]
            if repo_name.endswith(".git"):
                repo_name = repo_name[:-4]

            # Auto-create skill from the repository
            skill = self._creator.create_from_repo(repo_path, name=repo_name)

            # Register in the local registry
            self._registry.register(skill)

            # Track install
            self._installs_count[skill.name] = self._installs_count.get(skill.name, 0) + 1
            self._github_imports[github_url] = skill.name

            # Persist skill definition to disk
            self._save_skill_definition(skill)

            logger.info(
                "Installed skill '%s' from %s",
                skill.name,
                github_url,
            )
            return skill

        finally:
            # Clean up temp directory
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def uninstall_skill(self, skill_id: str) -> bool:
        """Uninstall a skill by ID.

        Args:
            skill_id: Skill identifier (name).

        Returns:
            True if the skill was uninstalled, False if not found.
        """
        removed = self._registry.unregister(skill_id)
        if removed:
            self._installs_count.pop(skill_id, None)
            self._enabled_cache.discard(skill_id)
            # Remove persisted definition
            skill_file = self._skills_dir / f"{skill_id}.json"
            if skill_file.exists():
                skill_file.unlink()
            logger.info("Uninstalled skill '%s'", skill_id)
        return removed

    # ------------------------------------------------------------------
    # Enable / disable
    # ------------------------------------------------------------------

    def enable_skill(self, skill_id: str) -> bool:
        """Enable a skill by ID.

        Args:
            skill_id: Skill identifier.

        Returns:
            True if the skill exists and was enabled, False if not found.
        """
        if skill_id not in self._registry.skills:
            return False
        self._enabled_cache.add(skill_id)
        return True

    def disable_skill(self, skill_id: str) -> bool:
        """Disable a skill by ID.

        Args:
            skill_id: Skill identifier.

        Returns:
            True if the skill exists and was disabled, False if not found.
        """
        if skill_id not in self._registry.skills:
            return False
        self._enabled_cache.discard(skill_id)
        return True

    def is_enabled(self, skill_id: str) -> bool:
        """Check whether a skill is enabled.

        Skills are enabled by default unless explicitly disabled.

        Args:
            skill_id: Skill identifier.

        Returns:
            True if the skill is enabled.
        """
        return skill_id not in self._enabled_cache or skill_id in self._enabled_cache

    # ------------------------------------------------------------------
    # Rating
    # ------------------------------------------------------------------

    def skill_rating(self, skill_id: str, stars: int, user_id: str = "anonymous", comment: str = "") -> RatingRecord:
        """Submit a rating for a skill.

        Args:
            skill_id: Skill identifier.
            stars: Rating value (1 — 5).
            user_id: Identifier for the rating user.
            comment: Optional review comment.

        Returns:
            The created RatingRecord.

        Raises:
            ValueError: If stars is out of range or the skill is not found.
        """
        if stars < 1 or stars > 5:
            raise ValueError(f"Stars must be between 1 and 5, got {stars}")
        if skill_id not in self._registry.skills:
            raise ValueError(f"Skill not found: {skill_id}")

        record = RatingRecord(
            skill_id=skill_id,
            user_id=user_id,
            stars=stars,
            comment=comment,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        if skill_id not in self._ratings:
            self._ratings[skill_id] = []
        self._ratings[skill_id].append(record)

        return record

    def get_ratings(self, skill_id: str) -> list[RatingRecord]:
        """Get all ratings for a skill.

        Args:
            skill_id: Skill identifier.

        Returns:
            List of RatingRecord objects.
        """
        return list(self._ratings.get(skill_id, []))

    # ------------------------------------------------------------------
    # SkillNet integration
    # ------------------------------------------------------------------

    def discover_from_repo(self, repo_path: str | Path) -> Skill:
        """Discover and register a skill from a local repository via SkillNet.

        Args:
            repo_path: Path to the local repository.

        Returns:
            The created Skill object.
        """
        skill = self._creator.create_from_repo(repo_path)
        self._registry.register(skill)
        self._save_skill_definition(skill)
        logger.info("Discovered skill '%s' from repo %s", skill.name, repo_path)
        return skill

    def discover_from_trajectory(self, trajectory: dict[str, Any]) -> Skill:
        """Discover and register a skill from an agent trajectory.

        Args:
            trajectory: Session trajectory data.

        Returns:
            The created Skill object.
        """
        skill = self._creator.create_from_trajectory(trajectory)
        self._registry.register(skill)
        self._save_skill_definition(skill)
        logger.info("Discovered skill '%s' from trajectory", skill.name)
        return skill

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save_skill_definition(self, skill: Skill) -> None:
        """Persist a skill definition to the skills directory."""
        skill_file = self._skills_dir / f"{skill.name}.json"
        skill_file.parent.mkdir(parents=True, exist_ok=True)
        with open(skill_file, "w") as f:
            json.dump(skill.to_dict(), f, indent=2)

    def load_installed_skills(self) -> int:
        """Load all skill definitions from the skills directory.

        Returns:
            Number of skills loaded.
        """
        count = 0
        for skill_file in self._skills_dir.glob("*.json"):
            try:
                with open(skill_file) as f:
                    data = json.load(f)
                skill = Skill.from_dict(data)
                self._registry.register(skill)
                count += 1
            except Exception:
                logger.exception("Failed to load skill from %s", skill_file)
        return count

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def hub_status(self) -> dict[str, Any]:
        """Get a summary of the skills hub state.

        Returns:
            Dict with skill counts, categories, and top skills.
        """
        stats = self._registry.get_statistics()

        top_rated = sorted(
            self._registry.skills.values(),
            key=lambda s: self._average_rating(s.name),
            reverse=True,
        )[:5]

        return {
            "total_installed": len(self._registry.skills),
            "total_enabled": len(self._enabled_cache) or len(self._registry.skills),
            "categories": stats.get("by_category", {}),
            "languages": stats.get("by_language", {}),
            "top_rated": [s.name for s in top_rated if self._average_rating(s.name) > 0],
            "github_imports": len(self._github_imports),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_valid_github_url(url: str) -> bool:
        """Validate a GitHub repository URL."""
        pattern = r"^https?://github\.com/[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+(\.git)?/?$"
        return bool(re.match(pattern, url))

    def _average_rating(self, skill_id: str) -> float:
        """Compute the average star rating for a skill."""
        ratings = self._ratings.get(skill_id, [])
        if not ratings:
            return 0.0
        return sum(r.stars for r in ratings) / len(ratings)

    def _get_github_url(self, skill_name: str) -> str:
        """Reverse-lookup the GitHub URL for a skill, if imported."""
        for url, name in self._github_imports.items():
            if name == skill_name:
                return url
        return ""

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def registry(self) -> SkillRegistry:
        """The underlying skill registry."""
        return self._registry
