"""Agent manager - Core agent orchestration"""

import re
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class AgentDefinition:
    """Agent definition from YAML frontmatter"""
    name: str
    description: str
    tools: list[str]
    model: str = "sonnet"
    prompt: str = ""
    triggers: list[str] = None

    def __post_init__(self):
        if self.triggers is None:
            self.triggers = []


class AgentManager:
    """Manages agent definitions and execution"""

    def __init__(self, agents_dir: Path | None = None):
        self.agents_dir = agents_dir or Path.home() / ".lyra" / "agents"
        self.agents: dict[str, AgentDefinition] = {}

    def load_agents(self):
        """Load agent definitions from directory"""
        if not self.agents_dir.exists():
            return

        for agent_file in self.agents_dir.glob("*.md"):
            try:
                agent = self._parse_agent_file(agent_file)
                if agent:
                    self.agents[agent.name] = agent
            except Exception as e:
                print(f"Warning: Failed to load agent {agent_file}: {e}")

    def _parse_agent_file(self, file_path: Path) -> AgentDefinition | None:
        """Parse agent file with YAML frontmatter"""
        content = file_path.read_text()

        # Extract YAML frontmatter
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
        if not match:
            return None

        frontmatter_text, prompt = match.groups()

        try:
            frontmatter = yaml.safe_load(frontmatter_text)
        except yaml.YAMLError:
            return None

        # Create agent definition
        return AgentDefinition(
            name=frontmatter.get("name", file_path.stem),
            description=frontmatter.get("description", ""),
            tools=frontmatter.get("tools", []),
            model=frontmatter.get("model", "sonnet"),
            prompt=prompt.strip(),
            triggers=frontmatter.get("triggers", []),
        )

    def get_agent(self, name: str) -> AgentDefinition | None:
        """Get agent by name"""
        return self.agents.get(name)

    def list_agents(self) -> list[AgentDefinition]:
        """List all agents"""
        return list(self.agents.values())

    def register_agent(self, agent: AgentDefinition):
        """Register an agent programmatically"""
        self.agents[agent.name] = agent

    def create_agent_prompt(self, agent: AgentDefinition, task: str) -> str:
        """Create full prompt for agent"""
        prompt = f"""# Agent: {agent.name}

{agent.description}

## Your Task

{task}

## Instructions

{agent.prompt}

## Available Tools

{', '.join(agent.tools)}

## Model

{agent.model}
"""
        return prompt


# Global agent manager instance
_agent_manager: AgentManager | None = None


def get_agent_manager() -> AgentManager:
    """Get or create global agent manager"""
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentManager()
        _agent_manager.load_agents()
    return _agent_manager
