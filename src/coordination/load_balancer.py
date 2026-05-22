"""
Load Balancer - Distribute workload across agents.
"""

import time
from typing import List, Dict, Optional
from dataclasses import dataclass
from collections import defaultdict

from src.agents.base import Agent, AgentStatus


@dataclass
class AgentLoad:
    """Agent load information."""
    agent_id: str
    current_tasks: int
    total_executions: int
    recent_executions: int
    success_rate: float
    avg_duration: float
    load_percentage: float
    
    def __lt__(self, other):
        """Compare by load percentage."""
        return self.load_percentage < other.load_percentage


class LoadBalancer:
    """
    Load balancer for distributing tasks across agents.
    
    Responsibilities:
    - Monitor agent workload
    - Prevent agent overload
    - Balance task distribution
    - Track performance metrics
    """

    def __init__(self, max_tasks_per_agent: int = 5):
        """
        Initialize load balancer.
        
        Args:
            max_tasks_per_agent: Maximum concurrent tasks per agent
        """
        self.max_tasks_per_agent = max_tasks_per_agent
        self.agent_loads: Dict[str, AgentLoad] = {}
        self.load_history: List[Dict] = []
        self.start_time = time.time()

    def get_agent_load(self, agent: Agent) -> AgentLoad:
        """
        Get current load for an agent.
        
        Args:
            agent: Agent to check
            
        Returns:
            Agent load information
        """
        # Count current tasks
        current_tasks = 1 if agent.current_task else 0
        
        # Get execution stats
        total_executions = len(agent.execution_history)
        recent_executions = len(agent.execution_history[-10:])
        success_rate = agent.get_success_rate()
        
        # Calculate average duration
        durations = [
            r.duration for r in agent.execution_history[-10:]
            if hasattr(r, 'duration') and r.duration
        ]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        
        # Calculate load percentage
        load_percentage = (current_tasks / self.max_tasks_per_agent) * 100
        
        load = AgentLoad(
            agent_id=agent.agent_id,
            current_tasks=current_tasks,
            total_executions=total_executions,
            recent_executions=recent_executions,
            success_rate=success_rate,
            avg_duration=avg_duration,
            load_percentage=load_percentage,
        )
        
        # Cache load info
        self.agent_loads[agent.agent_id] = load
        
        return load

    def get_least_loaded_agent(self, agents: List[Agent]) -> Optional[Agent]:
        """
        Get the least loaded agent.
        
        Args:
            agents: List of agents to check
            
        Returns:
            Least loaded agent or None
        """
        if not agents:
            return None
        
        # Get loads for all agents
        loads = [self.get_agent_load(agent) for agent in agents]
        
        # Filter out overloaded agents
        available = [
            load for load in loads
            if load.current_tasks < self.max_tasks_per_agent
        ]
        
        if not available:
            return None
        
        # Get least loaded
        least_loaded = min(available)
        
        # Find corresponding agent
        return next(a for a in agents if a.agent_id == least_loaded.agent_id)

    def is_agent_available(self, agent: Agent) -> bool:
        """
        Check if agent can accept more tasks.
        
        Args:
            agent: Agent to check
            
        Returns:
            True if agent can accept tasks
        """
        load = self.get_agent_load(agent)
        return load.current_tasks < self.max_tasks_per_agent

    def get_available_agents(self, agents: List[Agent]) -> List[Agent]:
        """
        Get all agents that can accept tasks.
        
        Args:
            agents: List of agents to check
            
        Returns:
            List of available agents
        """
        return [agent for agent in agents if self.is_agent_available(agent)]

    def balance_load(self, agents: List[Agent]) -> Dict[str, List[str]]:
        """
        Analyze load distribution and suggest rebalancing.
        
        Args:
            agents: List of agents
            
        Returns:
            Rebalancing suggestions
        """
        if not agents:
            return {"suggestions": []}
        
        # Get all loads
        loads = [self.get_agent_load(agent) for agent in agents]
        
        # Calculate statistics
        avg_load = sum(l.load_percentage for l in loads) / len(loads)
        max_load = max(l.load_percentage for l in loads)
        min_load = min(l.load_percentage for l in loads)
        
        suggestions = []
        
        # Check for imbalance
        if max_load - min_load > 50:  # More than 50% difference
            overloaded = [l for l in loads if l.load_percentage > avg_load + 20]
            underloaded = [l for l in loads if l.load_percentage < avg_load - 20]
            
            if overloaded and underloaded:
                suggestions.append(
                    f"Rebalance: {overloaded[0].agent_id} (overloaded) -> "
                    f"{underloaded[0].agent_id} (underloaded)"
                )
        
        # Check for overload
        overloaded_agents = [l for l in loads if l.load_percentage >= 100]
        if overloaded_agents:
            suggestions.append(
                f"Warning: {len(overloaded_agents)} agent(s) at capacity"
            )
        
        return {
            "average_load": avg_load,
            "max_load": max_load,
            "min_load": min_load,
            "imbalance": max_load - min_load,
            "suggestions": suggestions,
        }

    def record_load_snapshot(self, agents: List[Agent]):
        """
        Record current load state.
        
        Args:
            agents: List of agents to snapshot
        """
        snapshot = {
            "timestamp": time.time(),
            "agents": {},
        }
        
        for agent in agents:
            load = self.get_agent_load(agent)
            snapshot["agents"][agent.agent_id] = {
                "current_tasks": load.current_tasks,
                "load_percentage": load.load_percentage,
                "success_rate": load.success_rate,
            }
        
        self.load_history.append(snapshot)
        
        # Keep last 100 snapshots
        if len(self.load_history) > 100:
            self.load_history = self.load_history[-100:]

    def get_statistics(self) -> Dict:
        """
        Get load balancing statistics.
        
        Returns:
            Statistics dictionary
        """
        if not self.agent_loads:
            return {
                "total_agents": 0,
                "max_tasks_per_agent": self.max_tasks_per_agent,
            }
        
        loads = list(self.agent_loads.values())
        
        total_tasks = sum(l.current_tasks for l in loads)
        avg_load = sum(l.load_percentage for l in loads) / len(loads)
        
        return {
            "total_agents": len(loads),
            "max_tasks_per_agent": self.max_tasks_per_agent,
            "total_current_tasks": total_tasks,
            "average_load_percentage": avg_load,
            "agents": {
                load.agent_id: {
                    "current_tasks": load.current_tasks,
                    "load_percentage": load.load_percentage,
                    "success_rate": load.success_rate,
                }
                for load in loads
            },
        }

    def get_load_trends(self) -> Dict:
        """
        Analyze load trends over time.
        
        Returns:
            Trend analysis
        """
        if len(self.load_history) < 2:
            return {"trend": "insufficient_data"}
        
        # Get recent snapshots
        recent = self.load_history[-10:]
        
        # Calculate average load over time
        avg_loads = []
        for snapshot in recent:
            agent_loads = snapshot["agents"].values()
            if agent_loads:
                avg = sum(a["load_percentage"] for a in agent_loads) / len(agent_loads)
                avg_loads.append(avg)
        
        if len(avg_loads) < 2:
            return {"trend": "insufficient_data"}
        
        # Determine trend
        first_half = sum(avg_loads[:len(avg_loads)//2]) / (len(avg_loads)//2)
        second_half = sum(avg_loads[len(avg_loads)//2:]) / (len(avg_loads) - len(avg_loads)//2)
        
        if second_half > first_half + 10:
            trend = "increasing"
        elif second_half < first_half - 10:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "first_half_avg": first_half,
            "second_half_avg": second_half,
            "change": second_half - first_half,
            "snapshots_analyzed": len(recent),
        }
