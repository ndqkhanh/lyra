"""Agent metadata models."""
from dataclasses import dataclass


@dataclass
class AgentMetadata:
    """Metadata for an agent."""

    name: str
    description: str
    tools: list[str]
    model: str  # haiku, sonnet, opus
    origin: str = "ECC"
    file_path: str | None = None
