# DAG Teams -- How It Works

> DAG-based team decomposition using topological sort and parallel wave detection. Two primitives (pipeline and parallel) for task execution. Cross-team communication channels for inter-agent coordination.
> **Block:** 07 | **Phase:** 3 (Multi-Agent & Memory) | **Depends on:** Agent Loop, Subagent Worktree, Verifier

## DAG-Based Task Decomposition

When the Agent Loop detects that a task exceeds single-agent capacity, it delegates to DAG Teams. The LLM Planner (Opus-class) decomposes the task into a `TaskDAG` -- an immutable directed acyclic graph of `TaskNode` instances:

```python
@dataclass(frozen=True)
class TaskNode:
    id: str
    kind: NodeKind          # LOCALIZE | EDIT | TEST_GEN | VERIFY | REFACTOR
    description: str
    scope_files: list[str]
    depends_on: list[str]   # IDs of prerequisite nodes
    estimated_cost_usd: float

@dataclass(frozen=True)
class TaskDAG:
    nodes: dict[str, TaskNode]
    edges: list[tuple[str, str]]  # (from_id, to_id)
```

The DAG must be acyclic (validated at build time). Cycles are rejected with a structured error identifying the circular dependency.

## Topological Sort and Parallel Detection

The `WaveScheduler` partitions the DAG into maximal parallel waves using topological sort:

```python
# Given: DAG with edges a→b, a→c, b→d, c→d
# Topological order: [a, b, c, d]
# Waves:
wave_0 = [a]          # no dependencies
wave_1 = [b, c]       # both depend on a
wave_2 = [d]          # depends on b and c
```

**Wave properties:**
- Every node in wave N has all its dependencies satisfied by waves 0 through N-1.
- Nodes within a wave have no dependencies on each other (they are a maximal independent set).
- All nodes in a wave execute in parallel, up to the configured concurrency limit (default: 8).

The scheduling algorithm uses Kahn's algorithm (BFS-based topological sort) with O(V+E) complexity.

## Two Primitives: Pipeline and Parallel

DAG Teams exposes two primitives that compose:

### Pipeline (Sequential)

Node A must complete before Node B. Used for dependencies where the output of one step is the input of the next.

```
Pipeline = PLAN → EXECUTE → VERIFY → CONSOLIDATE
```

### Parallel (Concurrent)

Nodes at the same wave level execute simultaneously. Used for independent sub-tasks.

```
Parallel = [EDIT feature_x, EDIT feature_y, TEST feature_x, TEST feature_y]
```

Both primitives compose within a DAG: a pipeline can contain parallel steps, and a parallel step can contain nested pipelines.

```
PLAN → [EDIT_x, EDIT_y] → [TEST_x, TEST_y] → VERIFY → CONSOLIDATE
```

## Cross-Team Communication Channels

Subagents within a wave communicate through two mechanisms:

### Mailbox (Typed Async Channels)

In-process `asyncio.Queue` for subagents to broadcast findings mid-execution:

```python
# Subagent A publishes
mailbox.publish("api_signatures", {"login": "/api/login", "callback": "/api/callback"})

# Subagent B subscribes and reads
signatures = mailbox.consume("api_signatures")
```

Mailbox latency: <15ms p95. Zero serialization overhead (in-process only).

### ObservationStore (Cross-Wave Data Bus)

Key-value bus for passing structured data from wave N to wave N+1:

```python
# Wave 1: Localize node finds scope
store.put("auth_module", {"files": ["src/auth.py"], "api_count": 12})

# Wave 2: Edit node consumes find
scope = store.get("auth_module")
```

This reduces redundant analysis by 15-30% token savings across waves.

## Parallel Execution

Each wave node is dispatched to an isolated subagent worktree (Block 08). The `SubagentOrchestrator` uses `ThreadPoolExecutor` with context variable propagation for trace ID continuity.

```
DAG Teams ──(wave specs)──> SubagentOrchestrator
                │
                ├── Worktree 1 (subagent A)
                ├── Worktree 2 (subagent B)
                └── Worktree N (subagent ...)
```

## Merge and Verify

After each wave completes, results are merged and verified:

1. **Auto-merge**: 90% of conflicts auto-resolved with git merge drivers
2. **LLM-resolve**: 9.88% of conflicts resolved by Opus
3. **Human-resolve**: 0.12% of conflicts escalated to the user

The merged artifact then passes through verification (Block 10) before the next wave begins.

## Performance

| Metric | Value | Notes |
|--------|-------|-------|
| Parallel speedup (3-node) | 1.6x | vs sequential |
| Parallel speedup (8-node) | 3.0x | vs sequential |
| Planning overhead | $0.15-$0.35 | LLM decomposition |
| Merge conflict rate | 1.2% | 90% auto-resolved |
| Worktree creation | 80-120ms | git worktree add |
| Break-even DAG width | >= 3 nodes | To beat sequential |

## Related Documents

- **Concepts:** [Subagents](../concepts/04-subagents.md), [Plan Mode](../concepts/05-plan-mode.md), [Memory Tiers](../concepts/06-memory-tiers.md)
- **Architecture:** [Workflow Engine](../architecture/05-workflow-engine.md), [Worktree Isolation](../architecture/10-worktree-isolation.md), [Fleet Supervisor](../architecture/04-fleet-supervisor.md)
- **Related blocks:** [Agent Loop](01-agent-loop.md), [Subagent Worktree](08-subagent-worktree.md), [Verifier](10-verifier.md), [Context Engine](02-context-engine.md)

---

*References: SemaClaw (arXiv:2604.11548), AutoGen (arXiv:2308.08155), Wave Scheduling (Kwok & Ahmad, IEEE TPDS 1999)*
