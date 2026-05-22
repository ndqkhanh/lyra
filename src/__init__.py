"""
Lyra - Autonomous Team Orchestration AI System

A sophisticated multi-agent AI system that coordinates specialized agents
to work together like a high-performing human team.
"""

__version__ = "4.0.0"
__author__ = "Lyra Team"

from src.agents.base import Agent, AgentCapability, AgentStatus
from src.core.task import Task, TaskType, TaskPriority, Result

__all__ = [
    "Agent",
    "AgentCapability",
    "AgentStatus",
    "Task",
    "TaskType",
    "TaskPriority",
    "Result",
]
