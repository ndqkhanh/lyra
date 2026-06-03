# Orchestration System Implementation

**Version**: 2.0  
**Date**: 2026-06-02  
**Status**: Production

---

## Executive Summary

This document provides complete implementation guidance for Lyra's orchestration system: code examples, configuration, deployment, integration patterns, and testing strategies. Follow this guide to integrate orchestration into your agent workflows.

---

## Installation & Setup

### Prerequisites

```bash
# Python 3.11+
python --version  # >= 3.11

# Git (for worktree isolation)
git --version  # >= 2.25

# Optional: Docker (for container isolation)
docker --version  # >= 20.10
```

### Install Package

```bash
cd packages/lyra-orchestration
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

### Verify Installation

```python
from lyra_orchestration import (
    TaskQueue,
    FleetSupervisor,
    EventBus,
    ConsensusProtocol,
    WorktreeIsolation,
)

print("✓ Orchestration package installed")
```

---

## Quick Start Examples

### Example 1: Basic Task Queue

```python
import asyncio
from lyra_orchestration import TaskQueue, TaskPriority

async def main():
    # Initialize task queue
    queue = TaskQueue()
    
    # Register worker
    await queue.register_worker(
        worker_id="worker-1",
        capabilities={"code-review", "testing"},
        max_concurrent=5,
    )
    
    # Enqueue tasks
    task_id = await queue.enqueue(
        queue_name="code-review",
        payload={"file": "src/main.py", "severity": "high"},
        priority=TaskPriority.HIGH,
        max_retries=3,
        timeout=300,
    )
    
    print(f"Task enqueued: {task_id}")
    
    # Wait for completion
    result = await queue.wait_for_completion(task_id, timeout=60)
    print(f"Task result: {result}")

asyncio.run(main())
```

### Example 2: Event-Driven Workflow

```python
from lyra_orchestration import EventBus, AgentCompleted, AgentFailed

async def main():
    bus = EventBus()
    
    # Subscribe to agent completion
    async def handle_completion(event: AgentCompleted):
        print(f"Agent {event.agent_id} completed in {event.duration}s")
        print(f"Tokens used: {event.tokens_used}")
    
    # Subscribe to failures
    async def handle_failure(event: AgentFailed):
        print(f"Agent {event.agent_id} failed: {event.error}")
        # Trigger retry or escalation
    
    bus.subscribe("agent.completed", handle_completion)
    bus.subscribe("agent.failed", handle_failure)
    
    # Simulate agent completion
    await bus.publish(AgentCompleted(
        agent_id="agent-1",
        duration=42.5,
        tokens_used=15000,
        result={"status": "success"},
    ))
    
    await asyncio.sleep(1)  # Let handlers execute

asyncio.run(main())
```

### Example 3: Fleet Supervisor (Background Sessions)

```python
from lyra_orchestration import FleetSupervisor, TaskState

# Initialize supervisor
supervisor = FleetSupervisor()
supervisor.start()

# Dispatch background session
session = supervisor.dispatch(
    prompt="Audit all API endpoints for security vulnerabilities",
    name="security-audit",
    model="claude-opus-4",
    effort="xhigh",
    permission_mode="default",
    auto_worktree=True,
)

print(f"Session started: {session.session_id}")
print(f"Worktree: {session.worktree_path}")

# List all sessions
sessions = supervisor.list_sessions()
for s in sessions:
    print(f"{s.name}: {s.task_state.value} ({s.summary})")

# Resume a paused session
session = supervisor.resume_session(
    session_id=session.session_id,
    prompt="Also check for SQL injection",
)

# Stop session when done
supervisor.stop_session(session.session_id)
supervisor.stop()
```

### Example 4: Consensus Decision

```python
from lyra_orchestration import (
    ConsensusProtocol,
    VotingStrategy,
    VoteChoice,
)

async def main():
    consensus = ConsensusProtocol()
    
    # Create proposal
    proposal_id = await consensus.propose(
        topic="Deploy to production",
        description="Deploy v2.0 with new authentication system",
        options=["approve", "reject"],
        proposer_id="agent-orchestrator",
        voters={"security-agent", "qa-agent", "ops-agent"},
        strategy=VotingStrategy.UNANIMOUS,  # All must approve
        quorum=1.0,
        timeout=300,
    )
    
    # Agents vote
    await consensus.vote(
        proposal_id=proposal_id,
        voter_id="security-agent",
        choice=VoteChoice.APPROVE,
        reason="Security tests passed",
    )
    
    await consensus.vote(
        proposal_id=proposal_id,
        voter_id="qa-agent",
        choice=VoteChoice.APPROVE,
        reason="All E2E tests passed",
    )
    
    await consensus.vote(
        proposal_id=proposal_id,
        voter_id="ops-agent",
        choice=VoteChoice.APPROVE,
        reason="Infrastructure ready",
    )
    
    # Wait for decision
    decision = await consensus.wait_for_decision(proposal_id)
    print(f"Decision: {decision}")  # "approved"
    
    # Get voting stats
    stats = consensus.get_stats(proposal_id)
    print(f"Stats: {stats}")

asyncio.run(main())
```

---

## Configuration

### Task Queue Configuration

```python
# config/orchestration.json
{
  "task_queue": {
    "max_queue_depth": 1000,
    "default_timeout": 300,
    "default_max_retries": 3,
    "worker_heartbeat_interval": 30,
    "worker_heartbeat_timeout": 60
  }
}
```

### Fleet Supervisor Configuration

```python
# config/supervisor.json
{
  "fleet_supervisor": {
    "jobs_dir": "~/.lyra/jobs",
    "idle_timeout": 3600,
    "summary_refresh_interval": 15,
    "auto_pause_idle": true,
    "max_concurrent_sessions": 20
  }
}
```

### Event Bus Configuration

```python
# config/events.json
{
  "event_bus": {
    "max_history_size": 10000,
    "enable_persistence": true,
    "history_dir": "~/.lyra/event_history"
  }
}
```

---

## Integration Patterns

### Pattern 1: Multi-Agent Workflow

```python
from lyra_orchestration import TaskQueue, EventBus

async def multi_agent_workflow():
    """Orchestrate multiple agents for complex task."""
    queue = TaskQueue()
    bus = EventBus()
    
    # Phase 1: Research (parallel)
    research_tasks = [
        await queue.enqueue(
            queue_name="research",
            payload={"topic": f"topic-{i}"},
            priority=TaskPriority.NORMAL,
        )
        for i in range(5)
    ]
    
    # Wait for all research to complete
    research_results = await asyncio.gather(*[
        queue.wait_for_completion(tid)
        for tid in research_tasks
    ])
    
    # Phase 2: Analysis (depends on research)
    analysis_task = await queue.enqueue(
        queue_name="analysis",
        payload={"research": research_results},
        priority=TaskPriority.HIGH,
    )
    
    analysis_result = await queue.wait_for_completion(analysis_task)
    
    # Phase 3: Synthesis
    synthesis_task = await queue.enqueue(
        queue_name="synthesis",
        payload={"analysis": analysis_result},
        priority=TaskPriority.HIGH,
    )
    
    final_result = await queue.wait_for_completion(synthesis_task)
    return final_result
```

### Pattern 2: Adversarial Verification

```python
async def adversarial_verification(action: dict):
    """Verify action through 3-agent consensus."""
    consensus = ConsensusProtocol()
    
    proposal_id = await consensus.propose(
        topic=f"Verify action: {action['type']}",
        description=action["description"],
        options=["approve", "reject"],
        proposer_id="executor-agent",
        voters={"critic-1", "critic-2", "critic-3"},
        strategy=VotingStrategy.MAJORITY,
        quorum=0.67,  # Need 2/3 participation
        timeout=60,
    )
    
    # Critics evaluate in parallel
    await asyncio.gather(
        consensus.vote(proposal_id, "critic-1", VoteChoice.APPROVE),
        consensus.vote(proposal_id, "critic-2", VoteChoice.APPROVE),
        consensus.vote(proposal_id, "critic-3", VoteChoice.REJECT),
    )
    
    decision = await consensus.wait_for_decision(proposal_id)
    
    if decision == "approved":
        # Execute action
        return execute_action(action)
    else:
        # Block and log
        return {"status": "blocked", "reason": "Failed consensus"}
```

### Pattern 3: Worktree Isolation

```python
from lyra_orchestration import WorktreeIsolation, WorktreeConfig

def isolated_agent_execution(task: dict):
    """Execute agent in isolated git worktree."""
    iso = WorktreeIsolation()
    
    # Create worktree
    config = WorktreeConfig(
        name=f"agent-{task['id']}",
        include_patterns=[".env", ".env.local"],
    )
    
    status = iso.create(name=config.name, config=config)
    
    try:
        # Execute agent in worktree
        result = execute_agent(
            task=task,
            working_dir=status.path,
        )
        
        # Create PR from worktree
        if result["status"] == "success":
            create_pr_from_worktree(status.path, task["description"])
        
        return result
    finally:
        # Cleanup
        iso.remove(config.name, action=CleanupAction.STASH)
```

### Pattern 4: Background Session with Progress

```python
def background_research_session(topic: str):
    """Long-running research in background with progress tracking."""
    supervisor = FleetSupervisor()
    supervisor.start()
    
    # Dispatch
    session = supervisor.dispatch(
        prompt=f"Research {topic} comprehensively",
        name=f"research-{topic}",
        effort="xhigh",
        auto_worktree=True,
    )
    
    # Monitor progress
    while True:
        state = supervisor.get_session(session.session_id)
        
        if state.task_state == TaskState.COMPLETED:
            print(f"✓ Research completed: {state.summary}")
            break
        elif state.task_state == TaskState.FAILED:
            print(f"✗ Research failed: {state.error_message}")
            break
        elif state.task_state == TaskState.NEEDS_INPUT:
            print(f"⏸ Waiting for input: {state.summary}")
            # Provide input and resume
            supervisor.resume_session(session.session_id, "Continue")
        
        print(f"⏳ {state.summary} ({state.turns_completed} turns)")
        time.sleep(10)
    
    supervisor.stop()
```

---

## Testing Strategies

### Unit Testing

```python
import pytest
from lyra_orchestration import TaskQueue, TaskPriority

@pytest.mark.asyncio
async def test_task_enqueue():
    """Test task enqueue and assignment."""
    queue = TaskQueue()
    
    # Register worker
    success = await queue.register_worker(
        worker_id="test-worker",
        capabilities={"test"},
        max_concurrent=5,
    )
    assert success
    
    # Enqueue task
    task_id = await queue.enqueue(
        queue_name="test",
        payload={"data": "test"},
        priority=TaskPriority.NORMAL,
    )
    assert task_id
    
    # Verify task assigned
    await asyncio.sleep(0.1)  # Let assignment happen
    status = queue.get_task_status(task_id)
    assert status == TaskStatus.ASSIGNED
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_multi_agent_coordination():
    """Test multiple agents coordinating through event bus."""
    queue = TaskQueue()
    bus = EventBus()
    
    # Track events
    events = []
    async def track_event(event):
        events.append(event)
    
    bus.subscribe("agent.completed", track_event)
    
    # Register workers
    await queue.register_worker("agent-1", {"process"})
    await queue.register_worker("agent-2", {"process"})
    
    # Enqueue parallel tasks
    tasks = [
        await queue.enqueue("process", {"id": i})
        for i in range(10)
    ]
    
    # Simulate completion
    for task_id in tasks:
        await queue.complete_task(task_id, "agent-1", {"status": "done"})
        await bus.publish(AgentCompleted(
            agent_id="agent-1",
            duration=1.0,
            tokens_used=100,
            result={},
        ))
    
    # Verify
    assert len(events) == 10
```

### Performance Testing

```python
@pytest.mark.performance
async def test_task_throughput():
    """Test task queue throughput under load."""
    queue = TaskQueue()
    
    # Register 10 workers
    for i in range(10):
        await queue.register_worker(f"worker-{i}", {"load-test"})
    
    # Enqueue 1000 tasks
    start = time.time()
    tasks = [
        await queue.enqueue("load-test", {"id": i})
        for i in range(1000)
    ]
    enqueue_time = time.time() - start
    
    # Complete all tasks
    start = time.time()
    for task_id in tasks:
        await queue.complete_task(task_id, "worker-0", {})
    complete_time = time.time() - start
    
    print(f"Enqueue: {1000/enqueue_time:.0f} tasks/s")
    print(f"Complete: {1000/complete_time:.0f} tasks/s")
    
    assert enqueue_time < 1.0  # >1000 tasks/s
    assert complete_time < 2.0  # >500 tasks/s
```

### End-to-End Testing

```python
@pytest.mark.e2e
async def test_full_orchestration_workflow():
    """Test complete orchestration workflow."""
    queue = TaskQueue()
    bus = EventBus()
    supervisor = FleetSupervisor()
    consensus = ConsensusProtocol()
    
    # 1. Dispatch background session
    session = supervisor.dispatch(
        prompt="Analyze codebase security",
        name="security-analysis",
    )
    
    # 2. Session enqueues tasks
    task_id = await queue.enqueue("analysis", {"target": "src/"})
    
    # 3. Task completes, publishes event
    await queue.complete_task(task_id, "worker-1", {"findings": 5})
    await bus.publish(AgentCompleted(
        agent_id="worker-1",
        duration=30.0,
        tokens_used=5000,
        result={"findings": 5},
    ))
    
    # 4. Findings trigger consensus
    proposal_id = await consensus.propose(
        topic="Fix critical findings",
        voters={"agent-1", "agent-2"},
        strategy=VotingStrategy.MAJORITY,
    )
    
    # 5. Vote and decide
    await consensus.vote(proposal_id, "agent-1", VoteChoice.APPROVE)
    await consensus.vote(proposal_id, "agent-2", VoteChoice.APPROVE)
    decision = await consensus.wait_for_decision(proposal_id)
    
    # Verify
    assert decision == "approved"
    assert session.task_state in (TaskState.WORKING, TaskState.COMPLETED)
```

---

## Deployment

### Development Deployment

```bash
# Single-machine development
python -m lyra_orchestration.supervisor &  # Start daemon
python your_agent.py  # Run agent
```

### Production Deployment (Single-Node)

```bash
# 1. Install package
pip install lyra-orchestration

# 2. Configure
cat > /etc/lyra/orchestration.conf <<EOF
[supervisor]
jobs_dir = /var/lib/lyra/jobs
idle_timeout = 3600
max_concurrent_sessions = 50

[task_queue]
max_queue_depth = 5000
default_timeout = 600
EOF

# 3. Start supervisor as systemd service
cat > /etc/systemd/system/lyra-supervisor.service <<EOF
[Unit]
Description=Lyra Fleet Supervisor
After=network.target

[Service]
Type=simple
User=lyra
ExecStart=/usr/bin/python -m lyra_orchestration.supervisor
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl enable lyra-supervisor
systemctl start lyra-supervisor
```

### Production Deployment (Distributed)

```yaml
# docker-compose.yml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
  
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: lyra
      POSTGRES_USER: lyra
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
  
  supervisor:
    image: lyra-orchestration:latest
    environment:
      REDIS_URL: redis://redis:6379
      DATABASE_URL: postgresql://lyra:${DB_PASSWORD}@postgres:5432/lyra
    depends_on:
      - redis
      - postgres
    deploy:
      replicas: 3

volumes:
  redis-data:
  postgres-data:
```

---

## Monitoring & Observability

### Built-in Metrics

```python
# Task queue stats
stats = queue.get_queue_stats("code-review")
print(f"Pending: {stats['pending']}")
print(f"In progress: {stats['in_progress']}")
print(f"Completed: {stats['completed']}")

# Worker stats
worker_stats = queue.get_worker_stats("worker-1")
print(f"Active tasks: {worker_stats['active_tasks']}")

# Supervisor stats
supervisor_stats = supervisor.stats
print(f"Total sessions: {supervisor_stats['total_sessions']}")
print(f"Alive: {supervisor_stats['alive']}")
```

### Custom Metrics Integration

```python
from prometheus_client import Counter, Histogram

tasks_enqueued = Counter('tasks_enqueued', 'Total tasks enqueued')
task_duration = Histogram('task_duration_seconds', 'Task duration')

# Wrap task queue
original_enqueue = queue.enqueue

async def monitored_enqueue(*args, **kwargs):
    tasks_enqueued.inc()
    start = time.time()
    result = await original_enqueue(*args, **kwargs)
    task_duration.observe(time.time() - start)
    return result

queue.enqueue = monitored_enqueue
```

---

## Troubleshooting

### Common Issues

**Issue**: Tasks not assigned to workers  
**Solution**: Check worker capabilities match queue name

```python
# Debug worker registration
workers = queue._workers  # Internal state for debugging
for wid, worker in workers.items():
    print(f"{wid}: {worker.capabilities}")
```

**Issue**: Worktree creation fails  
**Solution**: Ensure git repository and sufficient disk space

```bash
# Check git status
git worktree list

# Check disk space
df -h
```

**Issue**: Events not delivered  
**Solution**: Verify event type matches subscription

```python
# Debug event bus
subscriptions = bus._subscribers
for event_type, handlers in subscriptions.items():
    print(f"{event_type}: {len(handlers)} handlers")
```

---

## Related Documentation

- [Architecture](./architecture.md) - System overview
- [System Design](./system-design.md) - Data models and algorithms
- [Tradeoffs](./tradeoffs.md) - Design decisions
- [Evaluation](./evaluation.md) - Performance benchmarks

---

<div align="center">

**Lyra Orchestration Implementation Guide**

Version 2.0 | 2026-06-02 | Production

[← Tradeoffs](./tradeoffs.md) · [Evaluation →](./evaluation.md)

</div>
