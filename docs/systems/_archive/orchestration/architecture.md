# Orchestration System Architecture

**Version**: 2.0  
**Date**: 2026-06-02  
**Status**: Production

---

## Executive Summary

Lyra's orchestration system enables sophisticated multi-agent coordination through distributed task queues, consensus protocols, event-driven communication, and worktree isolation. The system supports parallel agent execution, adversarial verification, typed inter-agent communication, and fleet management for autonomous research and complex task decomposition.

### Core Capabilities

1. **Fleet Supervisor**: Per-user daemon managing background agent sessions with lifecycle control
2. **Task Queue System**: Priority-based distributed task scheduling with retry logic
3. **Consensus Protocol**: Multi-strategy voting for agent decisions (majority, unanimous, weighted, quorum)
4. **Event Bus**: Typed pub/sub for cross-agent communication with zero serialization overhead
5. **Worktree Isolation**: Git-based process isolation for safe concurrent file editing
6. **Security Gate**: Multi-layer authorization with adversarial verification

---

## System Architecture

### High-Level Overview

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TB
    subgraph "Entry Layer"
        CLI[CLI Entry]
        TUI[Terminal UI]
        API[API Gateway]
    end
    
    subgraph "Orchestration Core"
        FS[Fleet Supervisor<br/>Background Session Manager]
        TQ[Task Queue<br/>Work Distribution]
        EB[Event Bus<br/>Typed Pub/Sub]
        CP[Consensus Protocol<br/>Decision Making]
    end
    
    subgraph "Isolation Layer"
        WI[Worktree Isolation<br/>Git-Based Sandboxing]
        COW[Copy-on-Write<br/>Fast Fork]
        SG[Security Gate<br/>Authorization]
    end
    
    subgraph "Agent Pool"
        A1[Agent 1]
        A2[Agent 2]
        A3[Agent 3]
        AN[Agent N]
    end
    
    subgraph "Storage"
        Jobs[(Jobs DB<br/>~/.lyra/jobs)]
        State[(State Store<br/>Session State)]
        History[(Event History<br/>Audit Log)]
    end
    
    CLI --> FS
    TUI --> FS
    API --> FS
    
    FS --> TQ
    FS --> EB
    FS --> WI
    
    TQ --> CP
    TQ --> A1
    TQ --> A2
    TQ --> A3
    TQ --> AN
    
    A1 --> EB
    A2 --> EB
    A3 --> EB
    AN --> EB
    
    WI --> SG
    SG --> A1
    SG --> A2
    
    FS --> Jobs
    FS --> State
    EB --> History
    
    style FS fill:#7c3aed20,stroke:#7c3aed,stroke-width:2px
    style TQ fill:#3b82f620,stroke:#3b82f6,stroke-width:2px
    style EB fill:#f59e0b20,stroke:#f59e0b,stroke-width:2px
    style CP fill:#10b98120,stroke:#10b981,stroke-width:2px
```

---

## Core Components

### 1. Fleet Supervisor

**Purpose**: Per-user daemon that manages lifecycle of background agent sessions.

**Key Features**:
- Survives terminal close and machine sleep
- Each session runs as independent process
- State persisted to `~/.lyra/jobs/<session_id>/`
- Idle sessions auto-paused after 1 hour
- Self-exits when no active sessions
- Worktree isolation for parallel editing

**State Model** (Two orthogonal axes):

```mermaid
%%{init: {'theme': 'dark'}}%%
stateDiagram-v2
    [*] --> WORKING: Dispatch
    WORKING --> NEEDS_INPUT: Blocked
    WORKING --> COMPLETED: Success
    WORKING --> FAILED: Error
    NEEDS_INPUT --> WORKING: Input provided
    COMPLETED --> [*]
    FAILED --> [*]
    WORKING --> IDLE: No activity
    IDLE --> WORKING: Resume
    IDLE --> STOPPED: Stop
    STOPPED --> [*]
```

**Process Liveness States**:
- `ALIVE`: Process running
- `EXITED_RESUMABLE`: Process stopped, can restart from disk
- `LOOP_SLEEPING`: In sleep/wait cycle
- `DEAD`: Terminated, cannot resume

### 2. Task Queue System

**Purpose**: Distributed task queue for priority-based work distribution.

**Architecture**:

```mermaid
%%{init: {'theme': 'dark'}}%%
graph LR
    subgraph "Task Queues"
        Q1[Queue: high-priority]
        Q2[Queue: normal]
        Q3[Queue: low-priority]
    end
    
    subgraph "Workers"
        W1[Worker 1<br/>Capabilities: A,B]
        W2[Worker 2<br/>Capabilities: B,C]
        W3[Worker 3<br/>Capabilities: A,C]
    end
    
    subgraph "Dead Letter"
        DLQ[Failed Tasks]
    end
    
    Q1 --> W1
    Q2 --> W2
    Q3 --> W3
    
    W1 -->|Failure| DLQ
    W2 -->|Failure| DLQ
    
    style Q1 fill:#ef444420,stroke:#ef4444,stroke-width:2px
    style Q2 fill:#f59e0b20,stroke:#f59e0b,stroke-width:2px
    style Q3 fill:#10b98120,stroke:#10b981,stroke-width:2px
```

**Features**:
- Priority-based scheduling (CRITICAL > HIGH > NORMAL > LOW)
- Worker capability matching
- Max concurrent tasks per worker (default: 5)
- Automatic retry (max 3 attempts)
- Timeout handling (default: 300s)
- Dead letter queue for persistent failures

### 3. Event Bus

**Purpose**: Typed pub/sub system for cross-agent communication.

**Event Flow**:

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant A1 as Agent 1 (Publisher)
    participant Bus as Event Bus
    participant S1 as Subscriber 1
    participant S2 as Subscriber 2
    participant S3 as Subscriber 3
    
    A1->>Bus: publish(ScanCompleted)
    Bus->>Bus: Validate schema
    Bus->>Bus: Priority queue
    
    par Parallel Delivery
        Bus->>S1: ScanCompleted event
        Bus->>S2: ScanCompleted event
        Bus->>S3: ScanCompleted event
    end
    
    S1-->>Bus: Handled
    S2-->>Bus: Handled
    S3-->>Bus: Handled
    
    Bus->>Bus: Record in history
```

**Domain Events**:
- `AgentStarted`, `AgentCompleted`, `AgentFailed`
- `ScanCompleted`, `VulnerabilityDiscovered`
- `ExploitAttempted`, `MemoryIngested`
- `IntegrationSynced`

**Performance**:
- Event delivery: <1ms per event
- Zero serialization overhead (native Python objects)
- Memory overhead: ~100KB per 1000 events

### 4. Consensus Protocol

**Purpose**: Multi-strategy voting for agent decisions.

**Voting Strategies**:

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TB
    Proposal[Proposal] --> Strategy{Select Strategy}
    
    Strategy -->|>50% required| Majority[Majority Voting]
    Strategy -->|100% required| Unanimous[Unanimous Voting]
    Strategy -->|Expertise-weighted| Weighted[Weighted Voting]
    Strategy -->|Min participation| Quorum[Quorum Voting]
    
    Majority --> Vote1[Cast Votes]
    Unanimous --> Vote2[Cast Votes]
    Weighted --> Vote3[Cast Votes]
    Quorum --> Vote4[Cast Votes]
    
    Vote1 --> Decision{Decision Ready?}
    Vote2 --> Decision
    Vote3 --> Decision
    Vote4 --> Decision
    
    Decision -->|Yes| Approved[Approved/Rejected]
    Decision -->|Timeout| Timeout[Timeout]
    
    style Proposal fill:#7c3aed20,stroke:#7c3aed,stroke-width:2px
    style Approved fill:#10b98120,stroke:#10b981,stroke-width:2px
    style Timeout fill:#ef444420,stroke:#ef4444,stroke-width:2px
```

### 5. Worktree Isolation

**Purpose**: Git worktree-based process isolation for safe concurrent operations.

**Isolation Model**:

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TB
    subgraph "Main Repository"
        Main[main branch<br/>Primary workspace]
    end
    
    subgraph "Worktrees"
        WT1[worktree-session-1<br/>Agent 1]
        WT2[worktree-session-2<br/>Agent 2]
        WT3[worktree-session-3<br/>Agent 3]
    end
    
    Main -.create.-> WT1
    Main -.create.-> WT2
    Main -.create.-> WT3
    
    WT1 -->|merge/PR| Main
    WT2 -->|merge/PR| Main
    WT3 -->|merge/PR| Main
    
    style Main fill:#7c3aed20,stroke:#7c3aed,stroke-width:2px
    style WT1 fill:#3b82f620,stroke:#3b82f6,stroke-width:2px
    style WT2 fill:#f59e0b20,stroke:#f59e0b,stroke-width:2px
    style WT3 fill:#10b98120,stroke:#10b981,stroke-width:2px
```

**Features**:
- 200-500ms creation time (vs 2-10s for containers)
- No Docker daemon required
- Built-in git integration
- Copy-on-write for efficiency
- `.worktreeinclude` for shared configs
- Non-destructive cleanup (STASH by default)

---

## Technology Stack

### Core Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Runtime | Python 3.11+ | Core orchestration logic |
| Concurrency | asyncio | Async event handling |
| Persistence | JSON | Session state storage |
| Isolation | Git worktrees | Process sandboxing |
| IPC | Native Python | Zero-overhead communication |
| Schema Validation | Pydantic (event_bus.py only) | Event type validation |

### Dependencies

```python
# Core
asyncio         # Async runtime
dataclasses     # Data structures (most modules use frozen dataclasses)
enum            # Type-safe enums
typing          # Type hints
pathlib         # Path operations
json            # State serialization

# External
pydantic>=2.0          # Schema validation (event_bus.py uses BaseModel)
typing-extensions>=4.5  # Extended typing support
```

**Note**: Most orchestration modules (consensus.py, task_queue.py, coordinator.py, fleet_supervisor.py) use standard Python dataclasses with `frozen=True`, not Pydantic. Only `event_bus.py` uses Pydantic for event schema validation. The task_queue.py and consensus.py modules are independent components -- they are not wired together in the described Task Queue → Consensus Protocol pipeline. Each can be used standalone.

---

## Integration Points

### With Agent Loop

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant Loop as Agent Loop
    participant FS as Fleet Supervisor
    participant TQ as Task Queue
    participant Agent as Worker Agent
    
    Loop->>FS: dispatch(prompt)
    FS->>FS: Create session
    FS->>TQ: enqueue(task)
    TQ->>Agent: assign(task)
    Agent->>Agent: Execute
    Agent-->>TQ: complete(result)
    TQ-->>FS: Task completed
    FS-->>Loop: Session result
```

### With Memory System

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    Agents[Agent Swarm] --> Events[Generate Events]
    Events --> EventBus[Event Bus]
    EventBus --> Memory[Memory System]
    Memory --> Episodic[Episodic Memory]
    Memory --> Semantic[Semantic Memory]
    
    Semantic --> Context[Context Retrieval]
    Context --> Agents
    
    style Agents fill:#7c3aed20,stroke:#7c3aed,stroke-width:2px
    style Memory fill:#3b82f620,stroke:#3b82f6,stroke-width:2px
```

### With Safety System

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    Agent[Agent Action] --> Gate[Security Gate]
    Gate --> Classify{Action Type}
    
    Classify -->|Read-only| Execute[Execute Immediately]
    Classify -->|Mutating| Verify[Adversarial Verification]
    
    Verify --> Panel[3-Critic Panel]
    Panel --> Consensus[Consensus Protocol]
    
    Consensus -->|Approved| Execute
    Consensus -->|Rejected| Block[Block + Log]
    
    Execute --> Result[Action Result]
    Block --> Alert[Alert User]
    
    style Gate fill:#7c3aed20,stroke:#7c3aed,stroke-width:2px
    style Verify fill:#f59e0b20,stroke:#f59e0b,stroke-width:2px
    style Block fill:#ef444420,stroke:#ef4444,stroke-width:2px
```

---

## Deployment Architecture

### Single-User Deployment

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TB
    subgraph "User Machine"
        CLI[CLI Process]
        Supervisor[Fleet Supervisor<br/>Daemon]
        
        subgraph "Agent Processes"
            A1[Agent 1]
            A2[Agent 2]
            A3[Agent N]
        end
        
        subgraph "Storage"
            Jobs[~/.lyra/jobs/]
            State[~/.lyra/state/]
        end
    end
    
    CLI --> Supervisor
    Supervisor --> A1
    Supervisor --> A2
    Supervisor --> A3
    
    Supervisor --> Jobs
    Supervisor --> State
    
    style Supervisor fill:#7c3aed20,stroke:#7c3aed,stroke-width:2px
```

### Multi-User Deployment (Future)

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TB
    subgraph "Load Balancer"
        LB[nginx/HAProxy]
    end
    
    subgraph "Fleet Supervisor Cluster"
        FS1[Supervisor 1]
        FS2[Supervisor 2]
        FS3[Supervisor N]
    end
    
    subgraph "Shared Services"
        Redis[(Redis<br/>Task Queue)]
        Postgres[(PostgreSQL<br/>State Store)]
        S3[(S3<br/>Artifact Storage)]
    end
    
    LB --> FS1
    LB --> FS2
    LB --> FS3
    
    FS1 --> Redis
    FS2 --> Redis
    FS3 --> Redis
    
    FS1 --> Postgres
    FS2 --> Postgres
    FS3 --> Postgres
    
    style Redis fill:#ef444420,stroke:#ef4444,stroke-width:2px
    style Postgres fill:#3b82f620,stroke:#3b82f6,stroke-width:2px
    style S3 fill:#f59e0b20,stroke:#f59e0b,stroke-width:2px
```

---

## Performance Characteristics

### Scalability Metrics

| Metric | Current | Target | Notes |
|--------|---------|--------|-------|
| Concurrent agents | 10-20 | 100+ | Per supervisor |
| Tasks/second | 5-10 | 100+ | With distributed queue |
| Event delivery | <1ms | <1ms | In-memory |
| Session startup | 200-500ms | <200ms | Worktree creation |
| Memory per session | ~50MB | ~50MB | Includes agent |

### Bottlenecks

1. **Worktree creation**: 200-500ms per worktree (git operation)
2. **File I/O**: JSON serialization for state persistence
3. **Process spawning**: Python process startup overhead
4. **Git operations**: Worktree add/remove requires git locks

---

## Related Documentation

- [System Design](./system-design.md) - Detailed algorithms and data models
- [Tradeoffs](./tradeoffs.md) - Design decisions and alternatives
- [Implementation](./implementation.md) - Code examples and integration
- [Evaluation](./evaluation.md) - Benchmarks and performance analysis

---

<div align="center">

**Lyra Orchestration System Architecture**

Version 2.0 | 2026-06-02 | Production

[← Back to Systems](../) · [System Design →](./system-design.md)

</div>
