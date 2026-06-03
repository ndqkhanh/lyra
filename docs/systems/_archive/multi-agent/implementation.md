# Multi-Agent System Implementation Guide

**Version:** 1.0  
**Date:** 2026-06-02  
**Status:** Production

---

## Executive Summary

Practical implementation guide for deploying Lyra's multi-agent system, including setup instructions, configuration examples, integration patterns, and testing strategies.

---

## Table of Contents

1. [Setup and Installation](#setup-and-installation)
2. [Configuration](#configuration)
3. [Code Examples](#code-examples)
4. [Integration Patterns](#integration-patterns)
5. [Testing Strategies](#testing-strategies)
6. [Deployment](#deployment)

---

## Setup and Installation

### Prerequisites

```bash
# System requirements
- Python 3.11+
- Git 2.40+
- Redis 7.0+ (optional for production)
- 16GB RAM minimum
- 4+ CPU cores

# Install dependencies
pip install lyra-core langgraph redis chromadb opentelemetry-api mlflow
```

### Quick Start

```python
from lyra_core.swarm import SwarmCoordinator, SwarmConfig
from lyra_core.agents import AnalystAgent, ExperimenterAgent, CriticAgent

# Initialize configuration
config = SwarmConfig(
    max_iterations=1000,
    team_config={
        "min_team_size": 2,
        "max_team_size": 5,
        "stagnation_threshold": 0.7
    },
    worker_config={
        "n_analysts": 3,
        "n_experimenters": 8,
        "n_critics": 2,
        "n_synthesizers": 1
    }
)

# Create coordinator
coordinator = SwarmCoordinator(config)

# Define research task
task = ResearchTask(
    name="optimize-model",
    objective="Improve model accuracy",
    baseline=load_baseline(),
    evaluation_fn=evaluate_model
)

# Execute
results = await coordinator.execute_research_task(task)
print(f"Best solution: {results.champion.score}")
```

---

## Configuration

### swarm_config.yaml

```yaml
# Core swarm settings
swarm:
  max_iterations: 1000
  heartbeat_interval: 10  # seconds
  convergence_check_interval: 30
  
# Team formation
team:
  min_team_size: 2
  max_team_size: 5
  stagnation_threshold: 0.7  # 70% failure rate triggers reorganization
  reorganization_cooldown: 300  # seconds
  
# Convergence criteria
convergence:
  min_effect_size: 0.01
  plateau_threshold: 0.001
  lookback_window: 20
  max_duration: 86400  # 24 hours
  
# Worker pool
worker:
  n_analysts: 3
  n_experimenters: 8
  n_critics: 2
  n_synthesizers: 1
  max_concurrent_experiments: 5
  
# Model routing
models:
  fast_slot: "deepseek-v4-flash"
  smart_slot: "deepseek-v4-pro"
  subagent_slot: "smart"  # Always use smart for subagents
  
# Storage
storage:
  backend: "sqlite"  # or "postgres"
  path: ".lyra/swarm/state.db"
  redis_url: "redis://localhost:6379/0"
  enable_caching: true
  
# Observability
observability:
  enable_tracing: true
  enable_metrics: true
  mlflow_uri: "file://.lyra/mlruns"
  log_level: "INFO"
  
# Subagent settings
subagent:
  worktree_base: ".lyra/worktrees"
  max_concurrent_subagents: 10
  default_budget:
    max_steps: 50
    max_cost_usd: 5.0
    max_duration_seconds: 600
```

---

## Code Examples

### Example 1: Spawning a Subagent

```python
from lyra_core.subagent import Subagent, Budgets

# Spawn isolated subagent
sub = Subagent(
    parent=session,
    purpose="Analyze authentication module for security issues",
    scope=["src/auth/**", "tests/auth/**"],
    worktree_branch=f"sub-auth-analysis-{session.id}",
    budgets=Budgets(
        max_steps=30,
        max_cost_usd=2.0,
        max_duration=timedelta(minutes=10)
    ),
    allowed_tools=["read", "grep", "ast_search", "lsp_diagnostics"],
    return_shape="observation"
)

# Execute and get summary
result = sub.run()
print(f"Security findings: {result.observation}")
```

### Example 2: Fan-Out Pattern

```python
from lyra_core.fleet import FleetOrchestrator

async def analyze_modules(modules: List[str]):
    """Analyze multiple modules in parallel"""
    
    fleet = FleetOrchestrator(session)
    
    # Create tasks
    tasks = [
        Task(
            id=f"analyze-{module}",
            description=f"Analyze {module} for code quality issues",
            scope=[f"src/{module}/**"],
            required_capabilities=["code_analysis"]
        )
        for module in modules
    ]
    
    # Execute in parallel
    results = await fleet.execute_fan_out(tasks)
    
    # Aggregate results
    all_issues = []
    for module, result in zip(modules, results):
        all_issues.extend(result.issues)
    
    return all_issues
```

### Example 3: Wave-Based Execution

```python
async def build_and_test():
    """Execute build → test → deploy pipeline"""
    
    # Define tasks with dependencies
    tasks = [
        Task(id="install", dependencies=[]),
        Task(id="lint", dependencies=["install"]),
        Task(id="test_unit", dependencies=["install"]),
        Task(id="test_integration", dependencies=["install", "test_unit"]),
        Task(id="build", dependencies=["lint", "test_integration"]),
        Task(id="deploy", dependencies=["build"])
    ]
    
    # Build dependency waves
    waves = build_dependency_waves(tasks)
    
    # Execute wave by wave
    completed = set()
    for wave in waves:
        results = await asyncio.gather(*[
            execute_task(task) for task in wave
        ])
        completed.update(task.id for task in wave)
    
    return completed
```

### Example 4: Team Formation

```python
from lyra_core.swarm import TeamFormationEngine

async def dynamic_research(problem: str):
    """Research with dynamic team formation"""
    
    engine = TeamFormationEngine(config)
    state = LyraSharedState()
    
    # Initial hypothesis generation
    hypotheses = await generate_hypotheses(problem)
    
    # Form teams
    teams = engine.form_teams(worker_pool.agents, state)
    
    # Execute research iterations
    iteration = 0
    while not converged:
        # Each team works on its hypothesis
        await asyncio.gather(*[
            execute_team_iteration(team, state)
            for team in teams
        ])
        
        # Check for stagnation and reorganize
        for team in teams:
            if engine.should_reorganize(team, state):
                teams = engine.reorganize(teams, state)
                break
        
        iteration += 1
    
    return state.champions
```

### Example 5: Consensus Building

```python
from lyra_core.consensus import ConsensusBuilder, ConsensusMethod

async def multi_agent_decision(problem: str):
    """Get consensus from multiple agents"""
    
    agents = [
        AnalystAgent("analyst-1"),
        AnalystAgent("analyst-2"),
        CriticAgent("critic-1")
    ]
    
    # Collect votes
    votes = []
    for agent in agents:
        proposal, confidence = await agent.propose_solution(problem)
        votes.append((agent, proposal, confidence))
    
    # Build consensus
    builder = ConsensusBuilder()
    consensus = builder.aggregate_votes(
        votes,
        method=ConsensusMethod.WEIGHTED,
        threshold=0.7
    )
    
    if consensus:
        print(f"Consensus reached: {consensus}")
    else:
        print("No consensus - escalating to human review")
    
    return consensus
```

---

## Integration Patterns

### Pattern 1: RAG + Multi-Agent

```python
from lyra_core.rag import RAGSystem
from lyra_core.swarm import SwarmCoordinator

class RAGEnhancedSwarm:
    def __init__(self):
        self.rag = RAGSystem()
        self.swarm = SwarmCoordinator()
    
    async def research_with_retrieval(self, query: str):
        # Retrieve relevant documents
        docs = await self.rag.retrieve(query, top_k=10)
        
        # Spawn analyst agents with context
        tasks = [
            Task(
                description=f"Analyze aspect: {aspect}",
                context=docs,
                required_capabilities=["analysis"]
            )
            for aspect in extract_aspects(query)
        ]
        
        # Execute in parallel
        results = await self.swarm.execute_fan_out(tasks)
        
        # Synthesize final answer
        answer = await self.synthesize(results, docs)
        return answer
```

### Pattern 2: Autonomous Planning + Multi-Agent

```python
from lyra_core.planning import GoalDecomposer
from lyra_core.swarm import SwarmCoordinator

async def autonomous_feature_development(feature: str):
    # Decompose feature into tasks
    decomposer = GoalDecomposer()
    task_dag = decomposer.decompose(feature)
    
    # Build execution waves
    waves = build_dependency_waves(task_dag)
    
    # Execute with multi-agent swarm
    coordinator = SwarmCoordinator()
    
    for wave in waves:
        results = await coordinator.execute_wave(wave)
        
        # Check if we need to re-plan
        if any(r.status == "failed" for r in results):
            task_dag = decomposer.replan(task_dag, results)
            waves = build_dependency_waves(task_dag)
    
    return results
```

### Pattern 3: Human-in-the-Loop Multi-Agent

```python
class HITLSwarm:
    async def execute_with_approval(self, task: Task):
        # Generate proposals
        proposals = await self.generate_proposals(task)
        
        # Critic review
        critiques = await self.review_proposals(proposals)
        
        # High-risk proposals need human approval
        for proposal, critique in zip(proposals, critiques):
            if critique.severity == "high":
                approved = await self.request_human_approval(
                    proposal, critique
                )
                if not approved:
                    continue
            
            # Execute approved proposals
            result = await self.execute_proposal(proposal)
            yield result
```

---

## Testing Strategies

### Unit Tests

```python
import pytest
from lyra_core.swarm import SwarmCoordinator, SwarmConfig

def test_wave_construction():
    """Test dependency wave construction"""
    tasks = [
        Task(id="A", dependencies=[]),
        Task(id="B", dependencies=["A"]),
        Task(id="C", dependencies=["A"]),
        Task(id="D", dependencies=["B", "C"])
    ]
    
    waves = build_dependency_waves(tasks)
    
    assert len(waves) == 3
    assert {t.id for t in waves[0]} == {"A"}
    assert {t.id for t in waves[1]} == {"B", "C"}
    assert {t.id for t in waves[2]} == {"D"}

def test_cyclic_dependency_detection():
    """Test cycle detection"""
    tasks = [
        Task(id="A", dependencies=["B"]),
        Task(id="B", dependencies=["A"])
    ]
    
    with pytest.raises(CyclicDependencyError):
        build_dependency_waves(tasks)

def test_capability_matching():
    """Test agent-task matching"""
    agent = Agent(
        id="agent-1",
        capabilities=["python", "testing"]
    )
    
    task = Task(
        id="task-1",
        required_capabilities=["python"]
    )
    
    score = compute_match_score(agent, task)
    assert score > 0.5  # Good match
```

### Integration Tests

```python
@pytest.mark.integration
async def test_fan_out_execution():
    """Test parallel fan-out execution"""
    coordinator = SwarmCoordinator(SwarmConfig.default())
    
    tasks = [
        Task(id=f"task-{i}", description=f"Task {i}")
        for i in range(5)
    ]
    
    results = await coordinator.execute_fan_out(tasks)
    
    assert len(results) == 5
    assert all(r.status == "completed" for r in results)

@pytest.mark.integration
async def test_team_reorganization():
    """Test dynamic team reorganization"""
    engine = TeamFormationEngine(config)
    state = LyraSharedState()
    
    # Create stagnated team
    team = Team(id="team-1", hypothesis=hypothesis, agents=agents)
    
    # Simulate failures
    for _ in range(10):
        state.write(agent, ExperimentResult(
            status="failed",
            team_id=team.id
        ))
    
    # Should trigger reorganization
    assert engine.should_reorganize(team, state)
    
    new_teams = engine.reorganize([team], state)
    assert len(new_teams) >= 1
```

### End-to-End Tests

```python
@pytest.mark.e2e
async def test_full_research_workflow():
    """Test complete research workflow"""
    config = SwarmConfig(max_iterations=50)
    coordinator = SwarmCoordinator(config)
    
    task = ResearchTask(
        name="optimize-test",
        objective="Improve test metric",
        baseline=MockSolution(score=0.5),
        evaluation_fn=mock_evaluate
    )
    
    results = await coordinator.execute_research_task(task)
    
    # Should find improvement
    assert results.champion.score > 0.5
    assert len(results.experiment_log) > 0
    assert results.convergence_status.should_stop
```

---

## Deployment

### Local Development

```bash
# Start Redis (optional for dev)
docker run -d -p 6379:6379 redis:7-alpine

# Run with hot reload
python -m lyra.cli swarm start \
    --config dev_config.yaml \
    --log-level DEBUG

# Monitor in another terminal
python -m lyra.cli swarm status --watch
```

### Production Deployment

```bash
# Using Docker Compose
docker-compose up -d

# Or Kubernetes
kubectl apply -f k8s/swarm-deployment.yaml

# Health check
curl http://localhost:8000/health
```

**Docker Compose Example:**

```yaml
version: '3.8'
services:
  coordinator:
    image: lyra/swarm-coordinator:latest
    environment:
      - REDIS_URL=redis://redis:6379
      - MLFLOW_URI=http://mlflow:5000
    depends_on:
      - redis
      - mlflow
    
  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
  
  mlflow:
    image: ghcr.io/mlflow/mlflow:latest
    ports:
      - "5000:5000"
    volumes:
      - mlflow-data:/mlflow

volumes:
  redis-data:
  mlflow-data:
```

### Monitoring

```python
# Prometheus metrics
from prometheus_client import Counter, Histogram

task_completions = Counter(
    'lyra_task_completions_total',
    'Total task completions',
    ['status']
)

task_duration = Histogram(
    'lyra_task_duration_seconds',
    'Task execution duration'
)
```

---

## Related Documentation

- [Architecture](./architecture.md) - System overview
- [System Design](./system-design.md) - Technical details
- [Tradeoffs](./tradeoffs.md) - Design decisions
- [Evaluation](./evaluation.md) - Performance metrics

---

**Version:** 1.0  
**Last Updated:** 2026-06-02
