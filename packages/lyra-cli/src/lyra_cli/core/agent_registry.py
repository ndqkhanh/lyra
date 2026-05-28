"""Agent registry for loading and managing agents."""
from pathlib import Path

import yaml

from .agent_metadata import AgentMetadata


class AgentRegistry:
    """Registry for loading and managing agents."""

    def __init__(self, agent_dirs: list[Path] | None = None):
        self.agent_dirs = agent_dirs or []
        self._agents: dict[str, AgentMetadata] = {}

    def load_agents(self) -> dict[str, AgentMetadata]:
        """Load all agents from configured directories."""
        self._agents.clear()

        for agent_dir in self.agent_dirs:
            if not agent_dir.exists():
                continue

            for agent_file in agent_dir.glob("*.md"):
                try:
                    metadata = self._parse_agent_file(agent_file)
                    if metadata:
                        self._agents[metadata.name] = metadata
                except Exception as e:
                    print(f"Error loading agent {agent_file}: {e}")

        return self._agents

    def _parse_agent_file(self, file_path: Path) -> AgentMetadata | None:
        """Parse agent file with YAML frontmatter."""
        content = file_path.read_text()

        if not content.startswith("---"):
            return None

        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        try:
            frontmatter = yaml.safe_load(parts[1])
            return AgentMetadata(
                name=frontmatter.get("name", ""),
                description=frontmatter.get("description", ""),
                tools=frontmatter.get("tools", []),
                model=frontmatter.get("model", "sonnet"),
                origin=frontmatter.get("origin", "ECC"),
                file_path=str(file_path)
            )
        except yaml.YAMLError:
            return None

    def get_agent(self, name: str) -> AgentMetadata | None:
        """Get agent by name."""
        return self._agents.get(name)

    def search_agents(self, query: str) -> list[AgentMetadata]:
        """Search agents by name or description."""
        query_lower = query.lower()
        return [
            agent for agent in self._agents.values()
            if query_lower in agent.name.lower() or query_lower in agent.description.lower()
        ]

    def list_agents(self) -> list[AgentMetadata]:
        """List all loaded agents."""
        return list(self._agents.values())
