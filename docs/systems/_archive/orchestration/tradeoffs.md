# Orchestration System Tradeoffs

**Version**: 2.0  
**Date**: 2026-06-02  
**Status**: Production

---

## Executive Summary

This document explains the design decisions behind Lyra's orchestration system, the alternatives considered, why we chose this approach, performance implications, cost analysis, and maintenance considerations. Every architectural choice involves tradeoffs—this document makes them explicit.

---

## Design Decision 1: Git Worktrees vs Docker Containers

### Decision

Use **git worktrees** as the default isolation mechanism for parallel agent execution.

### Alternatives Considered

| Approach | Pros | Cons |
|----------|------|------|
| **Git Worktrees** (chosen) | Fast (200-500ms), no daemon, native git integration, works everywhere | Limited to git repositories, less security isolation than containers |
| **Docker Containers** | Strong isolation, reproducible environments, industry standard | Slow startup (2-10s), requires Docker daemon, heavyweight (100MB+ per container), platform-specific |
| **Filesystem Copying** | Simple, no dependencies | Slow for large repos, high disk usage, no git integration |
| **In-Memory FS** | Very fast, no disk I/O | Limited by RAM, lost on crash, complex implementation |
| **Namespace Isolation** | Linux-native, lightweight | Linux-only, requires root, complex setup |

### Why Git Worktrees

**Performance**: Worktree creation takes 200-500ms vs 2-10s for Docker containers. For orchestration workflows that spawn 10-20 agents, this is a 20-180 second difference in startup time.

**Portability**: Works on macOS, Linux, Windows with only git dependency. Docker requires platform-specific daemon installation.

**Native Git Integration**: Each worktree is a full git repository with its own branch. Commits, diffs, merges, and PRs work naturally. No custom VCS integration needed.

**Disk Efficiency**: Worktrees use hardlinks for unchanged files. A 10GB repository with 5 worktrees uses ~10GB disk space, not 50GB.

**Developer Experience**: Developers already understand git worktrees. No new mental model for containers, volumes, networks.

### Performance Implications

| Metric | Git Worktrees | Docker Containers |
|--------|---------------|-------------------|
| Creation time | 200-500ms | 2-10s |
| Disk usage | ~10% per worktree | 100MB+ per container |
| Memory overhead | ~0MB (shares host) | 50-200MB per container |
| Cleanup time | 100-200ms | 1-5s |

### Cost Analysis

**Development Cost**: 1 week to implement worktree isolation vs 3-4 weeks for container orchestration.

**Runtime Cost**: Near-zero incremental cost. Containers would require Docker Desktop licenses ($5-21/user/month) for commercial use.

**Maintenance Cost**: Minimal. Git worktrees are a stable git feature since 2015. Docker API and runtime change frequently.

### When to Use Docker Instead

For **security-sensitive** workloads (untrusted code execution, penetration testing), Docker containers provide stronger isolation:
- Network isolation
- Filesystem sandboxing
- Resource limits (CPU/memory)
- Kernel-level security

Lyra supports both: worktrees for default agent tasks, containers for security-sensitive operations via optional `--isolation=docker` flag.

---

## Design Decision 2: In-Memory State vs Persistent Queue

### Decision

Use **in-memory state** with periodic disk persistence for task queue and session state.

### Alternatives Considered

| Approach | Pros | Cons |
|----------|------|------|
| **In-Memory + Disk Snapshots** (chosen) | Fast (<1ms ops), simple implementation, no external dependencies | Lost state on crash (mitigated by snapshots), single-node only |
| **Redis** | Distributed, fast, industry standard | External dependency, network latency, operational complexity |
| **PostgreSQL** | ACID guarantees, complex queries, durable | Slower (5-10ms per write), heavier resource usage |
| **SQLite** | Embedded, zero-config, ACID guarantees | Single-writer limitation, slower than in-memory |

### Why In-Memory First

**Latency**: In-memory operations are <1ms. Redis adds 0.5-2ms network latency. PostgreSQL adds 5-10ms per write.

**Simplicity**: Zero external dependencies for single-user deployment. No installation, configuration, or maintenance of external services.

**Development Velocity**: Faster to implement and iterate. No schema migrations, connection pooling, or transaction management.

### Performance Implications

| Operation | In-Memory | Redis | PostgreSQL |
|-----------|-----------|-------|------------|
| Task enqueue | <1ms | 1-2ms | 5-10ms |
| Task assign | <1ms | 1-2ms | 5-10ms |
| Session create | <1ms | 1-2ms | 10-20ms |
| Event publish | <1ms | 1-2ms | N/A |

### Migration Path to Distributed

The API contracts are designed for easy migration:

```python
# Current: In-memory
class TaskQueue:
    def __init__(self):
        self._tasks = {}  # In-memory dict

# Future: Redis backend
class TaskQueue:
    def __init__(self, redis_url: str):
        self._redis = Redis.from_url(redis_url)
        # API stays the same
```

When multi-node deployment is needed, we add Redis/PostgreSQL backends without changing the API.

### Cost Analysis

**Development Cost**: 1 week for in-memory implementation vs 3 weeks with Redis integration.

**Runtime Cost**: $0 for in-memory vs $30-200/month for managed Redis (AWS ElastiCache, Redis Cloud).

**Operational Cost**: 0 hours/month for in-memory vs 2-5 hours/month for Redis monitoring, upgrades, backups.

---

## Design Decision 3: Typed Events (Pydantic) vs Untyped JSON

### Decision

Use **Pydantic models** for event schema validation with compile-time type checking.

### Alternatives Considered

| Approach | Pros | Cons |
|----------|------|------|
| **Pydantic** (chosen) | Runtime validation, IDE autocomplete, type safety | Small overhead (0.1-0.5ms per event), more boilerplate |
| **Plain dicts/JSON** | Zero overhead, flexible, less code | No schema validation, runtime errors, no IDE support |
| **Protobuf** | Fast serialization, schema evolution | Complex setup, separate compilation step |
| **JSON Schema** | Language-agnostic, standard | Runtime validation only, no type hints |

### Why Pydantic

**Developer Experience**: IDE autocomplete for event fields. Type errors caught at development time, not production.

```python
# Typed event - IDE autocomplete works
event = ScanCompleted(target="192.168.1.1", findings=[...])
print(event.target)  # IDE knows this exists

# Untyped dict - no autocomplete, easy typos
event = {"targt": "192.168.1.1", "findings": [...]}  # Typo undetected
print(event["target"])  # Runtime KeyError
```

**Runtime Validation**: Invalid events are caught at publish time, not when processed by subscribers.

```python
# Pydantic catches invalid data immediately
event = ScanCompleted(target="192.168.1.1", severity="WRONG")
# ValidationError: severity must be one of [CRITICAL, HIGH, MEDIUM, LOW]

# Plain dict - error discovered later when agent tries to use it
event = {"target": "192.168.1.1", "severity": "WRONG"}
# Agent crashes during processing
```

**Schema Evolution**: Pydantic supports default values and optional fields for backward compatibility.

### Performance Implications

| Operation | Pydantic | Plain Dict | Protobuf |
|-----------|----------|------------|----------|
| Validation | 0.1-0.5ms | 0ms | 0.05-0.2ms |
| Serialization | N/A (in-memory) | N/A | 0.5-1ms |
| Memory | +10% | Baseline | -30% |

For in-memory event bus (no serialization), Pydantic overhead is 0.1-0.5ms per event—negligible compared to agent execution time (100ms-10s).

### Cost Analysis

**Development Cost**: +20% more code for Pydantic models vs plain dicts, but prevents 50-80% of runtime errors.

**Runtime Cost**: 0.1-0.5ms per event is acceptable for agent coordination (events are infrequent, ~1-10/second).

**Maintenance Cost**: Schema changes are explicit and version-controlled. Plain dicts lead to implicit schema drift.

---

## Design Decision 4: Async (asyncio) vs Thread Pool

### Decision

Use **asyncio** for concurrency throughout the orchestration system.

### Alternatives Considered

| Approach | Pros | Cons |
|----------|------|------|
| **asyncio** (chosen) | I/O efficient, single-threaded (no GIL), explicit concurrency | Complex error handling, function coloring (async/await) |
| **Thread Pool** | Familiar API, works with blocking code | GIL contention, higher memory (1MB/thread), harder to debug |
| **Process Pool** | True parallelism, no GIL | High overhead (10MB/process), slow IPC |
| **Green Threads (gevent)** | Transparent async, works with blocking code | Monkey patching, compatibility issues |

### Why asyncio

**I/O Bound Workload**: Orchestration is I/O bound (waiting for agent responses, file I/O, network). asyncio excels here.

**Memory Efficiency**: asyncio tasks use <1KB each. Thread pool uses 1MB per thread. For 100 concurrent operations, asyncio uses 100KB vs 100MB.

**Explicit Concurrency**: `async`/`await` makes concurrent code paths explicit. Thread pools hide concurrency, leading to race conditions.

### Performance Implications

| Metric | asyncio | Thread Pool | Process Pool |
|--------|---------|-------------|--------------|
| Context switch | ~0.5μs | ~2-5μs | ~50-100μs |
| Memory per task | <1KB | 1MB | 10MB |
| Max concurrency | 10,000+ | 100-500 | 10-50 |

### Cost Analysis

**Development Cost**: asyncio requires careful handling of blocking operations (use `run_in_executor`). Thread pool is more forgiving.

**Runtime Cost**: asyncio enables higher concurrency with same memory. 1000 concurrent operations: 1MB (asyncio) vs 1GB (threads).

### Tradeoff

**Function Coloring**: Once you use `async`, all calling code must be `async`. This propagates through the codebase. For orchestration (already async-heavy), this is acceptable.

---

## Design Decision 5: Priority Queue vs FIFO Queue

### Decision

Use **priority queue** with 4 levels (CRITICAL > HIGH > NORMAL > LOW).

### Alternatives Considered

| Approach | Pros | Cons |
|----------|------|------|
| **Priority Queue** (chosen) | Important tasks processed first, fair scheduling | Slightly more complex, potential starvation of low-priority |
| **FIFO Queue** | Simple, guaranteed fairness | No urgency handling, critical tasks wait behind normal tasks |
| **Shortest Job First** | Optimal average latency | Requires task time estimation, long tasks starved |
| **Weighted Fair Queueing** | Precise bandwidth allocation | Complex implementation, overkill for agent orchestration |

### Why Priority Queue

**Responsiveness**: Critical tasks (user-blocking operations, security scans) processed immediately, not queued behind batch jobs.

**Simplicity**: 4 priority levels are enough. More levels add complexity without benefit.

**Fairness**: Within same priority, tasks are FIFO. Prevents starvation within priority class.

### Performance Implications

| Metric | Priority Queue | FIFO Queue |
|--------|----------------|------------|
| Enqueue | O(log N) | O(1) |
| Dequeue | O(log N) | O(1) |
| Critical task latency | ~0ms (immediate) | 0-1000ms (variable) |

For N=1000 tasks, log(N) ≈ 10 operations. Still submillisecond.

### Starvation Prevention

Low-priority tasks can be starved if high-priority tasks keep arriving. Mitigation:

```python
# Age-based priority boost
if task.created_at < (now - 300):  # 5 minutes old
    task.priority = min(task.priority + 1, TaskPriority.CRITICAL)
```

After 5 minutes, LOW → NORMAL → HIGH → CRITICAL.

---

## Design Decision 6: Consensus Strategies (4 Options)

### Decision

Support **4 voting strategies**: Majority, Unanimous, Weighted, Quorum.

### Alternatives Considered

| Approach | Pros | Cons |
|----------|------|------|
| **Multiple Strategies** (chosen) | Flexible, fits different use cases | More complex API |
| **Majority Only** | Simple, well-understood | Not suitable for critical decisions |
| **Always Unanimous** | Maximum safety | Slow, one agent can block |
| **Custom Per-Proposal** | Ultimate flexibility | Too complex, hard to reason about |

### Why Multiple Strategies

Different decisions need different consensus models:

- **Majority**: Normal decisions, balance speed and safety
- **Unanimous**: Critical changes (deploy to production, delete data)
- **Weighted**: When agents have different expertise levels
- **Quorum**: When full participation is not required

### Use Case Examples

```python
# Majority: Choose best approach from 5 agents
consensus.propose(
    topic="Code review",
    voters={"agent1", "agent2", "agent3", "agent4", "agent5"},
    strategy=VotingStrategy.MAJORITY,
    quorum=0.6,  # Need 60% participation
)

# Unanimous: Deploy to production
consensus.propose(
    topic="Deploy v2.0 to production",
    voters={"security_agent", "qa_agent", "ops_agent"},
    strategy=VotingStrategy.UNANIMOUS,  # All must approve
    quorum=1.0,  # All must vote
)

# Weighted: Expert agents have more influence
consensus.propose(
    topic="Security vulnerability severity",
    voters={"security_expert", "junior_agent", "intern_agent"},
    strategy=VotingStrategy.WEIGHTED,
)
# Votes weighted by expertise: expert=2.0, junior=1.0, intern=0.5
```

### Performance Implications

| Strategy | Average Latency | Worst Case |
|----------|----------------|------------|
| Majority | 50-200ms | 300s (timeout) |
| Unanimous | 100-500ms | 300s (timeout) |
| Weighted | 50-200ms | 300s (timeout) |
| Quorum | 20-100ms | 150s (50% timeout) |

Majority is fastest (decision as soon as >50% vote). Unanimous is slowest (must wait for all votes).

---

## Design Decision 7: JSON Persistence vs Binary Formats

### Decision

Use **JSON** for session state and task queue persistence.

### Alternatives Considered

| Approach | Pros | Cons |
|----------|------|------|
| **JSON** (chosen) | Human-readable, debuggable, language-agnostic | Larger files, slower parsing |
| **MessagePack** | Compact, fast, schema-less | Binary (not human-readable) |
| **Protobuf** | Compact, fast, schema evolution | Requires schema compilation, more complex |
| **Pickle** | Native Python, fast | Python-only, security issues |

### Why JSON

**Debuggability**: Developers can inspect `~/.lyra/jobs/<id>/state.json` with any text editor. Critical for diagnosing issues.

**Tooling**: Standard Unix tools work (grep, jq, diff). Binary formats require custom tools.

**Compatibility**: JSON is language-agnostic. Future TypeScript/Rust/Go implementations can read the same state files.

### Performance Implications

| Format | File Size | Parse Time | Write Time |
|--------|-----------|------------|------------|
| JSON | 100KB | 5-10ms | 3-5ms |
| MessagePack | 60KB | 2-5ms | 1-2ms |
| Protobuf | 50KB | 1-3ms | 1-2ms |

For session state (written every 15s), 5-10ms is acceptable.

### Cost Analysis

**Development Cost**: JSON is built-in. MessagePack/Protobuf require dependencies and schema management.

**Debugging Cost**: JSON saves hours of debugging time. Engineers can directly inspect state without custom tools.

**Storage Cost**: For 1000 sessions, JSON uses ~100MB vs 60MB (MessagePack). Storage is cheap ($0.01/GB/month).

---

## Design Decision 8: Daemon vs On-Demand Spawning

### Decision

Use **daemon process** (Fleet Supervisor) for background session management.

### Alternatives Considered

| Approach | Pros | Cons |
|----------|------|------|
| **Daemon** (chosen) | Sessions survive terminal close, central management | Extra process overhead, daemon lifecycle management |
| **On-Demand Spawning** | Simple, no daemon | Sessions die with terminal, no cross-session coordination |
| **Systemd Service** | OS-managed, auto-restart | Linux-only, requires root for installation |
| **Cloud Service** | Scalable, highly available | Requires network, latency, monthly cost |

### Why Daemon

**Session Persistence**: Background sessions must survive terminal close. Daemon is the only local solution.

**Resource Sharing**: Daemon manages shared resources (worktree pool, task queue, event bus).

**Idle Management**: Daemon can pause idle sessions after 1 hour, resume on demand. On-demand spawning would keep all sessions alive.

### Performance Implications

| Metric | Daemon | On-Demand |
|--------|--------|-----------|
| Session startup | 200-500ms | 100-200ms |
| Memory (idle) | 50MB | 0MB |
| Sessions survive terminal close | Yes | No |

Daemon uses 50MB when idle, but enables critical features (background sessions, idle pause/resume).

### Cost Analysis

**Development Cost**: Daemon lifecycle (start, stop, restart, upgrade) adds 1-2 weeks development.

**Runtime Cost**: 50MB memory overhead. Acceptable on modern machines (8GB+ RAM).

**User Experience**: Massive improvement. Users can close terminal and resume sessions later. On-demand spawning cannot support this.

---

## Maintenance Considerations

### Code Complexity

| Component | Lines of Code | Complexity | Maintenance Cost |
|-----------|--------------|------------|------------------|
| Task Queue | 573 | Medium | Low (stable API) |
| Fleet Supervisor | 467 | High | Medium (lifecycle edge cases) |
| Event Bus | 150 | Low | Very Low (simple pub/sub) |
| Consensus Protocol | 427 | Medium | Low (voting math is stable) |
| Worktree Isolation | 619 | High | Medium (git edge cases) |

**Total**: ~2200 lines of well-structured Python. Manageable for a 2-3 person team.

### Operational Complexity

| Aspect | Complexity | Notes |
|--------|------------|-------|
| Deployment | Low | Single Python package, no external services |
| Monitoring | Low | Built-in observability via event history |
| Upgrades | Medium | Daemon restart, state migration |
| Scaling | Low (single-node) | High (distributed, requires Redis/PostgreSQL) |

### Technical Debt

**Current**: Minimal. Code is well-tested (8 test files, 30+ tests).

**Future**: When scaling to distributed deployment, we'll need:
- Redis integration for task queue
- PostgreSQL for durable state
- Leader election for multi-supervisor
- Distributed tracing

Estimated effort: 4-6 weeks.

---

## Summary of Key Tradeoffs

| Decision | Tradeoff | Rationale |
|----------|----------|-----------|
| Git worktrees over Docker | Security isolation vs speed | Speed matters for dev workflows, Docker for security-sensitive |
| In-memory over Redis | Scalability vs simplicity | Single-user use case doesn't need distributed state yet |
| Pydantic over plain dicts | Performance vs safety | 0.1ms overhead prevents hours of debugging |
| asyncio over threads | Function coloring vs efficiency | Orchestration is already async-heavy, efficiency wins |
| Priority queue over FIFO | Complexity vs responsiveness | 4 levels balance simplicity and urgency |
| JSON over MessagePack | File size vs debuggability | Storage is cheap, debugging time is expensive |
| Daemon over on-demand | Memory vs features | 50MB enables critical background session features |

---

## Related Documentation

- [Architecture](./architecture.md) - System overview
- [System Design](./system-design.md) - Algorithms and data models
- [Implementation](./implementation.md) - Code examples
- [Evaluation](./evaluation.md) - Performance benchmarks

---

<div align="center">

**Lyra Orchestration System Tradeoffs**

Version 2.0 | 2026-06-02 | Production

[← System Design](./system-design.md) · [Implementation →](./implementation.md)

</div>
