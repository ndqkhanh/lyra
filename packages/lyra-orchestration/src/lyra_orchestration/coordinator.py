"""
Agent Coordinator - Orchestrate multiple agents via event bus.

Features:
- Parallel agent execution
- Event-driven workflows
- Agent-to-agent communication
- Shared context via event bus
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from lyra_orchestration.event_bus import (
    AgentCompleted,
    AgentFailed,
    AgentStarted,
    Event,
    EventBus,
)


class AgentStatus(Enum):
    """Agent execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentTask:
    """Agent task definition."""

    agent_id: str
    agent_type: str
    handler: Callable
    dependencies: List[str]
    status: AgentStatus = AgentStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class AgentCoordinator:
    """
    Coordinate multiple agents via event bus.

    Features:
    - Dependency management
    - Parallel execution
    - Event-driven coordination
    """

    def __init__(self, event_bus: EventBus):
        """
        Initialize coordinator.

        Args:
            event_bus: Event bus instance
        """
        self.event_bus = event_bus
        self.tasks: Dict[str, AgentTask] = {}

    def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        handler: Callable,
        dependencies: Optional[List[str]] = None,
    ) -> AgentTask:
        """
        Register agent task.

        Args:
            agent_id: Unique agent identifier
            agent_type: Agent type
            handler: Async handler function
            dependencies: List of agent IDs this depends on

        Returns:
            Agent task
        """
        task = AgentTask(
            agent_id=agent_id,
            agent_type=agent_type,
            handler=handler,
            dependencies=dependencies or [],
        )

        self.tasks[agent_id] = task
        return task

    async def execute(self) -> Dict[str, Any]:
        """
        Execute all registered agents.

        Returns:
            Execution results
        """
        # Find agents with no dependencies
        ready_tasks = [
            task for task in self.tasks.values()
            if not task.dependencies and task.status == AgentStatus.PENDING
        ]

        # Execute in parallel
        while ready_tasks:
            # Run ready tasks
            await asyncio.gather(
                *[self._execute_task(task) for task in ready_tasks],
                return_exceptions=True,
            )

            # Find newly ready tasks
            ready_tasks = self._get_ready_tasks()

        # Collect results
        results = {
            task.agent_id: {
                "status": task.status.value,
                "result": task.result,
                "error": task.error,
            }
            for task in self.tasks.values()
        }

        return results

    async def _execute_task(self, task: AgentTask):
        """
        Execute single agent task.

        Args:
            task: Agent task
        """
        task.status = AgentStatus.RUNNING
        task.started_at = datetime.now()

        # Publish started event
        await self.event_bus.publish(
            AgentStarted(
                agent_id=task.agent_id,
                agent_type=task.agent_type,
            )
        )

        try:
            # Execute handler
            result = await task.handler()
            task.result = result
            task.status = AgentStatus.COMPLETED
            task.completed_at = datetime.now()

            # Publish completed event
            await self.event_bus.publish(
                AgentCompleted(
                    agent_id=task.agent_id,
                    agent_type=task.agent_type,
                    result=result,
                )
            )

        except Exception as e:
            task.error = str(e)
            task.status = AgentStatus.FAILED
            task.completed_at = datetime.now()

            # Publish failed event
            await self.event_bus.publish(
                AgentFailed(
                    agent_id=task.agent_id,
                    agent_type=task.agent_type,
                    error=str(e),
                )
            )

    def _get_ready_tasks(self) -> List[AgentTask]:
        """
        Get tasks ready to execute.

        Returns:
            List of ready tasks
        """
        ready = []

        for task in self.tasks.values():
            if task.status != AgentStatus.PENDING:
                continue

            # Check if all dependencies completed
            deps_completed = all(
                self.tasks[dep_id].status == AgentStatus.COMPLETED
                for dep_id in task.dependencies
                if dep_id in self.tasks
            )

            if deps_completed:
                ready.append(task)

        return ready

    def get_stats(self) -> Dict[str, Any]:
        """
        Get execution statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "total_tasks": len(self.tasks),
            "pending": sum(1 for t in self.tasks.values() if t.status == AgentStatus.PENDING),
            "running": sum(1 for t in self.tasks.values() if t.status == AgentStatus.RUNNING),
            "completed": sum(1 for t in self.tasks.values() if t.status == AgentStatus.COMPLETED),
            "failed": sum(1 for t in self.tasks.values() if t.status == AgentStatus.FAILED),
        }
