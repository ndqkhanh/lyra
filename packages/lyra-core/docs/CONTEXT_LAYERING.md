# Layered Context System Architecture

## Overview

The layered context system solves the O(n²) context growth problem by organizing context into 8 distinct layers with explicit ownership, persistence policies, and budget enforcement.

## 8-Layer Architecture

### Layer Hierarchy (Assembly Order)

1. **SYSTEM** (5,000 tokens)
   - System prompts, capabilities
   - Static, always loaded
   - Highest priority (10)

2. **USER** (2,000 tokens)
   - User preferences, directives
   - Session-scoped
   - High priority (8-9)

3. **PROJECT** (10,000 tokens)
   - Project context, CLAUDE.md
   - Project-scoped
   - High priority (8-9)

4. **SESSION** (20,000 tokens)
   - Current session state
   - Session-scoped
   - Medium priority (6-7)

5. **TASK** (15,000 tokens)
   - Current task context
   - Task-scoped
   - Medium-high priority (7-8)

6. **TOOL** (10,000 tokens)
   - Tool results, outputs
   - Ephemeral (TTL-based)
   - Medium priority (5-7)

7. **MEMORY** (20,000 tokens)
   - Retrieved memories, discoveries
   - Query-scoped
   - Medium priority (6-8)

8. **DYNAMIC** (18,000 tokens)
   - Runtime additions
   - Ephemeral
   - Variable priority (5-9)

**Total Budget: 100,000 tokens**

## Key Features

### 1. Provenance Tracking

Every entry knows its source:
```python
entry = ContextEntry(
    layer=ContextLayer.MEMORY,
    content="Found paper: Attention Is All You Need",
    source="discovery:arxiv",
    priority=8,
)
```

Query provenance:
```python
results = manager.get_provenance("Attention Is All You Need")
# Returns: [ContextEntry(source="discovery:arxiv", ...)]
```

### 2. Budget Enforcement

Per-layer and total budget limits:
```python
manager = LayeredContextManager(max_tokens=100_000)
manager.add(ContextLayer.MEMORY, content, source, priority=7)
manager.assemble()  # Triggers budget enforcement
```

Budget enforcement operates in two phases:
1. Per-layer budget enforcement (prune low-priority entries)
2. Total budget enforcement (if still over)

### 3. TTL Support

Automatic expiration of ephemeral content:
```python
manager.add(
    ContextLayer.TOOL,
    "File contents: ...",
    source="tool:read",
    ttl_seconds=300,  # Expire after 5 minutes
)
```

### 4. Priority-Based Pruning

Keep high-priority content when over budget:
- Priority 10: System prompts (never pruned)
- Priority 8-9: User/project context (rarely pruned)
- Priority 6-7: Task/memory context (pruned when needed)
- Priority 5: Tool outputs (pruned first)

### 5. Layer-Specific Assembly

Build context from selected layers only:
```python
# Full context
context = manager.assemble()

# Minimal context (system + project only)
context = manager.assemble(layers=[
    ContextLayer.SYSTEM,
    ContextLayer.PROJECT,
])
```

## Child-Task Context Isolation

### Isolation Policies

Three pre-defined policies for different agent types:

#### Discovery Agent
- **Inherit**: SYSTEM, PROJECT
- **Merge**: MEMORY, DYNAMIC
- **Strategy**: SELECTIVE (priority >= 7)
- **Budget**: 30,000 tokens
- **Savings**: 60-70%

```python
policy = IsolationPolicy.for_discovery_agent()
boundary = ContextBoundary(parent, policy)
child = boundary.spawn_child("discovery_1")
```

#### Analysis Agent
- **Inherit**: SYSTEM, USER, PROJECT, TASK
- **Merge**: MEMORY, DYNAMIC
- **Strategy**: SELECTIVE (priority >= 7)
- **Budget**: 50,000 tokens
- **Savings**: 40-50%

```python
policy = IsolationPolicy.for_analysis_agent()
boundary = ContextBoundary(parent, policy)
child = boundary.spawn_child("analysis_1")
```

#### Synthesis Agent
- **Inherit**: SYSTEM, USER, PROJECT, SESSION, TASK, MEMORY
- **Merge**: DYNAMIC
- **Strategy**: APPEND (all entries)
- **Budget**: 80,000 tokens
- **Savings**: 20-30%

```python
policy = IsolationPolicy.for_synthesis_agent()
boundary = ContextBoundary(parent, policy)
child = boundary.spawn_child("synthesis_1")
```

### Merge Strategies

Four merge strategies control how child results are merged back:

1. **APPEND**: Add all child entries to parent
2. **REPLACE**: Replace parent entries with child
3. **SELECTIVE**: Merge only high-priority entries (priority >= 7)
4. **NONE**: Don't merge (full isolation)

### Context Boundary Lifecycle

```python
# 1. Create boundary with policy
boundary = ContextBoundary(parent, policy)

# 2. Spawn child context
child = boundary.spawn_child("task_1")

# 3. Child performs work
child.add(ContextLayer.MEMORY, "Discovery", "source", priority=8)

# 4. Merge results back to parent
result = boundary.merge_child(child, "task_1")

# 5. Check isolation stats
stats = boundary.get_isolation_stats("task_1")
print(f"Saved {stats.tokens_saved} tokens ({stats.reduction_percent:.1f}%)")
```

## Integration with ResearchOrchestrator

### Full Pipeline Flow

```python
class ResearchOrchestrator:
    def __init__(self):
        # Initialize layered context
        self.context_manager = LayeredContextManager(max_tokens=100_000)
        self.audit_trail = ContextAuditTrail()
        self.context_manager.audit_trail = self.audit_trail
        
        # Create boundaries for each agent type
        self.discovery_boundary = ContextBoundary(
            self.context_manager,
            IsolationPolicy.for_discovery_agent(),
        )
        self.analysis_boundary = ContextBoundary(
            self.context_manager,
            IsolationPolicy.for_analysis_agent(),
        )
        self.synthesis_boundary = ContextBoundary(
            self.context_manager,
            IsolationPolicy.for_synthesis_agent(),
        )
    
    def research(self, topic: str, depth: str = "deep"):
        # Add query to TASK layer
        self.context_manager.add(
            ContextLayer.TASK,
            f"Research: {topic}",
            source="user_query",
            priority=9,
        )
        
        # Phase 1: Discovery (6 parallel agents with isolation)
        for i in range(6):
            child = self.discovery_boundary.spawn_child(f"discovery_{i}")
            # ... execute discovery with isolated context
            self.discovery_boundary.merge_child(child, f"discovery_{i}")
        
        # Phase 2: Analysis (parallel agents with isolation)
        for i in range(3):
            child = self.analysis_boundary.spawn_child(f"analysis_{i}")
            # ... execute analysis with isolated context
            self.analysis_boundary.merge_child(child, f"analysis_{i}")
        
        # Phase 3: Synthesis (full context)
        child = self.synthesis_boundary.spawn_child("synthesis_1")
        # ... execute synthesis with full context
        self.synthesis_boundary.merge_child(child, "synthesis_1")
        
        return report
```

## Performance Characteristics

### Context Reduction
- **10 sources**: 60-80% reduction
- **50 sources**: 60-80% reduction
- **100 sources**: 60-80% reduction
- **200 sources**: 60-80% reduction

### Growth Characteristics
- **Without layering**: O(n²) growth
- **With layering**: O(1) growth (bounded by budget)

### Agent Isolation Savings
- **Discovery agents**: 60-70% token savings
- **Analysis agents**: 40-50% token savings
- **Synthesis agents**: 20-30% token savings

### Performance Overhead
- **Add operations**: <5% overhead
- **Assemble operations**: <5% overhead
- **Prune operations**: <5% overhead
- **Budget enforcement**: <5% overhead

### Memory Efficiency
- **10 entries**: <1MB
- **100 entries**: <10MB
- **1000 entries**: <100MB
- **No memory leaks**: <10% growth after 1000 operations

## Usage Examples

### Basic Usage

```python
# Create manager
manager = LayeredContextManager(max_tokens=100_000)

# Add system context
manager.add(
    ContextLayer.SYSTEM,
    "You are a helpful assistant",
    source="system_prompt",
    priority=10,
)

# Add task context
manager.add(
    ContextLayer.TASK,
    "Research deep learning",
    source="user_query",
    priority=9,
)

# Add tool results (with TTL)
manager.add(
    ContextLayer.TOOL,
    "File contents: ...",
    source="tool:read",
    priority=6,
    ttl_seconds=300,
)

# Assemble context
context = manager.assemble()
```

### Multi-Agent Coordination

```python
# Parent context
parent = LayeredContextManager(max_tokens=100_000)
parent.add(ContextLayer.SYSTEM, "System", "system", priority=10)

# Spawn 6 discovery agents
boundary = ContextBoundary(parent, IsolationPolicy.for_discovery_agent())

for i in range(6):
    child = boundary.spawn_child(f"discovery_{i}")
    
    # Child discovers sources
    child.add(
        ContextLayer.MEMORY,
        f"Found source {i}",
        source=f"discovery_{i}",
        priority=7,
    )
    
    # Merge back to parent
    boundary.merge_child(child, f"discovery_{i}")

# Parent now has all discoveries
discoveries = parent.get_layer(ContextLayer.MEMORY)
print(f"Found {len(discoveries)} sources")
```

### Debugging with Provenance

```python
# Add audit trail
manager.audit_trail = ContextAuditTrail()

# Perform operations
manager.add(ContextLayer.MEMORY, "Content", "source", priority=7)
manager.prune()
manager.enforce_budget()

# Get audit trail
events = manager.audit_trail.get_events()
for event in events:
    print(f"{event.timestamp}: {event.event_type}")

# Query provenance
results = manager.get_provenance("Content")
for entry in results:
    print(f"Found in {entry.layer.value} from {entry.source}")

# Get debugger
debugger = manager.get_debugger()
timeline = debugger.get_timeline()
```

## Troubleshooting

### Context Budget Exceeded

**Symptom**: Context exceeds 100,000 tokens

**Solution**:
1. Check budget usage: `manager.get_budget_usage()`
2. Identify over-budget layers
3. Reduce priority of low-value entries
4. Add TTL to ephemeral content
5. Use child-task isolation for sub-tasks

### High-Priority Content Pruned

**Symptom**: Important content is being pruned

**Solution**:
1. Increase priority (8-10 for critical content)
2. Move to higher-priority layer (SYSTEM, USER, PROJECT)
3. Increase layer budget (if justified)

### Child Context Too Large

**Symptom**: Child context exceeds policy budget

**Solution**:
1. Use more restrictive policy (e.g., discovery instead of analysis)
2. Reduce inherited layers
3. Lower child budget in policy
4. Prune parent context before spawning child

### Memory Leaks

**Symptom**: Memory usage grows over time

**Solution**:
1. Add TTL to ephemeral content
2. Call `prune()` regularly
3. Clear layers after use: `manager.clear_layer(layer)`
4. Check for circular references in metadata

## Testing

### Unit Tests
- `test_layered_context.py`: 38 tests
- `test_provenance.py`: 37 tests
- `test_isolation.py`: 33 tests

### Integration Tests
- `test_context_integration.py`: 30+ tests
- Full orchestrator integration
- Multi-agent coordination
- Budget enforcement across pipeline

### Benchmarks
- `test_context_benchmarks.py`: 20+ benchmarks
- Context reduction validation
- Growth characteristics
- Agent isolation savings
- Performance overhead
- Memory efficiency

### Running Tests

```bash
# All context tests
pytest packages/lyra-core/tests/test_layered_context.py -v
pytest packages/lyra-core/tests/test_provenance.py -v
pytest packages/lyra-core/tests/test_isolation.py -v

# Integration tests
pytest packages/lyra-research/tests/test_context_integration.py -v

# Benchmarks
pytest packages/lyra-research/tests/test_context_benchmarks.py -v

# Full suite
pytest packages/ -k context -v
```

## Future Enhancements

### Phase 2: Advanced Features
1. **Semantic deduplication**: Detect and merge similar content
2. **Adaptive budgets**: Adjust layer budgets based on usage
3. **Context compression**: Compress low-priority content
4. **Multi-hop reasoning**: Track reasoning chains across layers

### Phase 3: Optimization
1. **Incremental assembly**: Only reassemble changed layers
2. **Lazy loading**: Load layers on-demand
3. **Parallel pruning**: Prune layers in parallel
4. **Cache-aware budgets**: Optimize for prompt caching

### Phase 4: Observability
1. **Context visualization**: Visual timeline of context changes
2. **Budget alerts**: Warn when approaching limits
3. **Provenance graphs**: Visualize content flow
4. **Performance profiling**: Identify bottlenecks

## References

- **autocontext**: Original inspiration for layered context
- **Phase 1 Week 1**: Core layering infrastructure (38 tests)
- **Phase 1 Week 2**: Provenance tracking (37 tests)
- **Phase 1 Week 3**: Child-task isolation (33 tests)
- **Phase 1 Week 4**: Integration and benchmarking (50+ tests)
