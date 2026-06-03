# Subagent Worktree System Design

## High-Level Design

The Subagent Worktree system enables parallel, isolated agent execution through a multi-layer architecture that separates concerns: orchestration, isolation, execution, and result aggregation.

### Design Principles

1. **Isolation by Default**: Each subagent operates in a separate git worktree with scoped filesystem access
2. **Context Efficiency**: Subagents return observations, not full traces, to preserve parent context budget
3. **Fail-Safe Merging**: Automated conflict resolution with manual review fallback
4. **Resource Bounded**: Concurrency, cost, and scope limits prevent resource exhaustion
5. **Composable Tools**: Subagents use the same tool primitives as parent, narrowed by scope

### System Boundaries

```
┌─────────────────────────────────────────────────────────────────┐
│                      Parent Process                             │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │              Orchestrator Layer                        │   │
│  │  • Lifecycle management                                │   │
│  │  • Concurrency control                                 │   │
│  │  • Result aggregation                                  │   │
│  └────────────────────┬───────────────────────────────────┘   │
│                       │                                         │
│  ┌────────────────────┴───────────────────────────────────┐   │
│  │            Isolation Layer                             │   │
│  │  • Worktree allocation                                 │   │
│  │  • Scope enforcement (FSSandbox)                       │   │
│  │  • Tool narrowing                                      │   │
│  └────────────────────┬───────────────────────────────────┘   │
│                       │                                         │
│  ┌────────────────────┴───────────────────────────────────┐   │
│  │            Execution Layer                             │   │
│  │  • Agent loop (smart model)                            │   │
│  │  • Tool execution                                      │   │
│  │  • Observation generation                              │   │
│  └────────────────────┬───────────────────────────────────┘   │
│                       │                                         │
│  ┌────────────────────┴───────────────────────────────────┐   │
│  │            Integration Layer                           │   │
│  │  • Git merge                                           │   │
│  │  • Conflict resolution                                 │   │
│  │  • Cleanup                                             │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Core Abstractions

### 1. SubagentOrchestrator

**Purpose**: Coordinate subagent lifecycle from spawn to result integration.

**Interface**:
```python
class SubagentOrchestrator:
    def spawn(
        self,
        purpose: str,
        scope: list[str],
        budgets: Budgets | None = None,
        allowed_tools: list[str] | None = None,
        return_shape: ReturnShape = ReturnShape.OBSERVATION,
    ) -> SubagentResult:
        """
        Spawn a subagent and block until completion.
        
        Args:
            purpose: Natural language description of the task
            scope: File patterns the subagent may edit (globs)
            budgets: Optional cost and step limits
            allowed_tools: Tool allowlist (default: Read, Edit, Write, Bash, Grep)
            return_shape: How to return results (observation, artifact, raw_trace)
        
        Returns:
            Structured result with summary, commit, metrics
        
        Raises:
            ConcurrencyLimitExceeded: Too many concurrent subagents
            MergeConflictError: Failed to merge after resolution attempts
            BudgetExceededError: Subagent exceeded cost or step budget
        """
```

**State**:
```python
@dataclass
class OrchestratorState:
    active_subagents: dict[str, Subagent]
    next_id: int
    concurrency_limiter: Semaphore
    cost_tracker: CostTracker
```

### 2. WorktreeManager

**Purpose**: Abstract git worktree operations and lifecycle.

**Interface**:
```python
class WorktreeManager:
    def allocate(
        self, session_id: str, subagent_id: str
    ) -> WorktreeAllocation:
        """
        Create a new git worktree on a session-scoped branch.
        
        Returns:
            WorktreeAllocation with path and branch name
        """
    
    def remove(self, subagent_id: str) -> None:
        """
        Remove worktree and delete branch after merge.
        """
    
    def reconcile_stale(self) -> list[str]:
        """
        Clean up worktrees left from crashed sessions.
        Returns list of removed subagent IDs.
        """
    
    def list_active(self) -> list[WorktreeAllocation]:
        """
        List all currently allocated worktrees.
        """
```

**State**:
```python
@dataclass
class WorktreeAllocation:
    subagent_id: str
    path: Path
    branch_name: str
    created_at: datetime
    session_id: str

class WorktreeRegistry:
    """Persistent registry of active worktrees (JSON file)."""
    def register(self, allocation: WorktreeAllocation) -> None: ...
    def unregister(self, subagent_id: str) -> None: ...
    def get(self, subagent_id: str) -> WorktreeAllocation | None: ...
    def all(self) -> list[WorktreeAllocation]: ...
```

### 3. FSSandbox

**Purpose**: Enforce filesystem scope constraints at the tool layer.

**Interface**:
```python
class FSSandbox:
    def __init__(self, root: Path, scope_globs: list[str]):
        """
        Initialize sandbox with worktree root and scope patterns.
        """
    
    def validate_write(self, path: Path) -> None:
        """
        Validate write is within scope.
        Raises PermissionError if outside scope.
        """
    
    def validate_read(self, path: Path) -> None:
        """
        Log reads outside scope (allowed but audited).
        """
    
    def is_in_scope(self, path: Path) -> bool:
        """
        Check if path matches any scope pattern.
        """
    
    def wrapped_tool(self, tool: Tool) -> Tool:
        """
        Wrap a tool to inject scope validation.
        """
```

**Implementation Strategy**:
```python
class FSSandbox:
    def wrapped_tool(self, tool: Tool) -> Tool:
        """
        Wrap tool execution with scope validation.
        """
        original_execute = tool.execute
        
        def validated_execute(**kwargs):
            # Extract file paths from kwargs
            paths = self._extract_paths(kwargs)
            
            # Validate writes
            if tool.writes:
                for path in paths:
                    self.validate_write(path)
            else:
                for path in paths:
                    self.validate_read(path)
            
            # Execute original tool
            return original_execute(**kwargs)
        
        tool.execute = validated_execute
        return tool
```

### 4. Subagent

**Purpose**: Execute a scoped task in isolation and return structured result.

**Interface**:
```python
class Subagent:
    def run(self) -> SubagentResult:
        """
        Execute the subagent's task.
        
        Returns:
            SubagentResult with summary, commit, metrics
        """
    
    def _build_context_seed(self) -> list[Message]:
        """
        Build initial context: SOUL + plan + purpose + scope.
        """
    
    def _build_system_prompt(self) -> str:
        """
        Build subagent-specific system prompt with constraints.
        """
    
    def _summarize_outcome(self, outcome: AgentOutcome) -> str:
        """
        Summarize agent outcome into observation.
        """
    
    def _commit_changes(self) -> str:
        """
        Commit changes in worktree and return commit hash.
        """
```

**State**:
```python
@dataclass
class SubagentState:
    subagent_id: str
    purpose: str
    scope: list[str]
    worktree_path: Path
    branch_name: str
    budgets: Budgets
    allowed_tools: list[str]
    fs_sandbox: FSSandbox
    metrics: SubagentMetrics
```

### 5. SubagentResult

**Purpose**: Structured return value from subagent execution.

**Schema**:
```python
@dataclass
class SubagentResult:
    subagent_id: str
    status: StopReason  # success, budget_exceeded, error, blocked
    summary: str  # Natural language observation
    files_touched: list[str]  # Relative paths modified
    commit_hash: str | None  # Git commit (None if no changes)
    test_delta: TestDelta | None  # Test changes (if tests run)
    cost_usd: float
    duration_ms: int
    trace_hash: str  # SHA256 of offloaded trace

@dataclass
class TestDelta:
    added: int
    removed: int
    passing_new: int
    failing_new: int
    regressions: int
```

## API Contracts

### Spawn Tool

The parent-facing tool for subagent dispatch.

```python
@tool(name="Spawn", writes=False, risk="medium")
def spawn_subagent(
    purpose: str,
    scope: list[str],
    budgets: dict | None = None,
    allowed_tools: list[str] | None = None,
    return_shape: Literal["observation", "artifact", "raw_trace"] = "observation",
) -> str:
    """
    Spawn a subagent to work on a focused task in isolation.
    
    Args:
        purpose: Natural language description of what the subagent should accomplish.
                 Example: "Reproduce issue #234 in a minimal test case"
        
        scope: File patterns the subagent may edit (glob syntax).
               Example: ["tests/**", "src/auth/**"]
               The subagent can READ outside scope but cannot WRITE.
        
        budgets: Optional resource limits.
                 Example: {"max_steps": 20, "max_cost_usd": 1.00}
        
        allowed_tools: Tool allowlist. Default: ["Read", "Edit", "Write", "Bash", "Grep"]
        
        return_shape: How to return results:
                      - "observation" (default): Structured JSON summary
                      - "artifact": Reference hash for lazy loading
                      - "raw_trace": Full trace (debug only)
    
    Returns:
        JSON string with SubagentResult structure.
    
    Example:
        ```python
        result = spawn_subagent(
            purpose="Add unit tests for authenticate() function",
            scope=["tests/auth/**"],
            budgets={"max_steps": 15, "max_cost_usd": 0.50},
        )
        ```
    """
    orchestrator = get_current_session().subagent_orchestrator
    result = orchestrator.spawn(
        purpose=purpose,
        scope=scope,
        budgets=Budgets.from_dict(budgets) if budgets else None,
        allowed_tools=allowed_tools,
        return_shape=ReturnShape(return_shape),
    )
    return result.to_json()
```

### View Tool (Artifact Loading)

For `return_shape="artifact"`, parent uses View to load result.

```python
@tool(name="View", writes=False, risk="low")
def view_artifact(hash: str) -> str:
    """
    Load an artifact by hash.
    
    Args:
        hash: SHA256 hash from SubagentResult.trace_hash or artifact reference
    
    Returns:
        Artifact content (JSON, text, or binary base64)
    """
```

## State Management

### Parent Session State

```python
@dataclass
class SessionState:
    session_id: str
    soul_content: str
    plan: Plan
    smart_model: str  # e.g., "deepseek-v4-pro"
    fast_model: str   # e.g., "deepseek-v4-flash"
    provider: Provider
    trust_level: TrustLevel
    subagent_orchestrator: SubagentOrchestrator
    repo_root: Path
    session_branch: str
```

### Subagent Ephemeral State

Subagent state is **not persisted**. It exists only during execution:

```python
# Created at spawn
subagent = Subagent(...)

# Runs in-memory
result = subagent.run()

# Result is persisted, subagent state is discarded
```

**Rationale**: Subagents are short-lived (seconds to minutes). Persistence overhead would exceed benefit.

### Persistent State

Only these components persist to disk:

1. **WorktreeRegistry**: `.lyra/worktrees/registry.json`
2. **Commits**: Git commits in worktree branches
3. **Traces**: Offloaded to artifact storage (`.lyra/artifacts/<hash>`)
4. **Metrics**: Emitted to telemetry sink (Prometheus, CloudWatch, etc.)

## Error Handling

### Error Categories

```python
class SubagentError(Exception):
    """Base class for subagent errors."""

class ConcurrencyLimitExceeded(SubagentError):
    """Too many concurrent subagents."""

class MergeConflictError(SubagentError):
    """Failed to merge after resolution attempts."""
    def __init__(self, conflicts: list[str], attempts: int):
        self.conflicts = conflicts
        self.attempts = attempts

class BudgetExceededError(SubagentError):
    """Subagent exceeded cost or step budget."""
    def __init__(self, budget_type: str, limit: float, actual: float):
        self.budget_type = budget_type
        self.limit = limit
        self.actual = actual

class ScopeViolationError(SubagentError):
    """Subagent attempted to write outside scope."""
    def __init__(self, path: Path, scope: list[str]):
        self.path = path
        self.scope = scope

class WorktreeAllocationError(SubagentError):
    """Failed to allocate worktree (disk full, git error, etc.)."""
```

### Error Handling Strategy

```python
class SubagentOrchestrator:
    def spawn(self, ...) -> SubagentResult:
        try:
            # Preflight checks
            self._check_concurrency_limit()
            self._check_disk_space()
            self._check_scope_overlap()
            
            # Allocate resources
            subagent = self._build_subagent(...)
            
            # Execute
            result = subagent.run()
            
            # Merge
            self._merge_changes(subagent, result)
            
            return result
            
        except BudgetExceededError as e:
            # Budget exceeded is a normal outcome, not a failure
            logger.info(f"Subagent {subagent.id} exceeded budget: {e}")
            return SubagentResult(
                status=StopReason.BUDGET_EXCEEDED,
                summary=f"Stopped: {e.budget_type} budget exceeded",
                ...
            )
        
        except MergeConflictError as e:
            # Escalate to human review
            logger.warning(f"Merge conflict after {e.attempts} attempts")
            raise  # Propagate to parent for user decision
        
        except ScopeViolationError as e:
            # Log and return error result
            logger.error(f"Scope violation: {e.path} not in {e.scope}")
            return SubagentResult(
                status=StopReason.ERROR,
                summary=f"Error: Attempted write outside scope",
                ...
            )
        
        finally:
            # Always cleanup
            self._cleanup_subagent(subagent.id)
```

### Cleanup Guarantees

```python
class SubagentOrchestrator:
    def _cleanup_subagent(self, subagent_id: str):
        """
        Cleanup is idempotent and always runs.
        """
        try:
            # Remove from active tracking
            self.active_subagents.pop(subagent_id, None)
            
            # Remove worktree (if not already removed by successful merge)
            self.worktree_manager.remove(subagent_id)
            
            # Emit final metrics
            self._emit_cleanup_metrics(subagent_id)
            
        except Exception as e:
            # Never let cleanup errors propagate
            logger.error(f"Cleanup failed for {subagent_id}: {e}")
            # Continue cleanup of other resources
```

## Scalability Strategies

### Horizontal Scaling (Future)

**Design**: Remote subagent execution on cloud runners.

```python
class RemoteSubagentRunner:
    """
    Execute subagents on remote compute (Modal, Fly, AWS Lambda).
    """
    def spawn_remote(
        self,
        purpose: str,
        scope: list[str],
        runner: Literal["modal", "fly", "lambda"],
    ) -> SubagentResult:
        """
        1. Package context (SOUL, plan, scope) → artifact
        2. Ship artifact to runner
        3. Runner allocates worktree, executes subagent
        4. Runner returns result + commit
        5. Orchestrator fetches commit, merges locally
        """
```

**Tradeoffs**:
- **Latency**: +200-500ms for network round-trip
- **Cost**: +$0.01-0.05 per subagent for compute
- **Complexity**: Auth, networking, failure handling

### Vertical Scaling

**Current Limits**:
- Concurrency: 4 (configurable up to 16)
- Disk: 10MB per worktree → 1000 subagents = 10GB
- Memory: 200MB per subagent → 4 concurrent = 800MB
- Cost: $0.023 per subagent → 1000 subagents = $23

**Scaling Strategies**:
1. **Shallow Worktrees**: Reduce disk usage 5x (opt-in v2)
2. **Adaptive Concurrency**: Scale up when system resources allow
3. **Worktree Pooling**: Pre-allocate worktrees for instant spawn

### Cost Control

```python
class CostPacer:
    """
    Pace subagent spawning to stay within budget.
    """
    def __init__(self, max_cost_usd: float):
        self.max_cost_usd = max_cost_usd
        self.spent = 0.0
        self.lock = Lock()
    
    def can_spend(self, estimated_cost: float) -> bool:
        with self.lock:
            return (self.spent + estimated_cost) <= self.max_cost_usd
    
    def record(self, actual_cost: float):
        with self.lock:
            self.spent += actual_cost
    
    def scale_concurrency(self) -> int:
        """
        Reduce concurrency as budget depletes.
        """
        remaining = self.max_cost_usd - self.spent
        if remaining < 0.10:  # Less than 10 cents left
            return 1  # Serialize
        elif remaining < 0.50:
            return 2
        else:
            return 4  # Full concurrency
```

## Observability

### Metrics

```python
# Counters
subagent.spawn.count{status=success|failed}
subagent.merge.conflicts{resolved=true|false}
subagent.scope.violations

# Histograms
subagent.duration.ms{phase=allocate|execute|merge|cleanup}
subagent.cost.usd

# Gauges
subagent.active.count
subagent.concurrency.limit
```

### Structured Logging

```python
logger.info(
    "Subagent spawned",
    subagent_id=subagent.id,
    purpose=subagent.purpose[:50],  # Truncate for logs
    scope=subagent.scope,
    budgets=subagent.budgets,
)

logger.info(
    "Subagent completed",
    subagent_id=subagent.id,
    status=result.status,
    files_touched=len(result.files_touched),
    cost_usd=result.cost_usd,
    duration_ms=result.duration_ms,
)
```

### Trace Correlation

```python
# Subagent trace includes parent trace ID for correlation
trace_context = {
    "parent_session_id": parent_session.id,
    "parent_trace_id": parent_session.trace_id,
    "subagent_id": subagent.id,
}
```

## Security Model

### Trust Boundaries

```
Parent Session (trust level: user-defined)
    │
    ├─> Subagent (inherits parent trust level)
    │       │
    │       ├─> FSSandbox (enforces scope)
    │       ├─> ToolRegistry (enforces allowlist)
    │       └─> Budget (enforces limits)
    │
    └─> No privilege escalation possible
```

### Scope Enforcement Layers

1. **Dispatch-time**: PermissionBridge checks scope before spawn
2. **Runtime**: FSSandbox validates paths at tool execution
3. **Physical**: Git worktree isolates filesystem

### Recursion Prevention

```python
class Subagent:
    def _build_narrowed_tools(self) -> list[Tool]:
        """
        Build tool registry without Spawn tool (prevents recursion).
        """
        tools = ToolRegistry.all()
        tools = [t for t in tools if t.name != "Spawn"]  # Remove Spawn
        tools = [t for t in tools if t.name in self.allowed_tools]
        return [self.fs_sandbox.wrapped_tool(t) for t in tools]
```

---

**Related Documentation:**
- [Architecture](./architecture.md)
- [Architecture Tradeoffs](./architecture-tradeoffs.md)
- [Implementation Guide](./implementation-guide.md)
- [Deep Dive](./deep-dive.md)
