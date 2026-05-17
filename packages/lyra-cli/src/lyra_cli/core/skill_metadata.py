"""Skill metadata models."""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SkillMetadata:
    """Metadata for a skill."""

    name: str
    description: str
    origin: str
    tags: List[str]
    triggers: Optional[List[str]] = None
    codemap: Optional[str] = None
    file_path: Optional[str] = None

    def __post_init__(self):
        if self.triggers is None:
            self.triggers = []
