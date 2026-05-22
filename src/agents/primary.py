"""
Primary agent - orchestrates and coordinates specialist agents.
"""

import asyncio
from typing import Dict, List, Optional

from src.agents.base import Agent, AgentCapability, AgentStatus
from src.core.task import Task, TaskType, Result


class PrimaryAgent(Agent):
    """
    Primary orchestrator agent that coordinates specialist agents.
    
    The primary agent:
    - Receives user requests
    - Analyzes and decomposes tasks
    - Delegates to specialist agents
    - Aggregates results
    - Learns from execution patterns
    """

    def __init__(self, agent_id: str = "primary"):
        """Initialize the primary agent."""
        capabilities = [
            AgentCapability(
                name="orchestration",
                description="Coordinate multiple agents to complete complex tasks",
                task_types=[TaskType.GENERIC],
                confidence=1.0,
            )
        ]
        super().__init__(agent_id, capabilities)
        self.specialists: Dict[str, Agent] = {}
        self.task_queue: asyncio.Queue[Task] = asyncio.Queue()

    def register_specialist(self, agent: Agent) -> None:
        """
        Register a specialist agent.
        
        Args:
            agent: Specialist agent to register
        """
        self.specialists[agent.agent_id] = agent
        print(f"[{self.agent_id}] Registered specialist: {agent.agent_id}")

    def unregister_specialist(self, agent_id: str) -> None:
        """
        Unregister a specialist agent.
        
        Args:
            agent_id: ID of agent to unregister
        """
        if agent_id in self.specialists:
            del self.specialists[agent_id]
            print(f"[{self.agent_id}] Unregistered specialist: {agent_id}")

    async def handle_request(self, request: str) -> str:
        """
        Main entry point for user requests.
        
        Args:
            request: User request string
            
        Returns:
            Response string
        """
        print(f"\n[{self.agent_id}] Handling request: {request}")
        
        # 1. Analyze request and create task
        task = await self.analyze_request(request)
        
        # 2. Execute task
        result = await self.execute(task)
        
        # 3. Format response
        if result.success:
            return f"✅ Task completed successfully: {result.data}"
        else:
            return f"❌ Task failed: {result.error}"

    async def analyze_request(self, request: str) -> Task:
        """
        Analyze user request and create a task.
        
        Args:
            request: User request string
            
        Returns:
            Task object
        """
        # Simple analysis - in production this would use LLM
        task_type = TaskType.GENERIC
        
        # Detect task type from keywords
        request_lower = request.lower()
        if any(word in request_lower for word in ["code", "implement", "refactor"]):
            task_type = TaskType.CODE_GENERATION
        elif any(word in request_lower for word in ["test", "verify"]):
            task_type = TaskType.TEST_GENERATION
        elif any(word in request_lower for word in ["research", "find", "search"]):
            task_type = TaskType.RESEARCH
        elif any(word in request_lower for word in ["review", "check"]):
            task_type = TaskType.CODE_REVIEW
        
        return Task(
            type=task_type,
            description=request,
            params={"request": request},
        )

    async def execute(self, task: Task) -> Result:
        """
        Execute a task by delegating to appropriate specialist.
        
        Args:
            task: Task to execute
            
        Returns:
            Execution result
        """
        self.status = AgentStatus.BUSY
        self.current_task = task
        task.start()
        
        try:
            # Find best agent for task
            agent = await self.select_agent(task)
            
            if not agent:
                # No specialist available, handle it ourselves
                result = await self.execute_directly(task)
            else:
                # Delegate to specialist
                print(f"[{self.agent_id}] Delegating to: {agent.agent_id}")
                result = await agent.execute(task)
            
            task.complete()
            self.record_execution(result)
            return result
            
        except Exception as e:
            task.fail()
            result = Result(
                task_id=task.task_id,
                success=False,
                error=str(e),
                agent_id=self.agent_id,
            )
            self.record_execution(result)
            return result
            
        finally:
            self.status = AgentStatus.IDLE
            self.current_task = None

    async def select_agent(self, task: Task) -> Optional[Agent]:
        """
        Select the best agent for a task.
        
        Args:
            task: Task to assign
            
        Returns:
            Best agent, or None if no suitable agent found
        """
        if not self.specialists:
            return None
        
        # Score each agent
        scores = []
        for agent in self.specialists.values():
            if agent.status == AgentStatus.IDLE:
                confidence = agent.can_handle(task)
                if confidence > 0:
                    scores.append((agent, confidence))
        
        if not scores:
            return None
        
        # Return agent with highest confidence
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[0][0]

    async def execute_directly(self, task: Task) -> Result:
        """
        Execute task directly (fallback when no specialist available).
        
        Args:
            task: Task to execute
            
        Returns:
            Execution result
        """
        print(f"[{self.agent_id}] Executing directly: {task.description}")
        
        # Simple execution - just acknowledge the task
        await asyncio.sleep(0.1)  # Simulate work
        
        return Result(
            task_id=task.task_id,
            success=True,
            data=f"Acknowledged: {task.description}",
            agent_id=self.agent_id,
        )

    def can_handle(self, task: Task) -> float:
        """
        Primary agent can handle any task (as orchestrator).
        
        Args:
            task: Task to evaluate
            
        Returns:
            Confidence score (always 1.0 for primary agent)
        """
        return 1.0

    async def execute_parallel(self, tasks: List[Task]) -> List[Result]:
        """
        Execute multiple tasks in parallel.
        
        Args:
            tasks: List of tasks to execute
            
        Returns:
            List of results
        """
        print(f"[{self.agent_id}] Executing {len(tasks)} tasks in parallel")
        
        # Execute all tasks concurrently
        results = await asyncio.gather(
            *[self.execute(task) for task in tasks],
            return_exceptions=True
        )
        
        # Convert exceptions to failed results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(
                    Result(
                        task_id=tasks[i].task_id,
                        success=False,
                        error=str(result),
                        agent_id=self.agent_id,
                    )
                )
            else:
                final_results.append(result)
        
        return final_results

    def get_statistics(self) -> Dict[str, any]:
        """
        Get orchestration statistics.
        
        Returns:
            Dictionary of statistics
        """
        return {
            "agent_id": self.agent_id,
            "status": self.status.value,
            "specialists_count": len(self.specialists),
            "specialists": list(self.specialists.keys()),
            "total_executions": len(self.execution_history),
            "success_rate": self.get_success_rate(),
        }
