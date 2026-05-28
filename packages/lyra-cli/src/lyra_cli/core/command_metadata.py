"""Command metadata models."""
from dataclasses import dataclass


@dataclass
class CommandMetadata:
    """Metadata for a command."""

    name: str
    description: str
    agent: str | None = None
    skill: str | None = None
    args: list[str] | None = None
    file_path: str | None = None

    def __post_init__(self):
        if self.args is None:
            self.args = []
