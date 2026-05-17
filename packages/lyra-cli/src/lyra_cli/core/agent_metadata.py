"""Agent metadata models."""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class AgentMetadata:
    """Metadata for an agent."""

    name: str
    description: str
    tools: List[str]
    model: str  # haiku, sonnet, opus
    origin: str = "ECC"
    file_path: Optional[str] = None
