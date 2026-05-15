"""
Agent Capability Matching for Lyra

Based on research from Multica and Ruflo.
Scores agents for task suitability and selects optimal agent.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class AgentScore:
    """Agent suitability score for a task."""
    agent_id: str
    total_score: float
    capability_score: float
    load_score: float
    performance_score: float
    health_score: float
    availability_score: float
    reasoning: str


@dataclass
class AgentState:
    """Current state of an agent."""
    id: str
    capabilities: List[str]
    workload: float  # 0-1, where 1 is fully loaded
    success_rate: float  # 0-1, historical success rate
    health: float  # 0-1, current health
    status: str  # "idle", "busy", "error", "offline"

    @classmethod
    def from_dict(cls, data: dict) -> "AgentState":
        """Create AgentState from dictionary."""
        return cls(
            id=data["id"],
            capabilities=data.get("capabilities", []),
            workload=data.get("workload", 0.0),
            success_rate=data.get("success_rate", 0.5),
            health=data.get("health", 1.0),
            status=data.get("status", "idle")
        )


def score_agent(
    agent: AgentState,
    required_capabilities: List[str],
    task_priority: int = 2
) -> AgentScore:
    """
    Score agent suitability for task.

    Scoring formula (from Ruflo Queen Coordinator):
    total = 0.30 * capability + 0.20 * load + 0.25 * performance
          + 0.15 * health + 0.10 * availability

    Args:
        agent: Agent state
        required_capabilities: Required capabilities for task
        task_priority: Task priority (1=high, 2=normal, 3=low)

    Returns:
        AgentScore with breakdown
    """
    # 1. Capability match (0-1)
    agent_caps = set(agent.capabilities)
    required_caps = set(required_capabilities)

    if not required_caps:
        capability_score = 1.0
    else:
        matched = len(agent_caps & required_caps)
        capability_score = matched / len(required_caps)

    # 2. Load score (prefer less loaded agents)
    load_score = 1.0 - agent.workload

    # 3. Performance score (historical success rate)
    performance_score = agent.success_rate

    # 4. Health score (current health)
    health_score = agent.health

    # 5. Availability score
    if agent.status == "idle":
        availability_score = 1.0
    elif agent.status == "busy":
        availability_score = 0.3  # Can still assign if urgent
    else:  # error or offline
        availability_score = 0.0

    # Weighted total
    total_score = (
        capability_score * 0.30 +
        load_score * 0.20 +
        performance_score * 0.25 +
        health_score * 0.15 +
        availability_score * 0.10
    )

    # Priority boost for high-priority tasks
    if task_priority == 1 and agent.status == "idle":
        total_score *= 1.1  # 10% boost for idle agents on high-priority tasks

    # Generate reasoning
    reasoning_parts = []
    if capability_score >= 0.8:
        reasoning_parts.append("strong capability match")
    elif capability_score >= 0.5:
        reasoning_parts.append("partial capability match")
    else:
        reasoning_parts.append("weak capability match")

    if load_score >= 0.7:
        reasoning_parts.append("low load")
    elif load_score >= 0.4:
        reasoning_parts.append("moderate load")
    else:
        reasoning_parts.append("high load")

    if performance_score >= 0.8:
        reasoning_parts.append("excellent track record")
    elif performance_score >= 0.6:
        reasoning_parts.append("good track record")

    reasoning = f"{agent.id}: {', '.join(reasoning_parts)}"

    return AgentScore(
        agent_id=agent.id,
        total_score=total_score,
        capability_score=capability_score,
        load_score=load_score,
        performance_score=performance_score,
        health_score=health_score,
        availability_score=availability_score,
        reasoning=reasoning
    )


def select_best_agent(
    agents: List[AgentState],
    required_capabilities: List[str],
    task_priority: int = 2,
    min_score: float = 0.3
) -> Optional[AgentScore]:
    """
    Select best agent for task.

    Args:
        agents: List of available agents
        required_capabilities: Required capabilities
        task_priority: Task priority
        min_score: Minimum acceptable score

    Returns:
        Best AgentScore or None if no suitable agent
    """
    if not agents:
        return None

    # Score all agents
    scores = [
        score_agent(agent, required_capabilities, task_priority)
        for agent in agents
    ]

    # Filter by minimum score
    viable_scores = [s for s in scores if s.total_score >= min_score]

    if not viable_scores:
        return None

    # Return highest scoring agent
    return max(viable_scores, key=lambda s: s.total_score)


def select_agent_pool(
    agents: List[AgentState],
    required_capabilities: List[str],
    pool_size: int = 3,
    task_priority: int = 2
) -> List[AgentScore]:
    """
    Select pool of suitable agents (primary + backups).

    Args:
        agents: List of available agents
        required_capabilities: Required capabilities
        pool_size: Number of agents to select
        task_priority: Task priority

    Returns:
        List of AgentScores, sorted by score (best first)
    """
    if not agents:
        return []

    # Score all agents
    scores = [
        score_agent(agent, required_capabilities, task_priority)
        for agent in agents
    ]

    # Sort by total score (descending)
    scores.sort(key=lambda s: s.total_score, reverse=True)

    # Return top N
    return scores[:pool_size]


def update_agent_metrics(
    agent_id: str,
    task_success: bool,
    agents: Dict[str, AgentState]
) -> None:
    """
    Update agent metrics after task completion.

    Args:
        agent_id: Agent ID
        task_success: Whether task succeeded
        agents: Dictionary of agent states (modified in-place)
    """
    if agent_id not in agents:
        return

    agent = agents[agent_id]

    # Update success rate (exponential moving average)
    alpha = 0.1  # Learning rate
    new_value = 1.0 if task_success else 0.0
    agent.success_rate = (1 - alpha) * agent.success_rate + alpha * new_value

    # Reduce workload (task completed)
    agent.workload = max(0.0, agent.workload - 0.1)


# Export for use in other modules
__all__ = [
    "AgentScore",
    "AgentState",
    "score_agent",
    "select_best_agent",
    "select_agent_pool",
    "update_agent_metrics"
]
