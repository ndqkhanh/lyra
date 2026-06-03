# Multi-Agent System Design

**Version:** 1.0  
**Date:** 2026-06-02  
**Status:** Production

---

## Executive Summary

This document details the algorithms, data models, APIs, and state management mechanisms that power Lyra's multi-agent system. It covers the technical implementation of coordination primitives, execution strategies, and scalability considerations.

---

## Table of Contents

1. [Data Models](#data-models)
2. [State Management](#state-management)
3. [Core Algorithms](#core-algorithms)
4. [API Design](#api-design)
5. [Scalability Design](#scalability-design)

---

## Data Models

### Agent Model

```python
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum

class AgentRole(Enum):
    ANALYST = "analyst"
    EXPERIMENTER = "experimenter"
    CRITIC = "critic"
    SYNTHESIZER = "synthesizer"

@dataclass
class Agent:
    id: str
    role: AgentRole
    team_id: Optional[str]
    capabilities: List[str]
    current_load: int
    success_rate: float
    total_tasks_completed: int
    
    def interested_in(self, hypothesis: Hypothesis) -> bool:
        """Check if agent is interested in hypothesis based on capabilities"""
        return any(cap in hypothesis.required_capabilities 
                self.has_capabilities(task.required_capabilities))
    
    def has_capabilities(self, required: List[str]) -> bool:
        return all(cap in self.capabilities for cap in required)
```

### Task Model

```python
@dataclass
class Task:
    id: str
    description: str
    subtasks: List['Task']
    dependencies: List[str]  # Task IDs
    required_capabilities: List[str]
    complexity: float
    estimated_duration: timedelta
    priority: float
    status: TaskStatus
    assigned_to: Optional[str]  # Agent ID
    created_at: datetime
    completed_at: Optional[datetime]
    
    def is_ready(self, completed_tasks: Set[str]) -> bool:
        """Check if all dependencies are completed"""
        return all(dep in completed_tasks for dep in self.dependencies)
    
    def estimate_effort(self) -> float:
        """Estimate effort based on complexity and subtasks"""
        base_effort = self.complexity
        subtask_effort = sum(st.estimate_effort() for st in self.subtasks)
        return base_effort + subtask_effort * 0.8  # Subtasks slightly discounted

class TaskStatus(Enum):
    PENDING = "pending"
    READY = "ready"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

### Proposal Model

```python
@dataclass
class Proposal:
    id: str
    proposer_id: str
    team_id: str
    description: str
    modifications: Dict[str, Any]
    rationale: str
    estimated_effect_size: float
    evidence: Evidence
    status: ProposalStatus
    priority: float

@dataclass
class Evidence:
    type: str
    data: Dict[str, Any]
    confidence: float
    sources: List[str]
    
    def verify(self) -> bool:
        """Verify evidence meets quality threshold"""
        return self.confidence >= 0.6 and len(self.sources) >= 2

class ProposalStatus(Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
```

### Team Model

```python
@dataclass
class Team:
    id: str
    hypothesis: Hypothesis
    agents: List[Agent]
    champion: Optional[Solution]
    queue: PriorityQueue[Proposal]
    created_at: datetime
    stagnation_count: int = 0
    
    def total_capacity(self) -> int:
        return sum(agent.current_load for agent in self.agents)
    
    def failure_rate(self, lookback: int = 10) -> float:
        recent = self.queue.recent(n=lookback)
        failed = sum(1 for p in recent if p.status == ProposalStatus.REJECTED)
        return failed / len(recent) if recent else 0.0

@dataclass
class Hypothesis:
    description: str
    rationale: str
    required_capabilities: List[str]
    proposed_experiments: List[Experiment]
    expected_impact: float
```

### Experiment Model

```python
@dataclass
class Experiment:
    id: str
    proposal_id: str
    team_id: str
    agent_id: str
    baseline: Solution
    candidate: Solution
    result: ExperimentResult
    timestamp: datetime
    duration: timedelta
    
@dataclass
class ExperimentResult:
    status: str  # "success" | "failed"
    baseline_score: float
    candidate_score: float
    effect_size: float

---

## State Management

### Shared State Schema

```sql
-- SQLite schema for persistent state

CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    team_id TEXT,
    capabilities TEXT,  -- JSON array
    current_load INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 0.0,
    total_tasks INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE teams (
    id TEXT PRIMARY KEY,
    hypothesis TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    stagnation_count INTEGER DEFAULT 0
);

CREATE TABLE proposals (
    id TEXT PRIMARY KEY,
    proposer_id TEXT NOT NULL,
    team_id TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    priority REAL DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (proposer_id) REFERENCES agents(id),
    FOREIGN KEY (team_id) REFERENCES teams(id)
);

CREATE TABLE experiments (
    id TEXT PRIMARY KEY,
    proposal_id TEXT NOT NULL,
    team_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    status TEXT NOT NULL,
    effect_size REAL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (proposal_id) REFERENCES proposals(id),
    FOREIGN KEY (team_id) REFERENCES teams(id),
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);

CREATE INDEX idx_proposals_team ON proposals(team_id, priority DESC);
CREATE INDEX idx_experiments_team ON experiments(team_id, timestamp DESC);
```

### Redis Caching Layer

```python
# Ephemeral state in Redis for fast access

class RedisStateCache:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    
    def push_proposal(self, team_id: str, proposal: Proposal):
        """Add proposal to team queue"""
        key = f"team:{team_id}:queue"
        self.redis.lpush(key, proposal.to_json())
        self.redis.zadd(f"team:{team_id}:priorities", 
                       {proposal.id: proposal.priority})
    
    def get_champion(self, team_id: str) -> Optional[Solution]:
        """Get current team champion"""
        key = f"team:{team_id}:champion"
        data = self.redis.get(key)
        return Solution.from_json(data) if data else None
```

---

## Core Algorithms

### Wave Construction Algorithm

```python
def build_dependency_waves(tasks: List[Task]) -> List[List[Task]]:
    """
    Organize tasks into dependency-ordered waves for parallel execution.
    
    Time Complexity: O(V + E) where V=tasks, E=dependencies
    Space Complexity: O(V)
    """
    # Build adjacency list and in-degree map
    graph = defaultdict(list)
    in_degree = {task.id: 0 for task in tasks}
    task_map = {task.id: task for task in tasks}
    
    for task in tasks:
        for dep in task.dependencies:
            graph[dep].append(task.id)
            in_degree[task.id] += 1
    
    # Topological sort with wave tracking
    waves = []
    remaining = set(task.id for task in tasks)
    
    while remaining:
        # Current wave: tasks with no unmet dependencies
        wave = [task_map[tid] for tid in remaining 
                if in_degree[tid] == 0]
        
        if not wave:
            # Detect cycle
            raise CyclicDependencyError(
                f"Cyclic dependency detected among: {remaining}"
            )
        
        waves.append(wave)
        
        # Update in-degrees for next wave
        for task in wave:
            remaining.remove(task.id)
            for child_id in graph[task.id]:
                in_degree[child_id] -= 1
    
    return waves
```

### Capability Matching Algorithm

```python
    
    Score = w1*skill_match + w2*experience + w3*availability + w4*success_rate
    """
    # Skill match (0-1)
    required = set(task.required_capabilities)
    available = set(agent.capabilities)
    skill_match = len(required & available) / len(required) if required else 1.0
    
    # Experience (0-1) - normalized by team average
    experience = min(agent.total_tasks_completed / 100, 1.0)
    
    # Availability (0-1) - inverse of current load
    availability = max(0, 1 - agent.current_load / MAX_LOAD)
    
    # Success rate (0-1)
    success_rate = agent.success_rate
    
    # Weighted combination
    weights = {"skill": 0.4, "experience": 0.2, "availability": 0.2, "success": 0.2}
    
    score = (weights["skill"] * skill_match +
             weights["experience"] * experience +
             weights["availability"] * availability +
             weights["success"] * success_rate)
    
    return score
```

### Consensus Algorithm

```python
def build_consensus(
    votes: List[Tuple[Agent, Proposal, float]],
    method: ConsensusMethod,
    threshold: float = 0.7
) -> Optional[Proposal]:
    """Build consensus from agent votes"""
    
    if method == ConsensusMethod.MAJORITY:
        # Most common proposal wins
        proposal_counts = Counter(v[1] for v in votes)
        winner, count = proposal_counts.most_common(1)[0]
        if count > len(votes) / 2:
            return winner
    
    elif method == ConsensusMethod.WEIGHTED:
        # Confidence-weighted voting
        proposal_scores = defaultdict(float)
        for agent, proposal, confidence in votes:
            proposal_scores[proposal] += confidence * agent.success_rate
        
        if proposal_scores:
            winner = max(proposal_scores.items(), key=lambda x: x[1])
            return winner[0]
    
    elif method == ConsensusMethod.THRESHOLD:
        # Require threshold% agreement
        proposal_counts = Counter(v[1] for v in votes)
        for proposal, count in proposal_counts.items():
            if count >= len(votes) * threshold:
                return proposal
    
    return None  # No consensus
```

---

## API Design

### Agent API

```python
    
    def claim_task(self, agent_id: str, task_id: str) -> Result[Task]:
        """Agent claims a task from the pool"""
    
    def submit_result(self, agent_id: str, task_id: str, result: Any) -> Result[None]:
        """Agent submits task result"""
    
    def get_state_view(self, agent_id: str) -> StateView:
        """Get agent-specific view of shared state"""

### Coordinator API

```python
class CoordinatorAPI:
    """Public API for swarm coordination"""
    
    async def spawn_team(self, hypothesis: Hypothesis, size: int) -> Team:
        """Create a new team around a hypothesis"""
    
    async def execute_wave(self, tasks: List[Task]) -> List[Result]:
        """Execute a wave of parallel tasks"""
    
    async def check_convergence(self) -> ConvergenceStatus:
        """Check if research has converged"""
    
    async def reorganize_teams(self) -> List[Team]:
        """Trigger team reorganization"""
```

---

## Scalability Design

### Horizontal Scaling

```python
class DistributedCoordinator:
    """Coordinator with distributed execution support"""
    
    def __init__(self, nodes: List[NodeAddress]):
        self.nodes = nodes
        self.load_balancer = RoundRobinBalancer(nodes)
    
    async def execute_distributed(self, tasks: List[Task]) -> List[Result]:
        """Distribute tasks across nodes"""
        assignments = self.load_balancer.assign(tasks)
        
        futures = []
        for node, node_tasks in assignments.items():
            future = self.execute_remote(node, node_tasks)
            futures.append(future)
        
        results = await asyncio.gather(*futures)
        return list(chain(*results))
```

### State Sharding

For large-scale deployments, shared state is sharded by team_id:

```python
def get_shard(team_id: str, num_shards: int) -> int:
    return hash(team_id) % num_shards
```

---

## Related Documentation

- [Architecture](./architecture.md) - System overview and components
- [Tradeoffs](./tradeoffs.md) - Design decisions
- [Implementation](./implementation.md) - Code examples
- [Evaluation](./evaluation.md) - Performance metrics

---

**Version:** 1.0  
**Last Updated:** 2026-06-02





