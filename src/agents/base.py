"""
Base agent classes and interfaces for the Lyra agent system.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from src.core.task import Task, TaskType, Result


class AgentStatus(str, Enum):
    """Agent operational status."""

    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


class MessageType(str, Enum):
    """Types of inter-agent messages."""

    PROGRESS = "progress"
    HELP_REQUEST = "help_request"
    RESULT = "result"
    ERROR = "error"
    STATUS_UPDATE = "status_update"


@dataclass
class AgentCapability:
    """Defines a capability that an agent can perform."""

    name: str
    description: str
    task_types: List[TaskType]
    required_tools: List[str] = field(default_factory=list)
    estimated_cost: float = 0.0
    estimated_time: float = 0.0
    confidence: float = 1.0  # 0-1 confidence in this capability

    def __post_init__(self) -> None:
        """Validate capability after initialization."""
        if not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")


@dataclass
class Message:
    """Inter-agent communication message."""

    from_agent: str
    to_agent: str
    message_type: MessageType
    content: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None


class Agent(ABC):
    """
    Base class for all agents in the Lyra system.
    
    Agents are autonomous entities that can execute tasks,
    communicate with other agents, and learn from experience.
    """

    def __init__(self, agent_id: str, capabilities: Optional[List[AgentCapability]] = None):
        """
        Initialize an agent.
        
        Args:
            agent_id: Unique identifier for this agent
            capabilities: List of capabilities this agent can perform
        """
        self.agent_id = agent_id
        self.capabilities = capabilities or []
        self.status = AgentStatus.IDLE
        self.current_task: Optional[Task] = None
        self.message_queue: asyncio.Queue[Message] = asyncio.Queue()
        self.execution_history: List[Result] = []
        self.metadata: Dict[str, Any] = {}

    @abstractmethod
    async def execute(self, task: Task) -> Result:
        """
        Execute a task and return the result.
        
        Args:
            task: The task to execute
            
        Returns:
            Result of the task execution
        """
        pass

    @abstractmethod
    def can_handle(self, task: Task) -> float:
        """
        Determine if this agent can handle a task.
        
        Args:
            task: The task to evaluate
            
        Returns:
            Confidence score (0-1) that this agent can handle the task
        """
        pass

    async def send_message(
        self, to_agent: str, message_type: MessageType, content: Dict[str, Any]
    ) -> None:
        """
        Send a message to another agent.
        
        Args:
            to_agent: ID of the recipient agent
            message_type: Type of message
            content: Message content
        """
        message = Message(
            from_agent=self.agent_id,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
        )
        # In a real implementation, this would route through a message broker
        # For now, we'll just log it
        print(f"[{self.agent_id}] -> [{to_agent}]: {message_type.value}")

    async def receive_message(self) -> Optional[Message]:
        """
        Receive a message from the queue.
        
        Returns:
            Next message in queue, or None if empty
        """
        try:
            return await asyncio.wait_for(self.message_queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return None

    async def report_progress(self, progress: float, message: str) -> None:
        """
        Report progress on current task.
        
        Args:
            progress: Progress percentage (0-1)
            message: Progress message
        """
        if self.current_task:
            await self.send_message(
                to_agent="coordinator",
                message_type=MessageType.PROGRESS,
                content={
                    "task_id": self.current_task.task_id,
                    "progress": progress,
                    "message": message,
                },
            )

    async def request_help(self, issue: str) -> Any:
        """
        Request help from the coordinator.
        
        Args:
            issue: Description of the issue
            
        Returns:
            Response from coordinator
        """
        await self.send_message(
            to_agent="coordinator",
            message_type=MessageType.HELP_REQUEST,
            content={"issue": issue, "task_id": self.current_task.task_id if self.current_task else None},
        )
        # In a real implementation, this would wait for a response
        return None

    def get_capability(self, task_type: TaskType) -> Optional[AgentCapability]:
        """
        Get capability for a specific task type.
        
        Args:
            task_type: Type of task
            
        Returns:
            Matching capability, or None if not found
        """
        for capability in self.capabilities:
            if task_type in capability.task_types:
                return capability
        return None

    def record_execution(self, result: Result) -> None:
        """
        Record a task execution result.
        
        Args:
            result: Execution result to record
        """
        self.execution_history.append(result)
        # Keep only last 100 results
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]

    def get_success_rate(self, task_type: Optional[TaskType] = None) -> float:
        """
        Calculate success rate for this agent.
        
        Args:
            task_type: Optional task type to filter by
            
        Returns:
            Success rate (0-1)
        """
        if not self.execution_history:
            return 0.0

        relevant_results = self.execution_history
        if task_type:
            # Filter by task type (would need to store task type in result)
            pass

        successful = sum(1 for r in relevant_results if r.success)
        return successful / len(relevant_results)

    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"<{self.__class__.__name__} id={self.agent_id} status={self.status.value}>"
