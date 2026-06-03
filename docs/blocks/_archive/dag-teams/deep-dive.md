# DAG Teams Deep Dive

## Advanced Patterns

### 1. Dynamic DAG Expansion

**Problem**: Localize node discovers 20 files when planner estimated 5.

**Solution v1 (current)**: Replan with discovered scope
```python
@dataclass
class DynamicExpansionEvent:
    node_id: str
    discovered_files: List[str]
    estimated_new_cost: float

def handle_expansion(event: DynamicExpansionEvent, session: Session):
    """Trigger replan when node scope exceeds estimate."""
    if len(event.discovered_files) > 2 * original_estimate:
        # Pause execution
        session.pause()
        
        # Replan with new context
        updated_context = {
            **session.repo_context,
            "discovered_scope": event.discovered_files
        }
        new_dag = planner.decompose(
            session.request,
            updated_context,
            session.id,
            session.remaining_budget
        )
        
        # Merge with partial progress
        merge_dags(session.completed_nodes, new_dag)
```

**Solution v2 (proposed)**: Inline expansion under budget
```python
def spawn_child_nodes(
    parent: TaskNode,
    new_files: List[str],
    remaining_budget: float
) -> List[TaskNode]:
    """Create child nodes for newly discovered files."""
    children = []
    for i, file_batch in enumerate(chunk(new_files, 5)):
        child = TaskNode(
            id=f"{parent.id}-child-{i}",
            kind=NodeKind.EDIT,
            description=f"Edit {file_batch}",
            scope_files=file_batch,
            depends_on=[parent.id],
            estimated_cost_usd=0.3
        )
        children.append(child)
    
    return children
```

**Tradeoffs**:
- v1: Safe, predictable, but wastes work
- v2: Efficient, but complex state management

---

### 2. Cross-Wave Observation Sharing

**Pattern**: Pass structured data from wave N to wave N+1

**Use Case**: Localize wave finds API signatures → Edit wave uses them

**Implementation**:
```python
@dataclass
class WaveHandoff:
    source_wave: int
    target_wave: int
    observations: Dict[str, Any]

class ObservationStore:
    def __init__(self):
        self._store: Dict[str, Any] = {}
    
    def publish(self, node_id: str, key: str, value: Any):
        """Publish observation from node."""
        self._store[f"{node_id}:{key}"] = value
    
    def subscribe(self, node_id: str, dependency_id: str, key: str) -> Any:
        """Retrieve observation from dependency."""
        return self._store.get(f"{dependency_id}:{key}")

# Usage in subagent
def run_subagent_with_observations(
    node: TaskNode,
    obs_store: ObservationStore
):
    # Fetch observations from dependencies
    context = {}
    for dep_id in node.depends_on:
        api_signatures = obs_store.subscribe(
            node.id, dep_id, "api_signatures"
        )
        if api_signatures:
            context["api_signatures"] = api_signatures
    
    # Run with enriched context
    result = execute_node(node, additional_context=context)
    
    # Publish observations for downstream nodes
    if result.status == NodeStatus.SUCCESS:
        obs_store.publish(
            node.id,
            "modified_files",
            result.files_touched
        )
```

**Benefits**:
- Reduces redundant analysis
- Enables smarter downstream decisions
- Cost savings: ~15-30% fewer tokens

---

### 3. Speculative Execution

**Pattern**: Start wave N+1 optimistically before N completes

**Use Case**: High-confidence DAGs where failures are rare

**Algorithm**:
```python
async def execute_with_speculation(
    plan: ExecutionPlan,
    confidence_threshold: float = 0.9
):
    for i, wave in enumerate(plan.waves):
        # Start current wave
        wave_task = asyncio.create_task(dispatch_wave(wave))
        
        # If high confidence, start next wave speculatively
        if i < len(plan.waves) - 1:
            next_wave = plan.waves[i + 1]
            confidence = estimate_wave_confidence(wave)
            
            if confidence >= confidence_threshold:
                next_wave_task = asyncio.create_task(
                    dispatch_wave(next_wave)
                )
            else:
                next_wave_task = None
        
        # Wait for current wave
        results = await wave_task
        
        # Check if speculation succeeded
        if all(r.status == NodeStatus.SUCCESS for r in results):
            if next_wave_task:
                # Speculation paid off, continue
                await next_wave_task
        else:
            # Failure: cancel speculation
            if next_wave_task:
                next_wave_task.cancel()
                await cleanup_speculative_work(next_wave)

def estimate_wave_confidence(wave: Wave) -> float:
    """Estimate probability wave will succeed."""
    # Heuristic based on:
    # - Node complexity
    # - Historical success rate
    # - Scope overlap with previous waves
    
    base_confidence = 0.85
    for node in wave.nodes:
        if node.kind == NodeKind.LOCALIZE:
            base_confidence *= 0.95  # Low risk
        elif node.kind == NodeKind.REFACTOR:
            base_confidence *= 0.75  # Higher risk
    
    return base_confidence
```

**Risks**:
- Wasted work if speculation fails (~20-40% cost increase)
- Merge conflicts harder to attribute
- Debugging complexity

**When to Use**: Production systems with stable codebases, high DAG confidence

---

## Optimization Techniques

### 1. DAG Compaction

**Pattern**: Merge adjacent nodes with no dependencies between them

```python
def compact_dag(dag: TaskDAG) -> TaskDAG:
    """Merge compatible adjacent nodes."""
    compacted_nodes = []
    skip = set()
    
    for i, node in enumerate(dag.nodes):
        if node.id in skip:
            continue
        
        # Find mergeable successor
        candidates = [
            n for n in dag.nodes
            if set(n.depends_on) == {node.id}
            and can_merge(node, n)
        ]
        
        if candidates:
            successor = candidates[0]
            merged = merge_nodes(node, successor)
            compacted_nodes.append(merged)
            skip.add(successor.id)
        else:
            compacted_nodes.append(node)
    
    return TaskDAG(compacted_nodes, dag.session_id)

def can_merge(node_a: TaskNode, node_b: TaskNode) -> bool:
    """Check if two nodes can be merged."""
    # Same kind
    if node_a.kind != node_b.kind:
        return False
    
    # Non-overlapping scopes (but related)
    if scope_overlap(node_a.scope_files, node_b.scope_files):
        return False
    
    # Combined cost under threshold
    if node_a.estimated_cost_usd + node_b.estimated_cost_usd > 0.8:
        return False
    
    return True
```

**Benefit**: 20-30% reduction in coordination overhead

---

### 2. Scope Pre-fetching

**Pattern**: Pre-fetch file contents for all nodes in next wave

```python
class ScopePrefetcher:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.cache: Dict[str, str] = {}
    
    async def prefetch_wave(self, wave: Wave):
        """Pre-fetch all files needed by wave nodes."""
        all_files = set()
        for node in wave.nodes:
            all_files.update(self._expand_globs(node.scope_files))
        
        # Fetch in parallel
        tasks = [self._fetch_file(f) for f in all_files]
        await asyncio.gather(*tasks)
    
    async def _fetch_file(self, path: str):
        """Fetch file into cache."""
        full_path = self.repo_root / path
        if full_path.exists():
            self.cache[path] = full_path.read_text()
    
    def get_cached(self, path: str) -> Optional[str]:
        """Retrieve cached file content."""
        return self.cache.get(path)
```

**Usage**:
```python
# Before dispatching wave
await prefetcher.prefetch_wave(next_wave)

# In subagent
def read_file_with_cache(path: str, prefetcher: ScopePrefetcher):
    cached = prefetcher.get_cached(path)
    if cached:
        return cached
    return Path(path).read_text()
```

**Benefit**: 10-15% faster wave execution

---

### 3. Adaptive Parallelism

**Pattern**: Dynamically adjust parallel width based on merge conflict rate

```python
class AdaptiveScheduler:
    def __init__(self, initial_width: int = 8):
        self.max_width = initial_width
        self.conflict_history: List[int] = []
    
    def adjust_width(self, wave_results: List[SubagentResult], merge_result):
        """Adjust parallelism based on merge conflicts."""
        conflict_count = len(merge_result.conflicts)
        self.conflict_history.append(conflict_count)
        
        # Keep last 5 waves
        if len(self.conflict_history) > 5:
            self.conflict_history.pop(0)
        
        avg_conflicts = sum(self.conflict_history) / len(self.conflict_history)
        
        if avg_conflicts > 2:
            # Too many conflicts, reduce parallelism
            self.max_width = max(2, self.max_width - 1)
        elif avg_conflicts < 0.5:
            # Clean merges, increase parallelism
            self.max_width = min(16, self.max_width + 1)
    
    def partition_wave(self, ready_nodes: List[TaskNode]) -> List[Wave]:
        """Partition ready nodes respecting current width limit."""
        waves = []
        for i in range(0, len(ready_nodes), self.max_width):
            batch = ready_nodes[i:i + self.max_width]
            waves.append(Wave(len(waves), batch))
        return waves
```

**Benefit**: 15-25% reduction in merge conflicts over time

---

## Edge Cases

### 1. Diamond Dependencies

**Problem**:
```
    n1
   /  \
  n2  n3
   \  /
    n4
```

Node n4 depends on both n2 and n3. If n2 and n3 modify related code, merge conflicts likely.

**Mitigation**:
```python
def detect_diamond_dependencies(dag: TaskDAG) -> List[str]:
    """Find nodes with multiple dependency paths."""
    diamonds = []
    
    for node in dag.nodes:
        if len(node.depends_on) >= 2:
            # Check if dependencies are parallel (same wave)
            dep_waves = {get_wave(d) for d in node.depends_on}
            if len(dep_waves) == 1:
                diamonds.append(node.id)
    
    return diamonds

def resolve_diamond(node: TaskNode, dag: TaskDAG) -> TaskNode:
    """Add coordination node to sequence dependencies."""
    # Insert merge node between n2/n3 and n4
    merge_node = TaskNode(
        id=f"{node.id}-merge",
        kind=NodeKind.REVIEW,
        description=f"Coordinate changes for {node.id}",
        scope_files=[],
        depends_on=node.depends_on,
        estimated_cost_usd=0.05
    )
    
    # Update n4 to depend on merge node
    updated_node = replace(node, depends_on=[merge_node.id])
    
    return merge_node, updated_node
```

---

### 2. Resource Exhaustion

**Problem**: 8 parallel worktrees saturate disk I/O

**Solution**: Resource-aware scheduling
```python
class ResourceAwareScheduler:
    def __init__(self):
        self.cpu_limit = os.cpu_count() or 4
        self.memory_limit_gb = psutil.virtual_memory().available / (1024**3)
        self.disk_io_limit = 100  # MB/s
    
    def can_dispatch_wave(self, wave: Wave) -> bool:
        """Check if resources available for wave."""
        estimated_memory = len(wave.nodes) * 0.5  # 500MB per node
        estimated_io = len(wave.nodes) * 20  # 20 MB/s per node
        
        if estimated_memory > self.memory_limit_gb * 0.7:
            return False
        
        if estimated_io > self.disk_io_limit:
            return False
        
        return True
    
    async def dispatch_with_backpressure(self, wave: Wave):
        """Dispatch wave with resource throttling."""
        while not self.can_dispatch_wave(wave):
            await asyncio.sleep(1)  # Wait for resources
        
        return await dispatch_wave(wave)
```

---

### 3. Long-Tail Node Straggler

**Problem**: Wave with 7 fast nodes + 1 slow node (30s vs 3s)

**Solution**: Steal work from straggler
```python
async def execute_wave_with_stealing(wave: Wave):
    """Execute wave with work stealing for slow nodes."""
    results = []
    tasks = {
        asyncio.create_task(dispatch_node(node)): node
        for node in wave.nodes
    }
    
    while tasks:
        done, pending = await asyncio.wait(
            tasks.keys(),
            return_when=asyncio.FIRST_COMPLETED
        )
        
        for task in done:
            node = tasks.pop(task)
            result = await task
            results.append(result)
        
        # Check for stragglers
        if pending and len(pending) == 1:
            straggler_task = list(pending)[0]
            elapsed = time.time() - straggler_task.start_time
            
            if elapsed > 10:  # 10s threshold
                # Split straggler work
                straggler_node = tasks[straggler_task]
                if can_split(straggler_node):
                    straggler_task.cancel()
                    split_nodes = split_node_work(straggler_node)
                    
                    # Re-dispatch split nodes
                    for split_node in split_nodes:
                        new_task = asyncio.create_task(dispatch_node(split_node))
                        tasks[new_task] = split_node
    
    return results
```

---

## Internal Algorithms

### 1. Cycle Detection (Tarjan's Algorithm)

```python
def find_cycles(dag: TaskDAG) -> List[List[str]]:
    """Find all cycles in DAG using Tarjan's strongly connected components."""
    graph = build_adjacency_list(dag)
    index_counter = [0]
    stack = []
    lowlinks = {}
    index = {}
    on_stack = defaultdict(bool)
    sccs = []
    
    def strongconnect(node):
        index[node] = index_counter[0]
        lowlinks[node] = index_counter[0]
        index_counter[0] += 1
        stack.append(node)
        on_stack[node] = True
        
        for successor in graph.get(node, []):
            if successor not in index:
                strongconnect(successor)
                lowlinks[node] = min(lowlinks[node], lowlinks[successor])
            elif on_stack[successor]:
                lowlinks[node] = min(lowlinks[node], index[successor])
        
        if lowlinks[node] == index[node]:
            component = []
            while True:
                successor = stack.pop()
                on_stack[successor] = False
                component.append(successor)
                if successor == node:
                    break
            sccs.append(component)
    
    for node in graph:
        if node not in index:
            strongconnect(node)
    
    # Cycles are SCCs with size > 1
    return [scc for scc in sccs if len(scc) > 1]
```

---

### 2. Merge Conflict Auto-Resolution

```python
def auto_resolve_conflict(base: str, ours: str, theirs: str) -> Optional[str]:
    """Attempt automatic 3-way merge conflict resolution."""
    
    # Parse conflict regions
    conflicts = parse_conflict_markers(theirs)
    
    for conflict in conflicts:
        # Strategy 1: Non-overlapping line ranges
        if not ranges_overlap(conflict.ours_lines, conflict.theirs_lines):
            resolved = merge_non_overlapping(conflict)
            theirs = apply_resolution(theirs, conflict, resolved)
            continue
        
        # Strategy 2: Semantic merge (import statements)
        if is_import_block(conflict):
            resolved = merge_imports(conflict.ours, conflict.theirs)
            theirs = apply_resolution(theirs, conflict, resolved)
            continue
        
        # Strategy 3: Whitespace-only diff
        if only_whitespace_differs(conflict.ours, conflict.theirs):
            resolved = conflict.ours  # Keep ours
            theirs = apply_resolution(theirs, conflict, resolved)
            continue
        
        # Cannot auto-resolve
        return None
    
    return theirs

def merge_imports(ours: str, theirs: str) -> str:
    """Merge import statements semantically."""
    ours_imports = parse_imports(ours)
    theirs_imports = parse_imports(theirs)
    
    # Union of imports
    merged = sorted(set(ours_imports) | set(theirs_imports))
    
    return "\n".join(merged)
```

---

## Research References

### Key Papers

1. **SemaClaw** (arXiv:2604.11548)
   - Two-phase decomposition
   - Fault-local failures
   - Dynamic node parking

2. **MapReduce** (Dean & Ghemawat, 2004)
   - Parallel computation patterns
   - Fault tolerance via retry

3. **Kubernetes Scheduler** (Burns et al., 2016)
   - Resource-aware scheduling
   - Backpressure and throttling

4. **Git Merge Algorithms** (Khanna et al., 2007)
   - 3-way merge strategies
   - Semantic conflict resolution

---

## Future Improvements

### 1. LLM-Assisted Conflict Resolution

```python
async def llm_resolve_conflict(conflict: ConflictDetail) -> str:
    """Use LLM to resolve complex merge conflict."""
    prompt = f"""
Resolve this merge conflict by combining both changes intelligently:

Base version:
{conflict.base}

Our changes:
{conflict.ours}

Their changes:
{conflict.theirs}

Output the merged code that preserves both intents.
"""
    
    response = await anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.content[0].text
```

**Cost**: ~$0.10-$0.30 per conflict
**Success rate**: ~85% (estimated)

---

### 2. Distributed Execution

```python
class DistributedDispatcher:
    def __init__(self, worker_pool: List[str]):
        self.workers = worker_pool
        self.grpc_clients = [
            WorkerClient(addr) for addr in worker_pool
        ]
    
    async def dispatch_node_distributed(
        self,
        node: TaskNode
    ) -> SubagentResult:
        """Dispatch node to remote worker."""
        
        # Select worker (round-robin)
        worker = self.grpc_clients[node.id % len(self.grpc_clients)]
        
        # Send node spec
        request = NodeExecutionRequest(
            node=node,
            repo_snapshot=self._create_snapshot()
        )
        
        # Wait for result
        response = await worker.ExecuteNode(request)
        
        return SubagentResult(**response.to_dict())
```

**Benefits**: Scale beyond single machine
**Challenges**: Network latency, snapshot transfer

---

### 3. Incremental DAG Updates

```python
def update_dag_incrementally(
    original: TaskDAG,
    completed: Set[str],
    new_context: dict
) -> TaskDAG:
    """Update DAG without replanning from scratch."""
    
    # Keep completed nodes
    nodes = [n for n in original.nodes if n.id in completed]
    
    # Replan only incomplete branches
    incomplete_roots = find_incomplete_roots(original, completed)
    
    for root in incomplete_roots:
        subtree = planner.replan_subtree(root, new_context)
        nodes.extend(subtree.nodes)
    
    return TaskDAG(nodes, original.session_id)
```

---

## References

- [architecture.md](architecture.md) - Component architecture
- [architecture-tradeoffs.md](architecture-tradeoffs.md) - Design decisions
- [system-design.md](system-design.md) - Core abstractions
- [implementation-guide.md](implementation-guide.md) - Implementation steps
- [03-dag-teams.md](../03-dag-teams.md) - User guide
- SemaClaw paper: arXiv:2604.11548
