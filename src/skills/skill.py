"""
Skills system for Lyra - Import and manage ECC skills.

This module provides the infrastructure for importing, storing, and
retrieving skills from the ECC framework.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

__version__ = "1.0.0"


class SkillCategory(str, Enum):
    """Skill categories."""

    CODING_STANDARDS = "coding-standards"
    BACKEND_PATTERNS = "backend-patterns"
    FRONTEND_PATTERNS = "frontend-patterns"
    TDD_TESTING = "tdd-testing"
    SECURITY_REVIEW = "security-review"
    DATABASE = "database"
    API_DESIGN = "api-design"
    DEPLOYMENT = "deployment"
    DOCKER = "docker"
    FRAMEWORK_SPECIFIC = "framework-specific"
    GENERAL = "general"


@dataclass
class Skill:
    """
    Represents a skill that can be applied by agents.

    A skill encapsulates knowledge, patterns, and best practices
    that agents can use to perform tasks.
    """

    name: str
    description: str
    content: str
    category: SkillCategory = SkillCategory.GENERAL
    trigger_patterns: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    language: str | None = None
    framework: str | None = None
    version: str = "1.0.0"
    source: str = "lyra"  # "lyra" or "ecc"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())

    def matches_trigger(self, text: str) -> bool:
        """
        Check if this skill matches a trigger pattern.

        Args:
            text: Text to match against trigger patterns

        Returns:
            True if any trigger pattern matches
        """
        text_lower = text.lower()
        return any(pattern.lower() in text_lower for pattern in self.trigger_patterns)

    def matches_tags(self, tags: set[str]) -> bool:
        """
        Check if this skill matches any of the given tags.

        Args:
            tags: Set of tags to match

        Returns:
            True if any tag matches
        """
        return bool(set(self.tags) & tags)

    def to_dict(self) -> dict[str, Any]:
        """Convert skill to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "category": self.category.value,
            "trigger_patterns": self.trigger_patterns,
            "tags": self.tags,
            "language": self.language,
            "framework": self.framework,
            "version": self.version,
            "source": self.source,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Skill":
        """Create skill from dictionary."""
        return cls(
            name=data["name"],
            description=data["description"],
            content=data["content"],
            category=SkillCategory(data.get("category", "general")),
            trigger_patterns=data.get("trigger_patterns", []),
            tags=data.get("tags", []),
            language=data.get("language"),
            framework=data.get("framework"),
            version=data.get("version", "1.0.0"),
            source=data.get("source", "lyra"),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.now().timestamp()),
            updated_at=data.get("updated_at", datetime.now().timestamp()),
        )


@dataclass
class SkillSearchResult:
    """Result from skill search."""

    skill: Skill
    score: float
    match_reason: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "skill": self.skill.to_dict(),
            "score": self.score,
            "match_reason": self.match_reason,
        }
