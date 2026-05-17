"""Agent mode for editing agent context files."""
from pathlib import Path
from typing import Optional
import json


class AgentMode:
    """Enable meta-agent to edit agent context files."""

    def __init__(self, agent_context_dir: Path):
        self.agent_context_dir = Path(agent_context_dir)
        self.agent_context_dir.mkdir(parents=True, exist_ok=True)

    def read_context(self, name: str) -> Optional[str]:
        """Read an agent context file."""
        path = self.agent_context_dir / name
        if path.exists():
            return path.read_text()
        return None

    def write_context(self, name: str, content: str) -> bool:
        """Write an agent context file."""
        path = self.agent_context_dir / name
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            return True
        except Exception:
            return False

    def read_memory(self) -> dict:
        """Read agent memory JSON."""
        path = self.agent_context_dir / "memory.json"
        if path.exists():
            return json.loads(path.read_text())
        return {}

    def write_memory(self, memory: dict) -> bool:
        """Write agent memory JSON."""
        path = self.agent_context_dir / "memory.json"
        try:
            path.write_text(json.dumps(memory, indent=2))
            return True
        except Exception:
            return False
