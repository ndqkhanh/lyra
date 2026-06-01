"""SkillNet-based auto-generator models — domains, templates, configs, and quality scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SkillDomain(Enum):
    """The nine Lyra skill domains supported by the auto-generator."""

    CODING = "coding"
    DEBUGGING = "debugging"
    TESTING = "testing"
    SECURITY = "security"
    DEVOPS = "devops"
    DATA = "data"
    DESIGN = "design"
    MANAGEMENT = "management"
    RESEARCH = "research"

    @property
    def display_name(self) -> str:
        return self.value.capitalize()

    @classmethod
    def from_string(cls, name: str) -> SkillDomain:
        for member in cls:
            if member.value == name.lower().strip():
                return member
        raise ValueError(f"Unknown domain: {name}")


@dataclass(frozen=True)
class SkillTemplate:
    """A parameterized skill template used by the generator."""

    domain: SkillDomain
    name: str
    description: str
    trigger_keywords: list[str]
    sections: list[str]
    difficulty: float = 0.5
    dependencies: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GeneratorConfig:
    """Configuration for the SkillGenerator."""

    output_dir: str = "./generated_skills"
    model_name: str = "claude-sonnet-4-6"
    temperature: float = 0.3
    max_tokens: int = 4096
    quality_threshold: float = 0.7
    enable_llm: bool = True


@dataclass(frozen=True)
class SkillQualityReport:
    """Five-dimensional quality assessment for a generated skill."""

    correctness: float = 0.0
    completeness: float = 0.0
    efficiency: float = 0.0
    readability: float = 0.0
    maintainability: float = 0.0

    @property
    def overall(self) -> float:
        return (
            self.correctness
            + self.completeness
            + self.efficiency
            + self.readability
            + self.maintainability
        ) / 5.0

    @property
    def dimensions(self) -> dict[str, float]:
        return {
            "correctness": self.correctness,
            "completeness": self.completeness,
            "efficiency": self.efficiency,
            "readability": self.readability,
            "maintainability": self.maintainability,
        }

    def meets_threshold(self, threshold: float) -> bool:
        return self.overall >= threshold


@dataclass(frozen=True)
class GeneratedSkill:
    """A complete generated skill with quality metadata."""

    template_name: str
    domain: SkillDomain
    content: str
    quality_report: SkillQualityReport = field(default_factory=SkillQualityReport)
    generated_at: datetime = field(default_factory=datetime.now)
    version: str = "1.0.0"


@dataclass
class SkillCatalog:
    """Mutable collection of skill templates for registration and lookup."""

    templates: dict[str, SkillTemplate] = field(default_factory=dict)

    def register(self, template: SkillTemplate) -> None:
        self.templates[template.name] = template

    def register_many(self, *templates: SkillTemplate) -> None:
        for t in templates:
            self.register(t)

    def get(self, name: str) -> SkillTemplate | None:
        return self.templates.get(name)

    def by_domain(self, domain: SkillDomain) -> list[SkillTemplate]:
        return [t for t in self.templates.values() if t.domain == domain]

    def list_domains(self) -> dict[SkillDomain, list[str]]:
        result: dict[SkillDomain, list[str]] = {}
        for t in self.templates.values():
            result.setdefault(t.domain, []).append(t.name)
        return result

    @property
    def count(self) -> int:
        return len(self.templates)
