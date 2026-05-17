"""Command metadata models."""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class CommandMetadata:
    """Metadata for a command."""

    name: str
    description: str
    agent: Optional[str] = None
    skill: Optional[str] = None
    args: Optional[List[str]] = None
    file_path: Optional[str] = None

    def __post_init__(self):
        if self.args is None:
            self.args = []
