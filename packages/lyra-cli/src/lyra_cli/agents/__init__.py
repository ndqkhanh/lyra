"""Agent orchestration system for Lyra - ECC-inspired"""

from .agent_manager import AgentManager, AgentDefinition
from .agent_registry import AgentRegistry
from .agent_selector import AgentSelector
from .builtin_agents import register_builtin_agents

__all__ = [
    "AgentManager",
    "AgentDefinition",
    "AgentRegistry",
    "AgentSelector",
    "register_builtin_agents",
]
