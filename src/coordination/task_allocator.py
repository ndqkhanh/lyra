"""
Task Allocator - Intelligent task routing and allocation.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

from src.core.task import Task, TaskPriority
from src.agents.base import Agent


class AllocationStrategy(Enum):
    """Task allocation strategies."""
    CAPABILITY_BASED = "capability_based"  # Route by capability match
    LOAD_BALANCED = "load_balanced"        # Balance load across agents
    PRIORITY_FIRST = "priority_first"      # High priority tasks first
    ROUND_ROBIN = "round_robin"            # Distribute evenly
    LEAST_LOADED = "least_loaded"          # Assign to least busy agent


@dataclass
class AllocationScore:
    """Score for task-agent allocation."""
    agent_id: str
    capability_score: float
    load_score: float
    priority_score: float
    total_score: float

    def __lt__(self, other):
        """Compare by total score."""
        return self.total_score < other.total_score


class TaskAllocator:
    """
    Intelligent task allocator with multiple strategies.
    
    Responsibilities:
    - Analyze task requirements
    - Score available agents
    - Select optimal agent for task
    - Support multiple allocation strategies
    """

    def __init__(self, strategy: AllocationStrategy = AllocationStrategy.CAPABILITY_BASED):
        """
        Initialize task allocator.
        
        Args:
            strategy: Allocation strategy to use
        """
        self.strategy = strategy
        self.allocation_history: List[Dict] = []

        # Strategy weights
        self.weights = {
            AllocationStrategy.CAPABILITY_BASED: {
                "capability": 0.7,
                "load": 0.2,
                "priority": 0.1,
            },
            AllocationStrategy.LOAD_BALANCED: {
                "capability": 0.3,
                "load": 0.6,
                "priority": 0.1,
            },
            AllocationStrategy.PRIORITY_FIRST: {
                "capability": 0.3,
                "load": 0.2,
                "priority": 0.5,
            },
            AllocationStrategy.LEAST_LOADED: {
                "capability": 0.2,
                "load": 0.7,
                "priority": 0.1,
            },
        }

    def allocate(
        self,
        task: Task,
        agents: List[Agent],
        exclude: Optional[List[str]] = None,
    ) -> Optional[Agent]:
        """
        Allocate task to best available agent.
        
        Args:
            task: Task to allocate
            agents: Available agents
            exclude: Agent IDs to exclude
            
        Returns:
            Selected agent or None if no suitable agent
        """
        if not agents:
            return None

        # Filter excluded agents
        exclude = exclude or []
        available = [a for a in agents if a.agent_id not in exclude]

        if not available:
            return None

        # Score all agents
        scores = self._score_agents(task, available)

        if not scores:
            return None

        # Select best agent
        best_score = max(scores)
        selected_agent = next(a for a in available if a.agent_id == best_score.agent_id)

        # Record allocation
        self._record_allocation(task, selected_agent, best_score)

        return selected_agent

    def _score_agents(self, task: Task, agents: List[Agent]) -> List[AllocationScore]:
        """
        Score all agents for a task.
        
        Args:
            task: Task to score for
            agents: Agents to score
            
        Returns:
            List of allocation scores
        """
        scores = []

        for agent in agents:
            # Calculate component scores
            capability_score = self._capability_score(task, agent)
            load_score = self._load_score(agent)
            priority_score = self._priority_score(task)

            # Get weights for current strategy
            weights = self.weights.get(
                self.strategy,
                self.weights[AllocationStrategy.CAPABILITY_BASED]
            )

            # Calculate total score
            total_score = (
                capability_score * weights["capability"] +
                load_score * weights["load"] +
                priority_score * weights["priority"]
            )

            scores.append(AllocationScore(
                agent_id=agent.agent_id,
                capability_score=capability_score,
                load_score=load_score,
                priority_score=priority_score,
                total_score=total_score,
            ))

        return scores

    def _capability_score(self, task: Task, agent: Agent) -> float:
        """
        Score agent's capability for task.
        
        Args:
            task: Task to score for
            agent: Agent to score
            
        Returns:
            Capability score (0-1)
        """
        # Use agent's can_handle method
        confidence = agent.can_handle(task)

        # Boost score based on success rate
        success_rate = agent.get_success_rate()

        # Combine confidence and success rate
        return confidence * 0.7 + success_rate * 0.3

    def _load_score(self, agent: Agent) -> float:
        """
        Score agent's current load (inverse - lower load = higher score).
        
        Args:
            agent: Agent to score
            
        Returns:
            Load score (0-1)
        """
        # Check if agent is busy
        if agent.current_task is not None:
            return 0.0

        # Consider recent execution count
        recent_executions = len(agent.execution_history[-10:])

        # Lower execution count = higher score
        load_factor = max(0.0, 1.0 - (recent_executions / 10.0))

        return load_factor

    def _priority_score(self, task: Task) -> float:
        """
        Score based on task priority.
        
        Args:
            task: Task to score
            
        Returns:
            Priority score (0-1)
        """
        priority_map = {
            TaskPriority.CRITICAL: 1.0,
            TaskPriority.HIGH: 0.8,
            TaskPriority.NORMAL: 0.5,
            TaskPriority.LOW: 0.3,
        }

        return priority_map.get(task.priority, 0.5)

    def _record_allocation(self, task: Task, agent: Agent, score: AllocationScore):
        """
        Record allocation decision.
        
        Args:
            task: Allocated task
            agent: Selected agent
            score: Allocation score
        """
        self.allocation_history.append({
            "task_id": task.task_id,
            "task_type": task.type.value,
            "agent_id": agent.agent_id,
            "score": score.total_score,
            "capability_score": score.capability_score,
            "load_score": score.load_score,
            "priority_score": score.priority_score,
            "strategy": self.strategy.value,
        })

        # Keep last 100 allocations
        if len(self.allocation_history) > 100:
            self.allocation_history = self.allocation_history[-100:]

    def get_statistics(self) -> Dict:
        """
        Get allocation statistics.
        
        Returns:
            Statistics dictionary
        """
        if not self.allocation_history:
            return {
                "total_allocations": 0,
                "strategy": self.strategy.value,
            }

        # Calculate statistics
        agent_counts = {}
        for alloc in self.allocation_history:
            agent_id = alloc["agent_id"]
            agent_counts[agent_id] = agent_counts.get(agent_id, 0) + 1

        avg_score = sum(a["score"] for a in self.allocation_history) / len(self.allocation_history)

        return {
            "total_allocations": len(self.allocation_history),
            "strategy": self.strategy.value,
            "average_score": avg_score,
            "allocations_by_agent": agent_counts,
            "most_used_agent": max(agent_counts.items(), key=lambda x: x[1])[0] if agent_counts else None,
        }

    def set_strategy(self, strategy: AllocationStrategy):
        """
        Change allocation strategy.
        
        Args:
            strategy: New strategy to use
        """
        self.strategy = strategy
