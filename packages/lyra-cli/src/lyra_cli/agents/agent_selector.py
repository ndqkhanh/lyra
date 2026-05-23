"""Agent selector - Proactive agent selection"""

from typing import Optional, List
from .agent_manager import AgentDefinition
from .agent_registry import get_registry


class AgentSelector:
    """Selects appropriate agent based on context"""

    def __init__(self):
        self.registry = get_registry()

    def select_agent(self, task: str, context: dict = None) -> Optional[AgentDefinition]:
        """Select best agent for task"""
        context = context or {}

        # Check for explicit agent request
        if "agent:" in task.lower():
            agent_name = task.lower().split("agent:")[1].split()[0]
            agent = self.registry.get(agent_name)
            if agent:
                return agent

        # Proactive selection based on triggers
        task_lower = task.lower()

        # Planning tasks
        if any(word in task_lower for word in ["plan", "design", "architecture", "implement"]):
            return self.registry.get("planner")

        # Code review
        if any(word in task_lower for word in ["review", "check code", "quality"]):
            return self.registry.get("code-reviewer")

        # Security
        if any(word in task_lower for word in ["security", "vulnerability", "cve"]):
            return self.registry.get("security-reviewer")

        # Testing
        if any(word in task_lower for word in ["test", "tdd", "coverage"]):
            return self.registry.get("tdd-guide")

        # Refactoring
        if any(word in task_lower for word in ["refactor", "clean", "optimize"]):
            return self.registry.get("refactor-cleaner")

        # Documentation
        if any(word in task_lower for word in ["document", "docs", "readme"]):
            return self.registry.get("doc-updater")

        # No specific agent needed
        return None

    def suggest_agents(self, task: str) -> List[AgentDefinition]:
        """Suggest multiple agents for task"""
        suggestions = []

        # Find by triggers
        matching = self.registry.find_by_trigger(task)
        suggestions.extend(matching)

        # Add general-purpose agents
        if not suggestions:
            planner = self.registry.get("planner")
            if planner:
                suggestions.append(planner)

        return suggestions[:3]  # Top 3 suggestions


# Global selector
_selector = AgentSelector()


def get_selector() -> AgentSelector:
    """Get global agent selector"""
    return _selector
