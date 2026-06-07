"""Skill export/import with Wasla-compatible format.

Provides standardized skill packaging with integrity hashes,
version negotiation, and cross-orchestrator compatibility via
the Wasla universal sync format (The-Untitled-Org/wasla, v2.0.1).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lyra.skills.skill import Skill


@dataclass
class SkillPackage:
    """Standardized skill export format with integrity verification.

    Compatible with Wasla v2.0.1 universal agent sync format.
    """

    name: str
    version: str
    description: str
    content: str
    category: str
    trigger_patterns: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    compatible_agents: list[str] = field(default_factory=lambda: ["lyra"])
    author: str = ""
    license: str = "MIT"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    integrity_sha256: str = ""
    source: str = "lyra"

    def compute_hash(self) -> str:
        """Compute SHA-256 integrity hash of the skill content."""
        payload = json.dumps({
            "name": self.name,
            "version": self.version,
            "content": self.content,
            "category": self.category,
            "trigger_patterns": sorted(self.trigger_patterns),
            "tags": sorted(self.tags),
            "dependencies": sorted(self.dependencies),
        }, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def sign(self):
        """Sign the package with an integrity hash."""
        self.integrity_sha256 = self.compute_hash()

    def verify(self) -> bool:
        """Verify the package integrity hash matches its content."""
        return self.integrity_sha256 == self.compute_hash()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to Wasla-compatible dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "content": self.content,
            "category": self.category,
            "trigger_patterns": self.trigger_patterns,
            "tags": self.tags,
            "dependencies": self.dependencies,
            "compatible_agents": self.compatible_agents,
            "author": self.author,
            "license": self.license,
            "created_at": self.created_at,
            "integrity_sha256": self.integrity_sha256,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillPackage":
        """Deserialize from Wasla-compatible dictionary."""
        return cls(
            name=data["name"],
            version=data["version"],
            description=data.get("description", ""),
            content=data["content"],
            category=data.get("category", "general"),
            trigger_patterns=data.get("trigger_patterns", []),
            tags=data.get("tags", []),
            dependencies=data.get("dependencies", []),
            compatible_agents=data.get("compatible_agents", ["lyra"]),
            author=data.get("author", ""),
            license=data.get("license", "MIT"),
            created_at=data.get("created_at", ""),
            integrity_sha256=data.get("integrity_sha256", ""),
            source=data.get("source", "unknown"),
        )

    @classmethod
    def from_skill(cls, skill: Skill) -> "SkillPackage":
        """Create a SkillPackage from a Lyra Skill."""
        pkg = cls(
            name=skill.name,
            version=skill.version,
            description=skill.description,
            content=skill.content,
            category=skill.category.value if hasattr(skill.category, 'value') else str(skill.category),
            trigger_patterns=skill.trigger_patterns,
            tags=skill.tags,
            dependencies=skill.dependencies if hasattr(skill, 'dependencies') else [],
            source="lyra",
        )
        pkg.sign()
        return pkg

    def to_skill(self) -> Skill:
        """Convert back to a Lyra Skill."""
        from lyra.skills.skill import Skill as S, SkillCategory
        try:
            cat = SkillCategory(self.category)
        except (ValueError, KeyError):
            cat = SkillCategory.GENERAL
        return S(
            name=self.name,
            description=self.description,
            content=self.content,
            category=cat,
            trigger_patterns=self.trigger_patterns,
            tags=self.tags,
            version=self.version,
            source=self.source,
            dependencies=self.dependencies,
        )

    def save(self, path: Path):
        """Save package to a JSON file."""
        self.sign()
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path) -> "SkillPackage":
        """Load package from a JSON file."""
        data = json.loads(path.read_text())
        pkg = cls.from_dict(data)
        if not pkg.verify():
            raise ValueError(f"Integrity check failed for {pkg.name} v{pkg.version}")
        return pkg


@dataclass
class SkillRegistryExport:
    """Bulk export of multiple skills as a Wasla-compatible registry."""

    name: str = "lyra-skills"
    version: str = "1.0.0"
    skills: list[SkillPackage] = field(default_factory=list)
    exported_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def add(self, pkg: SkillPackage):
        self.skills.append(pkg)

    def to_wasla_format(self) -> dict[str, Any]:
        """Export in Wasla universal sync format."""
        return {
            "format": "wasla/v1",
            "registry": self.name,
            "version": self.version,
            "exported_at": self.exported_at,
            "skills": [s.to_dict() for s in self.skills],
        }

    def save(self, path: Path):
        path.write_text(json.dumps(self.to_wasla_format(), indent=2))

    @classmethod
    def load(cls, path: Path) -> "SkillRegistryExport":
        data = json.loads(path.read_text())
        reg = cls(
            name=data.get("registry", "imported"),
            version=data.get("version", "1.0.0"),
            exported_at=data.get("exported_at", ""),
        )
        for s in data.get("skills", []):
            reg.add(SkillPackage.from_dict(s))
        return reg
