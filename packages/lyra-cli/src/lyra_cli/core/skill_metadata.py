"""Skill metadata models."""
from dataclasses import dataclass


@dataclass
class SkillMetadata:
    """Metadata for a skill."""

    name: str
    description: str
    origin: str
    tags: list[str]
    triggers: list[str] | None = None
    codemap: str | None = None
    file_path: str | None = None

    def __post_init__(self):
        if self.triggers is None:
            self.triggers = []
