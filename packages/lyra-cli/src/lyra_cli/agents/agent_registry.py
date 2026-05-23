"""Agent registry - Built-in agent definitions"""

from typing import Dict, List
from .agent_manager import AgentDefinition


class AgentRegistry:
    """Registry of built-in agents"""

    def __init__(self):
        self.agents: Dict[str, AgentDefinition] = {}

    def register(self, agent: AgentDefinition):
        """Register an agent"""
        self.agents[agent.name] = agent

    def get(self, name: str) -> AgentDefinition:
        """Get agent by name"""
        return self.agents.get(name)

    def list(self) -> List[AgentDefinition]:
        """List all agents"""
        return list(self.agents.values())

    def find_by_trigger(self, trigger: str) -> List[AgentDefinition]:
        """Find agents matching a trigger"""
        matching = []
        for agent in self.agents.values():
            if any(t in trigger.lower() for t in agent.triggers):
                matching.append(agent)
        return matching


# Global registry
_registry = AgentRegistry()


def get_registry() -> AgentRegistry:
    """Get global agent registry"""
    return _registry
